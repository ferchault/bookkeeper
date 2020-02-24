#!/usr/bin/env python
import importlib

def work(filename, commandstring):
	mod = importlib.import_module("job_registry.%s" % filename)
	task = mod.Task()
	return task.run(commandstring)

class Task():
	def __init__(self):
		# setup code here
		pass
	
	def run(self, commandstring):
		return len(commandstring)
