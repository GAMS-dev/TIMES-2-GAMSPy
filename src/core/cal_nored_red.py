# cal_nored_red.py
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
# *=============================================================================================*

from __future__ import annotations


def cal_nored_red(
    var: str,
    sow: str,
    pgprim: str,
    shff: str,
    def_rtp_ffcs: bool,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
) -> str:
    shp3 = ""
    vnt = arg5
    shg = f",{arg4},CG3,{arg1}"
    tst = f"$PRC_VINT(R,{arg4})"

    if arg7 == "V":
        tst = ""
    if not arg7 == "T":
        vnt = "V"
    if def_rtp_ffcs:
        shp3 = f"*({shff}S(R,{vnt}{shg}{sow}))"
    if vnt == "V":
        shp3 = f"*({shff}X(R,V,{arg5}{shg}){tst}){shp3}"

    return rf"""
{arg8}({arg9}
*  flow variable cannot be replaced
   {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},{arg1},{arg3} {sow})$(NOT RPC_EMIS(R,{arg4},{arg1}))
    +
*   emission flow = flow variable * emission factor
   SUM((FS_EMIT(R,{arg4},{arg1},CG3,COM2),ALL_TS)$(RS_FR(R,{arg3},ALL_TS)*RTPCS_VARF(R,{arg5},{arg4},COM2,ALL_TS)),
     {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},COM2,ALL_TS{sow}) * COEF_PTRAN(R,{vnt},{arg4},CG3,COM2,{arg1},ALL_TS){shp3} *
     RS_FR(R,{arg3},ALL_TS)*(1+RTCS_FR(R,{arg5},COM2,{arg3},ALL_TS))
   )$RPC_EMIS(R,{arg4},{arg1})
)
"""
