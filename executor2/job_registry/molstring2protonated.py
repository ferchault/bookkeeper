#!/usr/bin/env python
from job_registry import base
import importlib
import uuid
import shutil
import os
import json
import subprocess
from openbabel import openbabel

class Task():
	def __init__(self):
		self._hostname = base.get_hostname()
		self._scratch = base.get_scratch(self._hostname)
		self._tmpdir = self._scratch + "/" + str(uuid.uuid4())
	
	def line2molbabel(self, line):
		mol = openbabel.OBMol()
		elements = [8]*7 + [6] * 12 + [1]*12
		for element in elements:
			a = mol.NewAtom()
			a.SetAtomicNum(element)
		    
		bonds = line.strip().split()[1:]
		for bond in bonds:
			parts = bond.split('-')
			a,b = int(parts[0]), int(parts[1])
			mol.AddBond(a+1, b+1, 1)

		builder = openbabel.OBBuilder()
		builder.Build(mol)
		return mol

	def molstring2uff(self, molstring):
		MMFF = openbabel.OBForceField.FindType("UFF")

		conv = openbabel.OBConversion()
		conv.SetInAndOutFormats("pdb","xyz")
		omol = self.line2molbabel(molstring)

		MMFF.Setup(omol)
		MMFF.SteepestDescent(500)
		MMFF.UpdateCoordinates(omol)
		xyzstring = conv.WriteString(omol)
		return xyzstring

	def xtbgeoopt(self, xyzgeometry, charge):
		with open("run.xyz", "w") as fh:
			fh.write(xyzgeometry)

		# call xtb
		path = {
			"bismuth": "/mnt/c/Users/guido/opt/xtb/6.2.2/bin/xtb",
			"alchemy": "/home/vonrudorff/opt/xtb/xtb_6.2.2/bin/xtb",
			"avl03": "/home/grudorff/opt/xtb/xtb_6.2.2/bin/xtb"
		}[self._hostname]

		with open("run.log", "w") as fh:
			subprocess.run([path, "run.xyz", "--opt", "--wbo"], stdout=fh, stderr=fh)

		# read energy
		energy = "failed"
		with open("run.log") as fh:
			for line in fh:
				if "  | TOTAL ENERGY  " in line:
					energy = line.strip().split()[-3]

		# read geometry
		with open("xtbopt.xyz") as fh:
			geometry = fh.read()

		# read bonds
		with open("wbo") as fh:
			lines = fh.readlines()
		bonds = []
		for line in lines:
			parts = line.strip().split()[:2]
			parts = [int(_)-1 for _ in parts]
			parts = (min(parts), max(parts))
			bonds.append(parts)

		return geometry, bonds, energy

	def checkgraph(self, bonds, molstring):
		actual = []
		for bond in bonds:
			actual.append('-'.join([str(_) for _ in bond]))

		expected = molstring.strip().split()[1:]

		return set(actual) == set(expected)

	def cleanup(self):
		os.chdir("..")
		shutil.rmtree(self._tmpdir)

	def run(self, commandstring):
		os.makedirs(self._tmpdir)
		os.chdir(self._tmpdir)

		geometry = self.molstring2uff(commandstring)
		
		# neutral opt
		geometry, bonds, vertical_energy = self.xtbgeoopt(geometry, charge=0)

		if not self.checkgraph(bonds, commandstring):
			self.cleanup()
			return "ERROR: UFF to xTB did not converge to the same molecule"

		# get esp minima
		#atoms, positions, esps = self.xtbespminima(geometry)

		#verticals = []
		#elements = []
		#protonated_geos = []
		#for atom, position, esp in zip(atoms, positions, esps):
		#	elements.append(elementof(atom))

		#	protonated_geometry = self.add_proton(geometry, position)
		#	protonated_geometry, bondorders, vertical_energy = self.xtbgeoopt(geometry, charge=1)
		#	verticals.append(vertical_energy)

		#	if not self.checkgraph(protonated_geometry, bondorders, 1):
		#		continue

		#	protonated_geos.append(protonated_geometry)

		# build output
		data = {}

		#data['verticals'] = verticals
		#data['elements'] = elements
		#data['esps'] = esps
		#data['geos'] = protonated_geos
		data['geo'] = geometry

		data = json.dumps(data)

		self.cleanup()
		return data
