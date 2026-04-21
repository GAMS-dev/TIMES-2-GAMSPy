# equ_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQ_EXT.dsc declarations & call for actual DSC equations
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtDsc(GamsClass):
    """Translation unit for equ_ext.dsc."""

    # Instance attributes
    module_name: str = "equ_ext_dsc"
    gams_source: str = "equ_ext.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        if self.env.dsc.upper() != "YES":
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQUATIONS
    {self.env.eq}_DSCNCAP(R,ALLYEAR,P{self.env.swtd})  'Discrete capacity extension (=E=)'
    {self.env.eq}_DSCONE(R,ALLYEAR,P{self.env.swtd})   'Discrete capacity extension unity condition (=E=)'
  ;
""",
        )

        if self.env.stages == "YES":
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=f"${self.env.witspine} {self.env.sw_stvars}",
            )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  {self.env.eq}_DSCNCAP(RTP({self.env.r_t},P){self.env.swt})$PRC_DSCNCAP(R,P)..

    {self.env.var}_NCAP(R,T,P{self.env.sow}) =E=

    SUM(UNIT$NCAP_DISC(R,T,P,UNIT), {self.env.var}_DNCAP(R,T,P{self.env.sow},UNIT)*NCAP_DISC(R,T,P,UNIT)) +
    {self.env.var}_SNCAP(R,T,P{self.env.sow})$NCAP_SEMI(R,T,P);

  {self.env.eq}_DSCONE(RTP({self.env.r_t},P){self.env.swt})$(NCAP_DISC(R,T,P,'0')$PRC_DSCNCAP(R,P))..

    SUM(UNIT$NCAP_DISC(R,T,P,UNIT), {self.env.var}_DNCAP(R,T,P{self.env.sow},UNIT))  =E=  1;

""",
        )
