# eqobjfix_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJFIX the objective functions capacity fixed costs
# *   arg1 - mod or v# for the source code to be used
# *   - fixed O&M, including surveillance during decommissioning
# *   - tax
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Note that V=T in OBJ.DOC, but in the code V is assocated with the vintage year,
# *    that is the of investment as distinguished from T = the current MILESTONYR.
# *  - Combining all the Fix into a single equation at the moment
# *  - the test for relevant costs is done on the year of installation, perhaps should be Y-running year
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core import prepret_dsc
from core.coef_alt_lin import CoefAltLin

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjfixMod(GamsClass):
    """Translation unit for eqobjfix.mod."""

    # Instance attributes
    module_name: str = "eqobjfix_mod"
    gams_source: str = "eqobjfix.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        self.declarations()

        self.tc.enqueue(
            self.exec1,
            condition=self.env.validate == "YES",
        )
        self.env.set_scoped("zhalf", "CEIL(Z/2-.5)")
        self.env.set_scoped("istep", "IPD(T)")
        if not self.env.ctst == "":
            self.env.set_scoped("istep", "MIN(IPD(T),ROUND(Z))")
            self.env.set_scoped("zhalf", "FLOOR(ROUND(Z)/2)")

        self.tc.enqueue(
            self.exec_loop,
            ctst=self.env.ctst,
            zhalf=self.env.zhalf,
            istep=self.env.istep,
            condition=self.env.validate == "YES",
        )

        # * Commissioning years
        if not self.env.ctst.upper() == "":
            self.include(
                CoefAltLin(
                    self.tc,
                    self.env,
                    arg1="FIX",
                    arg2="*",
                )
            )

        self.tc.enqueue(self.exec2)

        # * Reset OBJ_DIVIV to be the year divisor in the equation
        # * Only single commissioning year B(V)+ILED is taken for PASTMILE
        if not self.env.ctst.upper() == "":
            pass
        else:
            self.tc.enqueue(
                self.exec3,
                ctst=self.env.ctst,
                condition=self.env.validate == "YES",
            )

        assert self.arg2.upper() in {
            "",
            "EXIT",
        }, f"Expected empty string or 'exit', but got '{self.arg2}'"

        if self.arg2.upper() == "EXIT":
            return

        self.define_equation(
            eq=self.env.eq,
            sow=self.env.sow,
            capwd=self.env.capwd,
            varv=self.env.varv,
            sws=self.env.sws,
            vart=self.env.vart,
            var=self.env.var,
            condition1=self.env.validate == "YES",
            condition2=self.tc.defined("VNRET"),
        )

    def declarations(
        self: EqobjfixMod,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* For loop controls
  SET OBJ_FCUR(REG,ALLYEAR,P,CUR)                //;
* OBJ coefficient SUM control set with the 3 ALLYEAR indexes in sequence =
*   Y-running OBJ year, V-variables' investment period, K-cost value counter & index
  SET OBJ_SUMIV(ALLYEAR,R,ALLYEAR,P,AGE,AGE)     //;
  SET OBJ_SUMIVS(R,ALLYEAR,P,ALLYEAR,ALLYEAR)    //;
* Shaping controls
  SET RTP_SHAPE(REG,ALLYEAR,PRC,J,J,J)           //;
* Fixed cost year span divisor
  PARAMETER OBJ_DIVIV(REG,ALLYEAR,PRC)           //;
* Present value factor of technical life
  PARAMETER OBJ_LIFE(ALLYEAR,REG,AGE,AGE,CUR)    //;
""",
        )

    def exec1(
        self: EqobjfixMod,
        condition: bool,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*UR: 09/30/01
* if some relevant cost
  OBJ_FCUR(RTP(R,V,P),CUR)$(OBJ_FOM(R,V,P,CUR)+OBJ_FTX(R,V,P,CUR)+OBJ_FSB(R,V,P,CUR)) = YES;
* Decommissioning
  OBJ_FCUR(RTP(R,V,P),CUR)$OBJ_DLAGC(R,V,P,CUR) = YES;
  OPTION OBJ_YES < OBJ_FCUR;
  OBJ_YES(RTP_OFF(R,T,P))$(NOT NCAP_PASTI(R,T,P)) = NO;

* Set up the rounded lifetimes; round half years down:
 OBJ_DIVIV(OBJ_YES(R,V,P)) = MAX(1,MIN(CARD(AGE),CEIL(NCAP_TLIFE(R,V,P)-0.5)));
 OBJ_DIVIV(OBJ_YES(R,PYR_S(V),P))$PRC_RESID(R,'0',P)=MAX(2,SMAX(T$(PRC_RESID(R,T,P)>0),E(T))-MIYR_V1+2);
*======================================================================================
* Apply SHAPE to OBJ_YES:
*--------------------------------------------------------------------------------------
OPTION CLEAR=RTP_SHAPE;
LOOP(SAMEAS(J,'1'),
 RTP_SHAPE(OBJ_YES(RTP),'1',J+MAX(0,NCAP_FOMX(RTP)-1),J+MAX(0,NCAP_FOMM(RTP)-1))$(NCAP_FOMX(RTP)+NCAP_FOMM(RTP)+NCAP_CPX(RTP)) = YES;
 RTP_SHAPE(OBJ_YES(RTP),'2',J+MAX(0,NCAP_FTAXX(RTP)-1),J+MAX(0,NCAP_FTAXM(RTP)-1))$(NCAP_FTAXX(RTP)+NCAP_FTAXM(RTP)) = YES;
 RTP_SHAPE(OBJ_YES(RTP),'3',J+MAX(0,NCAP_FSUBX(RTP)-1),J+MAX(0,NCAP_FSUBM(RTP)-1))$(NCAP_FSUBX(RTP)+NCAP_FSUBM(RTP)) = YES;
);
 OPTION RTP_ISHPR < RTP_SHAPE;
 RTP_SHAPE(RTP_SHAPE(RTP,J,'1','1'))$(NOT NCAP_CPX(RTP)) = NO;
{"RTP_ISHPR(RTP) = YES;" if condition else ""}
""",
        )

    def exec_loop(
        self: EqobjfixMod,
        ctst: str,
        zhalf: str,
        istep: str,
        condition: bool,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*===============================================================================
* Case IV/V.1.a: Fixed O&M/Tax ILEDt <= ILEDmin,t and TLIFEt + ILEDt >= D(t)
*===============================================================================
 LOOP(SAMEAS(AGE,'1'),
* [AL] 05/08/2003: small further speed-up

{
                (
                    '''
* Set period parameters for Case 1a:
    FIL2(V) = (IPD(V)-1)$T(V);
    MY_ARRAY(V) = B(V)-YEARVAL(V) + (M(V)-B(V)-FIL2(V))$T(V);
* The first commissioning year is LL+MY_ARRAY(LL) and the spread is AGE+FIL2(V)
    OBJ_SUMIV(LL+MY_ARRAY(LL),OBJ_1A(OBJ_YES(R,V(LL),P)),AGE+FIL2(V),AGE+(OBJ_DIVIV(R,V,P)-1)) = YES;

'''
                )
                if not condition
                else (
                    '''
* create square for investment costing if validating MARKAL
    MY_ARRAY(V) = MAX(MIYR_V1,B(V))-YEARVAL(V);
    OBJ_SUMIV(LL+MY_ARRAY(LL),OBJ_1A(OBJ_YES(R,V(LL),P)),AGE+(NCAP_ELIFE(R,V,P)-1),'1') = YES;
'''
                )
            }
     );
*===============================================================================
* Case IV/V.1.b: Fixed O&M/Tax ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
*===============================================================================
* if some relevant cost
 LOOP(SAMEAS(AGE,'1'),
{
                (
                    f'''
   LOOP(OBJ_1B(OBJ_YES(R,T(LL),P)),
      Z = NCAP_TLIFE(R,T,P);
* Slightly different handling according to objective formulation
      IF((ROUND(Z)-IPD(T){ctst}) LE 0, MY_F = OBJ_DIVIV(R,T,P)-1;
        F = B(T) - {zhalf} - YEARVAL(T);
        Z = ROUND(COEF_RPTI(R,T,P)*Z)-1;
* The first commissioning year is LL+F and the spread is AGE+Z
        OBJ_SUMIV(LL+F,R,T,P,AGE+Z,AGE+MY_F) = YES;
      ELSE CNT = {istep}; OBJ_D = CNT-1; MY_F = B(T)-YEARVAL(T)-FLOOR(CNT/2);
        FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
         F = MY_F; MY_F = F+Z; CNT = ROUND(MY_F)-ROUND(F)-1;
         OBJ_SUMIV(LL+F,R,T,P,AGE+OBJ_D,AGE+CNT) = YES));
       );

* create square for investment costing if validating MARKAL
'''
                )
                if not condition
                else (
                    '''
    OBJ_SUMIV(LL+MY_ARRAY(LL),OBJ_1B(OBJ_YES(R,T(LL),P)),AGE+(COEF_RPTI(R,T,P)*NCAP_ELIFE(R,T,P)-1),'1') = YES;
'''
                )
            }
    );
*===============================================================================
* Case IV/V.2.a: Fixed O&M/Tax ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
*===============================================================================
* if some relevant cost
*V05c 981007 - treat PAST == MILE except take cost from decision/capacity installed
  LOOP(SAMEAS(AGE,'1'),
* The commissioning year is B(V)+ILED for both MILESTONYR and PASTMILE, spread is '1'
    OBJ_SUMIV(LL+(B(LL)+NCAP_ILED(R,LL,P)-YEARVAL(LL)),OBJ_YES(OBJ_2A(R,V(LL),P)),'1',AGE+(OBJ_DIVIV(R,LL,P)-1)) = YES;
  );
*-----------------------------------------------------------------------------
* Case IV.2.a: Surveillance ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
*-----------------------------------------------------------------------------
* if some relevant cost
    LOOP((OBJ_2A(R,V(LL),P),CUR)$OBJ_DLAGC(R,V,P,CUR),
      MY_F = B(V) + NCAP_ILED(R,V,P);
      F = ROUND(MY_F + NCAP_TLIFE(R,V,P)); Z = F + NCAP_DLAG(R,V,P); MY_F = MY_F-YEARVAL(V);
      OBJ_SUMIVS(R,V,P,LL+MY_F,Y)$((YEARVAL(Y) >= F) AND (YEARVAL(Y) < Z)) = YES;
    );

*===============================================================================
* Case IV/V.2.b: Fixed O&M/Tax ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
*===============================================================================
* determine the number of repeated investments, if some relevant cost
  LOOP(SAMEAS(AGE,'1'),
    LOOP(OBJ_2B(OBJ_YES(R,T(LL),P)),
      Z = NCAP_TLIFE(R,T,P); MY_F = ROUND(B(T)+NCAP_ILED(R,T,P))-YEARVAL(T);
      FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
* The commissioning year is LL+F and the spread is 1
           F = MY_F; MY_F = F+Z; CNT = ROUND(MY_F)-ROUND(F)-1;
           OBJ_SUMIV(LL+F,R,T,P,'1',AGE+CNT) = YES;
         );
        );
      );
*-----------------------------------------------------------------------------
* Case IV.2.b: Surveillance ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
*-----------------------------------------------------------------------------
* determine the number of repeated investments, if some relevant cost
    LOOP((OBJ_2B(R,T(LL),P),CUR)$OBJ_DLAGC(R,T,P,CUR),
      FOR(OBJ_C = 1 TO COEF_RPTI(R,T,P),
        MY_F = B(T) + NCAP_ILED(R,T,P) + (OBJ_C-1) * NCAP_TLIFE(R,T,P);
        F = ROUND(MY_F + NCAP_TLIFE(R,T,P)); Z = F + NCAP_DLAG(R,T,P); MY_F = MY_F-YEARVAL(T);
        OBJ_SUMIVS(R,T,P,LL+MY_F,Y)$((YEARVAL(Y) >= F) AND (YEARVAL(Y) < Z)) = YES;
         );
    );

*------------------------------------------------------------------------------
* forget about PASTINV charges if not PASTInvestment
*------------------------------------------------------------------------------
    OBJ_SUMIV(OBJ_SUMIV(K_EOH,R,PASTMILE,P,JOT,AGE))$(NOT NCAP_PASTI(R,PASTMILE,P)) = NO;
    OBJ_SUMIVS(OBJ_SUMIVS(R,PASTMILE,P,K,Y))$(NOT NCAP_PASTI(R,PASTMILE,P)) = NO;
*-----------------------------------------------------------------------------*
* precalculation of the PVF sum for the simple case is usually efficient
    LOOP((OBJ_SUMIV(K,R,V,P,JOT,LIFE),RDCUR(R,CUR)),OBJ_LIFE(K,R,JOT,LIFE,CUR) = YES);
    OPTION KAGE <= OBJ_LIFE;
    INVSTEP(KAGE(LL,JOT),LL+(ORD(AGE)-1),AGE+(ORD(JOT)-ORD(AGE)))$OPYEAR(JOT,AGE) = YES;
    LOOP(KAGE(K,JOT),OBJ_LIFE(LL,R,JOT,LIFE,CUR)$INVSTEP(K,JOT,LL,JOT) $= OBJ_LIFE(K,R,JOT,LIFE,CUR));
    OBJ_LIFE(K(LL),R,JOT,LIFE,CUR)$OBJ_LIFE(K,R,JOT,LIFE,CUR) = SUM((OPYEAR(LIFE,AGE),Y_EOH(LL+(ORD(AGE)-1))),OBJ_DISC(R,Y_EOH,CUR));
""",
        )

    def exec2(
        self: EqobjfixMod,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    INVSPRED(KAGE(LL,JOT),K,K)$INVSTEP(LL,JOT,K,JOT) = YES;
""",
        )

    def exec3(
        self: EqobjfixMod,
        ctst: str,
        condtion: bool,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
    OBJ_DIVIV(OBJ_YES(R,PASTMILE,P)) = 1;
    OBJ_DIVIV(OBJ_YES(R,T,P))$(NOT OBJ_1B(R,T,P)) = 1+(IPD(T)-1)$OBJ_1A(R,T,P);
    IF(ALTOBJ, OBJ_DIVIV(OBJ_1B(OBJ_YES(R,T,P)))$((ROUND(NCAP_TLIFE(R,T,P))-IPD(T){ctst}) GT 0) = IPD(T));
{"OBJ_DIVIV(OBJ_YES(R,T,P)) = 1;" if condtion else ""}
*-----------------------------------------------------------------------------*
  OPTION CLEAR=OBJ_YES, CLEAR=YKAGE;
""",
        )

    def define_equation(
        self: EqobjfixMod,
        eq: str,
        sow: str,
        capwd: str,
        varv: str,
        sws: str,
        vart: str,
        var: str,
        condition1: str,
        condition2: bool,
    ):
        include_prepret = prepret_dsc.objfix(capwd=capwd, vart=vart, sws=sws)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*===============================================================================
* Generate Fixed Cost equation summing over all active indexes by region and currency
*===============================================================================
    {eq}_OBJFIX(RDCUR(R,CUR) {sow}) ..

*------------------------------------------------------------------------------
* Cases IV - Fixed O&M including surveillance during decommissioning, V - Taxes
*------------------------------------------------------------------------------
* Fixed O&M Cost and Taxes

      SUM(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE)$(NOT RTP_ISHPR(R,V,P)),
       SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd}
        (OBJ_FOM(R,K,P,CUR)+OBJ_FTX(R,K,P,CUR)-OBJ_FSB(R,K,P,CUR))) *
        ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)) / OBJ_DIVIV(R,V,P)) +

      SUM(OBJ_SUMIV(K_EOH,RTP_ISHPR(R,V,P),JOT,LIFE),
        SUM((INVSPRED(K_EOH,JOT,LL,K),OPYEAR(LIFE,AGE),Y_EOH(LL+(ORD(AGE)-1))),
             OBJ_DISC(R,Y_EOH,CUR) * (1+SUM(PERIODYR(T,Y_EOH),RTP_CPX(R,V,P,T))$NCAP_CPX(R,V,P)) * {capwd}
                (
                   OBJ_FOM(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                   OBJ_FTX(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
                   OBJ_FSB(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
                )

* [UR] 07.10.2003: for validating MARKAL using VAR_CAP instead of VAR_NCAP+NCAP_PASTI, since it is possible
*                  in MARKAL to decommission capacity of demand devices (DMD)
{f"                       *((SUM(PERIODYR(T(V),Y_EOH),{vart}_CAP(R,T,P {sws})))$(OBJ_1A(R,V,P)+OBJ_1B(R,V,P))+" if condition1 else ""}
{f"                        ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V))$(OBJ_2A(R,V,P)+OBJ_2B(R,V,P)))" if condition1 else ""}

           )
{f"            * ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)) / OBJ_DIVIV(R,V,P)" if not condition1 else ""}
         ) +

{include_prepret if condition2 else ""}

* Decommissioning Surveillance
      SUM(OBJ_SUMIVS(R,V,P,K,Y),
            OBJ_DISC(R,Y,CUR) * OBJ_DLAGC(R,K,P,CUR) *
* Case 2.a-b
            ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + (NCAP_PASTI(R,V,P)$PASTYEAR(V))$OBJ_2A(R,V,P))
         )

    =E=

      SUM(OBV,SUM_OBJ('OBJFIX',OBV)*{var}_OBJ(R,OBV,CUR {sow}));

* Clears in INITCLR.MOD
""",
        )
