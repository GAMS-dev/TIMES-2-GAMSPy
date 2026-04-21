# cal_cap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_CAP the code for capacity dependent commodity flows in EQ_COMxxx
# *   arg1 - IN/OUT indicator
# *   arg2 - I/O indicator
# *   arg3 - cost expression for EQOBJVAR
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_CPT derived in COEF_CPT.MOD

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def cal_cap_mod(
    varv: str,
    sws: str,
    rcapsub: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    """Translation unit for cal_cap.mod."""
    return rf"""
         SUM(RTP_CPTYR(R,V,T,P)$NCAP_COM(R,V,P,C,'{arg1}'),
*V05b 980902 - need to apply seasonal fraction
             COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,'{arg1}') * G_YRFR(R,S) *
             {arg3}
             ({varv}_NCAP{arg4}(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V) {rcapsub}) *
* Adjust for lagged commodity flows
             (1 + COEF_CIO(R,V,T,P,C,'{arg1}'))
         ) +
* CAL_NCOM: the term associated with invest/decommission commodities in the EQ_COMxxx
         SUM(RPC_CAPFLO(R,V,P,C)$COEF_{arg2}COM(R,V,T,P,C), COEF_{arg2}COM(R,V,T,P,C) *
             {arg3}
             G_YRFR(R,S) * ({varv}_NCAP{arg4}(R,V,P {sws})$T(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V))
         )
"""
