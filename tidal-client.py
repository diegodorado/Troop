#!/usr/bin/env python

from src.client import Client
from src.config import *
import sys

if "--host" in sys.argv:
    host = sys.argv[ sys.argv.index("--host") + 1 ]
else:
    host = "127.0.0.1"

lang = TIDAL
port = "57890"
logging = False
name = "dd"

myClient = Client(host, port, name, lang, logging, False, False)
