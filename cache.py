import redis as _redis
import json


class Cache(object):
    db = _redis.StrictRedis(host='localhost', port=6379, db=0)

    def __init__(self):
        with open('users.json', 'w') as f:
            data = []
            for k in self.db.keys():
                if b'-' in k or b'_' in k:
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
