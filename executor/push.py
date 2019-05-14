#!/usr/bin/env python
""" Runs a command via a redis cluster in local network. Assumes that all relevant files (and only relevant files) are in the directories given.

Usage: push.py long/short path/to/script.sh path/to/directory-list
"""

import sys, socket, tarfile, io, os, subprocess
import redis, rq

from common import *

if __name__ == '__main__':
    # check args
    if len(sys.argv) != 4:
        raise ValueError('Wrong arguments.')
    queuekind, scriptname, dirlist = sys.argv[1:]
    if queuekind not in 'short long'.split():
        raise ValueError('Unknown queue.')
    script = get_script(scriptname)

    # connect
    con = get_connection()
    q = rq.Queue(queuekind, connection=con)

    # build directory list
    hostname = get_hostname()
    directories = [_.strip() for _ in open(dirlist).readlines()]
    for directory in directories:
        tarfile = get_tarfile(directory)
        q.enqueue(run_in_memory, hostname=hostname, directory=directory, script=script, targzfile=tarfile, result_ttl=365*24*3600, ttl=-1)
