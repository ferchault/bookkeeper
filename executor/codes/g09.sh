#!/bin/bash
is_alchemy() {
	command -v scontrol >/dev/null 2>&1 || return
	scontrol show config | grep alchemy &> /dev/null
}
is_first_responder(){
	hostname | grep avl03 &> /dev/null
}
g09_alchemy() {
	export GAUSS_EXEDIR="/apps/gaussian/g09_d.01/g09/"
	export PATH="$GAUSS_EXEDIR:$PATH"
	export GAUSS_SCRDIR="$PWD"
	$GAUSS_EXEDIR/g09 run.inp
	$GAUSS_EXEDIR/formchk run.chk
	rm run.chk Gau-*.d2e Gau-*.int Gau-*.skr Gau-*.rwf Gau-*.inp
}
g09_first() {
	export GAUSS_EXEDIR="/home/grudorff/opt/gaussian/bin/"
	export PATH="$GAUSS_EXEDIR:$PATH"
	export GAUSS_SCRDIR="$PWD"
	$GAUSS_EXEDIR/g09 run.inp
	$GAUSS_EXEDIR/formchk run.chk
	rm run.chk Gau-*.d2e Gau-*.int Gau-*.skr Gau-*.rwf Gau-*.inp
}

is_alchemy && g09_alchemy
is_first_responder && g09_first
