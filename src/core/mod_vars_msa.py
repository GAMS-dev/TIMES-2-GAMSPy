# mod_vars_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * MOD_VARS.MSA Variable declarations for MACRO Stand-Alone
# *============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Variable

from core.base_class import GamsClass
from core.preppm_msa import PreppmMsa

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsMsa(GamsClass):
    """Translation unit for mod_vars.msa."""

    # Instance attributes
    module_name: str = "mod_vars_msa"
    gams_source: str = "mod_vars.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        self.include(PreppmMsa(self.tc, self.env, arg1="MSA"))

        # *  MACRO Related Variables
        g.VAR_K = Variable(
            m,
            name="VAR_K",
            domain=[g.Reg, g.t],
            description="total capital stock",
            type="POSITIVE",
        )
        g.VAR_D = Variable(
            m,
            name="VAR_D",
            domain=[g.Reg, g.t, g.Com],
            description="annual energy demands - before aeei adjustments",
            type="POSITIVE",
        )
        g.VAR_INV = Variable(
            m,
            name="VAR_INV",
            domain=[g.Reg, g.t],
            description="annual investments",
            type="POSITIVE",
        )
        g.VAR_EC = Variable(
            m,
            name="VAR_EC",
            domain=[g.Reg, g.t],
            description="annual energy cost",
            type="POSITIVE",
        )
        g.VAR_SP = Variable(
            m,
            name="VAR_SP",
            domain=[g.Reg, g.t, g.Com],
            description="artificial variable for scaling shadow price of demand",
            type="POSITIVE",
        )
        g.VAR_Y = Variable(
            m,
            name="VAR_Y",
            domain=[g.Reg, g.t],
            description="annual economy output (production)",
            type="POSITIVE",
        )
        g.VAR_C = Variable(
            m,
            name="VAR_C",
            domain=[g.Reg, g.t],
            description="annual consumption",
            type="POSITIVE",
        )
        # VAR_DEM(REG,T,COM) is already declared by ModVarsMod (mod_vars_mod.py),
        # which always runs ahead of this extension module -- guard against
        # redeclaration in case that assumption ever changes.
        if not self.tc.declared("VAR_DEM"):
            g.VAR_DEM = Variable(
                m,
                name="VAR_DEM",
                domain=[g.Reg, g.t, g.Com],
                description="Decoupled demands used in the energy model",
                type="POSITIVE",
            )
        g.VAR_CDM = Variable(
            m,
            name="VAR_CDM",
            domain=[g.r, g.item, g.ll],
            description="climate change damage",
            type="POSITIVE",
        )

        # * Objective Function Value
        g.VAR_UTIL = Variable(
            m, name="VAR_UTIL", description="discounted log of consumption"
        )
        g.VAR_NTX = Variable(
            m,
            name="VAR_NTX",
            domain=[g.r, g.t, g.item],
            description="trade (exports positive)",
        )

        self.tc.enqueue(self.exec1)

        if self.tc.defined("tm_udf"):
            self.env.set_global("objann", "YES")

        if not self.tc.defined("tm_udf"):
            self.tc.enqueue(self.exec2)

    def exec1(self) -> None:
        g = self.tc
        g.VAR_NTX.setRecords(None)
        g.VAR_CDM.lo[g.r, "N", g.Xtp] = 0.01

    def exec2(self) -> None:
        self.tc.tm_udf.setRecords(None)
