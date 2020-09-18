#!/usr/bin/python3

# Input
# json entry line by line

# Output
# csv line by line. ';' for separation and '\n' for newline

# Assumptions
#  - all the elements have the same keys
#  - all values are converted to string, even the lists

import sys
import json

in_json_l = []

# Read json input line by line
for l in sys.stdin.readlines():
    # filter
    if l.startswith('#') or l.startswith('['):
        continue
    in_json_l.append(json.loads(l))

# Get first json input to list columns
columns = list(in_json_l[0].keys())
# output CSV string could be large, then we write into stdin line by line
sys.stdout.write(";".join(columns) + ';\n')

# For all lines
for e in in_json_l:
    tmp_o = ""
    for c in columns:
        if c not in e:
            tmp_o += ";"
        elif isinstance(e[c], list):
            tmp_o += "["
            for r in e[c]:
                tmp_o += f"{r},"
            tmp_o += "];"
        elif isinstance(e[c], dict):
            tmp_o += "["
            for k in e[c]:
                tmp_o += f"{k}{e[c][k]},"
            tmp_o += "];"
        else:
            tmp_o += f"{e[c]};"
    tmp_o += "\n"
    sys.stdout.write(tmp_o)
