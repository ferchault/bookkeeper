#!/bin/bash
is_alchemy() {
	command -v scontrol >/dev/null 2>&1 || return
	scontrol show config | grep alchemy &> /dev/null
}
g09_alchemy() {
	export GAUSS_EXEDIR="/home/admin/software/gaussian/g09_d.01/g09/"
	export PATH="$GAUSS_EXEDIR:$PATH"
	export GAUSS_SCRDIR="$PWD"
	$GAUSS_EXEDIR/g09 run.inp
	$GAUSS_EXEDIR/formchk run.chk
}

is_alchemy && g09_alchemy

