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
from typing import TYPE_CHECKING, Literal, NamedTuple

from gamspy import (
    Alias,
    Else,
    Expression,
    For,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    set_options,
    sparse,
)

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Card
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillcostGmsConfig(NamedTuple):
    arg1: Parameter
    arg2: Alias | Set
    arg3: tuple[Set | Alias, ...]
    arg4: tuple[str, ...]
    arg5: Alias | Set
    arg6: ImplicitSet | Card | Literal[1]
    bext: Expression | Literal[1]
    fext: Expression | Literal[1]
    arg9: Parameter
    arg10: str
    arg11: int = 0


class FillcostGms(GamsClass):
    """Translation unit for fillcost.gms."""

    # Instance attributes
    module_name: str = "fillcost_gms"
    gams_source: str = "fillcost.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: FillcostGmsConfig
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        param = Parameter(
            container=self.tc.container,
            name=cc.arg10,
            domain=[cc.arg2, *cc.arg3, g.allyear],
        )
        g.set_parameter(name=cc.arg10, parameter=param)

        src = cc.arg9
        data = param[cc.arg2, *cc.arg3, cc.arg5]
        take = cc.arg6
        tmp: tuple[Set | Alias | str, ...] = (*cc.arg3, *cc.arg4)

        if len(cc.arg9.domain) == 8:
            tmp = (*cc.arg4,)

        self.tc.enqueue(
            self.exec1,
            cc,
            new_param=param,
            tmp=tmp,
            take=take,
            src=src,
            data=data,
            condition1=(cc.arg11 == 1),
            condition2=(cc.arg11 == 2),
        )

    def exec1(
        self: FillcostGms,
        cc: FillcostGmsConfig,
        new_param: Parameter,
        tmp: tuple[Set | Alias | str, ...],
        take: ImplicitSet | Card | Literal[1],
        src: Parameter,
        data: ImplicitParameter,
        condition1: bool,
        condition2: bool,
    ) -> None:
        g = self.tc
        ll, year = g.ll, g.year
        Uncd7, Datayear, DmYear = g.Uncd7, g.Datayear, g.DmYear

        Uncd7.setRecords(None)

        take_condition: ImplicitSet | Card | Number = (
            Number(take) if isinstance(take, int) else take
        )

        if condition1:
            cc.arg1[cc.arg2, Datayear, *cc.arg3] = sparse(
                cc.arg9[cc.arg2, Datayear, *cc.arg3].where[
                    take_condition  # type: ignore[index]
                ]
            )
            take_condition = Number(1)
            src = cc.arg1

        Uncd7[cc.arg2, ll.lag(Ord(ll), "circular"), *tmp].where[take_condition] = (  # type: ignore[index]
            sparse(src[cc.arg2, ll, *cc.arg3])
        )

        with Loop(Uncd7[cc.arg2, year, *tmp]):
            g.f[...] = 0
            g.last_val[...] = 0
            g.my_fil2.setRecords(None)
            g.my_array[DmYear] = src[cc.arg2, DmYear, *cc.arg3]
            # do linear interpolation
            with Loop(DmYear[ll].where[g.my_array[DmYear]]):  # check for nonzero
                g.my_f[...] = g.my_array[ll]
                g.z[...] = g.yearval[ll]
                with If(g.last_val):
                    g.last_val[...] = (g.my_f[...] - g.last_val[...]) / (
                        g.z[...] - g.my_fyear[...]
                    )
                    with For(g.cnt, start=g.my_fyear[...] - g.z[...] + 1, end=-1):  # type: ignore[arg-type]
                        g.my_fil2[cc.arg5[ll.lead(g.cnt)]] = (
                            g.my_f[...] + g.last_val[...] * g.cnt[...]
                        )
                with Else():  # type: ignore[no-untyped-call]
                    g.f[...] = g.z[...]
                    g.first_val[...] = g.my_f[...]

                g.last_val[...] = g.my_f[...]  # remember the value and year
                g.my_fyear[...] = g.z[...]

            # Do back/forward extrapolate
            if condition2:
                g.my_fil2[cc.arg5] = sparse(g.my_array[cc.arg5])

            cond1 = cc.bext & (g.yearval[cc.arg5] < g.f[...])
            cond2 = cc.fext & (g.yearval[cc.arg5] > g.z[...])

            new_param[cc.arg2, *cc.arg3, cc.arg5] = sparse(
                g.first_val[...].where[cond1]
                + g.my_fil2[cc.arg5]
                + g.last_val[...].where[cond2]
            )

        if condition2:
            set_options({"VALIDATION": 0})  # TODO: Remove in future GAMSPY version
            new_param["EMPTY", *cc.arg3, "EMPTY"] = 0
            set_options({"VALIDATION": 1})  # TODO: Remove in future GAMSPY version
        else:
            cc.arg1[cc.arg2, cc.arg5, *cc.arg3] = sparse(data)
            new_param.setRecords(None)
