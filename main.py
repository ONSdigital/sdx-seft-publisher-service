from collections import deque
from collections import namedtuple
import datetime

import tornado.ioloop
import tornado.web

class Work:

    Item = namedtuple("Item", ["ts", "tx_id"])
    recent = deque(maxlen=24)

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
    tornado.ioloop.IOLoop.current().start()
