#!/bin/bash

FILTER=$1

# Examples
# cat points.json | ./latseq_filter.sh "select(.[][\"dir\"][] == 1)" | ./latseq_stats.py -

usage(){
    echo "Filter tool for LatSeq analysis module"
    echo -e "$1 should be a jq argument or a file with jq arguments"
    exit
}

if [ $# -eq 0 ]; then usage; fi

# check if it is a file
if [ -f "$FILTER" ]; then
    # TODO: test for multiple lines
    # tr "\n" " " < infile
    FILTER=$(tr "\n" " " < $FILTER)
fi

while read line
do
  echo $line | jq -c "$FILTER"  # -c for ouput in one line. important for latseq_stats
done < "${2:-/dev/stdin}"