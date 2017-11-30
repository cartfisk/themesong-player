// server.js

// BASE SETUP
// =============================================================================

// call the packages we need
var express       = require('express');        // call express
var app           = express();                 // define our app using express
var bodyParser    = require('body-parser');
var redis         = require('redis');

var Client                = require('castv2-client').Client;
var DefaultMediaReceiver  = require('castv2-client').DefaultMediaReceiver;
var mdns                  = require('mdns');

class Cache {
  constructor() {
    this.db = redis.createClient();

    this.db.on('error', function(err) {
      console.error(err);
    });

    this.db.on('connect', function() {
      console.log('connected to redis');
    });

  }

  get(key, cb) {
    return this.db.get(key, cb);
  }

  set(key, value) {
    const v = JSON.stringify(value);
    console.log(`setting ${key}: ${v}`);
    this.db.set(key, JSON.stringify(value));
  }
}

let redisCache = new Cache();

// configure app to use bodyParser()
// this will let us get the data from a POST
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

var port = process.env.PORT || 8080;        // set our port

// STREAM User.song TO ChromeCast
var cast = (user) => {

  var greetings = [" is in da house!", " just dropped in!", " is currently blessing you with their presence!", " gives a BIG WAVE!", " is in!", " is coming out to party!"];

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
          contentId: user.audio,
          contentType: 'music/mp3',
          streamType: 'BUFFERED', // or LIVE

          // Title and cover displayed while buffering
          metadata: {
            type: 0,
            metadataType: 0,
            title: user.name + greetings[Math.floor(Math.random() * (5 - 0 + 1) + 0)],
            images: [
              { url: 'http://www.4cinsights.com/wp-content/uploads/2016/02/4C_Logo_New.png' }
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

  };

};

const redisCallback = (res, fns=[]) => (err, v) => {
  console.log(v);
  const user = JSON.parse(v);
  for (const f of fns) {
    f(user);
  }
  res.json(user);
}

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
        const user =  { name: req.body.name, audio: req.body.audio };
        redisCache.set(req.body.address, user);
        const cb = redisCallback(res);
        redisCache.get(req.body.address, cb);
    })

    // get all the users (accessed at GET http://localhost:8080/api/users)

    // .get(function(req, res) {
    //   res.json(redisCache.db.keys('*'));
    // });

  // on routes that end in /users/:user_id
  // ----------------------------------------------------
  router.route('/users/:mac_address')

    // get the user with that id (accessed at GET http://localhost:8080/api/users/:user_id)
    .get(function(req, res) {
      const user = redisCache.get(req.params.mac_address, redisCallback(res, [cast]));
    })

    // update the user with this id (accessed at PUT http://localhost:8080/api/users/:user_id)
    .put(function(req, res) {
        if (redisCache.db.exists(req.params.mac_address) && req.body.audio) {
          const putFn = (user) => {
            user.audio = req.body.audio;
            const success = redisCache.set(req.params.mac_address, user);  // update the user's info
            if (success) {
              res.json({ message: `Successfully changed audio for ${user.name}` });
            }
          }
          redisCache.get(req.params.mac_address, redisCallback(res, [putFn]));
        } else {
          res.json({ message: 'User not found' });
        }
    })

    // delete the user with this id (accessed at DELETE http://localhost:8080/api/users/:user_id)
    .delete(function(req, res) {
      res.json(redisCache.db.del(req.params.mac_address));
    });


// more routes for our API will happen here

// REGISTER OUR ROUTES -------------------------------
// all of our routes will be prefixed with /api
app.use('/api', router);

// START THE SERVER
// =============================================================================
app.listen(port);
console.log('Magic happens on port ' + port);
