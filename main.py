import base64

from cryptography.hazmat.primitives.serialization import load_pem_public_key
import tornado.ioloop
import tornado.web

from publisher import Work

class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v._asdict() for n, v in enumerate(work.recent)}

    def get(self):
        self.write(self.recent)

class Work:
    recent = deque(maxlen=24)

    @staticmethod
    def encrypt(self, keydata):
        public_key = load_pem_public_key(keydata)
        ciphertext = public_key.encrypt(cek, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None))
        return self._base_64_encode(ciphertext)

    @classmethod
    def transfer_task(cls, loop):
        worker = FTPWorker(**self.params)
        # publisher = ?
        with worker as active:
            for job in active.get(active.filenames):
                while True:
                    payload = encrypt(base64.b64encode(job.contents))
                    if not publisher.publish(payload):
                        loop.sleep(backoff)

                while True:
                    if not active.delete(job.fn):
                        loop.sleep(backoff)

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
    #start your period timer
    sched.start()
    tornado.ioloop.IOLoop.current().start()
