# rpt_obj_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOL_FLO - code associated with the substitution of flow variables
# *	%1 - target parameter name
# *	%2 - parameter name suffix
# *	%3 - VAR_FLO suffix (.L or .M)
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.eqobjvar_rpt import eqobjvar_rpt
from core.rpt_objc_rpt import rpt_objc_rpt
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptObjRpt(GamsClass):
    """Translation unit for rpt_obj.rpt."""

    module_name: str = "rpt_obj_rpt"
    gams_source: str = "rpt_obj.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            stages=self.env.stages,
            sysprefix=self.env.sysprefix,
            etl=self.env.etl,
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            var=self.env.var,
            varm=self.env.varm,
            varv=self.env.varv,
            sws=self.env.sws,
            timesed=self.env.timesed,
            bencost=self.env.bencost,
            obj=self.env.obj,
            varcost=self.env.varcost,
            pgprim=self.env.pgprim,
            discshift=self.env.discshift,
            vnret_defined=self.tc.defined("VNRET"),
        )

    def exec1(
        self: RptObjRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        stages: str,
        sysprefix: str,
        etl: str,
        capjd: str,
        capwd: str,
        var: str,
        timesed: str,
        obj: str,
        varcost: str,
        pgprim: str,
        varv: str,
        varm: str,
        sws: str,
        bencost: str,
        discshift: float,
        vnret_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rpt_obj_rpt(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                stages=stages,
                sysprefix=sysprefix,
                etl=etl,
                capjd=capjd,
                capwd=capwd,
                var=var,
                timesed=timesed,
                bencost=bencost,
                obj=obj,
                varcost=varcost,
                pgprim=pgprim,
                varv=varv,
                varm=varm,
                sws=sws,
                discshift=discshift,
                vnret_defined=vnret_defined,
            ),
        )


def rpt_obj_rpt(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    stages: str,
    sysprefix: str,
    etl: str,
    capjd: str,
    capwd: str,
    var: str,
    varv: str,
    varm: str,
    sws: str,
    timesed: str,
    obj: str,
    varcost: str,
    pgprim: str,
    bencost: str,
    discshift: float,
    vnret_defined: bool,
) -> str:
    sic = "*(1+PASTSUM(R,V,P))" if stages.upper() == "YES" else ""
    p1 = f"'{sysprefix}INSTCAP'"
    tpulse = (
        "Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)*"
        if varcost.upper() == "LIN"
        else "TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)*"
        if obj.upper() == "LIN"
        else "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)* OBJ_ALTV(R,T)*"
        if obj.upper() == "ALT"
        else "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)*"
    )

    return rf"""
$onMulti
  OPTION CLEAR=NCAP_YES,CLEAR=RTP_OBJ,CLEAR=RTP_NPV,CLEAR=RTP_CAPVL;
  RTP_CAPVL(RTP)=VAR_NCAP.L(RTP)+NCAP_PASTI(RTP);
  NCAP_YES(RTP)$(RTP_CAPVL(RTP)>0) = YES;
  MY_F=ROUND(RPT_OPT('OBJ','1'));
  {
        "PASTSUM(NCAP_YES(R,T,P)) = SUM(SW_TSW(SOW,T,WW),OBJ_SIC(R,T,P,WW)); MY_F=EPS$MY_F;"
        if stages.upper() == "YES"
        else ""
    }
*------------------------------------------------------------------------------
* Hurdle rates
  COEF_CRF(OBJ_ICUR(NCAP_YES(R,V,P),CUR))$(NCAP_DRATE(R,V,P)>0) = MAX(0,1-
   ((1-(1+NCAP_DRATE(R,V,P))**(-NCAP_ELIFE(R,V,P))) / (1-(1+OBJ_RFR(R,V,CUR))**(-NCAP_ELIFE(R,V,P)))) /
   (NCAP_DRATE(R,V,P)/OBJ_RFR(R,V,CUR)*((1+NCAP_DRATE(R,V,P))/(1+OBJ_RFR(R,V,CUR)))**MIN({
        discshift
    }-1,-0.5$NCAP_ILED(R,V,P))));
*------------------------------------------------------------------------------
* Lump-sum investment costs
*------------------------------------------------------------------------------
  F = RPT_OPT('NCAP','7')>0;
  COEF_RTP(RTP(R,T,P))$PRC_CAP(R,P) = VAR_NCAP.L(RTP)$NCAP_YES(RTP) +
    SUM(PERIODYR(T,Y_EOH)$NCAP_PASTI(R,Y_EOH,P),NCAP_PASTI(R,Y_EOH,P)*POWER(COEF_RPTI(RTP),1$T(Y_EOH)-1))$F;
  {arg1}CAP_NEW({arg2}RVPT(R,T,P,TT),{p1}) $= COEF_RTP(R,T,P);
  {arg1}CAP_NEW({arg2}RTP(R,T,P),T,{
        p1
    })$((NOT OBJ_2A(RTP))$COEF_RTP(RTP)) = COEF_RPTI(RTP)*COEF_RTP(RTP);
  OPTION CLEAR=UNCD1; UNCD1(J)$(ORD(J)<3)=YES;
  RTP_OBJ(JJ(UNCD1(J)),OBJ_ICUR(NCAP_YES(R,T(V),P),CUR))=
    {"(VAR_IC.L(R,T,P)*COR_SALVI(R,T,P,CUR))$SEG(R,P) +" if etl == "YES" else ""}
    SUM((OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT),INVSPRED(K_EOH,JOT,Y,K)),
        ({macro.obj_icost("R", "K", "P", "CUR")}{sic}$(ORD(J)=2)+({
        macro.obj_itax("R", "K", "P", "CUR")
    }-{macro.obj_isub("R", "K", "P", "CUR")})$(ORD(J)=1))) *
    COEF_RTP(R,T,P) * COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) /
    (1+G_DRATE(R,T,CUR))**({discshift}$(NOT NCAP_ILED(R,T,P)));
  SYSPLIT(SYSUC)=1-SUM(SYSUCMAP(SYSUC,ITEM),1);
  LOOP(UNCD1(J),{arg1}CAP_NEW({arg2}R,T,P,TT,SYSUC)$({arg1}CAP_NEW({arg2}R,T,P,TT,{
        p1
    })$SUCMAP(J,SYSUC))=SUM(RDCUR(R,CUR),RTP_OBJ(J,R,T,P,CUR)*ABS(SYSPLIT(SYSUC)-COEF_CRF(R,T,P,CUR)))
    IF(NOT MY_F,OPTION CLEAR=COEF_CRF));
  OPTION CLEAR=COEF_RTP,CLEAR=RTP_OBJ;
*-----------------------------------------------------------------------------
* Objective function by component
*-----------------------------------------------------------------------------
* Check objective INV
  RTP_OBJ('1',OBJ_ICUR(NCAP_YES(R,V,P),CUR)) =
    SUM(OBJ_SUMII(R,V,P,AGE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,YEAR,K), OBJ_DISC(R,K,CUR) * (1-SALV_INV(R,V,P,YEAR)) * {
        macro.obj_icost("R", "K", "P", "CUR")
    }) *
      (VAR_NCAP.L(R,V,P)$T(V) + OBJ_PASTI(R,V,P,CUR)){
        sic
    } * COR_SALVI(R,V,P,CUR) / OBJ_DIVI(R,V,P)) +
     SUM(OBJ_SUMIII(R,V,P,LL,K,Y), OBJ_DISC(R,Y,CUR) * (1-SALV_INV(R,V,P,LL)) *
       (VAR_NCAP.L(R,V,P)$T(V) + OBJ_PASTI(R,V,P,CUR)) / OBJ_DIVIII(R,V,P) *
       (COR_SALVD(R,V,P,CUR)*{
        macro.obj_dcost("R", "K", "P", "CUR")
    }-SUM(C$NCAP_OCOM(R,V,P,C),NCAP_OCOM(R,V,P,C)*NCAP_VALU(R,K,P,C,CUR))$(NOT Y_EOH(Y)))) -
     SUM(OBJ_SUMIVS(R,V,P,K,Y),OBJ_DISC(R,Y,CUR)*SALV_INV(R,V,P,K)*{
        macro.obj_dlagc("R", "K", "P", "CUR")
    }*RTP_CAPVL(R,V,P));

* Discounted taxes & subsidies
  RTP_OBJ('2',OBJ_ICUR(NCAP_YES(R,V,P),CUR)) =
    SUM(OBJ_SUMII(R,V,P,AGE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,YEAR,K), OBJ_DISC(R,K,CUR) * (1-SALV_INV(R,V,P,YEAR)) *
        ({macro.obj_itax("R", "K", "P", "CUR")} - {
        macro.obj_isub("R", "K", "P", "CUR")
    })) *
      (VAR_NCAP.L(R,V,P)$T(V) + OBJ_PASTI(R,V,P,CUR)) * COR_SALVI(R,V,P,CUR) / OBJ_DIVI(R,V,P));

{
        r'''
  VAR_SCAP.L(R,T,'0',P)$(NCAP_FDR(R,T,P)$RVPRL(R,'0',P)$RVPRL(R,T,P)) = RTP_CAPVL(R,T,P);
  PAR_OBJCAP(OBJ_ICUR(NCAP_YES(R,V,P),CUR))$RVPRL(R,V,P)=OBJSCC(R,V,P,CUR)*OBJ_DCEOH(R,CUR)*(RTP_CAPVL(R,V,P)-VAR_SCAP.L(R,V,'0',P))$OBJ_SUMS(R,V,P);
  RTP_OBJ('1',R,V,P,CUR)$PAR_OBJCAP(R,V,P,CUR) = RTP_OBJ('1',R,V,P,CUR)+PAR_OBJCAP(R,V,P,CUR)*(1-(1/(1+RTP_OBJ('1',R,V,P,CUR)/RTP_OBJ('2',R,V,P,CUR)))$(RTP_OBJ('2',R,V,P,CUR)>0));
  RTP_OBJ('2',R,V,P,CUR)$((RTP_OBJ('2',R,V,P,CUR)>0)$PAR_OBJCAP(R,V,P,CUR)) = RTP_OBJ('2',R,V,P,CUR)+PAR_OBJCAP(R,V,P,CUR)/(1+RTP_OBJ('1',R,V,P,CUR)/RTP_OBJ('2',R,V,P,CUR));
  RTP_ISHPR(RTP(R,V,P))$PRC_RCAP(R,P)=YES;
'''
        if vnret_defined
        else ""
    }
  {arg1}REG_WOBJ({
        arg2
    }R,'INVX',CUR) = SUM(OBJ_ICUR(NCAP_YES(R,V,P),CUR),RTP_OBJ('2',R,V,P,CUR));
  OBJVAL_1 = SUM(OBJ_ICUR(NCAP_YES(R,V,P),CUR),RTP_OBJ('1',R,V,P,CUR)) + SUM(RDCUR(R,CUR),{
        arg1
    }REG_WOBJ({arg2}R,'INVX',CUR));
  OBJVAL_2 = SUM(RDCUR(R,CUR),SUM(OBV,SUM_OBJ('OBJINV',OBV)*{var}_OBJ.L(R,OBV,CUR{
        arg3
    }))-{var}_OBJ.L(R,'OBJSAL',CUR{arg3}));
  {"DISPLAY OBJVAL_1,OBJVAL_2;" if arg1 != "S" else ""}

 IF(MY_F, SYSINV('{arg4}INV+')=YES);
 IF(MY_F>0,OPTION TRACKP<RTP_OBJ; {arg1}CST_PVP({
        arg2
    }SYSINV,TRACKP(R,P))=SUM((J,V,CUR)$RTP_OBJ(J,R,V,P,CUR),RTP_OBJ(J,R,V,P,CUR)*ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR))));

*------------------------------------------------------------------------------
* Fixed costs / sub / tax
*------------------------------------------------------------------------------
* Check objective FIX
 PASTSUM(NCAP_YES(R,V,P))$OBJ_DIVIV(R,V,P) = RTP_CAPVL(R,V,P)/OBJ_DIVIV(R,V,P);

 RTP_NPV('1',OBJ_FCUR(NCAP_YES(R,V,P),CUR)) =
   SUM(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE)$(NOT RTP_ISHPR(R,V,P)),
      SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd}
        {macro.obj_fom("R", "K", "P", "CUR")}) * PASTSUM(R,V,P)) +
   SUM(OBJ_SUMIV(K_EOH,RTP_ISHPR(R,V,P),JOT,LIFE), PASTSUM(R,V,P) *
      SUM(INVSPRED(K_EOH,JOT,LL,K), {capwd}
        SUM(KTYAGE(LL,Y,Y_EOH,AGE)$OPYEAR(LIFE,AGE), OBJ_DISC(R,Y_EOH,CUR) * (1+RTP_CPX(R,V,P,Y)$NCAP_CPX(R,V,P)) * {
        "(1-(VAR_SCAP.L(R,V,Y,P)/PASTSUM(R,V,P)/OBJ_DIVIV(R,V,P))$PRC_RCAP(R,P))*"
        if vnret_defined
        else ""
    }
             {
        macro.obj_fom("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))))) +
   SUM(OBJ_SUMIVS(R,V,P,K,Y),OBJ_DISC(R,Y,CUR)*{
        macro.obj_dlagc("R", "K", "P", "CUR")
    }*PASTSUM(R,V,P));

* Discounted taxes & subsidies
  RTP_NPV('2',OBJ_FCUR(NCAP_YES(R,V,P),CUR)) =
    SUM(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE)$(NOT RTP_ISHPR(R,V,P)),
      SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd}
        ({macro.obj_ftx("R", "K", "P", "CUR")}-{
        macro.obj_fsb("R", "K", "P", "CUR")
    })) * PASTSUM(R,V,P)) +
    SUM(OBJ_SUMIV(K_EOH,RTP_ISHPR(R,V,P),JOT,LIFE), PASTSUM(R,V,P) *
      SUM(INVSPRED(K_EOH,JOT,LL,K), {capwd}
        SUM(KTYAGE(LL,Y,Y_EOH,AGE)$OPYEAR(LIFE,AGE), OBJ_DISC(R,Y_EOH,CUR) * (1+RTP_CPX(R,V,P,Y)$NCAP_CPX(R,V,P)) * {
        "(1-(VAR_SCAP.L(R,V,Y,P)/PASTSUM(R,V,P)/OBJ_DIVIV(R,V,P))$PRC_RCAP(R,P))*"
        if vnret_defined
        else ""
    }
            (
              {
        macro.obj_ftx("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
              {
        macro.obj_fsb("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
            ))));

  {arg1}REG_WOBJ({
        arg2
    }R,'FIXX',CUR) = SUM(OBJ_FCUR(NCAP_YES(R,V,P),CUR),RTP_NPV('2',R,V,P,CUR));
  OBJVAL_1 = SUM(OBJ_FCUR(NCAP_YES(R,V,P),CUR),RTP_NPV('1',R,V,P,CUR)) + SUM(RDCUR(R,CUR),{
        arg1
    }REG_WOBJ({arg2}R,'FIXX',CUR));
  OBJVAL_2 = SUM(RDCUR(REG,CUR),SUM(OBV,SUM_OBJ('OBJFIX',OBV)*{var}_OBJ.L(REG,OBV,CUR{
        arg3
    })));
  {"DISPLAY OBJVAL_1,OBJVAL_2;" if arg1 != "S" else ""}

 IF(MY_F>0,OPTION TRACKP<RTP_NPV; {arg1}CST_PVP({arg2}'{
        arg4
    }FIX',TRACKP(R,P))=SUM((J,V,CUR)$RTP_NPV(J,R,V,P,CUR),RTP_NPV(J,R,V,P,CUR)));
 OPTION CLEAR=PASTSUM,CLEAR=TRACKP;

OPTION CLEAR=UNCD1; UNCD1('1')=MY_F+ACL;

{
        eqobjvar_rpt(
            arg1="PAR",
            arg2="J(UNCD1),",
            arg3="J('2'),",
            arg4="Y_EOH",
            arg5="SUM",
            tpulse=tpulse,
            tmp="Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)*",
            pgprim=pgprim,
            stages=stages,
            is_vnret_defined=vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )
    }

  IF(MY_F>0,
    OPTION PAR_RPMX < PAR_ACTC;
    {arg1}CST_PVP({arg2}'{
        arg4
    }ACT',RP) $= SUM((J,V,T,C,CUR)$PAR_RPMX(RP,J,V,T,C,CUR),PAR_RPMX(RP,J,V,T,C,CUR));
    OPTION PAR_RPMX < PAR_FLOC;
    {arg1}CST_PVP({arg2}'{
        arg4
    }FLO',RP) $= SUM((J,V,T,C,CUR)$PAR_RPMX(RP,J,V,T,C,CUR),PAR_RPMX(RP,J,V,T,C,CUR));
    OPTION PAR_RCMX < PAR_COMC;
    {arg1}CST_PVC({arg2}'{
        arg4
    }COM',RC) $= SUM((J,T,CUR)$PAR_RCMX(RC,J,T,CUR),PAR_RCMX(RC,J,T,CUR));
  );
  {arg1}REG_WOBJ({
        arg2
    }R,'VARX',CUR) = SUM((V,T,P,C)$PAR_FLOC('2',R,V,T,P,C,CUR),PAR_FLOC('2',R,V,T,P,C,CUR)) +
                               SUM((T,C)$PAR_COMC('2',R,T,C,CUR),PAR_COMC('2',R,T,C,CUR));
*------------------------------------------------------------------------------
  LOOP(RDCUR(R,CUR),
   {arg1}REG_WOBJ({arg2}R,'INV',CUR) = SUM(OBV,SUM_OBJ('OBJINV',OBV)*{
        var
    }_OBJ.L(R,OBV,CUR{arg3}))-{var}_OBJ.L(R,'OBJSAL',CUR{arg3})-{arg1}REG_WOBJ({
        arg2
    }R,'INVX',CUR)+EPS;
   {arg1}REG_WOBJ({arg2}R,'FIX',CUR) = SUM(OBV,SUM_OBJ('OBJFIX',OBV)*{
        var
    }_OBJ.L(R,OBV,CUR{arg3}))-{arg1}REG_WOBJ({arg2}R,'FIXX',CUR)+EPS;
   {arg1}REG_WOBJ({arg2}R,'VAR',CUR) = SUM(OBV,SUM_OBJ('OBJVAR',OBV)*{
        var
    }_OBJ.L(R,OBV,CUR{arg3}))-{arg1}REG_WOBJ({arg2}R,'VARX',CUR)+EPS;
* Elastic demand costs
   {arg1}REG_WOBJ({arg2}R,'ELS',CUR) = EPS
{
        "  +SUM(BD," + var + "_OBJELS.L(R,BD,CUR" + arg3 + ")*(BDSIG(BD)-1$LNX(BD)))"
        if timesed == "YES"
        else ""
    }
  );

{
        ""
        if arg5 == "0"
        else rpt_objc_rpt(
            arg1=arg1,
            arg2=arg2,
            arg3=arg4,
            capjd=capjd,
            capwd=capwd,
            tpulse=tpulse,
            stages=stages,
            bencost=bencost,
        )
    }
"""
