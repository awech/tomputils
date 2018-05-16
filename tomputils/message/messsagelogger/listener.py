# -*- coding: utf8 -*-
"""
Receive messages from broker.
"""
from datetime import datetime
import os
import struct

import pika


class Listener(object):
    def __init__(self, queue):
        self.queue = queue

    def listen(self):
        exchange = os.environ['AVOBROKER_EXCHANGE']
        mycred = pika.credentials.PlainCredentials(
            os.environ['AVOBROKER_USER'],
            os.environ['AVOBROKER_PASS'])

        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=os.environ['AVOBROKER_HOST'], credentials=mycred))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='topic')
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange=exchange, queue=queue_name,
                           routing_key="#")

        print(' [*] Waiting for logs. To exit press CTRL+C')
        channel.basic_consume(self._callback, queue=queue_name, no_ack=True)
        channel.start_consuming()

    def _callback(self, ch, method, properties, body):
        print("ROUTING KEY", method.routing_key)
        print("Message", body)
        print("Length", len(body), struct.pack("<I", len(body)))

        now = datetime.now()
        file_path = now.strftime("out/%Y/%m/%d")

        if not os.path.exists(file_path):
            os.makedirs(file_path, exist_ok=True)
            print("created {}".format(file_path))

        suffix = now.strftime("%Y%m%d.pb2")
        filename = "{}/{}_{}".format(file_path, method.routing_key, suffix)
        with open(filename, 'ab') as f:
            f.write(struct.pack("<I", len(body)))
            f.write(body)
            self.queue.put(filename)
