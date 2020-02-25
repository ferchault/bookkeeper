#!/usr/bin/env python
from redis import Redis
from rq import Queue
from rq.job import Job

redis = Redis()
q = Queue(connection=redis)

from job_registry import base
import sys

jobid = sys.argv[1]

def read_result(jobid):
	try:
		job = Job.fetch(jobid, connection=redis)
	except:
		print ("JOB:", jobid, "ERRORNoSuchJob")
		return

	if job.get_status() == "finished":
		print (job.result)
		job.delete()
	else:
		print ("JOB:", jobid, "WARNING%s" % job.get_status())

if jobid == "-":
	for line in sys.stdin:
		if line.startswith("JOB: "):
			jobid = line.strip().split()[1]
			read_result(jobid)
		else:
			print (line[:-1])
else:
	read_result(jobid)
