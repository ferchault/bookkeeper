#!/usr/bin/env python
from redis import Redis
from rq import Queue

q = Queue(connection=Redis())

from job_registry import base
import sys

filename = sys.argv[1]
commandstring = sys.argv[2]

result = q.enqueue(base.work, args=(filename, commandstring), timeout=5*60, result_ttl=365*24*60*60)
print (result.id)
