#!/usr/bin/env python
from redis import Redis
import os
import tqdm

redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))

from job_registry import base
import sys
import lz4.frame as lz4

jobid = f"job:{sys.argv[1]}"

known = redis.hgetall(jobid)
if known is None:
    print ("Unknown job")
    sys.exit(1)

if b'error' in known:
    commandstring = lz4.decompress(known[b'arg']).decode("ascii")
    print (f"Task: {known[b'fname'].decode('ascii')}('{commandstring}')")
    print ("\nFAILED:\n" + known[b'error'].decode('ascii')) 
