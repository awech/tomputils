# -*- coding: utf8 -*-
"""
Receive messages from broker, write to a file, and deliver to server.

Required:
    * AVOBROKER_EXCHANGE=<exchange>
    * AVOBROKER_USER=<user>
    * AVOBROKER_PASS=<pass>
    * AVOBROKER_HOST=<host>
    * WEB_HOST=<host>
    * PRIVATE_KEY=<key in single line>
    * REMOTE_USER=<remote user>
    * WEB_BASE=<base dir>

"""

from multiprocessing import Process, Queue

from tomputils.message.messsagelogger.listener import Listener
from tomputils.message.messsagelogger.shipper import ship

q = Queue()

# start listener
listener = Listener(q)
p = Process(target=listener.listen)
p.start()

# start file mover
p = Process(target=ship, args=(q,))
p.start()
