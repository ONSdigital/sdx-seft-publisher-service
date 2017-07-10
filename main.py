import tornado.ioloop
import tornado.web

from publisher import Work

class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v._asdict() for n, v in enumerate(work.recent)}

    def get(self):
        self.write(self.recent)

def transfer_task(loop):
    worker = FTPWorker(**self.params)
    # publisher = ?
    with worker as active:
        for item in active.get(active.filenames))
            while True:
                payload = encrypt(item.contents)
                if not publisher.publish(payload):
                    loop.sleep(backoff)

            while True:
                if not active.delete(item.fn):
                    loop.sleep(backoff)

def make_app():
    return tornado.web.Application([
        (r"/recent", StatusService, {"work": Work}),
    ])

if __name__ == "__main__":
    Work.recent.append(Work.Item(datetime.datetime.now().isoformat(), "a" * 32))
    Work.recent.append(Work.Item(datetime.datetime.now().isoformat(), "b" * 32))
    app = make_app()
    app.listen(8888)
    sched = tornado.ioloop.PeriodicCallback(schedule_func,interval_ms, io_loop = main_loop)
    #start your period timer
    sched.start()
    tornado.ioloop.IOLoop.current().start()
