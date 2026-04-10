# eqobjinv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJINV the objective functions on investments
# *   - Investment Costs
# *   - Investmnet Tax/Subsidies
# *   - Decommissioning
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Note that V=T in OBJ.DOC, but in the code V is assocated with the vintage year,
# *    that is the year of investment as distinguished from T = the current MILESTONYR
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *  - combining all the INVs into a single equation at the moment
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.coef_alt_lin import CoefAltLin

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjinvMod(GamsClass):
    """Translation unit for eqobjinv.mod."""

    module_name: str = "eqobjinv_mod"
    gams_source: str = "eqobjinv.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        # Discounting shift is zero unless the user says otherwise:
        if not self.env.is_set("discshift"):
            self.env.set_global("discshift", "0")

        # If annual cost should be reported for TLIFE years and not just ELIFE,
        # change INVLIF and DECLIF to TLIFE and DLIFE instead of ELIFE and DELIF
        self.env.set_global("invlif", "ELIFE")
        self.env.set_global("declif", "DELIF")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* For loop controls
  ALIAS(AGE,JOT);
  SCALARS OBJ_C /0/, OBJ_D /0/;
* OBJ coefficient SUM control set with the ALLYEAR indexes in sequence =
*   V - investment vintage year, K - commissioning index, Y - decommissioning index
  SET OBJ_SUMII(R,ALLYEAR,P,AGE,ALLYEAR,AGE)      //;
  SET OBJ_SUMIII(R,ALLYEAR,P,ALLYEAR,YEAR,ALLYEAR)//;
  SET OBJ_YES(REG,ALLYEAR,P)                      //;
  SET OBJ_I2(REG,ALLYEAR,P)                       //;
  SET YKAGE(ALLYEAR,ALLYEAR,AGE)                  //;
  SET KAGE(ALLYEAR,AGE)                           //;
  SET OBJ_SPRED(R,ALLYEAR,P,AGE)                  //;
  SET INVSTEP(ALLYEAR,AGE,ALLYEAR,AGE)            //;
  SET INVSPRED(ALLYEAR,AGE,ALLYEAR,ALLYEAR)       //;
  PARAMETER OBJ_PASTI(REG,ALLYEAR,P,CUR)          //;
  PARAMETER SALV_INV(REG,ALLYEAR,PRC,ALLYEAR)     //;
  PARAMETER COR_SALVI(REG,ALLYEAR,PRC,CUR)        //;
  PARAMETER COR_SALVD(REG,ALLYEAR,PRC,CUR)        //;
  PARAMETER OBJ_DIVI(REG,ALLYEAR,PRC)             //;
  PARAMETER OBJ_DIVIII(REG,ALLYEAR,PRC)           //;
  SET OBJ_IDC(R,ALLYEAR,P,LIFE,ALLYEAR,AGE);
  PARAMETER OBJ_IAD(R,CUR);
""",
        )

        self.tc.enqueue(
            self.exec1,
            etl_yes=(self.env.etl.upper() == "YES"),
            invlif=self.env.invlif,
            discshift=self.env.discshift,
        )

        self.env.set_scoped("zhalf", "CEIL(Z/2-.5)")
        self.env.set_scoped("istep", "IPD(T)")
        if self.env.ctst != "":
            self.env.set_scoped("zhalf", "FLOOR(ROUND(Z)/2)")
            self.env.set_scoped("istep", "MIN(IPD(T),ROUND(Z))")

        self.tc.enqueue(self.exec2)

        if self.env.validate == "YES":
            self.tc.enqueue(self._label_m2t)
        else:
            self.tc.enqueue(self.exec3)

        self.tc.enqueue(self._label_cont)
        # *===============================================================================
        # * Case I/II.1.b: Investment/Tax&Sub ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *   Note - no PASTINV as TLIFE always >= D(t) which = 1
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * build repeated investment blocks until end of lifetime
        # *------------------------------------------------------------------------------
        if self.env.validate == "YES":
            self.tc.enqueue(self._label_m2t_2)
        else:
            self.tc.enqueue(
                self.exec4,
                ctst=self.env.ctst,
                zhalf=self.env.zhalf,
                istep=self.env.istep,
            )
        self.tc.enqueue(self._label_cont_2)
        if self.env.ctst != "":
            self.include(
                CoefAltLin(
                    self.tc,
                    self.env,
                    arg1="INV",
                )
            )
        self.tc.enqueue(self._label_cont_2b)
        if self.env.ctst == "":
            self.tc.enqueue(
                self.exec5,
                validate_yes=(self.env.validate == "YES"),
                ctst=self.env.ctst,
            )
        self.tc.enqueue(self._label_clrs)
        # $LABEL EQUA %2
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*===============================================================================
* Generate Investment equation summing over all active indexes by region and currency
*===============================================================================
    {self.env.eq}_OBJINV(RDCUR(R,CUR) {self.env.sow}) ..

*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------

    SUM(OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT)$OBJ_ICUR(R,T,P,CUR), {self.env.capjd}
      SUM(INVSPRED(K_EOH,JOT,Y,K), OBJ_DISC(R,K,CUR) *
        (OBJ_ICOST(R,K,P,CUR) + OBJ_ITAX(R,K,P,CUR) - OBJ_ISUB(R,K,P,CUR))) *
      COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) * {self.env.vart}_NCAP(R,T,P {
                self.env.sws
            })
{
                rf"+ SUM(G_RCUR(R,CUR),{self.env.vart}_IC(R,T,P {self.env.sws})*SUM(INVSPRED(K_EOH,JOT,Y,K),OBJ_DISC(R,K,CUR))*COR_SALVI(R,T,P,CUR)/OBJ_DIVI(R,T,P))$SEG(R,P)"
                if self.env.etl == "YES"
                else ""
            }
       )
       +

{
                (
                    rf'''
    SUM((OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT),SW_TSW(SOW,T,WW))$OBJ_SIC(R,T,P,WW), {self.env.capjd}
      SUM(INVSPRED(K_EOH,JOT,Y,K), OBJ_DISC(R,K,CUR) * OBJ_ICOST(R,K,P,CUR) * (1-SALV_INV(R,T,P,Y))) *
      OBJ_SIC(R,T,P,WW) * COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) * {self.env.var}_NCAP(R,T,P {self.env.swd})) +
'''
                )
                if self.env.stages.upper() == "YES"
                else ""
            }

* PASTI charge
    SUM(OBJ_SUMII(R,PASTYEAR(V),P,LIFE,K_EOH,JOT)$OBJ_PASTI(R,V,P,CUR), {self.env.capjd}
      SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_DISC(R,K,CUR) *
        (OBJ_ICOST(R,K,P,CUR) + OBJ_ITAX(R,K,P,CUR) - OBJ_ISUB(R,K,P,CUR))) *
      OBJ_PASTI(R,V,P,CUR) * COR_SALVI(R,V,P,CUR) / OBJ_DIVI(R,V,P))

       + OBJ_IAD(R,CUR) +

*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------

    SUM(OBJ_SUMIII(R,V,P,LL,K,Y)$OBJ_DCOST(R,V,P,CUR),
      OBJ_DISC(R,Y,CUR) * COR_SALVD(R,V,P,CUR) * OBJ_DCOST(R,K,P,CUR) *
      ({self.env.varv}_NCAP(R,V,P {
                self.env.sws
            })$MILESTONYR(V) + OBJ_PASTI(R,V,P,CUR)$PASTYEAR(V)) / OBJ_DIVIII(R,V,P))

    =E=

     SUM(OBV,SUM_OBJ('OBJINV',OBV)*{self.env.var}_OBJ(R,OBV,CUR {self.env.sow}));
""",
        )

    def exec1(
        self: "EqobjinvMod",
        etl_yes: bool,
        invlif: str,
        discshift: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*===============================================================================
* Hold on to those RTPs for which some investment related cost is provided
*===============================================================================
* Investment
  RTP(R,PASTMILE,P)$(NCAP_PASTI(R,PASTMILE,P)=0) = NO;
  OBJ_ICUR(RTP(R,V,P),CUR)$(OBJ_ICOST(R,V,P,CUR) + OBJ_ISUB(R,V,P,CUR) + OBJ_ITAX(R,V,P,CUR)) = YES;
* if ETL technology then going to do it as well
{"OBJ_ICUR(RTP(R,V,TEG),CUR)$G_RCUR(R,CUR) = YES;" if etl_yes else ""}
* Decommissioning
  OBJ_ICUR(RTP(R,V,P),CUR)$OBJ_DCOST(R,V,P,CUR) = YES;
  LOOP(CUR,OBJ_SUMS3(RTP(R,V,P))$OBJ_DCOST(R,V,P,CUR) = YES);
  LOOP((RTP,COM)$NCAP_OCOM(RTP,COM),OBJ_SUMS3(RTP) = YES);
* Currency independent OBJ_YES
  OBJ_ICUR(RTP_OFF,CUR)$(NOT NCAP_PASTI(RTP_OFF)) = NO;
  OBJ_ICUR(R,LL,P,CUR)$(NOT RDCUR(R,CUR)) = NO;
  OPTION OBJ_YES < OBJ_ICUR; OBJ_YES(OBJ_SUMS3) = YES;

* Correct small TLIFE and DLIFE values, because rounded values are used as divisors
  NCAP_TLIFE(OBJ_YES(R,V,P))$(ROUND(NCAP_TLIFE(R,V,P)) LE 0) = 1;
  NCAP_ELIFE(OBJ_YES(R,V,P))$(ROUND(NCAP_ELIFE(R,V,P)) LE 0) = 1;
  NCAP_DLIFE(OBJ_SUMS3(R,V,P))$(ROUND(NCAP_DLIFE(R,V,P)) LE 0) = 1;
  NCAP_DELIF(OBJ_SUMS3(R,V,P)) = MAX(1,NCAP_DELIF(R,V,P));
* Classify processes into I1 / I2 Cases
  OBJ_I2(RTP)$NCAP_ILED(RTP) = YES;
  LOOP(SAMEAS(LIFE,'1'),OBJ_SPRED(OBJ_YES(R,V,P),LIFE+MAX(0,MIN(CARD(AGE),NCAP_{invlif}(R,V,P))-1))=YES);
*------------------------------------------------------------------------------
* COR_SALVI can be used to take into account technology-specific discount rate
* Take also into account a user-defined discounting shift (0/0.5/1 years):
  COR_SALVI(OBJ_ICUR(R,V,P,CUR))=(((((1+NCAP_DRATE(R,V,P))/(1+OBJ_RFR(R,V,CUR)))**{discshift})*
                                   ((1-1/(1+NCAP_DRATE(R,V,P)))*(1-(1+OBJ_RFR(R,V,CUR))**(-NCAP_ELIFE(R,V,P))))/
                                   ((1-1/(1+OBJ_RFR(R,V,CUR)))*(1-(1+NCAP_DRATE(R,V,P))**(-NCAP_ELIFE(R,V,P))))
                                -1)$(NCAP_DRATE(R,V,P) GT 0) + 1)*(1+G_DRATE(R,V,CUR))**{discshift};
  COR_SALVI(OBJ_ICUR(OBJ_I2(R,V,P),CUR)) = COR_SALVI(R,V,P,CUR) / ((1+G_DRATE(R,V,CUR))**{discshift});
* OBJ_CRF/OBJ_CRFD must now be based on G_DRATE because we use COR_SALVI and COR_SALVD for the correction
  OBJ_CRF(OBJ_ICUR(R,V,P,CUR)) = COR_SALVI(R,V,P,CUR) * (1-(1/(1+G_DRATE(R,V,CUR)))) / (1-(1+G_DRATE(R,V,CUR))**(-ROUND(NCAP_{invlif}(R,V,P))));
*------------------------------------------------------------------------------
* OBJ_PASTI is the correction for past investments (similar to SALV_INV fraction)
  OBJ_PASTI(OBJ_ICUR(RTP(R,PASTYEAR(V),P),CUR)) = NCAP_PASTI(R,V,P) *
            MAX(0,MIN(1,(((1+G_DRATE(R,V,CUR))**(YEARVAL(V)+ROUND(NCAP_ILED(R,V,P))-MINYR+NCAP_{invlif}(R,V,P))-1) /
                         ((1+G_DRATE(R,V,CUR))**NCAP_{invlif}(R,V,P)-1))));
*------------------------------------------------------------------------------
* Operating years for all technical lifetimes
  Z=SMAX((RTP(R,PYR_S(V),P),T)$PRC_RESID(R,T,P),E(T))-MIYR_V1+2;
  MAXLIFE = MAX(SMAX(T,2*D(T)),Z,CEIL(MAXLIFE));
  OPYEAR(LIFE,AGE)$((ORD(AGE) LE ORD(LIFE))$(ORD(LIFE) LE MAXLIFE)) = YES;
*--------------------------------------------------------------------------------------
""",
        )

    def exec2(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*===============================================================================
* Case 1.a: ILEDt <= ILEDmin,t and TLIFEt + ILEDt >= D(t)
*===============================================================================
    OBJ_1A(RTP(R,V,P))$((NOT OBJ_I2(R,V,P))$(COEF_RPTI(R,V,P) LT 1.01)) = YES;
*------------------------------------------------------------------------------
* build trapazoid covering year and number of payment blocks for a process
*------------------------------------------------------------------------------
* - K is EACHYEAR
*     beginning from the
*       MAX(period length before the middle year of the current (investment)
*           period, or the current year - the economic lifetime + 1)
*     until the
*       MIN(middle year of the current (investment) period - 1, or the year
*           calculating)
""",
        )

    def _label_m2t(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Y is investment year, V is cost basis year
    OBJ_SUMII(OBJ_SPRED(OBJ_1A(R,V,P),LIFE),Y,'1')$(YEARVAL(Y) = B(V)) = YES;
""",
        )

    def exec3(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Set period parameters for Case 1a:
  FIL2(V) = (IPD(V)-1)$T(V);
  MY_ARRAY(V) = B(V)-YEARVAL(V) + (M(V)-B(V)-FIL2(V))$T(V);
  LOOP(SAMEAS(AGE,'1'),
* K is both investment year and cost/commissioning year
    OBJ_SUMII(OBJ_SPRED(OBJ_1A(R,V(LL),P),LIFE),K(LL+MY_ARRAY(LL)),AGE+FIL2(V)) = YES;
  );
""",
        )

    def _label_cont(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
*===============================================================================
* Case 1.b: ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
*   Note - no PASTINV as TLIFE always >= D(t) which = 1
*===============================================================================
    OBJ_1B(RTP(R,T,P))$((NOT OBJ_I2(R,T,P))$(NOT OBJ_1A(R,T,P))) = YES;
""",
        )

    def _label_m2t_2(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  LOOP(OBJ_SPRED(OBJ_1B(R,T(LL),P),LIFE),
     Z = NCAP_TLIFE(R,T,P);
     FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
        F = B(T) + ROUND((OBJ_C-1)*Z) - YEARVAL(T);
* Y is investment year, T is cost basis year
        OBJ_SUMII(R,T,P,LIFE,Y(LL+F),'1') = YES);
   );
""",
        )

    def exec4(
        self: "EqobjinvMod",
        ctst: str,
        zhalf: str,
        istep: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 LOOP(SAMEAS(AGE,'1'),
  LOOP(OBJ_SPRED(OBJ_1B(R,T(LL),P),LIFE),
    Z = NCAP_TLIFE(R,T,P);
* Slightly different handling according to objective formulation
    IF((ROUND(Z)-IPD(T){ctst}) LE 0,
     F = B(T) - {zhalf} - YEARVAL(T);
     Z = ROUND(COEF_RPTI(R,T,P)*Z)-1;
* LL+F is both first investment year and first cost/commissioning year
     OBJ_SUMII(R,T,P,LIFE,K(LL+F),AGE+Z) = YES;
    ELSE CNT = {istep}; F = B(T)-YEARVAL(T)-FLOOR(CNT/2); CNT = CNT-1;
     FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
       OBJ_SUMII(R,T,P,LIFE,K(LL+F),AGE+CNT) = YES; F = F+Z));
     );
 );
""",
        )

    def _label_cont_2(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
*===============================================================================
* Case 2.a: ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
*===============================================================================
    OBJ_2A(OBJ_I2(R,V,P))$(COEF_RPTI(R,V,P) LE 1) = YES;
*===============================================================================
* Case I/II.2.a: Investment/Tax&Sub ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
*===============================================================================
*------------------------------------------------------------------------------
* build trapazoid covering year and number of payment blocks for a process
* - K is EACHYEAR
*    for MILESTONYR or PASTYEAR
*      beginning from the
*        MAX(beginning of the period, or the current year - the economic lifetime + 1)
*      until the
*        MIN(beginning of the period + leadtime - 1, or the year calculating)
*------------------------------------------------------------------------------
* there is a relevant cost
  LOOP(SAMEAS(AGE,'1'),
   LOOP(OBJ_SPRED(OBJ_2A(R,V(LL),P),LIFE),
     Z = NCAP_ILED(R,V,P); MY_F = B(V)-YEARVAL(V)+Z;
* LL+F is investment year; LL+MY_F is commissioning year (cost basis)
     OBJ_IDC(R,V,P,LIFE,LL+MY_F,AGE+MAX(0,Z-1)) = YES;
  ));
*===============================================================================
* Case 2.b: ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
*   Note - no PASTINV as TLIFE always >= D(t) which = 1
*===============================================================================
    OBJ_2B(OBJ_I2(R,T,P))$(NOT OBJ_2A(R,T,P)) = YES;
*===============================================================================
* Case I/II.2.b: Investment/Tax&Sub ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
*   Note - no PASTINV as TLIFE always >= D(t) which = 1
*===============================================================================
*------------------------------------------------------------------------------
* build repeated investment blocks until end of lifetime
*------------------------------------------------------------------------------
* calculate the contribution in each year, if there is a cost
  LOOP(SAMEAS(AGE,'1'),
   LOOP(OBJ_SPRED(OBJ_2B(R,T(LL),P),LIFE),
      FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
        Z = NCAP_ILED(R,T,P);
        MY_F = ROUND(B(T)+(OBJ_C-1)*NCAP_TLIFE(R,T,P))-YEARVAL(T)+Z;
* LL+F is investment year; LL+MY_F is commissioning year (cost basis)
        OBJ_IDC(R,T,P,LIFE,LL+MY_F,AGE+MAX(0,Z-1)) = YES);
  ));

*===============================================================================
* Calculate Interest During Construction (IDC) for any fractional ILED
* Note: Zero ILED represents half year's interest, consistently
  LOOP(OBJ_ICUR(OBJ_I2(R,V,P),CUR), Z = COEF_ILED(R,V,P);
    IF(Z, OBJ_C=1+G_DRATE(R,V,CUR); MY_F=0; F=0;
*..Interest according to rounded spreads using actual discount rates
    LOOP(OBJ_IDC(R,V,P,LIFE,LL,JOT), CNT=ORD(JOT);
       MY_F=MY_F+SUM((OPYEAR(JOT,AGE),YEAR(LL-ORD(AGE))),OBJ_DISC(R,YEAR,CUR)); F=F+OBJ_DISC(R,LL,CUR));
    MY_F = MY_F/F/CNT-1;
*..Interest according to rounded and accurate spreads using constant discount rate
    F = ((OBJ_C**CNT)-1)/(1-1/OBJ_C)/CNT-1;
    CNT = MAX(0.001,Z);
    Z = ((OBJ_C**CNT)-1)/(1-1/OBJ_C)/CNT-1;
    ELSE F=1); OBJ_DIVI(R,V,P) = 1/(1+Z*MY_F/F));
* Add spread header tuples
  OBJ_SUMII(R,V,P,LIFE,LL,JOT+(1-ORD(JOT)))$OBJ_IDC(R,V,P,LIFE,LL,JOT) = YES;
  OPTION CLEAR=OBJ_IDC;

*===============================================================================
* Generate the Investment spreads
*===============================================================================
  OPTION KAGE < OBJ_SUMII;
  INVSTEP(KAGE(LL,JOT),LL+(ORD(AGE)-1),AGE+(ORD(JOT)-ORD(AGE)))$OPYEAR(JOT,AGE) = YES;
""",
        )

    def _label_cont_2b(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
*===============================================================================
* Case III.1.a-b, III.2.a-b: Decommissioning
*===============================================================================
  OPTION CLEAR=UNCD7;
* Collect header tuples for decommissioning spreads
  UNCD7(OBJ_SUMS3(R,V,P),LIFE+(NCAP_DLIFE(R,V,P)-ORD(LIFE)),LL--(ORD(LL)$OBJ_I2(R,V,P)),LL,JOT)$OBJ_SUMII(R,V,P,LIFE,LL,JOT) = YES;

* Generate the Decommissioning spreads
  OPTION CLEAR = YKAGE;
  LOOP(UNCD7(R,V,P,LIFE,LASTLL(LL),K,JOT),YKAGE(LL,K,LIFE) = YES);
  LOOP(YKAGE(YEAR,K(LL),JOT),INVSPRED(YEAR,AGE+(ORD(JOT)-ORD(AGE)),LL+(ORD(AGE)-1),K)$OPYEAR(JOT,AGE) = YES);
  LOOP(UNCD7(R,V,P,LIFE,YEAR,K_EOH,JOT), F = CEIL(NCAP_TLIFE(R,V,P)+NCAP_DLAG(R,V,P));
* K is commissioning year (cost basis), LL+F is decommissioning year
    IF(LASTLL(YEAR),
         OBJ_SUMIII(R,V,P,K(K_EOH),K,LL+F)$INVSPRED(YEAR,LIFE,LL,K_EOH) = YES;
    ELSE OBJ_SUMIII(R,V,P,LL,      K,LL+F)$INVSPRED(K_EOH,JOT,LL,K) = YES));
  INVSPRED('0',JOT,YEAR,K) = NO;
""",
        )

    def _label_clrs(
        self: "EqobjinvMod",
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  OPTION CLEAR = OBJ_YES, CLEAR = OBJ_SUMS3, CLEAR = YKAGE;
  OPTION CLEAR = INVSTEP, CLEAR = OBJ_SPRED, CLEAR = OBJ_I2;
""",
        )

    def exec5(
        self: "EqobjinvMod",
        validate_yes: bool,
        ctst: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OBJ_DIVI(OBJ_YES(OBJ_1A(R,V,P))) = 1+(IPD(V)-1)$MILESTONYR(V);
  OBJ_DIVI(OBJ_YES(OBJ_1B(R,T,P))) = NCAP_TLIFE(R,T,P);
  IF(ALTOBJ,OBJ_DIVI(OBJ_YES(OBJ_1B(R,T,P)))$((ROUND(NCAP_TLIFE(R,T,P))-IPD(T){ctst}) GT 0) = IPD(T)*MIN(1,NCAP_TLIFE(R,T,P)));
{"OBJ_DIVI(OBJ_YES(R,T,P))$(NOT OBJ_I2(R,T,P)) = 1;" if validate_yes else ""}
* The equation divisors for decommissioning :
  OBJ_DIVIII(OBJ_SUMS3(R,V,P)) = OBJ_DIVI(R,V,P);
  OBJ_DIVIII(OBJ_SUMS3(OBJ_I2(R,V,P))) = ROUND(NCAP_DLIFE(R,V,P));
{"OPTION CLEAR=OBJ_PASTI;" if validate_yes else ""}
""",
        )
