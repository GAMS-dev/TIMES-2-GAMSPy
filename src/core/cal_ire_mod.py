# cal_ire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_IRE the code associated with the inter-region trade variable in EQ_COMxxx
# *   arg1 - IMPort/EXPort indicator
# *   arg2 - IN/OUT nature of the aux/emissions
# *   arg3 - IE or ''
# *   arg4 - * Peak multiplier
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.powerflo_vda import powerflo_vda_ireaux

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def cal_ire_mod(
    var: str,
    sow: str,
    shff: str,
    is_rtp_ffcs_defined: bool,
    is_ireauxbal: bool,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
) -> str:
    """Translation unit for cal_ire.mod."""

    mx_val = f"({shff}S(R,V,P,C,C{sow}))*" if is_rtp_ffcs_defined else ""
    # *V0.9 022100 - handle the fact that called 2x for aux
    ie_val = arg3 if arg3.strip() != "" else f"'{arg1}'"

    help_str = r""

    if f"{arg1},{arg2}" not in ["EXPOUT", "IMPIN"]:
        help_str += rf"""
* actual exchange
         SUM((RPC_IRE({arg6}R,P{arg7},C,'{arg1}'),RTP_VNTBYR(R,T,P,V)),
             SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,S,TS),
                 ({var}_IRE(R,V,T,P,C,TS,'{arg1}'{sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)
                 ){arg4} * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)))
         ) +
"""
    if is_ireauxbal:
        # take arg1 from powerflow.vda since if this is called its always IREAUX
        # from `$ SETGLOBAL IREAUXBAL $BATINCLUDE powerflo.vda IREAUX` in powerflow.vda
        help_str += powerflo_vda_ireaux(
            arg1="IREAUX", arg2=arg2, arg3=arg5, var=var, sow=sow
        )

    # AUXONLY
    # *V0.5b handle auxiliary commodity flows too
    # *** NOTE: assumes that attribute at the same level as the variable!!
    # *V0.9 022100 - do IN/OUT explicitly

    help_str += rf"""
    SUM((RPC_IRE({arg6}R,P{arg7},COM,{ie_val}),RTPCS_VARF(R,T,P,COM,TS))$(IRE_FLOSUM(R,T,P,COM,TS,{ie_val},C,'{arg2}')$RS_FR(R,S,TS)),
         IRE_FLOSUM(R,T,P,COM,TS,{ie_val},C,'{arg2}') *
         SUM(RTP_VNTBYR(R,T,P,V), {mx_val}
             ({var}_IRE(R,V,T,P,COM,TS,{ie_val}{sow})$(NOT RPC_AIRE(R,P,COM))+({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)
             ){arg4}
         ) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
     ) +
"""
    return help_str
