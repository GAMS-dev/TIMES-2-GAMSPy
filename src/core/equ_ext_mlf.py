# equ_ext_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * equ_ext.mlf - Equation formulations for MLF
# *-----------------------------------------------------------------------------
# * Calibration equations
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import If, Loop, Ord, Smax, SpecialValues, Sum, set_options, sparse
from gamspy.math import Max, Min, abs, log

from core.base_class import GamsClass
from core.calibase_mlf import CalibaseMlf
from core.presolve_mlf import PresolveMlf

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtMlf(GamsClass):
    """Translation unit for equ_ext.mlf."""

    # Instance attributes
    module_name: str = "equ_ext_mlf"
    gams_source: str = "equ_ext.mlf"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        # Calibration equations
        self.utility_objective_function()
        self.production_function()
        self.akl_aggregate()
        self.labor_resource()
        self.capital_dynamics_equation()
        self.capital_dummy_definition()
        self.terminal_condition_investment()
        self.bound_sum_of_investment_and_energy()
        self.demand_coupling_equation()
        self.energy_system_costs()
        self.trade_balance()

        # Variable bounds
        self.tc.enqueue(self.set_variable_bounds)

        self.include(CalibaseMlf(tc=self.tc, env=self.env))

        self.tc.enqueue(
            self.exec1,
            fixboh_set=self.env.is_set("fixboh"),
            fixboh=self.env.fixboh,
            reg_bdncap_defined=self.tc.defined("REG_BDNCAP"),
        )

        kestrel = self.env.kestrel.split(".")
        if len(kestrel) == 2:
            self.env.set_scoped("x1", kestrel[0])
            self.env.set_scoped("x2", kestrel[1])
        else:
            # Mirrors GAMS's own behavior for an unset %KESTREL%: an undefined
            # dollar variable substitutes to an empty string, so
            # `$SETCOMPS %KESTREL% X1 X2 .` yields blank X1/X2 rather than
            # erroring, and the downstream `%X2%==LP` / `%X1%%X2%==NLP` checks
            # simply don't match.
            self.env.set_scoped("x1", "")
            self.env.set_scoped("x2", "")

        if self.env.nonlp.upper() != "NL":
            self.include(PresolveMlf(tc=self.tc, env=self.env))
            if self.env.x2.upper() == "LP":
                self.tc.enqueue(self.option_lp)

            self.full_model_equations()

        self.nlp_equations()

        self.tc.enqueue(self.full_model_bounds)

        if self.env.nonlp.upper() == "NL":
            if f"{self.env.x1}{self.env.x2}".upper() == "NLP":
                self.tc.enqueue(self.option_nlp)
            self.tc.enqueue(self.exec2)

    def utility_objective_function(self: EquExtMlf) -> None:
        """Utility Objective Function"""
        g = self.tc

        g.eq_util[...] = (
            Sum(
                g.Mr[g.r],
                Sum(
                    g.t,
                    g.tm_nwt[g.r]
                    * g.tm_pwt[g.t]
                    * g.tm_dfact[g.r, g.t]
                    * log(g.VAR_C[g.r, g.t]),
                ),
            )
            == g.VAR_UTIL * Max(1.0, log(g.tm_scale_util * 1000.0)) / 1000.0
        )

    def production_function(self: EquExtMlf) -> None:
        """Production Function"""
        g = self.tc
        g.eq_prod_y[g.Mr[g.r], g.t] = g.VAR_C[g.r, g.t] + g.VAR_INV[
            g.r, g.t
        ] + g.VAR_EC[g.r, g.t] + g.VAR_NTX[g.r, g.t].where[g.Pp[g.t]] == (
            (
                g.tm_akl[g.r] * (g.VAR_D[g.r, g.t, "AKL"] ** g.tm_rho[g.r])
                + Sum(
                    g.Dm, g.tm_b[g.r, g.Dm] * (g.VAR_D[g.r, g.t, g.Dm] ** g.tm_rho[g.r])
                )
            )
            ** (1.0 / g.tm_rho[g.r])
        )

    def akl_aggregate(self: EquExtMlf) -> None:
        """AKL aggregate"""
        g = self.tc
        g.eq_akl[g.Mr[g.r], g.t] = g.VAR_D[g.r, g.t, "AKL"] == (
            g.VAR_D[g.r, g.t, "KN"] ** (g.tm_kpvs[g.r])
        ) * (g.VAR_D[g.r, g.t, "LAB"] ** (1.0 - g.tm_kpvs[g.r]))

    def labor_resource(self: EquExtMlf) -> None:
        """Labor resource"""
        g = self.tc
        g.eq_labor[g.Mr[g.r], g.t] = g.VAR_D[g.r, g.t, "LAB"] == g.tm_l[g.r, g.t]

    def capital_dynamics_equation(self: EquExtMlf) -> None:
        """Capital Dynamics Equation"""
        g = self.tc
        g.eq_mcap[g.Mr[g.r], g.Pp[g.t + 1]] = (
            g.VAR_K[g.r, g.Pp]
            == g.VAR_K[g.r, g.t] * g.tm_tsrv[g.r, g.t]
            + (
                g.d[g.t + 1] * g.VAR_INV[g.r, g.t + 1]
                + g.tm_tsrv[g.r, g.t] * g.d[g.t] * g.VAR_INV[g.r, g.t]
            )
            / 2.0
        )

    def capital_dummy_definition(self: EquExtMlf) -> None:
        """Capital dummy definition"""
        g = self.tc
        g.eq_kncap[g.Mr[g.r], g.t] = g.VAR_D[g.r, g.t, "KN"] == g.VAR_K[g.r, g.t]

    def terminal_condition_investment(self: EquExtMlf) -> None:
        """Terminal Condition for investment in last period"""
        g = self.tc
        g.eq_tmc[g.Mr[g.r], g.Tlast[g.t]] = (
            g.VAR_K[g.r, g.t] * (g.tm_growv[g.r, g.t] + g.tm_depr[g.r]) / 100.0
            <= g.VAR_INV[g.r, g.t]
        )

    def bound_sum_of_investment_and_energy(self: EquExtMlf) -> None:
        """Bound on Sum of Investment and Energy"""
        g = self.tc
        g.eq_ivecbnd[g.Mr[g.r], g.Pp[g.t]] = g.VAR_INV[g.r, g.t] + g.VAR_EC[
            g.r, g.t
        ] <= g.tm_y0[g.r] * (g.tm_l[g.r, g.t] ** g.tm_ivetol[g.r])

    def demand_coupling_equation(self: EquExtMlf) -> None:
        """Demand Coupling Equation"""
        g = self.tc

        g.eq_dd[g.Mr[g.r], g.Pp[g.t], g.c["ACT"]] = g.VAR_DEM[g.r, g.t, g.c] == (
            (1.0 / g.tm_scale_nrg)
            * (
                g.tm_aeeifac[g.r, g.t, g.c] * g.VAR_D[g.r, g.t, g.c]
                + g.VAR_SP[g.r, g.t, g.c]
            )
        )

    def energy_system_costs(self: EquExtMlf) -> None:
        """Energy System Costs"""
        g = self.tc
        g.eq_escost[g.Mr[g.r], g.Pp[g.t]] = (
            Sum(
                g.Dm["ACT"],
                g.tm_qsfa[g.r, g.t]
                + g.tm_qsfb[g.r, g.t, g.Dm] * (g.VAR_DEM[g.r, g.t, g.Dm] ** 2.0),
            )
            + g.tm_amp[g.r, g.t]
            == g.VAR_EC[g.r, g.t] * g.tm_hdf[g.r, g.t]
        )

    def trade_balance(self: EquExtMlf) -> None:
        """Trade balance"""
        g = self.tc
        g.eq_trdbal[g.Pp] = Sum(g.Mr[g.r], g.VAR_NTX[g.r, g.Pp]) == 0.0

    def set_variable_bounds(self: EquExtMlf) -> None:
        g = self.tc
        # * Variable bounds
        g.VAR_D.lo[g.Mr[g.r], g.t, g.Dm] = g.tm_dmtol[g.r] * g.tm_d0[g.r, g.Dm]
        g.VAR_D.l[g.Mr[g.r], g.Pp, g.Dm] = g.tm_d0[g.r, g.Dm]
        g.VAR_D.fx[g.Mr[g.r], g.t[g.tb], g.Dm] = g.tm_d0[g.r, g.Dm]
        g.VAR_DEM.fx[g.Mr, g.t[g.tb], g.Dm] = g.tm_dem[g.Mr, g.t, g.Dm]
        with Loop(g.Mr[g.r]):
            g.z[...] = g.tm_k0[g.r] * g.tm_depr[g.r] / 100.0
            with Loop(g.Pp[g.t + 1]):
                g.z[...] = g.z * g.tm_tsrv[g.r, g.t]
                g.VAR_INV.lo[g.r, g.Pp] = g.z
        g.VAR_INV.l[g.Mr, g.Pp] = g.tm_iv0[g.Mr] * g.tm_l[g.Mr, g.Pp]
        g.VAR_INV.fx[g.Mr, g.t[g.tb]] = g.tm_iv0[g.Mr]
        g.VAR_D.lo[g.Mr, g.t, "AKL"] = Min(1.0, g.tm_k0[g.Mr]) / 2.0
        g.VAR_D.lo[g.Mr, g.t, "KN"] = g.tm_k0[g.Mr] * 0.33
        g.VAR_D.lo[g.Mr, g.t, "LAB"] = g.tm_l[g.Mr, g.t] / 2.0
        g.VAR_K.fx[g.Mr, g.t[g.tb]] = g.tm_k0[g.Mr]
        g.VAR_C.l[g.Mr, g.tp] = g.tm_gdp0[g.Mr] - g.tm_iv0[g.Mr]
        g.VAR_C.lo[g.Mr, g.tp] = g.tm_gdp0[g.Mr] * 0.33
        g.VAR_SP.fx[g.Mr, g.tp, g.Dm] = 0.0
        g.VAR_EC.lo[g.Mr, g.Pp] = g.tm_annc[g.Mr, g.Pp] * 0.33
        g.VAR_EC.lo[g.Mr, g.t[g.tb]] = g.tm_ec0[g.Mr] + g.tm_amp[g.Mr, g.tb]
        # * set the bounds for the step variables for quad approx, clearing first
        g.VAR_XCAPP.up[g.Rtp, g.j] = SpecialValues.POSINF
        g.VAR_XCAPP.up[g.Rtp, g.Xcp[g.j]].where[Ord(g.j) < 7.0] = sparse(
            g.tm_expbnd[g.Rtp]
        )

    def exec1(
        # copied fixboh usage from solve_stp
        self: EquExtMlf,
        fixboh_set: bool,
        fixboh: int,
        reg_bdncap_defined: bool,
    ) -> None:
        g = self.tc
        if fixboh_set:
            with Loop(g.r):
                g.z[...] = g.reg_fixt[g.r]
                with If(g.z == 0.0):
                    g.z[...] = abs(fixboh)
                g.TmPp[g.r, g.t].where[g.m[g.t] <= g.z] = False

        if reg_bdncap_defined:
            with Loop(g.bd):
                g.TmPp[g.r, g.t].where[
                    (g.m[g.t] <= g.reg_bdncap[g.r, g.bd]).where[g.reg_bdncap[g.r, g.bd]]
                ] = False

    def option_lp(self: EquExtMlf) -> None:
        # Options.fromGams({"LP": "KESTREL"})
        # NOTE: # OPTION LP=KESTREL is overridden by solve.mod's `option lp=cplex, mip=cplex;`
        # before any LP solve, so it has no effect.
        self.tc.solve_options.lp = "KESTREL"

    def option_nlp(self: EquExtMlf) -> None:
        # Options.fromGams({"NLP": "KESTREL"})
        self.tc.solve_options.nlp = "KESTREL"

    def full_model_equations(self: EquExtMlf) -> None:
        self.utility_objective_function2()
        self.consumption()
        self.consumption_disaggregation()
        self.consumption_log_steps()
        self.macro_ces_function_shares()
        self.macro_ces_function_aggregation()
        self.macro_ces_function_constraint()
        self.demand_ces_function_shares()
        self.demand_ces_aggregation()
        self.demand_linear_ces_function_constraint()

    def nlp_equations(self: EquExtMlf) -> None:
        self.demand_non_linear_ces_function()
        self.energy_system_costs_nlp()

    def utility_objective_function2(self: EquExtMlf) -> None:
        """Utility Objective Function"""
        g = self.tc
        g.eq_utilp[...] = (
            Sum(
                g.Mr[g.r],
                Sum(
                    g.t,
                    g.tm_nwt[g.r]
                    * g.tm_pwt[g.t]
                    * g.tm_dfact[g.r, g.t]
                    * (
                        log(g.tm_midcon[g.r, g.t])
                        - Sum(
                            g.Logj[g.j, g.bd],
                            g.bdsig[g.bd]
                            * g.VAR_MELA[g.r, g.t, "CON", g.j, g.bd]
                            / g.tm_lsc,
                        )
                    ),
                ),
            )
            + Sum(
                g.r.where[(~(g.Mr[g.r]))],
                Sum(
                    g.t,
                    (
                        3.0 * g.tm_annc[g.r, g.t]
                        - g.VAR_OBJCOST[g.r, g.t] * g.tm_scale_cst
                    )
                    * g.tm_udf[g.r, g.t],
                ),
            )
            == g.VAR_UTIL * Max(1.0, log(g.tm_scale_util * 1000.0)) / 1000.0
        )

    def consumption(self: EquExtMlf) -> None:
        """Consumption"""
        g = self.tc
        g.eq_conso[g.Mr[g.r], g.t] = (
            g.VAR_D[g.r, g.t, "YN"]
            == g.VAR_C[g.r, g.t]
            + g.VAR_INV[g.r, g.t]
            + g.VAR_EC[g.r, g.t]
            + g.VAR_NTX[g.r, g.t].where[g.Pp[g.t]]
        )

    def consumption_disaggregation(self: EquExtMlf) -> None:
        """Consumption disaggregation"""
        g = self.tc
        g.eq_conda[g.Mr[g.r], g.t] = g.VAR_C[g.r, g.t] == g.tm_midcon[g.r, g.t] * (
            1.0
            - Sum(
                g.Logj[g.j, g.bd],
                g.VAR_MELA[g.r, g.t, "CON", g.j, g.bd]
                * g.tm_logval[g.j, g.bd]
                / g.tm_lsc,
            )
        )

    def consumption_log_steps(self: EquExtMlf) -> None:
        """Consumption LOG steps constraint"""
        g = self.tc
        g.eq_logbd[g.Mr[g.r], g.t] = (
            Sum(
                g.Logj[g.j, g.bd],
                g.VAR_MELA[g.r, g.t, "CON", g.j, g.bd] / Ord(g.j) / g.tm_logjot,
            )
            <= g.tm_lsc
        )

    def macro_ces_function_shares(self: EquExtMlf) -> None:
        """Macro CES function shares"""
        g = self.tc
        g.eq_macsh[g.Mr[g.r], g.t, g.TmDmas[g.cg, g.cg1]] = (
            g.VAR_D[g.r, g.t, g.cg1]
            + Sum(
                g.TmRcj[g.r, g.cg1, g.j, g.bd].where[g.TmPp[g.r, g.t]],
                g.bdsig[g.bd] * g.VAR_MELA[g.r, g.t, g.cg1, g.j, g.bd],
            )
            == g.tm_shar[g.r, g.t, g.cg, g.cg1]
            * g.VAR_D[g.r, g.t, g.cg]
            / g.tm_cie[g.r, g.t, g.cg]
        )

    def macro_ces_function_aggregation(self: EquExtMlf) -> None:
        """Macro CES function aggregation"""
        g = self.tc
        g.eq_macag[g.TmPp[g.Mr[g.r], g.t], g.TmCes[g.cg]] = (
            Sum(
                g.TmRcj[g.r, g.cg1, g.j, g.Bdneq[g.bd]].where[g.TmDmas[g.cg, g.cg1]],
                (
                    g.tm_pref[g.r, g.t, g.cg1]
                    * (g.tm_agc[g.r, g.t, g.cg, g.cg1, g.j, g.bd] - 1.0)
                    + g.tm_shar[g.r, g.t, g.cg1, g.cg]
                )
                * g.bdsig[g.bd]
                * g.VAR_MELA[g.r, g.t, g.cg1, g.j, g.bd],
            )
            == 0.0
        )

    def macro_ces_function_constraint(self: EquExtMlf) -> None:
        """Macro CES function constraint"""
        g = self.tc
        g.eq_maces[g.TmPp[g.Mr[g.r], g.t], g.TmDmas[g.cg, g.cg1]] = Sum(
            g.TmRcj[g.r, g.cg1, g.j, g.Bdneq[g.bd]],
            g.VAR_MELA[g.r, g.t, g.cg1, g.j, g.bd]
            * g.tm_step[g.r, g.cg1, g.bd]
            / Ord(g.j)
            / (g.tm_qref[g.r, g.t, g.cg1] * g.tm_voc[g.r, g.t, g.cg1, g.bd]),
        ) <= (
            g.VAR_D[g.r, g.t, g.cg]
            / g.tm_cie[g.r, g.t, g.cg]
            / g.tm_ceslev[g.r, g.t, g.cg]
        )

    def demand_ces_function_shares(self: EquExtMlf) -> None:
        """Demand CES function shares"""
        g = self.tc
        # MAG(CG) and VAR_DEM's C domain are sibling subsets of COM_GRP, which
        # GAMS accepts as domain-compatible but GAMSPy's stricter domain
        # validation rejects (only ancestor/descendant chains are allowed).
        set_options({"VALIDATION": 0})  # TODO: Remove in future GAMSPY version
        g.eq_demsh[g.Mr[g.r], g.Pp[g.t], g.c].where[g.TmDm[g.r, g.c]] = g.VAR_DEM[
            g.r, g.t, g.c
        ] + Sum(
            g.TmRcj[g.r, g.c, g.j, g.bd].where[g.TmPp[g.r, g.t]],
            g.bdsig[g.bd] * g.VAR_MELA[g.r, g.t, g.c, g.j, g.bd],
        ) == Sum(
            g.Mag["ACT"], g.tm_shar[g.r, g.t, g.Mag, g.c] * g.VAR_DEM[g.r, g.t, g.Mag]
        )
        set_options({"VALIDATION": 1})  # TODO: Remove in future GAMSPY version

    def demand_ces_aggregation(self: EquExtMlf) -> None:
        """Demand CES aggregation"""
        g = self.tc
        # MAG(CG) and TM_AGC/TM_SHAR's C domain are sibling subsets of
        # COM_GRP, which GAMS accepts as domain-compatible but GAMSPy's
        # stricter domain validation rejects (only ancestor/descendant
        # chains are allowed).
        set_options({"VALIDATION": 0})  # TODO: Remove in future GAMSPY version
        g.eq_demag[g.TmPp[g.Mr[g.r], g.t]] = (
            Sum(
                g.TmRcj[g.r, g.c, g.j, g.Bdneq[g.bd]].where[g.TmDm[g.r, g.c]],
                Sum(
                    g.Mag["ACT"],
                    (
                        g.tm_pref[g.r, g.t, g.c]
                        * (g.tm_agc[g.r, g.t, g.Mag, g.c, g.j, g.bd] - 1.0)
                        + g.tm_shar[g.r, g.t, g.c, g.Mag]
                    )
                    * g.bdsig[g.bd]
                    * g.VAR_MELA[g.r, g.t, g.c, g.j, g.bd],
                ),
            )
            == 0.0
        )
        set_options({"VALIDATION": 1})  # TODO: Remove in future GAMSPY version

    def demand_linear_ces_function_constraint(self: EquExtMlf) -> None:
        """Demand linear CES function constraint"""
        g = self.tc
        # MAG(CG) and VAR_DEM/TM_DEM's C domain are sibling subsets of
        # COM_GRP, which GAMS accepts as domain-compatible but GAMSPy's
        # stricter domain validation rejects (only ancestor/descendant
        # chains are allowed).
        set_options({"VALIDATION": 0})  # TODO: Remove in future GAMSPY version
        g.eq_demces[g.TmPp[g.Mr[g.r], g.t], g.c].where[g.TmDm[g.r, g.c]] = Sum(
            g.TmRcj[g.r, g.c, g.j, g.Bdneq[g.bd]],
            g.VAR_MELA[g.r, g.t, g.c, g.j, g.bd]
            * g.tm_step[g.r, g.c, g.bd]
            / Ord(g.j)
            / (g.tm_qref[g.r, g.t, g.c] * g.tm_voc[g.r, g.t, g.c, g.bd]),
        ) <= Sum(g.Mag["ACT"], (g.VAR_DEM[g.r, g.t, g.Mag] / g.tm_dem[g.r, g.t, g.Mag]))
        set_options({"VALIDATION": 1})  # TODO: Remove in future GAMSPY version

    def demand_non_linear_ces_function(self: EquExtMlf) -> None:
        """Demand non-linear CES function constraint"""
        g = self.tc
        g.eq_dnlces[g.Mr[g.r], g.Pp[g.t]] = g.VAR_DEM[g.r, g.t, "ACT"] == g.tm_dem[
            g.r, g.t, "ACT"
        ] * (
            Sum(
                g.TmDm[g.r, g.c],
                g.tm_cie[g.r, g.t, g.c]
                * (
                    (g.VAR_DEM[g.r, g.t, g.c] / g.tm_dem[g.r, g.t, g.c])
                    ** (1.0 - 1.0 / g.tm_desub[g.r])
                ),
            )
            ** (g.tm_desub[g.r] / (g.tm_desub[g.r] - 1.0))
        )

    def energy_system_costs_nlp(self: EquExtMlf) -> None:
        """Energy System costs"""
        g = self.tc
        g.eq_enscst[g.Mr[g.r], g.t] = (
            g.tm_scale_cst * g.VAR_OBJCOST[g.r, g.t]
            + g.tm_amp[g.r, g.t]
            + g.VAR_SP[g.r, g.t, "DEM"].where[(~(g.TmPp[g.r, g.t]))]
            # * Credit for lump-sum rebate of tax revenues
            - g.tm_scale_cst * g.tm_taxrev[g.r, g.t]
            # * quadratic market penetration curves (pending)
            + 0.0
            == g.VAR_EC[g.r, g.t] * g.tm_hdf[g.r, g.t]
        )

    def full_model_bounds(self: EquExtMlf) -> None:
        """Full model bounds"""
        g = self.tc
        g.VAR_DEM.fx[g.r, g.t, g.c].where[
            ((~(g.TmDm[g.r, g.c].where[g.Mr[g.r]])).where[g.Dem[g.r, g.c]])
        ] = g.com_proj[g.r, g.t, g.c]
        g.VAR_DEM.fx[g.Mr[g.r], g.t[g.tb], g.c].where[g.TmDm[g.r, g.c]] = g.tm_dem[
            g.r, g.t, g.c
        ]
        g.VAR_EC.up[g.Mr, g.t] = SpecialValues.POSINF
        g.VAR_EC.lo[g.Mr[g.r], g.t] = (
            (g.tm_annc[g.r, g.t] + g.tm_amp[g.r, g.t]) / g.tm_hdf[g.r, g.t]
        ).where[(~(g.TmPp[g.r, g.t]))]  # type: ignore[assignment]
        g.VAR_INV.fx[g.Mr[g.r], g.t].where[(~(g.TmPp[g.r, g.t]))] = g.VAR_INV.l[
            g.r, g.t
        ]
        # * Treat non-MR regions gracefully
        if g.Mr.number_records:
            g.z[...] = Sum(
                g.tb[g.t - 1],
                Smax(g.Mr, g.eq_escost.m[g.Mr, g.t] / g.coef_pvt[g.Mr, g.t]),
            )
        else:
            g.z[...] = 0.5
        g.tm_udf[g.r, g.t] = g.coef_pvt[g.r, g.t] * g.z

    def exec2(self: EquExtMlf) -> None:
        g = self.tc
        g.tm_cie[g.r, g.t, g.c].where[g.TmDm[g.r, g.c]] = (
            g.tm_dem[g.r, g.t, g.c]
            * g.tm_dmc[g.r, g.t, g.c]
            / (g.tm_dem[g.r, g.t, "ACT"] * g.tm_dmc[g.r, g.t, "ACT"])
        )
        g.VAR_DEM.up[g.Mr[g.r], g.Pp[g.t], g.c].where[
            ((~(g.TmPp[g.r, g.t])).where[g.TmDm[g.r, g.c]])
        ] = g.tm_dem[g.r, g.t, g.c]
        g.VAR_DEM.lo[g.r, g.Pp, g.c].where[g.TmDm[g.r, g.c]] = (
            g.tm_dem[g.r, g.Pp, g.c] * 0.5
        )
