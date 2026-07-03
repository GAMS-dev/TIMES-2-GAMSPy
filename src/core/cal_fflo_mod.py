# cal_fflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_FFLO the code associated with the flow variable in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# **  arg2 - 'I/O' for invest/decommission checks (no longer used)
# *   arg3 - * Peak multiplier
# *   arg4 - Peak by flow contribution
# *=============================================================================*
# *GaG Questions/Comments:
# *  - VAR_FLOs according to whether c-in-PCG otherwise RPS_S1
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cal_red_red import cal_red_red

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def cal_fflo_mod(
    reduce: str,
    sow: str,
    var: str,
    pgprim: str,
    is_rtp_ffcs_defined: bool,
    arg1: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    """Translation unit for cal_fflo.mod."""
    if reduce.upper() != "YES":
        shg = ",P,CG3,C"
        shp1_inner = ""

        if is_rtp_ffcs_defined:
            shp1_inner = f"*1+RTP_FFCS(R,V{shg}{sow}))"

        shp1_val = f"*(1+RTP_FFCX(R,V,T{shg})$PRC_VINT(R,P)){shp1_inner}"

        return rf"""
*V05c 980923 - check that commodity not just capacity related
         SUM(TOP(RP_FLO(R,P),C,'{arg1}')$(NOT RPC_EMIS(R,P,C)),
             SUM((RTP_VNTBYR(R,T,P,V),RTPCS_VARF(R,T,P,C,TS)),
* equation coarser than variable or equation finer than variable
* consider COM_TS shape too, so both TS_MAP and RS_BELOW embedded
               {var}_FLO(R,V,T,P,C,TS {sow}) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {arg3}){arg4}
         ) +
* Handle RPC_EMIS flows separately; They cannot be NOFLO
         SUM(TOP(RPC_EMIS(RP_FLO(R,P),C),'{arg1}'){arg4},
           SUM((FS_EMIT(R,P,C,CG3,COM2),RTPCS_VARF(R,T,P,COM2,TS))$RS_FR(R,S,TS),
             SUM(RTP_VNTBYR(R,T,P,V),{var}_FLO(R,V,T,P,COM2,TS {sow}) *
                COEF_PTRAN(R,V,P,CG3,COM2,C,TS) {shp1_val} {arg3}) *
             RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM2,S,TS)))) +
"""

    else:
        include_cal_red_1 = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            arg6="",
            arg7="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_rtp_ffcs_defined,
        )
        include_cal_red_2 = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            arg6="",
            arg7="V",
            arg8="SUM",
            arg9="RTP_VNTBYR(R,T,P,V),",
            arg10=f"{arg3}",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_rtp_ffcs_defined,
        )

        return rf"""
* [UR] model reduction %REDUCE% is set in *.run
* Sum over non-vintaged processes
         SUM(TOP(RP_FLO(R,P),C,'{arg1}')$(NOT PRC_VINT(R,P)),
             SUM(RTPCS_VARF(R,V(T),P,C,TS),
{include_cal_red_1}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {arg3}){arg4}
         ) +

* Sum over vintaged processes
         SUM((TOP(PRC_VINT(RP_FLO(R,P)),C,'{arg1}'),RTPCS_VARF(R,T,P,C,TS)){arg4},
{include_cal_red_2}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))
         ) +
"""
