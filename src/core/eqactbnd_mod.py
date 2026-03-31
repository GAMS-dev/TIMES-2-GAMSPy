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

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self.tc.enqueue(
            self.exec1,
            self.arg1,
            self.arg2,
            self.arg3,
            self.env.EQ,
            self.env.R_T,
            self.env.SWT,
            self.env.SOW,
            self.env.VAR,
        )

    def exec1(
        self,
        arg1: str,
        arg2: str,
        arg3: str,
        EQ: str,
        R_T: str,
        SWT: str,
        SOW: str,
        VAR: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*V0.5b 980902 - avoid equations if LO=0/UP=INF
*$ONLISTING
* [UR] 21.07.2003 tightended control for generation of equation to RTP_VARA
  {EQ}{arg1}_ACTBND(RTP_VARA({R_T},P),S {SWT})$((RPS_PRCTS(R,P,S)*(PRC_VINT(R,P)+(NOT PRC_TS(R,P,S)))${arg3})$ACT_BND(R,T,P,S,'{arg2}'))..

* sum over all possible at process TS-level
       SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),
* sum all the existing activities
           SUM(RTP_VINTYR(R,V,T,P), {VAR}_ACT(R,V,T,P,TS{SOW}))
       )

  ={arg1}=

       ACT_BND(R,T,P,S,'{arg2}')
  ;
*$OFFLISTING

""",
        )
