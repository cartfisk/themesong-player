
window.textBuffer = '';
window.admin = false;
window.purgeQueued = false;

function handleKeyDown(e) {
  if (e.target.tagName !== 'INPUT') {
    if (!window.purgeQueued) {
      window.purgeQueued = true;
      setTimeout(purgeBuffer, 1000);
    }
    window.textBuffer += e.key;
    switch (window.textBuffer) {
      case 'racecar':
        window.admin = true;

        let adminButtons = [
          document.getElementById("restart-server-button"),
          document.getElementById("lock-kitchen"),
          document.getElementById("unlock-kitchen")
        ];
        let consoleOut = document.getElementById("console-output");

        const unHide = (element) => {
          element.disabled = false;
          element.removeAttribute("hidden");
        }

        adminButtons.forEach((b) => unHide(b));

        console.log('Congratulations! You are now an admin');
        consoleOut.innerHTML = 'Congratulations! You are now an admin';

        purgeBuffer();
        break;

      case 'q1':
        if (window.admin) {
          get('v1/devices/lock/Kitchen', function() {
            console.log('Kitchen Chromecast is now LOCKED.');
            consoleOut.innerHTML = 'Kitchen Chromecast is now LOCKED.';
          });
        }
        purgeBuffer();
        break;

      case 'q2':
        if (window.admin) {
          get('v1/devices/unlock/Kitchen', function() {
            console.log('Kitchen Chromecast is now UNLOCKED.');
            consoleOut.innerHTML = 'Kitchen Chromecast is now UNLOCKED.';
          });
        }
        purgeBuffer();
        break;

      default:
        break;
    }
  }
}

const addUser = async (form) => {
  const url = 'v1/users';
  const data = new URLSearchParams();
  for (const pair of new FormData(form)) {
      data.append(pair[0], pair[1]);
  }
  const response = await fetch(url, { method: 'POST', body: data });

  const body = await response.json();

  if (body.status_code === 200) {
    console.log(body);
    const form = document.getElementById('user-form');

    const clear = (element) => {
      element.value = "";
    }
    [...form.elements].forEach((b) => clear(b));
    message.innerHTML = "User created successfully!";
  } else {
    message.innerHTML = body.error;
  }
  setTimeout(clearMessage, 5000);

}

function get(url, callback) {
  let xmlHttp = new XMLHttpRequest();
  xmlHttp.onreadystatechange = function() {
      if (xmlHttp.readyState == 4 && xmlHttp.status == 200) {
          callback ? callback(xmlHttp.responseText) : console.log('successful GET');
      }
  }
  xmlHttp.open("GET", url, true);
  xmlHttp.send(null);
}

const clearMessage = () => {
  const message = document.getElementById('message');
  message.innerHTML = "";
}

function purgeBuffer() {
  if (window.textBuffer) {
    window.textBuffer = '';
    window.purgeQueued = false;
    console.log('buffer purged');
  }
}

document.addEventListener('keydown', handleKeyDown);
