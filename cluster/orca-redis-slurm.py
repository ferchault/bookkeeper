#!/usr/bin/env python
""" Runs an diskless ORCA calculation. Requires the following env to be set:

ORCACMD: the full path to the orca binary
ORCAPROJECT: a unique projectprefix, no space
"""

import time
import subprocess
import shutil
import tarfile
import io
import os
import random
import string
from contextlib import contextmanager

import redis

def get_slurm_deadline():
	""" Returns the linux epoch at which this job will be terminated if run in a slurm environment. None otherwise. """

	def slurm_seconds(duration):
        if '-' in duration:
            days, rest = duration.split('-')
        else:
            days = 0
            rest = duration
        hours, minutes, seconds = rest.split(':')
        return ((int(days)*24 + int(hours))*60 + int(minutes))*60 + int(seconds)

	cmd = 'squeue -h -j $SLURM_JOB_ID -o "%L"'
	try:
		output = subprocess.check_output(cmd, shell=True)
	except:
		return None

	return slurm_seconds(output.strip()) + time.time()


def get_memory_scratch():
	""" Returns largest ramdisk available on this machine to this user."""
	# ugly
	return '/run/user/1022'

@contextmanager
def workdir():
	basedir = get_memory_scratch()

	name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
	path = '%s/orca-%s' % (basedir, name)
	os.mkdir(path)

	try:
		yield path
	finally:
		shutil.rmtree(path)

class RedisCache(object):
	def __init__(self, taskprefix):
		connectionstring = open(os.path.expanduser('~/.redis-credentials')).readlines()[0].strip()
		password, rest = connectionstring.split('@')
		hostname, rest = rest.split(':')
		port, db = rest.split('/')
		self._con = redis.Redis(host=hostname, port=int(port), db=int(db), password=password)
		self._project = os.getenv('ORCAPROJECT')

	def next(self, result):
		if result is not None:
			self._con.RPUSH('%s-results' % self._project, result)

		nexttask = self._con.LPOP('%s-tasks' % self._project)
		if nexttask is None:
			return None
		return nexttask

	def requeue(self, tasktar):
		self._con.LPUSH('%s-tasks' % self._project, tasktar)

	def errored(self, tasktar):
		self._con.LPUSH('%s-errors' % self._project, tasktar)


def run_orca(tasktar, deadline):
	""" Gets a simple tarfile, runs it in memory, returns results as targz file."""
	if deadline is None:
		timeout = None
	else:
		timeout = deadline - time.time() - 120

	with workdir() as path:
		fh = io.BytesIO(tasktar)
		tar = tarfile.open(fileobj=fh)
		tar.extractall(path=path)
		tar.close()

		inputpath = glob.glob('%s/**/run.inp' % path)[0]
		inputpath = inputpath[:-len('/run.inp')]

		try:
			p = subprocess.run('%s run.inp > run.log' % os.getenv('ORCACMD'), shell=True, timeout=timeout, cwd=inputpath)
		except subprocess.TimeoutExpired:
			return None

		fh = io.BytesIO()
		tar = tarfile.open(mode='w:gz', fileobj=fh)
		for fn in glob.glob('%s/*' % path):
			if 'tmp' in fn or 'gbw' in fn:
				continue
			tar.add(fn, recursive=False, arcname=fn[len(path):])
		tar.close()
		return fh.getvalue()

if __name__ == '__main__':
	deadline = get_slurm_deadline()
	cache = RedisCache()
	result = None
	while True:
		tasktar = cache.next(result)

		if tasktar is None:
			break

		haserror = False
		try:
			result = run_orca(tasktar, deadline)
		except:
			haserror = True

		if haserror:
			cache.errored(tasktar)
		else:
			if result is None:
				# timeout hit
				cache.requeue(tasktar)
