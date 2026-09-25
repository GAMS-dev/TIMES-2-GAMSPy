# prepparm_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * PREPPAR : Prepare parameters for preprocessing
# * Description: Non-default interpolation/extrapolation according to user option
# *              DFUNC = -1-> no interpolation, 0-> default action, 10->intra-period
# *              DFUNC = +1-> interp., 2->interp.+EPS, 3->interp.+extrap.
# *              DFUNC >999 -> exponential interpolation beyond year DFUNC
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1
# *      arg3 - control set 2
# *      arg4 - UNCD7 residual dimension
# *      arg5 - MODLYEAR or MILESTONYR depending on parameter
# *      arg6 - RTP controlling the assignment to the MODLYEARs
# *      arg7 - Option to prohibit extrapolation (1 for other than cost parameters)
# *      arg8 -
# *      arg9 -
# *      arg10-
# *******************************************************************************


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, NamedTuple

from gamspy import (
    Alias,
    Else,
    ElseIf,
    Expression,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    SpecialValues,
    UniverseAlias,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, floor, power

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepparmGmsConfig(NamedTuple):
    arg1: str
    arg2: tuple[Alias | Set, ...]
    arg3: tuple[Alias | Set | UniverseAlias, ...]
    arg4: tuple[str, ...] | tuple[()]
    arg5: Alias | Set
    arg6: ImplicitSet | Number
    arg7: float
    arg8: int = 0
    arg9: str | None = None
    arg10: Literal["+", "-ABS"] | None = None


class PrepparmGms(GamsClass):
    """Translation unit for prepparm.gms."""

    # Instance attributes
    module_name: str = "prepparm_gms"
    gams_source: str = "prepparm.gms"

    def __init__(
        self: PrepparmGms,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: PrepparmGmsConfig,
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self: PrepparmGms) -> None:
        g = self.tc
        cc = self.config

        if (cc.arg9 is not None) and (g.get_parameter(cc.arg9) is None):
            param = Parameter(
                g.container, name=cc.arg9, domain=[*cc.arg2, *cc.arg3, g.allyear]
            )
            g.set_parameter(name=cc.arg9, parameter=param)

        self.add_records_to_universe_item(records=[cc.arg1])

        self.tc.enqueue(
            prepparm,
            self,
            cc=self.config,
            dflbl=self.env.dflbl,
            def_iebd=self.env.def_iebd,
            reset=self.env.reset,
        )


def prepparm(
    module: GamsClass, cc: PrepparmGmsConfig, dflbl: str, def_iebd: int, reset: int
) -> None:
    g = module.tc
    ll = g.ll

    arg1_param = g.get_parameter(cc.arg1)
    arg9_param = g.get_parameter(cc.arg9) if cc.arg9 is not None else None

    data = g.my_fil2[cc.arg5]
    opt = cc.arg7 != 0
    c_ll = (dflbl,) if cc.arg7 != 0 else ()

    if cc.arg8:
        def_iebd = cc.arg8

    # conditional interpolation flag
    if g.g_nointerp.toValue():
        g.intdefault[cc.arg1] = False

    else:
        g.Uncd7.setRecords(None)
        g.cnt[...] = (
            def_iebd + Number(3 - def_iebd).where[g.ie_default[cc.arg1]]
        ).where[Number(cc.arg7)]
        if g.cnt.toValue() == 0:
            g.Uncd7[*cc.arg2, *c_ll, *cc.arg3, *cc.arg4].where[
                arg1_param[*cc.arg2, dflbl, *cc.arg3] > 0
            ] = True
        else:
            if opt:
                g.Uncd7[*cc.arg2, cc.arg5, *cc.arg3, *cc.arg4].where[
                    arg1_param[*cc.arg2, dflbl, *cc.arg3] == -13
                ] = sparse(arg1_param[*cc.arg2, cc.arg5, *cc.arg3])
                if g.Uncd7.number_records:
                    arg1_param[*cc.arg2, cc.arg5, *cc.arg3].where[
                        g.Uncd7[*cc.arg2, cc.arg5, *cc.arg3, *cc.arg4]
                    ] = 0
                    g.Uncd7.setRecords(None)

                if (cc.arg10 is None) or (cc.arg10 == "+"):
                    condition: Expression = arg1_param[*cc.arg2, dflbl, *cc.arg3] > -0.5
                elif cc.arg10 == "-ABS":
                    condition = (-abs(arg1_param[*cc.arg2, dflbl, *cc.arg3])) > -0.5
                else:
                    raise ValueError(f"Unexpected value {cc.arg10} for arg10.")

                g.Uncd7[
                    *cc.arg2, ll.lag(Ord(ll), "circular"), *cc.arg3, *cc.arg4
                ].where[condition.where[arg1_param[*cc.arg2, ll, *cc.arg3]]] = True

        if g.Uncd7.number_records:
            with Loop(g.Uncd7[*cc.arg2, *c_ll, *cc.arg3, *cc.arg4]):
                g.dfunc[...] = g.cnt
                g.dfunc[...] = sparse(Round(arg1_param[*cc.arg2, dflbl, *cc.arg3]))
                g.my_array[g.DmYear] = arg1_param[*cc.arg2, g.DmYear, *cc.arg3]
                g.my_fil2.setRecords(None)
                # do interpolate
                with If(g.dfunc != 10):
                    g.last_val[...] = 0
                    g.f[...] = 0
                    g.z[...] = 0
                    with Loop(
                        g.DmYear.where[g.my_array[g.DmYear]]
                    ):  # check for nonzero (including EPS)
                        g.my_f[...] = g.my_array[g.DmYear]
                        g.z[...] = g.yearval[g.DmYear]
                        with If(g.last_val):
                            with If(
                                (g.z > g.dfunc).where[g.dfunc > 999]
                            ):  # exponential function
                                data.where[
                                    (g.z > g.yearval[cc.arg5]).where[
                                        (g.yearval[cc.arg5] > g.my_fyear)
                                    ]
                                ] = (
                                    g.last_val
                                    * power(1 + g.my_f, g.yearval[cc.arg5] - g.my_fyear)
                                    + SpecialValues.EPS
                                )
                                g.my_f[...] = (
                                    g.last_val * power(1 + g.my_f, g.z - g.my_fyear)
                                    + SpecialValues.EPS
                                )
                                g.my_fil2[g.DmYear] = g.my_f  # overwrite old data
                            with Else():  # type: ignore[no-untyped-call] # linear interpolation
                                data.where[
                                    (g.z > g.yearval[cc.arg5]).where[
                                        (g.yearval[cc.arg5] > g.my_fyear)
                                    ]
                                ] = g.last_val + (g.my_f - g.last_val) / (
                                    g.z - g.my_fyear
                                ) * (g.yearval[cc.arg5] - g.my_fyear)
                        with Else():  # type: ignore[no-untyped-call]
                            g.f[...] = g.z
                            g.first_val[...] = g.my_f

                        g.last_val[...] = g.my_f
                        g.my_fyear[...] = g.z  # remember the value and year
                with Else():  # type: ignore[no-untyped-call]
                    if opt:
                        # intra-period I/E
                        g.first_val[...] = 0
                        g.my_fyear[...] = 0
                        with Loop(
                            g.MyFil[ll].where[g.my_array[g.MyFil]]
                        ):  # check for data values
                            g.my_f[...] = g.my_array[ll]
                            g.z[...] = g.yearval[ll]
                            g.f[...] = g.fil2[ll]
                            with If(g.my_fyear < g.f):
                                with If(g.f > Min(g.first_val, g.z)):
                                    g.last_val[...] = g.my_f
                                    g.first_val[...] = g.f
                                g.my_fil2[cc.arg5[ll.lead(g.f - g.yearval[ll])]].where[
                                    (~g.my_array[cc.arg5])
                                ] = g.last_val + (g.my_f - g.last_val) / (
                                    g.z - g.my_fyear
                                ) * (g.f - g.my_fyear)
                            g.last_val[...] = g.my_f
                            g.my_fyear[...] = g.z  # remember the value and year

                        g.dfunc[...] = cc.arg7

                if opt:
                    with If(floor(g.dfunc / 10) == 1):
                        with Loop(g.Miyr1[ll]):
                            g.my_fyear[...] = g.yearval[ll]
                            g.my_f[...] = g.fil2[ll.lead(g.f - g.my_fyear)]
                            with If(g.my_f < g.f.where[g.my_f]):
                                g.my_fil2[cc.arg5[ll.lead(g.my_f - g.my_fyear)]] = (
                                    g.first_val
                                )
                            g.my_f[...] = g.fil2[ll.lead(g.z - g.my_fyear)]
                            with If(g.my_f > g.z):
                                g.my_fil2[cc.arg5[ll.lead(g.my_f - g.my_fyear)]] = (
                                    g.last_val
                                )
                        g.dfunc[...] = g.dfunc - 10

                with If(g.dfunc != cc.arg7):
                    # Do back/forward extrapolate, or fill in with EPS
                    with If(g.dfunc <= 2):
                        data.where[cc.arg6.where[~(data + g.my_array[cc.arg5])]] = (
                            SpecialValues.EPS
                        )
                    with Else():  # type: ignore[no-untyped-call]
                        with If(g.dfunc == 4):
                            g.z[...] = SpecialValues.POSINF
                        with ElseIf(g.dfunc == 5):
                            g.f[...] = 0

                        data.where[cc.arg6] = sparse(
                            g.first_val.where[g.yearval[cc.arg5] < g.f]
                            + g.last_val.where[g.yearval[cc.arg5] > g.z]
                        )
                        with If((~Number(cc.arg7)).where[g.last_val]):
                            data.where[cc.arg6.where[~(data + g.my_array[cc.arg5])]] = (
                                SpecialValues.EPS
                            )

                if cc.arg9 is None:
                    arg1_param[*cc.arg2, cc.arg5, *cc.arg3] = sparse(data)
                else:
                    assert arg9_param is not None
                    arg9_param[*cc.arg2, *cc.arg3, cc.arg5].where[cc.arg6] = sparse(
                        data
                    )

        if cc.arg10 != "+":
            arg1_param[*cc.arg2, "0", *cc.arg3].where[
                (
                    Max(0, arg1_param[*cc.arg2, "0", *cc.arg3]) - Max(cc.arg7, reset)
                ).where[arg1_param[*cc.arg2, "0", *cc.arg3]]
            ] = reset
        if cc.arg9 is not None:
            assert arg9_param is not None
            arg1_param[*cc.arg2, cc.arg5, *cc.arg3] = sparse(
                arg9_param[*cc.arg2, *cc.arg3, cc.arg5]
            )
            module.tc.add_gams_code(
                module=module, phase="run", code=f"OPTION KILL={cc.arg9};"
            )

    arg1_param[*cc.arg2, "EMPTY", *cc.arg3] = 0
