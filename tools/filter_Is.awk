#!/usr/bin/awk
function usage(){
	print "awk -f filter_Is.awk main_ocp.16112020_123755.lseq"
}

function write_to_file(file, ts, ids){
	split(ids, arr_ids, ":");
	split(arr_ids[1], arr_props, ".");
	for (i in arr_props) {
		tmp_v=arr_props[i]
		sub(/[a-z]+/, "", tmp_v);
		sub(/[0-9]+/, "", arr_props[i]);
		printf "%s %s\n", ts, tmp_v >> file"."arr_props[i]".data";
	}
}

{
col_ts=$1
col_type=$2;
col_loc=$3;
col_id=$4;
if ( col_type=="I" )
{
	write_to_file(col_loc, col_ts, col_id);
}
if ( col_loc ~ /ip.out/ )
{
	match(col_id, /len[0-9]+/);
	tmp_rstart = RSTART+3;
	tmp_rlength = RLENGTH-3;
	match(col_id, /ipid[^\n:. ]*/);
	printf "%s %s %s\n", col_ts, substr(col_id, tmp_rstart, tmp_rlength), substr(col_id, RSTART+4, RLENGTH-4) >> "ip.out.data";
}
if ( col_loc ~ /ip.in/ )
{	
	match(col_id, /len[0-9]+/);
	tmp_rstart = RSTART+3;
	tmp_rlength = RLENGTH-3;
	match(col_id, /ipid[^\n:. ]*/);
	printf "%s %s %s\n", col_ts, substr(col_id, tmp_rstart, tmp_rlength), substr(col_id, RSTART+4, RLENGTH-4) >> "ip.in.data";
}
if ( col_loc ~ /phy.out.ant/ )
{
	match(col_id, /fm[0-9]+/);
	tmp_rstart = RSTART+2;
	tmp_rlength = RLENGTH-2;
	match(col_id, /subfm[0-9]+/);
	printf "%s %s.%s\n", col_ts, substr(col_id, tmp_rstart, tmp_rlength), substr(col_id, RSTART+5, RLENGTH-5) >> "sync.frame.data";
}
}
