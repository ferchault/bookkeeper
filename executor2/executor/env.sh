#!/bin/bash
conda create -n redis-worker python=3.8
conda install numpy scipy pandas
conda install -c conda-forge rdkit
conda install openbabel -c conda-forge
pip install quadpy lz4
