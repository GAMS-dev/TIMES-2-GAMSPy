# eqflofr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQFLOFR relationship between total flow and the flow in a specific timeslice
# *   %1 - equation declaration type
# *   %2 - LIM type of FLO_FR
# *=============================================================================*
# * Questions/Comments:
# *  - FLO_FR must be specified on TS-level of the flow or above; value below will be ignored
# *  - fraction of flows under parent timelice supported by a parent N (or negative) FLO_FR

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqflofrMod(GamsClass):
    """Translation unit for eqflofr.mod."""

    # Instance attributes
    module_name: str = "eqflofr_mod"
    gams_source: str = "eqflofr.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red as cal_red_func

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  {self.env.eq}{self.arg1}_FLOFR(RTPC({self.env.r_t},P,C),S,L({self.arg2}){self.env.swt})$(SUM(RPCS_VAR(RP_FLO(R,P),C,TS)$TS_MAP(R,S,TS),1)$FLO_FR(R,T,P,C,S,L))..

   SUM(RTP_VINTYR(R,V,T,P),{self.env.var}_FLO(R,V,T,P,C,S{self.env.sow})$IPS(L) +
     SUM(RS_BELOW1(R,SL,S),SUM(TS_ANN(SL,TS),{self.env.var}_FLO(R,V,T,P,C,TS{self.env.sow})*(FLO_FR(RTPC,TS,'N')>0))$FLO_FR(RTPC,SL,'N') +
       SUM(RTPCS_VARF(RTPC,TS)$(FLO_FR(RTPC,S,L)>-INF$RS_FR(R,SL,TS)),
{cal_red_func(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim, def_rtp_ffcs=self.tc.defined("RTP_FFCS"), arg1="C", arg2="COM", arg3="TS", arg4="P", arg5="T")}
          )$(NOT FLO_FR(RTPC,SL,'N')))$BD(L)) * ABS(FLO_FR(RTPC,S,L))

   ={self.arg1}=

   SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(RTPC,TS))$(STOA(TS)$TS_MAP(R,S,TS)),
{cal_red_func(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim, def_rtp_ffcs=self.tc.defined("RTP_FFCS"), arg1="C", arg2="COM", arg3="TS", arg4="P", arg5="T")}
      )$(MIN(0,FLO_FR(RTPC,S,L))->BD(L));
""",
        )
