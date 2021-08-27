/*
 * Software Name : LatSeq
 * Version: 1.0
 * SPDX-FileCopyrightText: Copyright (c) 2020-2021 Orange Labs
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * This software is distributed under the BSD 3-clause,
 * the text of which is available at https://opensource.org/licenses/BSD-3-Clause
 * or see the "license.txt" file for more details.
 *
 * Author: Flavien Ronteix--Jacquet
 * Software description: Example of measurement point implementation
 */

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

#if LATSEQ
    LATSEQ_P("I rlc.am.txbuf","occ%d:drb%d", l_rlc_p->sdu_buffer_occupancy, l_rlc_p->rb_id);
#endif
/*
 *
 * ...
 */
}
