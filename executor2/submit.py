#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import tqdm

con = Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0"))

taskname = sys.argv[1]
arguments = sys.argv[2]
resultfile = sys.argv[3]

def enqueue(taskname, commandstring):
	result = q.enqueue(base.work, args=(taskname, commandstring), timeout=5*60, result_ttl=365*24*60*60, description="auto")
	return "JOB: %s" % result.id

# read commands
results = []
with open(arguments) as fh:
	lines = fh.readlines()

# push to redis
pipe = redis.pipeline()
bulksize = 0
for line in tqdm.tqdm(lines):
	line = line.rstrip()
	jobid = str(uuid.uuid4())
	results.append("JOB: " + jobid)
	
	pipe.hmset('job:' + jobid, {'fname': taskname, 'arg': line})
	pipe.lpush('queue', jobid)
	bulksize += 1
	if bulksize == 1000:
		pipe.execute()
		pipe = redis.pipeline()
pipe.execute()

# write ids
with open(resultfile, 'w') as fh:
	fh.write('\n'.join(results))
