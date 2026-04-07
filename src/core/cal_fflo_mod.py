# cal_fflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_FFLO the code associated with the flow variable in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# **  arg2 - 'I/O' for invest/decommission checks (no longer used)
# *   arg3 - * Peak multiplier
# *   arg4 - Peak by flow contribution
# *=============================================================================*
# *GaG Questions/Comments:
# *  - VAR_FLOs according to whether c-in-PCG otherwise RPS_S1
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cal_red_red import cal_red_red

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CalFfloMod(GamsClass):
    """Translation unit for cal_fflo.mod."""

    # Instance attributes
    module_name: str = "cal_fflo_mod"
    gams_source: str = "cal_fflo.mod"

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

    def compile(self):
        if not self.env.reduce == "YES":
            self.env.set_scoped("shp1", "")
            self.env.set_scoped("shg", ",P,CG3,C")
            if self.tc.defined("RTP_FFCS"):
                self.env.set_scoped(
                    "shp1", f"*{self.env.shff}S(R,V{self.env.shg}{self.env.sow}))"
                )
            self.env.set_scoped(
                "shp1",
                f"*({self.env.shff}X(R,V,T{self.env.shg})$PRC_VINT(R,P)){self.env.shp1}",
            )
            return_str = rf"""
*V05c 980923 - check that commodity not just capacity related
         SUM(TOP(RP_FLO(R,P),C,'{self.arg1}')$(NOT RPC_EMIS(R,P,C)),
             SUM((RTP_VNTBYR(R,T,P,V),RTPCS_VARF(R,T,P,C,TS)),
* equation coarser than variable or equation finer than variable
* consider COM_TS shape too, so both TS_MAP and RS_BELOW embedded
               {self.env.var}_FLO(R,V,T,P,C,TS {self.env.sow}) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {self.arg3}){self.arg4}
         ) +
* Handle RPC_EMIS flows separately; They cannot be NOFLO
         SUM(TOP(RPC_EMIS(RP_FLO(R,P),C),'{self.arg1}'){self.arg4},
           SUM((FS_EMIT(R,P,C,CG3,COM2),RTPCS_VARF(R,T,P,COM2,TS))$RS_FR(R,S,TS),
             SUM(RTP_VNTBYR(R,T,P,V),{self.env.var}_FLO(R,V,T,P,COM2,TS {self.env.sow}) *
                COEF_PTRAN(R,V,P,CG3,COM2,C,TS) {self.env.shp1} {self.arg3}) *
             RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM2,S,TS)))) +
"""
            return return_str
        else:  # REDUCE
            include_cal_red_1 = cal_red_red("C", "COM", "TS", "P", "T", "", "T")
            include_cal_red_2 = cal_red_red(
                "C",
                "COM",
                "TS",
                "P",
                "T",
                "",
                "V",
                "SUM",
                "RTP_VNTBYR(R,T,P,V),",
                f"{self.arg3}",
            )
            return_str = rf"""
* [UR] model reduction REDUCE is set in *.run
* Sum over non-vintaged processes
         SUM(TOP(RP_FLO(R,P),C,'{self.arg1}')$(NOT PRC_VINT(R,P)),
             SUM(RTPCS_VARF(R,V(T),P,C,TS),
{include_cal_red_1}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {self.arg3}){self.arg4}
         ) +

* Sum over vintaged processes
         SUM((TOP(PRC_VINT(RP_FLO(R,P)),C,'{self.arg1}'),RTPCS_VARF(R,T,P,C,TS)){self.arg4},
{include_cal_red_2}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))
         ) +
"""
            return return_str
