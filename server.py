from flask import Flask, jsonify, request, render_template
from cache import Cache
from utils import now, arr_fcall

import json
import pychromecast
import random
import time

app = Flask(__name__)


GREETINGS = ["{name} is in da house!",
             "{name} just dropped in!",
             "{name} is currently blessing you with their presence!",
             "{name} gives a BIG WAVE!",
             "{name} is in!",
             "{name} is coming out to party!",
             "{name} is seen wandering the corridors",
             "{name} makes a grand entrance!",
             "{name} can't wait to start the day!",
             "Welcome back, {name}! We've missed you.",
             "A wild {name} appears!"]

LOCK_FORMAT = '%s-lock-status'

DEVICE_SET = {"Kitchen", "Home Alone", "Ferris Bueller", "Blues Brothers", "GameRoom"}

DEVICE_VOLUME_MAX = {
    "Kitchen": 4,
    "GameRoom speaker": 5,
}

SEEN_FORMAT = '%s-seen'

TTL_EXPIRE = 60 * 60 * 16  # reset every 16 hours.
CAST_DURATION = 35
MAX_WAIT_TIME = 120


AUTO_LOCK = '__LOCK__'
PLAY_QUEUE = 'play'
FADE_QUEUE = 'fade'

chromecasts = {cc.device.friendly_name: cc for cc in pychromecast.get_chromecasts()}


def play(targets, seen_key, args, kwargs):
    redis = Cache()
    redis.set(AUTO_LOCK, now())
    print 'STARTING PLAYBACK...'
    play_msg = json.dumps({'type': 'play', 'targets': targets, 'seen_key': seen_key, 'args': args, 'kwargs': kwargs})
    fade_msg = json.dumps({'type': 'fade', 'targets': targets, 'seen_key': seen_key})
    redis.publish(PLAY_QUEUE, play_msg)
    redis.publish(FADE_QUEUE, fade_msg)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/v1/devices', methods=['GET', 'POST'])
def devices():
    return jsonify({'status_code': 200, 'data': chromecasts.keys()})


@app.route('/v1/devices/lock/<target>', methods=['GET', 'POST'])
def lock(target):
    redis = Cache()
    if target in DEVICE_SET:
        manual_lock = LOCK_FORMAT % (target)
        redis.set(manual_lock, 1)
        cc = chromecasts.get(target)
        if cc is not None:
            mc = cc.media_controller
            if mc is not None:
                mc.stop()
        return jsonify({'status_code': 200, 'data': True})
    return jsonify({'status_code': 400, 'error': 'Unsupported Target'})


@app.route('/v1/devices/unlock/<target>', methods=['GET', 'POST'])
def unlock(target):
    redis = Cache()
    if target in DEVICE_SET:
        manual_lock = LOCK_FORMAT % (target)
        redis.set(manual_lock, 0)
        return jsonify({'status_code': 200, 'data': True})
    return jsonify({'status_code': 400, 'error': 'Unsupported Target'})


@app.route('/v1/users/<mac_address>', methods=['GET'])
def cast(mac_address, targets=['Kitchen', 'GameRoom']):
    target_ccs = filter(bool, [chromecasts.get(target) for target in targets])

    redis = Cache()

    locked_time = int(redis.get(AUTO_LOCK) or 0)
    if locked_time:
        if now() > locked_time + MAX_WAIT_TIME:
            redis.set(AUTO_LOCK, 0)
            print 'UNLOCKING DUE TO EXCEEDING MAX WAIT'
        else:
            return jsonify({'status_code': 400, 'error': 'Cannot cast, devices locked'})

    manual_lock = LOCK_FORMAT % ('Kitchen')  # meh.
    if int(redis.get(manual_lock) or 0):
        return jsonify({'status_code': 400, 'error': 'Cannot cast, devices locked'})

    sk = SEEN_FORMAT % (mac_address)
    seen = int(redis.get(sk) or 0)
    if seen:
        return jsonify({'status_code': 200, 'data': {'info': '%s has already been casted today.' % (mac_address)}})

    user = redis.get(mac_address)
    name = '__THE_ONE_FROM_THE_DATABASE__'
    audio = None
    if user is not None:
        user = json.loads(user)
        name = user.get('name')
        try:
            audio = user['audio']
        except KeyError:
            return jsonify({'status_code': 400, 'error': 'No audio to play for user %s' % (name)})
    else:
        return jsonify({'status_code': 400, 'error': 'User not found'})

    devices, data = targets, []
    media_args = (audio, 'music/mp3')
    media_kwargs = {'title': random.choice(GREETINGS).format(**user),
                    'thumb': 'http://10.1.242.213:8080/static/4c-logo-white.png'}
    for target_cc in target_ccs:
        data.append({'info': 'Playing theme for %s on %s' % (name, target_cc.device.friendly_name)})

    play(devices, sk, media_args, media_kwargs)

    status_code = 200 if len(data) else 500
    if status_code == 200:
        return jsonify({'status_code': 200, 'data': data})
    else:
        return jsonify({'status_code': 500, 'error': 'Target chromecast not found'})


@app.route('/v1/users', methods=['GET', 'POST'])
def create_user():
    redis = Cache()
    if request.method == 'GET':
        with open('users.json', 'r') as f:
            return jsonify(json.load(f))
    if request.json:
        data = request.json
    elif request.form:
        data = request.form
    print 'Attempting to create user: %s' % data
    try:
        address = data['address']
        if address in ['', None]:
            raise ValueError
        redis.set(data['address'], json.dumps(data))
        return jsonify({'status_code': 200, 'data': data})
    except (KeyError, ValueError):
        return jsonify({'status_code': 400, 'error': 'MAC Address not provided'})
    except Exception as e:
        print e
        return jsonify({'status_code': 500, 'error': 'Something went wrong'})


@app.route('/v1/users/<mac_address>', methods=['PUT'])
def update_user(mac_address):
    redis = Cache()
    data = request.json
    print 'Attempting to update user for address %s with: %s' % (mac_address, data)
    user = json.loads(redis.get(mac_address))
    if user is not None:
        user.update(data)
        redis.set(mac_address, json.dumps(user))
        return jsonify({'status_code': 200, 'data': user})
    else:
        return jsonify({'status_code': 400, 'error': 'No user to update'})


@app.route('/v1/users/<mac_address>', methods=['DELETE'])
def delete_user(mac_address):
    redis = Cache()
    print 'Deleting entry for %s' % (mac_address)
    success = redis.delete(mac_address) > 0
    return jsonify({'status_code': 200, 'data': success})


@app.route('/v1/reset', methods=['GET'])
def reset_seen():
    redis = Cache()
    n = redis.delete(*redis.keys('*-seen'))
    return jsonify({'status_code': 200, 'data': n})


@app.route('/v1/reset/<mac_address>', methods=['GET'])
def reset_user_seen(mac_address):
    redis = Cache()
    n = redis.delete(*redis.keys('%s-seen' % (mac_address)))
    return jsonify({'status_code': 200, 'data': n})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
