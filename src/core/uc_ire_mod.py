# uc_ire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_IRE the code associated with the IRE variable in the EQ_USERCON
# *     - %1 region summation index
# *     - %2 period summation index
# *     - %3 time-slice summation index
# *     - %4 'T' or 'T+1' index
# *     - %5 'LHS' or 'RHS'
# *=============================================================================*

from __future__ import annotations

import logging

from utils.macros import macro_config as macro

logger = logging.getLogger(__name__)


def uc_ire_mod(
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
    """Translation unit for uc_ire.mod."""

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket "("
 {arg1}
*     "SUM(UC_T_SUM(R,UC_N,T)," or bracket "("
      {arg2}
{"(1+(FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','IRE','PERDISC')-1)$UC_DT(R,UC_N)) *" if arg6 == "2" else ""}
*          "SUM(UC_TS_SUM(R,UC_N,S)," or bracket "("
           {arg3}
*[UR]: RPC_IRE control may be redundant, only necessary if UC_IRE given for non-exchange processes by mistake
                 SUM((RTP_VINTYR(R,V,{arg4},P),UC_MAP_IRE(UC_N,R,P,C,IE),RTPCS_VARF(R,{arg4},P,C,TS))$RS_FR(R,S,TS),
                     (

* [UR] model reduction %REDUCE% is set in *.run
                             ({var}_IRE(R,V,{arg4},P,C,TS,IE {sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,{arg4},P,TS {sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))
                             * UC_IRE(UC_N,{arg5},R,{arg7},P,C,TS,IE) *
*GG* use the derived multipier
* [AL] PROD operator is useful here, but must be activated due to a GAMS bug:
                               PROD(ANNUAL,1)*PROD(RS_BELOW(R,TS,S),RS_FR(R,S,TS)*(1+RTCS_FR(R,{arg4},C,S,TS))) *

{f"                               PROD(UC_ATTR(R,UC_N,{arg5},'IRE','GROWTH')," if arg6 == "1" else ""}
{f"                                    POWER(ABS(UC_IRE(UC_N,{arg5},R,{arg7},P,C,TS,IE)),{arg8}*UC_SIGN({arg5})-1)) *" if arg6 == "1" else ""}
{"                               (1/G_YRFR(R,S)) *" if arg6 == "S" else ""}
                               PROD(UC_ATTR(R,UC_N,{arg5},'IRE',UC_PERDS),FPD({arg4}) *
                                    PROD(UC_NEWFLO(UC_PERDS),1$(SAMEAS(V,{arg4})+RVPT(R,V,P,{arg4}))/FPD({arg4}))) *

                               PROD(REG(R)$SUM(UC_ATTR(R,UC_N,{arg5},'IRE',UC_COST),1),
                                SUM((RDCUR(R,CUR),TS_ANN(TS,SL)),
                                  {macro.obj_fcost("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'IRE','COST')
                                 +{macro.obj_fdelv("R", arg4, "P", "C", "SL", "CUR")}$UC_ATTR(R,UC_N,{arg5},'IRE','DELIV')
                                 +MIN(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'IRE','SUB')
                                 +MAX(0,{macro.obj_ftax("R", arg4, "P", "C", "SL", "CUR")})$UC_ATTR(R,UC_N,{arg5},'IRE','TAX')))
                     )
                    )

*          closing bracket of arg3 :
           )

*       closing bracket of arg2 :
        )

*   closing bracket of arg1 :
    )
"""
