set terminal pngcairo
set output 'journeys_latency_dots_crop.png'

set datafile separator ';'
set key autotitle columnhead font ",15"
set xlabel "Time (s)" font ",15" 
set ylabel "Latency (ms)" font ",15"
#set xtics 0.25 rotate by 45 right font ",15"
#set xtics time format "%.3tS"
set xtics font ",13"
set ytics 0.5 font ",13"
set xrange [1.98:2.1]
set grid
set arrow from 2.0403,0.0 to 2.0403,4.72 nohead lw 20 lc "#88FF0000"

t0=system(sprintf("awk -F';' 'FNR == 2 {print $2}' %s", dldata))
plot 	dldata using ($2-t0):3 with impulses lw 3 linecolor rgb "blue" notitle, \
	dldata using ($2-t0):3 title "Downlink"  with points linecolor rgb "blue" pointtype 7 ps 2, \
	uldata using ($2-t0):3 with impulses lw 3 linecolor rgb "orange" notitle, \
	uldata using ($2-t0):3 title "Uplink" with points linecolor rgb "orange" pointtype 7 ps 2, \

