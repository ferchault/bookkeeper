#!/usr/bin/env python
from redis import Redis
from rq import Queue
from job_registry import base
import sys
import os

q = Queue(connection=Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0")))

filename = sys.argv[1]
commandstring = sys.argv[2]

def enqueue(filename, commandstring):
	result = q.enqueue(base.work, args=(filename, commandstring), timeout=5*60, result_ttl=365*24*60*60)
	print ("JOB:", result.id)

if commandstring == "-":
	for line in sys.stdin:
		line = line[:-1]
		enqueue(filename, line)
else:
	enqueue(filename, commandstring)

