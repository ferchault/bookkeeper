#!/bin/bash
KEEP_PENDING=20

too_few_pending() {
	CURRENT=$(squeue -h -O comment,state | grep -v null | grep short | wc -l)
	DIFF=$(($KEEP_PENDING-CURRENT))
	[ $DIFF -lt 0 ] && DIFF=0

	for i in $(seq 1 $DIFF)
	do
		sbatch alchemy-short.job
	done
}

source /home/vonrudorff/opt/conda/install/bin/activate /home/vonrudorff/REDIS/conda
cd /home/vonrudorff/workcopies/bookkeeper/executor

python refill.py short && too_few_pending short
