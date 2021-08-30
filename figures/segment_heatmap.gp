set terminal pngcairo
set output 'segment_heatmap.png'

set datafile separator ';'
set key autotitle columnhead

set autoscale fix
set palette rgb 21,22,23
set tics scale 0
unset cbtics
set cblabel 'Delay'
set title "Segment heatmap"

plot datafile matrix rowheaders columnheaders using 1:2:(($3==0)? 1/0:$3) with image, \
     '' matrix rowheaders columnheaders using 1:2:(($3==0)?sprintf("NaN"):sprintf("%.3f",$3)) with labels tc "white"
