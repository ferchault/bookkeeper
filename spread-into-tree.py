#!/usr/bin/env python
""" Converts a list of files into a folder tree to increase access efficiency.

Usage example:
$ python spread-into-tree.py PREFIX <(find . -maxdepth 1 -name "*xyz")

creates a subfolder PREFIX in the current working directory and two nested levels of subdirectories amongst which all files matching *xyz are distributed.

"""

import sys
import hashlib
import os.path
import os

try:
	prefix, filelist = sys.argv[1:]
except:
	print ('Usage: %s FOLDERPREFIX LISTOFFILES' % sys.argv[0])
	exit(2)

created = []
for line in open(filelist):
	fullname = line.strip()
	filename = os.path.basename(fullname)
	digest = hashlib.sha256(filename.encode('utf-8')).hexdigest()
	newpath = '%s/%s/%s' % (prefix, digest[0:2], digest[2:4])
	if newpath not in created:
		try:
			os.makedirs(newpath)
		except FileExistsError:
			pass
		created.append(newpath) 
	os.rename(fullname, os.path.join(newpath, filename))
