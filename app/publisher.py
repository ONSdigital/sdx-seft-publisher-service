from collections import namedtuple
import logging

import pika
import pika.adapters

Job = namedtuple("Job", ["ts", "filename", "file"])


class DurableTopicPublisher:

    EXCHANGE = 'message'
    PUBLISH_INTERVAL = 1
    ROUTING_KEY = "JWT"

    def __init__(self, amqp_url, queue_name, log=None, **kwargs):
        self.logger = log or logging.getLogger("sdx.seft")
        self.confirmed_deliveries = []

        self._connection = None
        self._channel = None
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._stopping = False
        self._url = amqp_url
        self.queue_name = queue_name
        self._closing = False
        self.publishing = False

    def connect(self):
        self.logger.info("Connecting...")
        return pika.adapters.TornadoConnection(
            pika.URLParameters(self._url),
            self.on_connection_open,
            stop_ioloop_on_close=False
        )

    def on_connection_open(self, unused_connection):
        self.logger.info("Connection opened")
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        self.logger.info("Adding connection close callback")
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, unused_connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self.logger.warning(
                "Connection closed, reopening in 5 seconds: (%s) %s",
                reply_code, reply_text
            )
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        self._acked = 0
        self._nacked = 0
        self._message_number = 0

        # Create a new connection
        self._connection = self.connect()

    def open_channel(self):
        self.logger.info("Creating a new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self.logger.info("Channel opened")
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        self.logger.info("Adding channel close callback")
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, unused_channel, reply_code, reply_text):
        self.logger.warning("Channel was closed: (%s) %s", reply_code, reply_text)
        if not self._closing:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        self.logger.info("Declaring exchange %s", exchange_name)
        self._channel.exchange_declare(
            self.on_exchange_declareok, exchange_name, "topic"
        )

    def on_exchange_declareok(self, unused_frame):
        self.logger.info("Exchange declared")
        self.setup_queue(self.queue_name)

    def setup_queue(self, queue_name):
        self.logger.info("Declaring queue %s", queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name, durable=True)

    def on_queue_declareok(self, unused_method_frame):
        self.logger.info(
            "Binding %s to %s with %s",
            self.EXCHANGE, self.queue_name, self.ROUTING_KEY
        )
        self._channel.queue_bind(self.on_bindok, self.queue_name,
                                 self.EXCHANGE, self.ROUTING_KEY)

    def on_bindok(self, unused_frame):
        self.logger.info("Queue bound")
        self.start_publishing()

    def start_publishing(self):
        self.logger.info("Issuing consumer related RPC commands")
        self.enable_delivery_confirmations()
        self.publishing = True

    def enable_delivery_confirmations(self):
        self.logger.info("Issuing Confirm.Select RPC command")
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split(".")[1].lower()
        self.logger.info(
            "Received %s for delivery tag: %i",
            confirmation_type,
            method_frame.method.delivery_tag
        )
        if confirmation_type == "ack":
            self._acked += 1
        elif confirmation_type == "nack":
            self._nacked += 1
        self.confirmed_deliveries.append(method_frame.method.delivery_tag)
        self.logger.info(
            "Published %i messages, %i have been confirmed, "
            "%i were acked and %i were nacked",
            self._message_number, len(self.confirmed_deliveries),
            self._acked, self._nacked
        )

    def schedule_next_message(self):
        if self._stopping:
            return
        self.logger.info(
            "Scheduling next message for %0.1f seconds",
            self.PUBLISH_INTERVAL
        )
        self._connection.add_timeout(self.PUBLISH_INTERVAL,
                                     self.publish_message)

    def publish_message(self, message, content_type=None, headers=None):
        if self._channel is None or self._stopping:
            return None

        properties = pika.BasicProperties(
            app_id="sdx.seft", content_type=content_type, headers=headers
        )

        self._channel.basic_publish(
            self.EXCHANGE, self.ROUTING_KEY, message, properties,
            mandatory=True, immediate=False
        )
        self._message_number += 1
        self.logger.info("Published message # %i", self._message_number)
        return self._message_number

    def close_channel(self):
        self.logger.info("Closing the channel")
        if self._channel:
            self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        self.logger.info("Stopping")
        self._stopping = True
        self.close_channel()
        self.close_connection()
        self._connection.ioloop.start()
        self.logger.info("Stopped")

    def close_connection(self):
        self.logger.info("Closing connection")
        self._closing = True
        self._connection.close()
