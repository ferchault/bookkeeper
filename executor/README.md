## Use

Runs short calculations of a few minutes each in parallel via a redis cache. Steps:

1. Ask for credentials.
2. Install dependencies on own machine (see below).
3. clone this repo
4. Place each calculation with all dependent files in a single directory. Make sure to call the input file run.inp. Gaussian checkpoint files need to be run.chk
5. Create a list of all folders with calculations.
4. In this folder, run streamline.py for the short queue and give the folder list.

## Dependencies
Python 3.5 or newer
pip install -e git+https://github.com/nvie/rq.git@master#egg=rq

