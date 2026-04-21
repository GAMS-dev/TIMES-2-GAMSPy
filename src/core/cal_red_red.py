# cal_red_red.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================================*
# * CAL_RED the code associated with the substitution of flow variables by activity variables
# *	arg1 - commodity of flow
# *	arg2 - commodity associated with the activity variable
# *	arg3 - timeslice index	of flow variable
# *	arg4 - process index of flow variable
# *	arg5 - period index of flow variable
# *	arg6 - for output routine '.L' suffix. otherwise nothing
# *	arg7 - optional T or V or '' (for non-vintaged / vintaged / general case)
# *	arg8 - optional 'SUM' (only if %7 is not T)
# *	arg9 - optional 'RTP_VINTYR(R,V,%5,%4),' (only if %7 is not T)
# *	arg10 - optional multiplier (NCAP_PKCNT)
# *=============================================================================================*

from __future__ import annotations


def cal_red_red(
    var: str,
    sow: str,
    pgprim: str,
    shff: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
    def_rtp_ffcs: bool = False,
) -> str:
    shp1 = ""
    shp2 = ""
    shp3 = ""
    vnt = arg5
    tst = f"$PRC_VINT(R,{arg4})"
    shg1 = f",{arg4},'{pgprim}',COM2"
    shg2 = f",{arg4},'{pgprim}',{arg1}"
    shg = f",{arg4},CG1,{arg1}"
    if not arg7 == "T":
        vnt = "V"
    if def_rtp_ffcs:
        shp1 = f"*({shff}S(R,{vnt}{shg1}{sow}))"
        shp2 = f"*({shff}S(R,{vnt}{shg2}{sow}))"
        shp3 = f"*({shff}S(R,{vnt}{shg}{sow}))"
    if arg7 == "V":
        tst = ""
    if not arg7 == "T":
        shp1 = f"*({shff}X(R,V,{arg5}{shg1}){tst}){shp1}"
        shp2 = f"*({shff}X(R,V,{arg5}{shg2}){tst}){shp2}"
        shp3 = f"*({shff}X(R,V,{arg5}{shg}){tst}){shp3}"

    return rf"""
(
*  flow variable cannot be replaced
   ({arg8}({arg9}{var}_FLO{arg6}(R,{vnt},{arg5},{arg4},{arg1},{arg3}{sow}){arg10})$(NOT RPC_EMIS(R,{arg4},{arg1}))
    +
*   emission flow = flow variable * emission factor
   SUM((FS_EMIT(R,{arg4},{arg1},CG1,COM2),ALL_TS)$(RTPCS_VARF(R,{arg5},{arg4},COM2,ALL_TS)$RS_FR(R,{arg3},ALL_TS)),
     {arg8}({arg9}
        (
*        flow variable cannot be replaced
         {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},COM2,ALL_TS{sow})$(NOT RPC_ACT(R,{arg4},COM2)+RPC_FFUNC(R,{arg4},COM2))
         +
*        flow variable equals activity variable
         ({var}_ACT{arg6}(R,{vnt},{arg5},{arg4},ALL_TS{sow})*PRC_ACTFLO(R,{vnt},{arg4},COM2))$RPC_ACT(R,{arg4},COM2)
         +
         SUM((RPC_ACT(R,{arg4},{arg2}),PRC_TS2(R,{arg4},S2))$RS_FR(R,ALL_TS,S2),
             (
              {var}_ACT{arg6}(R,{vnt},{arg5},{arg4},S2{sow}) * ACT_FLO(R,{vnt},{arg4},COM2,ALL_TS){shp1}
             ) * RS_FR(R,ALL_TS,S2)*(1+RTCS_FR(R,{arg5},{arg2},ALL_TS,S2))
            )$RPC_FFUNC(R,{arg4},COM2)
        ) * COEF_PTRAN(R,{vnt},{arg4},CG1,COM2,{arg1},ALL_TS){shp3} {arg10}
       ) * RS_FR(R,{arg3},ALL_TS)*(1+RTCS_FR(R,{arg5},COM2,{arg3},ALL_TS))
      )$RPC_EMIS(R,{arg4},{arg1})
   )$(NOT RPC_ACT(R,{arg4},{arg1})+RPC_FFUNC(R,{arg4},{arg1}))
   +
*  flow variable equals activity variable
   {arg8}({arg9}{var}_ACT{arg6}(R,{vnt},{arg5},{arg4},{arg3}{sow})*PRC_ACTFLO(R,{vnt},{arg4},{arg1}){arg10})$RPC_ACT(R,{arg4},{arg1})
   +
   SUM((RPC_ACT(R,{arg4},{arg2}),PRC_TS2(R,{arg4},S2))$RS_FR(R,{arg3},S2),
       (
       {arg8}({arg9} {var}_ACT{arg6}(R,{vnt},{arg5},{arg4},S2{sow}) {arg10} * ACT_FLO(R,{vnt},{arg4},{arg1},{arg3}){shp2})
       ) * RS_FR(R,{arg3},S2)*(1+RTCS_FR(R,{arg5},{arg2},{arg3},S2))
    )$RPC_FFUNC(R,{arg4},{arg1})
)
"""
