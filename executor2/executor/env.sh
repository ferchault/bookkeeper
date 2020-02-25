#!/bin/bash
conda create -n redis-worker python=3.8
pip install rq
conda install numpy scipy pandas
