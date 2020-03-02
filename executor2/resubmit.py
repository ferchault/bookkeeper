#!/usr/bin/env python
from redis import Redis
import os
import sys

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))

# parse last seen
tmpfile = sys.argv[1]
try:
	with open(tmpfile) as fh:
		jobids_last_run = [_.strip() for _ in fh.readlines()]
except:
	jobids_last_run = None

# parse available now
jobids_now = []
for job in redis.lrange("running", 0, -1):
	jobid = job.decode("ascii")
	jobids_now.append(jobid)

# resubmit stale at the _end_ of the queue to give them higher priority
if jobids_last_run is None:
	pipe = redis.pipeline()
	for jobid in set(jobids_last_run) & set(jobids_now):
		pipe.rpush("queue", jobid)
		pipe.lrem("running", 1, jobid)
	pipe.execute()

# write new list
with open(tmpfile) as fh:
	fh.write("\n".join(jobids_now))
