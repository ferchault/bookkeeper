#!/usr/bin/env python
from redis import Redis
from rq import Queue
from job_registry import base
import sys
import os
import tqdm

q = Queue(connection=Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0")))

taskname = sys.argv[1]
arguments = sys.argv[2]

def enqueue(taskname, commandstring):
	result = q.enqueue(base.work, args=(taskname, commandstring), timeout=5*60, result_ttl=365*24*60*60, description="auto")
	print ("JOB:", result.id)


with open(arguments) as fh:
	lines = fh.readlines()
	for line in tqdm.tqdm(lines):
		line = line[:-1]
		enqueue(taskname, line)
