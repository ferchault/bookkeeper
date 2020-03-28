#!/usr/bin/env python
from job_registry import base
import sys
import os
import time
import traceback
import importlib
from redis import Redis
import signal

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))
filename = sys.argv[1]

mod = importlib.import_module("job_registry.%s" % filename)
task = mod.Task(redis)

for line in sys.stdin:
	commandstring = line[:-1]
	print(task.run(commandstring))
