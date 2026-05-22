# eqstgflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGFLO limits the flow of storage process at flow TS-level or higher
# *   arg1 - IN/OUT
# *   arg2 - equation declaration type
# *   arg3 - bound type for arg2
# *   arg4 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Bound TS restricted to the PRC_TS level or above
# *  - avoid equations if LO=0/UP=INF

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgfloMod(GamsClass):
    """Translation unit for eqstgflo.mod."""

    # Instance attributes
    module_name: str = "eqstgflo_mod"
    gams_source: str = "eqstgflo.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("tmp", "(NOT PRC_MAP(R,'NST',P))+")
        if self.arg1 == "OUT":
            self.env.set_scoped("tmp", "NOT")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  {self.env.eq}{self.arg2}_STG{self.arg1}(RTPC({self.env.r_t},P,C),S {self.env.swt})$((STG{self.arg1}_BND(R,T,P,C,S,'{self.arg3}') NE {self.arg4})$(PRC_VINT(R,P)+(NOT RPCS_VAR(R,P,C,S)))
                                         $RPS_PRCTS(R,P,S)$RPC_STG(R,P,C)$STG{self.arg1}_BND(R,T,P,C,S,'{self.arg3}')) ..

* sum over all possible flow variables at process TS-level
       SUM(RPCS_VAR(R,P,C,TS)$(RS_FR(R,S,TS) * ({self.env.tmp} PRC_NSTTS(R,P,TS))),
           SUM(RTP_VINTYR(R,V,T,P),{self.env.var}_S{self.arg1}(R,V,T,P,C,TS {self.env.sow})*RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))))

  ={self.arg2}=

       STG{self.arg1}_BND(R,T,P,C,S,'{self.arg3}')
  ;
""",
        )
