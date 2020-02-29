#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import time
import traceback
import importlib
import signal
import lz4.frame as lz4

redis = Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0"))

class Guard():
	def __init__(self):
		self.stopped = False
	
	def handler(self, signal, frame):
		self.stopped = True

guard = Guard()
signal.signal(signal.SIGINT, guard.handler)
signal.signal(signal.SIGTERM, guard.handler)

while not guard.stopped:
	starttime = time.time()
	# fetch
	jobid = redis.rpoplpush("queue", "running")
	if jobid is None:
		break
	jobid = jobid.decode("utf-8")
	payload = redis.hget("job:" + jobid, "arg").decode("utf-8")
	filename = redis.hget("job:" + jobid, "fname").decode("utf-8")

	# execute
	errored = False
	try:
		mod = importlib.import_module("job_registry.%s" % filename)
		task = mod.Task()
		commandstring = lz4.decompress(payload).decode("ascii")
		result = task.run(commandstring)
		redis.hset("job:%s" % jobid, "result", result)
	except:
		errored = True
		what = traceback.format_exc()
		redis.hset("job:" + jobid, "error", what)
	redis.lrem("running", 1, jobid)
	if errored:
		redis.lpush("%s:failed" % jobid, jobid)

	duration = time.time() - starttime
	# stats, expire 1min
	prefix = 'stats:' + filename
	if not redis.exists(prefix):
		redis.hset(prefix, "init", "yes")
		redis.expire(prefix, 60)
		redis.delete(prefix + ":duration")
		redis.delete(prefix + ":failed")
	redis.lpush(prefix + ":duration", duration)
	if errored:
		redis.incr(prefix + ":failed")
		
