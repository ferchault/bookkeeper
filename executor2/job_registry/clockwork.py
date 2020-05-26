#!/usr/bin/env python
from job_registry import base
import importlib
import uuid
import shutil
import os
import subprocess
import math
import json
import numpy as np
import itertools as it
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, ChemicalForceFields
import qml
from qml.kernels import get_global_kernel
from qml.representations import generate_fchl_acsf
import xyz2mol

# disable low-level logging output
RDLogger.DisableLog('rdApp.*') 

ENERGY_THRESHOLD = 1e-4
ANGLE_DELTA = 1e-7
FF_RELAX_STEPS = 50
QML_FCHL_SIGMA = 2
QML_FCHL_THRESHOLD = 0.98

class Task():
	def __init__(self, connection):
		self._hostname = base.get_hostname()
		self._scratch = base.get_scratch(self._hostname)
		self._tmpdir = self._scratch + "/" + str(uuid.uuid4())
		self._connection = connection
	
		self._xtbpath = {
			"bismuth": "/mnt/c/Users/guido/opt/xtb/6.2.2/bin/xtb",
			"alchemy": "/home/vonrudorff/opt/xtb/xtb_6.2.2/bin/xtb",
			"avl03": "/home/grudorff/opt/xtb/xtb_6.2.2/bin/xtb",
			"scicore": "/scicore/home/lilienfeld/rudorff/opt/xtb/xtb_6.2.2/bin/xtb"
		}[self._hostname]

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

	def _get_smiles(self, xyzgeometry):
		atoms = []
		coords = []
		lines = xyzgeometry.split("\n")
		natoms = int(lines[0])
		for line in lines[2:natoms+2]:
			parts = line.strip().split()
			atoms.append(xyz2mol.int_atom(parts[0]))
			coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
		
		mol = xyz2mol.xyz2mol(atoms, coords, charge=0)

		# canonicalize
		smiles = Chem.MolToSmiles(mol)
		m = Chem.MolFromSmiles(smiles)
		smiles = Chem.MolToSmiles(m)

		return smiles

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

		return f'{len(atoms)}\n\n' + '\n'.join([f'{element} {coords[0]} {coords[1]} {coords[2]}' for element, coords in zip(atoms, coordinates)]), atoms, coordinates

	def _xtbgeoopt(self, xyzgeometry, charge):
		with open("run.xyz", "w") as fh:
			fh.write(xyzgeometry)

		# call xtb
		with open("run.log", "w") as fh:
			subprocess.run([self._xtbpath, "run.xyz", "--opt", "-c", str(charge)], stdout=fh, stderr=fh)

		# read energy
		energy = "failed"
		vertical_energy = None
		with open("run.log") as fh:
			for line in fh:
				if "  | TOTAL ENERGY  " in line:
					energy = line.strip().split()[-3]
				if "convergence criteria cannot be satisfied" in line:
					raise ValueError("unconverged")
				if "SCC did not converge" in line:
					raise ValueError("unconverged")

		if math.isnan(float(energy)) or energy == "failed":
			raise ValueError("nan energy")

		# read geometry
		with open("xtbopt.xyz") as fh:
			geometry = fh.read()

		return geometry, energy

	def _condense_geo(self, instring):
		lines = instring.split("\n")[2:]
		res = []
		for line in lines:
			parts = line.strip().split()
			res.append(" ".join(parts))
		return "\n".join(res).strip()

	def _do_workpackage(self, molname, dihedrals, resolution):
		ndih = len(dihedrals)
		start, step, n_steps = self._clockwork(resolution)
		scanangles = np.arange(start, start+step*n_steps, step)

		# fetch input
		self._sdfstr = self._connection.get(f'clockwork:{molname}:sdf').decode("ascii")
		self._torsions = json.loads(self._connection.get(f'clockwork:{molname}:dihedrals').decode("ascii"))
		self._bonds = set([tuple(_) for _ in json.loads(self._connection.get(f'clockwork:{molname}:bonds').decode("ascii"))])
		self._smiles = self._connection.get(f'clockwork:{molname}:smiles').decode("ascii")

		accepted_geometries = []
		accepted_energies = []
		accepted_bondorders = []
		accepted_reps = []
		for angles in it.product(scanangles, repeat=ndih):
			try:
				xyzfile, atoms, coordinates = self._get_classical_constrained_geometry(dihedrals, angles)
				geometry, energy = self._xtbgeoopt(xyzfile, 0)
			except:
				continue
			try:
				energy = float(energy)
			except ValueError:
				continue

			# require same molecule
			if self._get_smiles(geometry) != self._smiles:
				continue

			# check for similar energies in list
			compare_required = np.where(np.abs(np.array(accepted_energies) - energy) < ENERGY_THRESHOLD)[0]
			charges = [{'H': 1, 'C': 6, 'N': 7, 'O': 8}[_] for _ in atoms]
			rep = generate_fchl_acsf(charges, coordinates, pad=len(atoms))
			include = True
			if len(compare_required) > 0:
				sim = get_global_kernel(np.array([rep]), np.array(accepted_reps)[compare_required], np.array([charges]), np.array([charges]*len(compare_required)), QML_FCHL_SIGMA)
				if np.max(sim) > QML_FCHL_THRESHOLD:
					include = False
			if include:
				accepted_energies.append(energy)
				accepted_geometries.append(self._condense_geo(geometry))
				accepted_reps.append(rep)
		
		results = {}
		results['mol'] = molname
		results['dih'] = dihedrals
		results['res'] = resolution
		results['geo'] = accepted_geometries
		results['ene'] = accepted_energies
		return results

	def run(self, commandstring):
		# Allow for cached scratchdir
		try:
			os.makedirs(self._tmpdir)
		except FileExistsError:
			pass
		os.chdir(self._tmpdir)

		# parse commandstring
		# molname:1-2-3:4
		parts = commandstring.split(":")
		molname = parts[0]
		dihedrals = [int(_) for _ in parts[1].split("-")]
		resolution = int(parts[2])

		result = self._do_workpackage(molname, dihedrals, resolution)

		# cleanup
		os.chdir("..")
		shutil.rmtree(self._tmpdir)

		return json.dumps(result)
