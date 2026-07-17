# eqobj_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJ the objective functions
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *  - V-index used in place to T for MODLYEAR
# * Note: PASTYEAR always have D(V) = 1
# *  - V-vintage MODLYEAR year, the point in time where the investment took place
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Set

from core.base_class import GamsClass
from core.eqobjann_tm import EqobjannTm
from core.eqobjels_mod import EqobjelsMod
from core.eqobjels_rpt import EqobjelsRpt
from core.eqobjfix_mod import EqobjfixMod
from core.eqobjfix_rpt import EqobjfixRpt
from core.eqobjinv_mod import EqobjinvMod
from core.eqobjinv_rpt import EqobjinvRpt
from core.eqobjvar_mod import EqobjvarMod
from core.eqobjvar_rpt import EqobjvarRpt
from core.eqobsalv_mod import EqobsalvMod
from core.eqobsalv_rpt import EqobsalvRpt
from core.prepret_dsc import PrepretDsc

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjMod(GamsClass):
    """Translation unit for eqobj.mod."""

    # Instance attributes
    module_name: str = "eqobj_mod"
    gams_source: str = "eqobj.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="SET K_EOH(ALLYEAR);",
        )
        self.tc.enqueue(self.exec1)
        # Sets for periodic costs
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="SET KTYAGE(LL,YEAR,LL,AGE);",
        )
        self.add_records_to_universe_item(["OBJELS"])
        self.tc.enqueue(self.exec2)

        r, allyear, p = g.r, g.allyear, g.p

        # * Cases for ILED and TLIFE/D(t); values assigned in EQOBJINV
        g.Obj1a = Set(m, name="OBJ_1A", domain=[r, allyear, p])
        g.Obj1b = Set(m, name="OBJ_1B", domain=[r, allyear, p])
        g.Obj2a = Set(m, name="OBJ_2A", domain=[r, allyear, p])
        g.Obj2b = Set(m, name="OBJ_2B", domain=[r, allyear, p])
        # * Salvage controls
        g.ObjSums = Set(m, name="OBJ_SUMS", domain=[r, allyear, p])
        g.ObjSums3 = Set(m, name="OBJ_SUMS3", domain=[r, allyear, p])
        g.ObjSumsi = Set(m, name="OBJ_SUMSI", domain=[r, allyear, p, allyear])

        if self.tc.declared("VNRET"):
            self.include(PrepretDsc(self.tc, self.env, arg1="EQOBJ"))

        # Elastic Demand costs
        if self.arg1.upper() == "MOD":
            self.include(EqobjinvMod(self.tc, self.env, arg1="EQOBJ", arg2=""))
        elif self.arg1.upper() == "RPT":
            self.include(EqobjinvRpt(self.tc, self.env))

        # Fixed O&M Cost and Tax components
        if self.env.timesed == "YES":
            if self.arg1.upper() == "MOD":
                self.include(EqobjelsMod(self.tc, self.env))
            elif self.arg1.upper() == "RPT":
                self.include(EqobjelsRpt(self.tc, self.env))

        # Fixed O&M Cost and Tax components
        if self.arg1.upper() == "MOD":
            self.include(EqobjfixMod(self.tc, self.env, arg1=self.arg1))
        elif self.arg1.upper() == "RPT":
            self.include(EqobjfixRpt(self.tc, self.env, arg1=self.arg1))

        # Variable O&M and direct commodity related cost components
        if (self.env.oblong + self.env.obj).upper() == "YESALT":
            self.env.set_scoped("obj", "LIN")
            self.env.set_scoped("varcost", "LIN")

        if self.arg1.upper() == "MOD":
            self.include(EqobjvarMod(self.tc, self.env, arg1=self.arg1))
        elif self.arg1.upper() == "RPT":
            self.include(EqobjvarRpt(self.tc, self.env, arg1=self.arg1))

        # Salvage value of investment and decommissioning costs
        if self.arg1.upper() == "MOD":
            self.include(EqobsalvMod(self.tc, self.env, arg1=self.arg1))
        elif self.arg1.upper() == "RPT":
            self.include(EqobsalvRpt(self.tc, self.env, arg1=self.arg1))

        # Annualized objective formulation
        if self.env.objann.upper() == "YES":
            self.include(EqobjannTm(self.tc, self.env, arg1=self.arg1))

        # Actual OBJ
        is_stages = self.env.stages.upper() == "YES"
        is_timesed = self.env.timesed == "YES"
        is_micro = self.env.micro.upper() == "YES"

        eq_lhs = (
            f"{self.env.eq}_ROBJ(REG(R){self.env.sow}) .. -{self.env.var}_UCR('OBJZ',R{self.env.sow}) +"
            if is_stages
            else f"{self.env.eq}_OBJ .. -objZ +"
        )

        include_main_ext = ""
        # TODO: no obj_ext files present -> remove code
        # if self.env.extend != "":
        #     extensions = {}
        #     requested_exts = set(self.env.extend.split())
        #     include_main_ext = include_extension(
        #         module=self,
        #         extensions=extensions,
        #         requested_exts=requested_exts,
        #         source="obj_ext",
        #     )

        if is_timesed or is_micro:
            self.add_records_to_universe_item(["OBJELS"])

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq_lhs}

      SUM(RDCUR(R,CUR),

* Investment Costs, Tax/Subsidies and Decommissioning
* Salvage value of investment and decommissioning costs
* Fixed O&M and Tax/Subsidies
* Variable O&M and direct commodity costs
* Damages

        SUM((ITEM,OBV)$SUM_OBJ(ITEM,OBV),{self.env.var}_OBJ(R,OBV,CUR {self.env.sow})*SUM_OBJ(ITEM,OBV))

* Elastic Demand costs
{" +SUM(BD," + self.env.var + "_OBJELS(R,BD,CUR " + self.env.sow + ")*BDSIG(BD))$SUM_OBJ(R,'OBJELS')" if is_timesed else ""}
{" -" + self.env.var + "_OBJELS(R,'FX',CUR " + self.env.sow + ")$SUM_OBJ(R,'OBJELS')" if is_micro else ""}

         )

* Extensions to objective function
{include_main_ext}

    =E= 0
;
""",
        )

        # Stochastic objective function
        if not is_stages:
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_EXPOBJ(AUXSOW(WW))..
     (SUM(SOW, SW_PROB(SOW) * {self.env.var}_UC('OBJZ'{self.env.sow}))/SW_NORM - VAS_EXPOBJ)$(NOT SW_PHASE) +
     SUM(SOW,SUM(UC_N$(SUM(UC_T_SUM(UC_R_SUM(R,UC_N),T),1)$S_UCOBJ(UC_N,SOW)),
               S_UCOBJ(UC_N,SOW)*{self.env.var}_UC(UC_N{self.env.sow})) - {self.env.var}_UC('OBJ1'{self.env.sow}))$(SW_PHASE GT 0) +
     SUM(SOW,SUM(UC_N$(SUM(UC_T_SUM(UC_R_SUM(R,UC_N),T),1)$S_UCOBJ(UC_N,WW)),
               S_UCOBJ(UC_N,WW)*{self.env.var}_UC(UC_N{self.env.sow})) - {self.env.var}_UC('OBJ1'{self.env.swd}))$(SW_PHASE LT 0)

   =E=  0;

  EQ_UPDEV(SOW)$SW_LAMBDA..
     {self.env.var}_UC('OBJZ'{self.env.sow}) - VAS_EXPOBJ$(SW_LAMBDA GT 0) - {self.env.var}_UC('OBJ1'{self.env.sow})$(SW_LAMBDA LT 0)
     =L=                     VAS_UPDEV(SOW)$(SW_LAMBDA GT 0) + VAS_UPDEV('1')$(SW_LAMBDA LT 0);

  {self.env.eq}_SOBJ('N'{self.env.sow}).. -{self.env.var}_UC('OBJZ'{self.env.sow}) + SUM(R,{self.env.var}_UCR('OBJZ',R{self.env.sow})) =E= 0;

  EQ_OBJ..
     ((VAS_EXPOBJ + SW_LAMBDA * SUM(SOW, SW_PROB(SOW) * VAS_UPDEV(SOW))/SW_NORM)$(SW_LAMBDA GE 0)
      - MIN(0,SW_LAMBDA)*VAS_UPDEV('1'))$(NOT SW_PHASE) +
     SUM(SOW,{self.env.var}_UC('OBJ1'{self.env.sow})$(ABS(SW_PHASE) EQ 1) + {self.env.var}_UC('OBJZ'{self.env.sow})$(ABS(SW_PHASE) EQ 2))

   =E=  objZ;
""",
        )

    def exec1(self: EqobjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* [UR] 21.06.2003: K_EOH must include pastyears, since it links to past vintages
  K_EOH(EACHYEAR)$((YEARVAL(EACHYEAR) >= PYR_V1) * (YEARVAL(EACHYEAR) <= MIYR_VL)) = YES;
""",
        )

    def exec2(self: EqobjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  LOOP(SAMEAS('1',AGE),
    KTYAGE(K(LL),PERIODYR(T,Y_EOH(YEAR)),AGE+(ORD(YEAR)-ORD(LL)))$YK(YEAR,LL)=YES;
    KTYAGE(K(LL),YK(PYR_S,Y_EOH(YEAR)),AGE+(ORD(YEAR)-ORD(LL)))$YK(YEAR,LL)=YES);

* Set up summing of OBJ component variables
  SUM_OBJ(OBV,ITEM) = DIAG(OBV,ITEM);
  SUM_OBJ(OBV('OBJSAL'),OBV)  =  -1;
  SUM_OBJ(R,'OBJELS') = 1$SUM(RCJ(R,C,J,BD),1);
""",
        )
