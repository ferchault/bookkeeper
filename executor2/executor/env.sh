#!/bin/bash
conda create -n redis-worker python=3.8
conda install numpy scipy pandas
conda install -c conda-forge rdkit
conda install openbabel -c conda-forge
pip install quadpy lz4 redis networkx
pip install git+https://github.com/qmlcode/qml@18f4e9b4fec38b71c9246fb2735a4821229e37b8 --user -U
# patch "/home/guido/.local/lib/python3.8/site-packages/qml/models/kernelridge.py" to remove ase dependency
# deploy https://raw.githubusercontent.com/ferchault/xyz2mol/master/xyz2mol.py