from flask import Flask, jsonify, request
import redis
import json
import pychromecast
import random

app = Flask(__name__)


GREETINGS = ["{name} is in da house!",
             "{name} just dropped in!",
             "{name} is currently blessing you with their presence!",
             "{name} gives a BIG WAVE!",
             "{name} is in!",
             "{name} is coming out to party!",
             "A disturbance in the force... it must be {name}"]

LOCK_FORMAT = '%s-lock-status'

DEVICE_SET = {"Kitchen", "Home Alone", "Ferris Bueller", "Blues Brothers"}


class Cache(object):
    db = redis.StrictRedis(host='localhost', port=6379, db=0)

    def __getattr__(self, name):
        return getattr(self.db, name)


@app.route('/')
def index():
    return 'Welcome to the Chromecast Emulsion API'


@app.route('/v1/devices', methods=['GET', 'POST'])
def devices():
    chromecasts = pychromecast.get_chromecasts()  # Maybe just do this once on server start? meh.
    devices = [cc.device.friendly_name for cc in chromecasts]
    return jsonify({'status_code': 200, 'data': devices})


@app.route('/v1/devices/lock/<target>', methods=['GET', 'POST'])
def lock(target):
    redis = Cache()
    if target in DEVICE_SET:
        lk = LOCK_FORMAT % (target)
        redis.set(lk, 1)
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
def cast(mac_address, target='Kitchen'):
    chromecasts = pychromecast.get_chromecasts()
    device_map = {cc.device.friendly_name: cc for cc in chromecasts}
    target_cc = device_map.get(target)

    redis = Cache()
    lk = LOCK_FORMAT % (target)
    locked = int(redis.get(lk) or False)
    if locked:
        return jsonify({'status_code': 400, 'error': 'Cannot cast, device is locked'})

    if target_cc:
        target_cc.wait()
        redis = Cache()
        user = json.loads(redis.get(mac_address))
        if user is not None:
            try:
                mc = target_cc.media_controller
                audio = user['audio']
                mc.play_media(audio,
                              'music/mp3',
                              title=random.choice(GREETINGS).format(**user),
                              thumb='http://www.4cinsights.com/wp-content/uploads/2016/02/4C_Logo_New.png')
                return jsonify({'status_code': 200, 'data': 'Playing theme for %s' % (user.get('name', '__THE_ONE_FROM_THE_DATABASE__'))})
            except Exception as e:
                print e
                return jsonify({'status_code': 400, 'error': 'Nothing to do'})
        else:
            return jsonify({'status_code': 400, 'error': 'User not found'})
    else:
        return jsonify({'status_code': 500, 'error': 'Target chromecast not found'})


@app.route('/v1/users', methods=['POST'])
def create_user():
    redis = Cache()
    data = request.json
    print 'Attempting to create user: %s' % data
    try:
        redis.set(data['address'], json.dumps(data))
        return jsonify({'status_code': 200, 'data': data})
    except KeyError:
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
    app.run(host='localhost', port=8080, debug=True)
