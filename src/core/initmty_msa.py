# initmty_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INITMTY.MSA has all the EMPTY declarations for system & user data           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyMsa(GamsClass):
    """Translation unit for initmty.msa."""

    # Instance attributes
    module_name: str = "initmty_msa"
    gams_source: str = "initmty.msa"

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
        g = self.tc
        m = g.container

        t, Reg, Com, year, r, item, c, ll, allyear = (
            g.t,
            g.Reg,
            g.Com,
            g.year,
            g.r,
            g.item,
            g.c,
            g.ll,
            g.allyear,
        )

        # Basic Sets
        g.niter = Set(m, name="NITER", records=range(1, 19))
        g.miter = Set(m, name="MITER", records=range(1, 17))
        g.Tb = Set(m, name="TB", domain=[t])
        g.Pp = Set(m, name="PP", domain=[t])
        g.Tlast = Set(m, name="TLAST", domain=[t])
        g.tp = Alias(m, name="TP", alias_with=t)

        # Initialized Scalar Defaults
        g.tm_arbm = Parameter(m, name="TM_ARBM", records=1)
        g.tm_scale_cst = Parameter(m, name="TM_SCALE_CST", records=0.001)
        g.tm_scale_nrg = Parameter(m, name="TM_SCALE_NRG", records=1)
        g.tm_scale_util = Parameter(m, name="TM_SCALE_UTIL", records=0.001)
        g.tm_defval = Parameter(
            m,
            name="TM_DEFVAL",
            domain=["*"],
            records=[
                ("DEPR", 5),
                ("ESUB", 0.25),
                ("KGDP", 2.5),
                ("KPVS", 0.25),
                ("DMTOL", 0.1),
                ("IVETOL", 0.5),
                ("REFTEMP", 2.5),
                ("REFLOSS", 0.02),
                ("ESC", 1.028),
            ],
        )

        # Declare/Initialize User Defined Sets
        g.Mr = Set(m, name="MR", domain=[Reg])
        g.Dm = Set(m, name="DM", domain=[Com])
        g.Mrtc = Set(m, name="MRTC", domain=[Reg, year, Com])
        g.trd = Set(m, name="TRD", records=["NMR", "IRE"])
        g.TmDam = Set(m, name="TM_DAM", domain=[r, item])

        # Declare/Initialize Input Parameters
        g.tm_gr = Parameter(
            m, name="TM_GR", domain=[Reg, year], description="Growth rate"
        )
        g.tm_gdp0 = Parameter(
            m, name="TM_GDP0", domain=[Reg], description="Initial GDP"
        )
        g.tm_depr = Parameter(
            m, name="TM_DEPR", domain=[r], description="Depreciation rate"
        )
        g.tm_dmtol = Parameter(
            m, name="TM_DMTOL", domain=[r], description="Demand lower bound factor"
        )
        g.tm_ivetol = Parameter(
            m,
            name="TM_IVETOL",
            domain=[r],
            description="Investment and enery tolerance",
        )
        g.tm_kgdp = Parameter(
            m, name="TM_KGDP", domain=[r], description="Initial capital to GDP ratio"
        )
        g.tm_kpvs = Parameter(
            m, name="TM_KPVS", domain=[r], description="Capital value share"
        )
        g.tm_esub = Parameter(
            m, name="TM_ESUB", domain=[r], description="Elasticity of substitution"
        )
        g.tm_mdtl = Parameter(
            m, name="TM_MDTL", domain=[r], description="Market damage linear coeff."
        )
        g.tm_mdtq = Parameter(
            m, name="TM_MDTQ", domain=[r], description="Market damage quadratic coeff."
        )
        g.tm_hsx = Parameter(
            m, name="TM_HSX", domain=[r, year], description="Hockey-stick exponent"
        )

        # Intermediate parameters for MACRO--1

        ## MACRO Sectoral Demands, marginals and AEEIs
        g.tm_ddatpref = Parameter(m, name="TM_DDATPREF", domain=[Reg, Com])
        g.tm_ddf = Parameter(m, name="TM_DDF", domain=[Reg, year, Com])
        g.tm_dem = Parameter(m, name="TM_DEM", domain=[Reg, year, Com])
        g.tm_dmc = Parameter(m, name="TM_DMC", domain=[Reg, year, Com])
        g.nyper = Parameter(
            m,
            name="NYPER",
            domain=[t],
            description="number of years until next milestone",
        )
        g.tm_ec0 = Parameter(
            m, name="TM_EC0", domain=[Reg], description="initial energy system cost"
        )
        g.tm_c0 = Parameter(
            m, name="TM_C0", domain=[Reg], description="initial consumption"
        )
        g.tm_y0 = Parameter(
            m, name="TM_Y0", domain=[Reg], description="initial gross output"
        )
        g.tm_iv0 = Parameter(
            m, name="TM_IV0", domain=[Reg], description="initial investment"
        )
        g.tm_k0 = Parameter(
            m, name="TM_K0", domain=[Reg], description="initial capital"
        )
        g.tm_rho = Parameter(
            m, name="TM_RHO", domain=[r], description="exponent derived from esub"
        )
        g.tm_asrv = Parameter(
            m, name="TM_ASRV", domain=[r], description="annual capital survival factor"
        )
        g.tm_tsrv = Parameter(
            m,
            name="TM_TSRV",
            domain=[r, t],
            description="yearly capital survival factor according to number of years per period",
        )
        g.tm_akl = Parameter(
            m,
            name="TM_AKL",
            domain=[Reg],
            description="prod function constant for k-l index",
        )

        # Intermediate Parameters for MACRO--2
        g.tm_aeeiv = Parameter(
            m,
            name="TM_AEEIV",
            domain=[r, year, c],
            description="Annual AEEI and demand decoupling factor",
        )
        g.tm_aeeifac = Parameter(
            m,
            name="TM_AEEIFAC",
            domain=[r, ll, c],
            description="Periodwise AEEI and demand decoupling factor",
        )
        g.tm_b = Parameter(
            m,
            name="TM_B",
            domain=[Reg, Com],
            description="Prod function constant for demand of useful energy",
        )
        g.tm_d0 = Parameter(
            m,
            name="TM_D0",
            domain=[Reg, Com],
            description="Base year useful demand - from TIMES",
        )
        g.tm_dfactcurr = Parameter(
            m,
            name="TM_DFACTCURR",
            domain=[r, ll],
            description="Current annual utility discount factor",
        )
        g.tm_dfact = Parameter(
            m,
            name="TM_DFACT",
            domain=[r, allyear],
            description="Utility discount factor",
        )
        g.tm_pwt = Parameter(
            m, name="TM_PWT", domain=[year], description="Periodic utility weight"
        )
        g.tm_l = Parameter(
            m,
            name="TM_L",
            domain=[Reg, year],
            description="Current labor force index (efficiency units)",
        )
        g.tm_annc = Parameter(
            m,
            name="TM_ANNC",
            domain=[Reg, year],
            description="Estimate of annual energy system cost",
        )
        g.tm_amp = Parameter(
            m,
            name="TM_AMP",
            domain=[Reg, year],
            description="Amortisation of past investments",
        )
        g.tm_gdpgoal = Parameter(
            m,
            name="TM_GDPGOAL",
            domain=[Reg, g.tp],
            description="Projected Baseline GDP",
        )
        g.tm_growv = Parameter(
            m,
            name="TM_GROWV",
            domain=[Reg, year],
            description="Potential Labor Growth Rates",
        )
        g.tm_qsfa = Parameter(
            m,
            name="TM_QSFA",
            domain=[Reg, g.tp],
            description="Quadratic supply function A",
        )
        g.tm_qsfb = Parameter(
            m,
            name="TM_QSFB",
            domain=[Reg, g.tp, Com],
            description="Quadratic supply function B",
        )
        g.tm_catt = Parameter(
            m, name="TM_CATT", domain=[r], description="Catastrophic temperature"
        )
        g.tm_udf = Parameter(
            m, name="TM_UDF", domain=[r, allyear], description="Utility discount factor"
        )
        g.tm_nwt = Parameter(
            m, name="TM_NWT", domain=[Reg], description="Negishi weights"
        )
        g.tm_nwtit = Parameter(
            m,
            name="TM_NWTIT",
            domain=[g.niter, Reg],
            description="Negishi weights by iteration",
        )
        g.tm_pvpi = Parameter(
            m,
            name="TM_PVPI",
            domain=[item, g.tp],
            description="Present value prices of tradeables",
        )
        g.par_y = Parameter(
            m, name="PAR_Y", domain=[r, t], description="Production parameter"
        )
        g.par_iv = Parameter(
            m, name="PAR_IV", domain=[r, year], description="Investment parameter"
        )
        g.par_grgdp = Parameter(
            m, name="PAR_GRGDP", domain=[r, t], description="Growth rate of GDP"
        )
        g.par_mc = Parameter(
            m, name="PAR_MC", domain=[r, t, c], description="Marginal costs of demands"
        )
        g.tm_ddf_y = Parameter(m, name="TM_DDF_Y", domain=[r, t])
        g.tm_ddf_dm = Parameter(m, name="TM_DDF_DM", domain=[r, t, c])
        g.tm_ddf_sp = Parameter(m, name="TM_DDF_SP", domain=[r, t, c])
        g.tm_f2 = Parameter(m, name="TM_F2", domain=[r, t, c])
        g.tm_ycheck = Parameter(m, name="TM_YCHECK", domain=[r])

        # Results Parameters for MACRO
        g.tm_dd = Parameter(
            m,
            name="TM_DD",
            domain=[r, c, t],
            description="Demand ratio MSA estimates to TED demand levels",
        )
        g.tm_gdp = Parameter(
            m,
            name="TM_GDP",
            domain=[Reg, year],
            description="Actualized gross domestic product",
        )
        if not g.declared(g.tm_result):
            g.tm_result = Parameter(
                m,
                name="TM_RESULT",
                domain=[item, r, year],
                description="MACRO Summary result parameters",
            )
