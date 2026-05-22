# rptmisc_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTMISC.rpt: Miscellaneous shared reportings
# *  arg1 - Prefix for parameter names (optional)
# *  arg2 - SOW, (optional)
# *  arg3 - SOW
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptmiscRpt(GamsClass):
    """Translation unit for rptmisc.rpt."""

    # Instance attributes
    module_name: str = "rptmisc_rpt"
    gams_source: str = "rptmisc.rpt"

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
            self.exec_rptmisc_rpt,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            var=self.env.var,
            cufscal=self.env.cufscal,
            var_uc=self.env.var_uc,
            sysprefix=self.env.sysprefix,
            model_name=self.env.model_name,
            vart=self.env.vart,
            sws=self.env.sws,
            eq=self.env.eq,
            rpt_flots=self.env.rpt_flots,
            stages=self.env.stages,
            solans=self.env.solans,
            if_defined_vnret=self.tc.defined("VNRET"),
            if_defined_eqe_ucrtp=self.tc.defined("EQE_UCRTP"),
            if_not_defined_eq_g_ucmax=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
        )

    def exec_rptmisc_rpt(
        self: RptmiscRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        var: str,
        cufscal: str,
        var_uc: str,
        sysprefix: str,
        model_name: str,
        vart: str,
        sws: str,
        eq: str,
        rpt_flots: str,
        stages: str,
        solans: str,
        if_defined_vnret: bool,
        if_defined_eqe_ucrtp: bool,
        if_not_defined_eq_g_ucmax: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rptmisc_rpt(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                var=var,
                cufscal=cufscal,
                var_uc=var_uc,
                sysprefix=sysprefix,
                model_name=model_name,
                vart=vart,
                sws=sws,
                eq=eq,
                rpt_flots=rpt_flots,
                stages=stages,
                solans=solans,
                if_defined_vnret=if_defined_vnret,
                if_defined_eqe_ucrtp=if_defined_eqe_ucrtp,
                if_not_defined_eq_g_ucmax=if_not_defined_eq_g_ucmax,
            ),
        )


def rptmisc_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    var: str,
    cufscal: str,
    sysprefix: str,
    model_name: str,
    vart: str,
    sws: str,
    eq: str,
    if_defined_vnret: bool,
    rpt_flots: str,
    stages: str,
    if_defined_eqe_ucrtp: bool,
    var_uc: str,
    if_not_defined_eq_g_ucmax: bool,
    solans: str,
) -> str:
    g_ucmax_code = ""
    if not if_not_defined_eq_g_ucmax:
        g_ucmax_code = f"""
      {arg1}PAR_UCMAX({arg2}UC_N,ALL_R,'-',C)$UC_GMAX(UC_N,ALL_R,'N',C,'N') = {var}_UC.L(UC_N{arg3})-{eq}G_UCMAX.L(UC_N,ALL_R,'N',C,'N'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,ALL_R,P,C)$UC_GMAX(UC_N,ALL_R,P,C,'EACH')  = {var}_UC.L(UC_N{arg3})-{eq}G_UCMAX.L(UC_N,ALL_R,P,C,'EACH'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,R,'-',C)$(UC_R_EACH(R,UC_N)$UC_GMAX(UC_N,R,'N',C,'N')) = {var}_UCR.L(UC_N,R{arg3})-{eq}G_UCMAX.L(UC_N,R,'N',C,'N'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,R,P,C)$(UC_R_EACH(R,UC_N)$UC_GMAX(UC_N,R,P,C,'EACH'))  = {var}_UCR.L(UC_N,R{arg3})-{eq}G_UCMAX.L(UC_N,R,P,C,'EACH'{arg3});
    """
    return rf"""
  R_DF(R,T) = SIGN(COEF_PVT(R,T))/MAX(1E-9,ABS(COEF_PVT(R,T)));
*-----------------------------------------------------------------------------
* Activity levels & marginals
*-----------------------------------------------------------------------------
  {arg1}PAR_ACTL({arg2}RTP_VINTYR(R,V,T,P),S)$PRC_TS(R,P,S) $= VAR_ACT.L(R,V,T,P,S);
* Shift up STS activity levels
  LOOP((RP_STL(R,P,TSL,BD),TS_GROUP(R,TSL,TS))$RLUP(R,'DAYNITE',TSL),Z=G_YRFR(R,TS)*365/TS_CYCLE(R,TS);
    YKVAL(VNT(V,T))=SMIN(RS_BELOW(R,TS,S),VAR_ACT.L(R,VNT,P,S)/Z)$NCAP_YES(R,V,P);
    {arg1}PAR_ACTL({
        arg2
    }R,VNT,P,S)$(TS_MAP(R,TS,S)$YKVAL(VNT))=VAR_ACT.L(R,VNT,P,S)+YKVAL(VNT)*(1-(1+Z)$RS_BELOW(R,TS,S)));
  Z = (RPT_OPT('ACT','2') GE 0);
  {arg1}PAR_ACTM({
        arg2
    }R,V,T,P,S)$VAR_ACT.M(R,V,T,P,S) = ROUND(VAR_ACT.M(R,V,T,P,S)*R_DF(R,T),7)$Z;
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQL_ACTBND.M(R,T,P,S)*R_DF(R,T);
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQG_ACTBND.M(R,T,P,S)*R_DF(R,T);
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQE_ACTBND.M(R,T,P,S)*R_DF(R,T);

*-----------------------------------------------------------------------------
* Capacity
*-----------------------------------------------------------------------------
  OPTION CLEAR=RTP_CAPYR,CLEAR=COEF_CAP;
  RTP_CAPYR(RTP_CPTYR(R,TT,T,P))$VAR_NCAP.L(R,TT,P) = YES;
  VAR_CAP.M(RTP)$(NOT VAR_CAP.M(RTP)) $= EQE_CPT.M(RTP);

  {arg1}PAR_CAPL({
        arg2
    }RTP(R,T,P))  = SUM(RTP_CAPYR(R,TT,T,P), COEF_CPT(R,TT,T,P)*VAR_NCAP.L(R,TT,P));
  {arg1}PAR_PASTI({
        arg2
    }RTP(R,T,P),'0') = SUM(PYR(K)$COEF_CPT(R,K,T,P),COEF_CPT(R,K,T,P)*NCAP_PASTI(R,K,P)-RTFORC(R,K,T,P)$PYR_S(K));

{
        f"COEF_CAP(R,V,T,P)$=VAR_SCAP.L(R,V,T,P); {arg1}PAR_PASTI({arg2}RTP(R,T,P),'€')$PRC_RCAP(R,P) = -SUM(VNRET(V,T),COEF_CAP(R,V,T,P)*COEF_CPT(R,V,T,P)-RTFORC(R,V,T,P));"
        if if_defined_vnret
        else ""
    }
  IF(RPT_OPT('CAP','5')>0,{arg1}PAR_CUMRET({arg2}RTP_CPTYR) $= COEF_CAP(RTP_CPTYR));
  {arg1}PAR_CAPM({arg2}RTP(R,T,P))   $= VAR_CAP.M(RTP)*R_DF(R,T);
  {arg1}PAR_CAPBD({arg2}RTP,'LO')    $= CAP_BND(RTP,'LO');
  {arg1}PAR_CAPBD({arg2}RTP_OFF(RTP),'UP')$RCAP_BND(RTP,'N') $= PRC_RESID(RTP);
  {arg1}PAR_CAPBD({arg2}RTP,'UP')$(CAP_BND(RTP,'UP') NE INF) $= CAP_BND(RTP,'UP');

  {arg1}PAR_NCAPL({arg2}RTP(R,V,P))  $= VAR_NCAP.L(RTP);
  {arg1}PAR_NCAPM({
        arg2
    }RTP)$(VAR_NCAP.M(RTP)*COEF_OBJINV(RTP)) = VAR_NCAP.M(RTP)/COEF_OBJINV(RTP);

*-----------------------------------------------------------------------------
* Commodities
*-----------------------------------------------------------------------------
* Variables
  {arg1}PAR_COMPRDL({arg2}R,T,C,S) $= VAR_COMPRD.L(R,T,C,S);
  {arg1}PAR_COMPRDM({arg2}R,T,C,S) $= VAR_COMPRD.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_COMNETL({arg2}R,T,C,S) $= VAR_COMNET.L(R,T,C,S);
  {arg1}PAR_COMNETM({arg2}R,T,C,S) $= VAR_COMNET.M(R,T,C,S)*R_DF(R,T);
  OPTION AGR < COM_AGG;
  {arg1}AGG_OUT({arg2}R,T,C,S)$(RTCS_VARC(R,T,C,S)$AGR(R,C)) =
    SUM(RTC(R,T,COM)$COM_AGG(RTC,C),COM_AGG(RTC,C) *
       SUM(RTCS_VARC(RTC,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS)) *
         (VAR_COMNET.L(RTC,TS)$RC_AGP(R,COM,'LO') + VAR_COMPRD.L(RTC,TS)$RC_AGP(R,COM,'FX'))));
  OPTION CLEAR=AGR;

* Equations
  {arg1}PAR_COMBALEM({arg2}R,T,C,S) $= EQG_COMBAL.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_COMBALEM({arg2}R,T,C,S) $= EQE_COMBAL.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_PEAKM({arg2}R,T,CG,S)   $= EQ_PEAK.M(R,T,CG,S)*R_DF(R,T);
{f"{arg1}PAR_COMBALGM({arg2}RTC,S) $= EQG_COMBAL.L(RTC,S);" if arg1 == "S" else ""}

*-----------------------------------------------------------------------------
* Process flows
*-----------------------------------------------------------------------------
  OPTION CLEAR=UNCD1,CLEAR=RTP_CAPYR,CLEAR=F_INOUT;
  F_INOUT(R,V,T,P,C,'IN')$COEF_ICOM(R,V,T,P,C) = COEF_ICOM(R,V,T,P,C) * RTP_CAPVL(R,V,P);
  F_INOUT(R,V,T,P,C,'OUT')$COEF_OCOM(R,V,T,P,C) = COEF_OCOM(R,V,T,P,C) * RTP_CAPVL(R,V,P);
  F_INOUT(RTP_CPTYR(R,V,T,P),C,IO)$NCAP_COM(R,V,P,C,IO) = F_INOUT(R,V,T,P,C,IO) +
    (RTP_CAPVL(R,V,P)-COEF_CAP(R,V,T,P)) * COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,IO) * (1+COEF_CIO(R,V,T,P,C,IO));
  F_INOUTS(R,V,T,P,C,ANNUAL(S),IO)$F_INOUT(R,V,T,P,C,IO) = F_INOUTS(R,V,T,P,C,S,IO)+F_INOUT(R,V,T,P,C,IO);

* inputs: main flows & emissions, aux flows & emissions
  {arg1}F_IN({arg2}R,V,T,P,C,S)$TOP(R,P,C,'IN')   $= PAR_FLO(R,V,T,P,C,S);
  {arg1}F_IN({arg2}R,V,T,P,C,S)                   $= PAR_IRE(R,V,T,P,C,S,'EXP');
  {arg1}F_IN({arg2}R,V,T,P,C,S)$RPCS_VAR(R,P,C,S) $= VAR_SIN.L(R,V,T,P,C,S);
  {arg1}F_IN({arg2}R,V,T,P,C,S)$F_INOUTS(R,V,T,P,C,S,'IN') = {arg1}F_IN({
        arg2
    }R,V,T,P,C,S)+F_INOUTS(R,V,T,P,C,S,'IN');
* outputs: main flows & emissions, aux flows & emissions
  PAR_FLO(R,V,T,P,C,S)$RPCS_VAR(R,P,C,S)  $= VAR_SOUT.L(R,V,T,P,C,S)*STG_EFF(R,V,P);
  {arg1}F_OUT({arg2}R,V,T,P,C,S)$TOP(R,P,C,'OUT') $= PAR_FLO(R,V,T,P,C,S);
  {arg1}F_OUT({arg2}R,V,T,P,C,S)                  $= PAR_IRE(R,V,T,P,C,S,'IMP');
  {arg1}F_OUT({arg2}R,V,T,P,C,S)$F_INOUTS(R,V,T,P,C,S,'OUT') = {arg1}F_OUT({
        arg2
    }R,V,T,P,C,S)+F_INOUTS(R,V,T,P,C,S,'OUT');
*-----------------------------------------------------------------------------
* Filter out small values if requested
  IF(SUM(UC_GRPTYPE$RPT_OPT(UC_GRPTYPE,'9'),1),RPT_OPT(UC_GRPTYPE,'9')$(RPT_OPT(UC_GRPTYPE,'9')>.1)=0;
    Z=RPT_OPT('ACT','9'); IF(Z>0,{arg1}PAR_ACTL({arg2}R,V,T,P,S)$(({arg1}PAR_ACTL({
        arg2
    }R,V,T,P,S)<Z)${arg1}PAR_ACTL({arg2}R,V,T,P,S))=0);
    Z=RPT_OPT('CAP','9');
    IF(Z>0,{arg1}PAR_CAPL({arg2}RTP)$(({arg1}PAR_CAPL({arg2}RTP)<Z)${arg1}PAR_CAPL({
        arg2
    }RTP))=0;
           {arg1}PAR_PASTI({arg2}RTP(R,T,P),'€')$((ABS({arg1}PAR_PASTI({
        arg2
    }RTP,'€'))<Z)${arg1}PAR_PASTI({arg2}RTP,'€'))=0);
    Z=RPT_OPT('NCAP','9');IF(Z>0,{arg1}PAR_NCAPL({arg2}RTP)$(({arg1}PAR_NCAPL({
        arg2
    }RTP)<Z)${arg1}PAR_NCAPL({arg2}RTP))=0);
    Z=RPT_OPT('FLO','9');
    IF(Z>0,{arg1}F_OUT({arg2}R,V,T,P,C,S)$((ABS({arg1}F_OUT({arg2}R,V,T,P,C,S))<Z)${
        arg1
    }F_OUT({arg2}R,V,T,P,C,S)) = 0;
           {arg1}F_IN({arg2}R,V,T,P,C,S)$((ABS({arg1}F_IN({arg2}R,V,T,P,C,S))<Z)${
        arg1
    }F_IN({arg2}R,V,T,P,C,S)) = 0));
*-----------------------------------------------------------------------------
* If power levels or fall-back to ANNUAL is requested, set reporting at com_TS
  UNCD1(U2(COM_TYPE))$RPT_OPT(U2,'3')=YES;
  UNCD1(U2(NRG_TYPE))$RPT_OPT(U2,'1')=YES;
  UNCD1(U2(NRG_TYPE))$RPT_OPT(U2,'3')=YES;
  RPT_OPT('FLO','1')$CARD(UNCD1)=YES;
  MY_TS(S) = ORD(S) EQ CARD(S);
  OPTION CLEAR=RTP_CAPVL,CLEAR=RVTPC,CLEAR=F_INOUTS,CLEAR=RCS;
* Check for unused COM variables
  RTTC(RTC)$(NOT SUM(RHS_COMPRD(RTC,S),1)) = YES;
  OPTION CLEAR=RXX; RXX(RTC)$(NOT SUM(RCS_COMBAL(RTC,S,BD),1))=YES;
  Z = (RPT_OPT('COMPRD','1') LE 0); IF(Z,RTTC(RTC)$(NOT RXX(RTC))=NO);
  IF(RPT_OPT('FLO','1')<1,
{"RCS(RC,ANNUAL)=YES;" if rpt_flots.upper() == "ANNUAL" else ""}
  ELSE RCS(COM_TS)=YES);
  IF(CARD(RCS),
* Represent all process flows at requested timeslices
    F_IOS(R,V,T,P,C,S)$(NOT RCS(R,C,S)) $= {arg1}F_IN({
        arg2
    }R,V,T,P,C,S); OPTION RVTPC<F_IOS;
    {arg1}F_IN({arg2}RVTPC,S)$F_IOS(RVTPC,S)=0;
    {arg1}F_IN({arg2}RVTPC(R,V,T,P,C),TS)$RCS(R,C,TS) = {arg1}F_IN({arg2}RVTPC,TS) +
      SUM(RS_TREE(R,TS,S)$F_IOS(RVTPC,S),RS_FR(R,TS,S)*(1+RTCS_FR(R,T,C,TS,S))*F_IOS(RVTPC,S));
    OPTION CLEAR=RVTPC,CLEAR=F_IOS;
    F_IOS(R,V,T,P,C,S)$(NOT RCS(R,C,S)) $= {arg1}F_OUT({
        arg2
    }R,V,T,P,C,S); OPTION RVTPC<F_IOS;
    {arg1}F_OUT({arg2}RVTPC,S)$F_IOS(RVTPC,S)=0;
    {arg1}F_OUT({arg2}RVTPC(R,V,T,P,C),TS)$RCS(R,C,TS) = {arg1}F_OUT({arg2}RVTPC,TS) +
      SUM(RS_TREE(R,TS,S)$F_IOS(RVTPC,S),RS_FR(R,TS,S)*(1+RTCS_FR(R,T,C,TS,S))*F_IOS(RVTPC,S));
    OPTION CLEAR=RCS,CLEAR=RVTPC,CLEAR=F_IOS;
    {arg1}PAR_COMPRDL({arg2}RTCS_VARC(RTTC(R,T,C),S)) = SUM((VNT(V,T),P)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S));
*...optional power levels
    LOOP(NRG_TYPE(U2)$RPT_OPT(U2,'1'), F=(ROUND(RPT_OPT(U2,'3'))=2);
     {arg1}P_OUT({
        arg2
    }RTPC(R,T,P,C),S)$(COM_TS(R,C,S)$NRG_TMAP(R,NRG_TYPE,C))=SUM(VNT(V,T)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S)/G_YRFR(R,S)/RPT_OPT(U2,'1'))
        - SUM(VNT(V,T)${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S)/G_YRFR(R,S)/RPT_OPT(U2,'1'))$F);
  ELSE {arg1}PAR_COMPRDL({arg2}RTTC(R,T,C),ANNUAL)=SUM((VNT(V,T),P,S)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S));
 );
{"RPT_OPT('FLO','3')=0;" if stages.upper() == "YES" else ""}
 IF(RPT_OPT('FLO','3'),
   VAL_FLO(R,V,T,P,C) $= SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S)*{arg1}PAR_COMBALEM({arg2}R,T,C,S));
   F_INOUTS(R,V,T,P,C,ANNUAL,'OUT') $= SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),{
        arg1
    }F_OUT({arg2}R,V,T,P,C,S)*{arg1}PAR_COMBALEM({arg2}R,T,C,S));
   VAL_FLO(R,V,T,P,C)$F_INOUTS(R,V,T,P,C,'ANNUAL','OUT') = VAL_FLO(R,V,T,P,C)-F_INOUTS(R,V,T,P,C,'ANNUAL','OUT');
   OPTION CLEAR=F_INOUTS;
 );
* Complete COMPRDL & COMNETL reporting
  {arg1}PAR_COMPRDL({arg2}RTTC(R,T,C),S)${arg1}AGG_OUT({arg2}RTTC,S) = {
        arg1
    }PAR_COMPRDL({arg2}RTTC,S)+{arg1}AGG_OUT({arg2}RTTC,S);
  {arg1}PAR_COMNETL({arg2}RTC(RXX(R,T,C)),S) $= {arg1}PAR_COMPRDL({arg2}RTC,S);
  {arg1}PAR_COMNETL({arg2}RTCS_VARC(RXX(R,T,C),ANNUAL(S))) = {arg1}PAR_COMPRDL({
        arg2
    }R,T,C,S)*PROD(RTTC(R,T,C),COM_IE(RTTC,S))-SUM(RPC_CAPFLO(R,V,P,C)$VNT(V,T),F_INOUT(R,V,T,P,C,'IN'));
  {arg1}PAR_COMPRDL({arg2}RXX(RTTC(R,T,C)),S)=0;
  {var}_COMNET.L(RTC(RXX(R,T,C)),S{arg3}) $= {arg1}PAR_COMNETL({arg2}RTC,S);
*-----------------------------------------------------------------------------
* Cumflo results (unscaling)
  {arg1}PAR_CUMFLOL({arg2}R,P,C,YEAR,LL) $= {var}_CUMFLO.L(R,P,C,YEAR,LL{arg3})*{
        cufscal
    };
  {arg1}PAR_CUMFLOM({arg2}R,P,C,YEAR,LL) $= {var}_CUMFLO.M(R,P,C,YEAR,LL{arg5})*(1/{
        cufscal
    });
  {arg1}PAR_CUMCST({arg2}R,YEAR,LL,COSTAGG,CUR) $= {var}_CUMCST.L(R,YEAR,LL,COSTAGG,CUR{
        arg3
    });
* Marginals of Dynamic process bounds
{
        "EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD('FX')) $= EQE_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD);"
        if if_defined_eqe_ucrtp
        else ""
    }
  {arg1}PAR_UCRTP({
        arg2
    }UC_N,R,T,P,UC_GRPTYPE) $= SUM(BD$PRC_DYNUC(UC_N,'RHS',R,T,P,UC_GRPTYPE,BD),EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD)*(1/COEF_OBJINV(R,T,P))$COEF_OBJINV(R,T,P));
  {arg1}PAR_UCRTP({
        arg2
    }UC_N,R,T,P,'ACT') $= SUM(BD$PRC_DYNUC(UC_N,'RHS',R,T,P,'ACT',BD),EQN_UCRTP.M(UC_N,R,T,P,'ACT',BD)*R_DF(R,T));
  IF(RPT_OPT('COMPRD','4'), {arg1}PAR_UCMRK({
        arg2
    }R,T,ITEM,C,S) $= EQL_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S) $= EQG_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S) $= EQE_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S)${arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S)=({
        arg1
    }PAR_UCMRK({arg2}R,T,ITEM,C,S)/COEF_PVT(R,T))$(NOT SUM(RX_MARK(R,LL,ITEM,C,BD),1)));
*-----------------------------------------------------------------------------
* User constraints
*-----------------------------------------------------------------------------
{
        ""
        if var_uc != "YES"
        else (
            f'''
* Levels
  {var}_UC.L('{sysprefix}SOLVE_STATUS'{arg3}) $= {model_name}.MODELSTAT;
  {arg1}PAR_UCSL({arg2}UC_N,'NONE','NONE','NONE') $= {var}_UC.L(UC_N{arg3});
  {arg1}PAR_UCSL({arg2}UC_N,R,'NONE','NONE')      $= {var}_UCR.L(UC_N,R{arg3});
  {arg1}PAR_UCSL({arg2}UC_N,'NONE',T,'NONE')      $= {vart}_UCT.L(UC_N,T{sws});
  {arg1}PAR_UCSL({arg2}UC_N,R,T,'NONE')           $= {vart}_UCRT.L(UC_N,R,T{sws});
  {arg1}PAR_UCSL({arg2}UC_N,'NONE',T,S)           $= {vart}_UCTS.L(UC_N,T,S{sws});
  {arg1}PAR_UCSL({arg2}UC_N,R,T,S)                $= {vart}_UCRTS.L(UC_N,R,T,S{sws});
* Marginals
  {arg1}PAR_UCSM({arg2}UCN,R,T,ANNUAL)$UC_R_SUM(R,UCN) $= {vart}_UCT.M(UCN,T{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UCN,R,T,S)$UC_TS_EACH(R,UCN,S)  $= {vart}_UCTS.M(UCN,T,S{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UC_N,'NONE','NONE','NONE') $= {var}_UC.M(UC_N{arg5});
  {arg1}PAR_UCSM({arg2}UC_N,R,'NONE','NONE')      $= {var}_UCR.M(UC_N,R{arg5});
  {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,'NONE')      $= {vart}_UCT.M(UC_N,T{arg4});
  {arg1}PAR_UCSM({arg2}UC_N,R,T,'NONE')           $= {vart}_UCRT.M(UC_N,R,T{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,S)           $= {vart}_UCTS.M(UC_N,T,S{arg4});
  {arg1}PAR_UCSM({arg2}UC_N,R,T,S)                $= {vart}_UCRTS.M(UC_N,R,T,S{
                arg4
            })*R_DF(R,T);

* UCMAX equations
{g_ucmax_code}
'''
        )
    }
*-----------------------------------------------------------------------------
* Prepare ELC supply by energy source
{"RPT_OPT('FLO','5')=1;" if solans == "YES" else ""}
  IF(RPT_OPT('FLO','5'),
  TRACKP(R,P)$SUM(TOP(RPC_SPG(R,P,C),'IN')$NRGELC(R,C),1) = YES;
  TRACKPC(RPC(RP_FLO(R,P),C))$(TOP(RPC,'OUT')$NRGELC(R,C)) = YES;
  TRACKPC(TRACKP,C) = NO; OPTION TRACKP < TRACKPC, CLEAR=F_VIO, CLEAR=KEEP_FLOF;
  TRACKPG(TRACKP(R,P),C)$((NOT NRGELC(R,C))$NRG(R,C)$TOP(R,P,C,'IN')) = YES;
  F_VIO(RTP_VINTYR(R,V,T,P),IO)$TRACKP(R,P) =
    SUM((TRACKPC(R,P,C),S)$(NOT IPS(IO)),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))+SUM((TRACKPG(R,P,C),IPS(IO),S),{arg1}F_IN({arg2}R,V,T,P,C,S))+1-1;
  {arg1}PAR_EOUT({arg2}RTP_VINTYR(R,V,T,P),C)$(F_VIO(R,V,T,P,'IN')$TRACKPG(R,P,C)) =
    F_VIO(R,V,T,P,'OUT') / F_VIO(R,V,T,P,'IN') * SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{
        arg1
    }F_IN({arg2}R,V,T,P,C,S));
  OPTION CLEAR=TRACKPC; LOOP(TOP_IRE(R,C,NRGELC(R,COM),P),TRACKPC(R,P,C)=YES; TRACKPC(R,P,COM)=YES);
  KEEP_FLOF(RPC(R,P,C))$(NOT TRACKPC(RPC)) $= SUM(RPC_IRE(RPC,IE),1)$NRGELC(R,C);
  {arg1}PAR_EOUT({arg2}RTP_VINTYR(R,V,T,P),C)$(KEEP_FLOF(R,P,C)$RP_IRE(R,P)) =
    SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))$RPC_IRE(R,P,C,'IMP') -
    SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S))$RPC_IRE(R,P,C,'EXP');
  KEEP_FLOF(RPC_SPG(TRACKP,C)) = YES;
  OPTION CLEAR=F_VIO,CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=TRACKPG);

*-----------------------------------------------------------------------------
* Levelized cost calculation
*-----------------------------------------------------------------------------
 F=RPT_OPT('NCAP','1');
 LOOP((SYSUC('{sysprefix}LEVCOST'),ANNUAL(SL))$F, Z=F<0; F=1-Z+(F>1);
  NCAP_YES(R,T,P)$(VAR_NCAP.L(R,T,P)*COEF_RTP(R,T,P)$(RP_INOUT(R,P,'OUT')+PRC_PKAF(R,P))=0)=NO;
  PASTSUM(R,T,P)${arg1}PAR_CAPL({arg2}R,T,P) = {arg1}PAR_CAPL({arg2}R,T,P)+SUM(PASTCV,{
        arg1
    }PAR_PASTI({arg2}R,T,P,PASTCV))+1-1;
* Calculate ENV credit
  LOOP(COM_LIM(ENV(R,C),'LO')$Z,TRACKC(R,C)=YES;TRACKP(R,P)$(PRC_MAP(R,'PRE',P)$TOP(R,P,C,'OUT'))=YES);
  TRACKPC(TRACKP(R,P),C)$(NRG(R,C)$TOP(R,P,C,'OUT'))=YES; TRACKC(R,C)$SUM(TRACKPC(R,P,C),1)=YES;
  VDA_EMCB(R,T,C,C)$(NRG(R,C)$TRACKC(R,C)) =
   MIN(SUM(TRACKC(ENV(R,COM)),MIN(0,COM_AGG(R,T,C,COM)*{arg1}PAR_COMBALEM({
        arg2
    }R,T,COM,SL))),
    SUM(P$TRACKPC(R,P,C),
     SUM((VNT(V,T),S)${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))/MAX(MICRO,SUM((TRACKPC(R,P,COM2),VNT(V,T),S)${arg1}F_OUT({
        arg2
    }R,V,T,P,COM2,S),{arg1}F_OUT({arg2}R,V,T,P,COM2,S))) *
     SUM((VNT(V,T),TRACKC(ENV(R,COM)))${arg1}F_OUT({arg2}R,V,T,P,COM,SL),{arg1}F_OUT({
        arg2
    }R,V,T,P,COM,SL)*MIN(0,{arg1}PAR_COMBALEM({arg2}R,T,COM,SL)))) /
    MAX(MICRO,SUM((VNT(V,T),P,S)${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))+SUM(S${arg1}AGG_OUT({arg2}R,T,C,S),{arg1}AGG_OUT({arg2}R,T,C,S))));
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=COEF_CAP; TRACKC(NRG)=NO;
* Credit for aux energy ouputs (ELE+CHP+HPL)
  OPTION RP_PRC < NCAP_YES; TRACKP(RP_PRC(RP))=ELE(RP)+CHP(RP)+HPL(RP);
  TRACKPC(TRACKP(R,P),C)$(TOP(R,P,C,'OUT')$(NOT RPC_PG(R,P,C)*(NRGELC(R,C)+(NOT CHP(R,P))))$NRG(R,C))=YES;
  OPTION TRACKP < TRACKPC;
  IF(Z,COEF_CAP(RTP_VINTYR(R,V,T,P))$TRACKP(R,P)=1-1/(1+SUM(RPCS_VAR(TRACKPC(R,P,C),S),PAR_FLO(R,V,T,P,C,S))/MAX(MICRO,SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,V,T,P,C,S)))));
  IF(F=1,RP_GRP(RPC_PG(RP_PRC,C))$(NOT TRACKPC(RPC_PG))=YES);
* Credit for peak capacity
  LOOP((COM_PEAK(R,CG),COM_GMAP(R,CG,C)),TRACKPG(RP_PRC(R,P),C)$TOP(R,P,C,'OUT')=YES;
    PAR_RTCS(RTCS_VARC(R,T,C,S))=SUM(COM_PKTS(R,CG,TS)$RS_TREE(R,S,TS),{arg1}PAR_PEAKM({
        arg2
    }R,T,CG,TS)/(1+MAX(COM_PKRSV(R,T,C),SUM(COM(CG),COM_PKRSV(R,T,COM))))*RS_FR(R,TS,S))*COM_IE(R,T,C,S));
  OPTION RP_PRC < RPC_PKC; RP_PRC(RP)$(F<2)=NO; TRACKPG(RPC_PG(RP_PRC,C))=NO;
* Cost ratio for vintaged
 {arg1}PAR_NCAPR({arg2}NCAP_YES(R,TT(V),P),SYSUC)$PRC_VINT(R,P) =
   (COEF_RTP(R,V,P)*VAR_NCAP.L(R,V,P) +
    SUM(RTP_VINTYR(R,V,T,P),COEF_PVT(R,T) *
        (SUM(RPM,{arg1}CST_ACTC({arg2}R,V,T,P,RPM)) +
         SUM(TOP(R,P,C,'IN'),(1-COEF_CAP(R,V,T,P)) * ({arg1}CST_FLOC({arg2}R,V,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,V,T,P,C) +
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_IN({arg2}R,V,T,P,C,TS),
                ({arg1}PAR_COMBALEM({arg2}R,T,C,S)+VDA_EMCB(R,T,C,C))*{arg1}F_IN({
        arg2
    }R,V,T,P,C,TS)*RS_FR(R,S,TS))$(NOT TRACKC(R,C)))) +
         SUM(TOP(R,P,C,'OUT')$(NOT TRACKPC(R,P,C)$Z),{arg1}CST_FLOC({arg2}R,V,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,V,T,P,C) -
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_OUT({arg2}R,V,T,P,C,TS),
                ({arg1}PAR_COMBALEM({
        arg2
    }R,T,C,S)*COM_IE(R,T,C,S)+(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))*PAR_RTCS(R,T,C,S)$TRACKPG(R,P,C))*{
        arg1
    }F_OUT({arg2}R,V,T,P,C,TS)*RS_FR(R,S,TS))$(NOT RP_GRP(R,P,C))$F) -
         SUM((RPC_PG(RP_PRC(R,P),C),COM_TS(R,C,S)),NCAP_PKCNT(R,V,P,S)*PAR_RTCS(R,T,C,S)*VAR_NCAP.L(R,V,P)*G_YRFR(R,S)*PRC_CAPACT(R,P)*PRC_ACTFLO(R,V,P,C))))) /
    MAX(MICRO,SUM(RTP_CPTYR(R,V,T,P),COEF_PVT(R,T)*SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,V,T,P,C,S))));
* Cost ratio for non-vintaged
 {arg1}PAR_NCAPR({arg2}NCAP_YES(R,TT(V),P),SYSUC)$(NOT PRC_VINT(R,P)) =
   (COEF_RTP(R,V,P) +
    SUM(RTP_CPTYR(R,V,T,P)$PASTSUM(R,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)/PASTSUM(R,T,P) *
        (SUM(RPM,{arg1}CST_ACTC({arg2}R,T,T,P,RPM)) +
         SUM(TOP(R,P,C,'IN'),(1-COEF_CAP(R,T,T,P)) * ({arg1}CST_FLOC({arg2}R,T,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,T,T,P,C) +
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_IN({arg2}R,T,T,P,C,TS),
                ({arg1}PAR_COMBALEM({arg2}R,T,C,S)+VDA_EMCB(R,T,C,C))*{arg1}F_IN({
        arg2
    }R,T,T,P,C,TS)*RS_FR(R,S,TS))$(NOT TRACKC(R,C)))) +
         SUM(TOP(R,P,C,'OUT')$(NOT TRACKPC(R,P,C)$Z),{arg1}CST_FLOC({arg2}R,T,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,T,T,P,C) -
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_OUT({arg2}R,T,T,P,C,TS),
                ({arg1}PAR_COMBALEM({
        arg2
    }R,T,C,S)*COM_IE(R,T,C,S)+(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))*PAR_RTCS(R,T,C,S)$TRACKPG(R,P,C))*{
        arg1
    }F_OUT({arg2}R,T,T,P,C,TS)*RS_FR(R,S,TS))$(NOT RP_GRP(R,P,C))$F) -
         SUM((RPC_PG(RP_PRC(R,P),C),COM_TS(R,C,S)),NCAP_PKCNT(R,V,P,S)*PAR_RTCS(R,T,C,S)*PASTSUM(R,T,P)*G_YRFR(R,S)*PRC_CAPACT(R,P)*PRC_ACTFLO(R,V,P,C))))) /
    MAX(MICRO,SUM(RTP_CPTYR(R,V,T,P)$PASTSUM(R,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)/PASTSUM(R,T,P)*SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,T,T,P,C,S))));
 OPTION CLEAR=TRACKP,CLEAR=TRACKC,CLEAR=TRACKPC,CLEAR=TRACKPG,CLEAR=VDA_EMCB,CLEAR=PASTSUM,CLEAR=PAR_RTCS,CLEAR=COEF_CAP;
 );
* Fallback of flows to ANNUAL level
 LOOP(ANNUAL(TS)$CARD(UNCD1),
   LOOP(UNCD1(COM_TYPE(CG)),TRACKC(R,C)$COM_TMAP(R,COM_TYPE,C)=RPT_OPT(CG,'3')<0);
   LOOP(UNCD1(NRG_TYPE(U2))$RPT_OPT(U2,'3'),TRACKC(R,C)$NRG_TMAP(R,NRG_TYPE,C)=RPT_OPT(U2,'3')<0);
   RVTPC(R,V,T,P,C)$TRACKC(R,C) $= SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),STOA(S));
   F_IOS(RVTPC,TS) = SUM(S${arg1}F_IN({arg2}RVTPC,S),{arg1}F_IN({arg2}RVTPC,S));
   {arg1}F_IN({arg2}RVTPC,S) = 0;  {arg1}F_IN({arg2}RVTPC,S) $= F_IOS(RVTPC,S);
   OPTION CLEAR=RVTPC,CLEAR=F_IOS;
   RVTPC(R,V,T,P,C)$TRACKC(R,C) $= SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),STOA(S));
   F_IOS(RVTPC,TS) = SUM(S${arg1}F_OUT({arg2}RVTPC,S),{arg1}F_OUT({arg2}RVTPC,S));
   {arg1}F_OUT({arg2}RVTPC,S) = 0; {arg1}F_OUT({arg2}RVTPC,S) $= F_IOS(RVTPC,S);
   OPTION CLEAR=TRACKC,CLEAR=RVTPC,CLEAR=F_IOS;
 );
"""
