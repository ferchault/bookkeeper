#!/bin/bash
is_alchemy() {
	command -v scontrol >/dev/null 2>&1 || return
	scontrol show config | grep alchemy &> /dev/null
}
orca_alchemy() {
	export PATH="/home/vonrudorff/orca/orca_4_0_1_2_linux_x86-64_openmpi202:$PATH"
	/home/vonrudorff/orca/orca_4_0_1_2_linux_x86-64_openmpi202/orca run.inp
}

is_alchemy && orca_alchemy
