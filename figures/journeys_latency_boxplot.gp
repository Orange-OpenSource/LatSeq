set terminal pngcairo
set output 'journeys_latency_boxplot.png'

set datafile separator ';'
set border 2 front lt black linewidth 1.000 dashtype solid
set boxwidth 0.5 absolute
set linetype 1 linecolor rgb "blue"
set linetype 2 linecolor rgb "orange"
set style fill solid 0.50 border lt -1
unset key
set pointsize 0.5
set style data boxplot
set xtics border in scale 0,0 nomirror norotate  autojustify
set xtics norangelimit 
set xtics (sprintf("Downlink %s journeys", system(sprintf("wc -l < %s", dldata))) 1, sprintf("Uplink %s journeys", system(sprintf("wc -l < %s", uldata))) 2)
set ytics 0.5 border in scale 1,0.5 nomirror norotate  autojustify
set yrange [ 0.00000 : 6.000 ] noreverse nowriteback
set ylabel "Latency (ms)"
set grid
set monochrome

plot 	dldata using (1):3,\
	uldata using (2):3
