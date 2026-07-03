# eqpk_ect_ier.py
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * [UR]: 04/22/2003: adjustment for extraction condensing CHP plants

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cal_fflo_mod import cal_fflo_mod

if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)


def eqpk_ect_ier(
    varv: str,
    sws: str,
    # args for cal_fflo_mod
    reduce: str,
    sow: str,
    var: str,
    pgprim: str,
    is_rtp_ffcs_defined: bool,
) -> str:
    """Translation unit for eqpk_ect.ier."""
    include_cal_fflo = cal_fflo_mod(
        reduce=reduce,
        sow=sow,
        var=var,
        pgprim=pgprim,
        is_rtp_ffcs_defined=is_rtp_ffcs_defined,
        arg1="OUT",
        # arg2 = "O" in cal_fflo_mod stated as no longer used
        arg3="*(-(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C)))$RPC_PKF(R,P,C)",
    )

    return rf"""
     + SUM(ECT_ELC(ECT_CHP(R,P),C)$((NOT PRC_CAP(R,P)*RPC_PKC(R,P,C))$TOP(R,P,C,'OUT')),
{include_cal_fflo}
             (G_YRFR(R,S)*SUM(RTP_CPTYR(R,V,T,P),PRC_CAPACT(R,P)*
                               NCAP_PKCNT(R,V,P,S)*COEF_CPT(R,V,T,P)*
                               ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V)))))

"""
