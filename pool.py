from Queue import Queue
from threading import Thread


class Worker(Thread):
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        fn, args, kwargs = self.tasks.get()
        try:
            fn(*args, **kwargs)
        except Exception as e:
            print e
        self.tasks.task_done()


class ThreadPool(object):
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in xrange(num_threads):
            Worker(self.tasks)

    def add_task(self, fn, *args, **kwargs):
        self.tasks.put((fn, args, kwargs))

    def wait(self):
        self.tasks.join()
