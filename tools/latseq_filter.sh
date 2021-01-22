#!/bin/bash

#################################################################################
# Software Name : LatSeq
# Version: 1.0
# SPDX-FileCopyrightText: Copyright (c) 2020-2021 Orange Labs
# SPDX-License-Identifier: BSD-3-Clause
#
# This software is distributed under the BSD 3-clause,
# the text of which is available at https://opensource.org/licenses/BSD-3-Clause
# or see the "license.txt" file for more details.
#
# Author: Flavien Ronteix--Jacquet
# Software description: LatSeq filter script
#################################################################################


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
