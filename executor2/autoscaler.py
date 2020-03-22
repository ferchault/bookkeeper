#!/usr/bin/env python
from job_registry import base
import getpass
from redis import Redis
import os
import subprocess
import time
import sys

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

tmpfile = "/tmp/%s.autoscaler-tmp" % username

if hostname == "scicore":
	qoss = ['30min', '6hours']
	times = ['00:30:00', '06:00:00']
else:
	qoss = ['noqos']
	times = ['notime']

for qos, stime in zip(qoss, times):
	args = ["squeue", "-u", username, "-r", "-h", "-n", "executor", "-O", "state"]
	if qos != 'noqos':
		args += ["-q", qos]
	with open(tmpfile, "w") as fh:
		subprocess.run(args, stdout=fh, stderr=fh)

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
		if qos == 'noqos':
			args = ["sbatch", "runners/%s.job" % hostname]
		else:
			args = ["sbatch", "--qos", qos, "--time", stime, "runners/%s.job" % hostname]
		subprocess.run(args)
		added += 1

	keyname = "%s-%s-%s" % (hostname, username, qos)
	redis.hset("meta:queued", keyname, pending + added)
	redis.hset("meta:running", keyname, running)
