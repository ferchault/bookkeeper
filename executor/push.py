#!/usr/bin/env python
""" Runs a command via a redis cluster in local network. Assumes that all relevant files (and only relevant files) are in the directories given.

Usage: push.py long/short path/to/script.sh path/to/directory-list
"""

import sys, socket, tarfile, io, os, subprocess
import redis, rq

def get_connection():
    connectionstring = open(os.path.expanduser('~/.redis-credentials')).readlines()[0].strip()
    password, rest = connectionstring.split('@')
    hostname, rest = rest.split(':')
    port, db = rest.split('/')
    return redis.Redis(host=hostname, port=int(port), db=1, password=password)

def get_tarfile(dirname):
    file_out = io.BytesIO()
    tar = tarfile.open(mode="w:gz", fileobj=file_out)
    tar.add(dirname, recursive=True, arcname='run')
    tar.close()
    return file_out.getvalue()

def get_script(scriptname):
    return '\n'.join(open(scriptname).readlines())

def get_hostname():
    return socket.gethostname()

def run_in_memory(hostname, directory, script, targzfile):
    file_in = io.BytesIO(targzfile)
    tar = tarfile.open(mode="r:gz", fileobj=file_in)
    tar.extractall('.')

    with open('run/run.sh', 'w') as fh:
        fh.write(script)
    
    subprocess.run('./run.sh > run.log', shell=True, cwd='run')

    tarfile = get_tarfile('run')
    return tarfile

if __name__ == '__main__':
    # check args
    if len(sys.argv) != 4:
        raise ValueError('Wrong arguments.')
    queuekind, scriptname, dirlist = sys.argv[1:]
    if queuekind not in 'short long'.split():
        raise ValueError('Unknown queue.')
    script = get_script()

    # connect
    con = get_connection()
    queue = Queue(queuekind, connection=con)

    # build directory list
    hostname = get_hostname()
    directories = [_.strip() for _ in open(dirlist).readlines()]
    for directory in directories:
        tarfile = get_tarfile(directory)
        q.enqueue(run_in_memory, hostname=hostname, directory=directory, script=script, targzfile=tarfile, result_ttl=365*24*3600, ttl=-1)
