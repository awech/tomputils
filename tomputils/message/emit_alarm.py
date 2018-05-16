#!/usr/bin/env python

from alarm_pb2 import Alarm
import pika
import os

exchange = os.environ['AVOBROKER_EXCHANGE']
mycred = pika.credentials.PlainCredentials(os.environ['AVOBROKER_USER'],
                                           os.environ['AVOBROKER_PASS'])

connection = pika.BlockingConnection(pika.ConnectionParameters(
    host=os.environ['AVOBROKER_HOST'], credentials=mycred))
channel = connection.channel()
channel.exchange_declare(exchange=exchange, exchange_type='topic')
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange=exchange, queue=queue_name, routing_key="#")

# with open("rabbit-logo_dfefmx.jpg", "rb") as image_file:
# encoded_string = base64.b64encode(image_file.read())
encoded_string = "test"

alarm = Alarm()
alarm.name = "Tomp test alarm"
alarm.type = "TompAirwave"
alarm.state = Alarm.OK
alarm.region = "none"
alarm.message = "Test message 1\nline2\nline3"

routing_key = "TomAirwave.MtLocal.triggered"
channel.basic_publish(exchange='alarms',
                      routing_key=routing_key,
                      body=alarm.SerializeToString())
print(" [x] Sent %r" % alarm)
alarm.message = "Test message 1\nline2\nline3"

routing_key = "TomAirwave.MtLocal.triggered"
channel.basic_publish(exchange='alarms',
                      routing_key=routing_key,
                      body=alarm.SerializeToString())
print(" [x] Sent %r" % alarm)
alarm.message = "Test message 2\nline2\nline3"

routing_key = "TomAirwave.MtLocal.triggered"
channel.basic_publish(exchange='alarms',
                      routing_key=routing_key,
                      body=alarm.SerializeToString())
print(" [x] Sent %r" % alarm)
alarm.message = "Test message 3\nline2\nline3"

routing_key = "TomAirwave.MtLocal.triggered"
channel.basic_publish(exchange='alarms',
                      routing_key=routing_key,
                      body=alarm.SerializeToString())
print(" [x] Sent %r" % alarm)

connection.close()
