# fillvint_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLVINT : Optional weighting of vintaged attributes
# *   arg1 - table name
# *   arg2 - Control set 1
# *   arg3 - Control set 2
# *   arg4 - Name for temporary cache
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillvintGms(GamsClass):
    """Translation unit for fillvint.gms."""

    # Instance attributes
    module_name: str = "fillvint_gms"
    gams_source: str = "fillvint.gms"

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
        prc_simv_defined = self.tc.defined("PRC_SIMV")
        if len(self.arg4) == 0:
            self.tc.enqueue(
                self.initialization,
                vintopteq2=self.env.vintopt == "2",
                prc_simv_defined=prc_simv_defined,
            )
        else:  # fill
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"PARAMETER {self.arg4}({self.arg2},{self.arg3},ALLYEAR);",
            )
            self.tc.enqueue(
                self.fill,
                arg1=self.arg1,
                arg2=self.arg2,
                arg3=self.arg3,
                arg4=self.arg4,
                prc_simv_defined=prc_simv_defined,
            )

    def initialization(
        self: FillvintGms,
        vintopteq2: bool,
        prc_simv_defined: bool,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Initialization
  OPTION CLEAR=PRC_YMIN,CLEAR=PASTSUM;
{"PRC_SIMV(PRC_VINT(R,P)) = NOT PRC_MAP(R,'STG',P);" if vintopteq2 else ""}
{"PRC_SIMV(R,P)$PRC_MAP(R,'STG',P) = NO; PRC_VINT(PRC_SIMV) = YES;" if prc_simv_defined else ""}
* Make sure that all PRC_VINT have first leading V in RTP:
  LOOP(T(LL),RVP(R,V(LL-LEAD(T)),P)$((NOT RVP(R,V,P))$RVP(R,T,P)$PRC_VINT(R,P)) = YES);
{"RTP(RVP(R,V,P)) $=PRC_SIMV(R,P);" if prc_simv_defined else ""}
""",
        )

    def fill(
        self: FillvintGms,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        prc_simv_defined: bool,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(CARD(PASTSUM)=0,
    PASTSUM(RTP(R,T,P))$PRC_VINT(R,P) =
      MIN(1,(MAX(YEARVAL(T)-(LEAD(T)-1)/2,B(T)+MAX(NCAP_ILED(RTP),(D(T)+NCAP_ILED(RTP)-NCAP_TLIFE(RTP))/2)) -
             (YEARVAL(T)-LEAD(T))) / LEAD(T)));
  TRACKP(PRC_VINT) = YES;
{"TRACKP(PRC_SIMV) = NO;" if prc_simv_defined else ""}
* Weighted average of vintages T and T-1
  LOOP((T(LL),V(LL-LEAD(LL))),
    {arg4}({arg2},{arg3},T)$({arg1}({arg2},T,{arg3})$TRACKP(R,P)) = {arg1}({arg2},T,{arg3})*PASTSUM(R,T,P)+{arg1}({arg2},V,{arg3})*(1-PASTSUM(R,T,P)));
  {arg1}({arg2},T,{arg3}) $= {arg4}({arg2},{arg3},T);
  OPTION CLEAR={arg4},CLEAR=TRACKP;
""",
        )
