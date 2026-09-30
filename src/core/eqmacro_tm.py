# eqmacro_tm.py
# # *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# *  Utility Production Function, the Objective Function                        *
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gamspy.math as gams_math
from gamspy import Card, Ord, Sum

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqmacroTm(GamsClass):
    """Translation unit for eqmacro.tm."""

    module_name: str = "eqmacro_tm"
    gams_source: str = "eqmacro.tm"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.add_eq_util()
        self.add_eq_conso()
        self.add_eq_dd()
        self.add_eq_mcap()
        self.add_eq_tmc()
        self.add_eq_ivecbnd()
        self.tc.enqueue(self.exec_tm_cstinv)
        self.add_eq_escost()
        self.add_eq_mpen()
        self.add_eq_xcapdb()

    def add_eq_util(self) -> None:
        """Utility Production Function, the Objective Function"""
        g = self.tc
        r, t = g.r, g.t

        g.eq_util[...] = (
            Sum(
                [r, t],
                g.tm_dfact[r, t] * g.tm_pwt[t] * gams_math.log(g.VAR_C[r, t]),
            )
            == g.VAR_UTIL
            * gams_math.Max(1, gams_math.log(g.tm_scale_util * 1000))
            / 1000
        )

    def add_eq_conso(self) -> None:
        """Production constraint."""
        g = self.tc
        r, t, c = g.r, g.t, g.c

        g.eq_conso[r, t] = (
            g.VAR_C[r, t]
            <= (
                g.tm_akl[r]
                * (g.VAR_K[r, t] ** (g.tm_kpvs[r] * g.tm_rho[r]))
                * g.tm_l[r, t] ** ((1 - g.tm_kpvs[r]) * g.tm_rho[r])
                + Sum(g.Dem[r, c], g.tm_b[r, c] * g.VAR_D[r, t, c] ** g.tm_rho[r])
            )
            ** (1 / g.tm_rho[r])
            - g.VAR_INV[r, t]
            - g.VAR_EC[r, t]
        )

    def add_eq_dd(self) -> None:
        """Demand coupling equation
        A demand relation is generated for each demand sector DM and ensures that
        the end-use energy output from the demand devices which have output to DM
        is greater than or equal to the end-use demand specified by the user."""
        g = self.tc
        r, t, c = g.r, g.t, g.c

        g.eq_dd[r, t, c].where[g.Dem[r, c]] = (
            g.VAR_DEM[r, t, c]
            == (
                (1 / g.tm_scale_nrg)
                * (
                    g.tm_aeeifac[r, t, c] * g.VAR_D[r, t, c]
                    + g.tm_adder[r, t, c]
                    + g.VAR_SP[r, t, c]
                )
            ).where[g.com_proj[r, t, c] > 0]
        )

    def add_eq_mcap(self) -> None:
        """Capital dynamics equation."""
        g = self.tc
        r, t = g.r, g.t

        g.eq_mcap[r, t + 1] = (
            g.VAR_K[r, t + 1]
            == g.VAR_K[r, t] * g.tm_tsrv[r, t]
            + (
                g.d[t + 1] * g.VAR_INV[r, t + 1]
                + g.tm_tsrv[r, t] * g.d[t] * g.VAR_INV[r, t]
            )
            / 2
        )

    def add_eq_tmc(self) -> None:
        """Terminal condition for investment in last period."""
        g = self.tc
        r, t = g.r, g.t

        g.eq_tmc[r, t].where[Ord(t) == Card(t)] = (
            g.VAR_K[r, t] * (g.tm_growv[r, t] + g.tm_depr[r]) / 100 <= g.VAR_INV[r, t]
        )

    def add_eq_ivecbnd(self) -> None:
        """Bound on sum of investment and energy."""
        g = self.tc
        r, t = g.r, g.t

        g.eq_ivecbnd[r, t].where[Ord(t) > 1] = (
            g.VAR_INV[r, t] + g.VAR_EC[r, t]
            <= g.tm_y0[r] * g.tm_l[r, t] ** g.tm_ivetol[r]
        )

    def exec_tm_cstinv(self) -> None:
        """Calculate annualized undiscounted investment costs."""
        g = self.tc
        r, v, p, cur = g.r, g.v, g.p, g.cur

        # * Calculate annualized undiscounted investment costs
        g.tm_cstinv[r, v, p].where[g.Rtp[r, v, p]] = Sum(
            g.ObjIcur[r, v, p, cur], g.coef_obinv[r, v, p, cur]
        )

    def add_eq_escost(self) -> None:
        """Energy system costs equation."""
        g = self.tc
        r, t, p, j = g.r, g.t, g.p, g.j

        g.eq_escost[r, t] = (
            g.tm_scale_cst
            * (
                g.VAR_OBJCOST[r, t]
                # * quadratic market penetration curve
                + (
                    Sum(
                        g.Rtp[r, t, p].where[g.tm_captb[r, p]],
                        0.5
                        * g.tm_qfac[r]
                        * g.tm_cstinv[r, t, p]
                        * (
                            g.tm_captb[r, p]
                            / g.tm_expf[r, t]
                            * Sum(g.Xcp[j], g.VAR_XCAPP[r, t, p, j] * Ord(j))
                        ),
                    )
                ).where[g.tm_qfac[r] != 0]
            )
            # * add initial amortization (from CSA only)
            + g.tm_amp[r, t]
            == g.VAR_EC[r, t]
        )

    def add_eq_mpen(self) -> None:
        """Variable definition for market penetration cost penalty function"""
        g = self.tc
        r, t, tt, p = g.r, g.t, g.tt, g.p

        g.eq_mpen[g.Rtp[r, tt[t + 1], p]].where[
            (g.tm_qfac[r] != 0).where[g.tm_cstinv[r, tt, p].where[g.tm_captb[r, p]]]
        ] = (
            g.VAR_CAP[r, tt, p]
            <= g.tm_expf[r, t] * g.VAR_CAP[r, t, p] + g.VAR_XCAP[r, tt, p]
        )

    def add_eq_xcapdb(self) -> None:
        """Market Penetration Cost Penalty Function, Quadratic Approximation"""
        g = self.tc
        r, t, tt, p, j = g.r, g.t, g.tt, g.p, g.j

        g.eq_xcapdb[g.Rtp[r, tt[t + 1], p]].where[
            (g.tm_qfac[r] != 0).where[g.tm_cstinv[r, tt, p].where[g.tm_captb[r, p]]]
        ] = g.VAR_XCAP[r, tt, p] == Sum(g.Xcp[j], g.VAR_XCAPP[r, tt, p, j])
