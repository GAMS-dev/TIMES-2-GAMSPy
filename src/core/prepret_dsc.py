# prepret_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREPRET.dsc oversees pre-processing for retirements
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, get_args

from core.fillparm_gms import FillparmGms
from core.prepparm_gms import PrepparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

PhaseArg = Literal["PREP", "DECL", "EQOBJ", "OBJFIX", "OBSALV", ""]


class PrepretDsc(GamsClass):
    """Translation unit for prepret.dsc."""

    # Instance attributes
    module_name: str = "prepret_dsc"
    gams_source: str = "prepret.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: PhaseArg,
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        self.arg1: str = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("mip", f"{self.env.solmip}==YES")

        arg_upper = self.arg1.upper() if self.arg1 else ""
        if arg_upper == "PREP":
            self.comp_prep()
        elif arg_upper == "DECL":
            self.comp_decl()
        elif arg_upper == "EQOBJ":
            self.comp_eqobj()
        elif arg_upper == "OBJFIX":
            return objfix(capwd=self.env.capwd, vart=self.env.vart, sws=self.env.sws)
        elif arg_upper == "OBSALV":
            objsalv(
                var=self.env.var, varv=self.env.varv, sws=self.env.sws, sow=self.env.sow
            )
        else:
            allowed = ", ".join(get_args(PhaseArg))
            raise ValueError(
                f"Unknown argument '{self.arg1}'. Expected one of: {allowed}"
            )

    def comp_prep(self: PrepretDsc):
        self.env.set_scoped("tst", self.arg2)
        if self.tc.defined("PRC_REFIT"):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"SET {self.arg2} //; PARAMETER {self.arg3} //;",
            )
        if self.env.retire.upper() == "NO":
            self.tc.add_gams_code(module=self, phase="init", code=rf"$KILL {self.arg2}")
        if self.tc.defined(self.arg2.upper()):
            self.tc.add_gams_code(
                module=self, phase="init", code=rf"PARAMETER {self.arg3} //;"
            )
            self.tc.enqueue(self.exec_prep1, sym2=self.arg2, sym3=self.arg3)
        if self.env.retire.upper() == "YES":
            self.arg1 = self.arg2
            self.arg2 = self.arg3
            self.arg3 = ""
        self.tc.enqueue(self.exec_prep2)
        if self.tc.defined(self.arg2.upper()):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* Declarations
  SET VNRET(YEAR,LL); PARAMETER RP_RTF(R,P);
""",
            )
            # Interpolate RCAP_BND
            if self.env.tst == self.arg1:
                self.tc.enqueue(self.exec_prep3, tst=self.env.tst, arg2=self.arg2)
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1="RCAP_BLK",
                    arg2="R",
                    arg3="P",
                    arg4=",'','','','',''",
                    arg5="V",
                    arg6="RTP(R,V,P)",
                    arg7="GE 0",
                )
            )
            self.include(
                PrepparmGms(
                    self.tc,
                    self.env,
                    arg1="RCAP_BND",
                    arg2="R",
                    arg3="P,L",
                    arg4=",'','',''",
                    arg5="V",
                    arg6="RTP(R,V,P)",
                    arg7="1",
                )
            )
            if self.tc.defined("NCAP_OLIFE"):
                self.include(
                    FillparmGms(
                        self.tc,
                        self.env,
                        arg1="NCAP_OLIFE",
                        arg2="R",
                        arg3="P",
                        arg4=",'','','','',''",
                        arg5="V",
                        arg6="RTP(R,V,P)",
                        arg7="GE 0",
                    )
                )
                self.tc.enqueue(self.exec_prep4)
            # Preprocess refits
            self.tc.enqueue(self.exec_prep5)
            # Activate MIP solution if requested
            if self.env.dsc.upper() == "YES":
                self.env.set_global("solmip", self.env.retire)
            if self.env.retire.upper() == "MIP":
                self.env.set_global("solmip", "YES")

    def exec_prep1(self: PrepretDsc, sym2: str, sym3: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"{sym3}(R,'0',P,'N')$({sym3}(R,'0',P,'N')=0)$={sym2}(R,P);",
        )

    def exec_prep2(self: PrepretDsc):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"PRC_REFIT(RP,P)$0=0;",
        )

    def exec_prep3(self: PrepretDsc, tst: str, arg2: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"OPTION {tst} < {arg2};",
        )

    def exec_prep4(self: PrepretDsc):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"OPTION PRC_CAP < NCAP_ELIFE; NCAP_ELIFE(R,V,P)$(NOT PRC_CAP(R,P)) $= NCAP_OLIFE(R,V,P); PRC_CAP(R,P)=0;",
        )

    def exec_prep5(self: PrepretDsc):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Preprocess refits
  LOOP((RP(R,PRC),P)$(RP(R,P)$PRC_REFIT(RP,P)),
    NCAP_ILED(RTP(R,V,P)) = -ABS(NCAP_ILED(RTP));
    PRC_RCAP(RP)=YES; TRACKP(R,P)$(PRC_REFIT(RP,P)<0)=YES);
  RTP_VARP(RTP(R,T,P)) $= PRC_RCAP(R,P);
  PRC_RCAP(TRACKP)=YES; OPTION CLEAR=TRACKP;
""",
        )

    def comp_decl(self: PrepretDsc):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{"INTEGER" if self.env.mip == "YES==YES" else ""}
  VARIABLE {self.env.var}_DRCAP(R,ALLYEAR,LL,P{self.env.swd},J);
  EQUATION {self.env.eq}_DSCRET(R,ALLYEAR,ALLYEAR,P{self.env.swtd});
""",
        )

        self.tc.enqueue(self.exec_decl1, sow=self.env.sow, var=self.env.str)

    def exec_decl1(self: PrepretDsc, sow: str, var: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Maps for refit vintages & types
  PRC_RCAP(PRC_RCAP(RP)) = PRC_CAP(RP);
  LOOP(PRC_RCAP(R,PRC), F=0; MY_F=0; CNT=EPS;
   LOOP(P$PRC_REFIT(R,PRC,P),Z=PRC_REFIT(R,PRC,P); CNT$CNT=CNT+1;
    IF(ABS(Z)>2, F=F+1); IF(MOD(Z,2)=0,MY_F$(ABS(Z)-4)=3);
    IF(Z<0,RTP_TT(R,T,TT,PRC)$COEF_CPT(R,T,TT,P)=YES;
    ELSE RTP_TT(R,T,T,PRC)$RTP(R,T,P)=YES; CNT=0;));
   IF(CNT,Z=(-1+2$(F=CNT))*MAX(1,MY_F); ELSE Z=-2);
   IF(NOT MAPVAL(CNT),RP_RTF(R,PRC) = Z);
   IF(F,RCAP_BND(RTP(R,T,PRC),'UP')$(NOT SUM(P$PRC_REFIT(R,PRC,P),RTP(R,T,P)$(ABS(PRC_REFIT(R,PRC,P))>2)))=EPS));
* Force obj type 2a/2b
  VNRET(VNT(V,T))$(NOT SAMEAS(V,T)) = YES;
  RVPRL(RTP(R,V,P))$PRC_RCAP(R,P)=MAX(0,SMAX(RTP_CPTYR(R,VNRET(V,T),P),YEARVAL(T))-YEARVAL(V));
  RVP(RTP) $= RVPRL(RTP);
  NCAP_ILED(RVP) = NCAP_ILED(RVP)+EPS;
* Set bounds for continuous retirements
  RCAP_BND(R,T,P,BDNEQ) $= RCAP_BND(R,T,P,'FX');
  PASTSUM(RVP(R,V,P))$RCAP_BND(RVP,'N') = -(B(V)+NCAP_ILED(RVP)+ABS(RCAP_BND(RVP,'N')));
  PASTSUM(RVP)$((RCAP_BND(RVP,'N')<0)+MAPVAL(RCAP_BLK(RVP))) = MAX(1,ABS(PASTSUM(RVP)));
  LOOP(TT(T--1),Z=ORD(T)-1;
  {var}_RCAP.LO(RTP_CPTYR(R,VNRET(V,T),P){sow})$RVP(R,V,P) = RCAP_BND(R,T,P,'LO')$(NOT MAPVAL(RCAP_BLK(R,V,P)))+MIN(0,RTFORC(R,V,T,P)-RTFORC(R,V,TT,P)$Z);
  {var}_RCAP.UP(RTP_CPTYR(R,VNRET(V,T),P){sow})$RCAP_BND(R,T,P,'UP') =
    MIN(SMIN(PASTMILE(V),NCAP_PASTI(R,V,P)),RCAP_BND(R,T,P,'UP')+MAX(0,RTFORC(R,V,T,P)-RTFORC(R,V,TT,P)$Z)));
  {var}_SCAP.LO(RTP_CPTYR(R,VNRET(V,T),P){sow})$RVP(R,V,P) = MAX(RCAP_BND(R,T,P,'LO'),RTFORC(R,V,T,P));
  {var}_SCAP.UP(RTP_CPTYR(R,PASTMILE(V),T,P){sow})$RVP(R,V,P) = MAX(RTFORC(R,V,T,P),NCAP_PASTI(R,V,P));
  LOOP(RVP(R,V,P),Z=1;LOOP(RTP_CPTYR(R,VNRET(V,T),P)$Z,Z=0; {var}_SCAP.UP(R,V,T,P{sow})=MIN({var}_RCAP.UP(R,V,T,P{sow}),{var}_SCAP.UP(R,V,T,P{sow}))));
  {var}_SCAP.FX(RTP_CPTYR(R,V,T,P){sow})$(((M(T) LT ABS(PASTSUM(R,V,P)))+((M(T)-LEAD(T))/PASTSUM(R,V,P) GE 1))$PASTSUM(R,V,P)) = RTFORC(R,V,T,P);
* Force refits = retirements on request
  PRC_YMAX(PRC_RCAP(RP)) = MIN(0,SUM(P$PRC_REFIT(RP,P),MAX(EPS,3-ABS(PRC_REFIT(RP,P)))));
  RVPRL(R,'0',P) $= PRC_YMAX(R,P);
  {var}_RCAP.UP(RTP_TT(R,T(TT++1),T,P){sow})$((RP_RTF(R,P)<3)$PRC_YMAX(R,P))=MAX(0,SUM(RTP(R,PYR_S(V),P),RTFORC(R,V,T,P)-RTFORC(R,V,TT,P))$VNT(TT,T)$(MOD(RP_RTF(R,P),2)=0));
  OPTION CLEAR=PASTSUM,CLEAR=RVP;
""",
        )

    def comp_eqobj(self: PrepretDsc):
        self.env.set_global(
            "rcapsub",
            rf"-SUM(VNRET(V,T),{self.env.vart}_SCAP(R,V,T,P{self.env.sws}))$PRC_RCAP(R,P)",
        )
        self.env.set_global(
            "rcapsbm",
            rf"-SUM(VNRET(MODLYEAR,T),{self.env.vart}_SCAP(R,MODLYEAR,T,P{self.env.sws}))$PRC_RCAP(R,P)",
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Allow retirements in integer multiples of a user-defined block-size or the full residual capacity
  {self.env.eq}_DSCRET(RTP_CPTYR({self.env.r_v_t},P){self.env.swt})$(VNRET(V,T)$RCAP_BLK(R,V,P))..

   {self.env.var}_SCAP(R,V,T,P{self.env.sow}) - RTFORC(R,V,T,P)  =E=
   RCAP_BLK(R,V,P) * {self.env.var}_DRCAP(R,V,T,P{self.env.sow},'2') + (NCAP_PASTI(R,V,P)-RTFORC(R,V,T,P)) * {self.env.var}_DRCAP(R,V,T,P{self.env.sow},'1');

* Cumulative retirements
  {self.env.eq}_CUMRET(R,VNRET(V,K(T-(1-1$RP_RTF(R,P)))),P{self.env.swt})$(RTP_CPTYR(R,V,T,P)$PRC_RCAP(R,P))..

   SUM(RTP_CPTYR(R,V,K,P),{self.env.var}_SCAP(R,V,T,P{self.env.sow}) - {self.env.var}_RCAP(R,V,T,P{self.env.sow})) -
   SUM(RTP_CPTYR(R,V,MODLYEAR(Y(T-1)),P)$VNRET(V,Y),{self.env.varm}_SCAP(R,V,Y,P{self.env.sws}))
   =E= 0;

* Maximum salvage capacity
  {self.env.eq}L_SCAP(RTP(R,V(LL),P),IPS{self.env.sow})$(((OBJ_SUMS(RTP)+(NOT PRC_VINT(R,P))$T(V))$RVPRL(RTP)$L(IPS) OR NCAP_OLIFE(RTP)$IO(IPS))$PRC_RCAP(R,P))..

   SUM(IO(IPS),SUM((RTP_CPTYR(R,V,TT,P),PRC_TS(R,P,S)),{self.env.vartt}_ACT(R,V,TT,P,S{self.env.sws})*FPD(TT))/PRC_CAPACT(R,P)/NCAP_OLIFE(RTP)) +
   SUM(VNRET(V,T(LL+RVPRL(RTP))),{self.env.vart}_SCAP(R,V,T,P{self.env.sws}))$LIM(IPS)

   =L=  {self.env.varv}_NCAP(R,V,P{self.env.sws})$T(V) + NCAP_PASTI(R,V,P) - {self.env.var}_SCAP(R,V,'0',P{self.env.sow})$OBJ_SUMS(R,V,P)$RVPRL(R,V,P);

* Retrofits and life-extensions
  {self.env.eq}L_REFIT(RTP_TT(R,TT,T,PRC),LNX(L){self.env.swt})$((BD(L)+VNT(T,TT)$(RP_RTF(R,PRC)=3))$RT_PP(R,T))..
   SUM((V(TT),P)$((VNT(T,V) OR PRC_REFIT(R,PRC,P)<0)$PRC_REFIT(R,PRC,P)),COEF_CPT(R,V,T,P)*({self.env.varv}_NCAP(R,V,P{self.env.sws}){self.env.rcapsub}))+{self.env.var}_RCAP(R,T,TT,PRC{self.env.sow})$(RP_RTF(R,PRC)$VNT(T,TT)$BD(L)<3)
   =E=
   SUM(RTP_CPTYR(R,VNRET(V,TT),PRC),COEF_CPT(R,V,T,PRC) * ({self.env.vartt}_RCAP(R,V,TT,PRC{self.env.sws})-SUM(MODLYEAR(K(TT-1))$VNT(V,K),MIN(INF$MOD(RP_RTF(R,PRC),2),RTFORC(R,V,TT,PRC)-RTFORC(R,V,K,PRC)))))+
   SUM(K(TT-1)$RTP_TT(R,K,T,PRC),{self.env.var}_RCAP(R,T,K,PRC{self.env.sow}))$(RP_RTF(R,PRC)$BD(L)>0);
""",
        )

        if self.env.varmac in ["0==0", "1==1"]:
            self.env.set_scoped("var", self.env.vas)
        self.tc.enqueue(
            self.exec_eqobj1,
            notmip=not self.env.mip == "YES==YES",
            var=self.env.var,
            sow=self.env.sow,
        )

    def exec_eqobj1(self: PrepretDsc, notmip: bool, var: str, sow: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{"OPTION CLEAR=RCAP_BLK;" if notmip else ""}
* Set bounds for integer retirements
  IF(CARD(RCAP_BLK), RCAP_BLK(RTP)$(RCAP_BLK(RTP) LE 0) = 0;
*  Define upper bound of 1 for binary variable if past investments
   COEF_CAP(RTP_CPTYR(R,V,T,P))$RCAP_BLK(R,V,P) = (NCAP_PASTI(R,V,P)-RTFORC(R,V,T,P))/RCAP_BLK(R,V,P);
   {var}_DRCAP.UP(RTP_CPTYR(R,V,T,P){sow},'1')$PRC_RCAP(R,P) = 1$(ABS(COEF_CAP(R,V,T,P)-MIN(10,ROUND(COEF_CAP(R,V,T,P)))) >1E-9);
*  Define upper bound for integer multiples
   {var}_DRCAP.UP(RTP_CPTYR(R,V,T,P){sow},'2')$RCAP_BLK(R,V,P) = MIN(10,FLOOR({var}_SCAP.UP(R,V,T,P{sow})/RCAP_BLK(R,V,P)+1E-8));
  );
  RVPRL(R,PYR_S,P)$PRC_RESID(R,'0',P)=NO; NCAP_OLIFE(R,T,P)$(NOT PRC_VINT(R,P))=NO;
  OPTION CLEAR=COEF_CAP;
""",
        )


def objfix(capwd: str, vart: str, sws: str):
    return rf"""
* Credit retired capacity for the avoided fixed costs
   SUM((OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE),VNRET(V,T))$RVPRL(R,V,P),
     SUM((INVSPRED(K_EOH,JOT,LL,K),KTYAGE(LL,T,Y_EOH,AGE))$OPYEAR(LIFE,AGE),
          -OBJ_DISC(R,Y_EOH,CUR) * (1+RTP_CPX(R,V,P,T)$NCAP_CPX(R,V,P)) * {capwd}
             (
                OBJ_FOM(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                OBJ_FTX(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
                OBJ_FSB(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
             )
        ) *
        {vart}_SCAP(R,V,T,P {sws}) / OBJ_DIVIV(R,V,P)) +

* RESIDS require special handling
   SUM(RTP_CPTYR(R,PYR_S(V(K)),T,P)$((NOT RVPRL(R,V,P))$PRC_RCAP(R,P)),
        SUM(PERIODYR(T,Y_EOH), -OBJ_DISC(R,Y_EOH,CUR) *
             (
                OBJ_FOM(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),MULTI(JJ,Y_EOH)-1)) +
                OBJ_FTX(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),MULTI(JJ,Y_EOH)-1)) -
                OBJ_FSB(R,K,P,CUR) * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),MULTI(JJ,Y_EOH)-1))
             )) *
        {vart}_SCAP(R,V,T,P {sws})) +
"""


def objsalv(var: str, varv: str, sws: str, sow: str):
    return rf"""
* Discredit salvage value for retired capacity
   SUM(OBJ_SUMS(R,V,P)$((NOT NCAP_FDR(R,V,P)$RVPRL(R,'0',P))$RVPRL(R,V,P)),
     OBJSCC(R,V,P,CUR) * OBJ_DCEOH(R,CUR) *
     ({var}_SCAP(R,V,'0',P{sow})-{varv}_NCAP(R,V,P{sws})$T(V)-NCAP_PASTI(R,V,P))) +
"""


def prepret_dsc():
    raise NotImplementedError()
