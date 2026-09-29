# ucbet_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UCBET.vda Derivation of maximum activities and flows according to UCBET     *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Else, If, Loop, Number, Set, Sum, UniverseAlias
from gamspy.math import same_as

from core.base_class import GamsClass
from core.cal_nored_red import cal_nored_red_GP
from core.cal_red_red import CalRedRedConfig, cal_red_red_GP

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class UcbetVda(GamsClass):
    """Translation unit for ucbet.vda."""

    # Instance attributes
    module_name: str = "ucbet_vda"
    gams_source: str = "ucbet.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        ucn, allr, item, c, r, p, v, t, s, com = (
            g.ucn,
            g.allr,
            g.item,
            g.c,
            g.r,
            g.p,
            g.v,
            g.t,
            g.s,
            g.Com,
        )

        # * Preprocessing of UC_FLOBET:
        g.UcGmax = Set(m, name="UC_GMAX", domain=[ucn, allr, item, c, item])
        g.UcGmaxR = Set(m, name="UC_GMAXR", domain=[allr, ucn])
        g.name = UniverseAlias(m, name="NAME")

        self.tc.enqueue(
            self.ucbet_exec,
            pgprim=self.env.pgprim,
        )

        # * [UR] model reduction REDUCE is set in *.run
        cal_red_config = CalRedRedConfig(
            var=self.env.var,
            sow=self.env.sow_GP,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            arg1=com,
            arg2=g.com1,
            arg3=s,
            arg4=p,
            arg5=t,
            arg10=Number(1),
        )
        if self.env.cal_red == "cal_nored.red":
            cal_red_term = cal_nored_red_GP(g=g, config=cal_red_config)
        else:
            cal_red_term = cal_red_red_GP(g=g, config=cal_red_config)

        swtd2 = self.env.swtd_GP
        sow2 = self.env.sow_GP
        if self.env.stages == "YES":
            swtd2 = (g.SwTsw[g.Sow, t, g.w],)
            sow2 = (g.w,)

        VAR_UC = g.get_variable(f"{self.env.var}_UC")
        VAR_UCR = g.get_variable(f"{self.env.var}_UCR")
        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")

        # *....Time Mutiplier
        time_mult = (
            g.fpd[t]
            + (g.coef_pvt[r, t] - g.fpd[t]).where[
                g.UcAttr[r, ucn, "LHS", "ACT", "PERDISC"]
            ]
        )

        flow_term = Sum(
            g.RtpcsVarf[r, t, p, com, s].where[
                g.ComGmap[r, c, com] & g.uc_flobet[ucn, r, t, p, c]
            ],
            g.uc_flobet[ucn, r, t, p, c]
            * Sum(
                g.RtpVintyr[r, v, t, p],
                cal_red_term.where[g.RpStd[r, p]]
                # *....For IRE processes, sum Import flows only
                + Sum(
                    g.RpcIre[r, p, com, g.ie["IMP"]],
                    VAR_IRE[r, v, t, p, com, s, g.ie, *sow2].where[
                        ~g.RpcAire[r, p, com]
                    ]
                    + (
                        VAR_ACT[r, v, t, p, s, *sow2] * g.prc_actflo[r, v, p, com]
                    ).where[g.RpcAire[r, p, com]],
                ).where[g.RpIre[r, p]],
            ),
        )

        activity_term = Sum(
            g.RtpVintyr[r, v, t, p[item]].where[
                g.uc_flobet[ucn, r, t, p, self.env.pgprim]
            ],
            g.uc_flobet[ucn, r, t, p, self.env.pgprim]
            * (
                # *........For Standard processes, sum activities
                Sum(
                    Domain(g.RtpVara[r, t, p], g.PrcTs[r, p, s]),
                    VAR_ACT[r, v, t, p, s, *sow2],
                ).where[g.RpStd[r, p]]
                # *........For IRE processes, sum Import flows only
                + Sum(
                    Domain(
                        g.RpcIre[r, p, com, g.ie["IMP"]],
                        g.RtpcsVarf[r, t, p, com, s],
                    ),
                    VAR_IRE[r, v, t, p, com, s, g.ie, *sow2].where[
                        ~g.RpcAire[r, p, com]
                    ]
                    + (
                        VAR_ACT[r, v, t, p, s, *sow2] * g.prc_actflo[r, v, p, com]
                    ).where[g.RpcAire[r, p, com]],
                ).where[g.RpIre[r, p]]
            ),
        )

        # * Select variable to be maximized (remove SUM if IMPEXP group allowed)
        select_var = VAR_UC[ucn, *self.env.sow_GP].where[~g.UcGmaxR[allr, ucn]] + Sum(
            r.where[r[allr]],
            VAR_UCR[ucn, r, *self.env.sow_GP].where[g.UcGmaxR[allr, ucn]],
        )

        # * Sum of flows by region
        flows_by_region = Sum(
            Domain(g.UcTSum[g.UcGmaxR[r[allr], ucn], t], *swtd2),
            time_mult * flow_term,
        ).where[g.lim[g.name]]

        # * Sum of flows globally
        flows_globally = Sum(
            Domain(g.UcTSum[r, ucn, t], *swtd2).where[~g.UcGmaxR[r, ucn]],
            time_mult * flow_term,
        ).where[(~g.Reg[allr]) & g.lim[g.name]]

        # * Sum of activities by region
        activities_by_region = Sum(
            Domain(g.UcTSum[r[allr], ucn, t], *swtd2),
            time_mult * activity_term,
        ).where[g.ucnumber[g.name]]

        # * Sum of activities globally
        activities_globally = Sum(
            Domain(g.UcTSum[r, ucn, t], *swtd2).where[~g.Reg[allr]],
            time_mult * activity_term,
        ).where[(~g.Reg[allr]) & g.ucnumber[g.name]]

        eq_ucmax = g.get_equation(f"{self.env.eq}G_UCMAX")
        eq_ucmax[g.UcGmax[ucn, allr, item, c, g.name], *self.env.sow_GP] = (
            select_var
            >= flows_by_region
            + flows_globally
            + activities_by_region
            + activities_globally
        )

        # *-----------------------------------------------------------------------------
        # * Sum regional maximums to global (change R to ALL_R if IMPEXP allowed)
        eq_ucsumax = g.get_equation(f"{self.env.eq}G_UCSUMAX")
        eq_ucsumax[ucn, *self.env.sow_GP].where[Sum(g.UcGmaxR[allr, ucn], 1)] = VAR_UC[
            ucn, *self.env.sow_GP
        ] >= Sum(g.UcGmaxR[r, ucn], VAR_UCR[ucn, r, *self.env.sow_GP])
        # *-----------------------------------------------------------------------------

    def ucbet_exec(self: UcbetVda, pgprim: str) -> None:
        g = self.tc
        ucn, allr, r, t, p, c, s, item, name = (
            g.ucn,
            g.allr,
            g.r,
            g.t,
            g.p,
            g.c,
            g.s,
            g.item,
            g.name,
        )

        # * Collect set of all regional cumulative UC_N
        g.uncd1.setRecords(None)
        with Loop(Domain(ucn, r, t, p, c).where[g.uc_flobet[ucn, r, t, p, c]]):
            g.uncd1[ucn] = True
        g.UcGmaxR[g.UcREach] = True
        g.UcRSum[r, ucn[g.uncd1]] = True

        # * Set Equation controls
        with Loop(Domain(ucn, r, t, p, c).where[g.uc_flobet[ucn, r, t, p, c]]):
            with If(same_as(pgprim, c)):
                with If(g.UcAttr[r, ucn, "LHS", "ACT", "N"]):
                    g.UcGmax[ucn, "IMPEXP", p, c, "EACH"] = True
                with Else():
                    g.UcGmax[ucn, r, p, c, "EACH"] = True
            with Else():
                with If(g.UcGmaxR[r, ucn]):
                    g.UcGmax[ucn, r, "N", c, "N"] = True
                with Else():
                    g.UcGmax[ucn, "IMPEXP", "N", c, "N"] = True

        # * If IMPEXP should be one group, add IMPEXP for regional UC_N
        with Loop(r):
            g.UcGmaxR["IMPEXP", ucn].where[g.UcGmaxR[r, ucn]] = True
        # * Remove all (ALL_R,UC_N) not used in betting parameters
        g.Rxx.setRecords(None)
        with Loop(g.UcGmax[ucn, allr, item, c, name]):
            g.Rxx["IMPEXP", ucn, allr] = True
        g.UcGmaxR[allr, ucn].where[~g.Rxx["IMPEXP", ucn, allr]] = False
        # * Remove EQE_UC equations for maxed UC_N
        g.UcTsSum[r, ucn[g.uncd1], s] = False
