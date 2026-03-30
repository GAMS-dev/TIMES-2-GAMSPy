# eqobjcst_tm.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJCST the objective functions investment, fixed and variable costs
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *  - Supports also alternative objective formulations
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.eqobjvar_mod import eqobjvar
from core.eqdamage_mod import EqdamageMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjcstTm(GamsClass):
    """Translation unit for eqobjcst.tm."""

    # Instance attributes
    module_name: str = "eqobjcst_tm"
    gams_source: str = "eqobjcst.tm"

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
        self.tc.enqueue(self.investment_equation)
        self.tc.enqueue(self.fixed_cost_equation)

        if self.tc.defined("DAM_COST"):
            is_dam_cost_defined = True
        else:
            is_dam_cost_defined = False
        self.tc.enqueue(
            self.variable_cost_equation,
            is_dam_cost_defined,
            self.env.TIMESED,
            self.env.VART,
            self.env.SWS,
        )

    def investment_equation(self):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
   EQ_ANNINV(R,T,CUR)$RDCUR(R,CUR)..

   VAR_ANNCST('OBJINV',R,T,CUR)  =E=

* Revised accounting for MACRO: Calculate annualized cost from discounted
* lump-sum investments undiscounted back to the lump-sum commissioning year K

   SUM(RTP_CPTYR(R,V,T,P)$OBJ_ICUR(R,V,P,CUR), COEF_CPT(R,V,T,P) *
       COEF_OBINV(R,V,P,CUR) * (VAR_NCAP(R,V,P)$TT(V)+NCAP_PASTI(R,V,P)))
   ;
""",
        )

    def fixed_cost_equation(self):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
   EQ_ANNFIX(R,T,CUR)$RDCUR(R,CUR) ..

   VAR_ANNCST('OBJFIX',R,T,CUR)*OBJ_PVT(R,T,CUR) =E=

* Revised accounting for MACRO: Calculate annualized cost from discounted
* lump-sum fixed costs undiscounted back to the lump-sum commissioning year K

$IF DEFINED VNRET $BATINCLUDE prepret.dsc OBJFIX

   SUM(RTP_CPTYR(R,V,T,P)$COEF_OBFIX(R,V,P,CUR), COEF_CPT(R,V,T,P) * OBJ_PVT(R,T,CUR) *
       COEF_OBFIX(R,V,P,CUR) * (VAR_NCAP(R,V,P)$TT(V)+NCAP_PASTI(R,V,P)))
  ;
""",
        )

    def variable_cost_equation(
        self, is_dam_cost_defined: bool, TIMESED: str, VART: str, SWS: str
    ):
        equation = rf"""
   EQ_ANNVAR(R,T,CUR)$RDCUR(R,CUR) ..

{eqobjvar("mod", "*")}

   OBJ_PVT(R,T,CUR) * VAR_ANNCST('OBJVAR',R,T,CUR)
"""

        if is_dam_cost_defined:
            equation += "-"
            equation += f"{EqdamageMod(self.tc, self.env, 'E', '*', '$EXIT')}"

        if TIMESED != "YES":
            equation += ";"
        else:
            equation += rf"""
    -
   SUM((MI_DMAS(R,COM,C),BDNEQ(BD))$MI_ESUB(R,T,COM), BDSIG(BD) *
     SUM(RTCS_VARC(R,T,C,S)$COM_STEP(R,C,BD), COEF_PVT(R,T) * COM_BPRICE(R,T,C,S,CUR) *
       SUM(RCJ(R,C,J,BD),{VART}_ELAST(R,T,C,S,J,BD {SWS}) * MI_AGC(R,T,COM,C,J,BD))));
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)
