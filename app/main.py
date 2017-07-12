from collections import deque

import tornado.ioloop
import tornado.web

from ftpclient import FTPWorker


class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v._asdict() for n, v in enumerate(work.recent)}

    def get(self):
        self.write(self.recent)


class Work:
    recent = deque(maxlen=24)

    @classmethod
    def transfer_task(cls, loop):
        worker = FTPWorker(**params)
        # publisher = ?
        with worker as active:
            for job in active.get(active.filenames):
                while True:
                    payload = encrypt(job.contents)
                    if not publisher.publish(payload):
                        continue

                while True:
                    if not active.delete(job.fn):
                        continue

                cls.recent.append((job.ts.isoformat(), job.fn))


def make_app():
    return tornado.web.Application([
        (r"/recent", StatusService, {"work": Work}),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    interval_ms = 30 * 60 * 1000
    sched = tornado.ioloop.PeriodicCallback(
        Work.transfer_task,
        interval_ms,
    )
    # start your period timer
    sched.start()
    tornado.ioloop.IOLoop.current().start()
