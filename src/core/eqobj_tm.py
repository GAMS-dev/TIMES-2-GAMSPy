# equobj_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJ the objective cost functions for Macro
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *10/21
# *  - V-index used in place to T for MODLYEAR
# * Note: PASTYEAR always have D(V) = 1
# *  - V-vintage MODLYEAR year, the point in time where the investment took place
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.eqobjann_tm import EqobjannTm
from core.eqobjels_mod import EqobjelsMod
from core.eqobjfix_mod import EqobjfixMod
from core.eqobjinv_mod import EqobjinvMod
from core.eqobsalv_mod import EqobsalvMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjTm(GamsClass):
    """Translation unit for equobj.tm."""

    # Instance attributes
    module_name: str = "equobj_tm"
    gams_source: str = "equobj.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(module=self, phase="init", code="SET K_EOH(ALLYEAR);")
        self.tc.enqueue(self.exec1)
        self.tc.add_gams_code(
            module=self, phase="init", code="SET KTYAGE(LL,YEAR,LL,AGE);"
        )
        self.tc.enqueue(self.exec2)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Cases for ILED and TLIFE/D(t); values assigned in EQOBJINV
  SET OBJ_1A(R,ALLYEAR,P) //;
  SET OBJ_1B(R,ALLYEAR,P) //;
  SET OBJ_2A(R,ALLYEAR,P) //;
  SET OBJ_2B(R,ALLYEAR,P) //;
* Salvage controls
  SET OBJ_SUMS(R,ALLYEAR,P) //;
  SET OBJ_SUMS3(R,ALLYEAR,P) //;
  SET OBJ_SUMSI(R,ALLYEAR,P,ALLYEAR) //;
  PARAMETER OBJ_DCEOH(REG,CUR) //;
""",
        )

        # Investment Cost, Fixed Cost and Variable Cost components
        self.include(EqobjinvMod(self.tc, self.env, "tm", "exit"))
        self.include(EqobjfixMod(self.tc, self.env, "tm", "exit"))
        self.include(EqobsalvMod(self.tc, self.env, "tm", "exit"))
        self.include(EqobjannTm(self.tc, self.env))

        # Elastic Demand costs: only when MLF
        if self.env.macro == "Yes":
            self.include(EqobjelsMod(self.tc, self.env))

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
    EQ_OBJ(R,T) ..

      SUM(RDCUR(R,CUR),

* Investment Costs, Fixed Costs and Variable Costs (elastic demand costs excluded)

         SUM(OBVANN,VAR_ANNCST(OBVANN,R,T,CUR))

         )

    =E=

    VAR_OBJCOST(R,T);

""",
        )

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* [UR] 21.06.2003: K_EOH must include pastyears, since in eqobjfix.mod it links to past vintages
  K_EOH(EACHYEAR)$((YEARVAL(EACHYEAR) >= PYR_V1) * (YEARVAL(EACHYEAR) <= MIYR_VL)) = YES;
""",
        )

    def exec2(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  LOOP(SAMEAS('1',AGE),KTYAGE(K(LL),PERIODYR(T,Y_EOH(YEAR)),AGE+(ORD(YEAR)-ORD(LL)))$YK(YEAR,LL)=YES);
""",
        )
