#!/usr/bin/env python
""" Tests typical compression times and costs. Goal of this compression: reduce network traffic as long as compression can be done in less than 10ms on a single core."""
import lz4.frame as lz4
import gzip
import timeit
import lzma
import bz2

# test cases
testdata = {}
testdata["task"] = "ci2057:63-65-66-68:1"
testdata[
    "result"
] = '{"mol": "ci2057", "dih": [63, 65, 66, 68], "res": 1, "geo": ["O -1.97573692330003 2.35696204733330 3.05329586157309\nC -2.00919859345254 2.66072419260163 1.70881955279989\nC -2.68968735757629 3.87483374429881 1.15013306681344\nC -3.13125779959671 2.50474728473186 0.71422133520601\nC -2.15029017839437 1.99426021202339 -0.33547838742880\nC -0.99593632330516 2.11646018625541 0.68794243258249\nC -0.40718912786970 0.77269361067820 1.10957608658191\nC 0.46812514616137 0.20664541821327 0.03409385358255\nO 0.35541806738911 -0.87887424797399 -0.46009386568263\nH -1.51899266064545 3.05641250236145 3.53587369170495\nH -3.35055613181796 4.38948566877028 1.83245947044282\nH -2.17344746263427 4.52093601782016 0.45441224566931\nH -4.13794129724101 2.14983648674926 0.84840259690839\nH -2.33109516692290 0.96772391531447 -0.64396591889444\nH -2.06107278178081 2.62492393581536 -1.21982473297406\nH -0.19663601508611 2.81364139512941 0.41662952523906\nH 0.20507315574946 0.92144618966517 2.00389721666164\nH -1.20755886402890 0.07289734408777 1.35269656632497\nH 1.26689251283253 0.90297789676672 -0.29487525043171"], "ene": [-28.15059185517]}'


def compress_lz4(s):
    return lz4.compress(s.encode("ascii"))


def compress_gzip(s):
    return gzip.compress(s.encode("ascii"))


def compress_lmza(s):
    return lzma.compress(s.encode("ascii"))


def compress_bz2(s):
    return bz2.compress(s.encode("ascii"))


count = 1000
testfunc = {
    "lz4": compress_lz4,
    "gz": compress_gzip,
    "lzma": compress_lmza,
    "bz2": compress_bz2,
}

for funcname, func in testfunc.items():
    for testname, test in testdata.items():
        duration = (
            timeit.timeit("func(test)", globals=globals(), number=count) / count * 1000
        )
        payload = func(test)
        print(
            f"{testname:<6} {funcname:>4} {duration:5.3} ms for {len(payload) / len(test):5.3} compression ratio"
        )
