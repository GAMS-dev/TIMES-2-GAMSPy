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

from core.powerflo_vda import PowerfloVda
from core.prepret_dsc import PrepretDsc

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsMod(GamsClass):
    """Translation unit for mod_vars.mod."""

    # Instance attributes
    module_name: str = "mod_vars_mod"
    gams_source: str = "mod_vars.mod"

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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Set of standard objective components
  SET OBV / OBJINV, OBJFIX, OBJSAL, OBJVAR /;

*-----------------------------------------------------------------------------
 POSITIVE VARIABLES
*-----------------------------------------------------------------------------
* Process-related variables
*-----------------------------------------------------------------------------
  {self.env.var}_ACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swd}) 		Overall activity of a process
  {self.env.var}_CAP(R,ALLYEAR,P {self.env.swd})           		Installed capacity of a process
  {self.env.var}_FLO(R,ALLYEAR,ALLYEAR,P,C,S {self.env.swd})		Level of process commodity flow
  {self.env.var}_IRE(R,ALLYEAR,ALLYEAR,P,C,S,IE {self.env.swd})		Inter-regional trade flow
  {self.env.var}_NCAP(R,ALLYEAR,P {self.env.swd})            		New capacity of a process

*-----------------------------------------------------------------------------
* Commodity-related variables
*-----------------------------------------------------------------------------
  {self.env.var}_COMNET(R,ALLYEAR,C,S {self.env.swd})     		Net commodity level
  {self.env.var}_COMPRD(R,ALLYEAR,C,S {self.env.swd})     		Production of commodity
  {self.env.var}_ELAST(R,ALLYEAR,C,S,J,BD {self.env.swd}) 		Demand change due to price elasticity
  {self.env.var}_DEM(R,MILESTONYR,C {self.env.swd})       		Demand variable for MACRO

*-----------------------------------------------------------------------------
* Cumulative variables
*-----------------------------------------------------------------------------
  {self.env.var}_CUMCOM(R,C,COM_VAR,ALLYEAR,ALLYEAR {self.env.swd}) 	Cumulative commodity PRD or NET
  {self.env.var}_CUMFLO(R,P,C,ALLYEAR,ALLYEAR {self.env.swd})      	Cumulative process flow
  {self.env.var}_CUMCST(R,ALLYEAR,ALLYEAR,COSTAGG,CUR {self.env.swd})	Cumulative regional cost

*-----------------------------------------------------------------------------
* Storage variables
*-----------------------------------------------------------------------------
  {self.env.var}_SIN(R,ALLYEAR,ALLYEAR,P,C,S {self.env.swd})  		Input flow into storage
  {self.env.var}_SOUT(R,ALLYEAR,ALLYEAR,P,C,S {self.env.swd}) 		Output flow from storage

*-----------------------------------------------------------------------------
* Additional features
*-----------------------------------------------------------------------------
  {self.env.var}_BLND(R,ALLYEAR,COM,COM {self.env.swd})      		Refinery blending
  {self.env.var}_DAM(R,T,C,BD,J {self.env.swd})              		Damage variables
  {self.env.var}_RCAP(R,ALLYEAR,LL,P {self.env.swd})        		New retirements
  {self.env.var}_SCAP(R,ALLYEAR,LL,P {self.env.swd})        		Cumulative retirements
  {self.env.var}_UPS(R,ALLYEAR,ALLYEAR,P,S,L {self.env.swd}) 		Start-ups
  {self.env.var}_UPT(R,ALLYEAR,ALLYEAR,P,S,UPT{self.env.swd})		Start-ups by type
  {self.env.var}_UDP(R,ALLYEAR,ALLYEAR,P,S,L {self.env.swd}) 		Unit dispatching
  {self.env.var}_RLD(R,T,S,ITEM {self.env.swd})     		 	Residual loads

*=============================================================================*
* Objective Function Components
*   - investment cost + tax/sub + decommissioning in INV
*   - fixed O&M + fixed tax/sub in FIX
*   - variable O&M + commodity direct costs
*   - salvage
*=============================================================================*
  {self.env.var}_OBJ(R,OBV,CUR {self.env.swd})    	"Objective costs INV,SAL,FIX,VAR,DAM"
  {self.env.var}_OBJELS(R,BD,CUR {self.env.swd})  	"Change in Consumer surplus"
  VAS_UPDEV(ALLSOW)             	"Upside deviation of OBJ"


 VARIABLES
*=============================================================================*
* Objective Function Variables
*   - total discounted system cost
*=============================================================================*

   OBJz
   VAS_EXPOBJ 				Expected value of total OBJ

*-----------------------------------------------------------------------------
* Slack variables of user-constraints
*-----------------------------------------------------------------------------
  {self.env.var}_UC(UC_N {self.env.swd})			Slacks for UC constraints
  {self.env.var}_UCR(UC_N,R {self.env.swd})		Slacks for UCR constraints
  {self.env.var}_UCT(UC_N,T {self.env.swd})		Slacks for UCT constraints
  {self.env.var}_UCRT(UC_N,R,T {self.env.swd})		Slacks for UCRT constraints
  {self.env.var}_UCTS(UC_N,T,S {self.env.swd})		Slacks for UCTS constraints
  {self.env.var}_UCRTS(UC_N,R,T,S {self.env.swd})		Slacks for UCRTS constraints
  ;
""",
        )
        if "VNRET" in self.tc.container.listSymbols():
            self.include(PrepretDsc(self.tc, self.env, arg1="DECL"))
        if self.tc.defined("PRC_REACT"):
            self.include(PowerfloVda(self.tc, self.env, arg1="DECL"))
        if self.tc.defined("VAR_STS"):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"PARAMETER VAR_STS(R,YEAR,T,P,S,L) //;",
            )
