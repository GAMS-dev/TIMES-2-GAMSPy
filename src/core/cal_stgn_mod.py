# cal_stgn_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_STG the code associated with the storage flows in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# *   arg2 - 'OUT/IN' for consumption/production
# *   arg3 - STG_EFF for output
# *   arg4 - STG_EFF for output
# *   arg5 - for day-night storage indicator
# *=============================================================================*
# * Questions/Comments:
# * arg6 - NCAP_PKCNT multiplier

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def cal_stgn_mod(
    var: str,
    sow: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
) -> str:
    """Translation unit for cal_cap.mod."""
    return rf"""
*V05c 980923 - check that commodity not just capacity related
  SUM((TOP(RPC_STG(R,P,C),'{arg1}'),RPCS_VAR(R,P,C,TS))${arg5},
       SUM(RTP_VNTBYR(R,T,P,V),
          ({var}_S{arg1}(R,V,T,P,C,TS {sow}){arg3}-{arg4}{var}_S{arg2}(R,V,T,P,C,TS {sow})$RPC_STGN(R,P,C,'{arg2}')){arg6})$(NOT RPC_STGN(R,P,C,'{arg1}')) *
* equation coarser than variable or finer than variable
        RS_FR(R,S,TS)
     ) +
"""
