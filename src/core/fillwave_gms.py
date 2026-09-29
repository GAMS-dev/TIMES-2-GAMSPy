# fillwave_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************
# * FILLWAVE : Fill parameters via weighted centered averaging
# * arg1 - table name
# * arg2 - index set (after year index)
# *******************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillwaveGms(GamsClass):
    """Translation unit for fillwave.gms."""

    # Instance attributes
    module_name: str = "fillwave_gms"
    gams_source: str = "fillwave.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("tmp", "OBJ_DISC(R,LL,CUR)/COEF_PVT(R,T)")
        if self.env.ctst == "":
            self.env.set_scoped("tmp", "1/D(T)")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
SET REG_{self.arg2}(REG,{self.arg2});
""",
        )

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            tmp=self.env.tmp,
        )

    def exec1(self: FillwaveGms, arg1: str, arg2: str, arg3: str, tmp: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(CARD(VDA_DISC)=0,VDA_DISC(R,MIYR_1)=1; LOOP((G_RCUR(R,CUR),T(TT+1)),VDA_DISC(R,Y_EOH(LL))$PERIODYR(T,LL)={tmp}));
  OPTION REG_{arg2} <= {arg1}; DONE=SMAX(T,M(T));
  LOOP(REG_{arg2}(R,{arg2}), OPTION CLEAR=FIL2;
    MY_ARRAY(DM_YEAR)={arg1}(R,DM_YEAR,{arg2}); MY_F=0; Z=0;
* interpolate densely
    LOOP(DM_YEAR(LL)$MY_ARRAY(LL),
      LAST_VAL=MY_F; F=Z; MY_F=MY_ARRAY(LL); Z=YEARVAL(LL);
      IF(LAST_VAL, FOR(CNT=F-Z+1 TO -1, FIL2(LL+CNT)=MY_F+(MY_F-LAST_VAL)/(Z-F)*CNT)));
    IF(DONE=Z${arg3},FIL2(Y_EOH)$(YEARVAL(Y_EOH)>Z)=MY_F);
* weighted centered average
    {arg1}(R,T,{arg2}) = SUM(PERIODYR(T,Y_EOH(LL)),(MY_ARRAY(LL)+FIL2(LL))*VDA_DISC(R,LL)));
""",
        )
