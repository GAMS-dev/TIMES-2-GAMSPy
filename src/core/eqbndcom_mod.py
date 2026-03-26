# eqbndcom_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCOMBND limits the total NET/PRD of a commodity at a level above COM_TS
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *   %4 - NET/PRD indicator
# *=============================================================================*
# *GaG Questions/Comments:
# * V0.5c added
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqbndcomMod(GamsClass):
    """Translation unit for eqbndcom.mod."""

    # Instance attributes
    module_name: str = "eqbndcom_mod"
    gams_source: str = "eqbndcom.mod"

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
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        EQ, R_T, SWT, VAR, SOW = (
            self.env.EQ,
            self.env.R_T,
            self.env.SWT,
            self.env.VAR,
            self.env.SOW,
        )
        self.tc.enqueue(self.exec1, EQ, R_T, SWT, VAR, SOW)

    def exec1(self, EQ: str, R_T: str, SWT: str, VAR: str, SOW: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*$ONLISTING
  {EQ}{self.arg1}_BND{self.arg4}(RTC({R_T},C),S {SWT})$((RCS_COMTS(R,C,S)$(NOT COM_TS(R,C,S))${self.arg3})$COM_BND{self.arg4}(R,T,C,S,'{self.arg2}'))..
* sum over all possible commodity flow at/below TS-level
       SUM(RTCS_VARC(R,T,C,TS)$TS_MAP(R,S,TS), {VAR}_COM{self.arg4}(R,T,C,TS {SOW}))

  ={self.arg1}=

       COM_BND{self.arg4}(R,T,C,S,'{self.arg2}')
  ;
*$OFFLISTING
  """,
        )
