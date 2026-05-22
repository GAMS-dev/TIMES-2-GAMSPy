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

from core.preppm_msa import PreppmMsa

from .base_class import GamsClass

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
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.include(PreppmMsa(self.tc, self.env, arg1="MSA"))

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
*  MACRO Related Variables

POSITIVE VARIABLES
  VAR_K(REG,T)        total capital stock
  VAR_D(REG,T,COM)    annual energy demands - before aeei adjustments
  VAR_INV(REG,T)      annual investments
  VAR_EC(REG,T)       annual energy cost
  VAR_SP(REG,T,COM)   artificial variable for scaling shadow price of demand
  VAR_Y(REG,T)        annual economy output (production)
  VAR_C(REG,T)        annual consumption
  VAR_DEM(REG,T,COM)  Decoupled demands used in the energy model
  VAR_CDM(R,ITEM,LL)  climate change damage

* Objective Function Value

VARIABLES
  VAR_UTIL           discounted log of consumption
  VAR_NTX(R,T,ITEM)  trade (exports positive)
;
""",
        )

        self.tc.enqueue(self.exec1)

        if self.tc.defined("tm_udf"):
            self.env.set_global("objann", "YES")

        if not self.tc.defined("tm_udf"):
            self.tc.enqueue(self.exec2)

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OPTION CLEAR=VAR_NTX;
VAR_CDM.LO(R,'N',XTP) = .01;
""",
        )

    def exec2(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OPTION CLEAR=TM_UDF;
""",
        )
