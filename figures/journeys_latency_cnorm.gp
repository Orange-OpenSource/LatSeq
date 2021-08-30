set terminal pngcairo
set output 'journeys_latency_cnorm.png'

set datafile separator ';'
set key autotitle columnhead
set xlabel "Latency (ms)" font ",15"
set ylabel "normalized CDF" font ",15"
#set nonlinear x via log10(x) inverse 10**x
set logscale x 10
set ytics scale 0.25
set xtics scale 1.0,0.5 rotate by 45 right font ",15"
set grid xtics ytics lt 8

plot 	dldata using 3:(1.) smooth cnorm with lines linecolor rgb "blue" lw 10, \
	uldata using 3:(1.) smooth cnorm with lines linecolor rgb "orange" lw 10
