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
# Software description: tests makefile
#################################################################################


TEST_DIR	= $(shell pwd)
OPENAIR_DIR 	= $(TEST_DIR)/../../..
OPENAIR2_COMMON = $(OPENAIR_DIR)/openair2/COMMON
UTILS_DIR 	= $(OPENAIR_DIR)/common/utils
LATSEQ_DIR	= $(UTILS_DIR)/LATSEQ

CC = gcc

#CFLAGS += -m32 -DPHYSIM -DNB_ANTENNAS_RX=2 -DNB_ANTENNAS_TX=2 -I/usr/include/X11
#CFLAGS += -I/usr/include/libxml2 -L/usr/local/lib -I/usr/include/atlas -L/usr/X11R6/lib 
CFLAGS += -std=gnu99 # to be compiled in c99 like all oai
CFLAGS += -Wall -Wconversion
CFLAGS += -g
#CFLAGS += -pg
#CFLAGS += -O3
CFLAGS += -DLATSEQ
#CFLAGS += -DLATSEQ_DEBUG
CFLAGS += -DTEST_LATSEQ
CFLAGS += -I$(OPENAIR_DIR) -I$(OPENAIR2_COMMON) -I$(UTILS_DIR)  -I$(LATSEQ_DIR)

LDLIBS = -lpthread

VPATH += $(LATSEQ_DIR)
VPATH += $(MEAS_DIR)

EXE = test_latseq
SRCS = test_latseq.c latseq.c
OBJS = $(SRCS:.c=.o)

all: $(EXE)

$(EXE): $(OBJS)
	@echo "Compiling test_latseq"
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDLIBS)

run: $(EXE)
	@echo "Run test_latseq"
	./test_latseq a

run-parsing: $(LATSEQ_DIR)/lseq_stats/lseqlogs.py
	cd $(LATSEQ_DIR)/lseq_stats/;\
	      	./lseqlogs.py -l $(TEST_DIR)/test1.lseq

clean:
	rm -f core gmon.out $(EXE) *.o test.*.lseq
