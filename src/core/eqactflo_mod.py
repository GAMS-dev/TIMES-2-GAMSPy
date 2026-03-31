# eqactflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTFLO.MOD relationship between process activity & individual primary     *
# *              commodity flows                                                *
# *=============================================================================*
# *GaG Questions/Comments:
# *  - always created at the PRC_TS level as tied to the PCG
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqactfloMod(GamsClass):
    """Translation unit for eqactflo.mod."""

    # Instance attributes
    module_name: str = "eqactflo_mod"
    gams_source: str = "eqactflo.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec1,
            self.env.EQ,
            self.env.R_V_T,
            self.env.SWT,
            self.env.SOW,
            self.env.VAR,
            self.env.REDUCE,
        )

    def exec1(self, EQ: str, R_V_T: str, SWT: str, SOW: str, VAR: str, REDUCE: str):
        equation = rf"""
*$ONLISTING
* adjust so VAR_FLO only when not IRE (or STG)
*  EQ_ACTFLO(RTP_VINTYR(R,V,T,P),S)$((RP_FLO(R,P) + RP_IRE(R,P)) * PRC_TS(R,P,S)
   {EQ}_ACTFLO(RTP_VINTYR({R_V_T},P),S {SWT})$(PRC_TS(R,P,S) *
"""
        if REDUCE == "YES":
            equation += "(NOT RTPS_OFF(R,T,P,S)) *"

        equation += rf"""
PRC_ACT(R,P)) ..

      {VAR}_ACT(R,V,T,P,S {SOW})$RTP_VARA(R,T,P)

  =E=

* handle both regular and IRE processes
* need to ensure that said commodity handled in current timeslice
       SUM(RPC_PG(R,P,C)$RTPCS_VARF(R,T,P,C,S),
                         ({VAR}_FLO(R,V,T,P,C,S {SOW})$RP_FLO(R,P) +
                          SUM(RPC_IRE(R,P,C,IE)$RP_AIRE(R,P,IE),
                            {VAR}_IRE(R,V,T,P,C,S,IE {SOW}))$RP_IRE(R,P)
                         ) / PRC_ACTFLO(R,V,P,C)
       );
*$OFFLISTING
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)
