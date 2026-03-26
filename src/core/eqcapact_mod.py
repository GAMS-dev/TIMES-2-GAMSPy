# eqcapact_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAPACT is the capacity utilization equation
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT is defined in COEF_CPT.MOD
# *  - COEF_AF established by applying SHAPE in COEF_CPT.MOD
# *  - Commodity-specific AF handled by EQ(l)_CAFLAC (VDA extension)
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcapactMod(GamsClass):
    """Translation unit for eqcapact.mod."""

    # Instance attributes
    module_name: str = "eqcapact_mod"
    gams_source: str = "eqcapact.mod"

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
        self.env.set_local("PASS", "")
        if self.tc.defined("RPS_CAFLAC"):
            self.env.set_local(
                "PASS", f"{self.env.PASS}*(NOT RPS_CAFLAC(R,P,S,'{self.arg2}'))"
            )

        self.tc.add_gams_code(module=self, phase="init", code="SET AFS(R,T,P,S,BD) //;")

        if self.arg1 == "L":
            self.tc.enqueue(self.exec1)

        EQ, R_V_T, SWT, PASS, VALIDATE, VARM, SWS, RCAPSBM, VAR, SOW, VARV, RCAPSUB = (
            self.env.EQ,
            self.env.R_V_T,
            self.env.SWT,
            self.env.PASS,
            self.env.VALIDATE,
            self.env.VARM,
            self.env.SWS,
            self.env.RCAPSBM,
            self.env.VAR,
            self.env.SOW,
            self.env.VARV,
            self.env.RCAPSUB,
        )
        self.tc.enqueue(
            self.exec2,
            EQ,
            R_V_T,
            SWT,
            PASS,
            VALIDATE,
            VARM,
            SWS,
            RCAPSBM,
            VAR,
            SOW,
            VARV,
            RCAPSUB,
        )

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
LOOP(V,AFS(RTP_VARA(R,T,P),S,BD)$COEF_AF(R,V,T,P,S,BD)=YES); AFS(RTPS_OFF,BD) = NO;
""",
        )

    def exec2(
        self,
        EQ: str,
        R_V_T: str,
        SWT: str,
        PASS: str,
        VALIDATE: str,
        VARM: str,
        SWS: str,
        RCAPSBM: str,
        VAR: str,
        SOW: str,
        VARV: str,
        RCAPSUB: str,
    ):
        lhs = rf"""
{EQ}{self.arg1}_CAPACT(RTP_VINTYR({R_V_T},P),S {SWT})$(AFS(R,T,P,S,'{self.arg2}') {PASS}) ..

* normal processes
      SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),{VAR}_ACT(R,V,T,P,TS {SOW}))$(NOT RP_STG(R,P))
      +
* storage: parent timeslice fraction of the number of storage cycles in a year
      SUM(PRC_TS(R,P,TS)$RS_FR(R,TS,S),({VAR}_ACT(R,V,T,P,TS {SOW})+VAR_STS(R,V,T,P,TS,'{self.arg2}'))*RS_FR(R,TS,S)*EXP(PRC_SC(R,P))/RS_STGPRD(R,TS))$RP_STG(R,P)

  ={self.arg1}=


"""

        if VALIDATE == "YES":
            rhs = rf"""
(COEF_AF(R,T,T,P,S,'{self.arg2}') * PRC_CAPACT(R,P) * {VAR}_CAP(R,T,P {SOW})
        )$(NOT PRC_VINT(R,P)) +

* process is vintaged
        (COEF_AF{self.arg3}(R,V,T,P,S,'{self.arg2}') * COEF_CPT(R,V,T,P) * PRC_CAPACT(R,P) *
         ({VARV}_NCAP(R,V,P {SWS})$T(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V){RCAPSUB}))$PRC_VINT(R,P)
      ) *

* UR 10/05/00
* capacity of storage process fully available in each time slice
      POWER(G_YRFR(R,S),1-1$RP_STG(R,P))

  ;
"""
        else:
            rhs = rf"""
(SUM(MODLYEAR$COEF_CPT(R,MODLYEAR,T,P),
             COEF_CPT(R,MODLYEAR,T,P) * COEF_AF{self.arg3}(R,MODLYEAR,T,P,S,'{self.arg2}') *
             ({VARM}_NCAP(R,MODLYEAR,P {SWS})$T(MODLYEAR) + NCAP_PASTI(R,MODLYEAR,P)$PASTYEAR(MODLYEAR){RCAPSBM})
            ) * PRC_CAPACT(R,P)
"""
        self.tc.add_gams_code(module=self, phase="run", code=lhs + rhs)
