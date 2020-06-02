#!/usr/bin/env python
from redis import Redis
import os
import tqdm

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))

from job_registry import base
import sys

current_resultfile = sys.argv[1]

# read current resultfile
with open(current_resultfile) as fh:
	lines = fh.readlines()

# fetch missing from redis
results = []
jobids = []
for line in tqdm.tqdm(lines):
        line = line.rstrip()
        if line.startswith("JOB: "):
                jobid = line.strip().split()[1]
                jobkey = "job:" + jobid
                if redis.hget(jobkey, "error") is not None:
                    redis.hdel(jobkey, "error")
                    redis.lpush("queue", jobid)
