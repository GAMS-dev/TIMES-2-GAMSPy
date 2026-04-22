# equ_ext_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * EQU_EXT.MSA Equation definitions for MACRO Stand-Alone
# *============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.eqobjann_tm import EqobjannTm

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtMsa(GamsClass):
    """Translation unit for equ_ext.msa."""

    # Instance attributes
    module_name: str = "equ_ext_msa"
    gams_source: str = "equ_ext.msa"

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
        # Prepare annualized coefficients and enable adjusted PV factors
        self.include(EqobjannTm(tc=self.tc, env=self.env, arg1="N", arg2="*0"))

        if (self.env.objann + self.env.msa).upper() == "YESMSA":
            self.tc.enqueue(self.exec1)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
EQUATIONS
   EQ_UTIL                  Utility equation - objective function for MKMC
   EQ_CONSO(REG,TP)         Computation of C (economy consumption)
   EQ_PROD_Y(REG,TP)        Computation of Y (economy output)
   EQ_DD(REG,TP,COM)        Demand decoupling
   EQ_MCAP(REG,TP)          Capital - trillion dollars
   EQ_TMC(REG,TP)           Terminal condition  - trillion dollars
   EQ_IVECBND(REG,T)        Bound on the sum of investment and energy costs
   EQ_ESCOST(REG,TP)        Energy system cost
   EQ_TRDBAL(TP,ITEM)       Trade balance
   EQ_CCDM(REG,MDM,YEAR)    Damage from climate change
;
        """,
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*=======================================================================
*  Utility Production Function, the Objective Function
* ======================================================================

 EQ_UTIL.. SUM(MR(R), SUM(T, TM_NWT(R) * TM_PWT(T) * TM_DFACT(R,T) * LOG(VAR_C(R,T))) +
      SUM((TM_DAM(R,L),XTP), TM_NWT(R) * TM_PWT(XTP)*TM_UDF(R,XTP) * LOG(VAR_CDM(R,L,XTP))))

  =E=  VAR_UTIL * MAX(1,LOG(TM_SCALE_UTIL*1000))/1000;

*=======================================================================
*  Consumption Constraint
*=======================================================================

 EQ_CONSO(MR(R),T)..  VAR_Y(R,T)  =E=  VAR_C(R,T) + VAR_INV(R,T) + VAR_EC(R,T) +
                      (SUM(TM_DAM(R,IO),VAR_CDM(R,IO,T)) + VAR_NTX(R,T,'NMR'))$PP(T);


*=======================================================================
*  Production Constraint
*=======================================================================

 EQ_PROD_Y(MR(R),T)..  VAR_Y(R,T) =L=

 (TM_AKL(R) * (VAR_K(R,T) ** (TM_KPVS(R) * TM_RHO(R))) * TM_L(R,T) ** ((1 - TM_KPVS(R)) * TM_RHO(R))

 +  SUM(DEM(R,DM)$TM_DEM(R,T,DM), TM_B(R,DM) * VAR_D(R,T,DM) ** TM_RHO(R))) ** (1 / TM_RHO(R));


*=======================================================================
*  Demand Decoupling  Constraint:
*  The energy service demands D are reduced by the DDF factors
*  while as production function factors increase ECONOMIC OUTPUT
*=======================================================================

  EQ_DD(MR(R),TP,DM) ..

  VAR_DEM(R,TP,DM) =E= ((1/TM_SCALE_NRG) * (TM_AEEIFAC(R,TP,DM) * VAR_D(R,TP,DM) + VAR_SP(R,TP,DM)))$(TM_DEM(R,TP,DM) GT 0);


*=======================================================================
*  Capital Constraint
*=======================================================================

  EQ_MCAP(MR(R),PP(T+1))..

  VAR_K(R,PP)  =L=

  VAR_K(R,T) * TM_TSRV(R,T) + (D(PP)*VAR_INV(R,PP) + D(T)*VAR_INV(R,T)*TM_TSRV(R,T))/2;

*=======================================================================
*  Terminal Condition
*=======================================================================

  EQ_TMC(MR(R),TLAST)..

  VAR_K(R,TLAST) * (TM_GROWV(R,TLAST) + TM_DEPR(R))/100 =L= VAR_INV(R,TLAST);


*=======================================================================
*  Bound on Sum of Investment and Energy
*=======================================================================
  EQ_IVECBND(MR(R),PP(T)) ..

  VAR_INV(R,T) + VAR_EC(R,T)  =L=  TM_Y0(R) * TM_L(R,T) ** TM_IVETOL(R);

*=======================================================================
*  Cost of Energy
*=======================================================================
  EQ_ESCOST(MR(R),PP)..

  TM_QSFA(R,PP) + SUM(DM, TM_QSFB(R,PP,DM)*VAR_DEM(R,PP,DM)**2) + TM_AMP(R,PP)

  =L=

  VAR_EC(R,PP);
*=======================================================================
* Trades and damage
*=======================================================================
  EQ_TRDBAL(PP,TRD)..  SUM(MR(R), VAR_NTX(R,PP,TRD)) =E= 0;

  EQ_CCDM(TM_DAM(MR(R),MDM),XTP)..  VAR_CDM(R,MDM,XTP)  =E=

   ((1-({self.cm_clibox("'DELTA-ATM'", "'ATM'", "XTP")}/TM_CATT(R))**2)**TM_HSX(R,XTP))$L(MDM) +

   SUM(SUPERYR(T(XTP),LL)$XTP(LL),TM_GDPGOAL(MR,T)*TM_XWT(R,LL)*
   (TM_MDTL(R)*{self.cm_clibox("'DELTA-ATM'", "'ATM'", "LL")}/MAX(1,TM_DEFVAL('REFTEMP')) +
    TM_MDTQ(R)*POWER({self.cm_clibox("'DELTA-ATM'", "'ATM'", "LL")}/MAX(1,TM_DEFVAL('REFTEMP')),2)))$IO(MDM);
        """,
        )

    def cm_clibox(self, arg1: str, arg2: str, arg3: str) -> str:
        if self.env.cli.upper() != "YES":
            return "0"

        return f"VAR_CLIBOX({arg1}, {arg2}, {arg3})"

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""COEF_PVT(R,T) $= TM_UDF(R,T); OBJ_PVT(R,T,CUR)$RDCUR(R,CUR) $= TM_UDF(R,T);""",
        )
