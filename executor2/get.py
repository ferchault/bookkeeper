#!/usr/bin/env python
from redis import Redis
from rq import Queue
from rq.job import Job

redis = Redis()
q = Queue(connection=redis)

from job_registry import base
import sys

jobid = sys.argv[1]
try:
	job = Job.fetch(jobid, connection=redis)
except:
	print ("NoSuchJob")
	sys.exit(2)

if job.get_status() == "finished":
	print (job.result)
	job.delete()
else:
	print (job.get_status())
	sys.exit(1)
