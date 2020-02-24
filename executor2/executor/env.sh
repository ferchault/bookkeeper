#!/bin/bash
conda create -n redis-worker python=3.8
conda install rq redis
conda install numpy scipy pandas
