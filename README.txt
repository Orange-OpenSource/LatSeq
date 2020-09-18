# LATency SEQuence framework is used to extract statistics about internal latency (with jitter,...) in OAI's RAN.

## USAGE

0) Add a new data measure point in the code with
#include "common/utils/LATSEQ/latseq.h"
#if LATSEQ
LATSEQ_P("D pdcp--rlc", "pdcp%d.rlc%d", 0, 1);  
#endif
where first argument is the direction, the second the observed segment and the third argument is a string of data_identifier
1) Compile OAI code with option --enable-latseq (LATSEQ)
2) Run scanario for Uplink and Downlink
3) Process lseq traces to yield data do statistics with LatSeq tools

## LATSEQ MEASUREMENT MODULE

For now, latseq is designed to be the more independant as possible : Means that it does not use oai LOG system (not register by logInit()) and the flag "LATSEQ" disable all lines related to latseq in the code (using #ifdef). In a second time, it could be conceivable to integrate more deeply latseq into oai code.

latseq_t, global structure for latseq embodied the latseq logging info. log_buffer is a circular buffer with 2 head index, i_write_head and i_read_head. this buffer of latseq_element_t is designed to bo mutex-less.

LATSEQ_P macro calls log_measure(). The idea is to have a low-footprint at logging explains why log_measure() should do a minimal amount of operations.

latseq_log_to_file() is the function run in the logger thread. It writes log_elements in the log file.

LATSEQ_P with direction of D (Downlink) or U (Uplink) observed the passage of a data.
LATSEQ_P with direction of I (Information) observed a scalar property at a point of code. e.g. buffer occupancy.

=== Assumptions
- All the point and latseq module run on the same machine (to don't have to synchronize clock of different machines)
- Clock give by asm rdtsc is same for all the CPU cores (constant_tsc)

## TEST_LATSEQ
in targets/TEST/LATSEQ test_latseq test different part of latseq module

## TOOLS
- latseq_checker : verify constitency of Latseq points before compiling
- latseq_logs : convert lseq log file into useful json file for statistics and visualization
- latseq_filter : filter output of latseq_logs
- latseq_stats : perform statistic

=== latseq_checker
Checker to verify that points LATSEQ_P points are consistent.
Verify the number of argument, the emptiness, format...

ex. ./latseq_checker.sh /home/oai/

=== latseq_logs
Proceeds LatSeq logs.
A *.lseq is required.
By default, builds the latseq_log object.
- Reads lseq file given in raw_input
- Cleans raw_input to inputs.
- Builds points structure and paths possible.
- Saves object related to the *.lseq files to a *.plk (pickle)

"-f" specifies we use flask to make http request. Overwise, it is used in CLI.

"-C" cleans pickle file associated to the log file and rebuild

"-i" returns the inputs after filtering and cleaning as a string

"-r" returns the paths present in the log file as json.
```
{
    "D": [
        ["ip", "pdcp.in",...],
        ...
    ],
    "U": ...
}
``̀

"-p" returns points structure as json.
Becareful, if journeys has not been rebuilt, then you do not have "duration" attibute which is used for statistics.
```
{
    "layer1.point": {
        "next": [layer2.point2,...],
        "count": 5,
        "dir": [0],
        "duration": {
            "journeys uid": 0.0115,
            ...
        }
    }
}
{
    ...
}
```

"-j" returns journeys structure as json.
- Rebuilds journeys with rebuild_packets_journey method
- Builds out_journeys
```
{
    "uid": 52,
    "dir": 0,
    "glob": {
        "rnti": "54614",...
    },
    "set": [45,46,47,...],  # set of pointer to input entry
    "set_ids": {
        "drb": "1",...
    },
    "path": 0,  # path according to direction and paths obtainable by -p
    "completed": true,
    "ts_in": 123.456,
    "ts_out": 789.012
}
{
    ...
}
```

"-m" returns metadata of information as list
```
20200423_143226.191801  rlc.am.txbuf    occ1:drb1
20200423_143226.191802  rlc.am.txbuf    occ2:drb1
...
20200423_143226.192000  rlc.um.txbuf    occ15:drb2
```

"-o" returns a latseq journey file line by line. redirects output to a file to have a *.lseqj
```
#funcId ip pdcp.in pdcp.tx rlc.tx.um rlc.seg.um mac.mux mac.txreq phy.out.proc phy.in.proc mac.demux rlc.rx.um rlc.unseg.um pdcp.rx 
20200423_143226.191801 D (len64)        ip--pdcp.in.gtp uid0.rnti54614.drb1.gsn12
20200423_143226.191802 D (len64)        pdcp.in--pdcp.tx        uid0.rnti54614.drb1.gsn12.psn10
20200423_143226.191803 D (len66)        pdcp.tx--rlc.tx.um      uid0.rnti54614.drb1.psn10.lcid3.rsdu0
```

Requested json are printed in stdout line by line
Errors, Warnings, Informations are printed in stderr

Example of usage:
./latseq_logs.py -l ~/latseq.23042020.lseq 2>/dev/null
./latseq_logs.py -j -l ~/latseq.23042020.lseq 2>/dev/null
./latseq_logs.py -p -l ~/latseq.23042020.lseq 2>/dev/null
./latseq_logs.py -o -l ~/latseq.23042020.lseq > 23042020.lseqj 2>/dev/null

=== latseq_filter
Applies a filter to a json stream.
It uses jq.

Takes a file with a filter or a filter as string in argument.

Example of usage:
./latseq_filter.sh journeys_downlinks_gsn.lfilter
cat journeys_downlinks_gsn.lfilter
> select(.["dir"] == 0 and .["set_ids"]["gsn"] == "18")

=== latseq_stats
Performs statistics from json. Report json or print in stdout.

By default, reads on stdin. "-l" *.lseq will try to open a *.json associated.

By default, returns a json report on stdout.
"-f" enables to choose format "json", "csv",...
"-P" prints statistics formated by the latseq_stats module.

"-sj" returns statistics on journeys
`̀``
{
    "D": {
        "size": 34,
        "min": 0.19598,
        "max": 1.187086,
        "mean": 0.788976,
        "stdev": 0.153623,
        "quantiles": [0.694859, 0.699043, 0.834942, 0.838041, 0.955701]
}
`̀``

"-sjpp" returns the shares of delay introduced by each point for each journeys by path.
```
{
  "U02": {  # Uplinks, path 0, point 2
    "size": 4,
    "min": 0,
    "max": 0.7273,
    "mean": 0.36239999999999994,
    "stdev": 0.2915949673776967,
    "quantiles": [
      0.025005000000000003,
      0.125025,
      0.36114999999999997,
      0.598525,
      0.7015449999999999
    ]
  }
}
```

"-sp" returns statistics on points
```
{
    "pdcp.rx": {
        "dir": "U",
        "size": 4,
        "min": 0.01,
        "max": 0.02,
        "mean": 0.015,
        "stdev": 0.005,
        "quantiles": [0.012,...]  # 5%, 25%, 50%, 75%, 95%
    },
    ...
}
`̀``

"-djd" returns data journeys' duration
`̀``
{
    "00": {  # first decimal indicates uplink/downlink followed by the journey unique id
        "ts": 1587645146.191801,
        "durations": 0.19598  # in ms
    },
    ...
}
`̀``

Example of usage of the full toolchain for LatSeq Analysis Module
./latseq_logs.py -l ~/latseq.simple.lseq -j 2>/dev/null | ./latseq_filter.sh journeys_downlinks_gsn.lfilt | ./latseq_stats.py -sj --print

TODO
- do the list of point
- do the list of useful idenfier
- handle the end of local oai thread
