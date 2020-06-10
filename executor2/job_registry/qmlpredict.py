import qml
import numpy as np
import os
from redis import Redis
import json
import gzip

# redis = Redis.from_url("redis://" + os.environ.get("EXECUTOR_CONSTR", "127.0.0.1:6379/0"))


class MockXYZ(object):
    def __init__(self, lines):
        self._lines = lines

    def readlines(self):
        return self._lines


class Task:
    def _upload(self):
        cutoff = 9000
        basename = "/mnt/c/Users/guido/data/tmp-enrico/"
        included = open(basename + "production/index_nonegative_new.dat").readlines()[
            :cutoff
        ]
        # lines = []
        # import tqdm
        # for geo in tqdm.tqdm(included):
        # 	geo = geo.strip().rjust(5, '0')
        # 	filename = f'{basename}random/random-{geo}.xyz'
        # 	lines += [_.strip() for _ in open(filename).readlines()]

        # self.connection.set("qml-structures", gzip.compress(('\n'.join(lines)).encode('ascii')))
        self.connection.set(
            "qml-alphas1",
            gzip.compress(
                open(f"{basename}production/alphaS1_osc_0.128_7.dat")
                .read()
                .encode("ascii")
            ),
        )
        self.connection.set(
            "qml-alphas2",
            gzip.compress(
                open(f"{basename}production/alphaS2_osc_0.128_7.dat")
                .read()
                .encode("ascii")
            ),
        )
        self.connection.set(
            "qml-alphas3",
            gzip.compress(
                open(f"{basename}production/alphaS3_osc_0.128_7.dat")
                .read()
                .encode("ascii")
            ),
        )

    def __init__(self, connection):
        self.connection = connection
        # self._upload()
        # return "uploaded"

        lines = (
            gzip.decompress(self.connection.get("qml-structures"))
            .decode("ascii")
            .split("\n")
        )
        q = (
            gzip.decompress(self.connection.get("qml-alphas1"))
            .decode("ascii")
            .strip()
            .split("\n")
        )
        alphas1 = np.array([float(_) for _ in q])
        q = (
            gzip.decompress(self.connection.get("qml-alphas2"))
            .decode("ascii")
            .strip()
            .split("\n")
        )
        alphas2 = np.array([float(_) for _ in q])
        q = (
            gzip.decompress(self.connection.get("qml-alphas3"))
            .decode("ascii")
            .strip()
            .split("\n")
        )
        alphas3 = np.array([float(_) for _ in q])

        reps = []
        Qs = []
        for geoidx in range(len(alphas1)):
            c = qml.Compound(xyz=MockXYZ(lines[geoidx * 33 : (geoidx + 1) * 33]))
            reps.append(
                qml.representations.generate_fchl_acsf(
                    c.nuclear_charges,
                    c.coordinates,
                    gradients=False,
                    pad=31,
                    elements=[1, 6, 8],
                )
            )
            Qs.append(c.nuclear_charges)

        self._reps = np.array(reps)
        self._Qs = np.array(Qs)
        self._alphas1 = alphas1
        self._alphas2 = alphas2
        self._alphas3 = alphas3

    def run(self, commandstring):
        if "ERROR" in commandstring:
            return "--"
        content = json.loads(commandstring)
        xyz = MockXYZ(content["neutralgeometry"].split("\n"))
        c = qml.Compound(xyz=xyz)
        rep = qml.representations.generate_fchl_acsf(
            c.nuclear_charges,
            c.coordinates,
            gradients=False,
            pad=31,
            elements=[1, 6, 8],
        )

        K = qml.kernels.get_local_kernel(
            self._reps, np.array([rep]), self._Qs, [c.nuclear_charges], 0.128
        )
        preds1 = np.dot(K, self._alphas1)[0]
        preds2 = np.dot(K, self._alphas2)[0]
        preds3 = np.dot(K, self._alphas3)[0]

        return str(preds1) + "," + str(preds2) + "," + str(preds3)
