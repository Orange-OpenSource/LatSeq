set terminal png size 1874,971
set output "downlink_I.png"

datarlc="rlc.txbuf.am.occ.data"
dataharq="mac.harq.down.nack.data"
datatbs="mac.sched.down.tbs.data"
datamcs="mac.sched.down.mcs.data"
datacqi="phy.srs.dcqi.data"

set ytics nomirror
set lmargin 20
set rmargin 20

t0=system(sprintf("awk -F' ' 'FNR == 1 {print $1}' %s", datarlc))
### average curve from https://stackoverflow.com/questions/42855285/plotting-average-curve-for-points-in-gnuplot
# number of points in moving average
n = 500

# initialize the variables
do for [i=1:n] {
    eval(sprintf("back%d=0", i))
}

# build shift function (back_n = back_n-1, ..., back1=x)
shift = "("
do for [i=n:2:-1] {
    shift = sprintf("%sback%d = back%d, ", shift, i, i-1)
}
shift = shift."back1 = x)"
# uncomment the next line for a check
# print shift

# build sum function (back1 + ... + backn)
sum = "(back1"
do for [i=2:n] {
    sum = sprintf("%s+back%d", sum, i)
}
sum = sum.")"
# uncomment the next line for a check
# print sum

# define the functions like in the gnuplot demo
# use macro expansion for turning the strings into real functions
samples(x) = $0 > (n-1) ? n : ($0+1)
avg_n(x) = (shift_n(x), @sum/samples($0))
shift_n(x) = @shift

set multiplot layout 3,1

# TOP PLOT
set bmargin 0
set format x ""
set xtics 0.1
set grid xtics
set key left top
set ylabel "Volume (Bytes)"
set autoscale y
set ytics auto
set grid ytics
set y2label ""
unset y2tics
plot	datarlc using ($1-t0):2 title "RLC buffer occupancy" with steps ls 2 lw 2, \
	datarlc using ($1-t0):2 notitle with fillsteps fs solid 0.4 noborder ls 2, \
	datarlc using ($1-t0):(avg_n($2)) title "moving average (".n.")" with lines lc 'black' lw 2, \
	datatbs using ($1-t0):2 title "Transport block size" with steps ls 1

# MIDDLE PLOT
set tmargin 0
set key left bottom
set ylabel ""
set y2label ""
set yrange [1:29]
set y2range [0:16]
set ytics 1
set y2tics 1
plot	datamcs using ($1-t0):2 axis x1y1 title "MCS (left)" with points ls 3, \
	datamcs using ($1-t0):2 axis x1y1 notitle with steps ls 3, \
	datacqi using ($1-t0):2 axis x1y2 title "CQI (right)" with linespoints ls 4

# BOTTOM PLOT
set bmargin
set key left top
set xtics rotate by 45 right format "+%.3t"
set ylabel "round number"
set y2label ""
set yrange [-1:5]
set ytics
unset y2tics
plot	dataharq using ($1-t0):2 title "HARQ round (0=ack)" with linespoints ls 5

unset multiplot
