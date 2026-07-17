# fillparm_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLPARM : Interpolation/extrapolation of user data
# * Description: Default interpolation/extrapolation if no control option given
# *              Non-default interpolation/extrapolation according to user option
# *              DFUNC = -1-> no interpolation, 0-> default action,
# *              DFUNC = +1-> interp., 2->interp.+EPS, 3->interp.+extrap.
# *              DFUNC >999 -> exponential interpolation beyond year DFUNC
# * Parameters:
# *      args1 - table name
# *      args2 - control set 1
# *      args3 - control set 2
# *      args4 - UNCD7 residual dimension
# *      args5 - MODLYEAR or MILESTONYR depending on parameter
# *      args6 - RTP controlling the assignment to the MODLYEARs
# *      args7 - Selective test for control option (normally GE 0)
# *      args8 - Optional name for temporary write cache
# *      args9 -
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillparmGms(GamsClass):
    """Translation unit for fillparm.gms."""

    # Instance attributes
    module_name: str = "fillparm_gms"
    gams_source: str = "fillparm.gms"

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
        arg9: str = "",
        arg10: str = "",
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
        self.arg9 = arg9
        self.arg10 = arg10
        self.compile()

    def compile(self) -> None:
        self.env.set_local("data", f"{self.arg1}({self.arg2},{self.arg5},{self.arg3})")
        self.env.set_local("item", f"{self.arg1}({self.arg2},{self.arg5},{self.arg3})")
        self.env.set_local("add", "")
        if len(self.arg8):
            self.env.set_local(
                "data", f"{self.arg8}({self.arg2},{self.arg3},{self.arg5})"
            )
            self.env.set_local("item", f"MY_FIL2({self.arg5})")
            self.env.set_local("add", f"+MY_FIL2({self.arg5})")
        if self.arg8 != self.arg9:
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=f"PARAMETER {self.arg8}({self.arg2},{self.arg3},ALLYEAR);",
            )
        self.tc.enqueue(
            fillparm,
            self,
            dflbl=self.env.dflbl,
            item=self.env.item,
            data=self.env.data,
            add=self.env.add,
            reset=self.env.reset,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg8,  # the arg9=arg8 is on purpose to have the execution part not fail
        )


def fillparm(
    module: GamsClass,
    dflbl: str,
    item: str,
    data: str,
    add: str,
    reset: str,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg7: str,
    arg8: str,
    arg9: str,
) -> None:
    if not arg8 == arg9:
        raise Exception(
            f" {arg8} <> {arg9} requires parameter declaration and can't be used during execution only"
        )

    # TODO: Add setlocal as local Python variables
    module.tc.add_gams_code(
        module=module,
        phase="run",
        code=rf"""
* conditional interpolation flag
 IF(NOT G_NOINTERP, OPTION CLEAR = UNCD7;
   LOOP(DATAYEAR, UNCD7({arg2},{arg3}{arg4})${arg1}({arg2},DATAYEAR,{arg3}) = YES;);
   LOOP(UNCD7({arg2},{arg3}{arg4}), DFUNC = ROUND({arg1}({arg2},'{dflbl}',{arg3}));
    IF(DFUNC {arg7}, OPTION CLEAR=MY_FIL2; CNT = (DFUNC LE 999);
      MY_ARRAY(DM_YEAR) = {arg1}({arg2},DM_YEAR,{arg3}); LAST_VAL=0; F = 0; Z = 0;
* do interpolate
	LOOP(DM_YEAR$MY_ARRAY(DM_YEAR),                    {"! check for nonzero (including EPS)" if False else ""}
           MY_F = MY_ARRAY(DM_YEAR); Z = YEARVAL(DM_YEAR);
           IF(LAST_VAL,
             IF(CNT OR (Z LE DFUNC),             {"! linear interpolation" if False else ""}
                {item}$((Z GT YEARVAL({arg5}))$(YEARVAL({arg5}) GT MY_FYEAR))
			= LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(YEARVAL({arg5})-MY_FYEAR); {"! not the first one" if False else ""}
             ELSE                                {"! exponential function" if False else ""}
                {item}$((Z GT YEARVAL({arg5}))$(YEARVAL({arg5}) GT MY_FYEAR))
			= LAST_VAL*POWER(1+MY_F,YEARVAL({arg5})-MY_FYEAR)+EPS;
                MY_F = LAST_VAL*POWER(1+MY_F,Z-MY_FYEAR)+EPS;
                {arg1}({arg2},DM_YEAR,{arg3}) = MY_F;);      {"! overwrite old data" if False else ""}
           ELSE F = Z; FIRST_VAL = MY_F;);
           LAST_VAL = MY_F; MY_FYEAR=Z;);        {"! remember the value and year" if False else ""}
      IF(DFUNC GT 1,
        IF(CNT,DFUNC=MOD(DFUNC,10);
         IF(DFUNC EQ 2, FIRST_VAL = EPS; LAST_VAL = EPS; ELSEIF DFUNC EQ 4, Z = INF; ELSEIF DFUNC EQ 5, F = 0)));
      IF((DFUNC NE 1),
* Do back/forward extrapolate, or fill in with EPS
       {data}${arg6} $= FIRST_VAL$(YEARVAL({arg5}) LT F) {add} + LAST_VAL$(YEARVAL({arg5}) GT Z);
       {f"ELSE {data}${arg6} $= {item};" if len(arg8) else ""}
   )));
* Reset OPT and add DATA
  {arg1}({arg2},'{dflbl}',{arg3})${arg1}({arg2},'{dflbl}',{arg3}) = MIN({reset},{arg1}({arg2},'{dflbl}',{arg3}));
  {f"{arg1}({arg2},{arg5},{arg3}) $= {data}; OPTION KILL = {arg8};" if len(arg8) else ""}
    );
""",
    )
