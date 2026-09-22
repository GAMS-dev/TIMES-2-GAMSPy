# resloadc_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * ResLoadC.vda - define residual load curve equations
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from utils.macros import macro_config as macro

# from core.cal_nored_red import cal_nored_red
# from core.cal_red_red import cal_red_red

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


# dummy functions
def cal_nored_red(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    def_rtp_ffcs: bool = False,
    sow: str = "",
    var: str = "",
) -> str:
    return ""


def cal_red_red(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
    pgprim: str = "",
    def_rtp_ffcs: bool = False,
    sow: str = "",
    var: str = "",
) -> str:
    return ""


class ResloadcVda(GamsClass):
    """Translation unit for resloadc.vda."""

    # Instance attributes
    module_name: str = "resloadc_vda"
    gams_source: str = "resloadc.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        if not len(self.arg1):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
  SET RLDC / RL-DISP /, ITEM / RL-NDIS, RL-CHP, RL-ROR, RL-SOL, RL-WIND, RL-THMIN, RL-TP /;
  SET GR_RLDC(R,LL);
  SET RLDBD(LIM) / UP /;
  SET GR_RLGT(R,P,ITEM);
  PARAMETER GR_THBND(R,LL,P,LIM);
  PARAMETER GR_TP(R,BD) / (SET.R).UP INF /;
""",
            )
            self.tc.enqueue(self.preparations)
            self.include(
                FillparmGms(
                    self.tc,
                    self.env.fork(),
                    FillparmGmsConfig(
                        arg1=g.gr_thmin,
                        arg2=(g.r,),
                        arg3=(g.p,),
                        arg4=("0",) * 5,
                        arg5=g.t,
                        arg6=g.Rtp[g.r, g.t, g.p],
                        arg7=Number(0),
                    ),
                )
            )
        elif self.arg1.upper() == "COEF":
            self.tc.enqueue(self.coef)
        elif self.arg1.upper() == "EQUA":
            self.tc.enqueue(self.equa, vas=self.env.vas, sow=self.env.sow)
            if self.env.cal_red == "cal_nored.red":
                cal_red_code = cal_nored_red(
                    arg1="C",
                    arg2="COM",
                    arg3="TS",
                    arg4="P",
                    arg5="T",
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                    sow=self.env.sow,
                    var=self.env.var,
                )
            else:
                cal_red_code = cal_red_red(
                    arg1="C",
                    arg2="COM",
                    arg3="TS",
                    arg4="P",
                    arg5="T",
                    pgprim=self.env.pgprim,
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                    sow=self.env.sow,
                    var=self.env.var,
                )
            rts = macro.rts(s="S", g=self.tc, env=self.env)
            rts_ts = macro.rts(s="TS", g=self.tc, env=self.env)
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
*-----------------------------------------------------------------------
* Define the residual load as the sum of dispatchable production plus net storage output
  {self.env.eq}_RL_LOAD(GR_RLDC({self.env.r_t}),{rts}{self.env.swt})$FINEST(R,S)..

* Dispatchable production
  SUM(TOP(R,P,C,'OUT')$(NRG_TMAP(R,'ELC',C)$GR_GENMAP(R,P,'RL-DISP')),
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS))$RS_FR(R,S,TS),
         {cal_red_code}
         * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")}))) +
  SUM(RLDC('RL-THMIN'),{self.env.var}_RLD(R,T,S,RLDC{self.env.sow})*G_YRFR(R,S)) -
* Net storage input
  SUM(TOP(RPC_STG(R,P,C),IO)$NRG_TMAP(R,'ELC',C),
    SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),
     ({self.env.var}_SIN(R,V,T,P,C,TS {self.env.sow})$IPS(IO)-{self.env.var}_SOUT(R,V,T,P,C,TS {self.env.sow})*STG_EFF(R,V,P)$(NOT IPS(IO)))*RS_FR(R,S,TS))) -
* Curtailment
  SUM(RHS_COMBAL(R,T,C,TS)$(RS_FR(R,S,TS)$NRG_TMAP(R,'ELC',C)$GR_RLDC(R,'0')),
    ({self.env.var}_COMNET(R,T,C,TS{self.env.sow})/COM_IE(R,T,C,TS)*RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")}))$(NOT SUM(COM$COM_AGG(R,T,C,COM),1)))

  =E=  {self.env.var}_RLD(R,T,S,'RL-DISP'{self.env.sow})*G_YRFR(R,S);

*-----------------------------------------------------------------------
* Total levels of generation by group
  {self.env.eq}_RL_NDIS(GR_RLDC({self.env.r_t}),{rts},RLDC{self.env.swt})$(FINEST(R,S)$GR_VARGEN(R,'ANNUAL',RLDC,'FX'))..

  SUM(TOP(R,P,C,'OUT')$(NRG_TMAP(R,'ELC',C)$GR_RLGT(R,P,RLDC)),
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS))$RS_FR(R,S,TS),
         {cal_red_code}
         * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")})))
  =E=  {self.env.var}_RLD(R,T,S,RLDC {self.env.sow})*G_YRFR(R,S);
*-----------------------------------------------------------------------
* Available storage capacity must be at least thermal min minus residual load with lower variation
  {self.env.eq}_RL_STCAP(GR_RLDC({self.env.r_t}),{rts}{self.env.swt})$FINEST(R,S)..

* Daynite storage capacity
  SUM(TOP(RPC_STG(PRC_CAP(R,P),C),'OUT')$(PRC_TS(R,P,S)$NRG_TMAP(R,'ELC',C)), PRC_CAPACT(R,P) * RS_STGPRD(R,S) *
     SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P) * PRC_ACTFLO(R,V,P,C) *
       SMIN(TS_MAP(R,TS,S)$COEF_AF(R,V,T,P,TS,'UP'),COEF_AF(R,V,T,P,TS,'UP') / RS_FR(R,S,TS) *
         PROD(TS_GROUP(R,TSL,TS)$RPS_CAFLAC(R,P,TS,'UP'), 1 / RS_STGPRD(R,S) / STG_EFF(R,V,P) *
           (NCAP_AFCS(R,V,P,C,TS)+PROD(COM_TMAP(R,COM_TYPE(CG),C)$NCAP_AFCS(R,V,P,CG,TS),NCAP_AFCS(R,V,P,CG,TS))$(NOT NCAP_AFCS(R,V,P,C,TS))))) *
       ({macro.VAR_NCAP(self.env.varv, "R", "V", "P", self.env.sws)}$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V){self.env.rcapsub})))

  =G=

* Thermal min capacity - residual load
  {self.env.var}_RLD(R,T,S,'RL_THMIN'{self.env.sow}) - {self.env.var}_RLD(R,T,S,'RL-DISP'{self.env.sow}) +
* Plus lower variation
  SUM((RLDC,BDNEQ(BD))$(DIAG('RL-DISP',RLDC)=DIAG('LO',BD)), {self.env.var}_RLD(R,T,S,RLDC{self.env.sow}) * GR_VARGEN(R,S,RLDC,BD));

*-----------------------------------------------------------------------
* Available dispatchable plus storage output capacity must be at least residual load upper variation
  {self.env.eq}_RL_PKCAP(GR_RLDC({self.env.r_t}),{rts}{self.env.swt})$FINEST(R,S)..

* Dispatchable capacity
  SUM(GR_RLGT(PRC_CAP(R,P),'RL-DISP'), PRC_CAPACT(R,P) *
     SUM(V$COEF_CPT(R,V,T,P), COEF_CPT(R,V,T,P) * SMAX(RPC_PG(R,P,C)$NRG_TMAP(R,'ELC',C),PRC_ACTFLO(R,V,P,C)) * SUM(PRC_TS(R,P,TS)$RS_FR(R,S,TS),COEF_AF(R,V,T,P,S,'UP')) *
         ({macro.VAR_NCAP(self.env.varv, "R", "V", "P", self.env.sws)}$TT(V) + NCAP_PASTI(R,V,P)$PYR(V){self.env.rcapsub}))) +
* Storage output capacity
  SUM(TOP(RPC_STG(PRC_CAP(R,P),C),'OUT')$(PRC_TS(R,P,S)$NRG_TMAP(R,'ELC',C)), PRC_CAPACT(R,P) * RS_STGPRD(R,S) *
     SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P) * COEF_AF(R,V,T,P,S,'UP') * PRC_ACTFLO(R,V,P,C) * STG_EFF(R,V,P) *
       PROD(L('N'),
         PROD(TS_GROUP(R,TSL,S)$RPS_CAFLAC(R,P,S,'UP'), 1 / RS_STGPRD(R,S) / STG_EFF(R,V,P) *
           (NCAP_AFCS(R,V,P,C,S)+PROD(COM_TMAP(R,COM_TYPE(CG),C)$NCAP_AFCS(R,V,P,CG,S),NCAP_AFCS(R,V,P,CG,S))$(NOT NCAP_AFCS(R,V,P,C,S))))) *
       ({macro.VAR_NCAP(self.env.varv, "R", "V", "P", self.env.sws)}$TT(V) + NCAP_PASTI(R,V,P)$PYR(V){self.env.rcapsub})))

  =G=

* Residual load plus upper variation
  {self.env.var}_RLD(R,T,S,'RL-DISP'{self.env.sow}) +
  SUM((RLDC,BDNEQ(BD))$(DIAG('RL-DISP',RLDC)=DIAG('UP',BD)), {self.env.var}_RLD(R,T,S,RLDC{self.env.sow}) * GR_VARGEN(R,S,RLDC,BD));

*-----------------------------------------------------------------------
* Aggregate thermal min level
  {self.env.eq}_RL_THMIN(GR_RLDC({self.env.r_t}),{rts_ts},BDNEQ {self.env.swt})$((BDLOX(BDNEQ)+RLDC('RL-THMIN'))$FINEST(R,TS))..

  {self.env.var}_RLD(R,T,TS,'RL_THMIN'{self.env.sow})*BDSIG(BDNEQ) +
  {self.env.var}_RLD(R,T,TS,'RL-THMIN'{self.env.sow})*BDUPX(BDNEQ)

  =G=

* Aggregate target load level according to THMIN
  SUM(GR_RLGT(PRC_CAP(R,P),'RL-THMIN'), PRC_CAPACT(R,P) * (GR_THBND(R,T,P,'FX') +
      SUM((RTP_VINTYR(R,V,T,P),PRC_TS(R,P,S))$RS_FR(R,TS,S),SMAX(RPC_PG(R,P,C)$NRG_TMAP(R,'ELC',C),PRC_ACTFLO(R,V,P,C)) *
        (SUM(BD$BDNEQ(BD),GR_THBND(R,T,P,BD))+SUM(TS_ANN(S,SL),ACT_UPS(R,V,P,SL,'FX'))$(NOT GR_THMIN(R,T,P))) *
        (SUM(MODLYEAR(K)$(COEF_CPT(R,K,T,P)$(DIAG(V,K)>=1$PRC_VINT(R,P))),COEF_CPT(R,MODLYEAR,T,P) *
          ({macro.VAR_NCAP(self.env.varm, "R", "K", "P", self.env.sws)}$TT(K)+NCAP_PASTI(R,K,P)$PYR(K){self.env.rcapsbm})){macro.upscaps.render()}))))$BDLOX(BDNEQ);
""",
            )

    def preparations(self: ResloadcVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* FX - constant; LO - proportional to capacity; UP - proportional to online capacity
* Preparations
  GR_RLDC(R,'0') $=SUM((S,RLDC,BD)$GR_VARGEN(R,S,RLDC,BD),1);
  GR_TP(R,BD)$=GR_VARGEN(R,'ANNUAL','RL-TP',BD); GR_TP(R,BD)$=GR_TP(R,'FX'); GR_VARGEN(R,S,'RL-TP',BD)=0;
  OPTION CLEAR=UNCD1; GR_RLDC(R,T(TT+1))$((YEARVAL(T)>=GR_TP(R,'LO'))$(YEARVAL(T)<=GR_TP(R,'UP'))) $= GR_RLDC(R,'0');
  LOOP((R,S,ITEM,BD)$GR_VARGEN(R,S,ITEM,BD),UNCD1(ITEM)=YES); RLDC(UNCD1) = YES;
  RLDBD(BD)$=NOT RLDC('RL-THMIN'); GR_VARGEN(R,S,'RL-THMIN',BD) = 0;
""",
        )

    def coef(self: ResloadcVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Preprocessing
  TRACKPC(RPC_PG(RP_STD(R,P),C))$(TOP(R,P,C,'OUT')$NRG_TMAP(R,'ELC',C)) = YES;
  OPTION TRACKP<TRACKPC; GR_THMIN(R,LL,P)$(NOT TRACKP(R,P))=0;
* Set generation types
  GR_RLGT(TRACKP(RP),RLDC)$=GR_GENMAP(RP,RLDC);
  OPTION RP_UPL < ACT_UPS, RP_PRC < GR_THMIN;
  GR_RLGT(RP_PRC(RP),'RL-DISP')=YES;
  LOOP(RLDC$(NOT SAMEAS('RL-NDIS',RLDC)),GR_RLGT(RP,'RL-NDIS')$GR_RLGT(RP,RLDC)=NO);
  RP_PRC(RP)$GR_RLGT(RP,'RL-DISP')$=RP_UPL(RP,'FX');
  GR_RLGT(RP_PRC(RP),'RL-THMIN')=YES;
  GR_GENMAP(RP_PRC,'RL-DISP')=NOT RLDC('RL-THMIN'); OPTION CLEAR=RP_PRC;
  RP_PRC(TRACKP(R,P))$SUM(TOP(R,P,C,'IN')$NRG_TMAP(R,'ELC',C),1) = YES;
  RP_PRC(CHP)=NO; TRACKP(RP_PRC)=NO;
  GR_RLGT(TRACKP(RP),'RL-NDIS')$(NOT SUM(RLDC$GR_RLGT(RP,RLDC),1)) = YES;
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=RP_PRC;
* Process thermal minimum
  GR_THBND(RTP,'FX')$((GR_THMIN(RTP)<0)$GR_THMIN(RTP)) = -GR_THMIN(RTP);
  GR_THBND(RTP,'LO')$((GR_THMIN(RTP)<1)$GR_THMIN(RTP)) = MAX(0,GR_THMIN(RTP)+1-1);
  GR_THBND(RTP,'UP')$((GR_THMIN(RTP)>=1)$GR_THMIN(RTP)) = 1/GR_THMIN(RTP);
* Levelize variations
  FOR(Z=CARD(TSLVL)-2 DOWNTO 0,
   LOOP((ANNUAL(TS(TSL-Z)),TS_GROUP(R,TSL,SL)),
     GR_VARGEN(FINEST(R,S),RLDC,BDNEQ(BD))$((NOT GR_VARGEN(R,S,RLDC,BD))$RS_BELOW(R,SL,S)) $= GR_VARGEN(R,SL,RLDC,BD)));
* Ensure curtailment is accounted
  GR_RLDC(R,'0')$GR_VARGEN(R,'ANNUAL','RL-DISP','FX') = NO;
  LOOP(R$GR_RLDC(R,'0'),
    RHS_COMBAL(RTCS_VARC(GR_RLDC(R,T),C,S))$(COM_LIM(R,C,'LO')$NRG_TMAP(R,'ELC',C)) = YES;
    RCS_COMBAL(RHS_COMBAL(GR_RLDC(R,T),C,S),'FX')$NRG_TMAP(R,'ELC',C) = YES);
  GR_VARGEN(R,ANNUAL,RLDC,'FX') = 1-DIAG('RL-DISP',RLDC);
* Move to ACT_UPS when needed
  LOOP(RLDBD(BDNEQ(BD)),ACT_UPS(RTP,ANNUAL(S),'FX')$GR_THBND(RTP,BD)=MAX(GR_THBND(RTP,BD),ACT_UPS(RTP,S,'FX'));
    GR_THBND(R,LL,P,BD)$RP_UPL(R,P,'FX')=0)
  IF(RLDBD('FX'),FLO_BND(RTP(R,T,P),C,S,'LO')$(RPC_PG(R,P,C)$NRG_TMAP(R,'ELC',C)$PRC_TS(R,P,S)$GR_THBND(RTP,'FX')) =
     MAX(FLO_BND(RTP,C,S,'LO'),GR_THBND(RTP,'FX')*PRC_CAPACT(R,P)*G_YRFR(R,S)));
  OPTION GR_THMIN < GR_THBND;
""",
        )

    def equa(self: ResloadcVda, vas: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Remove cycling if lower bounds are per nominal capacity
  RPS_UPS(R,P,S)$SUM(RTP(R,V,P)$GR_THBND(RTP,'LO'),1)=NO;
* Set bounds
  {vas}_RLD.LO(R,T,S,'RL-DISP'{sow})=-INF;
""",
        )
