# preshape_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2024 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * PRESHAPE : Prepare SHAPE parameters for preprocessing
# * Description: Interpolation of X parameter on user request
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1
# *      arg3 - control set 2
# *      arg4 - residual dimension for control tuple
# *      arg5 - MODLYEAR or MILESTONYR depending on parameter
# *      arg6 - temporary table of control tuples
# *      arg7 - P/C
# *******************************************************************************


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PreshapeGms(GamsClass):
    """Translation unit for preshape.gms."""

    # Instance attributes
    module_name: str = "preshape_gms"
    gams_source: str = "preshape.gms"

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
        arg7: str = "",
        arg8: str = "",
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
        self.arg7 = arg7
        self.arg8 = arg8
        self.compile()

    def compile(self) -> None:
        self.env.set_local("tail", f",{self.arg3}")
        self.env.set_local("def", "10")
        if not len(self.arg3):
            self.env.set_local("tail", "")

        if len(self.arg8):
            self.env.set_local("def", f"{self.arg8}")

        self.tc.enqueue(
            self.exec1,
            tail=self.env.tail,
            arg1=self.arg1,
            arg2=self.arg2,
            arg6=self.arg6,
            arg4=self.arg4,
        )
        self.tc.enqueue(
            self.main_loop,
            tail=self.env.tail,
            dflbl=self.env.dflbl,
            DEF=self.env.get("def"),
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
        )

    def exec1(
        self: PreshapeGms,
        tail: str,
        arg1: str,
        arg2: str,
        arg6: str,
        arg4: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR = {arg6};
{arg6}({arg2},LL--ORD(LL){tail}{arg4}) $= {arg1}({arg2},LL{tail});
""",
        )

    def main_loop(
        self: PreshapeGms,
        tail: str,
        dflbl: str,
        DEF: str,  # def is a keyword
        arg1: str,
        arg2: str,
        arg4: str,
        arg5: str,
        arg6: str,
        arg7: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
LOOP({arg6}({arg2},'{dflbl}'{tail}{arg4}),
  DFUNC={DEF}; DFUNC $= MOD(ROUND({arg1}({arg2},'{dflbl}'{tail})),1000);
  MY_ARRAY(DM_YEAR) = {arg1}({arg2},DM_YEAR{tail});
  IF(DFUNC NE 10, F=0; LAST_VAL=0;
* do interpolate
   LOOP(DM_YEAR$MY_ARRAY(DM_YEAR),          {"! check for nonzero (including EPS)" if False else ""}
     MY_F = MY_ARRAY(DM_YEAR); Z = YEARVAL(DM_YEAR);
     IF(LAST_VAL, {arg1}({arg2},{arg5}{tail})$((Z>YEARVAL({arg5}))$(YEARVAL({arg5})>MY_FYEAR)) = LAST_VAL;
     ELSE F = Z; FIRST_VAL = MY_F);
     LAST_VAL = ROUND(MY_F); MY_FYEAR=Z;);  {"! remember the value and year" if False else ""}
  ELSE FIRST_VAL = 0; MY_FYEAR = 0;         {"! intra-period I/E" if False else ""}
   LOOP(MY_FIL(LL)$MY_ARRAY(MY_FIL),        {"! check for data values" if False else ""}
     MY_F = MY_ARRAY(LL); Z = YEARVAL(MY_FIL); F = FIL2(MY_FIL);
     IF(MY_FYEAR<F, IF(F>MIN(FIRST_VAL,Z), LAST_VAL = MY_F; FIRST_VAL = F;);
     {arg1}({arg2},{arg5}(LL+(F-YEARVAL(LL))){tail})$(NOT MY_ARRAY({arg5})) = LAST_VAL);
     LAST_VAL = MY_F; MY_FYEAR=Z;);         {"! remember the value and year" if False else ""}
     DFUNC=0;
   );
   IF(ROUND(DFUNC-5,-1)=10,
     {arg1}({arg2},{arg5}{tail})${arg7} $= FIRST_VAL$(YEARVAL({arg5})<F)$(E({arg5}) GE F) + LAST_VAL$(YEARVAL({arg5})>Z)$(B({arg5}) LE Z);
     DFUNC=DFUNC-10);
   IF(DFUNC GE 2,
* Do back/forward extrapolate
     IF(DFUNC=4, Z = INF; ELSEIF DFUNC=5, F = 0; ELSEIF DFUNC=(2-F), LAST_VAL=EPS; Z=0);
     {arg1}({arg2},{arg5}{tail})${arg7} $= FIRST_VAL$(YEARVAL({arg5})<F) + LAST_VAL$(YEARVAL({arg5})>Z);
   );
  );

""",
        )
