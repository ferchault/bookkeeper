#!/usr/bin/env python
import importlib
import socket

def work(filename, commandstring):
	mod = importlib.import_module("job_registry.%s" % filename)
	task = mod.Task()
	return task.run(commandstring)

def get_scratch(hostname):
	if hostname == "bismuth":
		return "/run/shm/"

	if hostname in ("alchemy", "avl03", "scicore"):
		return "/dev/shm"
	raise NotImplementedError()

def get_hostname():
	hostname = socket.gethostname()
	if hostname in ("bismuth", "avl03"):
		return hostname

	if "alchemy" in hostname:
		return "alchemy"

	if "cluster.bc2" in hostname:
		return "scicore"

	raise NotImplementedError()

class Task():
	def __init__(self):
		# setup code here
		pass
	
	def run(self, commandstring):
		return str(len(commandstring))
