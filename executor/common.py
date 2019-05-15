#!/usr/bin/env python
import sys, socket, tarfile, io, os, subprocess, shutil, hashlib, time
import redis, rq

def get_connection():
    try:
        connectionstring = open(os.path.expanduser('~/.redis-credentials')).readlines()[0].strip()
    except:
        print ('Unable to read credentials ~/.redis-credentials')
        sys.exit(1)
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

def extract_tarfile(location, targzfile, strip=False):
    file_in = io.BytesIO(targzfile)
    tar = tarfile.open(mode="r:gz", fileobj=file_in)
    if strip:
        for member in tar.getmembers():
            if member.name == 'run':
                continue
            outname = member.name[4:]
            if member.isdir():
                os.makedirs(os.path.join(outname, location))
            else:
                contents = tar.extractfile(member)
                with open(os.path.join(location, outname), 'wb') as fh:
                    fh.write(contents.read())
    else:
        tar.extractall(location)

def get_script(scriptname):
    return '\n'.join(open(scriptname).readlines())

def get_hostname():
    return socket.gethostname()

def get_job_id(queue, hostname, directory, script):
    m = hashlib.sha256()
    m.update(('%s-%s-%s-%s' % (queue, hostname, directory, script)).encode('utf-8'))
    return m.hexdigest()

def run_in_memory(hostname, directory, script, targzfile, deadline):
    import tarfile, subprocess, shutil, os
    extract_tarfile('.', targzfile)

    with open('run/run.sh', 'w') as fh:
        fh.write(script)
    
    # run job safely
    now = time.time()
    timeout = max(10, deadline - now - 120)
    
    try:
        with open('run/run.log', 'w') as fh:
            subprocess.run('bash run.sh', shell=True, cwd='run', timeout=timeout, stdout=fh, stderr=fh)
    except subprocess.TimeoutExpired:
        shutil.rmtree('run')
        raise ValueError('Not enough time.')

    os.remove('run/run.sh')
    tarfile = get_tarfile('run')

    shutil.rmtree('run')

    return tarfile

def get_queue_length(queuename, connection):
    q = rq.Queue(queuename, connection=connection)
    return q.count

def get_worker_count(queuename, connection):
    workers = rq.Worker.all(connection=connection)
    return len([_ for _ in workers if queuename in _.queues])

def get_slurm_deadline():
    """ Returns the linux epoch at which this job will be terminated if run in a slurm environment. 24h otherwise"""

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
            return time.time() + 24*60*60

    try:
            ret = slurm_seconds(output.strip()) + time.time()
    except:
            return time.time() + 24*60*60
    return ret


class DeadlineWorker(rq.worker.Worker):
    def __init__(self, *args, **kwargs):
        # get deadline
        self._deadline = get_slurm_deadline()
        super().__init__(*args, **kwargs)

    def execute_job(self, job, queue):
        job.kwargs['deadline'] = self._deadline
        super().execute_job(job, queue)
