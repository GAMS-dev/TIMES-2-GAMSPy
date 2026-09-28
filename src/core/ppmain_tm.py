# pp_main_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * ppmain.tm oversees all the preprocessing activities needed by MACRO


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Ord, Parameter, Smax, Sum
from gamspy.math import Max, Min

from core.base_class import GamsClass
from core.prep_ext_tm import PrepExtTm

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmainTm(GamsClass):
    """Translation unit for ppmain.tm."""

    # Instance attributes
    module_name: str = "ppmain_tm"
    gams_source: str = "ppmain.tm"

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
        self.include(PrepExtTm(self.tc, self.env))
        self.tc.enqueue(self.initialize_economic_parameters)
        self.tc.enqueue(self.calc_vals_for_econ_variables)
        self.tc.enqueue(self.calc_utility_and_production_params)
        g.help_expf = Parameter(g.container, name="HELP_EXPF", domain=[g.r, g.t])
        self.tc.enqueue(self.execFinal)

    def initialize_economic_parameters(self: PpmainTm) -> None:
        g = self.tc
        # *============================================================================*
        # * Initialize the economic parameters
        # *============================================================================*

        g.tm_aeeiv[g.r, g.t, g.c].where[g.Dem[g.r, g.c]] = (
            g.tm_ddf[g.r, g.t, g.c] / 100.0
        )
        g.tm_asrv[g.r] = 1.0 - g.tm_depr[g.r] / 100.0
        g.tm_dfactcurr[g.r, g.t] = 1.0 - (
            g.tm_kpvs[g.r] / g.tm_kgdp[g.r]
            - g.tm_depr[g.r] / 100.0
            - g.tm_growv[g.r, g.t] / 100.0
        )
        g.tm_rho[g.r] = 1.0 - 1.0 / g.tm_esub[g.r]

        # * Capital survival defined as factor between the middle year of the period T+1 and the period T
        g.tm_tsrv[g.r, g.t] = g.tm_asrv[g.r] ** g.nyper[g.t]

    def calc_vals_for_econ_variables(self: PpmainTm) -> None:
        g = self.tc
        # *============================================================================*
        # *  Calculate initial values for the economic variables for the first time period
        # *   - Capital Stock
        # *   - Investment during time period 0
        # *   - Consumption during time period 0
        # *   - GDP (Consumption + Investment) + Energy Costs
        # *============================================================================*

        g.tm_k0[g.r] = g.tm_kgdp[g.r] * g.tm_gdp0[g.r]
        g.tm_iv0[g.r] = (
            g.tm_k0[g.r]
            * (g.tm_depr[g.r] + Sum(g.t.where[Ord(g.t) == 1.0], g.tm_growv[g.r, g.t]))
            / 100.0
        )
        g.tm_c0[g.r] = g.tm_gdp0[g.r] - g.tm_iv0[g.r]
        g.tm_y0[g.r] = (
            g.tm_gdp0[g.r] + g.tm_ec0[g.r] + Sum(g.T1[g.t], g.tm_amp[g.r, g.t])
        )

        # *============================================================================*
        # * Calculate intermediate values
        # *============================================================================*
        g.tm_aeeifac[g.r, g.t, g.c].where[g.Dem[g.r, g.c]] = 1.0
        g.tm_dfact[g.r, g.t] = 1.0
        g.tm_l[g.r, g.t] = 1.0

        with Loop(g.t):
            g.tm_aeeifac[g.r, g.t + 1, g.c].where[g.Dem[g.r, g.c]] = g.tm_aeeifac[
                g.r, g.t, g.c
            ] * ((1.0 - g.tm_aeeiv[g.r, g.t + 1, g.c]) ** g.nyper[g.t])
            g.tm_dfact[g.r, g.t + 1] = g.tm_dfact[g.r, g.t] * (
                g.tm_dfactcurr[g.r, g.t] ** g.nyper[g.t]
            )
            g.tm_l[g.r, g.t + 1] = g.tm_l[g.r, g.t] * (
                (1.0 + g.tm_growv[g.r, g.t] / 100.0) ** g.nyper[g.t]
            )

    def calc_utility_and_production_params(self: PpmainTm) -> None:
        g = self.tc
        # * Arbitrary multiplier on utility in last time period.
        with Loop(g.Miyr1[g.t.lead(1, "circular")].where[g.tm_arbm != 1.0]):
            g.tm_dfact[g.r, g.t] = (
                g.tm_dfact[g.r, g.t]
                * (
                    1.0
                    - Min(0.999, g.tm_dfactcurr[g.r, g.t]) ** (g.nyper[g.t] * g.tm_arbm)
                )
                / (1.0 - Min(0.999, g.tm_dfactcurr[g.r, g.t]) ** (g.nyper[g.t] * 1.0))
            )
        # * Weights for periods (use only if requested by TM_ARBM=1)
        g.tm_pwt[g.t] = 1.0
        if g.tm_sl.toValue():
            g.z[...] = Max(1.0, Smax(g.t, g.d[g.t]))
            g.tm_pwt[g.t] = g.d[g.t] / g.z

        g.tm_d0[g.Dem[g.r, g.c]] = g.tm_scale_nrg * Sum(
            g.Miyr1[g.t], g.com_proj[g.r, g.t, g.c]
        )

        g.tm_b[g.Dem[g.r, g.c]] = g.tm_d0[g.r, g.c] / g.tm_y0[g.r]
        g.tm_b[g.Dem[g.r, g.c]] = g.tm_b[g.r, g.c] ** (1.0 - g.tm_rho[g.r])
        g.tm_b[g.Dem[g.r, g.c]] = (
            g.tm_scale_cst / g.tm_scale_nrg * g.tm_ddatpref[g.r, g.c] * g.tm_b[g.r, g.c]
        )

        g.tm_akl[g.r] = g.tm_y0[g.r] ** g.tm_rho[g.r] - Sum(
            g.Dem[g.r, g.c], g.tm_b[g.r, g.c] * (g.tm_d0[g.r, g.c] ** g.tm_rho[g.r])
        )
        g.tm_akl[g.r] = g.tm_akl[g.r] / (
            g.tm_k0[g.r] ** (g.tm_kpvs[g.r] * g.tm_rho[g.r])
        )

        g.tm_ycheck[g.r] = g.tm_akl[g.r] * (
            g.tm_k0[g.r] ** (g.tm_kpvs[g.r] * g.tm_rho[g.r])
        ) + Sum(
            g.Dem[g.r, g.c], g.tm_b[g.r, g.c] * (g.tm_d0[g.r, g.c] ** g.tm_rho[g.r])
        )
        g.tm_ycheck[g.r] = g.tm_ycheck[g.r] ** (1.0 / g.tm_rho[g.r])

    def execFinal(self: PpmainTm) -> None:
        g = self.tc
        # * annual percent expansion factor converted into 1 period factor
        g.help_expf[g.r, g.t] = g.tm_expf[g.r, g.t]
        g.tm_expf[g.r, g.t] = (1.0 + g.help_expf[g.r, g.t] / 100.0) ** (
            g.d[g.t] / 2.0
        ) * ((1.0 + g.help_expf[g.r, g.t + 1] / 100.0) ** (g.d[g.t + 1] / 2.0))
        g.help_expf.setRecords(None)

        print(g.tm_b.records)
        print(g.tm_expf.records)
