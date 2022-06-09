set terminal png size 1874,971
set output "uplink_I.png"

datarlc="rlc.rxbuf.am.occ.data"
dataharq="mac.harq.up.nack.data"
databsr="mac.ind.bsr.data"
datasr="mac.ind.sr.data"
datacqi="phy.srs.ucqi.data"

set ytics nomirror
set lmargin 20
set rmargin 20

t0=system(sprintf("awk -F' ' 'FNR == 1 {print $1}' %s", dataharq))
### average curve from https://stackoverflow.com/questions/42855285/plotting-average-curve-for-points-in-gnuplot
# number of points in moving average
n = 50

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

set multiplot layout 4,1

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
plot	datarlc using ($1-t0):2 title "RLC rx buffer occupancy" with steps ls 2 lw 2, \
	datarlc using ($1-t0):2 notitle with fillsteps fs solid 0.4 noborder ls 2, \
	datarlc using ($1-t0):(avg_n($2)) title "average(".n.")" with lines lc 'black' lw 2

# MIDDLE PLOTS UE
set tmargin 0
set key left bottom
set ylabel "BSR index"
set y2label ""
set autoscale y
set y2range [0:2]
set ytics auto
unset y2tics
plot	databsr using ($1-t0):2 axis x1y1 title "UE BSR (left)" with linespoints ls 3, \
	datasr using ($1-t0):2 axis x1y2 notitle with impulse ls 7, \
	datasr using ($1-t0):2 axis x1y2 title "UE SR" with points ls 7 pt 2 

# MIDDLE PLOT
set ylabel "SNR from CQI"
set autoscale y
plot	datacqi using ($1-t0):2 title "Calculated pusch cqi" with lines ls 4

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
