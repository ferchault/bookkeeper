#!/usr/bin/env python
from redis import Redis
from job_registry import base
import sys
import os
import uuid
import tqdm
import lz4.frame as lz4

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))

taskname = sys.argv[1]
arguments = sys.argv[2]
resultfile = sys.argv[3]

# safety check
if os.path.exists(resultfile):
	raise ValueError("Won't overwrite existing result file.")

# read commands
results = []
with open(arguments) as fh:
	lines = fh.readlines()

# push to redis
pipe = redis.pipeline()
bulksize = 0
totalentries = len(lines)
for lineno in tqdm.tqdm(range(totalentries)):
	line = lines[lineno].rstrip()
	payload = lz4.compress(line.encode("ascii"))
	jobid = str(uuid.uuid4())
	results.append("JOB: " + jobid)

	pipe.hmset("job:" + jobid, {"fname": taskname, "arg": payload})
	pipe.lpush("queue", jobid)
	bulksize += 1
	if bulksize == 1000:
		pipe.execute()
		pipe = redis.pipeline()
		bulksize = 0
	if lineno == totalentries - 1:
		pipe.execute()

# write ids
with open(resultfile, "w") as fh:
	fh.write("\n".join(results))
