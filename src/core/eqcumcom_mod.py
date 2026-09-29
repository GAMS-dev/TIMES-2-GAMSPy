# eqcumcom_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCUMCOM sets the cumulative limit on a commodity
# *   %1 - equation declaration type
# *   %2 - NET/PRD indicator
# *=============================================================================*
# *GaG Questions/Comments:
# * - scale both sides!!!
# * [AL] Changed to support arbitrary year range
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Ord, Sum
from gamspy.math import Max, Min

from core.base_class import GamsClass
from core.utils import generate_equation, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcumcomMod(GamsClass):
    """Translation unit for eqcumcom.mod."""

    # Instance attributes
    module_name: str = "eqcumcom_mod"
    gams_source: str = "eqcumcom.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal["E"],
        arg2: Literal["NET", "PRD"],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.sense = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc

        (
            Rc,
            r,
            c,
            e,
            allyear,
            ll,
            t,
            tt,
            lagt,
            yearval,
            b,
            m,
            lead,
            Tpulse,
            year,
            s,
            RcCumcom,
            RtcsVarc,
            Tpulseyr,
        ) = (
            g.Rc,
            g.r,
            g.c,
            g.e,
            g.allyear,
            g.ll,
            g.t,
            g.tt,
            g.lagt,
            g.yearval,
            g.b,
            g.m,
            g.lead,
            g.tpulse,
            g.year,
            g.s,
            g.RcCumcom,
            g.RtcsVarc,
            g.Tpulseyr,
        )

        sow = self.env.sow_GP
        sws = self.env.sws_GP
        cucscal = self.env.cucscal
        vartt_id, vartt_set = self.env.vartt_GP

        Rtc = g.get_set(f"RTC_{self.arg2}")
        VARTT_COM = g.get_variable(f"{vartt_id}_COM{self.arg2}")

        VARRT_COM_expr = wrap_in_sum(VARTT_COM[r, t, c, s, *sws], vartt_set)

        if self.env.obj.upper() != "LIN":
            condition = (e[t] >= yearval[allyear]).where[b[t] <= yearval[ll]]
        else:
            condition = ((m[t] + lagt[t]) > yearval[allyear]).where[
                (m[t] - lead[t]) < yearval[ll]
            ]

        if self.env.obj.upper() != "LIN":
            rhs = Max(0, Min(e[t], yearval[ll]) - Max(b[t], yearval[allyear]) + 1)
        else:
            rhs = Sum(  # type: ignore[assignment]
                Tpulseyr[t, year].where[
                    (Ord(year) >= Ord(allyear)).where[Ord(year) <= Ord(ll)]
                ],
                Tpulse[t, year],
            )

        eq_cum, sow = macro.EQ_CUM_GP(self.env.eq, self.arg2, sow)

        eq_cum[Rc[r, c], allyear, ll, *sow].where[
            RcCumcom[r, self.arg2, allyear, ll, c]
        ] = generate_equation(
            # all commodity flows within period range
            Sum(
                Rtc[r, tt[t], c].where[condition],
                Sum(
                    RtcsVarc[r, t, c, s],
                    (rhs * VARRT_COM_expr) / cucscal,
                ),
            ),
            self.sense,
            macro.VAR_CUMCOM_GP(self.env.var, r, c, self.arg2, allyear, ll, sow),
        )
