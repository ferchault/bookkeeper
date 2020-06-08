#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import time
import string
import traceback
import random
import importlib
import signal
import getpass
import lz4.frame as lz4

redis = Redis.from_url(
    "redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0")
)


class Guard:
    def __init__(self):
        self.stopped = False

    def handler(self, signal, frame):
        self.stopped = True


guard = Guard()
signal.signal(signal.SIGINT, guard.handler)
signal.signal(signal.SIGTERM, guard.handler)

cache = {}

# identify client to server based on host
randomid = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
)
myhost = base.get_hostname()
redis.client_setname(myhost + ":" + randomid)

while not guard.stopped:
    bytecost = 0
    starttime = time.time()
    # fetch
    jobid = redis.rpoplpush("queue", "running")
    if jobid is None:
        break
    bytecost += 20 + len(jobid)
    jobid = jobid.decode("utf-8")
    try:
        payload, filename = redis.hmget("job:" + jobid, "arg", "fname")
        bytecost += len(payload) + len(filename) + 20
        filename = filename.decode("utf-8")
    except:
        # No valid job decription available anymore
        redis.lrem("running", 1, jobid)
        bytecost += 20 + len(jobid)
        continue

    # execute
    errored = False
    try:
        if filename not in cache:
            mod = importlib.import_module("job_registry.%s" % filename)
            cache[filename] = mod.Task(redis)
        task = cache[filename]
        commandstring = lz4.decompress(payload).decode("ascii")
        result, trafficcost = task.run(commandstring)
        bytecost += trafficcost
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
        bytecost += len(prefix) * 4 + 20 + 5 + 10 + 10

    pipe.lpush(prefix + ":duration", duration)
    bytecost += len(prefix) + 10 + 10
    if errored:
        pipe.incr(prefix + ":failed")
        pipe.lpush("%s:failed" % filename, jobid)
        bytecost += len(prefix) + 20 + len(filename) + len(jobid)
    else:
        pipe.hdel("job:" + jobid, "arg")
        bytecost += len(jobid) + 5

    pipe.hset("job:" + jobid, retkey, retcontent)
    pipe.lrem("running", 1, jobid)
    bytecost += 20 + 2*len(jobid) + len(retkey) + len(retcontent)
    bytecost += 20

    pipe.incrbyfloat("traffic:" + myhost, float(bytecost))
    pipe.execute()
