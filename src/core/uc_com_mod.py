# uc_com_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_COMPD the code associated with the COMPRD variable in the EQ_USERCON
# *     - %1 region summation index
# *     - %2 period summation index
# *     - %3 time-slice summation index
# *     - %4 'T' or 'T+1' index
# *     - %5 'LHS' or 'RHS'
# *     - %6 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def uc_com_mod(
    var: str = "",
    sow: str = "",
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
    arg11: str = "",
) -> str:
    """Translation unit for uc_com.mod."""

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket (
 {arg1}
*     "SUM(UC_T_SUM(UC_N,T)," or bracket (
      {arg2}
*          "SUM(UC_TS_SUM(UC_N,S)," or bracket (
           {arg3}
              SUM(UC_GMAP_C(R,UC_N,'{arg9}',C,UC_GRPTYPE),
{"(1+(FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS',UC_GRPTYPE,'PERDISC')-1)$UC_DT(R,UC_N)) *" if arg6 == "2" else ""}
                  SUM(RHS_COM{arg8}(R,{arg4},C,TS)$RS_FR(R,S,TS),
                      UC_COM(UC_N,'{arg9}',{arg5},R,{arg7},C,TS,UC_GRPTYPE) * {var}_COM{arg9}(R,{arg4},C,TS {sow})*
                      (1+(1/COM_IE(R,{arg4},C,TS)-1)$(UC_ATTR(R,UC_N,{arg5},UC_GRPTYPE,'EFF') XOR DIAG(UC_GRPTYPE,'COM{arg9}'))) *

* [AL] PROD operator is useful here
                      PROD(ANNUAL,1)*PROD(RS_BELOW(R,TS,S),RS_FR(R,S,TS)*(1+RTCS_FR(R,{arg4},C,S,TS))) *
{f"                      PROD(UC_ATTR(R,UC_N,{arg5},UC_GRPTYPE,'GROWTH')," if arg6 == "1" else ""}
{f"                           POWER(ABS(UC_COM(UC_N,'{arg9}',{arg5},R,{arg7},C,TS,UC_GRPTYPE)),{arg11}*UC_SIGN({arg5})-1)) *" if arg6 == "1" else ""}
{"                      (1/G_YRFR(R,S)) *" if arg6 == "S" else ""}
                      PROD(UC_ATTR(R,UC_N,{arg5},UC_GRPTYPE,'PERIOD'),FPD({arg4})) *

                      PROD(REG(R)$SUM(UC_ATTR(R,UC_N,{arg5},UC_GRPTYPE,UC_COST),1),
                        SUM((UC_ATTR(R,UC_N,{arg5},UC_GRPTYPE,UC_COST),RDCUR(R,CUR)),
                            OBJ_COM{arg10}(R,{arg4},C,TS,UC_COST,CUR)))
                  )
              )
*          closing bracket of arg3 :
           )
*       closing bracket of arg2 :
        )
*   closing bracket of arg1 :
    )
"""
