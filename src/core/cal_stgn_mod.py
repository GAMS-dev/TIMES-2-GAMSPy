# cal_stgn_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_STG the code associated with the storage flows in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# *   arg2 - 'OUT/IN' for consumption/production
# *   arg3 - STG_EFF for output
# *   arg4 - STG_EFF for output
# *   arg5 - for day-night storage indicator
# *=============================================================================*
# * Questions/Comments:
# * arg6 - NCAP_PKCNT multiplier

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CalStgnMod(GamsClass):
    """Translation unit for cal_stgn.mod."""

    # Instance attributes
    module_name: str = "cal_stgn_mod"
    gams_source: str = "cal_stgn.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.compile()

    def compile(self):
        return rf"""
*V05c 980923 - check that commodity not just capacity related
  SUM((TOP(RPC_STG(R,P,C),'{self.arg1}'),RPCS_VAR(R,P,C,TS))${self.arg5},
       SUM(RTP_VNTBYR(R,T,P,V),
          ({self.env.var}_S{self.arg1}(R,V,T,P,C,TS {self.env.sow}){self.arg3}-{self.arg4}{self.env.var}_S{self.arg2}(R,V,T,P,C,TS {self.env.sow})$RPC_STGN(R,P,C,'{self.arg2}')){self.arg6})$(NOT RPC_STGN(R,P,C,'{self.arg1}')) *
* equation coarser than variable or finer than variable
        RS_FR(R,S,TS)
     ) +
"""
