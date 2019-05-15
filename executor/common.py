#!/usr/bin/env python
import sys, socket, tarfile, io, os, subprocess, shutil, hashlib, time
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

def run_in_memory(hostname, directory, script, targzfile, deadline):
    file_in = io.BytesIO(targzfile)
    tar = tarfile.open(mode="r:gz", fileobj=file_in)
    tar.extractall('.')

    with open('run/run.sh', 'w') as fh:
        fh.write(script)
    
    # run job safely
    now = time.time()
    timeout = max(10, deadline - now - 120)
    
    try:
        subprocess.run('./run.sh > run.log', shell=True, cwd='run', timeout=timeout)
    except subprocess.TimeoutExpired:
        shutil.rmtree('run')
        raise ValueError('Not enough time.')

    tarfile = get_tarfile('run')

    shutil.rmtree('run')

    return tarfile

def get_queue_length(queuename, connection):
    q = rq.Queue(queuename, connection=connection)
    return q.count

def get_worker_count(queuename, connection):
    workers = rq.Worker.all(connection=connection)
    return len([_ for _ in workers]) if queuename in _.queues])

def get_slurm_deadline():
    """ Returns the linux epoch at which this job will be terminated if run in a slurm environment. None otherwise. """

    def slurm_seconds(duration):
            if '-' in duration:
                    days, rest = duration.split('-')
            else:
                    days = 0
            rest = duration
            try:
                    hours, minutes, seconds = rest.split(':')
            except:
                    hours = 0
                    minutes, seconds = rest.split(':')
            return ((int(days)*24 + int(hours))*60 + int(minutes))*60 + int(seconds)

    cmd = 'squeue -h -j "$SLURM_JOB_ID" -o "%L"'
    try:
            output = subprocess.check_output(cmd, shell=True).decode()
    except:
            return None

    try:
            ret = slurm_seconds(output.strip()) + time.time()
    except:
            return None
    return ret


class DeadlineWorker(rq.worker.Worker):
    def __init__():
        # get deadline
        self._deadline = get_slurm_deadline()

    def execute_job(self, job, queue):
        job.kwargs['deadline'] = self._deadline
        super().work(job, queue)