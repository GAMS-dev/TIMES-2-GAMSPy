# mod_vars_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.MOD lists the individual variables of all instances of the MODEL
# *=============================================================================*
# * Questions/Comments:
# *  - no need to add SOW-index to variables under MACRO
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Set, SpecialValues, Variable

from core.base_class import GamsClass
from core.mod_vars_mod import ModVarsMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsTm(GamsClass):
    """Translation unit for mod_vars.tm."""

    # Instance attributes
    module_name: str = "mod_vars_tm"
    gams_source: str = "mod_vars.tm"

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
        m = g.container

        self.include(ModVarsMod(self.tc, self.env))
        g.Obvann = Set(
            m, name="OBVANN", domain=[g.obv], records=["OBJINV", "OBJFIX", "OBJVAR"]
        )
        # *-----------------------------------------------------------------------------*
        # * MACRO Interface Variables
        # * - Annual Cost Components: investment, fixed, variable costs
        # * - Annual Demands
        # *-----------------------------------------------------------------------------*
        g.VAR_ANNCST = Variable(
            m,
            name="VAR_ANNCST",
            domain=[g.obv, g.r, g.allyear, g.cur],
            description="Annualized costs",
            type="POSITIVE",
        )
        g.VAR_DEM = Variable(
            m,
            name="VAR_DEM",
            domain=[g.r, g.Milestonyr, g.c],
            description="Annual useful demand",
            type="POSITIVE",
        )
        # *-----------------------------------------------------------------------------*
        # * MACRO variables
        # *-----------------------------------------------------------------------------*
        g.VAR_EC = Variable(
            m,
            name="VAR_EC",
            domain=[g.r, g.allyear],
            description="Annual energy costs in MACRO",
            type="POSITIVE",
        )
        g.VAR_C = Variable(
            m,
            name="VAR_C",
            domain=[g.r, g.t],
            description="Annual consumption in MACRO",
            type="POSITIVE",
        )
        g.VAR_Y = Variable(
            m,
            name="VAR_Y",
            domain=[g.r, g.t],
            description="Annual production in MACRO",
            type="POSITIVE",
        )
        g.VAR_K = Variable(
            m,
            name="VAR_K",
            domain=[g.r, g.t],
            description="Total capital",
            type="POSITIVE",
        )
        g.VAR_INV = Variable(
            m,
            name="VAR_INV",
            domain=[g.r, g.t],
            description="Annual investments in MACRO",
            type="POSITIVE",
        )
        g.VAR_D = Variable(
            m,
            name="VAR_D",
            domain=[g.r, g.t, g.cg],
            description="Annual useful demand in MACRO",
            type="POSITIVE",
        )
        g.VAR_SP = Variable(
            m,
            name="VAR_SP",
            domain=[g.r, g.t, g.cg],
            description="Artificial variable for scaling shadow price",
            type="POSITIVE",
        )
        g.VAR_OBJCOST = Variable(
            m,
            name="VAR_OBJCOST",
            domain=[g.r, g.allyear],
            description="Annual energy costs in TIMES",
            type="POSITIVE",
        )
        g.VAR_XCAP = Variable(
            m,
            name="VAR_XCAP",
            domain=[g.r, g.year, g.item],
            description="Market penetration bounds - total new capacity",
            type="POSITIVE",
        )
        g.VAR_XCAPP = Variable(
            m,
            name="VAR_XCAPP",
            domain=[g.r, g.year, g.p, g.j],
            description="Market penetration bounds - additional capacity",
            type="POSITIVE",
        )
        g.VAR_MELA = Variable(
            m,
            name="VAR_MELA",
            domain=[g.r, g.t, g.cg, g.j, g.bd],
            description="Step variables for elasticities",
            type="POSITIVE",
        )
        # *-----------------------------------------------------------------------------*
        # * MACRO variables
        # *-----------------------------------------------------------------------------*
        g.VAR_UTIL = Variable(m, name="VAR_UTIL", description="Total utility")
        g.VAR_NTX = Variable(
            m, name="VAR_NTX", domain=[g.r, g.t], description="Trade in numeraire"
        )

        self.tc.enqueue(self.mod_vars_tm_exec)

    def mod_vars_tm_exec(self: ModVarsTm) -> None:
        g = self.tc
        # * Activate demand variables
        g.rd_nlp[g.Dem] = 1.0
        g.VAR_ANNCST.lo[g.obv[g.ucn], g.r, g.t, g.cur].where[
            (g.Rdcur[g.r, g.cur].where[g.uc_rhs[g.ucn, "N"]])
        ] = SpecialValues.POSINF
        g.VAR_ANNCST.lo[g.obv[g.ucn], g.r, g.t, g.cur].where[
            (g.Rdcur[g.r, g.cur].where[g.uc_rhsr[g.r, g.ucn, "N"]])
        ] = SpecialValues.POSINF
