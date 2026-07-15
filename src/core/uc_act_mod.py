# uc_act_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_ACT the code associated with the activity variable in the EQ_USERCON
# *     - %1 region summation index
# *     - %2 period summation index
# *     - %3 time-slice summation index
# *     - %4 'T' or 'T+1' index
# *     - %5 'LHS' or 'RHS'
# *     - %6 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*

from __future__ import annotations

import logging

from utils.macros import macro_config as macro

logger = logging.getLogger(__name__)


def uc_act_mod(
    var: str,
    sow: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
) -> str:
    """Translation unit for uc_act.mod."""

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket "("
 {arg1}
*     "SUM(UC_T_SUM(UC_N,T)," or bracket "("
      {arg2}
{"(1+(FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','ACT','PERDISC')-1)$UC_DT(R,UC_N)) *" if arg6 == "2" else ""}
*          "SUM(UC_TS_SUM(UC_N,S)," or bracket "("
           {arg3}
              SUM(RTP_VINTYR(R,V,{arg4},P)$UC_GMAP_P(R,UC_N,'ACT',P),
                          (
*V0.9a S reference should be TS
                           SUM(PRC_TS(R,P,TS)$(RS_FR(R,S,TS)*RTP_VARA(R,{arg4},P)),
                               {var}_ACT(R,V,{arg4},P,TS {sow})*UC_ACT(UC_N,{arg5},R,{arg7},P,TS)*

* [AL] PROD operator is useful here:
                               PROD(ANNUAL,RS_FR(R,S,TS)) *

{f"                               PROD(UC_ATTR(R,UC_N,{arg5},'ACT','GROWTH')," if arg6 == "1" else ""}
{f"                                 POWER(ABS(UC_ACT(UC_N,{arg5},R,{arg7},P,TS)),{arg8}*UC_SIGN({arg5})-1)) *" if arg6 == "1" else ""}
{"                               (1/G_YRFR(R,S)) *" if arg6 == "S" else ""}
                               PROD(UC_ATTR(R,UC_N,{arg5},'ACT',UC_PERDS),FPD({arg4}) *
                                 PROD(UC_NEWFLO(UC_PERDS),1$(SAMEAS(V,{arg4})+RVPT(R,V,P,{arg4}))/FPD({arg4})))

                           )
                          )
                            *
                          PROD(UC_ATTR(R,UC_N,{arg5},'ACT','COST'),SUM(RDCUR(R,CUR),{macro.obj_acost("R", arg4, "P", "CUR")}))
              )
*          closing bracket of arg3 :
           )

*       closing bracket of arg2 :
        )

*   closing bracket of arg1 :
    )
"""
