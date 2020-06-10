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

fh_result = open(resultfile)
fh_tasks = open(arguments)

for result, task in tqdm.tqdm(zip(fh_result, fh_tasks)):
    if result.startswith("JOB: "):
        jobid = result.strip().split()[1]
        payload = task
        redis.hmset("job:" + jobid, {"fname": taskname, "arg": payload})
        redis.lpush("queue", jobid)
