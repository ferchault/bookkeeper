#!/usr/bin/env python
from job_registry import base
import getpass
from redis import Redis
import os
import subprocess
import time

constr = os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0")

# change db to 0
parts = constr.split("/")
parts[-1] = "0"
constr = "/".join(parts)

redis = Redis.from_url("redis://" + constr)

# check operational
if redis.get("meta:operational").decode("ascii") != "yes":
	sys.exit(0)

hostname = base.get_hostname()
username = getpass.getuser()

tmpfile = ".autoscaler-tmp"
with open(tmpfile, "w") as fh:
	subprocess.run(["squeue", "-u", username, "-r", "-h", "-n", "executor", "-O", "state"], stdout=fh, stderr=fh)

with open(tmpfile) as fh:
	lines = fh.readlines()

running = len([_ for _ in lines if "RUNNING" in _])
pending = len(lines) - running

# submit additional jobs
max_pending = 50
free_slots = max(0, max_pending - pending)
keyname = "meta:submitted:%d" % (int(time.time()) // 3600)
added = 0
for i in range(free_slots):
	has_work = redis.rpoplpush("meta:capacity", keyname)
	if has_work is None:
		break
	subprocess.run(["sbatch", "runners/%s.job" % hostname])
	added += 1

keyname = "%s-%s" % (hostname, username)
redis.hset("meta:queued", keyname, pending + added)
redis.hset("meta:running", keyname, running)
