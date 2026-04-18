# uc_cli_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_CLI the UC code associated with climate variables
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


def uc_cli_mod(
    is_uc_cli_defined: bool,
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
    """Translation unit for uc_cli.mod."""
    if not is_uc_cli_defined:
        return ""

    growth_term = ""
    if arg6 == "1":
        growth_term = rf"""
                      PROD(UC_ATTR(R,UC_N,{arg5},'CLI','GROWTH'),
                           POWER(ABS(UC_CLI(UC_N,{arg5},R,{arg7},CM_VAR)),{arg8}*UC_SIGN({arg5})-1)) *
"""
    return rf"""
* "SUM(UC_R_SUM(R,UC_N)," or bracket (
  {arg1}
*     "SUM(UC_T_SUM(UC_N,T)," or bracket (
       {arg2}
*         "SUM(UC_TS_SUM(UC_N,S)," or bracket (
           {arg3}
              SUM(CM_VAR$UC_CLI(UC_N,{arg5},R,{arg7},CM_VAR), UC_CLI(UC_N,{arg5},R,{arg7},CM_VAR) *
                ({var}_CLITOT(CM_VAR,{arg4} {sow})$CM_KIND(CM_VAR) +
                 SUM(CM_BOXMAP(CM_KIND,CM_VAR,CM_BOX)$(NOT CM_ATMAP(CM_KIND,CM_VAR)$CM_EMIS(CM_KIND)),{var}_CLIBOX(CM_VAR,CM_BOX,{arg4} {sow})) +
                 SUM(CM_BOXMAP(CM_EMIS,CM_HISTS,CM_BOX)$(CM_PHI(CM_EMIS,CM_BOX,CM_EMIS)$CM_ATMAP(CM_EMIS,CM_VAR)),
                     {var}_CLIBOX(CM_VAR,CM_BOX,{arg4} {sow})/CM_PPM(CM_EMIS))$(NOT CM_TKIND(CM_VAR))) *
* [AL] PROD operator is useful here, but requires 'initialization' due to GAMS bug
                      PROD(ANNUAL,1) *
{growth_term}
                      PROD(UC_ATTR(R,UC_N,{arg5},'CLI','PERIOD'),FPD({arg4}))
              )

*          closing bracket of {arg3} :
           )

*       closing bracket of {arg2} :
       )

*   closing bracket of {arg1} :
   )
"""
