# eqcumflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCUMFLO sets the cumulative upper limit on a flow or activity
# *   %1 - equation declaration type
# *=============================================================================*
# *AL Questions/Comments:
# * - scale both sides
# * - support arbitrary year range
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Number, Ord, Sum
from gamspy.math import MathOp, Max, Min, map_value, same_as

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy.math import MathOp

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcumfloMod(GamsClass):
    """Translation unit for eqcumflo.mod."""

    # Instance attributes
    module_name: str = "eqcumflo_mod"
    gams_source: str = "eqcumflo.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func

        # sow is changed after the equation domain declaration
        # thus, sow_domain captures the state prior to the change
        sow_domain = self.env.sow_GP

        self.env.set_local("sw1_GP", "")
        self.env.set_local("sw2_GP", ())
        if self.env.stages + self.env.scum == "YES":
            self.env.set_scoped("sow_GP", (g.ww,))
            self.env.set_scoped("swt_GP", (g.Sow,))
            # will never take effect as the previous set_local
            # overshadows the following set_scoped scope
            # likely a "bug" in GAMS TIMES
            self.env.set_scoped("sw1_GP", "S_")
            self.env.set_scoped("sw2_GP", ("1", g.Sow))

        sw1 = self.env.sw1_GP
        sw2 = self.env.sw2_GP

        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        vartt_id, domain = extract_var_domain(self.env.vartt_GP)
        VARTT_ACT = g.get_variable(name=f"{vartt_id}_ACT")

        sw1_flo_cum = g.get_parameter(f"{sw1}FLO_CUM")
        eq_cumflo, sow_domain = macro.EQ_CUMFLO_GP(self.env.eq, sow_domain)

        if self.env.obj.upper() != "LIN":
            condition = (g.e[g.t] >= g.yearval[g.allyear]).where[
                (g.b[g.t] <= g.yearval[g.ll])
            ]
        else:
            condition = (g.m[g.t] + g.lagt[g.t] > g.yearval[g.allyear]).where[
                (g.m[g.t] - g.lead[g.t] < g.yearval[g.ll])
            ]

        term1: MathOp | Sum
        if self.env.obj.upper() != "LIN":
            term1 = Max(
                0.0,
                Min(g.e[g.t], g.yearval[g.ll])
                - Max(g.b[g.t], g.yearval[g.allyear])
                + 1.0,
            )
        else:
            term1 = Sum(
                g.Tpulseyr[g.t, g.year].where[
                    ((Ord(g.year) >= Ord(g.allyear)).where[(Ord(g.year) <= Ord(g.ll))])
                ],
                g.tpulse[g.t, g.year],
            )

        include_cal_red = cal_red_func(
            g=g,
            config=CalRedRedConfig(
                arg1=g.c,
                arg2=g.Com,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                var=self.env.var,
                sow=self.env.sow_GP,
                pgprim=self.env.pgprim,
            ),
        )

        sow = self.env.sow_GP
        swt = self.env.swt_GP
        term2: Expression | Sum = (
            include_cal_red.where[g.RpStd[g.r, g.p]]
            + (
                Sum(
                    g.RpcIre[g.r, g.p, g.c, g.ie],
                    VAR_IRE[g.r, g.v, g.t, g.p, g.c, g.ts, g.ie, *sow],
                ).where[(~(g.RpcAire[g.r, g.p, g.c]))]
                + (
                    VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow]
                    * g.prc_actflo[g.r, g.v, g.p, g.c]
                ).where[g.RpcAire[g.r, g.p, g.c]]
            ).where[g.RpIre[g.r, g.p]]
        )

        if self.env.stages == "YES":
            term2 = wrap_in_sum(term2, self.env.swsw_GP)

        term3: MathOp | Sum
        if self.env.obj.upper() != "LIN":
            term3 = Max(
                0.0,
                Min(g.e[g.t], g.yearval[g.ll])
                - Max(g.b[g.t], g.yearval[g.allyear])
                + 1.0,
            )
        else:
            term3 = Sum(
                g.Tpulseyr[g.t, g.year].where[
                    ((Ord(g.year) >= Ord(g.allyear)).where[(Ord(g.year) <= Ord(g.ll))])
                ],
                g.tpulse[g.t, g.year],
            )

        term3_vartt = term3 * wrap_in_sum(
            VARTT_ACT[g.r, g.v, g.t, g.p, g.ts, *self.env.sws_GP], domain
        )

        eq_cumflo[g.RpcCumflo[g.Rp[g.r, g.p], g.c, g.allyear, g.ll], *sow_domain] = (
            # * all commodity/activity flows within period range
            Sum(
                g.tt[g.t].where[condition],
                Sum(
                    Domain(
                        g.RtpVintyr[g.r, g.v, g.t, g.p],
                        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts],
                    ),
                    term1 * (term2),
                ).where[g.Rpc[g.r, g.p, g.c]]
                + Sum(
                    Domain(
                        g.RtpVintyr[g.r, g.v, g.t, g.p],
                        g.RtpVara[g.r, g.t, g.p],
                        g.PrcTs[g.r, g.p, g.ts],
                    ),
                    term3_vartt,
                ).where[same_as(self.env.pgprim, g.c)],
            )
            / self.env.cufscal
            ==
            # * bound range working on
            macro.VAR_CUMFLO_GP(
                self.env.var, g.r, g.p, g.c, g.allyear, g.ll, swt
            ).where[
                (
                    map_value(sw1_flo_cum[g.r, g.p, g.c, g.allyear, g.ll, "UP", *sw2])
                    != 8.0
                )
            ]
        )
