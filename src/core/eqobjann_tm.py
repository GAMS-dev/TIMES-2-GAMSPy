# eqobjann_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJANN the objective function components for MACRO
# *   - Annualized costs for all components
# *=============================================================================*
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, Equation, Ord, Parameter, Set, Sum, Variable
from gamspy.math import diag

from core.base_class import GamsClass
from core.eqobjcst_tm import EqobjcstTm
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression, Number
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqobjannTmConfig:
    """Strongly typed data contract replacing the legacy positional BATINCLUDE args."""

    # %1 - suffix appended to the COEF_OBINV/COEF_OBFIX symbol names
    arg1: str = ""
    # %2 - multiplier trailing the investment/fixed tax and subsidy terms
    arg2: float = 1


class EqobjannTm(GamsClass):
    """Translation unit for eqobjann.tm."""

    # Instance attributes
    module_name: str = "eqobjann_tm"
    gams_source: str = "eqobjann.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqobjannTmConfig | None = None,
    ):
        self.env = env.fork()
        self.config = config if config is not None else EqobjannTmConfig()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        cc = self.config
        g = self.tc
        m = g.container

        if self.tc.defined(f"COEF_OBINV{cc.arg1}"):
            self._label_coef()
            return

        g.set_parameter(
            name=f"COEF_OBINV{cc.arg1}",
            parameter=Parameter(
                m, name=f"COEF_OBINV{cc.arg1}", domain=[g.r, g.year, g.p, g.cur]
            ),
        )
        g.set_parameter(
            name=f"COEF_OBFIX{cc.arg1}",
            parameter=Parameter(
                m, name=f"COEF_OBFIX{cc.arg1}", domain=[g.r, g.year, g.p, g.cur]
            ),
        )
        g.coef_crf = Parameter(m, name="COEF_CRF", domain=[g.r, g.allyear, g.p, g.cur])

        if cc.arg1 == "N":
            self._label_coef()
            return

        g.Obvann = Set(
            m,
            name="OBVANN",
            domain=[g.obv],
            records=["OBJINV", "OBJFIX", "OBJVAR"],
        )

        self.tc.enqueue(self.exec1)

        g.VAR_ANNCST = Variable(
            m,
            name="VAR_ANNCST",
            type="positive",
            domain=[g.obv, g.r, g.allyear, g.cur],
        )
        g.set_equation(
            name="EQ_OBJANN",
            eq=Equation(m, name="EQ_OBJANN", domain=[g.Obvann, g.Reg, g.cur]),
        )
        if not self.tc.declared("EQ_ANNFIX"):
            g.set_equation(
                name="EQ_ANNFIX",
                eq=Equation(m, name="EQ_ANNFIX", domain=[g.Reg, g.allyear, g.cur]),
            )
        if not self.tc.declared("EQ_ANNINV"):
            g.set_equation(
                name="EQ_ANNINV",
                eq=Equation(m, name="EQ_ANNINV", domain=[g.Reg, g.allyear, g.cur]),
            )
        if not self.tc.declared("EQ_ANNVAR"):
            g.set_equation(
                name="EQ_ANNVAR",
                eq=Equation(m, name="EQ_ANNVAR", domain=[g.Reg, g.allyear, g.cur]),
            )

        self.equation()

        self.include(EqobjcstTm(self.tc, self.env))

        self._label_coef()

    def equation(self) -> None:
        g = self.tc
        r, v, p, t, cur = g.r, g.v, g.p, g.t, g.cur
        Obvann = g.Obvann
        VAR_OBJ = g.VAR_OBJ

        eq_objann = g.eq_objann

        rhs: Expression | Sum = Sum(
            t, g.obj_pvt[r, t, cur] * g.VAR_ANNCST[Obvann, r, t, cur]
        )
        if g.defined(g.Vnret):
            rhs += Sum(
                g.ObjSums[r, v, p].where[g.rvprl[r, v, p]],
                g.objscc[r, v, p, cur]
                * g.obj_dceoh[r, cur]
                * (
                    g.VAR_NCAP[r, v, p].where[g.t[v]]
                    + g.ncap_pasti[r, v, p]
                    - g.VAR_SCAP[r, v, "0", p]
                ),
            ).where[diag(Obvann, "OBJINV")]

        eq_objann[Obvann, g.Rdcur[r, cur]] = VAR_OBJ[r, Obvann, cur] == rhs

    def exec1(self) -> None:
        g = self.tc

        g.sum_obj[g.obv["OBJSAL"], g.obv] = 0

    def exec3(
        self,
        arg1: str,
        capjd: ImplicitParameter | Number,
        arg2: float,
        anncost: str,
        capwd: ImplicitParameter | Number,
    ) -> None:
        g = self.tc
        r, v, p, t, tt, cur = g.r, g.v, g.p, g.t, g.tt, g.cur
        ll, k, y, age, life, jot = g.ll, g.k, g.Y, g.age, g.life, g.jot
        j, jj = g.j, g.jj
        KEoh, YEoh = g.KEoh, g.YEoh

        coef_obinv = g.get_parameter(f"COEF_OBINV{arg1}")
        coef_obfix = g.get_parameter(f"COEF_OBFIX{arg1}")
        coef_crf = g.coef_crf

        # * Calculate coefficients for annualized costs
        # * Investment costs: Commissioning years
        g.ObjSumsi.setRecords(None)
        g.fil2[v] = g.b[v] - g.yearval[v]
        g.ObjSumsi[g.Rtp[r, v[ll], p], ll + (g.fil2[v] + g.ncap_iled[r, v, p])] = True

        # * Annualizing coefficient for investment costs over years of capacity transfer
        coef_crf[g.ObjIcur[r, v, p, cur]] = Sum(
            g.RtpCptyr[r, tt[v], t, p], g.coef_cpt[r, v, t, p] * g.obj_pvt[r, t, cur]
        ) + Sum(
            g.ObjSumsi[r, g.Pastmile[v], p, k],
            g.obj_disc[r, k, cur]
            * (1 - (1 + g.g_drate[r, v, cur]) ** (-g.ncap_tlife[r, v, p]))
            / (1 - (1 / (1 + g.g_drate[r, v, cur]))),
        )

        # * Investment cost coefficient
        coef_obinv[g.ObjIcur[r, v, p, cur]] = (1 / coef_crf[r, v, p, cur]).where[
            coef_crf[r, v, p, cur]
        ] * (
            # * Cases I - Investment Cost and II - Taxes/Subsidies
            Sum(
                g.ObjSumii[r, v, p, life, KEoh, jot],
                capjd
                * Sum(
                    g.Invspred[KEoh, jot, ll, k],
                    g.obj_disc[r, k, cur]
                    * (1 - g.salv_inv[r, v, p, ll].where[t[v]])
                    * (
                        macro.obj_icost_GP(r, k, p, cur)
                        + (
                            macro.obj_itax_GP(r, k, p, cur)
                            - macro.obj_isub_GP(r, k, p, cur)
                        )
                        * arg2
                    ),
                )
                * g.cor_salvi[r, v, p, cur]
                / g.obj_divi[r, v, p],
            )
            # * Cases III - Decommissioning
            + Sum(
                g.ObjSumiii[r, v, p, ll, k, y].where[macro.obj_dcost_GP(r, v, p, cur)],
                g.obj_disc[r, y, cur]
                * g.cor_salvd[r, v, p, cur]
                * macro.obj_dcost_GP(r, k, p, cur)
                / g.obj_diviii[r, v, p],
            )
        )

        coef_obinv[g.ObjIcur[r, g.Pastmile[v], p, cur]].where[
            g.prc_resid[r, "0", p]
        ] = g.obj_crf[r, v, p, cur] * (
            macro.obj_icost_GP(r, v, p, cur)
            + (macro.obj_itax_GP(r, v, p, cur) - macro.obj_isub_GP(r, v, p, cur)) * arg2
        )

        # *----------------------------------------------------------------------------
        # * Fixed costs: Annualizing coefficient for costs over years of capacity transfer
        coef_crf[g.ObjFcur[r, v, p, cur]] = Sum(
            g.RtpCptyr[r, v, t, p], g.coef_cpt[r, v, t, p] * g.obj_pvt[r, t, cur]
        )
        if anncost.upper() != "LEV":
            coef_crf[g.ObjFcur[r, g.Pastmile[v], p, cur]] = Sum(
                g.ObjSumiv[KEoh, r, v, p, jot, life],
                g.obj_life[KEoh, r, jot, life, cur],
            )

        # * Fixed cost coefficient
        coef_obfix[g.ObjFcur[r, v, p, cur]] = (1 / coef_crf[r, v, p, cur]).where[
            coef_crf[r, v, p, cur]
        ] * (
            # * Case IV - Fixed O&M Cost and Taxes
            Sum(
                g.ObjSumiv[KEoh, r, v, p, jot, life].where[~g.RtpIshpr[r, v, p]],
                Sum(
                    g.Invspred[KEoh, jot, ll, k],
                    g.obj_life[ll, r, jot, life, cur]
                    * capwd
                    * (
                        macro.obj_fom_GP(r, k, p, cur)
                        + (
                            macro.obj_ftx_GP(r, k, p, cur)
                            - macro.obj_fsb_GP(r, k, p, cur)
                        )
                        * arg2
                    ),
                )
                / g.obj_diviv[r, v, p],
            )
            + Sum(
                g.ObjSumiv[KEoh, g.RtpIshpr[r, v, p], jot, life],
                Sum(
                    Domain(
                        g.Invspred[KEoh, jot, ll, k],
                        g.Opyear[life, age],
                        YEoh[ll + (Ord(age) - 1)],
                    ),
                    g.obj_disc[r, YEoh, cur]
                    * (
                        1
                        + Sum(g.Periodyr[t, YEoh], g.rtp_cpx[r, v, p, t]).where[
                            g.ncap_cpx[r, v, p]
                        ]
                    )
                    * capwd
                    * (
                        macro.obj_fom_GP(r, k, p, cur)
                        * (
                            1
                            + Sum(
                                g.RtpShape[r, v, p, "1", j, jj],
                                g.shape[j, age] * g.multi[jj, YEoh] - 1,
                            )
                        )
                        + macro.obj_ftx_GP(r, k, p, cur)
                        * (
                            1
                            + Sum(
                                g.RtpShape[r, v, p, "2", j, jj],
                                g.shape[j, age] * g.multi[jj, YEoh] - 1,
                            )
                        )
                        * arg2
                        - macro.obj_fsb_GP(r, k, p, cur)
                        * (
                            1
                            + Sum(
                                g.RtpShape[r, v, p, "3", j, jj],
                                g.shape[j, age] * g.multi[jj, YEoh] - 1,
                            )
                        )
                        * arg2
                    ),
                )
                / g.obj_diviv[r, v, p],
            )
            # * Case V - Decommissioning Surveillance
            + Sum(
                g.ObjSumivs[r, v, p, k, y],
                g.obj_disc[r, y, cur] * macro.obj_dlagc_GP(r, k, p, cur),
            )
        )

        coef_obfix[g.ObjFcur[r, g.Pastmile[v], p, cur]].where[
            g.prc_resid[r, "0", p]
        ] = (
            coef_obfix[r, v, p, cur]
            * coef_crf[r, v, p, cur]
            / Sum(
                g.Vnt[v, t].where[g.prc_resid[r, t, p]],
                g.prc_resid[r, t, p] / g.ncap_pasti[r, v, p] * g.obj_pvt[r, t, cur],
            )
        )
        # *=============================================================================
        g.ObjSumsi.setRecords(None)
        coef_crf.setRecords(None)

    def _label_coef(self) -> None:
        self.tc.enqueue(
            self.exec3,
            arg1=self.config.arg1,
            capjd=self.env.capjd_GP,
            arg2=self.config.arg2,
            anncost=self.env.anncost,
            capwd=self.env.capwd_GP,
        )
