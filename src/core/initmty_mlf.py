# initmty_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * Init Declarations for the MLF Macro extension
# *=============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set

from core.base_class import GamsClass
from core.initmty_tm import InitmtyTm
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyMlf(GamsClass):
    """Translation unit for initmty.mlf."""

    # Instance attributes
    module_name: str = "initmty_mlf"
    gams_source: str = "initmty.mlf"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        self.include(InitmtyTm(tc=self.tc, env=self.env))
        self.env.set_global("macro", "Yes")
        self.env.set_global("spoint", "")

        r, cg, lim, year, bd, UcCost, t, c, Reg, item, Com = (
            g.r,
            g.cg,
            g.lim,
            g.year,
            g.bd,
            g.UcCost,
            g.t,
            g.c,
            g.Reg,
            g.item,
            g.Com,
        )

        # --- Redefined & Additional input parameters ---
        g.tm_arbm = Parameter(
            m, name="TM_ARBM", description="Arbitrary multiplier", records=1
        )
        g.tm_scale_util = Parameter(
            m,
            name="TM_SCALE_UTIL",
            description="Scaling factor utility function",
            records=0.001,
        )
        g.tm_scale_nrg = Parameter(
            m,
            name="TM_SCALE_NRG",
            description="Scaling factor demand units",
            records=0.001,
        )
        g.tm_scale_cst = Parameter(
            m,
            name="TM_SCALE_CST",
            description="Scaling factor cost units",
            records=0.001,
        )
        g.tm_desub = Parameter(
            m,
            name="TM_DESUB",
            domain=[r],
            description="Elasticity of substitution between demands",
        )
        g.tm_step = Parameter(
            m,
            name="TM_STEP",
            domain=[r, cg, lim],
            description="Steps in CES substitution",
        )
        g.tm_voc = Parameter(
            m,
            name="TM_VOC",
            domain=[r, year, cg, bd],
            description="Variance in CES component or utility",
        )
        # --- Internal attributes ---
        comgrp_records = ["AKL", "LAB", "KN", "YN", "CON", "UTIL"]
        if g.comgrp is None:
            g.comgrp = Set(m, name="COM_GRP", records=comgrp_records)
        else:
            expand_set(g.comgrp, comgrp_records)
        g.niter = Set(m, name="NITER", records=range(1, 19))
        g.TmPp = Set(m, name="TM_PP", domain=[r, year])
        # Initialized Scalar Defaults *
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
                ("NEGTOL", 0.01),
                ("MACVOC", 0.4),
                ("MACSTEP", 200),
                ("LOGSTEP", 550),
                ("USEHDF", 1),
                ("ESC", 1.028),
            ],
        )
        g.sol_acfr = Parameter(
            m,
            name="SOL_ACFR",
            domain=[r, UcCost, t],
            description="Baseline annual cost data",
        )
        # MACRO Sectoral Demands, marginals and AEEIs
        g.tm_dem = Parameter(
            m, name="TM_DEM", domain=[Reg, year, Com], description="Demand levels"
        )
        g.tm_dmc = Parameter(
            m, name="TM_DMC", domain=[Reg, year, Com], description="Demand marginals"
        )
        g.tm_ddf_y = Parameter(
            m, name="TM_DDF_Y", domain=[r, t], description="Production growths"
        )
        g.tm_ddf_dm = Parameter(
            m, name="TM_DDF_DM", domain=[r, t, c], description="Demand growth rate"
        )
        g.tm_ddf_sp = Parameter(
            m,
            name="TM_DDF_SP",
            domain=[r, t, c],
            description="Demand marginals change rate",
        )
        g.tm_f2 = Parameter(
            m, name="TM_F2", domain=[r, t, c], description="Demand DDF calibration"
        )
        g.tm_annc = Parameter(
            m,
            name="TM_ANNC",
            domain=[Reg, year],
            description="Estimate of annual energy system cost",
        )
        g.tm_gdpgoal = Parameter(
            m,
            name="TM_GDPGOAL",
            domain=[Reg, year],
            description="Projected Baseline GDP",
        )
        g.tm_gdp = Parameter(
            m,
            name="TM_GDP",
            domain=[r, t],
            description="Actualized gross domestic product",
        )
        g.tm_qsfa = Parameter(
            m,
            name="TM_QSFA",
            domain=[Reg, t],
            description="Quadratic supply function A",
        )
        g.tm_qsfb = Parameter(
            m,
            name="TM_QSFB",
            domain=[Reg, t, Com],
            description="Quadratic supply function B",
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
        g.tm_cie = Parameter(
            m, name="TM_CIE", domain=[r, t, cg], description="Expnditure rate"
        )
        g.par_y = Parameter(
            m, name="PAR_Y", domain=[r, t], description="Production parameter"
        )
        g.par_grgdp = Parameter(
            m, name="PAR_GRGDP", domain=[r, t], description="Growth rate of GDP"
        )
        g.par_mc = Parameter(
            m,
            name="PAR_MC",
            domain=[r, year, c],
            description="Marginal costs of demands",
        )
        if not g.declared(g.tm_result):
            g.tm_result = Parameter(
                m,
                name="TM_RESULT",
                domain=[item, r, year],
                description="MACRO Summary result parameters",
            )
