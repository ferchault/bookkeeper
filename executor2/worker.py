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
	payload, filename = redis.hmget("job:" + jobid, "arg", "fname")
	filename = filename.decode("utf-8")

	# execute
	errored = False
	try:
		mod = importlib.import_module("job_registry.%s" % filename)
		task = mod.Task()
		commandstring = lz4.decompress(payload).decode("ascii")
		result = task.run(commandstring)
		retkey = "result"
		retcontent = result
	except:
		errored = True
		what = traceback.format_exc()
		retkey = "error"
		retcontent = what
		
	duration = time.time() - starttime
	# stats, expire 1min
	prefix = 'stats:' + filename
	pipe = redis.pipeline()
	if not redis.exists(prefix):
		pipe.hset(prefix, "init", "yes")
		pipe.expire(prefix, 60)
		pipe.delete(prefix + ":duration")
		pipe.delete(prefix + ":failed")

	pipe.lpush(prefix + ":duration", duration)
	if errored:
		pipe.incr(prefix + ":failed")
		pipe.lpush("%s:failed" % jobid, jobid)
	else:
		pipe.hdel("job:" + jobid, "arg")
	
	pipe.hset("job:" + jobid, retkey, retcontent)
	pipe.lrem("running", 1, jobid)
		
	pipe.execute()
