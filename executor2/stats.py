#!/usr/bin/env python
from redis import Redis
import glob
import os
import json
import time

redis = Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0"))

def get_throughput(source):
	items = redis.llen("stats:%s:duration" % source)
	remaining = int(redis.pttl("stats:" + source))
	elapsed = 60000 - remaining
	return float(elapsed)/1000, items

res = []
for source in glob.glob("job_registry/*.py"):
	source = source.split("/")[1][:-3]
	if source.startswith("__"):
		continue
	
	if redis.exists("stats:" + source):
		elapsed, items = get_throughput(source)
		if elapsed < 10:
			time.sleep(10)
			elapsed, items = get_throughput(source)

		failed = redis.get("stats:%s:failed" % source)
		if failed is None:
			failed = 0
		speed = items/elapsed
	else:
		speed = 0
		failed = 0
	res.append({'source': source, 'throughput': speed, 'failed': failed, 'when': time.time()})
	
print (json.dumps(res))	

