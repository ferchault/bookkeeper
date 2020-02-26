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

	if hostname == "alchemy":
		return "/dev/shm"
	raise NotImplementedError()

def get_hostname():
	hostname = socket.gethostname()
	if hostname == "bismuth":
		return hostname

	if hostname == "alchemy" or len(hostname) < 3:
		return "alchemy"

	raise NotImplementedError()

class Task():
	def __init__(self):
		# setup code here
		pass
	
	def run(self, commandstring):
		return str(len(commandstring))
