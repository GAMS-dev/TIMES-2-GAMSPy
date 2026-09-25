# eqlducs_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQLDUCS - implements linear and discrete unit commitment
# *   arg1 - Section
# *=============================================================================*

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Equation, Number, Variable

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqlducsVda(GamsClass):
    """Translation unit for eqlducs.vda."""

    # Instance attributes
    module_name: str = "eqlducs_vda"
    gams_source: str = "eqlducs.vda"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        if self.env.obmac != "YES":
            return

        if self.arg1 != "EQU":
            # * Internal attributes for equation control
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
  PARAMETER DP_NON(R,LL,P,UPT,TSL,BD) 'Bounds on non-operational time between shut-down and next start-up';
""",
            )

            self.tc.enqueue(self.exec1)

        else:  # EQU
            self.tc.enqueue(self.disable_linear_dispatch)
            self.set_macros(
                var=self.env.var,
                sow=self.env.sow,
                condition=self.env.abs.upper() == "YES",
            )
            self.env.set_scoped(
                "capon",
                f"(COEF_CPT(R,V,T,P)*({macro.VAR_NCAP(self.env.varv, 'R', 'V', 'P', self.env.sws)}$T(V)+NCAP_PASTI(R,V,P){self.env.rcapsub}))$PRC_VINT(R,P)+{macro.VAR_CAP(self.env.var, 'R', 'T', 'P', self.env.sow)}$RP_UX(R,P)",
            )

            g = self.tc
            if (
                isinstance(self.env.rcapsub_GP, Number)
                and self.env.rcapsub_GP_value == 1
            ):
                raise ValueError("rcapsub_GP cannot be Number(1) in this assignment.")

            self.env.set_scoped(
                "capon_GP",
                g.coef_cpt[g.r, g.v, g.t, g.p]
                * (
                    macro.VAR_NCAP_GP(
                        self.env.varv_GP, g.r, g.v, g.p, self.env.sws_GP
                    ).where[g.t[g.v]]
                    + g.ncap_pasti[g.r, g.v, g.p]
                    + self.env.rcapsub_GP
                ).where[g.PrcVint[g.r, g.p]]
                + macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, self.env.sow_GP).where[
                    g.RpUx[g.r, g.p]
                ],
            )

            capups = f"({self.env.capon}-SUM(rs_below(r,all_ts,s)$rps_ups(r,p,all_ts),var_off(r,v,t,p,all_ts)))"
            self.define_equation1(
                capon=self.env.capon,
                capups=capups,
                r_v_t=self.env.r_v_t,
                swx=self.env.swx,
                swtx=self.env.swtx,
            )
            # * Discrete Unit Commitment
            if self.env.duc.upper() != "YES":
                return

            self.env.set_global("solmip", "YES")

            self.tc.enqueue(
                self.prepare_unit_size,
                condition1=self.tc.defined("PRC_DSCNCAP"),
                condition2=self.env.stages == "YES",
            )
            self.var_equ_indicators()
            self.tc.enqueue(self.exec2)

            ind = Path("indic.txt").read_text() if Path("indic.txt").exists() else ""
            if Path("cplex.opt").exists():
                Path("cplex.op2").write_text(Path("cplex.opt").read_text() + ind)
            if Path("xpress.opt").exists():
                Path("xpress.op2").write_text(Path("xpress.opt").read_text() + ind)

            self.define_equation2(
                r_v_t=self.env.r_v_t, capon=self.env.capon, capups=capups
            )

    def exec1(self: EqlducsVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Assume valid UPTs must have a cost or SD-time; reset simplified UC options
  OPTION RP_UPT<ACT_CSTSD, TRACKP<RP_UPT;
  RP_DP(TRACKP(RP))$=RP_UPL(RP,'FX');
  RP_DP(RP)$SUM(RPS_CAFLAC(PRC_TS(RP,S),BD),1)=NO;
  RP_DPL(PRC_TSL(RP_DP,TSL)) = YES;
  RP_DPL(RP_DP(R,P),TSL)$(RLUP(R,'DAYNITE',TSL)$PRC_TSL(R,P,'DAYNITE')) = ORD(TSL)>1;
  ACT_CSTUP(RTP(R,V,P),TSL,CUR)$RP_DP(R,P) = 0;
  ACT_CSTSD(RTP(R,V,P),UPT,'FX',CUR)$(RDCUR(R,CUR)$RP_DP(R,P)) = ACT_CSTSD(RTP,UPT,'UP',CUR)+ACT_CSTSD(RTP,'HOT','LO',CUR);
  ACT_CSTUP(RTP(R,V,P),TSL,CUR)$RP_DPL(R,P,TSL) $=SUM(UPT$ACT_CSTSD(RTP,UPT,'FX',CUR),EPS);
  RP_UPT(RP_DP,UPT,'LO')=DIAG('HOT',UPT); LOOP(V,RP_UPT(R,P,UPT,BD('UP'))$ACT_SDTIME(R,V,P,UPT,BD)=YES);
*------------------------------------
* Max. non-op. time processing
  ACT_MAXNON(R,V,P,UPT)$((NOT ACT_MAXNON(R,V,P,UPT))$RP_DP(R,P)) = EPS;
  DP_NON(RTP(R,V,P),UPT,TSL,'UP')$((ACT_MAXNON(RTP,UPT)<8760/G_CYCLE(TSL))$RP_DPL(R,P,TSL)) = ACT_MAXNON(RTP,UPT)/8760;
  DP_NON(RTP(R,V,P),'WARM',TSL,'LO')$RP_DP(R,P) = DP_NON(RTP,'HOT',TSL,'UP');
  DP_NON(RTP(R,V,P),UPT,TSL,'LO')$RP_DP(R,P) = MAX(DP_NON(RTP,UPT,TSL,'LO'),ACT_TIME(RTP,'LO')/8760);
  DP_NON(RTP(R,V,P),UPT,TSL,BDNEQ(BD))$RP_DP(R,P) = DP_NON(RTP,UPT,TSL,BD)+(ACT_SDTIME(RTP,UPT,'UP')+ACT_SDTIME(RTP,'HOT','LO'))/8760;
  DP_NON(RTP(R,V,P),UPT,TSL,'UP')$(DP_NON(RTP,UPT,TSL,'UP')$RP_DP(R,P)) = DP_NON(RTP,UPT,TSL,'UP')-DP_NON(RTP,UPT,TSL,'LO');
  DP_NON(RTP,'COLD',TSL,'UP') = 0;
*------------------------------------
* Partial loss processing
  ACT_SDTIME(RTP(R,V,P),UPT,BD)$(NOT RP_UPT(R,P,UPT,BD)) = 0;
  DP_PSUD(RTP,UPT,BDNEQ(BD))$((ACT_SDTIME(RTP,UPT,BD)>0)$ACT_SDTIME(RTP,UPT,BD)) = ACT_MINLD(RTP)/ACT_SDTIME(RTP,UPT,BD);
  ACT_LOSSD(RTP,UPT,BD)$(ACT_MINLD(RTP)$DP_PSUD(RTP,UPT,BD)<=DP_PSUD(RTP,UPT,BD)) = 0;
  OPTION CLEAR=TRACKP,DP_LOSD<ACT_LOSSD; DP_LOSD(RTP(R,V,P))$RP_PL(R,P,'N')$=RP_PL(R,P,'FX');
  ACT_LOSPL(DP_LOSD(RTP(R,V,P)),'FX')$(ACT_LOSPL(RTP,'FX')=0) = .01**(1$RP_PL(R,P,'N'));
  ACT_LOSSD(RTP,UPT,BD)$((ACT_LOSSD(RTP,UPT,BD)<ACT_LOSPL(RTP,'FX'))$ACT_LOSSD(RTP,UPT,BD)) = 0;
  DP_PSUD(DP_LOSD(RTP(R,V,P)),UPT,BDNEQ(BD)) = (DP_PSUD(RTP,UPT,BD)*(ACT_LOSSD(RTP,UPT,BD)/ACT_LOSPL(RTP,'FX')-1$RP_PL(R,P,'N'))/(ACT_MINLD(RTP)-DP_PSUD(RTP,UPT,BD)))$ACT_LOSSD(RTP,UPT,BD);
""",
        )

    def disable_linear_dispatch(self: EqlducsVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Disable inconsistent linear dispatch features, add UX control for CAP
  RP_UPS(RP_DP,TSL,L)=NO;
  RP_UPC(RP_DP,TSL,BD)=NO;
  AFUPS(R,T,P,S)$RP_DP(R,P)=NO;
  RPS_UPS(PRC_TS(RP_DP,S))=YES;
  RP_UX(RP)$(NOT PRC_VINT(RP))$=RP_DP(RP); RTP_VARP(RTP(R,T,P))$RP_UX(R,P)=YES;
  RP_UPS(RP_DP(R,P),TSL,'FX')$=SUM(RLUP(R,TSLVL,TSL)$PRC_TSL(R,P,TSLVL),1);
""",
        )

    def set_macros(self: EqlducsVda, var: str, sow: str, condition: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
$ macro sdtol .001
$ macro var_on(r,v,t,p,s) {var}_udp(r,v,t,p,s,'N'{sow})
$ macro var_off(r,v,t,p,s) {var}_ups(r,v,t,p,s,'N'{sow})
$ macro var_load(r,v,t,p,s) {var}_act(r,v,t,p,s{sow})/g_yrfr(r,s)/prc_capact(r,p)
$ macro var_gap(r,v,t,p,s) {var}_udp(r,v,t,p,s,'FX'{sow})
$ macro v_u(x,r,v,t,p,s,l) {var}_&x(r,v,t,p,s,l{sow})
$ macro SUDHFR(r,s,x,sl) (G_YRFR(r,s) x G_YRFR(r,sl))/2/RS_STGPRD(r,s)
$ macro SPRSV \
{f"-sum(bs_comts(bs_apos(r,c),s)$bs_bsc(r,p,c),{var}_bsprs(r,v,t,p,c,s,'N'{sow}))$bs_supp(r,p)" if condition else ""}
""",
        )

    def define_equation1(
        self: EqlducsVda,
        capon: str,
        capups: str,
        r_v_t: str,
        swx: str,
        swtx: str,
    ) -> None:
        rts = macro.rts(s="S", g=self.tc, env=self.env)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------

  eq_sdlogic(rtp_vintyr({r_v_t},p),tsl,{rts},lnx(l){swx})$({swtx}ts_group(r,tsl,s)$rp_dpl(r,p,tsl))..

     (sum(ts(s--rs_stg(r,s)),var_on(r,v,t,p,ts)-var_on(r,v,t,p,s)) - SUM(bd,v_u(ups,r,v,t,p,s,bd)*BDSIG(bd)))$ips(l) +
     (v_u(ups,r,v,t,p,s,'UP') - SUM(rp_upt(r,p,upt,'UP'),v_u(upt,r,v,t,p,s,upt)))$bd(l) =E= 0;

*-----------------------------------------------------------------------------

  eq_sudupt(rtp_vintyr({r_v_t},p),tsl,{rts},upt{swx})$({swtx}DP_NON(r,v,p,upt,tsl,'UP')$ts_group(r,tsl,s)$rp_dpl(r,p,tsl))..

     v_u(upt,r,v,t,p,s,upt) =L= sum((rs_up(r,s,js),rj_sl(r,js,sl))$(ORD(s)<>ORD(sl)),
       v_u(ups,r,v,t,p,sl,'LO')$(MOD(RS_HR(r,s)-RS_HR(r,sl)-DP_NON(r,v,p,upt,tsl,'LO')+(G_YRFR(r,sl)/4+G_YRFR(r,s))/RS_STGPRD(r,s)+2/JS_CCL(r,js),1/JS_CCL(r,js))<DP_NON(r,v,p,upt,tsl,'UP')*(1+sdtol)+G_YRFR(r,s)/RS_STGPRD(r,s)/2));

*-----------------------------------------------------------------------------

  eq_sdslant(rtp_vintyr({r_v_t},p),tsl,{rts}{swx})$({swtx}ts_group(r,tsl,s)$rp_dpl(r,p,tsl))..

     var_on(r,v,t,p,s) =E= sum(rs_below1(r,ts,s),v_u(ups,r,v,t,p,ts,'FX')-{capups})$PRC_TS(R,P,S) + ({capups}) - var_off(r,v,t,p,s) -
     sum(rp_upt(r,p,upt,bd),
      sum((rs_up(r,s,js),rj_sl(r,js,sl))$(RS_MODUS(R,SL,JS,S)<ACT_SDTIME(r,v,p,upt,bd)/8760*(1+sdtol)),
         v_u(upt,r,v,t,p,sl,upt)*(0$DIAG(S,SL) +
                                  MAX(0,1-MOD(RS_HR(r,sl)-RS_HR(r,s)+SUDHFR(r,sl,-,s)+2/JS_CCL(r,js),1/JS_CCL(r,js))/(ACT_SDTIME(r,v,p,upt,bd)/8760))*(1-DIAG(S,SL))))$bdupx(bd) +
      sum((rs_up(r,s,js),rj_sl(r,js,sl))$(RS_MODUS(R,S,JS,SL)<ACT_SDTIME(r,v,p,upt,bd)/8760*(1+sdtol)),
          v_u(ups,r,v,t,p,sl,bd)*(1$DIAG(S,SL) +
                                  MAX(0,1-MOD(RS_HR(r,s)-RS_HR(r,sl)+SUDHFR(r,sl,-,s)+2/JS_CCL(r,js),1/JS_CCL(r,js))/(ACT_SDTIME(r,v,p,upt,bd)/8760))*(1-DIAG(S,SL))))$bdlox(bd));

*-----------------------------------------------------------------------------

  eq_sdminon(rtp_vintyr({r_v_t},p),{rts}{swx})$({swtx}prc_ts(r,p,s)$rp_dp(r,p))..

     var_on(r,v,t,p,s)+sum(rs_below1(r,ts,s),var_gap(r,v,t,p,ts)) =G= var_gap(r,v,t,p,s)+v_u(ups,r,v,t,p,s,'UP')+
     (SUM(rp_upt(r,p,upt,'UP')$(G_YRFR(r,s)/RS_STGPRD(r,s)/2<=ACT_SDTIME(R,V,P,upt,'UP')/8760),v_u(upt,r,v,t,p,s,upt))-v_u(ups,r,v,t,p,s,'UP'))$(SMIN(rp_upt(r,p,upt,'UP'),ACT_SDTIME(r,v,p,upt,'UP')/8760)<G_YRFR(r,s)/RS_STGPRD(r,s)/2);

*-----------------------------------------------------------------------------

  eq_sudload(rtp_vintyr({r_v_t},p),{rts}{swx})$({swtx}prc_ts(r,p,s)$rp_dp(r,p))..

     var_load(r,v,t,p,s) =E= ({capon}{macro.upscaps.render()})*ACT_MINLD(R,V,P) + var_gap(r,v,t,p,s)*(COEF_AF(r,v,t,p,s,'UP')-ACT_MINLD(r,v,p)) SPRSV;

*-----------------------------------------------------------------------------

  eq_sudtime(rtp_vintyr({r_v_t},p),tsl,{rts},bd{swx})$({swtx}prc_tsl(r,p,tsl)$ts_group(r,tsl,s)$act_time(r,v,p,bd)$rp_dp(r,p))..

     sum(bdlox(bd), var_off(r,v,t,p,s) -
       sum((rs_up(r,s,js),rj_sl(r,js,sl)),v_u(ups,r,v,t,p,sl,bd)$(MOD(RS_HR(r,s)-RS_HR(r,sl)-ACT_SDTIME(r,v,p,'HOT','LO')/8760+G_YRFR(r,s)/RS_STGPRD(r,s)/2+2/JS_CCL(r,js),1/JS_CCL(r,js))<ACT_TIME(r,v,p,bd)/8760))) +
     sum(bdupx(bd), var_on(r,v,t,p,s) -
       sum((rs_up(r,s,js),rj_sl(r,js,sl)),
        sum(rp_upt(r,p,upt,bd),v_u(upt,r,v,t,p,sl,upt)$(MOD(RS_HR(r,s)-RS_HR(r,sl)+1/JS_CCL(r,js),1/JS_CCL(r,js))<(ACT_TIME(r,v,p,bd)-ACT_SDTIME(r,v,p,'HOT','LO')-ACT_SDTIME(r,v,p,upt,bd))/8760+G_YRFR(r,sl)/RS_STGPRD(r,s)/2))))
      =G= 0;

*-----------------------------------------------------------------------------

  eq_sudpll(rtp_vintyr({r_v_t},p),tsl,{rts}{swx})$({swtx}ts_group(r,tsl,s)$prc_tsl(r,p,tsl)$DP_LOSD(r,v,p)$rp_dp(r,p))..

     v_u(ups,r,v,t,p,s,'FX') =G=
     sum(rp_upt(r,p,upt,bd),
       sum((rs_up(r,s,js),rj_sl(r,js,sl))$(MOD((RS_HR(r,s)-RS_HR(r,sl))*BDSIG(bd)+G_YRFR(r,sl)/RS_STGPRD(r,s)/2+2/JS_CCL(r,js),1/JS_CCL(r,js))<ACT_SDTIME(r,v,p,upt,bd)/8760*(1+sdtol)),
         (1+MIN(1,MOD((RS_HR(r,s)-RS_HR(r,sl))*BDSIG(bd)+SUDHFR(r,sl,-,s)+2/JS_CCL(r,js),1/JS_CCL(r,js))/(ACT_SDTIME(r,v,p,upt,bd)/8760))*(DP_PSUD(r,v,p,upt,bd)-1)) *
         (v_u(upt,r,v,t,p,sl,upt)$bdupx(bd) + v_u(ups,r,v,t,p,sl,bd)$bdlox(bd)))) * PRC_CAPACT(r,p)*G_YRFR(r,s)*ACT_MINLD(r,v,p);

""",
        )

    def prepare_unit_size(self: EqlducsVda, condition1: bool, condition2: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Prepare min. unit sizes for semi-continuous modeling
  NCAP_SEMI(RVP)$=0; TRACKP(RP_DP(RP))$(PRC_SEMI(RP)<10)=YES;
  COEF_CAP(RTP_VINTYR(R,T,T,P))$TRACKP(R,P)=MIN(NCAP_SEMI(R,T,P),SUM(RTP_CPTYR(R,PYR(V),T,P),NCAP_PASTI(R,V,P)*COEF_CPT(R,V,T,P)));
  COEF_CAP(RTP_VINTYR(R,PYR(V),T,P))$(PRC_VINT(R,P)$TRACKP(R,P))=MIN(NCAP_SEMI(R,V,P),NCAP_PASTI(R,V,P)*COEF_CPT(R,V,T,P));
  COEF_CAP(RTP_VINTYR(R,TT,T,P))$((COEF_CAP(R,TT,T,P)=0)$TRACKP(R,P)) = NCAP_SEMI(R,TT,P);
  DP_UNS(RTP_VINTYR(R,V,T,P),TSL,'IN',LNX)$RP_DPL(R,P,TSL) $= COEF_CAP(R,V,T,P);
  DP_UNS(RTP_VINTYR(R,V,T,P),TSL,'IN',L)$(RP_UPS(R,P,TSL,'FX')$RP_DP(R,P)) $= COEF_CAP(R,V,T,P);
  DP_UNS(RTP_VINTYR(R,V,T,P),TSL,IPS(L),L)$((NOT DP_UNS(R,V,T,P,TSL,'IN',L))$RP_DPL(R,P,TSL))=1;
{"PRC_DSCNCAP(TRACKP)=0;" if condition1 else ""}
  OPTION CLEAR=TRACKP,CLEAR=COEF_CAP;
{"OPTION CLEAR=DP_UNS;" if condition2 else ""}
""",
        )

    def var_equ_indicators(self: EqlducsVda) -> None:
        g = self.tc
        m = g.container
        r, ll, t, p, s, lA = g.r, g.ll, g.t, g.p, g.s, g.lA

        # *Variables, Equations and Indicators
        g.VAR_ONIND = Variable(
            m,
            name="VAR_ONIND",
            domain=[r, ll, t, p, s, lA],
            description="on-line status of unit in timeslice s",
            type="BINARY",
        )
        g.eq_sdind_1 = Equation(m, name="eq_sdind_1")
        g.eq_sdind_0 = Equation(m, name="eq_sdind_0")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET INDIC(J) /
  1 "eq_sdind_0(r,v,t,p,tsl,s,ips,l)$var_onind(r,v,t,p,s,l) 0"
  2 "eq_sdind_1(r,v,t,p,tsl,s,ips,l)$var_onind(r,v,t,p,s,l) 1"
  /;
  *--------------------------------------
  FILE INDFILE / INDIC.TXT /;
  """,
        )

    def exec2(self: EqlducsVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  IF(SUM(RP_DP,1),PUT INDFILE; LOOP(INDIC(J)$(ORD(J)<3), put "indic ",INDIC.TE(J) /);
   PUTCLOSE INDFILE; OPTFILEID=2;
   """,
        )

    def define_equation2(self: EqlducsVda, r_v_t: str, capon: str, capups: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  eq_sdind_1(rtp_vintyr({r_v_t},p),tsl,ts(s--rs_stg(r,s)),ips,L)$(ts_group(r,tsl,s)$DP_UNS(r,v,t,p,tsl,ips,l))..

     var_onind(r,v,t,p,ts,l)*EPS +
     (var_on(r,v,t,p,ts)-sum(rs_below1(r,sl,s)$prc_ts(r,p,s),var_ups(r,v,t,p,sl,'FX')-{capups}) - (({capups})+var_ups(r,v,t,p,ts,'LO')+var_ups(r,v,t,p,s,'UP')))$L(ips) +
     ((var_on(r,v,t,p,ts) - var_gap(r,v,t,p,ts)$(NOT PRC_TSL(r,p,tsl)) - MAX(DP_UNS(r,v,t,p,tsl,ips,l),NCAP_SEMI(r,v,p)$PRC_TSL(r,p,tsl)/2))$ips(L) +
      (var_ups(r,v,t,p,ts,'UP') + var_ups(r,v,t,p,ts,'LO') - MAX(DP_UNS(r,v,t,p,tsl,ips,l),NCAP_SEMI(r,v,p)$PRC_TSL(r,p,tsl)/2))$diag('FX',L) +
      ({capon}-var_on(r,v,t,p,ts) - DP_UNS(r,v,t,p,tsl,ips,l))$diag('LO',L) +
      (var_gap(r,v,t,p,ts) - DP_UNS(r,v,t,p,tsl,ips,l))$diag('UP',L))$io(ips) =G= 0;

*-----------------------------------------------------------------------------

  eq_sdind_0(rtp_vintyr({r_v_t},p),tsl,ts(s--rs_stg(r,s)),ips,l)$(ts_group(r,tsl,s)$DP_UNS(r,v,t,p,tsl,ips,l))..

     (var_on(r,v,t,p,ts)+sum(rs_below1(r,sl,s),var_gap(r,v,t,p,sl)+var_ups(r,v,t,p,ts,'UP'))$prc_ts(r,p,s))$L(ips) +
     ((var_on(r,v,t,p,ts) - var_gap(r,v,t,p,ts)$(NOT PRC_TSL(r,p,tsl)) + var_ups(r,v,t,p,ts,'UP'))$ips(L) +
      (var_ups(r,v,t,p,ts,'UP') + var_ups(r,v,t,p,ts,'LO'))$diag('FX',L) +
      ({capon}-var_on(r,v,t,p,ts)+var_ups(r,v,t,p,ts,'LO'))$diag('LO',L) +
      (var_gap(r,v,t,p,ts))$diag('UP',L))$io(ips) =L= 0;
""",
        )
