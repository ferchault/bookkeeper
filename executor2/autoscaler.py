#!/usr/bin/env python
from job_registry import base
import getpass
from redis import Redis
import os
import subprocess
import time
import sys

constr = os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0")
CALL_INTERVAL=5*60  # crontab interval in seconds
MAX_KBPS_SCICORE=10*1024/3

# change db to 0
parts = constr.split("/")
parts[-1] = "0"
constr = "/".join(parts)

redis = Redis.from_url("redis://" + constr)
redis4 = Redis.from_url("redis://" + constr[:-1] + "4")

# check operational
if redis.get("meta:operational").decode("ascii") != "yes":
	sys.exit(0)

hostname = base.get_hostname()
username = getpass.getuser()

tmpfile = "/tmp/%s.autoscaler-tmp" % username

if hostname == "scicore":
	qoss = ['30min', '6hours', '1day']
	times = ['00:30:00', '06:00:00', '24:00:00']
else:
	qoss = ['noqos']
	times = ['notime']

# bandwidth limit
local_capacity = 1e4
if hostname == "scicore":
	clients = len(["one" for _ in redis.client_list() if 'scicore' in _['name']])
	total_traffic_bytes = float(redis4.get("traffic:scicore"))
	KBps_per_worker = total_traffic_bytes /clients/1024 / CALL_INTERVAL
	local_capacity = min(local_capacity, int(MAX_KBPS_SCICORE/KBps_per_worker))
	redis4.set("traffic:scicore", 0)
	
	# total enqueued count
	args = ["squeue", "-u", username, "-r", "-h", "-n", "executor", "-O", "state"]
	with open(tmpfile, "w") as fh:
		subprocess.run(args, stdout=fh, stderr=fh)

	with open(tmpfile) as fh:
		lines = fh.readlines()
	total_enqueued = len(lines)
	local_capacity -= total_enqueued

	# edge case
	local_capacity = max(0, local_capacity)

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
	if qos == "noqos":
		max_pending = 100
	free_slots = max(0, max_pending - pending)
	free_slots = max(0, min(free_slots, local_capacity))
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
		local_capacity -= 1

	keyname = "%s-%s-%s" % (hostname, username, qos)
	redis.hset("meta:queued", keyname, pending + added)
	redis.hset("meta:running", keyname, running)
