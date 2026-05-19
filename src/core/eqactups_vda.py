# eqactups_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTUPS - implements the linear dispatching equations
# *   arg1 - MX control
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.pp_lvlfc_mod import pp_lvlfc_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqactupsVda(GamsClass):
    """Translation unit for eqactups.vda."""

    # Instance attributes
    module_name: str = "eqactups_vda"
    gams_source: str = "eqactups.vda."

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
        self.tc.enqueue(self.set_indicators, pgprim=self.env.pgprim)

        self.env.set_scoped(
            "capon",
            f"(COEF_CPT(R,V,T,P)*({self.env.varv}_NCAP(R,V,P{self.env.sws})$T(V)+NCAP_PASTI(R,V,P){self.env.rcapsub}))$PRC_VINT(R,P)+{self.env.var}_CAP(R,T,P{self.env.sow})$RP_UX(R,P)",
        )
        self.env.set_scoped(
            "mx",
            f"SUM(RVP_KMAP(R,V,P,MODLYEAR(K)),COEF_VNT(R,T,P,K)*({self.env.varm}_NCAP(R,K,P{self.env.sws})$T(K)+NCAP_PASTI(R,K,P){self.env.rcapsbm}))",
        )
        self.env.set_scoped(
            "tmp",
            f"$(NOT RP_UX(R,P))+{self.env.var}_CAP(R,T,P{self.env.sow})$RP_UX(R,P){self.env.upscaps}",
        )

        self.equation_capload(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            capon=self.env.capon,
            upscaps=self.env.upscaps,
            arg1=self.arg1,
        )
        self.equation_acttramp(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            mx=self.env.mx,
            tmp=self.env.tmp,
        )
        self.equation_actups(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            mx=self.env.mx,
            tmp=self.env.tmp,
        )
        self.equation_actupc(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            capon=self.env.capon,
            upscaps=self.env.upscaps,
        )
        self.equation_actpl(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            mx=self.env.mx,
            tmp=self.env.tmp,
        )
        self.equation_actrmpc(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
        )
        self.equation_stgccl(
            r_v_t=self.env.r_v_t,
            mx=self.env.mx,
            var=self.env.var,
            sow=self.env.sow,
            swx=self.env.swx,
            swtx=self.env.swtx,
        )

        if self.env.obmac.upper() == "YES":
            # TODO: Macro, check implication.
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""$macro var_sift(v,s,l) {self.env.var}_udp(r,v,t,p,s,l{self.env.sow})*prc_capact(r,p)*rs_stgprd(r,s)/8760""",
            )

        self.equation_slsift(
            eq=self.env.eq,
            r_t=self.env.r_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            pgprim=self.env.pgprim,
        )

    def set_indicators(self: EqactupsVda, pgprim: str) -> None:
        m = self.tc.container
        RpUpl = m["RP_UPL"]
        RpPl = m["RP_PL"]
        act_cstrmp = m["ACT_CSTRMP"]

        # Set indicators
        # IF(CARD(RP_UPL)+CARD(RP_PL)+CARD(ACT_CSTRMP),
        if RpPl.number_records + RpUpl.number_records + act_cstrmp.number_records:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
  OPTION CLEAR=UNCD7;
  AFUPS(R,T,P,S)$((NOT RPS_CAFLAC(R,P,S,'UP'))$PRC_TS(R,P,S)) $= AFS(R,T,P,S,'UP')$RP_UPL(R,P,'FX'); AFS(AFUPS,BD)=NO;
  RPS_UPS(R,P,S)$((STOAL(R,S)<2+1$RP_UPR(R,P,'N'))$RP_UPL(R,P,'FX')) = SUM(PRC_TS(R,P,TS)$RS_BELOW(R,S,TS),RS_BELOW1(R,S,TS) OR STOA(S));
  RP_UX(RP)$(NOT PRC_VINT(RP))$=RP_UPL(RP,'FX'); RTP_VARP(RTP(R,T,P))$RP_UX(R,P)=YES;
  COEF_AF(R,T,T,P,S,'UP')$AFUPS(R,T,P,S) $= NCAP_AF(R,T,P,S,'UP')$RP_UX(R,P);
* Check for startup costs
  UNCD7(R,LL--ORD(LL),P,TSL,RDCUR(R,CUR),'UP') $= ACT_CSTUP(R,LL,P,TSL,CUR);
  UNCD7(R,LL--ORD(LL),P,BD,RDCUR(R,CUR),'N') $= ACT_CSTRMP(R,LL,P,BD,CUR);
  LOOP(UNCD7(R,LL,P,ITEM,R,CUR,L),RP_UPS(R,P,TSL(ITEM),L)$(TSLVLNUM(TSL)$RP_UPL(R,P,'FX')>1)=YES; RPC_CUR(R,P,'{pgprim}',CUR)=YES);
  RP_UPS(RP,TSL,L)$SUM(PRC_TSL(RP,TSLVL)$(ORD(TSL)>ORD(TSLVL)),1)=NO;
  RPS_UPS(RP,S)$SUM(RP_UPS(PRC_TSL(RP,TSL),L),1)=NO;
  RPS_UPS(R,P,S) $= SUM(RP_UPS(R,P,TSL,L)$TS_GROUP(R,TSL,S),1);
  RP_UPS(R,P,TSL,LNX(L))$RP_UPS(R,P,TSL,'UP') = SUM(RP_UPS(R,P,TSLVL,BD),RLUP(R,TSLVL,TSL)$BD(L)+RLUP(R,TSL,TSLVL)$IPS(L));
  RP_UPS(R,P,TSL,'FX')$(SUM(RP_UPS(PRC_TSL(R,P,TSLVL),L),RLUP(R,TSLVL,TSL))$RP_UPR(R,P,'UP'))=YES;
* Check partial loads
  LOOP(UNCD7(R,LL,P,TSL(ANNUAL),R,CUR,L),RP_UPS(R,P,TSL,L)=YES; RP_PL(R,P,'N')=NOT RP_PL(R,P,L));
  ACT_LOSPL(RTP(R,V,P),BDNEQ(BD))$((ACT_LOSPL(RTP,BD)<=0)$RP_PL(R,P,'N'))=MAX(.1+.5$BDUPX(BD),ACT_MINLD(RTP));
""",
            )

            pp_lvlfc_mod(
                module=self,
                arg1="ACT_UPS",
                arg2="P",
                arg3="PRC_TS",
                arg4="',BD'",
                arg5=",'','',''",
                arg6="ALL_TS",
                arg7="V",
                arg8="RTP(R,V,P)",
                arg9="0",
                arg10="",
                arg11="N",
                arg12="",
            )

            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
  RTP_PL(RTP(R,V,P))$((ACT_LOSPL(RTP,'LO')=ACT_MINLD(RTP))$RP_UPL(R,P,'FX'))$=RP_PL(R,P,'N');
* Check for cycling limits
  RP_UPC(R,P,TSL,'N')$RP_UPR(R,P,'N') $= SUM(RP_UPS(PRC_TSL(R,P,TSLVL),L),RLUP(R,TSLVL,TSL));
  RP_UPC(PRC_TSL(RP,TSL),BDNEQ(BD))$RP_UPS(RP,TSL,'UP') $= RP_UPR(RP,BD));
""",
            )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION RP_UPR < ACT_CSTRMP;""",
        )

    def equation_capload(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
        capon: str,
        upscaps: str,
        arg1: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}_CAPLOAD(RTP_VINTYR({r_v_t},P),S,BDNEQ(BD){swt})$AFUPS(R,T,P,S)..

* activity bounded from LO/UP
   {var}_ACT(R,V,T,P,S{sow})*BDSIG(BD)  =G=  {var}_UPS(R,V,T,P,S,'FX'{sow})$RTP_PL(R,V,P)$BDLOX(BD) +

* fraction of capacity - vintaged or not
   ({capon}{upscaps}) * MIN(COEF_AF{arg1}(R,V,T,P,S,'UP')*BDSIG(BD),SUM(TS_ANN(S,TS)$(NOT RTP_PL(R,V,P)),ACT_UPS(R,V,P,TS,'FX'))$BDLOX(BD)) *
   PRC_CAPACT(R,P) * G_YRFR(R,S);
""",
        )

    def equation_acttramp(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
        mx: str,
        tmp: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}_ACTRAMP(RTP_VINTYR({r_v_t},P),RTS(S),BDNEQ(BD){swt})$(SUM(TS_ANN(S,TS)$ACT_UPS(R,V,P,TS,BD),1)$PRC_TS(R,P,S)$RP_UPL(R,P,BD))..

* max fraction of capacity
   SUM(RS_PREV(R,S,TS)$PRC_TS(R,P,TS),PRC_CAPACT(R,P)*SUM(TS_ANN(S,SL),ACT_UPS(R,V,P,SL,BD)) *
     ({mx}{tmp} + (({var}_UPS(R,V,T,P,S,'N'{sow})-{var}_UPS(R,V,T,P,TS,'N'{sow}))$BDLOX(BD))$RPS_UPS(R,P,S)) +

* dynamic ramp limits
     RS_STGPRD(R,S)*2/(G_YRFR(R,S)+G_YRFR(R,TS))/8760 *
     ({var}_ACT(R,V,T,P,S{sow})/G_YRFR(R,S)-{var}_ACT(R,V,T,P,TS{sow})/G_YRFR(R,TS) +
      (({var}_UPS(R,V,T,P,S,'N'{sow})-{var}_UPS(R,V,T,P,TS,'N'{sow}))*PRC_CAPACT(R,P)*ACT_MINLD(R,V,P))$RPS_UPS(R,P,S))*BDSIG(BD))

    =G= 0;
""",
        )

    def equation_actups(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
        mx: str,
        tmp: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}E_ACTUPS(RTP_VINTYR({r_v_t},P),TSL,L(BND_TYPE),RTS(S){swt})$(TS_GROUP(R,TSL,S)$RP_UPS(R,P,TSL,L))..

* start-up/shut-down capacity
   (SUM(RS_PREV(R,S,TS),{var}_UPS(R,V,T,P,S,'N'{sow})-{var}_UPS(R,V,T,P,TS,'N'{sow})-SUM(BD,{var}_UPS(R,V,T,P,S,BD{sow})*BDSIG(BD)))$STOA(S) +
    SUM(ANNUAL(S)$RP_PL(R,P,'N'),{var}_UPS(R,V,T,P,S,L{sow})-SUM(PRC_TS(R,P,TS),{var}_UPS(R,V,T,P,TS,'FX'{sow}))))$(BDSIG(L)<0) +
   SUM(BDLOX(BD(L)),{mx}{tmp}-{var}_UDP(R,V,T,P,S,'FX'{sow})-{var}_UPS(R,V,T,P,S,'FX'{sow})$RP_UPL(R,P,'FX'))

    =E= 0;

*-----------------------------------------------------------------------

  {eq}L_ACTUPS(RTP_VINTYR({r_v_t},P),TSL,LNX(L),RTS(S){swt})$(TS_GROUP(R,TSL,S)$RP_UPS(R,P,TSL,L))..

* balance at higher level
   ({var}_UPS(R,V,T,P,S,L{sow})-SUM(RS_BELOW1(R,TS,S),{var}_UPS(R,V,T,P,TS,'FX'{sow})))$IPS(L) +
   ({var}_UPS(R,V,T,P,S,L{sow})-SUM(RS_BELOW1(R,S,TS),{var}_UPS(R,V,T,P,TS,'UP'{sow})))$BD(L)

    =L= 0;


""",
        )

    def equation_actupc(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
        capon: str,
        upscaps: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}L_ACTUPC(RTP_VINTYR({r_v_t},P),TSL,L,RTS(S){swt})$(TS_GROUP(R,TSL,S)$RP_UPC(R,P,TSL,L))..

* max number of cycles
   (SUM(RS_BELOW1(R,S,SL),{var}_UPS(R,V,T,P,SL,'UP'{sow})) - ({capon}{upscaps})*ACT_TIME(R,T,P,L))$IPS(L) +
* min UP/LO hours
   SUM(BD(L),
     SUM((RS_UP(R,S,JS),RJ_SL(R,JS,SL)),{var}_UPS(R,V,T,P,SL,L{sow})$(RS_MODUS(R,S,JS,SL) < ACT_TIME(R,T,P,L)/8760)) -
     SUM(RS_UP(R,S,J,TS),{var}_UPS(R,V,T,P,TS,'FX'{sow}))$BDUPX(BD)-{var}_UPS(R,V,T,P,S,'N'{sow})*BDSIG(L))

    =L= 0;


""",
        )

    def equation_actpl(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
        mx: str,
        tmp: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}_ACTPL(RTP_VINTYR({r_v_t},P),RTS(S){swt})$(PRC_TS(R,P,S)$RP_PL(R,P,'N'))..

* partial loads
   {var}_UPS(R,V,T,P,S,'FX'{sow})  =G=

   (({mx}{tmp})*PRC_CAPACT(R,P)*G_YRFR(R,S) * (ACT_LOSPL(R,V,P,'UP')+ACT_LOSPL(R,V,P,'LO')*(1-ACT_LOSPL(R,V,P,'UP'))) -
    {var}_ACT(R,V,T,P,S{sow})) / (ACT_LOSPL(R,V,P,'UP')*(1/ACT_LOSPL(R,V,P,'LO')-1)) +
   sum((rp_upt(r,p,upt,bd),PRC_TSL(R,P,TSL))$DP_UNS(R,V,T,P,TSL,'IN','N'),
     sum((rs_up(r,s,js),rj_sl(r,js,sl))$(MOD((RS_HR(r,s)-RS_HR(r,sl))*BDSIG(bd)+G_YRFR(r,sl)/RS_STGPRD(r,s)/2+2/G_CYCLE(tsl),1/G_CYCLE(tsl))<ACT_SDTIME(r,v,p,upt,bd)/8760*(1.001)),
       MIN(1,MOD((RS_HR(r,s)-RS_HR(r,sl))*BDSIG(bd)+(G_YRFR(r,sl)-G_YRFR(r,s))/2/RS_STGPRD(r,s)+2/G_CYCLE(tsl),1/G_CYCLE(tsl))/(ACT_SDTIME(r,v,p,upt,bd)/8760))*(1-DIAG(S,SL))*DP_PSUD(r,v,p,upt,bd) *
       ({var}_upt(r,v,t,p,sl,upt{sow})$bdupx(bd) + {var}_ups(r,v,t,p,sl,bd{sow})$bdlox(bd))) * PRC_CAPACT(r,p)*G_YRFR(r,s)*ACT_MINLD(r,v,p))$DP_LOSD(r,v,p);

""",
        )

    def equation_actrmpc(
        self: EqactupsVda,
        eq: str,
        r_v_t: str,
        swt: str,
        var: str,
        sow: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------

  {eq}_ACTRMPC(RTP_VINTYR({r_v_t},P),TS(S--RS_STG(R,S)){swt})$(PRC_TS(R,P,S)$RP_STD(R,P)$SUM(RP_UPR(R,P,BD),1))..

* ramping costs
   ({var}_ACT(R,V,T,P,TS{sow})/G_YRFR(R,TS)-{var}_ACT(R,V,T,P,S{sow})/G_YRFR(R,S))/PRC_CAPACT(R,P) =E=
   SUM(BDNEQ(BD),{var}_UDP(R,V,T,P,S,BD{sow})*BDSIG(BD))-ACT_MINLD(R,V,P)*({var}_UPS(R,V,T,P,TS,'N'{sow})-{var}_UPS(R,V,T,P,S,'N'{sow}))$RPS_UPS(R,P,S);


""",
        )

    def equation_stgccl(
        self: EqactupsVda,
        r_v_t: str,
        mx: str,
        var: str,
        sow: str,
        swx: str,
        swtx: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""

  EQL_STGCCL(RTP_VINTYR({r_v_t},P){swx})$({swtx}SUM(RPS_STG(R,P,S)$COEF_AFUPS(R,V,P,S),1)$STG_MAXCYC(R,V,P)$RP_STG(R,P))..

* Storage cycling penalty
   ({mx}+{var}_UPS(R,V,T,P,'ANNUAL','UP'{sow}))/EXP(PRC_SC(R,P))*SMAX(RPS_STG(R,P,S),COEF_AFUPS(R,V,P,S))*PRC_CAPACT(R,P) =G=
   SUM((TOP(RPC_STG(R,P,C),'OUT'),RPCS_VAR(R,P,C,S)),{var}_SOUT(R,V,T,P,C,S{sow})/PRC_ACTFLO(R,V,P,C))*NCAP_TLIFE(R,V,P) / STG_MAXCYC(R,V,P);

""",
        )

    def equation_slsift(
        self: EqactupsVda,
        eq: str,
        r_t: str,
        swt: str,
        var: str,
        sow: str,
        pgprim: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Load Shifting
  {eq}_SLSIFT(RTP({r_t},P),COM,RTS(S),LNX,L{swt})$((PRC_TS(R,P,S)$ACT_TIME(RTP,L)+BD(LNX)$LNX(L))$RPS_PRCTS(R,P,S)$RPC_LS(R,P,COM))..

  SUM(RTP_VINTYR(R,V,T,P),
* Limit net and gross sifting flows
    SUM(IPS(L)$(PRC_TS(R,P,S)+YES$STG_SIFT(RTP,'{pgprim}',S)+ANNUAL(S)$ACTCG(COM)),
      SUM(PRC_TS(R,P,TS)$RS_BELOW1(R,S,TS),{var}_ACT(R,V,T,P,TS{sow}))$STG_SIFT(RTP,'{pgprim}',S) +
      SUM((TOP(RPC_STG(R,P,C),'OUT'),RPCS_VAR(R,P,C,TS)),{var}_SOUT(R,V,T,P,C,TS{sow}))$ANNUAL(S)$ACTCG(COM) +
      ({var}_SIN(R,V,T,P,COM,S{sow}) + {var}_ACT(R,V,T,P,S{sow}))$PRC_TS(R,P,S) + {var}_SOUT(R,T,T,P,'{pgprim}',S{sow}) -
      SUM((TOP(RPC_STG(R,P,C),'OUT'),RTCS_VARC(RTC(R,T,C),TS))$RS_FR(R,S,TS),(STG_SIFT(RTP,C,TS)$(PRC_TS(R,P,S)+ANNUAL(S)$ACTCG(COM))+STG_SIFT(RTP,'{pgprim}',S))*{var}_COMPRD(R,T,C,TS{sow})/COM_IE(RTC,TS)*RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)))) -
* Get net sifting, force zero shifting at seasonal level
    SUM(BD(L)$LNX(L),
      (SUM((TOP(RPC_STG(R,P,C),'OUT'),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),{var}_SOUT(R,V,T,P,C,TS{sow})*RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))) -
       SUM(TOP(RPC_STG(R,P,C),'IN'),{var}_SIN(R,V,T,P,C,S{sow}))-({var}_ACT(R,V,T,P,S{sow})-{var}_SIN(R,V,T,P,COM,S{sow})))$PRC_TS(R,P,S) +
      SUM(PRC_TS(R,P,TS)$RS_BELOW1(R,S,TS),{var}_SIN(R,V,T,P,COM,TS{sow})-{var}_ACT(R,V,T,P,TS{sow}))$(SUM(LIM$ACT_TIME(RTP,LIM),1)=0)) +
* Asymmetric advance or delay
    SUM(BDNEQ(BD(L))$ACT_TIME(RTP,'LO'),VAR_SIFT(V,S,L)+VAR_SIFT('0',S,L) -
       SUM((RS_UP(R,S,JS),RJ_SL(R,JS,SL)),{var}_UPS(R,V,T,P,SL,L{sow})$(MOD((RS_HR(R,S)-RS_HR(R,SL)+G_YRFR(R,S)/RS_STGPRD(R,S)/9)*BDSIG(L)+1/JS_CCL(R,JS),1/JS_CCL(R,JS))<ACT_TIME(RTP,L)/8760))))$BD(LNX)
  =E=
  SUM(RTP_VINTYR(R,V,T,P),
* Balance for sifting (LO=advance, UP=delay)
    SUM(TS(S--RS_STG(R,S)),SUM(BDNEQ(BD),(VAR_SIFT(V,TS,BD)-VAR_SIFT(V,S,BD))*BDSIG(BD))+{var}_SIN(R,V,T,P,COM,S{sow})-{var}_ACT(R,V,T,P,S{sow}))$(BDSIG(L)<0) +
    (SUM(BDNEQ(BD),{var}_UPS(R,V,T,P,S,BD{sow}))-{var}_SIN(R,V,T,P,COM,S{sow}))$(BDSIG(L)>0) +
* Limit advance and delay or balancing time window
    SUM(LASTLL$LNX(L),SUM(LIM$(IPS(L) XOR BD(LIM)),VAR_SIFT(V,S,LIM)) +
      SUM((RS_UP(R,S,JS),RJ_SL(R,JS,TS(SL--RS_STG(R,SL)))),
        ({var}_ACT(R,V,T,P,SL{sow})$IPS(L)-{var}_SIN(R,V,T,P,COM,SL{sow}) -
         (VAR_SIFT(V,SL,'UP')-VAR_SIFT(V,TS,'UP'))$BD(L))$(MOD(RS_HR(R,S)-RS_HR(R,SL)+G_YRFR(R,S)/RS_STGPRD(R,S)/9+1/JS_CCL(R,JS),1/JS_CCL(R,JS))<ACT_TIME(RTP,L)/8760))))$IPS(LNX);

""",
        )
