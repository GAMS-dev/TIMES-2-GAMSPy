# eqdeclr_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQDECLR.MOD declarations for actual equations                               *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqdeclrTm(GamsClass):
    """Translation unit for eqdeclr.tm."""

    # Instance attributes
    module_name: str = "eqdeclr_tm"
    gams_source: str = "eqdeclr.tm"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.arg1 = arg1
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # *-----------------------------------------------------------------------------
        # EQUATIONS
        # *-----------------------------------------------------------------------------
        # * Objective Function & Components
        # *-----------------------------------------------------------------------------

        # * Overall OBJ by regional objs (which are built from rest)
        g.eq_obj = Equation(
            m,
            name="EQ_OBJ",
            domain=[g.r, g.allyear],
            description="Overall Objective Function",
        )
        # * Costs of elastic demands
        g.eq_objels = Equation(m, name="EQ_OBJELS", domain=[g.Reg, g.bd, g.cur])
        # * Fixed Costs
        g.eq_annfix = Equation(m, name="EQ_ANNFIX", domain=[g.Reg, g.allyear, g.cur])
        # * Investment component
        g.eq_anninv = Equation(m, name="EQ_ANNINV", domain=[g.Reg, g.allyear, g.cur])
        # * Variable operating costs
        g.eq_annvar = Equation(m, name="EQ_ANNVAR", domain=[g.Reg, g.allyear, g.cur])

        # *-----------------------------------------------------------------------------
        # * MACRO equations
        # *-----------------------------------------------------------------------------
        g.eq_util = Equation(m, name="EQ_UTIL", description="Utility function")
        g.eq_conso = Equation(
            m, name="EQ_CONSO", domain=[g.r, g.t], description="Consumption equation"
        )
        g.eq_dd = Equation(
            m,
            name="EQ_DD",
            domain=[g.r, g.t, g.c],
            description="Demand decoupling equation",
        )
        g.eq_mcap = Equation(
            m,
            name="EQ_MCAP",
            domain=[g.r, g.t],
            description="Capital dynamics equation",
        )
        g.eq_tmc = Equation(
            m,
            name="EQ_TMC",
            domain=[g.r, g.t],
            description="Terminal condition for investment in last period",
        )
        g.eq_ivecbnd = Equation(
            m,
            name="EQ_IVECBND",
            domain=[g.r, g.t],
            description="Bound on the sum of investment and energy costs",
        )
        g.eq_escost = Equation(
            m, name="EQ_ESCOST", domain=[g.r, g.t], description="Energy System costs"
        )
        g.eq_mpen = Equation(
            m,
            name="EQ_MPEN",
            domain=[g.r, g.t, g.p],
            description="Definition of variables for cost penalty function",
        )
        g.eq_xcapdb = Equation(
            m,
            name="EQ_XCAPDB",
            domain=[g.r, g.t, g.p],
            description="Quadratic approximation of market penetration cost penalty function",
        )

        # *-----------------------------------------------------------------------------
        # * MACRO MLF calibration equations
        # *-----------------------------------------------------------------------------
        # * Calibration
        # *  EQ_UTIL              'Utility function'
        g.eq_prod_y = Equation(
            m, name="EQ_PROD_Y", domain=[g.r, g.t], description="Production unction"
        )
        g.eq_akl = Equation(
            m, name="EQ_AKL", domain=[g.r, g.t], description="Aggregate Kapital Labor"
        )
        g.eq_labor = Equation(
            m, name="EQ_LABOR", domain=[g.r, g.t], description="Labor dummy definition"
        )
        g.eq_kncap = Equation(
            m,
            name="EQ_KNCAP",
            domain=[g.r, g.t],
            description="Capital dummy definition",
        )
        # *  EQ_MCAP(R,T)         'Capital dynamics equation'
        # *  EQ_TMC(R,T)          'Terminal condition for investment in last period'
        # *  EQ_IVECBND(R,T)      'Bound on the sum of investment and energy costs'
        # *  EQ_DD(R,T,C)         'Demand decoupling equation'
        # *  EQ_ESCOST(R,T)       'Energy System costs'
        g.eq_trdbal = Equation(
            m, name="EQ_TRDBAL", domain=[g.t], description="Trade balance"
        )
        g.eq_dnlces = Equation(
            m, name="EQ_DNLCES", domain=[g.r, g.t], description="Demand CES function"
        )
        # *-----------------------------------------------------------------------------
        # * Full MLF model formulation
        # *-----------------------------------------------------------------------------
        g.eq_utilp = Equation(m, name="EQ_UTILP", description="Utility function")
        # *  EQ_CONSO(R,T)        'Consumption equation'
        g.eq_conda = Equation(
            m,
            name="EQ_CONDA",
            domain=[g.r, g.t],
            description="Consumption disaggregation",
        )
        g.eq_logbd = Equation(
            m, name="EQ_LOGBD", domain=[g.r, g.t], description="Linearized log bound"
        )
        g.eq_macsh = Equation(
            m,
            name="EQ_MACSH",
            domain=[g.r, g.t, g.cg, g.cg],
            description="Macro shares in aggergate",
        )
        g.eq_macag = Equation(
            m,
            name="EQ_MACAG",
            domain=[g.r, g.t, g.cg],
            description="Macro aggergations",
        )
        g.eq_maces = Equation(
            m,
            name="EQ_MACES",
            domain=[g.r, g.t, g.cg, g.cg],
            description="Macro CES functions",
        )
        # *  EQ_LABOR(R,T)        'Labor dummy definition'
        # *  EQ_KNCAP(R,T)        'Capital dummy definition'
        # *  EQ_MCAP(R,T)         'Capital dynamics equation'
        # *  EQ_TMC(R,T)          'Terminal condition for investment in last period'
        # *  EQ_IVECBND(R,T)      'Bound on the sum of investment and energy costs'
        # *  EQ_DD(R,T,C)         'Demand decoupling equation'
        g.eq_demsh = Equation(
            m,
            name="EQ_DEMSH",
            domain=[g.r, g.t, g.c],
            description="Demand shares in aggergate",
        )
        g.eq_demag = Equation(
            m, name="EQ_DEMAG", domain=[g.r, g.t], description="Demand aggregation"
        )
        g.eq_demces = Equation(
            m,
            name="EQ_DEMCES",
            domain=[g.r, g.t, g.c],
            description="Demand CES function",
        )
        g.eq_enscst = Equation(
            m, name="EQ_ENSCST", domain=[g.r, g.t], description="Energy System costs"
        )
        # *  EQ_TRDBAL(T,TRD)     'Trade balance'
