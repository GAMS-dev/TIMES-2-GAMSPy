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

from core.mod_vars_mod import ModVarsMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self.include(ModVarsMod(self.tc, self.env))
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET OBVANN(OBV) / OBJINV, OBJFIX, OBJVAR /;

  POSITIVE VARIABLES

*-----------------------------------------------------------------------------*
* MACRO Interface Variables
* - Annual Cost Components: investment, fixed, variable costs
* - Annual Demands
*-----------------------------------------------------------------------------*
  VAR_ANNCST(OBV,R,ALLYEAR,CUR)  Annualized costs
  VAR_DEM(R,MILESTONYR,C)        Annual useful demand

*-----------------------------------------------------------------------------*
* MACRO variables
*-----------------------------------------------------------------------------*
  VAR_EC(R,ALLYEAR)       'Annual energy costs in MACRO'
  VAR_C(R,T)              'Annual consumption in MACRO'
  VAR_Y(R,T)              'Annual production in MACRO'
  VAR_K(R,T)              'Total capital'
  VAR_INV(R,T)            'Annual investments in MACRO'
  VAR_D(R,T,CG)           'Annual useful demand in MACRO'
  VAR_SP(R,T,CG)          'Artificial variable for scaling shadow price'
  VAR_OBJCOST(R,ALLYEAR)  'Annual energy costs in TIMES'
  VAR_XCAP(R,YEAR,ITEM)   'Market penetration bounds - total new capacity'
  VAR_XCAPP(R,YEAR,P,J)   'Market penetration bounds - additional capacity'
  VAR_MELA(R,T,CG,J,BD)   'Step variables for elasticities'
  ;


  VARIABLES

*-----------------------------------------------------------------------------*
* MACRO variables
*-----------------------------------------------------------------------------*
  VAR_UTIL                Total utility
  VAR_NTX(R,T)            Trade in numeraire
  ;
""",
        )
        self.tc.enqueue(self.mod_vars_tm_exec)

    def mod_vars_tm_exec(self: ModVarsTm):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Activate demand variables
  RD_NLP(DEM) = 1;

  VAR_ANNCST.LO(OBV(UCN),R,T,CUR)$(RDCUR(R,CUR)$UC_RHS(UCN,'N')) = INF;
  VAR_ANNCST.LO(OBV(UCN),R,T,CUR)$(RDCUR(R,CUR)$UC_RHSR(R,UCN,'N')) = INF;
""",
        )
