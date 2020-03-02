#!/usr/bin/env python
from redis import Redis
import os
import tqdm

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))

from job_registry import base
import sys

current_resultfile = sys.argv[1]


def communicate(results, jobids):
	pipe = redis.pipeline()
	for jobid in jobids:
		pipe.hget("job:%s" % jobid, "result")
	downloaded = pipe.execute()

	pipe = redis.pipeline()
	for result, jobid in zip(downloaded, jobids):
		if result is not None:
			pipe.delete("job:%s" % jobid)
			results.append(result)
		else:
			results.append("JOB: " + jobid)
	pipe.execute()

	return results


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
		jobids.append(jobid)
		if len(jobids) > 100:
			results = communicate(results, jobids)
			jobids = []
	else:
		if len(jobids) > 0:
			results = communicate(results, jobids)
			jobids = []
		results.append(line)
results = communicate(results, jobids)

with open(current_resultfile, "w") as fh:
	fh.write("\n".join(results) + "\n")
