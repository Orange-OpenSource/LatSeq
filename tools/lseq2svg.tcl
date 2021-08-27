#! /bin/sh
# -*- mode: Tcl ; tab-width: 8 -*-
#\
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
# Author: Alexandre Ferieux
# Software description: Waterfall representation of journey in *.svg from *.lseqj
#################################################################################


exec tclsh $0 "$@"


set xoff 100
set yoff 200
set xscale 50
set yscale 100000
set maxyy 0
set uid 0

set buf(1) ""
set buf(2) ""
set buf(3) ""


# fatal
proc fatal s {puts stderr "\#\#\# [file tail $::argv0]:$s";exit 1}



#========= UTILITIES ==================================

proc setonce {vvar val} {
    upvar $vvar var
    if {[info exists var]} {
	fatal "# double definition for '$vvar'
 First:   $var
 Second:  $val"
    }
    set var $val
}

proc parray2 varr {
    upvar $varr arr
    foreach k [lsort -ascii [array names arr]] {
	puts stderr [format "  %30s = %s" "${varr}($k)" $arr($k)]
    }
}

proc tdiff6 {t2 t1} {
	if {![regexp {[.]} $t1]} {append t1 .000000}
	if {![regexp {^(........)_(..)(..)(..)\.(......)} $t1 pipo j1 h1 m1 s1 us1]} {
		error "Bad tstamp: $t1"
	}
	if {![regexp {[.]} $t2]} {append t2 .000000}
	if {![regexp {^(........)_(..)(..)(..)\.(......)} $t2 pipo j2 h2 m2 s2 us2]} {
		error "Bad tstamp: $t2"
	}
	foreach v {h1 m1 s1 us1 h2 m2 s2 us2} {scan [set $v] %d $v}
	set dj 0
	if {$j1!=$j2} {
		set dj [expr {[clock scan $j2]-[clock scan $j1]}]
	}
	set c1 [expr {$us1/1000.0+$s1*1000+$m1*60000+$h1*3600000}]
	set c2 [expr {$us2/1000.0+$s2*1000+$m2*60000+$h2*3600000}]
	return [format %.6f [expr {$dj+($c2-$c1)/1000.0}]]
}

proc out {lay txt} {
    append ::buf($lay) $txt \n
}


proc tfx {x dx} {
    expr {int($x*$::xscale+$dx+$::xoff)}
}

proc tfy {y dy} {
    expr {int($y*$::yscale+$dy+$::yoff)}
}

proc dtfy {y2 y1} {
    expr {int(($y2-$y1)*$::yscale)}
}

proc deja {x y} {
    global deja

    set x [tfx $x 0]
    set y [tfy $y 0]
    if {![info exists deja($x,$y)]} {set r 0} else {set r $deja($x,$y)}
    set deja($x,$y) [expr {$r+4}]
    return $r
}

proc finddang {s id vfid} {
    global dang
    upvar $vfid fid
    
    set sh $id
    while {1} {
	if {[info exists dang($s,$sh)]} {set fid $sh;return 1}
	if {![regexp {^(.*)[.][^.]*$} $sh -> sh]} break
    }
    set cdt [array names dang $s,$id.*]
    switch -exact -- [llength $cdt] {
	0 {return 0}
	1 {}
	default {
	    puts stderr "* skipping ambiguous retrolinks: $cdt"
	}
    }
    set fid [lindex $cdt 0]
    regexp {^[^,]*,(.*)$} $fid -> fid
    return 1
}

#========= SVG STUFF ==================================

set style {
    <style>
    line.col {
	stroke-width: 1;
	stroke:       black;
	stroke-dasharray: 2 5;
    }
    </style>
}

proc svgmultiline {txt xx} {
    if {![regexp "\n" $txt]} {return $txt}
    set out ""
    set l [split $txt \n]
    set n [expr {[llength $l]-1}]
    set dy "dy=\"-${n}em\""
    foreach li $l {
	append out "<tspan x=\"$xx\" $dy>$li</tspan>"
	set dy "dy=\"1em\""
    }
    return $out
}

proc rendercol {pos txt} {
    out 1 [format {  <line class="col" x1="%d" y1="%d" x2="%d" y2="100%%" />} [tfx $pos 0] [tfy 0 -50] [tfx $pos 0 ]]    
    out 3 [format {  <text transform="rotate(-90,%d,%d)" x="%d" y="%d" text-anchor="start" dominant-baseline="middle">%s</text>} [tfx $pos 0] [tfy 0 -60] [tfx $pos 0] [tfy 0 -60] $txt]
}

proc render  {x1 y1 x2 y2 ign txt}  {
    set d [deja $x2 $y1]
    set u [incr ::uid]
    out 1 [format {  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke-width="1" stroke="#ccc" />} [tfx $x1 17] [tfy $y1 0] [tfx $x2 -17] [tfy $y1 0]]
    out 1 [format {  <rect id="r%d" x="%d" y="%d" width="%d" height="%d" fill="red" stroke="none" fill-opacity=".25" rx="5" ry="5">
	</rect>} $u [tfx $x2 [expr {$d-20}]] [tfy $y1 0] 40 [dtfy $y2 $y1]]
    out 2 [format {  <rect id="fr%d" x="%d" y="%d" width="%d" height="%d" fill="none" stroke="red" rx="5" ry="5">
	<set attributeName="stroke-width" to="3" begin="mouseover;r%d.mouseover" end="mouseout;r%d.mouseout"/>
	</rect>} $u [tfx $x2 [expr {$d-20}]] [tfy $y1 0] 40 [dtfy $y2 $y1] $u $u]
    set xx [tfx $x2 $d]
    set yy [tfy $y1 -5]
    if {$yy>$::maxyy} {set ::maxyy $yy}
    set txt [svgmultiline $txt $xx]
    out 3 [format {  <text x="%d" y="%d" text-anchor="start" dominant-baseline="text-bottom" fill="black" font-size="10" filter="" visibility="hidden">
	<set attributeName="visibility" to="visible" begin="r%d.mouseover;fr%d.mouseover" end="r%d.mouseout;fr%d.mouseout"/>
	<set attributeName="filter" to="url(#bgwhite)"  begin="r%d.mouseover;fr%d.mouseover" end="r%d.mouseout;fr%d.mouseout"/>
	%s</text>} $xx $yy $u $u $u $u $u $u $u $u $txt]
}

proc render0 {x y ign txt {fix 1}} {
    set d [deja $x $y]
    set u [incr ::uid]
    out 1 [format {  <path id="p%d" d="M %d,%d %d,%d %d,%d z" fill="red" fill-opacity=".25" stroke="red">
	<set attributeName="stroke-width" to="2" begin="mouseover" end="mouseout"/>
	</path>} \
	       $u \
	       [tfx $x [expr {$d-20}]] [tfy $y 0] \
	       [tfx $x [expr {-$d+20}]] [tfy $y 0] \
	       [tfx $x 0] [tfy $y 5] \
	      ]
    set xx [tfx $x 0]
    set yy [tfy $y -5]
    if {$yy>$::maxyy} {set ::maxyy $yy}
    set txt [svgmultiline $txt $xx]

    if {$fix} {
	out 3 [format {  <text x="%d" y="%d" text-anchor="middle" dominant-baseline="text-bottom" font-size="10" filter="url(#bgwhite)">%s</text>} $xx $yy $txt]
    } else {
	out 3 [format {  <text x="%d" y="%d" text-anchor="middle" dominant-baseline="text-bottom" font-size="10" filter="" visibility="hidden">
	    <set attributeName="visibility" to="visible" begin="p%d.mouseover" end="p%d.mouseout"/>
	    <set attributeName="filter" to="url(#bgwhite)" begin="p%d.mouseover" end="p%d.mouseout"/> 
	    %s</text>} $xx $yy $u $u $u $u $txt]
    }
}

proc render2  {x1 x2 y}  {
    set d [deja $x2 $y]
    set u [incr ::uid]
    out 1 [format {  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke-width="1" stroke="#ccc" />} [tfx $x1 17] [tfy $y 0] [tfx $x2 -17] [tfy $y 0]]
}


#========= PARSING ==================================

set first 1
while {[gets stdin line]>=0} {
    set line [string trim $line]

    # Handle metadata
    if {[regexp {^#} $line]} {
	if {[regexp {^#funcId[ 	]} $line]} {
	    setonce funcId [lrange $line 1 end]
	    continue
	}
	continue
    }
    if  {$line==""} continue

    # First data line here
    if {$first} {
	set first 0
	if {![info exists funcId]} {
	    fatal "Missing #funcId header before data line: $line"
	}

	# Expand funcId's
	set ff {}
	foreach f $funcId {
	    regsub -all {[.]\[0\]} $f ".0" f
	    if {[regexp {^([^][]*)\[([0-9]+)-([0-9]+)\]$} $f -> pre a b]} {
		for {set i $a} {$i<=$b} {incr i} {
		    lappend ff $pre$i
		}
	    } else {
		lappend ff $f
	    }
	}
	# Store X positions in fx($f)
	set pos 0
	foreach f $ff {
	    set fx($f) $pos
	    rendercol $pos $f
	    incr pos
	}
    }
    if {[llength $line]!=4} {
	puts stderr "* ignoring malformed line, should be: 'timestamp U/D src--dest dataId': $line"
	continue
    }
    foreach {ts dir sd id} $line break
    if {![info exists tsbase]} {set tsbase $ts}
    set rts [tdiff6 $ts $tsbase] 
    if {![regexp {^(.*)--(.*)$} $sd -> s d]} {
	puts stderr "* ignoring malformed line, src--dst expected instead of: $sd"
	continue
    }
    set ::orphan($d,$id) [list $rts $s]
    if {[finddang $s $id fid]} {
	foreach {ts0 dir0 s0 d0} $dang($s,$fid) break
	set x1 $fx($s0)
	set t1 $ts0
	set x2 $fx($d0)
	set t2 $rts
	set dur [format %.6f [expr {$t2-$t1}]]
	render $x1 $t1 $x2 $t2 -- "ID:  $id\nLAY: $s\nDUR: $dur\nRTS:  $t1"
	catch {unset orphan($s,$fid)}
    } else {
	render0 $fx($s) $rts -- $id
    }
    set dang($d,$id) [list $rts $dir $s $d]
}

#========= OUTPUT ==================================

parray2 orphan
foreach {did tss} [array get orphan] {
    if {![regexp {^([^,]*),(.*)$} $did -> d id]} {fatal "Internal: malformed orphan key: $did"}
    foreach {ts s} $tss break
    set x1 $fx($s)
    set x2 $fx($d)
    render2 $x1 $x2 $ts
    render0 $x2 $ts -- "ID:  $id\nLAY: $d\nRTS:  $ts" 0
}

puts [format {<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="3000" height="%d">} [expr {$maxyy+50}]]

puts $style

puts {
    <defs>
    <filter x="0" y="0" width="1" height="1" id="bgwhite">
    <feFlood flood-color="white"/>
    <feComposite in="SourceGraphic" operator="over" />
    </filter>
    </defs>
}

puts  { <g>}

puts $buf(1)
puts $buf(2)
puts $buf(3)

puts { </g>
</svg>}

