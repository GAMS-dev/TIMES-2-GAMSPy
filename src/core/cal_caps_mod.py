# cal_caps_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_CAPS the code for capacity dependent commodity flows regardless of IO
# *   arg1 - Milestone year
# *   arg2 - coefficient expression for EQOBJVAR / UC_FLO
# *   arg3 - TS control index for RPCS_VAR summing
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT derived in COEF_CPT.MOD

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)


def cal_caps_mod(
    # TODO not sure if this is ok...
    # $IF DEFINED VNRET
    condition: bool,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    varv: str = "",
    sws: str = "",
    varm: str = "",
) -> str:
    return rf"""
*V05c 980923 - use the capacity flow control set
   SUM((VNT(V,{arg1}),RPC_CAPFLO(R,V,P,C)),
*V05b 980902 - need to apply seasonal fraction
* Flows related to investment / decommissioning
      ((COEF_ICOM(R,V,{arg1},P,C)+COEF_OCOM(R,V,{arg1},P,C)) * G_YRFR(R,S) *
        ({varv}_NCAP{arg4}(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)) *
        SUM(RPCS_VAR(R,P,C,{arg3}), RS_FR(R,TS,S) * {arg2}))$(COEF_ICOM(R,V,{arg1},P,C)+COEF_OCOM(R,V,{arg1},P,C)) +
* Flows related to existing capacity over lifetime
      SUM((RTP_CPTYR(R,V,{arg1},P),IO)$NCAP_COM(R,V,P,C,IO),
        COEF_CPT(R,V,{arg1},P) * NCAP_COM(R,V,P,C,IO) * G_YRFR(R,S) *
        ({varv}_NCAP{arg4}(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P)
{f"-SUM(VNRET(V,MODLYEAR({arg1})),{varm}_SCAP{arg4}(R,V,{arg1},P{sws}))$PRC_RCAP(R,P)" if condition else ""}
        ) * SUM(RPCS_VAR(R,P,C,{arg3}), RS_FR(R,TS,S) * {arg2}) * (1+COEF_CIO(R,V,{arg1},P,C,IO)))
     )
"""
