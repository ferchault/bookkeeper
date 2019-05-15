#!/bin/bash
is_alchemy() {
	command -v scontrol >/dev/null 2>&1 || return
	scontrol show config | grep alchemy &> /dev/null
}
g09_alchemy() {
	export GAUSS_EXEDIR="/apps/gaussian/g09_d.01/g09/"
	export PATH="$GAUSS_EXEDIR:$PATH"
	export GAUSS_SCRDIR="$PWD"
	$GAUSS_EXEDIR/g09 run.inp
	$GAUSS_EXEDIR/formchk run.chk
	rm run.chk
	rm Gau-*.d2e
	rm Gau-*.int
	rm Gau-*.skr
	rm Gau-*.rwf
	rm Gau-*.inp
}

is_alchemy && g09_alchemy

