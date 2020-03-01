#!/usr/bin/env python
from job_registry import base
import getpass
from redis import Redis
import os
import subprocess

constr = os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0")

# change db to 0
parts = constr.split("/")
parts[-1] = "0"
constr = '/'.join(parts)

redis = Redis.from_url("redis://" + constr)

hostname = base.get_hostname()
username = getpass.getuser()

tmpfile = ".autoscaler-tmp"
with open(tmpfile, "w") as fh:
	subprocess.run(['squeue', '-u', username, '-r', '-h', '-n', 'executor', '-O', 'state'], stdout=fh, stderr=fh)

with open(tmpfile) as fh:
	lines = fh.readlines()

running = len([_ for _ in lines if "RUNNING" in _])
pending = len(lines) - running

keyname = "%s-%s" % (hostname, username)
redis.hset("meta:queued", keyname, pending)
redis.hset("meta:running", keyname, running)
