#!/usr/bin/env python
from redis import Redis
from rq import Queue
from rq.job import Job
import os
import tqdm

redis = Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0"))
q = Queue(connection=redis)

from job_registry import base
import sys

current_resultfile = sys.argv[1]

def read_result(jobid):
	try:
		job = Job.fetch(jobid, connection=redis)
	except:
		return "JOB: %s ERRORNoSuchJob" % jobid

	if job.get_status() == "finished":
		result = job.result
		job.delete()
		return result
	else:
		return "JOB: %s WARNING%s" % (jobid, job.get_status())

with open(current_resultfile) as fh:
	lines = fh.readlines()

results = []
for line in tqdm.tqdm(lines):
	line = line[:-1]
	if line.startswith("JOB: "):
		jobid = line.strip().split()[1]
		results.append(read_result(jobid))
	else:
		results.append(line)

with open(current_resultfile, "w") as fh:
	fh.write('\n'.join(results) + "\n")
