# eqcapvac_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAPVAC is the capacity utilization equation for vintage-simulated processes
# *   %1 - equation lim type
# *   %2 - bound type for %1
# *=============================================================================*
# * Questions/Comments:
# * - COEF_CSV is defined in COEF_CSV.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcapvacMod(GamsClass):
    """Translation unit for eqcapvac.mod."""

    # Instance attributes
    module_name: str = "eqcapvac_mod"
    gams_source: str = "eqcapvac.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        R_V_T, SWX, SWTX, VAR, SOW, VARM, SWS = (
            self.env.R_V_T,
            self.env.SWX,
            self.env.SWTX,
            self.env.VAR,
            self.env.SOW,
            self.env.VARM,
            self.env.SWS,
        )
        self.tc.enqueue(self.exec1, R_V_T, SWX, SWTX, VAR, SOW, VARM, SWS)

    def exec1(self, R_V_T, SWX, SWTX, VAR, SOW, VARM, SWS) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 EQ{self.arg1}_CAPVAC(RTP_VINTYR({R_V_T},P),S{SWX})$({SWTX}AFSV(R,T,P,S,'{self.arg2}'))..

* Activity level at timeslice S
    SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),{VAR}_ACT(R,V,T,P,TS {SOW}))$(NOT RPS_CAFLAC(R,P,S,'{self.arg2}')) +
* Flow levels when commodity-specific availabilities
    SUM((RPC_PG(R,P,C),COM_TMAP(R,COM_TYPE(CG),C)), (1/PRC_ACTFLO(R,V,P,C)) /
        (NCAP_AFCS(R,V,P,C,S)+PROD(XPT$NCAP_AFCS(R,V,P,CG,S),NCAP_AFCS(R,V,P,CG,S))$(NOT NCAP_AFCS(R,V,P,C,S))) *
        SUM(RPCS_VAR(R,P,C,TS)$TS_MAP(R,S,TS),{VAR}_FLO(R,V,T,P,C,TS {SOW})$RP_STD(R,P) +
          SUM(RPC_IRE(R,P,C,IE),{VAR}_IRE(R,V,T,P,C,TS,IE {SOW}))))$RPS_CAFLAC(R,P,S,'{self.arg2}')

  ={self.arg1}=

* process is vintaged
    SUM(MODLYEAR(K)$COEF_CSV(R,K,T,P,V),COEF_CSV(R,K,T,P,V)*COEF_AF(R,K,T,P,S,'{self.arg2}')*{VARM}_NCAP(R,K,P{SWS})$T(K)+NCAP_PASTI(R,K,P))*PRC_CAPACT(R,P)*G_YRFR(R,S)
  ;

""",
        )
