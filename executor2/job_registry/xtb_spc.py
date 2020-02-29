#!/usr/bin/env python
from job_registry import base
import importlib
import uuid
import shutil
import os
import subprocess

class Task():
	def __init__(self):
		self._hostname = base.get_hostname()
		self._scratch = base.get_scratch(self._hostname)
		self._tmpdir = self._scratch + "/" + str(uuid.uuid4())
	
	def run(self, commandstring):
		os.makedirs(self._tmpdir)
		os.chdir(self._tmpdir)

		# write input file
		with open("run.xyz", "w") as fh:
			fh.write(commandstring.replace("###", "\n"))

		# call xtb
		path = {
			"bismuth": "/mnt/c/Users/guido/opt/xtb/6.2.2/bin/xtb",
			"alchemy": "/home/vonrudorff/opt/xtb/xtb_6.2.2/bin/xtb",
			"avl03": "/home/grudorff/opt/xtb/xtb_6.2.2/bin/xtb",
			"scicore": "/scicore/home/lilienfeld/rudorff/opt/xtb/xtb_6.2.2/bin/xtb"
		}[self._hostname]

		with open("run.log", "w") as fh:
			subprocess.run([path, "run.xyz"], stdout=fh, stderr=fh)

		energy = "failed"
		with open("run.log") as fh:
			for line in fh:
				if "  | TOTAL ENERGY  " in line:
					energy = line.strip().split()[-3]

		# cleanup
		os.chdir("..")
		shutil.rmtree(self._tmpdir)

		return energy
