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
# Software description: LatSeq checker script
#################################################################################


OAI_PATH=$1
LATSEQ_TOKEN="LATSEQ_P("
LATSEQ_H_INC="#include \"common/utils/LATSEQ/latseq.h\""
NB_TOKEN_BEFORE_VARARGS=2
REPORT_FILE="latseq_checker_report.txt"
nb_errors=0
nb_files=0
nb_points=0


usage() {
    echo "The absolute path to oai should be the last argument"
    echo -e "-h \t : help"
    echo -e "-v \t : to increase verbosity"
    echo -e "-p \t : print internal variables of latseq"
    echo -e "-r \t : output a report of all valid measurement points in OAI code"
    exit
}

# function to get latseq info in sources
get_latseq_info () {
    if [[ ! -z "$VERBOSE" ]] ; then echo "${FUNCNAME[0]}"; fi
    ENTRY_MAX_LEN=$(cat $LATSEQ_PATH/latseq.h | grep MAX_LEN_DATA_ID | tr -s ' ' | cut -d " " -f3)
}

# function to check one line of LATSEQ_P
# $1 : path to a source file
# $2 : line contains LATSEQ_P
check_latseq_p() {
    if [[ ! -z "$VERBOSE" ]] ; then echo "checking line... $1:$2"; fi
    P_ERROR=false
    # check the presence of include latseq 0 if found
    if [ `grep "$LATSEQ_H_INC" $1 >/dev/null; echo $?` -eq 1 ]; then 
        echo -e "\e[31m\e[1m[INCLUDE]\t$1\e[21m :\n\t$LATSEQ_H_INC is missing\e[0m";
        nb_errors=$((nb_errors+1));
        P_ERROR=true
    fi
    # check if LATSEQ_P commented
    if [[ $2 == //* ]]; then
	return
    fi
    # check if LATSEQ_P not empty
    if [[ "$2" != *");" ]]; then 
        echo -e "\e[31m\e[1m[EMPTY]\t\t$1:$2\e[21m :\n\tLATSEQ_P empty or multilined\e[0m";
        nb_errors=$((nb_errors+1));
        P_ERROR=true
        return
    fi
    # check for no-information type
    if grep -voq "I" <<< "$2" ; then
        # check the format properties:globals:locals
        if [ "$(grep -o ":" <<< "$2" | wc -l)" -ne 2 ]; then
            echo -e "\e[31m\e[1m[NB_VAR]\t$1:$2\e[21m :\n\tdata identifer's format should be properties:globals:locals\e[0m";
            nb_errors=$((nb_errors+1));
            P_ERROR=true
        fi
    fi

    # check number of argument
    if grep -voq "I" <<< "$2" ; then
        nbArgsFmt=$(echo $2 | grep -o "%d" | wc -l)
        nbArgsGiven=$((`echo $2 | tr -dc ',' | wc -c` + 1 - NB_TOKEN_BEFORE_VARARGS))
        if [ "$nbArgsFmt" -ne "$nbArgsGiven" ]; then
            echo -e "\e[31m\e[1m[NB_VAR]\t$1:$2\e[21m :\n\tnumber of arguments for format ($nbArgsFmt) and given ($nbArgsGiven) are different\e[0m";
            nb_errors=$((nb_errors+1));
            P_ERROR=true
        fi
    fi
    # check the variable length
    #   get the entry length in sources
    if [[ -z "$ENTRY_MAX_LEN" ]]; then get_latseq_info; fi
    #   compute approximated length
    fmtLen=$(echo $2 | cut -d ',' -f2)
    fmtLen=${#fmtLen}
    computedLen=$((fmtLen + nbArgsFmt*4))
    if [ "$computedLen" -gt $((nbArgsFmt*ENTRY_MAX_LEN)) ]; then
        echo -e "\e[31m\e[1m[DATAID_LEN]\t$1:$2\e[21m :\n\tNot enough space reserved for data id ($computedLen vs $ENTRY_MAX_LEN)\e[0m";
        nb_errors=$((nb_errors+1));
        P_ERROR=true
    fi

    if [ "$P_ERROR" = false ] && [[ ! -z "$REPORT" ]]; then
        print_report "$1" "$2"
    fi
}

# Print internal variables of latseq
print_intvar() {
    echo "${FUNCNAME[0]}"
}

# Output a report on latseq points
# $1 : source file
# $2 : LATSEQ_P point
print_report() {
    echo -e "$1\n\t$2\n" >> $REPORT_FILE
    echo "Writing report to $REPORT_FILE ..." 
}

# function to update header of latseq log file in latseq sources
update_latseq_header() {
    if [[ ! -z "$VERBOSE" ]] ; then echo "${FUNCNAME[0]}"; fi
}

F_OLD=""

if [ $# -eq 0 ]; then usage; fi

case $1 in
    "-v")
        VERBOSE=1
	OAI_PATH=$2;;
    "-p")
        print_intvar
	exit;;
    "-r")
        REPORT=1
        rm -f $REPORT_FILE
	OAI_PATH=$2;;
    "-h")
        usage
        exit;;
esac

# check that OAI_PATH exists
[ ! -d "$OAI_PATH" ] && echo -e "Directory $OAI_PATH DOES NOT exists."

LATSEQ_PATH="$OAI_PATH/common/utils/LATSEQ"

# get all files where are LATSEQ_P
while read F
do
    if [[ "$F" != "$F_OLD" ]]; then 
        if [[ ! -z "$VERBOSE" ]] ; then echo "-----"; fi
        while read L
        do
            check_latseq_p "$F" "$L"
            nb_points=$(($nb_points + 1));
        done <<<$(grep $F -e $LATSEQ_TOKEN)
        nb_files=$(($nb_files + 1));
    fi
    F_OLD=$F
done <<<$(grep --exclude-dir={common,targets} --include=\*.c -rnw $OAI_PATH -e $LATSEQ_TOKEN | cut -d: -f1)
echo "LatSeq checker done."
echo "$nb_files file(s)/ $nb_points point(s) analyzed"
echo "$nb_errors error(s)"
