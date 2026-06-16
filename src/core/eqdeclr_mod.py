# eqdeclr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQDECLR.MOD declarations for actual equations
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *   - declare all equations so that restarting changed models will work
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation

from core.base_class import GamsClass
from core.eqdeclr_tm import EqdeclrTm

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqdeclrMod(GamsClass):
    """Translation unit for eqdeclr.mod."""

    # Instance attributes
    module_name: str = "eqdeclr_mod"
    gams_source: str = "eqdeclr.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self._sub_modules = {}
        self.arg1 = arg1
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        r, year, spe, allsow = g.r, g.year, g.spe, g.allsow
        ble = g.Ble

        if self.env.macro.upper() == "YES":
            self.include(EqdeclrTm(self.tc, self.env))
        else:
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
*-----------------------------------------------------------------------------
  EQUATIONS
*-----------------------------------------------------------------------------
* Objective Function & Components
*-----------------------------------------------------------------------------
* Overall OBJ linear combination of the regional objs (which are built from rest)
    EQ_OBJ 				'Overall Objective Function'

* OBJ cost components
   {self.env.eq}_OBJELS(R,BD,CUR {self.env.swd})    'Costs of elastic demands'
   {self.env.eq}_OBJFIX(R,CUR {self.env.swd})       'Fixed Costs'
   {self.env.eq}_OBJINV(R,CUR {self.env.swd}) 		'Investment component'
   {self.env.eq}_OBJSALV(R,CUR {self.env.swd}) 		'Salvage'
   {self.env.eq}_OBJVAR(R,CUR {self.env.swd}) 		'Variable operating costs'
   {self.env.eq}_OBJDAM(R,CUR {self.env.swd}) 		'Damage costs'
""",
            )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------
* Core Equations
  EQUATIONS
*-----------------------------------------------------------------------------

* Relationship between process activity & individual primary commodity flows
   {self.env.eq}_ACTFLO(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Process Activity/Primary Commodity Flows'

* Bound on activity
   {self.env.eq}G_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=G=)' //
   {self.env.eq}E_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=E=)' //
   {self.env.eq}L_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=L=)' //

* Bound on commodities
   {self.env.eq}G_BNDNET(R,ALLYEAR,C,S {self.env.swtd}) 			'Net bound on a commodity (=G=)'
   {self.env.eq}E_BNDNET(R,ALLYEAR,C,S {self.env.swtd}) 			'Net bound on a commodity (=E=)'
   {self.env.eq}L_BNDNET(R,ALLYEAR,C,S {self.env.swtd}) 			'Net bound on a commodity (=L=)'
   {self.env.eq}G_BNDPRD(R,ALLYEAR,C,S {self.env.swtd}) 			'Production bound on a commodity (=G=)'
   {self.env.eq}E_BNDPRD(R,ALLYEAR,C,S {self.env.swtd}) 			'Production bound on a commodity (=E=)'
   {self.env.eq}L_BNDPRD(R,ALLYEAR,C,S {self.env.swtd}) 			'Production bound on a commodity (=L=)'

* Utilization of capacity, or the relationship between process capacity and activity
   {self.env.eq}L_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=L=)'
   {self.env.eq}E_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=E=)'
   {self.env.eq}G_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=G=)'

* Basic commodity balance equations (by type) ensuring that production >=/= consumption
    {self.env.eq}G_COMBAL(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Balance (=G=)' //
    {self.env.eq}E_COMBAL(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Balance (=E=)' //
    {self.env.eq}E_COMPRD(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Production (=E=)'
    {self.env.eq}L_COMCES(R,ALLYEAR,C,C,S{self.env.swtd})     		'CES substitution steps (=L=)'

* Transfer of installed capacity between periods
    {self.env.eq}G_CPT(R,ALLYEAR,P {self.env.swtd})                   	'Capacity Transfer (=G=)'
    {self.env.eq}E_CPT(R,ALLYEAR,P {self.env.swtd})                   	'Capacity Transfer (=E=)'
    {self.env.eq}L_CPT(R,ALLYEAR,P {self.env.swtd})                   	'Capacity Transfer (=L=)'

* Cumulative constraints
    {self.env.eq}_CUMNET(R,C,ALLYEAR,ALLYEAR {self.env.swd}) 		'Cummulative Net Commodity Limit (=E=)'
    {self.env.eq}_CUMPRD(R,C,ALLYEAR,ALLYEAR {self.env.swd}) 		'Cummulative Commodity Production Limit (=E=)'
    {self.env.eq}_CUMFLO(R,P,C,ALLYEAR,LL {self.env.swd})    		'Cummulative Commodity Flow Limit (=E=)'

* Bound on the fraction of a flow within a time slice
    {self.env.eq}G_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=G=)'
    {self.env.eq}E_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=E=)'
    {self.env.eq}L_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=L=)'

* Bound on the total flow
    {self.env.eq}G_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=G=)'
    {self.env.eq}E_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=E=)'
    {self.env.eq}L_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=L=)'

* Market share equation allocating commodity percentages of a group
    {self.env.eq}G_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=G=)'
    {self.env.eq}E_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=E=)'
    {self.env.eq}L_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=L=)'

* Inter-period storage equation
    {self.env.eq}_STGIPS(R,ALLYEAR,ALLYEAR,P,ITEM {self.env.swtd}) 	'Inter-period storage equation'
    {self.env.eq}_STGAUX(R,ALLYEAR,ALLYEAR,P,C,S {self.env.swtd}) 	'Storage auxiliary flows'

* Inter-regional exchange balance
    {self.env.eq}_IRE(R,ALLYEAR,P,C,IE,S {self.env.swtd}) 		'Inter-regional Exchange Process Balance (=E=)'

* Bound on inter-regional exchange of a commodity
    {self.env.eq}G_IREBND(R,ALLYEAR,C,S,ALL_REG,IE {self.env.swtd}) 	'Limit on Inter-regional Exchange (=G=)'
    {self.env.eq}E_IREBND(R,ALLYEAR,C,S,ALL_REG,IE {self.env.swtd}) 	'Limit on Inter-regional Exchange (=E=)'
    {self.env.eq}L_IREBND(R,ALLYEAR,C,S,ALL_REG,IE {self.env.swtd}) 	'Limit on Inter-regional Exchange (=L=)'

* Bound on total exchange of a commodity to/from all regions
    {self.env.eq}G_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=G=)'
    {self.env.eq}E_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=E=)'
    {self.env.eq}L_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=L=)'

* Product share equation allocating commodity percentages of a group
    {self.env.eq}G_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=G=)'
    {self.env.eq}E_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=E=)'
    {self.env.eq}L_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=L=)'

* Process market-share equation of total commodity production
    {self.env.eq}G_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=G=)' //
    {self.env.eq}E_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=E=)' //
    {self.env.eq}L_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=L=)' //

* Peaking Equation
    {self.env.eq}_PEAK(R,ALLYEAR,COM_GRP,S {self.env.swtd}) 		'Commodity Peaking constraint (=G=)'

* Commodity-to-commodity transformation
    {self.env.eq}_PTRANS(R,ALLYEAR,ALLYEAR,P,CG,CG,S {self.env.swtd}) 	'Commodity-to-Commodity Transform (=E=)'

* Time-slice storage equation
    {self.env.eq}_STGTSS(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd})		'Time-slice storage equation'
    {self.env.eq}_STSBAL(R,ALLYEAR,ALLYEAR,P,TSL,S,L{self.env.swtd})   	'Time-slice storage balancer'
    EQ_STSLEV(R,ALLYEAR,ALLYEAR,P,TSLVL,S,ALLSOW)    	'Time-slice storage levelizer'

* Bound on storage flow
    {self.env.eq}G_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=G=)'
    {self.env.eq}E_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=E=)'
    {self.env.eq}L_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=L=)'
    {self.env.eq}G_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=G=)'
    {self.env.eq}E_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=E=)'
    {self.env.eq}L_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=L=)'

* Retirements
    {self.env.eq}_CUMRET(R,ALLYEAR,ALLYEAR,P{self.env.swtd}) 		'Cumulative retirements'
    {self.env.eq}L_REFIT(R,ALLYEAR,ALLYEAR,P,L{self.env.swtd})	 	'Retrofit/life-extension (=L=)'
    {self.env.eq}L_SCAP(R,ALLYEAR,P,IPS{self.env.swd})    		'Salvage capacity (=L=)'

* Cost bounds
    {self.env.eq}_BNDCST(REG,ALLYEAR,T,ALLYEAR,COSTCAT,CUR {self.env.swd}) 'Bound on cumulative costs'

* User-constraints
    {self.env.eq}E_UC(UC_N {self.env.swd}) 		'User-constraints (=E=)'
    {self.env.eq}E_UCR(R,UC_N {self.env.swd}) 		'User-constraints (=E=)'
    {self.env.eq}E_UCT(UC_N,T {self.env.swtd}) 		'User-constraints (=E=)'
    {self.env.eq}E_UCRT(R,T,UC_N {self.env.swtd}) 	'User-constraints (=E=)'
    {self.env.eq}E_UCTS(UC_N,T,S {self.env.swtd}) 	'User-constraints (=E=)'
    {self.env.eq}E_UCRS(R,T,UC_N,TSL,S {self.env.swtd})	'User-constraints (=E=)'
    {self.env.eq}E_UCRTS(R,T,UC_N,S {self.env.swtd}) 	'User-constraints (=E=)'
    {self.env.eq}E_UCSU(UC_N,T {self.env.swd}) 		'User-constraints (=E=)'
    {self.env.eq}E_UCSUS(UC_N,T,S {self.env.swd}) 	'User-constraints (=E=)'
    {self.env.eq}E_UCRSUS(R,T,UC_N,S {self.env.swd}) 	'User-constraints (=E=)'
    {self.env.eq}E_UCRSU(R,T,UC_N {self.env.swd}) 	'User-constraints (=E=)'
""",
        )
        if self.env.var_uc != "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
  EQUATIONS
    EQG_UC(UC_N) 			'User-constraints (=G=)'
    EQG_UCR(R,UC_N) 			'User-constraints (=G=)'
    EQG_UCT(UC_N,T) 			'User-constraints (=G=)'
    EQG_UCRT(R,T,UC_N) 			'User-constraints (=G=)'
    EQG_UCTS(UC_N,T,S) 			'User-constraints (=G=)'
    EQG_UCRS(R,T,UC_N,TSL,S) 		'User-constraints (=G=)'
    EQG_UCRTS(R,T,UC_N,S) 		'User-constraints (=G=)'
    EQG_UCSU(UC_N,T) 			'User-constraints (=G=)'
    EQG_UCSUS(UC_N,T,S) 		'User-constraints (=G=)'
    EQG_UCRSUS(R,T,UC_N,S) 		'User-constraints (=G=)'
    EQG_UCRSU(R,T,UC_N) 		'User-constraints (=G=)'

    EQL_UC(UC_N) 			'User-constraints (=L=)'
    EQL_UCR(R,UC_N) 			'User-constraints (=L=)'
    EQL_UCT(UC_N,T) 			'User-constraints (=L=)'
    EQL_UCRT(R,T,UC_N) 			'User-constraints (=L=)'
    EQL_UCTS(UC_N,T,S) 			'User-constraints (=L=)'
    EQL_UCRS(R,T,UC_N,TSL,S) 		'User-constraints (=L=)'
    EQL_UCRTS(R,T,UC_N,S) 		'User-constraints (=L=)'
    EQL_UCSU(UC_N,T) 			'User-constraints (=L=)'
    EQL_UCSUS(UC_N,T,S) 		'User-constraints (=L=)'
    EQL_UCRSUS(R,T,UC_N,S) 		'User-constraints (=L=)'
    EQL_UCRSU(R,T,UC_N) 		'User-constraints (=L=)'
""",
            )

        # *GG* V07_2 BLENDing equation
        g.eql_blnd = Equation(
            m,
            name="EQL_BLND",
            domain=[r, year, ble, spe, allsow],
            description="Blending (=L=)",
        )
        g.eqg_blnd = Equation(
            m,
            name="EQG_BLND",
            domain=[r, year, ble, spe, allsow],
            description="Blending (=G=)",
        )
        g.eqe_blnd = Equation(
            m,
            name="EQE_BLND",
            domain=[r, year, ble, spe, allsow],
            description="Blending (=E=)",
        )
        g.eqn_blnd = Equation(
            m,
            name="EQN_BLND",
            domain=[r, year, ble, spe, allsow],
            type="nonbinding",
            description="Blending non-binding",
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQUATIONS
*-----------------------------------------------------------------------------

* Damage Extension
    {self.env.eq}_DAMAGE(R,T,C {self.env.swd}) 	'Damages'

* Stochastic extension
    {self.env.eq}_ROBJ(R{self.env.swd})   	'Deterministic objective by region and SOW'
    {self.env.eq}_SOBJ(LIM{self.env.swd}) 	'Deterministic objective by SOW'
    EQ_EXPOBJ(ALLSOW) 		'Expected value of total system cost'
    EQ_UPDEV(ALLSOW) 		'Upper absolute deviation'
;
""",
        )
