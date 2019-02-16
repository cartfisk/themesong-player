from cache import Cache
from utils import arr_fcall

import json
import sys
import time

import pychromecast
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TTL_EXPIRE = 60 * 60 * 16  # reset every 16 hours.
CAST_DURATION = 35
MAX_WAIT_TIME = 120


AUTO_LOCK = '__LOCK__'

chromecasts = {cc.device.friendly_name: cc for cc in pychromecast.get_chromecasts()}


def unpack(d, keys):
    return [d.get(k, default) for k, default in keys]


def fade(targets, seen_key):
    for target in targets:
        target.set_volume(.35)
    time.sleep(CAST_DURATION)
    for _ in range(4):
        arr_fcall(targets, 'volume_down')
        time.sleep(.5)
    for target in targets:
        target.media_controller.stop()
    redis = Cache()
    logger.info('UNLOCKING NOW...')
    redis.set(AUTO_LOCK, 0)
    logger.info('SETTING %s with %s second expiration' % (seen_key, TTL_EXPIRE))
    redis.setex(seen_key, TTL_EXPIRE, 1)


class Channel(object):
    def __init__(self, key):
        self.key = key

    def listen(self, **kwargs):
        redis = Cache()
        pubsub = redis.pubsub()
        pubsub.subscribe(self.key)

        while True:
            message = pubsub.get_message(timeout=.25)

            if message is None:
                continue

            if message.get('type') == 'subscribe':
                continue

            elif message.get('type') == 'unsubscribe':
                break

            logger.info(message)
            data = json.loads(message['data'])
            mtype = data.get('type')
            targets = [chromecasts[t] for t in data.get('targets') if t in chromecasts]
            seen_key, f_args, f_kwargs = unpack(data, [['seen_key', None], ['args', []], ['kwargs', {}]])
            if mtype == 'play':
                try:
                    for target in targets:
                        target.play_media(*f_args, **f_kwargs)
                except Exception:
                    logger.exception('play failed for one or more targets.')
            elif mtype == 'fade':
                try:
                    fade(targets, seen_key)
                except Exception:
                    logger.exception('fade failed')
            else:
                continue

            time.sleep(.001)

        pubsub.unsubscribe(self.key)


def run(key, *args):
    logger.info('Starting Channel for %s...', key)
    Channel(key).listen()


if __name__ == '__main__':
    try:
        run(*sys.argv[1:])
    except Exception:
        logger.exception('Something went wrong!')
        sys.exit(1)
