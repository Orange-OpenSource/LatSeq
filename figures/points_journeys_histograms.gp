set terminal pngcairo
set output 'points_journeys_histograms.png'

set datafile separator ';'
set key autotitle columnhead

set title "Share of time spent at each point"
set yrange [0:1]
set ylabel "% of total"
set grid y
set ytics 0.05
set border 3
set boxwidth 0.75
set xlabel "Journeys' path names"
set style data histograms
set style histogram columnstacked
# set style fill solid 0.50 border lt -1
set style fill pattern border
set monochrome

plot datafile using 2, '' using 3, '' using 4:key(1)
