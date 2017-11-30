// server.js

// BASE SETUP
// =============================================================================

// call the packages we need
var express    = require('express');        // call express
var app        = express();                 // define our app using express
var bodyParser = require('body-parser');
var mongoose   = require('mongoose');
var User     = require('./app/models/user');

var Client                = require('castv2-client').Client;
var DefaultMediaReceiver  = require('castv2-client').DefaultMediaReceiver;
var mdns                  = require('mdns');

mongoose.connect('mongodb://localhost/audiomacmap', {
  useMongoClient: true,
  /* other options */
}); // connect to our database

// configure app to use bodyParser()
// this will let us get the data from a POST
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

var port = process.env.PORT || 8080;        // set our port

// ROUTES FOR OUR API
// =============================================================================
var router = express.Router();              // get an instance of the express Router

// middleware to use for all requests
router.use(function(req, res, next) {
    // do logging
    console.log('Something is happening.');
    next(); // make sure we go to the next routes and don't stop here
});

// test route to make sure everything is working (accessed at GET http://localhost:8080/api)
router.get('/', function(req, res) {
    res.json({ message: 'Welcome to the http-gimbal api!' });
});

// on routes that end in /users
// ----------------------------------------------------
router.route('/users')

    // create a user (accessed at POST http://localhost:8080/api/users)
    .post(function(req, res) {

        var user = new User();      // create a new instance of the User model
        console.log("name: " + req.body.name + " address: " + req.body.address + " audio: " + req.body.name)
        user.name = req.body.name;  // set the user's name (comes from the request)
        user.address = req.body.address;
        user.audio = req.body.audio;

        // save the user and check for errors
        user.save(function(err) {
            if (err)
                res.send(err);

            res.json({ message: 'User created!' });
        });

    })

    // get all the users (accessed at GET http://localhost:8080/api/users)
    .get(function(req, res) {
        User.find(function(err, users) {
            if (err)
                res.send(err);

            res.json(users);
        });
    });

  // on routes that end in /users/:user_id
  // ----------------------------------------------------
  router.route('/users/:user_id')

    // get the user with that id (accessed at GET http://localhost:8080/api/users/:user_id)
    .get(function(req, res) {
        User.findById(req.params.user_id, function(err, user) {
            if (err)
                res.send(err);
            res.json(user);

            // CHROMECAST SHIT
            var browser = mdns.createBrowser(mdns.tcp('googlecast'));

            browser.on('serviceUp', function(service) {
              console.log('found device "%s" at %s:%d', service.name, service.addresses[0], service.port);
              // SO IMPORTANT TO NOT DELETE
              if (service.name === 'Chromecast-538f9cdd3694854a98ced8cf7da1568b') {
                ondeviceup(service.addresses[0]);
              }
              browser.stop();
            });

            browser.start();

            function ondeviceup(host) {

              var client = new Client();

              client.connect(host, function() {
                console.log('connected, launching app ...');

                client.launch(DefaultMediaReceiver, function(err, player) {
                  var media = {

                  	// Here you can plug an URL to any mp4, webm, mp3 or jpg file with the proper contentType.
                    contentId: "http://www.kevinsmedia.com/km/mp3z/AmyWinehouse/BackToBlack/" + user.audio,
                    contentType: 'music/mp3',
                    streamType: 'BUFFERED', // or LIVE

                    // Title and cover displayed while buffering
                    metadata: {
                      type: 0,
                      metadataType: 0,
                      title: "Theme Song for " + user.name,
                      images: [
                        { url: 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg' }
                      ]
                    }
                  };

                  player.on('status', function(status) {
                    console.log('status broadcast playerState=%s', status.playerState);
                  });

                  console.log('app "%s" launched, loading media %s ...', player.session.displayName, media.contentId);

                  player.load(media, { autoplay: true }, function(err, status) {
                    console.log('media loaded playerState=%s', status.playerState);

                    // Seek to 2 minutes after 15 seconds playing.
                    setTimeout(function() {
                      player.seek(2*60, function(err, status) {
                        //
                      });
                    }, 15000);

                  });

                });

              });

              client.on('error', function(err) {
                console.log('Error: %s', err.message);
                client.close();
              });

            }
        });
    })

    // update the user with this id (accessed at PUT http://localhost:8080/api/users/:user_id)
    .put(function(req, res) {

        // use our user model to find the user we want
        User.findById(req.params.user_id, function(err, user) {

            if (err)
                res.send(err);

            if (req.body.name) {
              user.name = req.body.name;  // update the user's info
            }
            if (req.body.address) {
              user.address = req.body.address;  // update the user's info
            }
            if (req.body.audio) {
              user.audio = req.body.audio;  // update the user's info
            }

            // save the user
            user.save(function(err) {
                if (err)
                    res.send(err);

                res.json({ message: 'User updated!' });
            });

        });
    })

    // delete the user with this id (accessed at DELETE http://localhost:8080/api/users/:user_id)
    .delete(function(req, res) {
        User.remove({
            _id: req.params.user_id
        }, function(err, user) {
            if (err)
                res.send(err);

            res.json({ message: 'Successfully deleted' });
        });
    });


// more routes for our API will happen here

// REGISTER OUR ROUTES -------------------------------
// all of our routes will be prefixed with /api
app.use('/api', router);

// START THE SERVER
// =============================================================================
app.listen(port);
console.log('Magic happens on port ' + port);
