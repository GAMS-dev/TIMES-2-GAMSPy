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

from gamspy import Alias, Equation, Set

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

        eq: str = self.env.eq
        swtd: tuple[Alias | Set, ...] | tuple[()] = self.env.swtd_GP

        r, p, s, c, year, spe, allsow, ie, allreg = (
            g.r,
            g.p,
            g.s,
            g.c,
            g.year,
            g.spe,
            g.allsow,
            g.ie,
            g.allreg,
        )
        ble, allyear = g.Ble, g.allyear

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
   {eq}_OBJELS(R,BD,CUR {self.env.swd})    'Costs of elastic demands'
   {eq}_OBJFIX(R,CUR {self.env.swd})       'Fixed Costs'
   {eq}_OBJINV(R,CUR {self.env.swd}) 		'Investment component'
   {eq}_OBJSALV(R,CUR {self.env.swd}) 		'Salvage'
   {eq}_OBJVAR(R,CUR {self.env.swd}) 		'Variable operating costs'
   {eq}_OBJDAM(R,CUR {self.env.swd}) 		'Damage costs'
""",
            )

        # *-----------------------------------------------------------------------------
        # * Core Equations
        # *-----------------------------------------------------------------------------

        # Relationship between process activity & individual primary commodity flows
        g.set_equation(
            f"{eq}_ACTFLO",
            Equation(
                m,
                name=f"{eq}_ACTFLO",
                domain=[r, allyear, allyear, p, s, *swtd],
                description="Process Activity/Primary Commodity Flows",
            ),
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------
* Core Equations
  EQUATIONS
*-----------------------------------------------------------------------------
* Bound on activity
   {eq}G_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=G=)' //
   {eq}E_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=E=)' //
   {eq}L_ACTBND(R,ALLYEAR,P,S {self.env.swtd}) 			'Process activity Bound in a Period (=L=)' //
""",
        )

        # Bound on commodities
        g.set_equation(
            name=f"{eq}G_BNDNET",
            eq=Equation(
                m,
                name=f"{eq}G_BNDNET",
                domain=[r, allyear, c, s, *swtd],
                description="Net bound on a commodity (=G=)",
            ),
        )
        g.set_equation(
            name=f"{eq}E_BNDNET",
            eq=Equation(
                m,
                name=f"{eq}E_BNDNET",
                domain=[r, allyear, c, s, *swtd],
                description="Net bound on a commodity (=E=)",
            ),
        )
        g.set_equation(
            name=f"{eq}L_BNDNET",
            eq=Equation(
                m,
                name=f"{eq}L_BNDNET",
                domain=[r, allyear, c, s, *swtd],
                description="Net bound on a commodity (=L=)",
            ),
        )

        g.set_equation(
            name=f"{eq}G_BNDPRD",
            eq=Equation(
                m,
                name=f"{eq}G_BNDPRD",
                domain=[r, allyear, c, s, *swtd],
                description="Production bound on a commodity (=G=)",
            ),
        )
        g.set_equation(
            name=f"{eq}E_BNDPRD",
            eq=Equation(
                m,
                name=f"{eq}E_BNDPRD",
                domain=[r, allyear, c, s, *swtd],
                description="Production bound on a commodity (=E=)",
            ),
        )
        g.set_equation(
            name=f"{eq}L_BNDPRD",
            eq=Equation(
                m,
                name=f"{eq}L_BNDPRD",
                domain=[r, allyear, c, s, *swtd],
                description="Production bound on a commodity (=L=)",
            ),
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQUATIONS
* Utilization of capacity, or the relationship between process capacity and activity
   {eq}L_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=L=)'
   {eq}E_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=E=)'
   {eq}G_CAPACT(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd}) 		'Capacity Utilzation (=G=)'

* Basic commodity balance equations (by type) ensuring that production >=/= consumption
    {eq}G_COMBAL(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Balance (=G=)' //
    {eq}E_COMBAL(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Balance (=E=)' //
    {eq}E_COMPRD(R,ALLYEAR,C,S {self.env.swtd}) 			'Commodity Production (=E=)'
    {eq}L_COMCES(R,ALLYEAR,C,C,S{self.env.swtd})     		'CES substitution steps (=L=)'
""",
        )

        g.set_equation(
            f"{eq}G_CPT",
            Equation(
                m,
                name=f"{eq}G_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_CPT",
            Equation(
                m,
                name=f"{eq}E_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_CPT",
            Equation(
                m,
                name=f"{eq}L_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=L=)",
            ),
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQUATIONS
* Cumulative constraints
    {eq}_CUMNET(R,C,ALLYEAR,ALLYEAR {self.env.swd}) 		'Cummulative Net Commodity Limit (=E=)'
    {eq}_CUMPRD(R,C,ALLYEAR,ALLYEAR {self.env.swd}) 		'Cummulative Commodity Production Limit (=E=)'
    {eq}_CUMFLO(R,P,C,ALLYEAR,LL {self.env.swd})    		'Cummulative Commodity Flow Limit (=E=)'

* Bound on the fraction of a flow within a time slice
    {eq}G_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=G=)'
    {eq}E_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=E=)'
    {eq}L_FLOFR(R,T,P,C,S,L {self.env.swtd})			'Flow fraction (=L=)'

* Bound on the total flow
    {eq}G_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=G=)'
    {eq}E_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=E=)'
    {eq}L_FLOBND(R,T,P,CG,S {self.env.swtd}) 			'Flow bound (=L=)'

* Market share equation allocating commodity percentages of a group
    {eq}G_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=G=)'
    {eq}E_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=E=)'
    {eq}L_INSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Input Group Share (=L=)'

* Inter-period storage equation
    {eq}_STGIPS(R,ALLYEAR,ALLYEAR,P,ITEM {self.env.swtd}) 	'Inter-period storage equation'
    {eq}_STGAUX(R,ALLYEAR,ALLYEAR,P,C,S {self.env.swtd}) 	'Storage auxiliary flows'

* Inter-regional exchange balance
    {eq}_IRE(R,ALLYEAR,P,C,IE,S {self.env.swtd}) 		'Inter-regional Exchange Process Balance (=E=)'

* Bound on inter-regional exchange of a commodity
""",
        )
        g.set_equation(
            name=f"{eq}G_IREBND",
            eq=Equation(
                m,
                name=f"{eq}G_IREBND",
                domain=[r, allyear, c, s, allreg, ie, *swtd],
                description="Limit on Inter-regional Exchange (=G=)",
            ),
        )
        g.set_equation(
            name=f"{eq}E_IREBND",
            eq=Equation(
                m,
                name=f"{eq}E_IREBND",
                domain=[r, allyear, c, s, allreg, ie, *swtd],
                description="Limit on Inter-regional Exchange (=E=)",
            ),
        )
        g.set_equation(
            name=f"{eq}L_IREBND",
            eq=Equation(
                m,
                name=f"{eq}L_IREBND",
                domain=[r, allyear, c, s, allreg, ie, *swtd],
                description="Limit on Inter-regional Exchange (=L=)",
            ),
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQUATIONS
* Bound on total exchange of a commodity to/from all regions
    {eq}G_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=G=)'
    {eq}E_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=E=)'
    {eq}L_XBND(ALL_REG,ALLYEAR,C,S,IE {self.env.swtd}) 		'Limit on Total Exchange (=L=)'

* Product share equation allocating commodity percentages of a group
    {eq}G_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=G=)'
    {eq}E_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=E=)'
    {eq}L_OUTSHR(R,ALLYEAR,ALLYEAR,P,C,CG,S {self.env.swtd}) 	'Commodity Output Group Share (=L=)'

* Process market-share equation of total commodity production
    {eq}G_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=G=)' //
    {eq}E_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=E=)' //
    {eq}L_FLOMRK(R,ALLYEAR,ITEM,C,S {self.env.swtd}) 		'Process market-share (=L=)' //

* Peaking Equation
    {eq}_PEAK(R,ALLYEAR,COM_GRP,S {self.env.swtd}) 		'Commodity Peaking constraint (=G=)'

* Commodity-to-commodity transformation
    {eq}_PTRANS(R,ALLYEAR,ALLYEAR,P,CG,CG,S {self.env.swtd}) 	'Commodity-to-Commodity Transform (=E=)'

* Time-slice storage equation
    {eq}_STGTSS(R,ALLYEAR,ALLYEAR,P,S {self.env.swtd})		'Time-slice storage equation'
    {eq}_STSBAL(R,ALLYEAR,ALLYEAR,P,TSL,S,L{self.env.swtd})   	'Time-slice storage balancer'
    EQ_STSLEV(R,ALLYEAR,ALLYEAR,P,TSLVL,S,ALLSOW)    	'Time-slice storage levelizer'

* Bound on storage flow
    {eq}G_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=G=)'
    {eq}E_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=E=)'
    {eq}L_STGIN(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on input flow of storage (=L=)'
    {eq}G_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=G=)'
    {eq}E_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=E=)'
    {eq}L_STGOUT(R,ALLYEAR,P,C,S {self.env.swtd}) 		'Bound on output flow of storage (=L=)'

* Retirements
    {eq}_CUMRET(R,ALLYEAR,ALLYEAR,P{self.env.swtd}) 		'Cumulative retirements'
    {eq}L_REFIT(R,ALLYEAR,ALLYEAR,P,L{self.env.swtd})	 	'Retrofit/life-extension (=L=)'
    {eq}L_SCAP(R,ALLYEAR,P,IPS{self.env.swd})    		'Salvage capacity (=L=)'

* Cost bounds
    {eq}_BNDCST(REG,ALLYEAR,T,ALLYEAR,COSTCAT,CUR {self.env.swd}) 'Bound on cumulative costs'

* User-constraints
    {eq}E_UC(UC_N {self.env.swd}) 		'User-constraints (=E=)'
    {eq}E_UCR(R,UC_N {self.env.swd}) 		'User-constraints (=E=)'
    {eq}E_UCT(UC_N,T {self.env.swtd}) 		'User-constraints (=E=)'
    {eq}E_UCRT(R,T,UC_N {self.env.swtd}) 	'User-constraints (=E=)'
    {eq}E_UCTS(UC_N,T,S {self.env.swtd}) 	'User-constraints (=E=)'
    {eq}E_UCRS(R,T,UC_N,TSL,S {self.env.swtd})	'User-constraints (=E=)'
    {eq}E_UCRTS(R,T,UC_N,S {self.env.swtd}) 	'User-constraints (=E=)'
    {eq}E_UCSU(UC_N,T {self.env.swd}) 		'User-constraints (=E=)'
    {eq}E_UCSUS(UC_N,T,S {self.env.swd}) 	'User-constraints (=E=)'
    {eq}E_UCRSUS(R,T,UC_N,S {self.env.swd}) 	'User-constraints (=E=)'
    {eq}E_UCRSU(R,T,UC_N {self.env.swd}) 	'User-constraints (=E=)'
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
    {eq}_DAMAGE(R,T,C {self.env.swd}) 	'Damages'

* Stochastic extension
    {eq}_ROBJ(R{self.env.swd})   	'Deterministic objective by region and SOW'
    {eq}_SOBJ(LIM{self.env.swd}) 	'Deterministic objective by SOW'
    EQ_EXPOBJ(ALLSOW) 		'Expected value of total system cost'
    EQ_UPDEV(ALLSOW) 		'Upper absolute deviation'
;
""",
        )
