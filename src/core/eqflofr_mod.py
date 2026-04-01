# eqflofr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQIREBND limits the activity of inter-regional exchange process
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - BND ts restricted to the PRC_TS level or above?
# *UR* /12/09/99 commodity names can be different in the two regions
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        if self.env.CAL_RED == "cal_red.red":
            from core.cal_red_red import cal_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored as cal_red_func

        self.tc.enqueue(
            self.exec1,
            self.env.EQ,
            self.env.R_T,
            self.arg2,
            self.env.SWT,
            self.env.VAR,
            self.env.SOW,
            cal_red_func,
            self.arg1,
        )

    def exec1(
        self,
        EQ: str,
        R_T: str,
        arg2: str,
        SWT: str,
        VAR: str,
        SOW: str,
        cal_red_func: Callable,
        arg1: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {EQ}{arg1}_FLOFR(RTPC({R_T},P,C),S,L({arg2}){SWT})$(SUM(RPCS_VAR(RP_FLO(R,P),C,TS)$TS_MAP(R,S,TS),1)$FLO_FR(R,T,P,C,S,L))..

   SUM(RTP_VINTYR(R,V,T,P),{VAR}_FLO(R,V,T,P,C,S{SOW})$IPS(L) +
     SUM(RS_BELOW1(R,SL,S),SUM(TS_ANN(SL,TS),{VAR}_FLO(R,V,T,P,C,TS{SOW})*(FLO_FR(RTPC,TS,'N')>0))$FLO_FR(RTPC,SL,'N') +
       SUM(RTPCS_VARF(RTPC,TS)$(FLO_FR(RTPC,S,L)>-INF$RS_FR(R,SL,TS)),
$          {cal_red_func("C", "COM", "TS", "P", "T")}
          )$(NOT FLO_FR(RTPC,SL,'N')))$BD(L)) * ABS(FLO_FR(RTPC,S,L))

   ={arg1}=

   SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(RTPC,TS))$(STOA(TS)$TS_MAP(R,S,TS)),
$      {cal_red_func("C", "COM", "TS", "P", "T")}
      )$(MIN(0,FLO_FR(RTPC,S,L))->BD(L));
""",
        )
