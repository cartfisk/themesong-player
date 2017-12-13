# http-chromecast-emulsion
Basic Python (Flask) API that maps a MAC address to an audio file and streams to ChromeCast via CASTV2

This was written as part of an implementation of [@buntine](https://github.com/buntine)'s [Hulkamania project](https://dev.to/buntine/hulkamania-or-how-i-made-our-office-play-personalized-entrance-theme-music) at [4C Insights](https://github.com/VoxsupInc)' Chicago office.

### Running the Server

- From the root project directory, run `./restart.sh/` to start the server.

- Access a user-friendly webUI for adding users at `http://<server_ip>:8080`.

### Setup

1. [Configure a remote syslog server](https://dev.to/buntine/hulkamania-or-how-i-made-our-office-play-personalized-entrance-theme-music) that listens for DHCP events coming from a router/firewall.

2. Convert those messages into HTTP requests. Something like this–

    `GET http://<server-ip>:8080/v1/<MAC_Address>`

3. Add users via HTTP requests or the web portal. You will need:
  - A wifi MAC address (preferrably from a user's mobile device).
  - A url to an MP3 file
    - Could be from the public web or hosted locally.
    - For local hosting, MP3s can be saved to the project directory in `static/songs`.
    - These are accessible via `http://<server-ip>:8080/static/songs/<filename>`.
    - Avoid spaces in filenames. MP3 files only (for now).
  - A user name. (This will be displayed on the Chromecast when the user's song is cast.)
  
4. Run the server with `./restart.sh`.

5. Done!

This project is under semi-active development.





