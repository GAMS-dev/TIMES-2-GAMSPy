# pp_shapr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_SHPRC.MOD shape a process based attribute
# *   %1 - attribute name
# *   %2 - driving indexes
# *   %3 - any qualifiers to help narrow loop (if none, set to YES)
# *   %4 - mapped coefficient
# *   %5 - optional -M(R,V,P) or 1
# *=============================================================================*
# *AL Comments:
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Number, Set, SpecialValues, Sum
from gamspy.math import Max, Min

from core.base_class import GamsClass

if TYPE_CHECKING:
    from collections.abc import Sequence

    from gamspy import Alias, Number, Parameter, Set
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpShaprMod(GamsClass):
    """Translation unit for pp_shapr.mod."""

    # Instance attributes
    module_name: str = "pp_shapr_mod"
    gams_source: str = "pp_shapr.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Parameter,
        arg2: Sequence[Set | Alias],
        arg3: ImplicitSet | Expression,
        arg4: ImplicitParameter,
        arg5: ImplicitParameter,
        arg6: Parameter,
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
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        Reg, allyear, prc, bd, j, ll = (g.Reg, g.allyear, g.prc, g.bd, g.j, g.ll)
        g.RtpShapi = Set(m, "RTP_SHAPI", domain=[Reg, allyear, prc, bd, j, j, ll, ll])

        pass_var = self.arg3 if self.arg3 is not None else Number(1)

        self.tc.enqueue(
            self.exec_start_end,
            self.arg1,
            self.arg2,
            self.arg4,
            self.arg5,
            self.arg6,
            pass_var,
        )

    def exec_start_end(
        self: PpShaprMod,
        arg1: Parameter,
        arg2: Sequence[Set | Alias],
        arg4: ImplicitParameter,
        arg5: ImplicitParameter,
        arg6: Parameter,
        pass_var: ImplicitSet | Expression | Number,
    ) -> None:
        g = self.tc

        r, v, p, bd, j, jj, ll = g.r, g.v, g.p, g.bd, g.j, g.jj, g.ll
        t, year, yearval = g.t, g.year, g.yearval

        with Loop(bd):
            g.RtpIshpr[g.Rtp[r, v, p]].where[
                (arg6[g.Rtp, bd] >= 1.5).where[arg6[g.Rtp, bd]]
            ] = True

        g.RtpIshpr[g.Rtp[r, v, p]].where[(arg5 >= 1.5).where[arg5]] = True

        # Prepare for start and end years
        g.fil2.setRecords(None)
        g.fil2[v] = g.b[v] - yearval[v]
        g.pastsum[g.RtpIshpr[r, v, p]] = (
            g.fil2[v] + g.ncap_iled[r, v, p] + g.ncap_tlife[r, v, p] - 1
        )

        # Shape attributes only for processes around for > 1 period
        arg6[g.RtpIshpr[r, v, p], bd].where[
            g.pastsum[r, v, p] - g.fil2[v] + 1 < g.d[v]
        ] = 0

        # Get hold of the shape and multi index J,JJ for each RVP, as well as start and end years
        with Loop(j.sameAs("1")):
            g.RtpShapi[
                g.RtpIshpr[r, v[ll], p],
                bd,
                j + Max(0, arg6[r, v, p, bd] - 1),
                j + Max(0, arg5 - 1),
                ll + (g.fil2[v] + g.ncap_iled[r, v, p]),
                ll + g.pastsum[r, v, p],
            ] = True

        # Calculate average SHAPE for plants still operating in each period:
        with Loop(g.age.sameAs("1")):
            arg4.where[pass_var.where[g.RtpIshpr[r, v, p]]] = arg1[*arg2] * Sum(
                g.RtpShapi[r, v, p, bd, j, jj, ll, year],
                SpecialValues.EPS
                + g.multi[jj, t]
                * Sum(
                    g.Periodyr[t, g.Eohyears].where[
                        yearval[g.Eohyears] <= Max(g.b[t], yearval[year])
                    ],
                    g.shape[
                        j,
                        g.age + (Min(yearval[g.Eohyears], yearval[year]) - yearval[ll]),
                    ],
                )
                / (Max(1, Min(g.e[t], yearval[year]) - Max(g.b[t], yearval[ll]) + 1)),
            )

        # If no shape index is specified, set the BASE value for the attribute
        g.RtpIshpr[g.Rtp[r, v, p]] = ~g.RtpIshpr[g.Rtp]
        arg4.where[g.RtpIshpr[r, v, p].where[pass_var]] = arg1[*arg2]
        # Clear the temporary sets
        g.RtpShapi.setRecords(None)
        g.RtpIshpr.setRecords(None)
        g.pastsum.setRecords(None)
