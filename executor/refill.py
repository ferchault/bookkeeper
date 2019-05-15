#!/usr/bin/env python
""" Decides whether the queue needs more workers. Tells via exit code.

Usage: refill.py long/short
"""

import sys, socket, tarfile, io, os, subprocess
import redis, rq

from common import *

if __name__ == '__main__':
    # check args
    if len(sys.argv) != 2:
        raise ValueError('Wrong arguments.')
    queuekind = sys.argv[1]
    if queuekind not in 'short long'.split():
        raise ValueError('Unknown queue.')
    
    # connect
    con = get_connection()

    # decide
    numjobs = get_queue_count(queuekind, con)
    numworkers = get_worker_count(queuekind, con)

    refill = False
    if queue == 'long':
        # every job should be run separately
        if numjobs > numworkers:
            refill = True
    if queue == 'short':
        # jobs can be combined, estimate 5min per job, 2h per worker
        expected_current_load = numworkers * 60 / 5
        if numjobs > expected_current_load:
            refill = True
    
    sys.exit(refill)