from flask import Flask, jsonify, request, render_template
from pool import ThreadPool

import redis as _redis
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

cast_pool = ThreadPool(2)
fade_pool = ThreadPool(1)


class Cache(object):
    db = _redis.StrictRedis(host='localhost', port=6379, db=0)

    def __init__(self):
        with open('users.json', 'w') as f:
            data = []
            for k in self.db.keys():
                if '-' in k or '_' in k:
                    continue
                try:
                    data.append(json.loads(self.db.get(k)))
                except Exception:
                    continue
            s = json.dumps(data,
                           indent=4,
                           sort_keys=True,
                           separators=(',', ': '),
                           ensure_ascii=False)
            f.write(s)

    def __getattr__(self, name):
        return getattr(self.db, name)


chromecasts = {cc.device.friendly_name: cc for cc in pychromecast.get_chromecasts()}


def arr_fcall(targets, fname, *args, **kwargs):
    for t in targets:
        if hasattr(t, fname):
            fn = getattr(t, fname)
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)


def play(targets, args, kwargs):
    for target in targets:
        target.wait()
        target.play_media(*args, **kwargs)
    fade_pool.add_task(fade, targets)


def fade(targets):
    arr_fcall(targets, 'set_volume', 0)
    for _ in xrange(4):
        arr_fcall(targets, 'volume_up')
        time.sleep(.5)
    time.sleep(CAST_DURATION)
    for _ in xrange(4):
        arr_fcall(targets, 'volume_down')
        time.sleep(.5)
    for target in targets:
        target.wait()
        target.media_controller.skip()
        target.set_volume(0)


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
        lk = LOCK_FORMAT % (target)
        redis.set(lk, 1)
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
        lk = LOCK_FORMAT % (target)
        redis.set(lk, 0)
        return jsonify({'status_code': 200, 'data': True})
    return jsonify({'status_code': 400, 'error': 'Unsupported Target'})


@app.route('/v1/users/<mac_address>', methods=['GET'])
def cast(mac_address, targets=['Kitchen', 'GameRoom']):
    target_ccs = filter(bool, [chromecasts.get(target) for target in targets])

    redis = Cache()

    glk = LOCK_FORMAT % ('master')  # meh.
    locked = int(redis.get(glk) or False)
    if locked:
        return jsonify({'status_code': 400, 'error': 'Cannot cast, devices locked'})

    sk = SEEN_FORMAT % (mac_address)
    seen = int(redis.get(sk) or False)
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

    devices, data = target_ccs, []
    media_args = (audio, 'music/mp3')
    media_kwargs = {'title': random.choice(GREETINGS).format(**user),
                    'thumb': 'http://www.4cinsights.com/wp-content/uploads/2016/02/4C_Logo_New.png'}
    for target_cc in target_ccs:
        data.append({'info': 'Playing theme for %s on %s' % (name, target_cc.device.friendly_name)})

    cast_pool.add_task(play, devices, media_args, media_kwargs)
    redis.setex(glk, CAST_DURATION, 1)
    redis.setex(sk, TTL_EXPIRE, 1)
    cast_pool.wait()

    status_code = 200 if len(data) else 500
    if status_code == 200:
        return jsonify({'status_code': 200, 'data': data})
    else:
        return jsonify({'status_code': 500, 'error': 'Target chromecast not found'})


@app.route('/v1/users', methods=['POST'])
def create_user():
    redis = Cache()
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
