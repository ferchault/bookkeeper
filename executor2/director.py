#!/usr/bin/env python
from redis import Redis
import time
import os
import sys

def get_redis_capacity(redis_cpu_load, submitted_count_this_hour, total_queueing, total_running):
	""" If negative, signals failure, requires halting."""
	max_cpu = 0.8 					# accpeptable redis cpu load
	max_per_hour = 2000 			# largest number of jobs started per hour
	min_cores = 100					# smallest work force
	accepted_failure_count = 100	# in last hour

	# redis load too high, back off
	if redis_cpu_load > max_cpu:
		return 0

	# jobs burning through, probably misconfiguration
	if submitted_count_this_hour > max_per_hour:
		return -1

	# too many failures, probably bug in worker code
	#if failure_count > accepted_failure_count:
	#	return -2

	# ramp up with some cores
	if total_running + total_queueing < min_cores:
		return min_cores - total_queueing - total_running

	# default case: business as usual
	load_per_core = (redis_cpu_load / total_running)
	max_jobs = max_cpu / load_per_core
	top_up = max(0, max_jobs - total_running - total_queueing)
	return int(top_up)

def get_cpu_load(redis):
	info = redis.info()
	DURATION = 5
	time.sleep(DURATION)
	info2 = redis.info()
	cpu = (info2['used_cpu_sys'] + info2['used_cpu_user'] - info['used_cpu_sys'] - info['used_cpu_user'])/DURATION
	return cpu

def get_submitted_this_hour(redis):
	keyname = "meta:submitted:%d" % (int(time.time()) // 3600)
	return redis.llen(keyname)

def _sum_key(redis, keyname):
	found = redis.hgetall(keyname)
	queueing = 0
	for k, v in found.items():
		queueing += int(v.decode("ascii"))
	return queueing

def get_queueing(redis):
	keyname = "meta:queued"
	return _sum_key(redis, keyname)

def get_running(redis):
	keyname = "meta:running"
	return _sum_key(redis, keyname)

def register_capacity(redis, capacity):
	keyname = "meta:capacity"
	redis.delete(keyname)
	for i in range(capacity):
		redis.lpush(keyname, "work")
	redis.expire(keyname, 60*10)

if __name__ == "__main__":
	constr = os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0")

	# change db to 0
	parts = constr.split("/")
	parts[-1] = "0"
	constr = '/'.join(parts)

	redis = Redis.from_url("redis://" + constr)

	# check operational
	if redis.get("meta:operational").decode("ascii") != "yes":
		sys.exit(0)

	redis_cpu_load = get_cpu_load(redis)
	submitted_count_this_hour = get_submitted_this_hour(redis)
	total_queueing = get_queueing(redis)
	total_running = get_running(redis)

	capacity = get_redis_capacity(redis_cpu_load, submitted_count_this_hour, total_queueing, total_running)
	if capacity < 0:
		redis.set("meta:operational", "no".encode("ascii"))

	register_capacity(redis, capacity)
