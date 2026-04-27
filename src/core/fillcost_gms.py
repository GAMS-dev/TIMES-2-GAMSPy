# fillcost_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLCOST : Fill cost parameters
# * Description: Dense interpolation/extrapolation of cost parameters
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1 (before year index)
# *      arg3 - control set 2 (after year index)
# *      arg4 - UNCD7 residual dimension
# *      arg5 - CKEYERS2 or EOHYEARS depending on cost parameter
# *      arg6 - Validity Qualifier restricting interpolation
# *      arg7 - Qualifier restricting backward extrapolation
# *      arg8 - Qualifier restricting forward extrapolation
# *      arg9 - Original data table
# *     arg10 - Write cache
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillcostGms(GamsClass):
    """Translation unit for fillcost.gms."""

    # Instance attributes
    module_name: str = "fillcost_gms"
    gams_source: str = "fillcost.gms"

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
        arg11: str = "",
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
        self.arg11 = arg11
        self.compile()

    def compile(self) -> None:
        self.env.set_local("src", f"{self.arg9}")
        self.env.set_local("data", f"{self.arg10}({self.arg2},{self.arg3},{self.arg5})")
        self.env.set_local("take", f"${self.arg6}")
        self.env.set_local("tmp", f"{self.arg3}{self.arg4}")

        if len(self.tc.container[self.arg9.upper()].domain) == 8:
            self.env.set_local("tmp", f"{self.arg4}")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
PARAMETER {self.arg10}({self.arg2},{self.arg3},ALLYEAR);
""",
        )

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg5=self.arg5,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg9,
            arg10=self.arg10,
            tmp=self.env.tmp,
            take=self.env.take,
            src=self.env.src,
            data=self.env.data,
            condition1=(self.arg11 == "1"),
            condition2=(self.arg11 == "2"),
        )

    def exec1(
        self: FillcostGms,
        arg1: str,
        arg2: str,
        arg3: str,
        arg5: str,
        arg7: str,
        arg8: str,
        arg9: str,
        arg10: str,
        tmp: str,
        take: str,
        src: str,
        data: str,
        condition1: bool,
        condition2: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 IF(YES,OPTION CLEAR=UNCD7;
{f"{arg1}({arg2},DATAYEAR,{arg3}) $= {arg9}({arg2},DATAYEAR,{arg3}){take};" if condition1 else ""}
{f"$SETLOCAL TAKE '' SETLOCAL SRC {arg1}" if condition1 else ""}
 UNCD7({arg2},LL--ORD(LL),{tmp}){take} $= {src}({arg2},LL,{arg3});
 LOOP(UNCD7({arg2},YEAR,{tmp}), F=0; LAST_VAL=0;
    OPTION CLEAR=MY_FIL2; MY_ARRAY(DM_YEAR)= {src}({arg2},DM_YEAR,{arg3});
* do linear interpolation
* check for nonzero
	LOOP(DM_YEAR(LL)$MY_ARRAY(DM_YEAR),
	  MY_F = MY_ARRAY(LL); Z = YEARVAL(LL);
	  IF(LAST_VAL, LAST_VAL=(MY_F-LAST_VAL)/(Z-MY_FYEAR);
	     FOR(CNT=MY_FYEAR-Z+1 TO -1, MY_FIL2({arg5}(LL+CNT)) = MY_F+LAST_VAL*CNT;);
	  ELSE F = Z; FIRST_VAL = MY_F;);
* remember the value and year
	  LAST_VAL = MY_F; MY_FYEAR=Z);
* Do back/forward extrapolate
{f" MY_FIL2({arg5}) $= MY_ARRAY({arg5});" if condition2 else ""}
    {data} $= FIRST_VAL$({arg7}(YEARVAL({arg5}) LT F)) + MY_FIL2({arg5}) + LAST_VAL$({arg8}(YEARVAL({arg5}) GT Z));
  );
);
{f" {arg1}({arg2},{arg5},{arg3}) $= {data}; OPTION CLEAR={arg10};" if not condition2 else ""}
{f"{arg10}('EMPTY',{arg3},'EMPTY')=0;" if condition2 else ""}
""",
        )
