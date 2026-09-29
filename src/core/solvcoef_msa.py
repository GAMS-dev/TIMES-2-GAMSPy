# solvcoef_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * SOLVCOEF.MSA oversees extended preprocessing activities for MSA
# *============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Smax, Sum
from gamspy.math import Max, Min, aggregate

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolvcoefMsa(GamsClass):
    """Translation unit for solvcoef.msa."""

    # Instance attributes
    module_name: str = "solvcoef_msa"
    gams_source: str = "solvcoef.msa"

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
        self.tc.enqueue(self.exec1)

    def exec1(self: SolvcoefMsa) -> None:
        g = self.tc
        r, c, t, tp = g.r, g.c, g.t, g.tp
        Dm, Xtp, Mr, Tb, Tlast, Pp, Dem, Mrtc = (
            g.Dm,
            g.Xtp,
            g.Mr,
            g.Tb,
            g.Tlast,
            g.Pp,
            g.Dem,
            g.Mrtc,
        )

        # *============================================================================*
        # * Initialize the economic parameters                                         *
        # *============================================================================*
        g.tm_aeeiv[r, tp, c].where[Dem[r, c]] = g.tm_ddf[r, tp, c] / 100
        g.tm_asrv[r] = 1 - g.tm_depr[r] / 100
        g.tm_dfactcurr[r, Xtp] = 1 - (
            g.tm_kpvs[r] / g.tm_kgdp[r] - g.tm_depr[r] / 100 - g.tm_growv[r, Xtp] / 100
        )
        g.tm_rho[r] = 1 - 1 / g.tm_esub[r]
        g.tm_tsrv[r, tp] = g.tm_asrv[r] ** g.nyper[tp]

        # *============================================================================*
        # *  Calculate the initial values for the economic variables for the first time period
        # *   - Capital Stock
        # *   - Investment during time period 0
        # *   - Consumption during time period 0
        # *   - GDP (Consumption + Investment) + Energy Costs
        g.tm_k0[r] = g.tm_kgdp[r] * g.tm_gdp0[r]
        g.tm_iv0[r] = g.tm_k0[r] * (g.tm_depr[r] + Sum(Tb, g.tm_growv[r, Tb])) / 100
        g.tm_c0[r] = g.tm_gdp0[r] - g.tm_iv0[r]
        g.tm_y0[r] = g.tm_gdp0[r] + g.tm_ec0[r] + Sum(Tb, g.tm_amp[r, Tb])

        # *============================================================================*
        # * Calculate intermediate values                                              *
        # *============================================================================*
        g.tm_aeeifac[r, Tb, Dm] = 1
        g.tm_dfact[r, Tb] = 1
        g.tm_l[r, Tb] = 1

        with Loop(Pp[t + 1]):
            g.tm_aeeifac[r, Pp, Dm] = (
                g.tm_aeeifac[r, t, Dm] * (1 - g.tm_aeeiv[r, Pp, Dm]) ** g.nyper[t]
            )
            g.tm_dfact[r, Pp] = g.tm_dfact[r, t] * g.tm_dfactcurr[r, t] ** g.nyper[t]
            g.tm_l[r, Pp] = g.tm_l[r, t] * (1 + g.tm_growv[r, t] / 100) ** g.nyper[t]
        aggregate(source=g.tm_dfact, target=g.tm_udf)

        # *  Arbitrary multiplier on utility in last time period.
        g.tm_dfact[Mr[r], Tlast].where[g.tm_arbm != 1] = (
            g.tm_dfact[r, Tlast]
            * (1 - Min(0.999, g.tm_dfactcurr[r, Tlast]) ** (g.nyper[Tlast] * g.tm_arbm))
            / (1 - Min(0.999, g.tm_dfactcurr[r, Tlast]) ** (g.nyper[Tlast] * 1))
        )
        # * Weights for periods (use only if requested by TM_ARBM=1)
        g.tm_pwt[t] = 1
        if g.tm_arbm.toValue() == 1:
            g.z[...] = Max(1, Smax(t, g.d[t]))
            g.tm_pwt[t] = g.d[t] / g.z

        g.tm_d0[Mr[r], Dm] = Sum(Tb, g.tm_dem[r, Tb, Dm]) * g.tm_scale_nrg

        g.tm_b[Mr[r], Dm] = g.tm_d0[r, Dm] / g.tm_y0[r]
        g.tm_b[Mr[r], Dm] = g.tm_b[r, Dm] ** (1 - g.tm_rho[r])
        g.tm_b[Mr[r], Dm] = (
            g.tm_scale_cst / g.tm_scale_nrg * g.tm_ddatpref[r, Dm] * g.tm_b[r, Dm]
        )

        g.tm_akl[Mr[r]] = g.tm_y0[r] ** g.tm_rho[r] - Sum(
            Dem[r, c], g.tm_b[r, c] * (g.tm_d0[r, c] ** g.tm_rho[r])
        )
        g.tm_akl[Mr[r]] = g.tm_akl[r] / (g.tm_k0[r] ** (g.tm_kpvs[r] * g.tm_rho[r]))

        g.tm_ycheck[Mr[r]] = g.tm_akl[r] * g.tm_k0[r] ** (
            g.tm_kpvs[r] * g.tm_rho[r]
        ) + Sum(Dem[r, c], g.tm_b[r, c] * (g.tm_d0[r, c] ** g.tm_rho[r]))
        g.tm_ycheck[Mr[r]] = g.tm_ycheck[r] ** (1 / g.tm_rho[r])

        print(g.tm_b.records)
        print(g.tm_akl.records)
        print(g.tm_ycheck.records)

        # *-----------------------------------------------------------------
        # * Variable bounds
        g.VAR_D.lo[Mrtc[r, Pp, Dm]] = g.tm_dmtol[r] * g.tm_d0[r, Dm]
        g.VAR_D.l[Mrtc[r, Pp, Dm]] = g.tm_d0[r, Dm]
        g.VAR_D.fx[Mr[r], Tb, Dm] = g.tm_d0[r, Dm]
        g.VAR_D.fx[Mr[r], t, Dm].where[g.tm_dem[r, t, Dm] <= 0] = 0
        g.VAR_DEM.fx[Mr[r], t, c].where[(g.tm_ddatpref[r, c] <= 0) & Dem[r, c]] = (
            g.tm_dem[r, t, c]
        )
        g.VAR_DEM.fx[Mr[r], t, c].where[g.no_rt[r, t]] = g.tm_dem[r, t, c]

        with Loop(Mr[r]):
            g.z[...] = g.tm_k0[r] * g.tm_depr[r] / 100
            with Loop(Pp[t + 1]):
                g.z[...] = g.z * g.tm_tsrv[r, t]
                g.VAR_INV.lo[r, t + 1] = g.z
        g.VAR_INV.fx[Mr[r], t].where[g.no_rt[r, t]] = g.par_iv[r, t]

        g.VAR_INV.l[Mr, Pp] = g.tm_iv0[Mr] * g.tm_l[Mr, Pp]
        g.VAR_INV.fx[Mr, Tb] = g.tm_iv0[Mr]
        g.VAR_K.l[Mr, tp] = g.tm_k0[Mr] * g.tm_l[Mr, tp]
        g.VAR_K.lo[Mr, tp] = g.tm_k0[Mr] * 0.5
        g.VAR_K.fx[Mr, Tb] = g.tm_k0[Mr]

        g.VAR_C.l[Mr, tp] = g.tm_gdp0[Mr] - g.tm_iv0[Mr]
        g.VAR_C.lo[Mr, tp] = g.tm_gdp0[Mr] * 0.1
        g.VAR_Y.l[Mr, tp] = g.tm_y0[Mr]
        g.VAR_Y.lo[Mr, tp] = g.tm_gdp0[Mr] * 0.5
        g.VAR_SP.fx[Mr, tp, Dm] = 0

        g.VAR_EC.lo[Mr, Pp] = g.tm_annc[Mr, Pp] * 0.1
        g.VAR_EC.fx[Mr, Tb] = g.tm_ec0[Mr] + g.tm_amp[Mr, Tb]
