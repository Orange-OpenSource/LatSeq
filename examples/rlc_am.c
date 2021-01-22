
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
      } else {
        if (rlc_am_get_control_pdu_infos(rlc_am_pdu_sn_10_p, &tb_size_in_bytes, &l_rlc_p->control_pdu_info) >= 0) {
          tb_size_in_bytes   = ((struct mac_tb_req *) (tb_p->data))->tb_size; //tb_size_in_bytes modified by rlc_am_get_control_pdu_infos!
/*
 * ...
 */
}
