#!/usr/bin/env
""" Checks via comparison of the coulomb matrix representation whether there are sites with an approximately similar local environment in a given molecule."""
import qml
import networkx as nx
import sys
import numpy as np

def find_similar_local_environments(filename, element=6):
    c = qml.Compound(xyz=filename)

    # relevant atoms
    atoms = np.where(c.nuclear_charges == element)[0]
    if len(atoms) < 2:
        return []

    # get coulomb matrix
    a = qml.representations.generate_coulomb_matrix(c.nuclear_charges, c.coordinates, size=c.natoms, sorting='unsorted')
    
    # reconstruct full symmetric matrix
    s = np.zeros((c.natoms, c.natoms))
    s[np.tril_indices(c.natoms)] = a
    d = np.diag(s)
    s += s.T
    s[np.diag_indices(c.natoms)] = d
    
    # find similar sites
    accepted = nx.Graph()
    sorted_elements = [np.sort(_) for _ in s[atoms]]
    for i in range(len(atoms)):
        for j in range(i+1, len(atoms)):
            dist = np.linalg.norm(sorted_elements[i] - sorted_elements[j])
            if dist < 1:
                accepted.add_edge(i, j)
    return [list(_.nodes) for _ in nx.connected_component_subgraphs(accepted)]

if len(sys.argv) != 2:
	print ('Usage: %s filename.xyz' % sys.argv[0])
	exit(2)

for atomset in find_similar_local_environments(sys.argv[1]):
	print (' '.join(map(str, atomset)))
