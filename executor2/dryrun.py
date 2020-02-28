#!/usr/bin/env python
from job_registry import base
import sys
import os
import time
import traceback
import importlib
import signal

filename = sys.argv[1]

mod = importlib.import_module("job_registry.%s" % filename)
task = mod.Task()

for line in sys.stdin:
	commandstring = line[:-1]
	print (task.run(commandstring))
