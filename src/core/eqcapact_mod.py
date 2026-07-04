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
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        self.env.set_local("pass", "")
        if self.tc.defined_assigned("RPS_CAFLAC"):
            self.env.set_local(
                "pass",
                f"{self.env.__getattr__('pass')}*(NOT RPS_CAFLAC(R,P,S,'{self.arg2}'))",
            )

        self.tc.add_gams_code(module=self, phase="init", code="SET AFS(R,T,P,S,BD) //;")
        self.tc.enqueue(
            self.exec,
            validate=(self.env.validate == "YES"),
            eq=self.env.eq,
            var=self.env.var,
            varv=self.env.varv,
            varm=self.env.varm,
            pass_var=self.env.__getattr__("pass"),
            sws=self.env.sws,
            swt=self.env.swt,
            sow=self.env.sow,
            r_v_t=self.env.r_v_t,
            rcapsbm=self.env.rcapsbm,
            rcapsub=self.env.rcapsub,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
        )

    def exec(
        self: EqcapactMod,
        validate: bool,
        eq: str,
        var: str,
        varv: str,
        varm: str,
        pass_var: str,
        sws: str,
        swt: str,
        sow: str,
        r_v_t: str,
        rcapsbm: str,
        rcapsub: str,
        arg1: str,
        arg2: str,
        arg3: str,
    ) -> None:
        if not validate:
            rhs_start = rf"""
      (SUM(MODLYEAR$COEF_CPT(R,MODLYEAR,T,P),
             COEF_CPT(R,MODLYEAR,T,P) * COEF_AF{arg3}(R,MODLYEAR,T,P,S,'{arg2}') *
             ({varm}_NCAP(R,MODLYEAR,P {sws})$T(MODLYEAR) + NCAP_PASTI(R,MODLYEAR,P)$PASTYEAR(MODLYEAR){rcapsbm})
            ) * PRC_CAPACT(R,P)
"""
        else:
            rhs_start = rf"""
        (COEF_AF(R,T,T,P,S,'{arg2}') * PRC_CAPACT(R,P) * {var}_CAP(R,T,P {sow})
"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* COEF_AFs are always at PRC_TS or above, can be directly used for testing:
{"LOOP(V,AFS(RTP_VARA(R,T,P),S,BD)$COEF_AF(R,V,T,P,S,BD)=YES); AFS(RTPS_OFF,BD) = NO;" if arg1 == "L" else ""}
{eq}{arg1}_CAPACT(RTP_VINTYR({r_v_t},P),S {swt})$(AFS(R,T,P,S,'{arg2}') {pass_var}) ..

* normal processes
      SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),{var}_ACT(R,V,T,P,TS {sow}))$(NOT RP_STG(R,P))
      +
* storage: parent timeslice fraction of the number of storage cycles in a year
      SUM(PRC_TS(R,P,TS)$RS_FR(R,TS,S),({var}_ACT(R,V,T,P,TS {sow})+VAR_STS(R,V,T,P,TS,'{arg2}'))*RS_FR(R,TS,S)*EXP(PRC_SC(R,P))/RS_STGPRD(R,TS))$RP_STG(R,P)

  ={arg1}=

      (

{rhs_start}
        )$(NOT PRC_VINT(R,P)) +

* process is vintaged
        (COEF_AF{arg3}(R,V,T,P,S,'{arg2}') * COEF_CPT(R,V,T,P) * PRC_CAPACT(R,P) *
         ({varv}_NCAP(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V){rcapsub}))$PRC_VINT(R,P)
      ) *

* UR 10/05/00
* capacity of storage process fully available in each time slice
      POWER(G_YRFR(R,S),1-1$RP_STG(R,P))
  ;
""",
        )
