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
from core.prepret_dsc import PrepretDsc

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

        g.VAR_ACT = Variable(
            m,
            name="VAR_ACT",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.s],
            description="Overall activity of a process",
        )
        g.VAR_CAP = Variable(
            m,
            name="VAR_CAP",
            type="Positive",
            domain=[g.r, g.allyear, g.p],
            description="Installed capacity of a process",
        )
        Variable(
            m,
            name="VAR_FLO",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s],
            description="Level of process commodity flow",
        )
        Variable(
            m,
            name="VAR_IRE",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, g.ie],
            description="Inter regional trade flow",
        )
        g.VAR_NCAP = Variable(
            m,
            name="VAR_NCAP",
            type="Positive",
            domain=[g.r, g.allyear, g.p],
            description="New capacity of a process",
        )
        g.VAR_COMNET = Variable(
            m,
            name="VAR_COMNET",
            type="Positive",
            domain=[g.r, g.allyear, g.c, g.s],
            description="Net commodity level",
        )
        g.VAR_COMPRD = Variable(
            m,
            name="VAR_COMPRD",
            type="Positive",
            domain=[g.r, g.allyear, g.c, g.s],
            description="Production of commodity",
        )
        g.VAR_ELAST = Variable(
            m,
            name="VAR_ELAST",
            type="Positive",
            domain=[g.r, g.allyear, g.c, g.s, g.j, g.bd],
            description="Demand change due to price elasticity",
        )
        g.VAR_DEM = Variable(
            m,
            name="VAR_DEM",
            type="Positive",
            domain=[g.r, g.Milestonyr, g.c],
            description="Demand variable for MACRO",
        )
        g.VAR_CUMCOM = Variable(
            m,
            name="VAR_CUMCOM",
            type="Positive",
            domain=[g.r, g.c, g.comvar, g.allyear, g.allyear],
            description="Cumulative commodity PRD or NET",
        )
        g.VAR_CUMFLO = Variable(
            m,
            name="VAR_CUMFLO",
            type="Positive",
            domain=[g.r, g.p, g.c, g.allyear, g.allyear],
            description="Cumulative process flow",
        )
        g.VAR_CUMCST = Variable(
            m,
            name="VAR_CUMCST",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.costagg, g.cur],
            description="Cumulative regional cost",
        )
        g.VAR_SIN = Variable(
            m,
            name="VAR_SIN",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s],
            description="Input flow into storage",
        )
        g.VAR_SOUT = Variable(
            m,
            name="VAR_SOUT",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s],
            description="Output flow from storage",
        )
        g.VAR_BLND = Variable(
            m,
            name="VAR_BLND",
            type="Positive",
            domain=[g.r, g.allyear, g.Com, g.Com],
            description="Refinery blending",
        )
        g.VAR_DAM = Variable(
            m,
            name="VAR_DAM",
            type="Positive",
            domain=[g.r, g.t, g.c, g.bd, g.j],
            description="Damage variables",
        )
        g.VAR_RCAP = Variable(
            m,
            name="VAR_RCAP",
            type="Positive",
            domain=[g.r, g.allyear, g.ll, g.p],
            description="New retirements",
        )
        g.VAR_SCAP = Variable(
            m,
            name="VAR_SCAP",
            type="Positive",
            domain=[g.r, g.allyear, g.ll, g.p],
            description="Cumulative retirements",
        )
        g.VAR_UPS = Variable(
            m,
            name="VAR_UPS",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.lA],
            description="Start ups",
        )
        g.VAR_UPT = Variable(
            m,
            name="VAR_UPT",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.upt],
            description="Start ups by type",
        )
        g.VAR_UDP = Variable(
            m,
            name="VAR_UDP",
            type="Positive",
            domain=[g.r, g.allyear, g.allyear, g.p, g.s, g.lA],
            description="Unit dispatching",
        )
        g.VAR_RLD = Variable(
            m,
            name="VAR_RLD",
            type="Positive",
            domain=[g.r, g.t, g.s, g.item],
            description="Residual loads",
        )
        g.VAR_OBJ = Variable(
            m,
            name="VAR_OBJ",
            type="Positive",
            domain=[g.r, g.obv, g.cur],
            description="Objective costs INV,SAL,FIX,VAR,DAM",
        )
        g.VAR_OBJELS = Variable(
            m,
            name="VAR_OBJELS",
            type="Positive",
            domain=[g.r, g.bd, g.cur],
            description="Change in Consumer surplus",
        )
        g.VAS_UPDEV = Variable(
            m,
            name="VAS_UPDEV",
            type="Positive",
            domain=[g.allsow],
            description="Upside deviation of OBJ",
        )

        g.OBJZ = Variable(m, name="OBJZ", type="Free")
        g.VAR_UC = Variable(
            m,
            name="VAR_UC",
            type="Free",
            domain=[g.ucn],
            description="Slacks for UC constraints",
        )
        g.VAR_UCR = Variable(
            m,
            name="VAR_UCR",
            type="Free",
            domain=[g.ucn, g.r],
            description="Slacks for UCR constraints",
        )
        g.VAR_UCT = Variable(
            m,
            name="VAR_UCT",
            type="Free",
            domain=[g.ucn, g.t],
            description="Slacks for UCT constraints",
        )
        g.VAR_UCRT = Variable(
            m,
            name="VAR_UCRT",
            type="Free",
            domain=[g.ucn, g.r, g.t],
            description="Slacks for UCRT constraints",
        )
        g.VAR_UCTS = Variable(
            m,
            name="VAR_UCTS",
            type="Free",
            domain=[g.ucn, g.t, g.s],
            description="Slacks for UCTS constraints",
        )
        g.VAR_UCRTS = Variable(
            m,
            name="VAR_UCRTS",
            type="Free",
            domain=[g.ucn, g.r, g.t, g.s],
            description="Slacks for UCRTS constraints",
        )

        if "VNRET" in self.tc.container.listSymbols():
            self.include(PrepretDsc(self.tc, self.env, arg1="DECL"))
        if self.tc.defined("PRC_REACT"):
            self.include(PowerfloVda(self.tc, self.env, arg1="DECL"))
        if self.tc.defined("VAR_STS"):
            g.var_sts = Parameter(
                m, "VAR_STS", domain=[g.r, g.year, g.t, g.p, g.s, g.lA]
            )
