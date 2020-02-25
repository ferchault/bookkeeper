#!/usr/bin/env python
from pkg_resources import load_entry_point
import sys
import pickle
pickle.HIGHEST_PROTOCOL = 2
load_entry_point('rq', 'console_scripts', 'rq')()
