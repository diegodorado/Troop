from __future__ import absolute_import

from .interface import *
from .sender import *
from .receiver import *
from .message import *
from .config import *
from .interpreter import *

from time import sleep, time
from getpass import getpass
from hashlib import md5

import sys

class Client:

    version = '0.4'

    def __init__(self, hostname="127.0.0.1", port=57890, name=None, lang=FOXDOT, logging=False, ipv6=False, promptPwd=True):

        self.hostname = str(hostname)
        self.port     = int(port)
        self.name     = str(name if name is not None else hostname)
        self.id       = None

        # Try and connect to server

        try:

            password=''
            if promptPwd:
                password = getpass()

                self.send = Sender().connect(self.hostname, self.port, ipv6, password)

            if not self.send.connected:

                raise ConnectionError("Login attempt failed")

            else:

                self.id = self.send.conn_id

                print("Password accepted")

        except ConnectionError as e:

            sys.exit(e)

        if self.id is None:

            print("No ID number assigned by server")

        # Set up a receiver on the connected socket

        self.recv = Receiver(self.send.conn)
        self.recv.start()

        self.address  = (self.send.hostname, self.send.port)

        # Choose the language to use

        try:

            if lang in langtypes:

                self.lang = langtypes[lang]()

            else:

                self.lang = Interpreter(lang)

        except ExecutableNotFoundError as e:

            print(e)

            self.lang = DummyInterpreter()

        # Set up a user interface

        self.ui = Interface("Troop - {}@{}:{}".format(self.name, self.send.hostname, self.send.port), self.lang, logging)

        # If there was an error connecting then this method  does not create a local marker

        self.ui.createLocalMarker(self.id, self.name)

        # Send information about this client to the server

        self.send( MSG_CONNECT(self.id, self.name, self.send.hostname, self.send.port) )

        # Give the IDE access to push/pull -> their __call__ methods
        # make them act like methods of self.ui
        self.ui.push = self.send
        self.ui.pull = self.recv

        # Give the receiving server a reference to the user-interface
        self.recv.ui = self.ui
        self.send.ui = self.ui

        self.ui.run()

    @staticmethod
    def read_configuration_file(filename):
        conf = {}
        with open(filename) as f:
            for line in f.readlines():
                try:
                    line = line.strip().split("=")
                    conf[line[0]] = line[1]
                except:
                    pass
        return conf['host'], int(conf['port'])
