# eqactbnd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTBND limits the activity of vintage processes or higher TS-level bounds
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *=============================================================================*
# * Questions/Comments:
# *  - ACT_BND ts restricted to the PRC_TS level or above
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqactbndMod(GamsClass):
    """Translation unit for eqactbnd.mod."""

    # Instance attributes
    module_name: str = "eqactbnd_mod"
    gams_source: str = "eqactbnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
        arg3: str,
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*V0.5b 980902 - avoid equations if LO=0/UP=INF
*$ONLISTING
* [UR] 21.07.2003 tightended control for generation of equation to RTP_VARA
  {self.env.eq}{self.arg1}_ACTBND(RTP_VARA({self.env.r_t},P),S {self.env.swt})$((RPS_PRCTS(R,P,S)*(PRC_VINT(R,P)+(NOT PRC_TS(R,P,S)))${self.arg3})$ACT_BND(R,T,P,S,'{self.arg2}'))..

* sum over all possible at process TS-level
       SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),
* sum all the existing activities
           SUM(RTP_VINTYR(R,V,T,P), {self.env.var}_ACT(R,V,T,P,TS{self.env.sow}))
       )

  ={self.arg1}=

       ACT_BND(R,T,P,S,'{self.arg2}')
  ;
*$OFFLISTING

""",
        )
