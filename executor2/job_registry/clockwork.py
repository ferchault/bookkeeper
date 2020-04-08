#!/usr/bin/env python
from job_registry import base
import importlib
import uuid
import shutil
import os
import subprocess
import json
import numpy as np
import itertools as it
from rdkit import Chem
from rdkit.Chem import AllChem, ChemicalForceFields

ENERGY_THRESHOLD = 1e-4
ANGLE_DELTA = 1e-7
FF_RELAX_STEPS = 50

class Task():
	def __init__(self, connection):
		self._hostname = base.get_hostname()
		self._scratch = base.get_scratch(self._hostname)
		self._tmpdir = self._scratch + "/" + str(uuid.uuid4())
		self._connection = connection
	
	def _clockwork(self, resolution):
		if resolution == 0:
			start = 0
			step = 360
			n_steps = 1
		else:
			start = 360.0 / 2.0 ** (resolution)
			step = 360.0 / 2.0 ** (resolution-1)
			n_steps = 2 ** (resolution - 1)
		return start, step, n_steps

	def _get_classical_constrained_geometry(self, dihedrals, angles):
		mol = Chem.MolFromMolBlock(self._sdfstr, removeHs=False)

		ffprop = ChemicalForceFields.MMFFGetMoleculeProperties(mol)
		ffc = ChemicalForceFields.MMFFGetMoleculeForceField(mol, ffprop)
		conformer = mol.GetConformer()

		# Set angles and constrains for all torsions
		for dih_id, angle in zip(dihedrals, angles):
			# Set clockwork angle
			try: Chem.rdMolTransforms.SetDihedralDeg(conformer, *self._torsions[dih_id], float(angle))
			except: pass

			# Set forcefield constrain
			ffc.MMFFAddTorsionConstraint(*self._torsions[dih_id], False, angle-ANGLE_DELTA, angle+ANGLE_DELTA, 1.0e10)

		# reduce bad contacts
		try:
			ffc.Minimize(maxIts=FF_RELAX_STEPS, energyTol=1e-2, forceTol=1e-3)
		except RuntimeError:
			pass

		atoms = [atom.GetSymbol() for atom in mol.GetAtoms()]
		coordinates = conformer.GetPositions()

		return f'{len(atoms)}\n\n' + '\n'.join([f'{element} {coords[0]} {coords[1]} {coords[2]}' for element, coords in zip(atoms, coordinates)])

	def _do_workpackage(self, molname, dihedrals, resolution):
		ndih = len(dihedrals)
		start, step, n_steps = self._clockwork(resolution)
		scanangles = np.arange(start, start+step*n_steps, step)

		# fetch input
		self._sdfstr = self._connection.get(f'clockwork:{molname}:sdf').decode("ascii")
		self._torsions = json.loads(self._connection.get(f'clockwork:{molname}:dihedrals').decode("ascii"))

		accepted_geometries = []
		accepted_energies = []
		for angles in it.product(scanangles, repeat=ndih):
			xyzfile = self._get_classical_constrained_geometry(dihedrals, angles)
			#optxyzfile, energy, bonds = get_xtb_geoopt(xyzfile)
			#if set(bonds) != set(refbonds):
			#	continue

			#for i in range(len(accepted_energies)):
			#	if abs(accepted_energies[i] - energy) < ENERGY_THRESHOLD:
			#		# compare geometries optxyzfile vs accepted_geometries
			#else:
			#	accepted_energies.append(energy)
			#	accepted_geometries.append(optxyzfile)
		
		results = {}
		results['mol'] = molname
		results['ndih'] = ndih
		results['res'] = resolution
		results['geometries'] = accepted_geometries
		results['energies'] = accepted_energies
		return results

	def run(self, commandstring):
		# Allow for cached scratchdir
		try:
			os.makedirs(self._tmpdir)
		except FileExistsError:
			pass
		os.chdir(self._tmpdir)

		# parse commandstring
		# molname:dih1-dih2-dih3:4
		parts = commandstring.split(":")
		molname = parts[0]
		dihedrals = [int(_) for _ in parts[1].split("-")]
		resolution = int(parts[2])

		result = self._do_workpackage(molname, dihedrals, resolution)

		# cleanup
		os.chdir("..")
		shutil.rmtree(self._tmpdir)

		return json.dumps(result)