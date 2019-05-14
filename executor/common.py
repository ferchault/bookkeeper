#!/usr/bin/env python
import sys, socket, tarfile, io, os, subprocess, shutil, hashlib
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

def get_job_id(queue, hostname, directory, script):
    m = hashlib.sha256()
    m.update('%s-%s-%s-%s' % (queue, hostname, directory, script).encode('utf-8'))
    return m.hexdigest()

def run_in_memory(hostname, directory, script, targzfile):
    file_in = io.BytesIO(targzfile)
    tar = tarfile.open(mode="r:gz", fileobj=file_in)
    tar.extractall('.')

    with open('run/run.sh', 'w') as fh:
        fh.write(script)
    
    subprocess.run('./run.sh > run.log', shell=True, cwd='run')

    tarfile = get_tarfile('run')

    shutil.rmtree('run')

    return tarfile
