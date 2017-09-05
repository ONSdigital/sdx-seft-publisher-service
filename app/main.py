from sdc.crypto.encrypter import encrypt
from sdc.crypto.key_store import KeyStore

from app.sdxftp import SDXFTP
from app import settings
from app import create_and_wrap_logger
import yaml
import base64
import pika
import uuid
import json

logger = create_and_wrap_logger(__name__)

KEY_PURPOSE_PRODUCER = "outbound"


class SeftProducer:
    def __init__(self, keys):
        self.key_store = KeyStore(keys)

        self._ftp = SDXFTP(logger,
                           settings.FTP_HOST,
                           settings.FTP_USER,
                           settings.FTP_PASS,
                           settings.FTP_PORT)

    def open_connection(self):
        logger.info("Opening connection to Rabbit MQ")

        parameters = pika.URLParameters(settings.RABBIT_URL)

        # Open a connection to RabbitMQ
        connection = pika.BlockingConnection(parameters)

        # Open the channel
        channel = connection.channel()

        # Declare the queue
        channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True, exclusive=False, auto_delete=False)
        # Turn on delivery confirmations
        channel.confirm_delivery()
        logger.info("Connection open")
        return connection, channel

    def run(self):
        logger.info("About to upload files")
        connection, channel = self.open_connection()

        logger.info("Reading FTP directory")
        files = self._ftp.read_directory()

        for file in files:
            logger.info("Retrieving file {}".format(file))
            file_bytes = self._ftp.read_file(file)
            if file_bytes:
                logger.info("Read file")

                encrypted_file = self.encrypt(file, file_bytes)
                logger.info("Encrypted file")

                if self.publish(channel, encrypted_file):
                    logger.info("Published file")
                    self._ftp.delete_file(file)
                else:
                    logger.error("Error publishing file {}".format(file))
            else:
                logger.error("Error retrieving file from FTP {}".format(file))

        logger.info("Closing connection to Rabbit MQ")
        connection.close()
        logger.info("Connection closed")

    def encrypt(self, file, file_bytes):
        encoded_contents = base64.b64encode(file_bytes)

        payload = '{"filename":"' + file + '", "file":"' + encoded_contents.decode() + '"}'

        payload_as_json = json.loads(payload)

        return encrypt(payload_as_json, self.key_store, KEY_PURPOSE_PRODUCER)

    def publish(self, channel, encrypted_file):
        # Send a message
        headers = {'tx_id': str(uuid.uuid4())}
        logger.info("About to publish file")
        published = channel.basic_publish(exchange=settings.RABBIT_EXCHANGE,
                                          routing_key=settings.RABBIT_QUEUE,
                                          body=encrypted_file,
                                          properties=pika.BasicProperties(
                                              headers=headers,
                                              delivery_mode=2),
                                          mandatory=True, immediate=False)
        logger.info("Published successfully {}".format(published))
        return published


if __name__ == '__main__':
    with open(settings.SDX_SEFT_CONSUMER_KEYS_FILE) as file:
        keys = yaml.safe_load(file)

    seft = SeftProducer(keys)
    seft.run()
