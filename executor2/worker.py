#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import time
import traceback
import importlib
import signal
import getpass
import lz4.frame as lz4

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))


class Guard:
	def __init__(self):
		self.stopped = False

	def handler(self, signal, frame):
		self.stopped = True


guard = Guard()
signal.signal(signal.SIGINT, guard.handler)
signal.signal(signal.SIGTERM, guard.handler)

cache = {}

while not guard.stopped:
	starttime = time.time()
	# fetch
	jobid = redis.rpoplpush("queue", "running")
	if jobid is None:
		break
	jobid = jobid.decode("utf-8")
	try:
		payload, filename = redis.hmget("job:" + jobid, "arg", "fname")
		filename = filename.decode("utf-8")
	except:
		# No valid job decription available anymore
		redis.lrem("running", 1, jobid)
		continue

	# execute
	errored = False
	try:
		if filename not in cache:
			mod = importlib.import_module("job_registry.%s" % filename)
			cache[filename] = mod.Task(redis)
		task = cache[filename]
		commandstring = lz4.decompress(payload).decode("ascii")
		result = task.run(commandstring)
		retkey = "result"
		retcontent = result
	except:
		errored = True
		what = getpass.getuser() + str(sys.path)
		what += traceback.format_exc()
		retkey = "error"
		retcontent = what

	duration = time.time() - starttime
	# stats, expire 1min
	prefix = "stats:" + filename
	pipe = redis.pipeline()
	if not redis.exists(prefix):
		pipe.hset(prefix, "init", "yes")
		pipe.expire(prefix, 60)
		pipe.delete(prefix + ":duration")
		pipe.delete(prefix + ":failed")

	pipe.lpush(prefix + ":duration", duration)
	if errored:
		pipe.incr(prefix + ":failed")
		pipe.lpush("%s:failed" % filename, jobid)
	else:
		pipe.hdel("job:" + jobid, "arg")

	pipe.hset("job:" + jobid, retkey, retcontent)
	pipe.lrem("running", 1, jobid)

	pipe.execute()
