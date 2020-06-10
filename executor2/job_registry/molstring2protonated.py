#!/usr/bin/env python
from job_registry import base
import importlib
import uuid
import shutil
import os
import quadpy
import json
import subprocess
import numpy as np
from openbabel import openbabel


class Task:
    def __init__(self, connection):
        self._hostname = base.get_hostname()
        self._scratch = base.get_scratch(self._hostname)
        self._tmpdir = self._scratch + "/" + str(uuid.uuid4())

        self._xtbpath = {
            "bismuth": "/mnt/c/Users/guido/opt/xtb/6.2.2/bin/xtb",
            "alchemy": "/home/vonrudorff/opt/xtb/xtb_6.2.2/bin/xtb",
            "avl03": "/home/grudorff/opt/xtb/xtb_6.2.2/bin/xtb",
            "scicore": "/scicore/home/lilienfeld/rudorff/opt/xtb/xtb_6.2.2/bin/xtb",
        }[self._hostname]
        # grid
        scheme = quadpy.sphere.lebedev_031()
        self._OHgrid = scheme.points.copy() * 0.97
        self._CHgrid = scheme.points.copy() * 1.09

        self._environments = []
        number_neighbors = (
            7
        )  # self + six neighbors (in 3d, the highest coordination with octahedral symmetry)
        for point in range(len(scheme.points)):
            self._environments.append(
                (
                    [
                        _
                        for _ in np.argpartition(
                            np.linalg.norm(
                                scheme.points[point] - scheme.points, axis=1
                            ),
                            number_neighbors,
                        )[:number_neighbors]
                        if _ != point
                    ]
                )
            )

    def line2molbabel(self, line):
        mol = openbabel.OBMol()
        elements = [8] * 7 + [6] * 12 + [1] * 12
        for element in elements:
            a = mol.NewAtom()
            a.SetAtomicNum(element)

        bonds = line.strip().split()[1:]
        for bond in bonds:
            parts = bond.split("-")
            a, b = int(parts[0]), int(parts[1])
            mol.AddBond(a + 1, b + 1, 1)

        builder = openbabel.OBBuilder()
        builder.Build(mol)
        return mol

    def molstring2uff(self, molstring):
        MMFF = openbabel.OBForceField.FindType("UFF")

        conv = openbabel.OBConversion()
        conv.SetInAndOutFormats("pdb", "xyz")
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
        with open("run.log", "w") as fh:
            subprocess.run(
                [self._xtbpath, "run.xyz", "--opt", "--wbo", "-c", str(charge)],
                stdout=fh,
                stderr=fh,
            )

        # read energy
        energy = "failed"
        vertical_energy = None
        with open("run.log") as fh:
            for line in fh:
                if "  | TOTAL ENERGY  " in line:
                    energy = line.strip().split()[-3]
                if vertical_energy is None and " :: total energy " in line:
                    vertical_energy = line.strip().split()[-3]

        # read geometry
        with open("xtbopt.xyz") as fh:
            geometry = fh.read()

        # read bonds
        with open("wbo") as fh:
            lines = fh.readlines()
        bonds = []
        bondorders = []
        for line in lines:
            parts = line.strip().split()
            bondorders.append(float(parts[-1]))
            parts = parts[:2]
            parts = [int(_) - 1 for _ in parts]
            parts = (min(parts), max(parts))
            bonds.append(parts)

        return bondorders, geometry, bonds, energy, vertical_energy

    def checkgraph(self, bonds, molstring):
        actual = []
        for bond in bonds:
            actual.append("-".join([str(_) for _ in bond]))

        expected = molstring.strip().split()[1:]

        return set(actual) == set(expected)

    def cleanup(self):
        os.chdir("..")
        shutil.rmtree(self._tmpdir)

    def xtbespminima(self, geometry):
        # build esp grid for every heavy atom, assumes heavy atoms in the beginning of the geometry
        gridpts = []
        heavy = []
        for line in geometry.split("\n")[2:]:
            parts = line.split()
            if len(parts) == 0:
                continue
            element = parts[0]
            if element == "H":
                continue
            if element not in "O C".split():
                raise NotImplementedError()
            if element == "O":
                grid = self._OHgrid
            else:
                grid = self._CHgrid
            Z = float("0H2345C7O".index(parts[0]))
            heavy.append(Z)
            base = np.array([float(_) for _ in parts[1:]])
            grid = grid.copy() + base
            gridpts.append(grid)
        gridpts = np.vstack(gridpts)

        # write grid
        to_bohr = 1.8897259886
        gridpts *= to_bohr  # convert to bohr
        np.savetxt("esp_coord", gridpts)

        # write geometry
        with open("run.xyz", "w") as fh:
            fh.write(geometry)

        # call xtb
        with open("run.log", "w") as fh:
            subprocess.run([self._xtbpath, "run.xyz", "--esp"], stdout=fh, stderr=fh)

        # read total ESP
        esp = np.loadtxt("xtb_esp.dat")[:, 3]

        # subtract nuclear contributions
        # for line in geometry.split("\n")[2:]:
        # 	parts = line.split()
        # 	if len(parts) == 0:
        # 		continue
        # 	Z = float('0H2345C7O'.index(parts[0]))
        # 	base = np.array([float(_) for _ in parts[1:]]) * to_bohr
        # 	ds = np.linalg.norm(base - gridpts, axis=1)
        # 	ds[ds<1e-5] = 1e-5 # truncate close distances
        # 	esp -= Z / ds

        # find minima
        npts = len(self._CHgrid)
        minima = []
        atoms = []
        esps = []
        for heavyidx, Z in enumerate(heavy):
            chunk_esp = esp[heavyidx * npts : (heavyidx + 1) * npts]
            for grididx in range(npts):
                if chunk_esp[grididx] < min(chunk_esp[self._environments[grididx]]):
                    atoms.append(heavyidx)
                    minima.append(list(gridpts[heavyidx * npts + grididx] / to_bohr))
                    esps.append(chunk_esp[grididx])

        return heavy, atoms, minima, esps

    def add_proton(self, geometry, position):
        geometry = geometry.split("\n")
        newgeo = "%d\n\n" % (int(geometry[0].strip()) + 1)
        newgeo += "\n".join(geometry[2:])
        newgeo += "H %f %f %f" % (position[0], position[1], position[2])
        return newgeo

    def run(self, commandstring):
        try:
            os.makedirs(self._tmpdir)
        except FileExistsError:
            pass
        os.chdir(self._tmpdir)

        geometry = self.molstring2uff(commandstring)

        # neutral opt
        try:
            bondorders, geometry, bonds, final_energy, vertical_energy = self.xtbgeoopt(
                geometry, charge=0
            )
        except FileNotFoundError:
            return "ERROR: unable to optimize in xTB"

        if not self.checkgraph(bonds, commandstring):
            self.cleanup()
            return "ERROR: UFF to xTB did not converge to the same molecule"

        # build output
        data = {}
        # data['elements'] = elements
        # data['esps'] = esps
        # data['protonatedgeos'] = protonated_geos
        # data['atoms'] = atoms
        # data['positions'] = positions
        data["neutralgeometry"] = geometry
        data["energy"] = final_energy
        data["bonds"] = bonds
        data["bondorders"] = bondorders
        # data['vertical_energies'] = verticals
        # data['relaxed_energies'] = relaxed_energies
        data = json.dumps(data)

        self.cleanup()
        return data

        # get esp minima
        Zs, atoms, positions, esps = self.xtbespminima(geometry)

        verticals = []
        elements = []
        protonated_geos = []
        relaxed_energies = []
        for atom, position, esp in zip(atoms, positions, esps):
            elements.append(Zs[atom])

            protonated_geometry = self.add_proton(geometry, position)
            protonated_geometry, bonds, final_energy, vertical_energy = self.xtbgeoopt(
                protonated_geometry, charge=1
            )
            verticals.append(vertical_energy)
            relaxed_energies.append(final_energy)

            if not self.checkgraph(bonds, commandstring + " %d-%d" % (atom, 31)):
                protonated_geos.append("checkgraph failed")
            else:
                protonated_geos.append(protonated_geometry)
