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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import (
    Alias,
    Else,
    ElseIf,
    Expression,
    If,
    Loop,
    Number,
    Parameter,
    Set,
    SpecialValues,
    sparse,
)
from gamspy.math import Min, Round, mod, power

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import UniverseAlias
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class FillparmGmsConfig:
    arg1: Parameter
    arg2: tuple[Set | Alias, ...]
    arg3: tuple[Set | Alias | UniverseAlias, ...]
    arg4: tuple[str, ...]
    arg5: Set | Alias
    arg6: Number | ImplicitSet | Alias | Expression
    arg7: Number | Condition | None = None
    arg8: Parameter | str | None = ""
    arg9: Parameter | str | None = ""
    arg10: str = ""


class FillparmGms(GamsClass):
    """Translation unit for fillparm.gms."""

    # Instance attributes
    module_name: str = "fillparm_gms"
    gams_source: str = "fillparm.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: FillparmGmsConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        cc = self.config

        data = cc.arg1[*cc.arg2, cc.arg5, *cc.arg3]
        item = cc.arg1[*cc.arg2, cc.arg5, *cc.arg3]
        add = None

        arg8_param = None
        if isinstance(cc.arg8, str) and cc.arg8 != cc.arg9 and cc.arg8 not in {""}:
            arg8_param = Parameter(
                m, name=cc.arg8, domain=[*cc.arg2, *cc.arg3, g.allyear]
            )
            g.set_parameter(arg8_param.name, arg8_param)

        if isinstance(cc.arg8, str) and cc.arg8 not in {""}:
            arg8_param = g.get_parameter(cc.arg8)
            data = arg8_param[*cc.arg2, *cc.arg3, cc.arg5]
            item = g.my_fil2[cc.arg5]
            add = g.my_fil2[cc.arg5]

        self.tc.enqueue(
            fillparm,
            self,
            dflbl=self.env.dflbl,
            item=item,
            data=data,
            add=add,
            reset=self.env.reset,
            config=FillparmGmsConfig(
                arg1=cc.arg1,
                arg2=cc.arg2,
                arg3=cc.arg3,
                arg4=cc.arg4,
                arg5=cc.arg5,
                arg6=cc.arg6,
                arg7=cc.arg7,
                arg8=arg8_param,
                arg9=cc.arg8,  # the arg9=arg8 is on purpose to have the execution part not fail
            ),
        )


def fillparm(
    module: GamsClass,
    dflbl: str,
    item: ImplicitParameter,
    data: ImplicitParameter,
    add: ImplicitParameter | None,
    reset: str,
    config: FillparmGmsConfig,
) -> None:
    g = module.tc
    (
        g_nointerp,
        Uncd7,
        Datayear,
        dfunc,
        my_fil2,
        cnt,
        my_array,
        DmYear,
        last_val,
        f,
        z,
        my_f,
        yearval,
        my_fyear,
        first_val,
    ) = (
        g.g_nointerp,
        g.Uncd7,
        g.Datayear,
        g.dfunc,
        g.my_fil2,
        g.cnt,
        g.my_array,
        g.DmYear,
        g.last_val,
        g.f,
        g.z,
        g.my_f,
        g.yearval,
        g.my_fyear,
        g.first_val,
    )

    cc = config

    # conditional interpolation flag
    if g_nointerp.toValue() == 0:
        Uncd7.setRecords(None)
        with Loop(Datayear):
            Uncd7[*cc.arg2, *cc.arg3, *cc.arg4].where[
                cc.arg1[*cc.arg2, Datayear, *cc.arg3]
            ] = True

        with Loop(Uncd7[*cc.arg2, *cc.arg3, *cc.arg4]):
            dfunc[...] = Round(cc.arg1[*cc.arg2, dflbl, *cc.arg3])

            if_cond = dfunc >= cc.arg7 if cc.arg7 is not None else dfunc
            with If(if_cond):
                my_fil2.setRecords(None)
                cnt[...] = dfunc <= 999
                my_array[DmYear] = cc.arg1[*cc.arg2, DmYear, *cc.arg3]
                last_val[...] = 0
                f[...] = 0
                z[...] = 0

                # do interpolate
                with Loop(DmYear.where[my_array[DmYear]]):
                    my_f[...] = my_array[DmYear]
                    z[...] = yearval[DmYear]
                    with If(last_val):
                        with If(cnt | (z <= dfunc)):
                            item.where[
                                (z > yearval[cc.arg5]).where[
                                    yearval[cc.arg5] > my_fyear
                                ]
                            ] = last_val + (my_f - last_val) / (z - my_fyear) * (
                                yearval[cc.arg5] - my_fyear
                            )
                        with Else():
                            item.where[
                                (z > yearval[cc.arg5]).where[
                                    yearval[cc.arg5] > my_fyear
                                ]
                            ] = (
                                last_val * power(1 + my_f, yearval[cc.arg5] - my_fyear)
                                + SpecialValues.EPS
                            )
                            my_f[...] = (
                                last_val * power(1 + my_f, z - my_fyear)
                                + SpecialValues.EPS
                            )
                            cc.arg1[*cc.arg2, DmYear, *cc.arg3] = my_f
                    with Else():
                        f[...] = z
                        first_val[...] = my_f
                    last_val[...] = my_f
                    my_fyear[...] = z
                with If(dfunc > 1):  # noqa: SIM117
                    with If(cnt):
                        dfunc[...] = mod(dfunc, 10)
                        with If(dfunc == 2):
                            first_val[...] = SpecialValues.EPS
                            last_val[...] = SpecialValues.EPS
                        with ElseIf(dfunc == 4):
                            z[...] = SpecialValues.POSINF
                        with ElseIf(dfunc == 5):
                            f[...] = 0
                with If(dfunc != 1):
                    # Do back/forward extrapolate, or fill in with EPS
                    expr: Expression | Condition = first_val.where[yearval[cc.arg5] < f]
                    if add is not None:
                        expr += add

                    expr += last_val.where[yearval[cc.arg5] > z]
                    data.where[cc.arg6] = sparse(expr)  # type: ignore[index]

                    if cc.arg8 is None:
                        data.where[cc.arg6] = sparse(item)  # type: ignore[index]

        cc.arg1[*cc.arg2, dflbl, *cc.arg3].where[cc.arg1[*cc.arg2, dflbl, *cc.arg3]] = (
            Min(reset, cc.arg1[*cc.arg2, dflbl, *cc.arg3])
        )

        if isinstance(cc.arg8, Parameter):
            cc.arg1[*cc.arg2, cc.arg5, *cc.arg3] = sparse(data)
            cc.arg8.setRecords(None)
