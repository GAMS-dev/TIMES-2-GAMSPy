# eqobjcst_tm.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJCST the objective functions investment, fixed and variable costs
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *  - Supports also alternative objective formulations
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum

from core.base_class import GamsClass
from core.eqdamage_mod import eq_damage_mod_GP
from core.eqobjvar_mod import eqobjvar_mod_GP
from core.prepret_dsc import objfix_GP
from core.utils import extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjcstTm(GamsClass):
    """Translation unit for eqobjcst.tm."""

    # Instance attributes
    module_name: str = "eqobjcst_tm"
    gams_source: str = "eqobjcst.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.investment_equation()
        self.fixed_cost_equation()
        self.variable_cost_equation()

    def investment_equation(self) -> None:
        g = self.tc
        r, v, t, p, cur = g.r, g.v, g.t, g.p, g.cur

        # *===============================================================================
        # * Generate Investment equation summing over all active indexes by region and currency
        # *===============================================================================

        # * Revised accounting for MACRO: Calculate annualized cost from discounted
        # * lump-sum investments undiscounted back to the lump-sum commissioning year K
        g.eq_anninv[r, t, cur].where[g.Rdcur[r, cur]] = g.VAR_ANNCST[
            "OBJINV", r, t, cur
        ] == Sum(
            g.RtpCptyr[r, v, t, p].where[g.ObjIcur[r, v, p, cur]],
            g.coef_cpt[r, v, t, p]
            * g.coef_obinv[r, v, p, cur]
            * (g.VAR_NCAP[r, v, p].where[g.tt[v]] + g.ncap_pasti[r, v, p]),
        )

    def fixed_cost_equation(self) -> None:
        g = self.tc
        r, v, t, p, cur = g.r, g.v, g.t, g.p, g.cur

        # *===============================================================================
        # * Generate Fixed Cost equation summing over all active indexes by region and currency
        # *===============================================================================

        # * Revised accounting for MACRO: Calculate annualized cost from discounted
        # * lump-sum fixed costs undiscounted back to the lump-sum commissioning year K

        rhs = Sum(
            g.RtpCptyr[r, v, t, p].where[g.coef_obfix[r, v, p, cur]],
            g.coef_cpt[r, v, t, p]
            * g.obj_pvt[r, t, cur]
            * g.coef_obfix[r, v, p, cur]
            * (g.VAR_NCAP[r, v, p].where[g.tt[v]] + g.ncap_pasti[r, v, p]),
        )
        if self.tc.defined("VNRET"):
            rhs = (
                objfix_GP(
                    g,
                    capwd=self.env.capwd_GP,
                    vart=self.env.vart_GP,
                    sws=self.env.sws_GP,
                )
                + rhs
            )

        g.eq_annfix[r, t, cur].where[g.Rdcur[r, cur]] = (
            g.VAR_ANNCST["OBJFIX", r, t, cur] * g.obj_pvt[r, t, cur] == rhs
        )

    def variable_cost_equation(self) -> None:
        g = self.tc
        r, t, c, s, j, bd, cur, Com = g.r, g.t, g.c, g.s, g.j, g.bd, g.cur, g.Com

        # *===============================================================================
        # * Generate Variable cost equation summing over all active indexes by region and currency
        # *===============================================================================

        # $BATINCLUDE eqobjvar.mod mod * -- '*' comments out its header and RHS,
        # leaving only the LHS of EQ_ANNVAR
        lhs = eqobjvar_mod_GP(
            g=g,
            varcost=self.env.varcost,
            obj=self.env.obj,
            var=self.env.var,
            sow=self.env.sow_GP,
            pgprim=self.env.pgprim,
            vart=self.env.vart_GP,
            sws=self.env.sws_GP,
            stages=self.env.stages,
            is_vnret_defined=self.tc.defined("VNRET"),
            is_def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            varv=self.env.varv_GP,
            varm=self.env.varm_GP,
            cal_red=self.env.cal_red,
        )

        rhs = g.obj_pvt[r, t, cur] * g.VAR_ANNCST["OBJVAR", r, t, cur]

        if self.tc.defined("DAM_COST"):
            rhs = rhs - eq_damage_mod_GP(
                g, self.env.var, self.env.swd_GP, self.env.stages
            )

        if self.env.timesed == "YES":
            vart_id, vart_set = extract_var_domain(self.env.vart_GP)
            VART_ELAST = g.get_variable(f"{vart_id}_ELAST")
            rhs = rhs - Sum(
                Domain(g.MiDmas[r, Com, c], g.Bdneq[bd]).where[g.mi_esub[r, t, Com]],
                g.bdsig[bd]
                * Sum(
                    g.RtcsVarc[r, t, c, s].where[g.com_step[r, c, bd]],
                    g.coef_pvt[r, t]
                    * g.com_bprice[r, t, c, s, cur]
                    * Sum(
                        g.Rcj[r, c, j, bd],
                        wrap_in_sum(
                            VART_ELAST[r, t, c, s, j, bd, *self.env.sws_GP],
                            vart_set,
                        )
                        * g.mi_agc[r, t, Com, c, j, bd],
                    ),
                ),
            )

        g.eq_annvar[r, t, cur].where[g.Rdcur[r, cur]] = lhs == rhs
