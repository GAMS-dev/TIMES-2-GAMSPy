# uc_ncap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_NCAP the code associated with the flow variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 'T' or 'T+1' index
# *     - arg4 'LHS' or 'RHS'
# *     - arg5 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*
# *UR Questions/Comments:
# *  -

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from utils.macros import macro_config as macro

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def uc_ncap_mod(
    var: str,
    sow: str,
    varv: str,
    sws: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
) -> str:
    """Translation unit for uc_ncap.mod."""

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket "("
 {arg1}

* UR 05/15/00
*    SUM(UC_GRP$( UC_GMAP(R,UC_N,'NCAP',UC_GRP)*{arg4}   ),

*       "SUM(UC_T_SUM(UC_N,T)," or bracket "("
        {arg2}
* [AL] VAR_NCAP(R,arg3,P) can be active even if there is no RTP_CPTYR(R,V,T,P) (due to ILED)!
* [AL] Therefore, changed to check for RTP(R,arg3,P) without RTP_OFF(R,arg3,P)
*              SUM((P,CUR)$(UC_GMAP_P(R,UC_N,'NCAP',P)*SUM(V,RTP_CPTYR(R,V,T,P))),
              SUM(UC_GMAP_P(R,UC_N,'NCAP',P)$RTP(R,{arg3},P), UC_NCAP(UC_N,{arg4},R,{arg6},P) *
                  ({var}_NCAP(R,{arg3},P {sow})$(NOT RTP_OFF(R,{arg3},P)) +
                   (SUM(RVPT(R,V,P,{arg3}),{varv}_NCAP(R,V,P {sws})) + {var}_NCAP(R,{arg3},P {sow}) *
                    (COEF_RPTI(R,{arg3},P)-PROD(RVPT(R,{arg3},P,MILESTONYR),2)))$UC_ATTR(R,UC_N,{arg4},'NCAP','PERIOD')) *

* [AL] PROD operator is useful here, but needs to be 'tweaked' due to a bug in GAMS 21.3-21.4:
{f"                   PROD(UC_ATTR(R,UC_N,{arg4},'NCAP','GROWTH')," if arg5 == "1" else ""}
{f"                       POWER(ABS(UC_NCAP(UC_N,{arg4},R,{arg6},P)),{arg7}*UC_SIGN({arg4})-1)) *" if arg5 == "1" else ""}
                  PROD(UC_ATTR(R,UC_N,{arg4},'NCAP','BUILDUP'),1/LEAD({arg3})) *

                  PROD(L('N'),PROD(REG(R)$SUM(UC_ATTR(R,UC_N,{arg4},'NCAP',UC_COST),1),
                    SUM(RDCUR(R,CUR),
{f"                            SUM(UC_ATTR(R,UC_N,{arg4},'NCAP',UC_ANNUL),CST_ANNC(R,{arg3},P,{arg6},UC_ANNUL,CUR))+" if arg3 != arg6 else ""}
                       {macro.obj_icost("R", arg3, "P", "CUR")}$UC_ATTR(R,UC_N,{arg4},'NCAP','COST')
                       +{macro.obj_itax("R", arg3, "P", "CUR")}$UC_ATTR(R,UC_N,{arg4},'NCAP','TAX')
                       -{macro.obj_isub("R", arg3, "P", "CUR")}$UC_ATTR(R,UC_N,{arg4},'NCAP','SUB'))))

              )

*       closing bracket of arg2 :
        )

*   closing bracket of arg1	:
    )
"""
