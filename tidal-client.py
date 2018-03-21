#!/usr/bin/env python

from src.client import Client
from src.config import *
import sys

if "--host" in sys.argv:
    host = sys.argv[ sys.argv.index("--host") + 1 ]
else:
    host = "192.168.0.100"

lang = TIDAL
port = "57890"
logging = False
name = "dd"

try:
    myClient = Client(host, port, name, lang, logging, False, False)
except Exception as e:
    print("Error:\n{}\n".format(e))
