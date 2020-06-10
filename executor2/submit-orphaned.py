#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import uuid
import tqdm

redis = Redis.from_url(
    "redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0")
)

taskname = sys.argv[1]
arguments = sys.argv[2]
resultfile = sys.argv[3]

# read commands
with open(arguments) as fh:
    lines = fh.readlines()

# read existing output
with open(resultfile) as fh:
    results = fh.readlines()


# push to redis
pipe = redis.pipeline()
bulksize = 0
totalentries = len(lines)
for lineno in tqdm.tqdm(range(totalentries)):
    result = results[lineno].strip()
    if not result.startswith("JOB:"):
        continue
    jobid = result.split()[-1]
    line = lines[lineno].rstrip()
    payload = line
    pipe.hmset("job:" + jobid, {"fname": taskname, "arg": payload})
    pipe.lpush("queue", jobid)
    bulksize += 1
    if bulksize == 1000:
        pipe.execute()
        pipe = redis.pipeline()
        bulksize = 0
pipe.execute()
