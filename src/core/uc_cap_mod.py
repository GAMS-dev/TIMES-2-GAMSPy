# uc_cap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_CAP the code associated with the VAR_CAP variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 'T' or 'T+1' or 'T-1' index
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


def uc_cap_mod(
    var: str,
    sow: str,
    vda: str,
    abs: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
) -> str:
    """Translation unit for uc_cap.mod."""

    return rf"""
* "SUM(UC_R_SUM(R,UC_N)," or bracket (
   {arg1}
*      "SUM(UC_T_SUM(UC_N,T)," or bracket (
        {arg2}
             SUM(RTP(R,{arg3},P)$UC_GMAP_P(R,UC_N,'CAP',P),

* VAR_CAP can always be directly used for UC_CAP
                     {var}_CAP(R,{arg3},P {sow}) * UC_CAP(UC_N,{arg4},R,{arg6},P) *

* PROD operator needs to be 'tweaked' due to bug in older GAMS versions
{
        f"                      PROD(UC_ATTR(R,UC_N,{arg4},'CAP','GROWTH'),"
        if arg5 == "1"
        else ""
    }
{
        f"                           POWER(ABS(UC_CAP(UC_N,{arg4},R,{arg6},P)),{arg7}*UC_SIGN({arg4})-1)) *"
        if arg5 == "1"
        else ""
    }
                     PROD(UC_ATTR(R,UC_N,{arg4},'CAP','CAPACT'),PRC_CAPACT(R,P)) *
                     PROD(L('N'),1)
             )
*       closing bracket of arg2 :
        )
*  closing bracket of arg1 :
   )

{
        ""
        if f"{vda}{arg5}" != "YESS"
        else (
            f'''
* Subtract offline capacity if requested
* SUM or bracket (
  +{arg2}
     SUM(RTP(R,{arg3},P)$(RP_UPL(R,P,'FX')$UC_GMAP_P(R,UC_N,'CAP',P)), EPS+
         UC_CAP(UC_N,{arg4},R,{arg6},P)*PROD(UC_ATTR(R,UC_N,{
                arg4
            },'CAP','CAPACT'),PRC_CAPACT(R,P)) *
         SUM(RTP_VINTYR(R,V,{arg3},P),({macro.upscaps.render()})))$UC_ATTR(R,UC_N,{
                arg4
            },'CAP','ONLINE')
   )
   {
                ""
                if abs.upper() != "YES"
                else (
                    f"""
* Add reserve flows if requested
  +{arg2}
     SUM(BS_UCMAP(UC_N,{arg4},R,P,C)$BS_COMTS(R,C,S),UC_FLO(UC_N,{arg4},R,{arg6},P,C,'ANNUAL') * PRC_CAPACT(R,P) *
         SUM((RTP_VINTYR(R,V,{arg3},P),BS_PRS(R,P,TS))$RS_FR(R,S,TS),RS_FR(R,TS,S) *
           SUM(LNX(L),{var}_BSPRS(R,V,T,P,C,TS,L{sow})$(IPS(L)+BS_SUPP(R,P)$(ABS(BS_RTYPE(R,C))>2)))))
   )
"""
                )
            }
'''
        )
    }

"""
