#!/usr/bin/env python
""" Runs a command via a redis cluster in local network. Assumes that all relevant files (and only relevant files) are in the directories given.

Usage: streamline.py long/short path/to/script.sh path/to/directory-list

Directory list contains relative or absolute paths. Lines with # in front are considered to be completed. # will be added upon download of results.

Short queue:
- few minutes runtime

Long queue:
- at most 24 hours runtime
"""

import sys, socket, tarfile, io, os, subprocess
import redis, rq

from common import *

if __name__ == '__main__':
    # check args
    if len(sys.argv) != 4:
        print ('Usage: %s long/short path/to/script.sh path/to/directory-list' % sys.argv[0])
        sys.exit(1)
    queuekind, scriptname, dirlist = sys.argv[1:]
    if queuekind not in 'short long'.split():
        raise ValueError('Unknown queue.')
    script = get_script(scriptname)

    # connect
    con = get_connection()
    q = rq.Queue(queuekind, connection=con)
    
    # get local job list
    directories = [_.strip() for _ in open(dirlist).readlines()]
    stages = {'QUEUED': [], 'COMPLETED': []}
    for directory in directories:
        if directory.startswith('#'):
            stages['COMPLETED'].append(directory[1:].strip())
        else:
            stages['QUEUED'].append(directory.strip())

    # get remote job list
    hostname = get_hostname()
    jobids = {get_job_id(queuekind, hostname, _, script): None for _ in stages['QUEUED']}

    for job in rq.job.Job.fetch_many(jobids.keys(), connection=con):
        if job is None:
            continue
        jobids[job.id] = job.get_status()
    
    # compare
    output = ['# %s' % _ for _ in stages['COMPLETED']]
    for directory in stages['QUEUED']:
        jobid = get_job_id(queuekind, hostname, directory, script)
        status = jobids[jobid]

        # not submitted yet
        if status is None:
            tarfile = get_tarfile(directory)
            q.enqueue(run_in_memory, job_id=jobid, hostname=hostname, directory=directory, script=script, targzfile=tarfile, result_ttl=365*24*3600, ttl=-1)
            output.append(directory)
        
        # has results
        if status == rq.job.JobStatus.FINISHED:
            # download here
            output.append('# %s' % directory)
            raise NotImplementedError()

    # write output
    completed = [_[0] for _ in output if _[0] == '#']
    print ('%d / %d finished' % (len(completed), len(output)))
    with open(dirlist, 'w') as fh:
        fh.write('\n'.join(output))
    
