#!/usr/bin/env python
from redis import Redis
import os

redis = Redis.from_url("redis://" + os.environ.get('EXECUTOR_CONSTR', "127.0.0.1:6379/0"))

while not redis.rpoplpush("running", "queue") is None:
	pass