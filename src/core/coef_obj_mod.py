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
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Set

from core.base_class import GamsClass
from core.fillcost_gms import FillcostGms, FillcostGmsConfig
from core.filparam_gms import FilparamGms, FilparamGmsConfig

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        g = self.tc

        r, p, c, s, ie, cur, costype = g.r, g.p, g.c, g.s, g.ie, g.cur, g.costype
        Rp, Rdcur, Fil, ComTs, RpcsVar = g.Rp, g.Rdcur, g.Fil, g.ComTs, g.RpcsVar

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
                config=FilparamGmsConfig(
                    src=g.g_drate,
                    arg2=(g.r,),
                    tail1=(g.cur,),
                    arg4=("", "", "", "", ""),
                    arg5=g.allyear,
                    arg6=g.ll,
                    arg7=g.Fil[g.ll],  # "FIL(LL)$" handle $ at end
                    arg8=g.Fil[g.ll],  # "FIL(LL)$" handle $ at end
                ),
            )
        )

        self.tc.enqueue(self.set_obj_disc)
        self.env.set_scoped("take", "RDCUR(R,CUR)")
        take: ImplicitSet | Literal[1] = Rdcur[r, cur]
        self.env.set_scoped("tmp", "1")
        tmp = 1
        # * Can we use macroes?
        if self.env.obmac == "YES":
            self.env.set_scoped("tmp", "2")
            tmp = 2

        if self.tc.defined_assigned("R_CUREX"):
            self.env.set_scoped("take", "1")
            take = 1

        self.tc.enqueue(
            self.determine_min_max_year, condition=self.env.validata == "YES"
        )

        self.env.set_local("bext", "(YEARVAL(FIL) GE PRC_YMIN(R,P))$")
        bext = g.yearval[Fil] >= g.prc_ymin[r, p]
        self.env.set_local("fext", "(YEARVAL(FIL) LE PRC_YMAX(R,P))$")
        fext = g.yearval[Fil] <= g.prc_ymax[r, p]

        # * investment related costs
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_icost, arg2=r, arg3=(p,cur), arg4=('0','0','0'),arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_cost, arg10="OB_ICOST", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_isub, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_isub, arg10="OB_ISUB", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_itax, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_itax, arg10="OB_ITAX", arg11=tmp),
            FillcostGmsConfig(arg1=g.ncap_ispct, arg2=r, arg3=(p,), arg4=('0','0','0','0'), arg5=Fil, arg6=1, bext=bext, fext=fext, arg9=g.ncap_ispct, arg10="X_RP", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        self.tc.enqueue(self.exec2)

        # * fixed O&M and taxes
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_fom, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_fom, arg10="OB_FOM", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_fsb, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_fsub, arg10="OB_FSB", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_ftx, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_ftax, arg10="OB_FTX", arg11=tmp),
            # * decommissioning (actual & surveillance)
            FillcostGmsConfig(arg1=g.obj_dcost, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_dcost, arg10="OB_DCC", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_dlagc, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_dlagc, arg10="OB_DLC", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        self.tc.enqueue(
            self.exec3,
            condition1=self.env.varcost.upper() == "LIN",
            condition2=self.env.validate == "YES",
        )

        # * variable costs
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_acost, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=Rp[r,p], bext=1, fext=1, arg9=g.act_cost, arg10="OB_ACT", arg11=tmp),
            # * commodity costs
            FillcostGmsConfig(arg1=g.obj_comnt, arg2=r, arg3=(c,s,costype,cur), arg4=('0',), arg5=Fil, arg6=ComTs[r,c,s], bext=1, fext=1, arg9=g.obj_comnt, arg10="OB_COM"),
            FillcostGmsConfig(arg1=g.obj_compd, arg2=r, arg3=(c,s,costype,cur), arg4=('0',), arg5=Fil, arg6=ComTs[r,c,s], bext=1, fext=1, arg9=g.obj_compd, arg10="OB_COM"),
            FillcostGmsConfig(arg1=g.obj_ipric, arg2=r, arg3=(p,c,s,ie,cur), arg4=(), arg5=Fil, arg6=RpcsVar[r,p,c,s], bext=1, fext=1, arg9=g.obj_ipric, arg10="OB_IRE"),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        # * flow cost
        self.env.set_scoped("take", "(RPCS_VAR(R,P,C,S)+ANNUAL(S))")
        take = RpcsVar[r, p, c, s] + g.Annual[s]  # type: ignore[assignment]
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_fcost, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.flo_cost, arg10="OB_FCOS", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_fdelv, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.flo_deliv, arg10="OB_FDEL", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_ftax, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.obj_fsub, arg10="OB_FTAX", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

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

        if (self.env.validate != "YES") and (self.env.timesed != "YES"):
            # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
            pass
        else:
            self.tc.enqueue(self.exec5)
            if self.env.validate != "YES":
                # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
                pass
            else:
                self.tc.enqueue(self.exec6)

    def declaration1(self: CoefObjMod) -> None:
        g = self.tc
        m = g.container

        g.k = Alias(m, name="K", alias_with=g.Eachyear)
        g.Y = Set(m, name="Y", domain=[g.allyear])
        g.YEoh = Set(m, name="Y_EOH", domain=[g.allyear])
        g.Yk = Set(m, name="YK", domain=[g.allyear, g.allyear])
        g.TsAnn = Set(m, name="TS_ANN", domain=[g.s, g.s])

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
