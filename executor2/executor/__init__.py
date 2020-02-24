#!/usr/bin/env python

def get_connection():
	""" Parse connection string from env."""
	pass

def run_worker(connection):
	""" Execute worker."""
	pass

def detect_environment():
	""" Returns a string for different environments.

	Possible values:
	- bismuth
	- alchemy
	- scicore"""
	pass

def get_scratch():
	""" Returns a writable directory, preferably in memory."""
	pass
