import time


def now():
    return int(time.time())


def arr_fcall(targets, fname, *args, **kwargs):
    for t in targets:
        if hasattr(t, fname):
            fn = getattr(t, fname)
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)
