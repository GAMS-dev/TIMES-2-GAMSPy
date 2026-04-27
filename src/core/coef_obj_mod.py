# coef_obj_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_OBJ.MOD do coefficient calculations for the OBJ
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *  responsible for moving cost data to EACHYEAR from each input period
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillcost_gms import FillcostGms
from core.filparam_gms import FilparamGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefObjMod(GamsClass):
    """Translation unit for coef_obj.mod."""

    # Instance attributes
    module_name: str = "coef_obj_mod"
    gams_source: str = "coef_obj.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.declaration1()
        self.tc.enqueue(self.exec1)
        self.declaration2()
        self.tc.enqueue(
            self.check_year_matches_doc,
            condition1=(self.env.anncost.upper() == "LEV"),
            condition2=(f"{self.env.anncost}{self.env.ctst}".upper() == "LEV"),
        )

        # * interpolate discount rates
        self.include(
            FilparamGms(
                self.tc,
                self.env,
                arg1="G_DRATE",
                arg2="R,",
                arg3="CUR",
                arg4=",'','','','',''",
                arg5="ALLYEAR",
                arg6="LL",
                arg7="FIL(LL)$",
                arg8="FIL(LL)$",
            )
        )

        self.tc.enqueue(self.set_obj_disc)

        self.env.set_scoped("take", "RDCUR(R,CUR)")
        self.env.set_scoped("tmp", "1")
        # * Can we use macroes?
        if self.env.obmac == "YES":
            self.env.set_scoped("tmp", "2")

        if self.tc.defined("R_CUREX"):
            self.env.set_scoped("take", "1")

        self.tc.enqueue(
            self.determine_min_max_year,
            condition=self.env.validata == "YES",
        )

        self.env.set_local("bext", "(YEARVAL(FIL) GE PRC_YMIN(R,P))$")
        self.env.set_local("fext", "(YEARVAL(FIL) LE PRC_YMAX(R,P))$")

        # * investment related costs
        # fmt: off
        batincludes = [
            ("OBJ_ICOST", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_COST", "OB_ICOST", f"{self.env.tmp}"),
            ("OBJ_ISUB", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_ISUB", "OB_ISUB", f"{self.env.tmp}"),
            ("OBJ_ITAX", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_ITAX", "OB_ITAX", f"{self.env.tmp}"),
            ("NCAP_ISPCT", "R", "P", ",'0','0','0','0'", "FIL", "1", f"{self.env.bext}", f"{self.env.fext}", "NCAP_ISPCT", "X_RP", f"{self.env.tmp}"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillcostGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                )
            )

        self.tc.enqueue(self.exec2)

        # * fixed O&M and taxes
        # fmt: off
        batincludes = [
            ("OBJ_FOM", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_FOM", "OB_FOM", f"{self.env.tmp}"),
            ("OBJ_FSB", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_FSUB", "OB_FSB", f"{self.env.tmp}"),
            ("OBJ_FTX", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_FTAX", "OB_FTX", f"{self.env.tmp}"),
            # * decommissioning (actual & surveillance)
            ("OBJ_DCOST", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_DCOST", "OB_DCC", f"{self.env.tmp}"),
            ("OBJ_DLAGC", "R", "P,CUR", ",'0','0','0'", "FIL", f"{self.env.take}", f"{self.env.bext}", f"{self.env.fext}", "NCAP_DLAGC", "OB_DLC", f"{self.env.tmp}"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillcostGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                )
            )

        self.tc.enqueue(
            self.exec3,
            condition1=self.env.varcost.upper() == "LIN",
            condition2=self.env.validate == "YES",
        )

        # * variable costs
        # fmt: off
        batincludes = [
            ("OBJ_ACOST", "R", "P,CUR", ",'0','0','0'", "FIL", "RP(R,P)", "", "", "ACT_COST", "OB_ACT", f"{self.env.tmp}"),
            # * commodity costs
            ("OBJ_COMNT", "R", "C,S,COSTYPE,CUR", ",'0'", "FIL", "COM_TS(R,C,S)", "", "", "OBJ_COMNT", "OB_COM", ""),
            ("OBJ_COMPD", "R", "C,S,COSTYPE,CUR", ",'0'", "FIL", "COM_TS(R,C,S)", "", "", "OBJ_COMPD", "OB_COM", ""),
            ("OBJ_IPRIC", "R", "P,C,S,IE,CUR", "", "FIL", "RPCS_VAR(R,P,C,S)", "", "", "OBJ_IPRIC", "OB_IRE", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillcostGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                )
            )

        # * flow cost
        self.env.set_scoped("take", "(RPCS_VAR(R,P,C,S)+ANNUAL(S))")
        # fmt: off
        batincludes = [
            ("OBJ_FCOST", "R", "P,C,S,CUR", ",'0'", "FIL", f"{self.env.take}", "", "", "FLO_COST", "OB_FCOS", f"{self.env.tmp}"),
            ("OBJ_FDELV", "R", "P,C,S,CUR", ",'0'", "FIL", f"{self.env.take}", "", "", "FLO_DELIV", "OB_FDEL", f"{self.env.tmp}"),
            ("OBJ_FTAX", "R", "P,C,S,CUR", ",'0'", "FIL", f"{self.env.take}", "", "", "OBJ_FSUB", "OB_FTAX", f"{self.env.tmp}"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillcostGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                    arg11=arg[10],
                )
            )

        self.tc.enqueue(self.exec4)

        if self.env.obmac == "YES":
            self.compile_macros()

        # *-----------------------------------------------------------------------------*
        # * investment related costs
        # *-----------------------------------------------------------------------------*
        # * capital recovery factors: CRFs now defined in eqobjinv.mod / eqobsalv.mod
        # *    OBJ_CRF(RTP(R,V,P),CUR)    = (1-(1/(1+(G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP))))) /
        # *                                 (1-(1/(1+G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP)))**NCAP_ELIFE(RTP));
        # *    OBJ_CRFD(RTP(R,V,P),CUR)$NCAP_DELIF(RTP)  = (1-(1/(1+(G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP))))) /
        # *                                 (1-(1/(1+G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP)))**NCAP_DELIF(RTP));

        if (not self.env.validate == "YES") and (not self.env.timesed == "YES"):
            # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
            pass
        else:
            self.tc.enqueue(self.exec5)
            if not self.env.validate == "YES":
                # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
                pass
            else:
                self.tc.enqueue(self.exec6)

    def declaration1(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  ALIAS(K,EACHYEAR);
  SET Y(ALLYEAR);
  SET Y_EOH(ALLYEAR);
  SET YK(ALLYEAR,ALLYEAR);
  SET TS_ANN(S,S);
""",
        )

    def declaration2(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
 SCALARS YR_V1 /0/, YR_VL /0/, ACL /0/;

* For shaped demand elasticises
  ALIAS(AGE,SPAN);
  SET SHEDJ(LIM,J) 'Elastic demand shape indexes';
  PARAMETER SHAPED(BD,J,AGE) 'Elastic demand shape curves' //;
""",
        )

    def exec1(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  TS_ANN(S,S) = YES;
  TS_ANN(S,ANNUAL) = YES;
""",
        )

    def check_year_matches_doc(
        self: CoefObjMod, condition1: bool, condition2: bool
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* establish eachyear sets matching documentation
  YR_VL = MIYR_VL+DUR_MAX;
  LOOP(RTP(R,PASTMILE(LL),P)$NCAP_ILED(R,LL,P), K(LL+NCAP_ILED(R,LL,P)) = YES);
  Y(K)$((YEARVAL(K) >= MINYR) * (YEARVAL(K) <= YR_VL)) = YES;
  YK(Y,K)$(YEARVAL(K)<=YEARVAL(Y)) = YES;
{"ACL=MINYR; MINYR=MIYR_V1; RPT_OPT('OBJ','2')=1;" if condition1 else ""}
{"MINYR=ACL;" if condition2 else ""}
  Y_EOH(EOHYEARS)$(YEARVAL(EOHYEARS) >= MINYR) = YES;

  OPTION CLEAR=FIL;
  YR_V1 = MIN(SMIN(DATAYEAR,YEARVAL(DATAYEAR)),PYR_V1);
  YR_VL = MAX(SMAX(DATAYEAR,YEARVAL(DATAYEAR)),YR_VL);
  FIL(LL)$((YEARVAL(LL) GE YR_V1)*(YEARVAL(LL) LE YR_VL)) = YES;
""",
        )

    def set_obj_disc(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* set discounting factor OBJ_DISC in 'cumulative' way, covering EACHYEAR
* First, initialize the discount factor for YR_V1 to 1.0:
   OBJ_DISC(R,LL,CUR)$(RDCUR(R,CUR)$(YEARVAL(LL)=YR_V1)) = 1;
   IF(G_DYEAR=0,G_DYEAR=SUM(MIYR_1(T),YEARVAL(T)));
* Calculate all discount factors with respect to YR_V1:
   LOOP(FIL(LL-1), OBJ_DISC(R,LL,CUR) = OBJ_DISC(R,FIL,CUR) / (1+G_DRATE(R,LL,CUR)));
* Find the year among FIL that is closest to the base year G_DYEAR:
   F = SUM(MIYR_1(LL),YEARVAL(LL)-MAX(MIN(YR_VL,G_DYEAR),YR_V1));
* Normalize all discount factors so that the base year discount factor = 1.0:
   LOOP(RDCUR(R,CUR),
     Z = SUM(MIYR_1(LL+F),OBJ_DISC(R,LL,CUR)*(1+G_DRATE(R,LL,CUR))**(-(G_DYEAR-YEARVAL(LL))));
     OBJ_DISC(R,FIL(LL),CUR) = OBJ_DISC(R,LL,CUR) / Z);
* Prevent divide-by-zero if zero discount rate
   G_DRATE(R,V,CUR)$((G_DRATE(R,V,CUR) LE 0)$RDCUR(R,CUR)) = 1E-11;
*-----------------------------------------------------------------------------
* Calculate present value factors for time in periods
  LOOP(R$(NOT SUM(G_RCUR(RDCUR(R,CUR)),1)),
    Z = SMAX(RDCUR(R,CUR), SUM(T,D(T)*OBJ_DISC(R,T,CUR)));
    LOOP(RDCUR(R,CUR)$Z, F=SUM(T,D(T)*OBJ_DISC(R,T,CUR));
      IF(ABS(F-Z) LT 1E-7, G_RCUR(R,CUR) = YES; Z = 0)));
  OBJ_PVT(R,T,CUR)$RDCUR(R,CUR) = SUM(PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR));
  COEF_PVT(R,T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR));
  OBJ_RFR(R,V,CUR) $= G_DRATE(R,V,CUR);
  OBJ_RFR(R,V,CUR)$RDCUR(R,CUR) $= G_RFRIR(R,V);
*-----------------------------------------------------------------------------
* move original data from input to annual value arrays
* commodity costs
      OBJ_COMNT(R,DATAYEAR,C,S,COSTYPE,CUR)$(NOT COM_TS(R,C,S)) = 0;
      OBJ_COMPD(R,DATAYEAR,C,S,COSTYPE,CUR)$(NOT COM_TS(R,C,S)) = 0;

* IRE_PRICE - exports negative
* Take IRE_PRICE into account ONLY if the trade is exogenous; map ALL_R into R:
* Additionally allow using R directly as a placeholder of any external region
      LOOP(ALL_R$(NOT REG(ALL_R)),OBJ_IPRIC(R,DATAYEAR,P,C,S,IE,CUR)$RPC_IREIO(R,P,C,IE,'OUT') $=
         IRE_PRICE(R,DATAYEAR,P,C,S,ALL_R,IE,CUR)*(1-2$XPT(IE)));
      OBJ_IPRIC(R,DATAYEAR,P,C,S,IE,CUR)$RPC_IREIO(R,P,C,IE,'OUT') $= IRE_PRICE(R,DATAYEAR,P,C,S,R,IE,CUR)*(1-2$XPT(IE));
* flow costs; remove invalid costs on storage flows
      FLO_COST(R,LL,P,C,S,CUR)$((NOT TOP(R,P,C,'IN'))$RPC_STG(R,P,C)) = 0;
      FLO_DELIV(R,LL,P,C,S,CUR)$((NOT TOP(R,P,C,'OUT'))$RPC_STG(R,P,C)) = 0;
      OBJ_FSUB(R,LL,P,C,S,CUR) $= FLO_TAX(R,LL,P,C,S,CUR);
      OBJ_FSUB(R,LL,P,C,S,CUR)$FLO_SUB(R,LL,P,C,S,CUR) = OBJ_FSUB(R,LL,P,C,S,CUR)-FLO_SUB(R,LL,P,C,S,CUR);
      OBJ_FSUB(R,LL,P,C,S,CUR)$((NOT V(LL))$OBJ_VFLO(R,P,C,CUR,'SUB')) = 0;
      OPTION RPC_CUR <= FLO_COST; OBJ_VFLO(RPC_CUR,'COST') = YES;
      OPTION RPC_CUR <= FLO_DELIV; OBJ_VFLO(RPC_CUR,'COST') = YES;
      OPTION RPC_CUR <= FLO_TAX; OBJ_VFLO(RPC_CUR,'TAX') = YES;
      OPTION RPC_CUR <= FLO_SUB; OBJ_VFLO(RPC_CUR,'SUB') = YES;
* remove proportional subsidy if absolute defined
  IF(CARD(NCAP_ISPCT),OPTION PRC_YMAX<NCAP_ISUB; NCAP_ISPCT(R,LL,P)$PRC_YMAX(R,P)=0);

* V07_1b blending
  OBJ_BLNDV(R,Y_EOH,BLE,OPR,CUR)$(RDCUR(R,CUR)$BLE_OPR(R,BLE,OPR)) = BL_VAROMC(R,BLE,CUR) +
            SUM(COM$BL_DELIVC(R,BLE,COM,CUR), BL_INP(R,BLE,COM) * BL_DELIVC(R,BLE,COM,CUR));
""",
        )

    def determine_min_max_year(self: CoefObjMod, condition: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Establish process-wise subset of EACHYEAR by determining the MIN and MAX years
  MY_ARRAY(V) = MIN(B(V),M(V)-IPD(V));
  PRC_YMIN(RP(R,P)) = SMIN(RTP(R,V,P),MY_ARRAY(V));
  PRC_YMAX(RP(R,P)) = SMAX(RTP(R,PYR,P),YEARVAL(PYR));
* Make sure last commissioning year of repeated investments is included
  LOOP(T, Z = M(T)-E(T)+LAGT(T);
    PRC_YMAX(RP(R,P))$RTP(R,T,P) = MAX(PRC_YMAX(R,P),E(T)+NCAP_ILED(R,T,P)+MAX(Z,NCAP_TLIFE(R,T,P))$(COEF_RPTI(R,T,P) GT 1)));

*-----------------------------------------------------------------------------*
* Interpolation/extrapolation of cost parameters
* EACHYEAR will be sufficient for all capacity related costs
  Z = SMAX(RP,PRC_YMAX(RP));
  OPTION CLEAR=FIL,CLEAR=MY_ARRAY; FIL(K)$(YEARVAL(K) LE Z) = YES;
{"FIL(K)=V(K);" if condition else ""}
""",
        )

    def exec2(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  IF(CARD(X_RP),OB_ISUB(RP,CUR,YEAR)$X_RP(RP,YEAR) $= OB_ICOST(RP,CUR,YEAR)*X_RP(RP,YEAR); OPTION CLEAR=X_RP);
""",
        )

    def exec3(self: CoefObjMod, condition1: bool, condition2: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR=FIL; FIL(Y_EOH)$(YEARVAL(Y_EOH) GE MIYR_V1) = YES;
{"OPTION CLEAR=FIL; FIL(T) = YES;" if condition1 else ""}
{"OPTION CLEAR=FIL; FIL(T) = YES;" if condition2 else ""}
""",
        )

    def exec4(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=PRC_YMIN,CLEAR=PRC_YMAX;
  OPTION CLEAR=RPC_CUR,CLEAR=OBJ_FSUB;
""",
        )

    def compile_macros(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
$macro OBJ_ICOST(r,y,p,m) OB_ICOST(r,p,m,y)
$macro OBJ_ISUB(r,y,p,m) OB_ISUB(r,p,m,y)
$macro OBJ_ITAX(r,y,p,m) OB_ITAX(r,p,m,y)
$macro OBJ_FOM(r,y,p,m) OB_FOM(r,p,m,y)
$macro OBJ_FSB(r,y,p,m) OB_FSB(r,p,m,y)
$macro OBJ_FTX(r,y,p,m) OB_FTX(r,p,m,y)
$macro OBJ_DCOST(r,y,p,m) OB_DCC(r,p,m,y)
$macro OBJ_DLAGC(r,y,p,m) OB_DLC(r,p,m,y)
$macro OBJ_ACOST(r,y,p,m) OB_ACT(r,p,m,y)
$macro OBJ_FCOST(r,y,p,c,s,m) OB_FCOS(r,p,c,s,m,y)
$macro OBJ_FDELV(r,y,p,c,s,m) OB_FDEL(r,p,c,s,m,y)
$macro OBJ_FTAX(r,y,p,c,s,m) OB_FTAX(r,p,c,s,m,y)
""",
        )

    def exec5(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Calculate coefficients for shaped demand elasticises
* Collect all tuples (J,BD) from COM_ELASTX to SHEDJ(BD,J)
  SHEDJ(BD,J) $= SUM(RTC_SHED(R,T,C,BD,J),1); SHEDJ(BDNEQ,'1') = YES;
* Calculate price changes by percent, and cumulate
  BDSIG(BDNEQ)=CEIL(SMAX(RTC_SHED(R,T,C,BDNEQ,J),COM_VOC(R,T,C,BDNEQ))*100); BDSIG('LO')=MIN(100,BDSIG('LO'));
  SHAPED(SHEDJ(BDNEQ,J),AGE)$(ORD(AGE) LE BDSIG(BDNEQ)) = (1+.01/(1+(ORD(AGE)-1)/100))**(1/MAX(1E-3,SHAPE(J,AGE)));
  LOOP((AGE,SPAN(AGE-1),BDNEQ(BD))$(ORD(AGE) LE BDSIG(BD)),SHAPED(SHEDJ(BD,J),AGE) = SHAPED(BD,J,AGE)*SHAPED(BD,J,SPAN));
  BDSIG(BDNEQ) = 1-2$BDUPX(BDNEQ);
""",
        )

    def exec6(self: CoefObjMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Flat period assignment
* As original parameters are not filled, flat data must be taken from OBJ_xxx
  LOOP(V, FIL(FIL)=NO; FIL(K)$PERIODYR(V,K) = YES;
      OBJ_ICOST(R,FIL,P,CUR)      $= OBJ_ICOST(R,V,P,CUR);
      OBJ_FOM(R,FIL,P,CUR)        $= OBJ_FOM(R,V,P,CUR);
      OBJ_ACOST(R,FIL,P,CUR)      $= OBJ_ACOST(R,V,P,CUR);
      OBJ_IPRIC(R,FIL,P,C,S,R,IE,CUR) $= OBJ_IPRIC(R,V,P,C,S,R,IE,CUR);
      OBJ_FCOST(R,FIL,P,C,S,CUR)  $= OBJ_FCOST(R,V,P,C,S,CUR);
      OBJ_FDELV(R,FIL,P,C,S,CUR)  $= OBJ_FDELV(R,V,P,C,S,CUR);
  );
*display "*** after flat period assignment ***", obj_icost, obj_fom;
""",
        )
