# initmty_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * INIT DECLARATIONS FOR THE MACRO EXTENSION
# *=============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyTm(GamsClass):
    """Translation unit for initmty.tm."""

    # Instance attributes
    module_name: str = "initmty_tm"
    gams_source: str = "initmtytm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        g = self.tc
        m = g.container
        print(self.module_name, phase)
        self.env.set_global("spoint", "3")

        # * As in original IER implementation, disable warm start in MACRO
        # * This may be overridden in the RUN file after the INITMTY call
        self.tc.add_gams_code(module=self, phase=phase, code="OPTION BRATIO=1;")

        g.tm_qfac = Parameter(
            m,
            name="TM_QFAC",
            domain=[g.r],
            description="Switch for market penetration penalty function",
        )

        r, allyear, p, c, year, t = g.r, g.allyear, g.p, g.c, g.year, g.t

        def input_parameters() -> None:
            g.tm_arbm = Parameter(m, name="TM_ARBM", records=1000)
            g.tm_scale_util = Parameter(
                m,
                name="TM_SCALE_UTIL",
                description="Scaling factor utility function",
                records=0,
            )
            g.tm_scale_nrg = Parameter(
                m,
                name="TM_SCALE_NRG",
                description="Scaling factor demand units",
                records=0,
            )
            g.tm_scale_cst = Parameter(
                m,
                name="TM_SCALE_CST",
                description="Scaling factor cost units",
                records=0,
            )
            g.tm_depr = Parameter(
                m, name="TM_DEPR", domain=[r], description="Depreciation rate"
            )
            g.tm_dmtol = Parameter(
                m, name="TM_DMTOL", domain=[r], description="Demand lower bound factor"
            )
            g.tm_esub = Parameter(
                m, name="TM_ESUB", domain=[r], description="Elasticity of substitution"
            )
            g.tm_gdp0 = Parameter(
                m, name="TM_GDP0", domain=[r], description="GDP in the first period"
            )
            g.tm_gr = Parameter(
                m,
                name="TM_GR",
                domain=[r, allyear],
                description="MACRO Projected Annual GDP Growth",
            )
            g.tm_ivetol = Parameter(
                m,
                name="TM_IVETOL",
                domain=[r],
                description="Investment and enery tolerance",
            )
            g.tm_kgdp = Parameter(
                m,
                name="TM_KGDP",
                domain=[r],
                description="Initial capital to GDP ratio",
            )
            g.tm_kpvs = Parameter(
                m, name="TM_KPVS", domain=[r], description="Capital value share"
            )
            # PARAMETER TM_QFAC(R)                   'Switch for market penetration penalty function'             //;
            g.tm_expbnd = Parameter(
                m,
                name="TM_EXPBND",
                domain=[r, allyear, p],
                description="Market Penetration Cutoff for Applying Cost Penalty",
            )
            g.tm_expf = Parameter(
                m,
                name="TM_EXPF",
                domain=[r, allyear],
                description="Annual percent expansion factor",
            )

        def calibration_parameters() -> None:
            g.tm_ec0 = Parameter(
                m,
                name="TM_EC0",
                domain=[r],
                description="Energy costs in the first period",
            )
            g.tm_growv = Parameter(
                m,
                name="TM_GROWV",
                domain=[r, allyear],
                description="Labour growth rate",
            )
            g.tm_ddatpref = Parameter(
                m,
                name="TM_DDATPREF",
                domain=[r, c],
                description="Reference marginal price for demand",
            )
            g.tm_ddf = Parameter(
                m,
                name="TM_DDF",
                domain=[r, allyear, c],
                description="Demand decoupling factor",
            )

        def internal_parameters() -> None:
            g.tm_captb = Parameter(
                m,
                name="TM_CAPTB",
                domain=[g.r, g.p],
                description="Cumulative quadratic capacity penalty level",
            )

            g.tm_pwt = Parameter(
                m, name="TM_PWT", domain=[allyear], description="Period weight"
            )
            g.tm_amp = Parameter(
                m,
                name="TM_AMP",
                domain=[r, allyear],
                description="Amortisation of past investments (from CSA only)",
            )
            g.tm_akl = Parameter(
                m, name="TM_AKL", domain=[r], description="Production function constant"
            )
            g.tm_asrv = Parameter(
                m,
                name="TM_ASRV",
                domain=[r],
                description="Annual capital survival factor",
            )
            g.tm_rho = Parameter(
                m, name="TM_RHO", domain=[r], description="Substitution constant"
            )
            g.tm_b = Parameter(
                m, name="TM_B", domain=[r, c], description="Demand coefficient"
            )
            g.tm_d0 = Parameter(
                m, name="TM_D0", domain=[r, c], description="Demand in first period"
            )
            g.tm_l = Parameter(
                m, name="TM_L", domain=[r, year], description="Annual labor index"
            )
            g.tm_tsrv = Parameter(
                m,
                name="TM_TSRV",
                domain=[r, year],
                description="Capital survival factor between two periods",
            )
            g.tm_aeeiv = Parameter(
                m,
                name="TM_AEEIV",
                domain=[r, year, c],
                description="Annual Autonomous energy efficiency and demand decoupling factor",
            )
            g.tm_aeeifac = Parameter(
                m,
                name="TM_AEEIFAC",
                domain=[r, year, c],
                description="Periodwise Autonomous energy efficiency and demand decoupling factor",
            )
            g.tm_adder = Parameter(
                m,
                name="TM_ADDER",
                domain=[r, t, c],
                description="Demand decoupling adder",
            )
            g.tm_c0 = Parameter(
                m, name="TM_C0", domain=[r], description="Consume in the first period"
            )
            g.tm_k0 = Parameter(
                m, name="TM_K0", domain=[r], description="Capital stock in first period"
            )
            g.tm_iv0 = Parameter(
                m,
                name="TM_IV0",
                domain=[r],
                description="Investment in the first period",
            )
            g.tm_y0 = Parameter(
                m,
                name="TM_Y0",
                domain=[r],
                description="Annual production in first period",
            )
            g.tm_dfact = Parameter(
                m,
                name="TM_DFACT",
                domain=[r, year],
                description="Utility discount factor",
            )
            g.tm_dfactcurr = Parameter(
                m,
                name="TM_DFACTCURR",
                domain=[r, year],
                description="Intermediate parameter for the utility discount factor",
            )
            g.tm_udf = Parameter(
                m,
                name="TM_UDF",
                domain=[r, allyear],
                description="Utility discount factor",
            )
            g.tm_cap = Parameter(
                m,
                name="TM_CAP",
                domain=[r, p],
                description="Base year capacity values for expanding technologies",
            )
            # PARAMETER TM_CAPTB(R,P)                'Cumulative quadratic capacity penalty level'                //;
            g.tm_cstinv = Parameter(
                m,
                name="TM_CSTINV",
                domain=[r, allyear, p],
                description="Annualized investment costs",
            )
            g.tm_ycheck = Parameter(
                m, name="TM_YCHECK", domain=[r], description="Check"
            )

        input_parameters()
        calibration_parameters()
        internal_parameters()
