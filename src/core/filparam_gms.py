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
from typing import TYPE_CHECKING, NamedTuple

from gamspy import (
    Alias,
    Domain,
    ElseIf,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    SpecialValues,
    sparse,
)
from gamspy._symbols.implicits import ImplicitSet
from gamspy.math import Round, mod

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FilparamGmsConfig(NamedTuple):
    src: Parameter
    arg2: tuple[Set | Alias, ...] | tuple[()]
    tail1: tuple[Set | Alias, ...] | tuple[()]
    arg4: tuple[str, ...]
    arg5: Set | Alias
    arg6: Set | Alias
    arg7: ImplicitSet | Number = Number(1)
    arg8: ImplicitSet | Number = Number(1)
    arg9: int = 0
    arg10: tuple[Set | Alias, ...] | tuple[()] = ()


class FilparamGms(GamsClass):
    """Translation unit for filparam.gms."""

    # Instance attributes
    module_name: str = "filparam_gms"
    gams_source: str = "filparam.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: FilparamGmsConfig
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            filparam_gms_gp, g=self.tc, cc=self.config, dflbl=self.env.dflbl
        )


def filparam_gms_gp(g: TimesModelClass, cc: FilparamGmsConfig, dflbl: str) -> None:
    ll, yearval = g.ll, g.yearval

    tail2 = cc.tail1
    tail1 = ("",) if cc.tail1 == () else cc.tail1

    g.Uncd7.setRecords(None)

    if cc.arg10 == ():
        # TODO: Wait for Domain to be able to process a single set
        index_list = [*cc.arg2, cc.arg5, *tail2]
        if len(index_list) >= 2:
            loop_domain = Domain(*cc.arg2, cc.arg5, *tail2)
        else:
            loop_domain = cc.arg5  # type: ignore

        with Loop(loop_domain.where[cc.src[*cc.arg2, cc.arg5, *tail2]]):
            g.Uncd7[*cc.arg2, *tail1, *cc.arg4] = True
    else:
        g.Uncd7[*cc.arg2, ll.lag(Ord(ll), "circular"), *tail1, *cc.arg4].where[
            cc.src[*cc.arg2, ll, *tail2]
        ] = True

    with Loop(g.Uncd7[*cc.arg2, *cc.arg10, *tail1, *cc.arg4]):
        g.f[...] = 0
        g.z[...] = SpecialValues.POSINF
        g.my_fyear[...] = 9999
        g.dfunc[...] = Round(cc.src[*cc.arg2, dflbl, *tail2])

        if cc.arg9:
            with If(~g.dfunc):
                g.dfunc[...] = cc.arg9

        with If(g.dfunc >= 0):
            g.my_array[cc.arg5] = cc.src[*cc.arg2, cc.arg5, *tail2]
            g.my_array[dflbl] = 0

            # do interpolate
            with Loop(
                cc.arg5.where[g.my_array[cc.arg5]]
            ):  # check for nonzero (including EPS)
                g.my_f[...] = g.my_array[cc.arg5]
                g.z[...] = yearval[cc.arg5]

                with If(g.z > (g.my_fyear + 1)):  # linear interpolation
                    cc.src[*cc.arg2, cc.arg6, *tail2].where[
                        (g.z > yearval[cc.arg6]).where[yearval[cc.arg6] > g.my_fyear]
                    ] = g.last_val + (g.my_f - g.last_val) / (g.z - g.my_fyear) * (
                        yearval[cc.arg6] - g.my_fyear
                    )  # not the first one

                with ElseIf(g.z < g.my_fyear):
                    #  remember the value and year
                    g.f[...] = g.z[...]
                    g.first_val[...] = g.my_f[...]

                g.last_val[...] = g.my_f[...]
                g.my_fyear[...] = g.z[...]

            # Do back/forward extrapolate
            with If(g.dfunc >= 1):
                g.dfunc[...] = mod(g.dfunc, 10)
                with If(g.dfunc == 2):
                    g.first_val[...] = SpecialValues.EPS
                    g.last_val[...] = SpecialValues.EPS
                with ElseIf(g.dfunc == 4):
                    g.z[...] = SpecialValues.POSINF
                with ElseIf(g.dfunc == 5):
                    g.f[...] = 0

            with If(g.dfunc != 1):
                cc.src[*cc.arg2, cc.arg6, *tail2] = sparse(
                    g.first_val[...].where[cc.arg7.where[yearval[cc.arg6] < g.f]]
                    + g.last_val[...].where[cc.arg8.where[yearval[cc.arg6] > g.z]]
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
