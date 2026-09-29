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
from typing import TYPE_CHECKING, NamedTuple

from gamspy import Else, ElseIf, If, Loop, Ord, SpecialValues, sparse
from gamspy.math import Min, Round, mod

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Number, Parameter, Set
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PreshapeGmsConfig(NamedTuple):
    arg1: Parameter
    arg2: tuple[Alias | Set, ...]
    arg3: tuple[Alias | Set, ...]
    arg4: tuple[str, ...] | tuple[()]
    arg5: Alias | Set
    arg6: Set
    arg7: ImplicitSet | Number
    arg8: int = 0


class PreshapeGms(GamsClass):
    """Translation unit for preshape.gms."""

    # Instance attributes
    module_name: str = "preshape_gms"
    gams_source: str = "preshape.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: PreshapeGmsConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        cc = self.config

        # $SETLOCAL DEF 10 / $IF NOT '%8'=='' $SETLOCAL DEF %8
        default = cc.arg8 if cc.arg8 else 10

        self.tc.enqueue(self.exec1, cc=cc)
        self.tc.enqueue(self.main_loop, cc=cc, default=default, dflbl=self.env.dflbl)

    def exec1(self: PreshapeGms, cc: PreshapeGmsConfig) -> None:
        g = self.tc
        ll = g.ll

        cc.arg6.setRecords(None)
        cc.arg6[*cc.arg2, ll.lag(Ord(ll), "circular"), *cc.arg3, *cc.arg4] = sparse(
            cc.arg1[*cc.arg2, ll, *cc.arg3]
        )

    def main_loop(
        self: PreshapeGms, cc: PreshapeGmsConfig, default: int, dflbl: str
    ) -> None:
        g = self.tc
        ll = g.ll

        with Loop(cc.arg6[*cc.arg2, dflbl, *cc.arg3, *cc.arg4]):
            g.dfunc[...] = default
            g.dfunc[...] = sparse(mod(Round(cc.arg1[*cc.arg2, dflbl, *cc.arg3]), 1000))
            g.my_array[g.DmYear] = cc.arg1[*cc.arg2, g.DmYear, *cc.arg3]
            with If(g.dfunc != 10):
                g.f[...] = 0
                g.last_val[...] = 0
                # do interpolate
                with Loop(
                    g.DmYear.where[g.my_array[g.DmYear]]
                ):  # check for nonzero (including EPS)
                    g.my_f[...] = g.my_array[g.DmYear]
                    g.z[...] = g.yearval[g.DmYear]
                    with If(g.last_val):
                        cc.arg1[*cc.arg2, cc.arg5, *cc.arg3].where[
                            (g.z > g.yearval[cc.arg5]).where[
                                g.yearval[cc.arg5] > g.my_fyear
                            ]
                        ] = g.last_val
                    with Else():
                        g.f[...] = g.z
                        g.first_val[...] = g.my_f
                    g.last_val[...] = Round(g.my_f)
                    g.my_fyear[...] = g.z  # remember the value and year
            with Else():  # intra-period I/E
                g.first_val[...] = 0
                g.my_fyear[...] = 0
                with Loop(
                    g.MyFil[ll].where[g.my_array[g.MyFil]]
                ):  # check for data values
                    g.my_f[...] = g.my_array[ll]
                    g.z[...] = g.yearval[g.MyFil]
                    g.f[...] = g.fil2[g.MyFil]
                    with If(g.my_fyear < g.f):
                        with If(g.f > Min(g.first_val, g.z)):
                            g.last_val[...] = g.my_f
                            g.first_val[...] = g.f
                        cc.arg1[
                            *cc.arg2, cc.arg5[ll.lead(g.f - g.yearval[ll])], *cc.arg3
                        ].where[~g.my_array[cc.arg5]] = g.last_val
                    g.last_val[...] = g.my_f
                    g.my_fyear[...] = g.z  # remember the value and year
                g.dfunc[...] = 0

            with If(Round(g.dfunc - 5, -1) == 10):
                cc.arg1[*cc.arg2, cc.arg5, *cc.arg3].where[cc.arg7] = sparse(
                    g.first_val.where[
                        (g.yearval[cc.arg5] < g.f).where[g.e[cc.arg5] >= g.f]
                    ]
                    + g.last_val.where[
                        (g.yearval[cc.arg5] > g.z).where[g.b[cc.arg5] <= g.z]
                    ]
                )
                g.dfunc[...] = g.dfunc - 10

            with If(g.dfunc >= 2):
                # Do back/forward extrapolate
                with If(g.dfunc == 4):
                    g.z[...] = SpecialValues.POSINF
                with ElseIf(g.dfunc == 5):
                    g.f[...] = 0
                with ElseIf(g.dfunc == (2 - g.f)):
                    g.last_val[...] = SpecialValues.EPS
                    g.z[...] = 0

                cc.arg1[*cc.arg2, cc.arg5, *cc.arg3].where[cc.arg7] = sparse(
                    g.first_val.where[g.yearval[cc.arg5] < g.f]
                    + g.last_val.where[g.yearval[cc.arg5] > g.z]
                )
