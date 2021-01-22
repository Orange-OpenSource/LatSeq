
#if LATSEQ
  #include "common/utils/LATSEQ/latseq.h"
#endif


struct mac_data_req
rlc_am_mac_data_request (/*....*/) {
/*
 * ...
 */

#if LATSEQ
    LATSEQ_P("D rlc.seg.am--mac.mux","len%d:rnti%d:drb%d.lcid%d.rsn%d.fm%d", tb_size_in_bytes, ctxt_pP->rnti, l_rlc_p->rb_id, l_rlc_p->channel_id, pdu_info.sn , ctxt_pP->frame);
    //.so%d : pdu_info.so
#endif
/*
 * ...
 */
}
