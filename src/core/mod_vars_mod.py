# mod_vars_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.MOD lists the individual variables of all instances of the MODEL   *
# *=============================================================================*
# * Questions/Comments:
# *  -
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set, Variable

from core.base_class import GamsClass
from core.powerflo_vda import PowerfloVda
from core.prepret_dsc import PrepretDsc, PrepretDscConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsMod(GamsClass):
    """Translation unit for mod_vars.mod."""

    # Instance attributes
    module_name: str = "mod_vars_mod"
    gams_source: str = "mod_vars.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # Set of standard objective components
        g.obv = Set(m, "OBV", records=["OBJINV", "OBJFIX", "OBJSAL", "OBJVAR"])

        var = self.env.var
        swd = self.env.swd_GP

        # *-----------------------------------------------------------------------------
        # POSITIVE VARIABLES
        # *-----------------------------------------------------------------------------
        # * Process-related variables
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_ACT",
            var=Variable(
                m,
                name=f"{var}_ACT",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swd],
                description="Overall activity of a process",
            ),
        )
        g.set_variable(
            name=f"{var}_CAP",
            var=Variable(
                m,
                name=f"{var}_CAP",
                type="Positive",
                domain=[g.r, g.allyear, g.p, *swd],
                description="Installed capacity of a process",
            ),
        )
        g.set_variable(
            name=f"{var}_FLO",
            var=Variable(
                m,
                name=f"{var}_FLO",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, *swd],
                description="Level of process commodity flow",
            ),
        )
        g.set_variable(
            name=f"{var}_IRE",
            var=Variable(
                m,
                name=f"{var}_IRE",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, g.ie, *swd],
                description="Inter regional trade flow",
            ),
        )
        g.set_variable(
            name=f"{var}_NCAP",
            var=Variable(
                m,
                name=f"{var}_NCAP",
                type="Positive",
                domain=[g.r, g.allyear, g.p, *swd],
                description="New capacity of a process",
            ),
        )

        # *-----------------------------------------------------------------------------
        # * Commodity-related variables
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_COMNET",
            var=Variable(
                m,
                name=f"{var}_COMNET",
                type="Positive",
                domain=[g.r, g.allyear, g.c, g.s, *swd],
                description="Net commodity level",
            ),
        )
        g.set_variable(
            name=f"{var}_COMPRD",
            var=Variable(
                m,
                name=f"{var}_COMPRD",
                type="Positive",
                domain=[g.r, g.allyear, g.c, g.s, *swd],
                description="Production of commodity",
            ),
        )
        g.set_variable(
            name=f"{var}_ELAST",
            var=Variable(
                m,
                name=f"{var}_ELAST",
                type="Positive",
                domain=[g.r, g.allyear, g.c, g.s, g.j, g.bd, *swd],
                description="Demand change due to price elasticity",
            ),
        )
        g.set_variable(
            name=f"{var}_DEM",
            var=Variable(
                m,
                name=f"{var}_DEM",
                type="Positive",
                domain=[g.r, g.Milestonyr, g.c, *swd],
                description="Demand variable for MACRO",
            ),
        )

        # *-----------------------------------------------------------------------------
        # * Cumulative variables
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_CUMCOM",
            var=Variable(
                m,
                name=f"{var}_CUMCOM",
                type="Positive",
                domain=[g.r, g.c, g.comvar, g.allyear, g.allyear, *swd],
                description="Cumulative commodity PRD or NET",
            ),
        )
        g.set_variable(
            name=f"{var}_CUMFLO",
            var=Variable(
                m,
                name=f"{var}_CUMFLO",
                type="Positive",
                domain=[g.r, g.p, g.c, g.allyear, g.allyear, *swd],
                description="Cumulative process flow",
            ),
        )
        g.set_variable(
            name=f"{var}_CUMCST",
            var=Variable(
                m,
                name=f"{var}_CUMCST",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.costagg, g.cur, *swd],
                description="Cumulative regional cost",
            ),
        )

        # *-----------------------------------------------------------------------------
        # * Storage variables
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_SIN",
            var=Variable(
                m,
                name=f"{var}_SIN",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, *swd],
                description="Input flow into storage",
            ),
        )

        g.set_variable(
            name=f"{var}_SOUT",
            var=Variable(
                m,
                name=f"{var}_SOUT",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, *swd],
                description="Output flow from storage",
            ),
        )

        # *-----------------------------------------------------------------------------
        # * Additional features
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_BLND",
            var=Variable(
                m,
                name=f"{var}_BLND",
                type="Positive",
                domain=[g.r, g.allyear, g.Com, g.Com, *swd],
                description="Refinery blending",
            ),
        )
        g.set_variable(
            name=f"{var}_DAM",
            var=Variable(
                m,
                name=f"{var}_DAM",
                type="Positive",
                domain=[g.r, g.t, g.c, g.bd, g.j, *swd],
                description="Damage variables",
            ),
        )
        g.set_variable(
            name=f"{var}_RCAP",
            var=Variable(
                m,
                name=f"{var}_RCAP",
                type="Positive",
                domain=[g.r, g.allyear, g.ll, g.p, *swd],
                description="New retirements",
            ),
        )
        g.set_variable(
            name=f"{var}_SCAP",
            var=Variable(
                m,
                name=f"{var}_SCAP",
                type="Positive",
                domain=[g.r, g.allyear, g.ll, g.p, *swd],
                description="Cumulative retirements",
            ),
        )
        g.set_variable(
            name=f"{var}_UPS",
            var=Variable(
                m,
                name=f"{var}_UPS",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.lA, *swd],
                description="Start ups",
            ),
        )
        g.set_variable(
            name=f"{var}_UPT",
            var=Variable(
                m,
                name=f"{var}_UPT",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.upt, *swd],
                description="Start ups by type",
            ),
        )
        g.set_variable(
            name=f"{var}_UDP",
            var=Variable(
                m,
                name=f"{var}_UDP",
                type="Positive",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.lA, *swd],
                description="Unit dispatching",
            ),
        )
        g.set_variable(
            name=f"{var}_RLD",
            var=Variable(
                m,
                name=f"{var}_RLD",
                type="Positive",
                domain=[g.r, g.t, g.s, g.item, *swd],
                description="Residual loads",
            ),
        )

        # *=============================================================================*
        # * Objective Function Components
        # *   - investment cost + tax/sub + decommissioning in INV
        # *   - fixed O&M + fixed tax/sub in FIX
        # *   - variable O&M + commodity direct costs
        # *   - salvage
        # *=============================================================================*

        g.set_variable(
            name=f"{var}_OBJ",
            var=Variable(
                m,
                name=f"{var}_OBJ",
                type="Positive",
                domain=[g.r, g.obv, g.cur, *swd],
                description="Objective costs INV,SAL,FIX,VAR,DAM",
            ),
        )
        g.set_variable(
            name=f"{var}_OBJELS",
            var=Variable(
                m,
                name=f"{var}_OBJELS",
                type="Positive",
                domain=[g.r, g.bd, g.cur, *swd],
                description="Change in Consumer surplus",
            ),
        )
        g.VAS_UPDEV = Variable(
            m,
            name="VAS_UPDEV",
            type="Positive",
            domain=[g.allsow],
            description="Upside deviation of OBJ",
        )

        # *=============================================================================*
        # * Objective Function Variables
        # *   - total discounted system cost
        # *=============================================================================*
        g.OBJZ = Variable(m, name="OBJZ", type="Free")
        g.VAS_EXPOBJ = Variable(
            m, name="VAS_EXPOBJ", description="Expected value of total OBJ"
        )

        # *-----------------------------------------------------------------------------
        # * Slack variables of user-constraints
        # *-----------------------------------------------------------------------------

        g.set_variable(
            name=f"{var}_UC",
            var=Variable(
                m,
                name=f"{var}_UC",
                type="Free",
                domain=[g.ucn, *swd],
                description="Slacks for UC constraints",
            ),
        )
        g.set_variable(
            name=f"{var}_UCR",
            var=Variable(
                m,
                name=f"{var}_UCR",
                type="Free",
                domain=[g.ucn, g.r, *swd],
                description="Slacks for UCR constraints",
            ),
        )
        g.set_variable(
            name=f"{var}_UCT",
            var=Variable(
                m,
                name=f"{var}_UCT",
                type="Free",
                domain=[g.ucn, g.t, *swd],
                description="Slacks for UCT constraints",
            ),
        )
        g.set_variable(
            name=f"{var}_UCRT",
            var=Variable(
                m,
                name=f"{var}_UCRT",
                type="Free",
                domain=[g.ucn, g.r, g.t, *swd],
                description="Slacks for UCRT constraints",
            ),
        )
        g.set_variable(
            name=f"{var}_UCTS",
            var=Variable(
                m,
                name=f"{var}_UCTS",
                type="Free",
                domain=[g.ucn, g.t, g.s, *swd],
                description="Slacks for UCTS constraints",
            ),
        )
        g.set_variable(
            name=f"{var}_UCRTS",
            var=Variable(
                m,
                name=f"{var}_UCRTS",
                type="Free",
                domain=[g.ucn, g.r, g.t, g.s, *swd],
                description="Slacks for UCRTS constraints",
            ),
        )

        # *-----------------------------------------------------------------------------
        # * Other variables in model extensions
        # *-----------------------------------------------------------------------------
        # * [AL] ETL variables automatically by extension manager

        if self.tc.declared("VNRET"):
            self.include(
                PrepretDsc(self.tc, self.env, config=PrepretDscConfig(arg1="DECL"))
            )
        if self.tc.defined("PRC_REACT"):
            self.include(PowerfloVda(self.tc, self.env, arg1="DECL"))

        if not macro.var_sts.active:
            g.var_sts = Parameter(
                m, name="VAR_STS", domain=[g.r, g.year, g.t, g.p, g.s, g.lA]
            )
