import tornado.ioloop
import tornado.web

from publisher import Work

class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v._asdict() for n, v in enumerate(work.recent)}

    def get(self):
        self.write(self.recent)

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
