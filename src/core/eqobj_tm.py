# eqobj_tm.py
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

from gamspy import Parameter, Set

from core.base_class import GamsClass
from core.eqobjann_tm import EqobjannTm
from core.eqobjels_mod import EqobjelsMod
from core.eqobjfix_mod import EqobjfixMod
from core.eqobjinv_mod import EqobjinvMod
from core.eqobsalv_mod import EqobsalvMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjTm(GamsClass):
    """Translation unit for eqobj.tm."""

    # Instance attributes
    module_name: str = "eqobj_tm"
    gams_source: str = "eqobj.tm"

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
        g = self.tc
        m = g.container

        g.KEoh = Set(m, name="K_EOH", domain=[g.allyear])
        self.tc.enqueue(self.exec1)
        g.Ktyage = Set(m, name="KTYAGE", domain=[g.ll, g.year, g.ll, g.age])
        self.tc.enqueue(self.exec2)

        r, allyear, p, reg, cur = g.r, g.allyear, g.p, g.Reg, g.cur

        # * Cases for ILED and TLIFE/D(t); values assigned in EQOBJINV
        g.Obj1a = Set(m, name="OBJ_1A", domain=[r, allyear, p])
        g.Obj1b = Set(m, name="OBJ_1B", domain=[r, allyear, p])
        g.Obj2a = Set(m, name="OBJ_2A", domain=[r, allyear, p])
        g.Obj2b = Set(m, name="OBJ_2B", domain=[r, allyear, p])
        # * Salvage controls
        g.ObjSums = Set(m, name="OBJ_SUMS", domain=[r, allyear, p])
        g.ObjSums3 = Set(m, name="OBJ_SUMS3", domain=[r, allyear, p])
        g.ObjSumsi = Set(m, name="OBJ_SUMSI", domain=[r, allyear, p, allyear])
        g.obj_dceoh = Parameter(m, name="OBJ_DCEOH", domain=[reg, cur])

        # Investment Cost, Fixed Cost and Variable Cost components
        self.include(EqobjinvMod(self.tc, self.env, "tm", "exit"))
        self.include(EqobjfixMod(self.tc, self.env, arg1="exit"))
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
