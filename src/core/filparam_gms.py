# filparam_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILPARAM : Fill parameter
# * Description: Dense interpolation/extrapolation of parameters
# * Parameters:
# *      %1 - table name
# *      %2 - control set 1 (before year index)
# *      %3 - control set 2 (after year index)
# *      %4 - UNCD7 residual dimension
# *      %5 - Source data years (e.g. ALLYEAR, DM_YEAR)
# *      %6 - Target data years (e.g. ALLYEAR, MILESTONYR)
# *      %7 - Qualifier restricting backward extrapolation
# *      %8 - Qualifier restricting forward extrapolation
# *      %9 - Default interpolation option
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FilparamGms(GamsClass):
    """Translation unit for filparam.gms."""

    # Instance attributes
    module_name: str = "filparam_gms"
    gams_source: str = "filparam.gms"

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
        self.tc.enqueue(self.exec1, dflbl=self.env.dflbl)

    def exec1(self: FilparamGms, dflbl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=filparam_gms(
                arg1=self.arg1,
                arg2=self.arg2,
                arg3=self.arg3,
                arg4=self.arg4,
                arg5=self.arg5,
                arg6=self.arg6,
                arg7=self.arg7,
                arg8=self.arg8,
                arg9=self.arg9,
                arg10=self.arg10,
                dflbl=dflbl,
            ),
        )


def filparam_gms(
    *,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg7: str,
    arg8: str,
    arg9: str,
    arg10: str,
    dflbl: str,
) -> str:
    src = arg1
    tail1 = arg3
    tail2 = f",{arg3}"

    if arg3 == "":
        tail1 = "''"
        tail2 = ""

    if arg10 == "":
        code_block = (
            f"IF(YES, OPTION CLEAR = UNCD7; "
            f"LOOP(({arg2}{arg5}{tail2})${src}({arg2}{arg5}{tail2}), "
            f"UNCD7({arg2}{tail1}{arg4}) = YES));"
        )
    else:
        code_block = (
            f"IF(YES, OPTION CLEAR = UNCD7; "
            f"UNCD7({arg2}LL--ORD(LL),{tail1}{arg4})${src}({arg2}LL{tail2}) = YES);"
        )

    # TODO: EOLINE does not work -> therefore comments starting with ! in {} if False else ""
    code_block += rf"""
LOOP(UNCD7({arg2}{arg10}{tail1}{arg4}), F=0; Z=INF; MY_FYEAR=9999;
DFUNC = ROUND({src}({arg2}'{dflbl}'{tail2}));
{f"IF(NOT DFUNC, DFUNC = {arg9});" if arg9 != "" else ""}
IF(DFUNC GE 0,
MY_ARRAY({arg5}) = {src}({arg2}{arg5}{tail2}); MY_ARRAY('{dflbl}')=0;
    LOOP({arg5}$MY_ARRAY({arg5}),              {"! check for nonzero (including EPS)" if False else ""}
    MY_F = MY_ARRAY({arg5}); Z = YEARVAL({arg5});
    IF(Z > MY_FYEAR+1,               {"! linear interpolation" if False else ""}
        {arg1}({arg2}{arg6}{tail2})$((Z GT YEARVAL({arg6}))$(YEARVAL({arg6}) GT MY_FYEAR))
        = LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(YEARVAL({arg6})-MY_FYEAR); {"! not the first one" if False else ""}
    ELSEIF Z LT MY_FYEAR, F=Z; FIRST_VAL = MY_F);
    LAST_VAL = MY_F; MY_FYEAR=Z);    {"! remember the value and year" if False else ""}
IF(DFUNC GT 1, DFUNC=MOD(DFUNC,10);
    IF(DFUNC EQ 2, FIRST_VAL=EPS; LAST_VAL=EPS; ELSEIF DFUNC EQ 4, Z=INF; ELSEIF DFUNC EQ 5, F=0));
IF(DFUNC NE 1,
    {arg1}({arg2}{arg6}{tail2}) $= FIRST_VAL$({arg7}(YEARVAL({arg6}) LT F)) + LAST_VAL$({arg8}(YEARVAL({arg6}) GT Z));
));
);
"""
    return code_block
