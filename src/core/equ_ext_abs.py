# equ_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * EQU_EXT.abs - Extension for Ancillery Balancing Services
# *-----------------------------------------------------------------------------
# * ABS Final pre-processing
# *-----------------------------------------------------------------------------
# ---------------------------------------------------------------------------


from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtAbs(GamsClass):
    """Translation unit for equ_ext.abs."""

    # Instance attributes
    module_name: str = "equ_ext_abs"
    gams_source: str = "equ_ext.abs"

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
        self.cal_red_func = self._resolve_cal_red_func()
        self.compile()

    def _resolve_cal_red_func(self) -> Callable[..., Any]:
        """Helper method to determine and return the correct reduction function."""
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red

            return cal_red_red
        elif self.env.cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red

            return cal_nored_red
        else:
            raise ValueError(f"Unexpected value for cal_red: {self.env.cal_red}")

    def compile(self) -> None:
        self.tc.enqueue(self.exec1, pgprim=self.env.pgprim)
        self.macros(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim)

        if self.env.stages == "YES":
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.sw_stvars}"
            )

        self.env.set_scoped(
            "tmp",
            f"SUM(MODLYEAR(K)$(COEF_VNT(R,T,P,K)$(PRC_VINT(R,P)->DIAG(V,K))),COEF_VNT(R,T,P,K)*({macro.VAR_NCAP(self.env.varm, 'R', 'K', 'P', self.env.sws)}$T(K)+NCAP_PASTI(R,K,P){self.env.rcapsbm}))",
        )
        self.env.set_scoped("r_w_t", f"BS_RVT({self.env.r_v_t})")

        # ABS Equation Formulations - numbers refer to document (00=01)
        self.abs_eq_1(
            r_t=self.env.r_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_1p(
            r_t=self.env.r_t,
            var=self.env.var,
            sow=self.env.sow,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_2(
            r_t=self.env.r_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )
        self.abs_eq_3(
            r_t=self.env.r_t,
            swtx=self.env.swtx,
            swx=self.env.swx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_4(
            r_t=self.env.r_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            tmp=self.env.tmp,
            mx=self.env.mx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_5_to_6(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_7_to_8(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_9(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            mx=self.env.mx,
            sow=self.env.sow,
            var=self.env.var,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_10(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            sow=self.env.sow,
            var=self.env.var,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_11_to_17(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_18_20(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_19_21(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_22(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_23(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            sow=self.env.sow,
            var=self.env.var,
            tmp=self.env.tmp,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_24(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            mx=self.env.mx,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_25(
            r_w_t=self.env.r_w_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            var=self.env.var,
            sow=self.env.sow,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )
        self.abs_eq_26(
            r_t=self.env.r_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_27(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            varm=self.env.varm,
            sws=self.env.sws,
            mx=self.env.mx,
            rcapsbm=self.env.rcapsbm,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )
        self.abs_eq_28(
            r_v_t=self.env.r_v_t,
            swx=self.env.swx,
            swtx=self.env.swtx,
            tmp=self.env.tmp,
            mx=self.env.mx,
            rts=macro.rts(s="S", g=self.tc, env=self.env),
        )

    def exec1(self: EquExtAbs, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Adjust equation controls
  BS_UPL(RP_UPL(BS_SUPP,BDNEQ))=YES;
  BS_UPC(PRC_TSL(BS_SUPP(R,P),TSL),BDNEQ)$SUM(BS_BSC(R,P,C)$(ABS(BS_RTYPE(R,C))>2),1)$=RP_UPS(R,P,TSL,'UP');
  RP_UPL(BS_UPL)=NO;
  RP_UPC(BS_UPC)=NO;
* Activate capacity equations
  OPTION TRACKP<BS_BSC; RP_UPL(TRACKP,'N')=YES;
  RP_UPS(TRACKP(R,P),TSL,'FX')$SUM(RP_UPS(PRC_TSL(R,P,TSLVL),L),RLUP(R,TSLVL,TSL))=YES;
  RP_UPS(TRACKP(R,P),TSL,'LO')$SUM(PRC_TSL(R,P,TSLVL)$RLUP(R,TSLVL,TSL),NOT RP_UPS(R,P,TSL,'FX'))=YES;
  RP_UPS(PRC_TSL(TRACKP,TSL(S)),'LO')=YES;
* Remove other basic Capact equations
  OPTION TRACKP<AFUPS; BS_MAINT(R,V,P,S)$(NOT TRACKP(R,P)+RP_DP(R,P))=0;
  OPTION TRACKP<BS_SUPP, RP_PRC<NCAP_AFX; TRACKP(BS_STGP)=YES;
  RP_PRC(RP_STD(RP))$RP_UPL(RP,'FX')=NO;
  AFS(R,T,P,S,L('UP'))$((NOT RPS_CAFLAC(R,P,S,L)+RP_PRC(R,P))$TRACKP(R,P)$BS_PRS(R,P,S))=NO;
  AFUPS(R,T,P,S)$BS_SUPP(R,P)=NO;
  NCAP_AFC(R,V,P,'{pgprim}',STL(S))$(BS_PRS(R,P,S)$BS_STGP(R,P))=0;
  OPTION CLEAR=UNCD7,CLEAR=TRACKP,CLEAR=RP_PRC;
  LOOP((RTP(R,V,P),RPS_PRCTS(R,P,S))$((NOT PRC_TS(R,P,S))$BS_MAINT(RTP,S)),Z=BS_MAINT(RTP,S);
    F=ABS(Z); IF((F>=TS_CYCLE(R,S)*24$(F>1))$(RPS_UPS(R,P,S) OR (STOAL(R,S)*SIGN(Z)<2)),UNCD7(RTP,S,RTP)=YES));
  LOOP(UNCD7(RTP,S,R,T,P),RPS_UPS(R,P,TS)$(STOAL(R,TS)=1)=YES; BS_MAINT(RTP,TS)$RS_TREE(R,S,TS)=EPS$(BS_MAINT(RTP,TS)>=0)$BS_MAINT(RTP,TS));
  BS_RVT(R,VNT(V,T)) $= SUM(RC(R,C)$BS_LAMBDA(R,T,C),1);

""",
        )

    def macros(self: EquExtAbs, var: str, sow: str, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Variable macros
$ macro var_bson(r,v,t,p,s) sum(ts_map(r,all_ts,s)$(rs_below1(r,all_ts,s)+annual(s)),var_gap(r,v,t,p,all_ts)+({var}_ups(r,v,t,p,all_ts,'FX'{sow})-var_off(r,v,t,p,s))$rps_ups(r,p,s))
$ macro var_bsd(typ,rtc,s) {var}_comlv(typ,rtc,s{sow})
$ macro var_bsmup(r,v,t,p,s) {var}_bsprs(r,v,t,p,'{pgprim}',s,'N'{sow})
$ macro var_bsfsp(r,v,t,p,c,s) {var}_bsprs(r,v,t,p,c,s,'N'{sow})$bs_rvt(r,v,t)
$ macro var_bsfnsp(r,v,t,p,c,s) {var}_bsprs(r,v,t,p,c,s,'FX'{sow})$bs_rvt(r,v,t)
$ macro var_bsupsr(r,v,t,p,s,bd) {var}_bsprs(r,v,t,p,'{pgprim}',s,bd{sow})$bs_rvt(r,v,t)
$ macro var_bslack(r,t,p,c,s) {var}_bsprs(r,t,t,p,c,s,'UP'{sow})
""",
        )

    def abs_eq_1(
        self: EquExtAbs, r_t: str, swx: str, swtx: str, var: str, sow: str, rts: str
    ) -> None:
        """Demands for reserves"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS00(RTC({r_t},C),{rts}{swx})$({swtx}BS_OMEGA(R,'0',C,S)$BS_LAMBDA(RTC))..
  SUM(RHS_COMBAL(RTC,TS)$TS_MAP(R,TS,S),{var}_COMPRD(RTC,TS{sow})/G_YRFR(R,TS))
  =L=
* Supply (converted to common flow units, as also demand)
  SUM((RHS_COMBAL(RTC,SL),TS_MAP(R,SL,S))$BS_OMEGA(RTC,SL),
    SUM(RTP_VINTYR(R,V,T,P)$(BS_BSC(R,P,C)+YES$BS_STIME(R,P,C,'UP')),PRC_CAPACT(R,P) *
      SUM(BS_PRS(R,P,TS)$RS_FR(R,S,TS),(VAR_BSFSP(R,V,T,P,C,TS)+SUM(BS_SUPP(R,P)$(ABS(BS_RTYPE(R,C))>2),VAR_BSFNSP(R,V,T,P,C,TS)))*RS_FR(R,TS,S))));

""",
        )

    def abs_eq_1p(
        self: EquExtAbs, r_t: str, var: str, sow: str, swx: str, swtx: str, rts: str
    ) -> None:
        """Max and ABS(diff) and Share equations"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
          EQ_BS01(RHS_COMBAL(RTC({r_t},C),{rts}),BS_K,L{swx})$({swtx}(BS_OMEGA(RTC,S)<>2$IPS(L))$BS_SHARE(RTC,BS_K,L)$BS_OMEGA(RTC,S))..
  SUM(BD(LIM(BS_K)),{var}_COMNET(RTC,S{sow})/G_YRFR(R,S) - BS_LAMBDA(RTC) *
    (VAR_BSD('PRB',RTC,S)$BDUPX(BD)-VAR_BSD('DET',RTC,S)$BDLOX(BD))$(BS_OMEGA(RTC,S)<2) -
    ((VAR_BSD('PRB',RTC,S)-VAR_BSD('DET',RTC,S))*BDSIG(BD))$(BS_OMEGA(RTC,S)>2))$IPS(L) +
  SUM(BD(L),
* Supply by group
    SUM(RTP_VINTYR(R,V,T,P)$((BS_BSC(R,P,C)+YES$BS_STIME(R,P,C,'UP'))$GR_GENMAP(R,P,BS_K)),PRC_CAPACT(R,P) *
      SUM(BS_PRS(R,P,TS)$RS_FR(R,S,TS),(VAR_BSFSP(R,V,T,P,C,TS)+SUM(BS_SUPP(R,P)$(ABS(BS_RTYPE(R,C))>2),VAR_BSFNSP(R,V,T,P,C,TS)))*RS_FR(R,TS,S))) -
* Share in demand
    BS_SHARE(RTC,BS_K,L)*{var}_COMNET(RTC,S{sow})/G_YRFR(R,S))*BDSIG(L)
  =G= 0;
""",
        )

    def abs_eq_2(
        self: EquExtAbs,
        r_t: str,
        swx: str,
        swtx: str,
        var: str,
        sow: str,
        rts: str,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        """Loads by source of imbalance for each user category k"""

        cal_red = self.cal_red_func(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS02({r_t},{rts},BS_K{swx})$({swtx}SUM(BS_SBD(FINEST(R,S),BD),1)$BS_RTK(R,T,BS_K))..
  SUM(BS_TOP(RP_STD(R,P),C,IO)$GR_GENMAP(R,P,BS_K),
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS))$RS_FR(R,S,TS),
{cal_red}
       * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")}))) +
  SUM(RPC_STG(R,P,C)$GR_GENMAP(R,P,BS_K),SIGN(GR_GENMAP(R,P,BS_K))*
    SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")})*
       SUM(BS_TOP(R,P,C,'OUT'),V_U(SOUT,R,V,T,P,C,TS)*STG_EFF(R,V,P))-SUM(BS_TOP(R,P,C,'IN'),V_U(SIN,R,V,T,P,C,TS)))) +
  SUM(RPC_IRE(R,P,C,IE)$(NRG_TMAP(R,'ELC',C)$GR_GENMAP(R,P,BS_K)),SIGN(GR_GENMAP(R,P,BS_K))*
    SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS))$RS_FR(R,S,TS),
       ({var}_IRE(R,V,T,P,C,TS,IE{sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))*
       (1-2$XPT(IE)) * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "C", "S", "TS")})))
  =E=  {var}_RLD(R,T,S,BS_K{sow})*G_YRFR(R,S);
""",
        )

    def abs_eq_3(
        self: EquExtAbs, r_t: str, swtx: str, swx: str, var: str, sow: str, rts: str
    ) -> None:
        """Stochastic or combined demand with variances"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS03(RTC({r_t},C),{rts}{swx})$({swtx}FINEST(R,S)$BS_LAMBDA(RTC))..
  SUM((RTCS_VARC(RTC,TS),TS_MAP(R,TS,S))$BS_OMEGA(RTC,TS),
    (BS_LAMBDA(RTC)*VAR_BSD('PRB',RTC,TS))$(BS_OMEGA(RTC,TS)<>2) +
    ({var}_COMNET(RTC,TS{sow})/G_YRFR(R,TS)-BS_LAMBDA(RTC)*VAR_BSD('DET',RTC,TS)*BS_DETWT(RTC))$(BS_OMEGA(RTC,TS)=2) -
    BS_LAMBDA(RTC)*(1-BS_DETWT(RTC)$(BS_OMEGA(RTC,TS)=2))*BS_DELTA(RTC,TS)*3*SUM(BS_RTK(R,T,BS_K),BS_SIGMA(RTC,BS_K,S)*{var}_RLD(R,T,S,BS_K{sow})))
  =G= 0;
""",
        )

    def abs_eq_4(
        self: EquExtAbs, r_t: str, swx: str, swtx: str, tmp: str, mx: str, rts: str
    ) -> None:
        """Deterministic demand"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 EQ_BS04(RHS_COMBAL(RTC({r_t},C),{rts}),P{swx})$({swtx}RTP(R,T,P)$GR_GENMAP(R,P,'SI')$BS_OMEGA(RTC,S))..
  VAR_BSD('DET',RTC,S)
  =G=
  BS_RTCS('EXOGEN',RTC,S)*BS_CAPACT(R) + PRC_CAPACT(R,P) *
  BS_RTCS('WMAXSI',RTC,S)*SUM(RTP_VINTYR(R,V,T,P),({tmp})*SUM(PRC_TS(R,P,TS)$RS_FR(R,TS,S),SUM(BDUPX(BD),COEF_AF{mx}(R,V,T,P,TS,BD))*RS_FR(R,TS,S)));

""",
        )

    def abs_eq_5_to_6(
        self: EquExtAbs, r_v_t: str, swx: str, swtx: str, rts: str
    ) -> None:
        """Minimum online and offline times (adjusted)"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 EQ_BS05(RTP_VINTYR({r_v_t},P),TSL,BD(L),{rts}{swx})$({swtx}TS_GROUP(R,TSL,S)$BS_UPC(R,P,TSL,L))..
  SUM((RS_UP(R,S,JS),RJ_SL(R,JS,SL)),
    V_U(UPS,R,V,T,P,SL,L)$(RS_MODUS(R,S,JS,SL)<ACT_TIME(R,T,P,L)/8760)) +
  SUM(LIM(BDNEQ)$(BDSIG(LIM)*BDSIG(L)<0),VAR_BSUPSR(R,V,T,P,S,LIM)$BS_SBD(R,S,LIM) -
    (SUM(RS_UP(R,S,J,TS),V_U(UPS,R,V,T,P,TS,'FX'))$BDUPX(BD)+VAR_OFF(R,V,T,P,S)*BDSIG(BD))$(BS_SBD(R,S,LIM)+YES$ACT_TIME(R,T,P,L)))
  =L= 0;
""",
        )

    def abs_eq_7_to_8(
        self: EquExtAbs, r_v_t: str, swx: str, swtx: str, var: str, sow: str, rts: str
    ) -> None:
        """Ramping rates (adjusted)"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS07(RTP_VINTYR({r_v_t},P),{rts},BDNEQ(BD){swx})$({swtx}SUM(TS_ANN(S,TS)$ACT_UPS(R,V,P,TS,BD),1)$PRC_TS(R,P,S)$BS_UPL(R,P,BD))..
* max fraction of capacity
   SUM(PRC_TS(R,P,TS(S--RS_STG(R,S))),PRC_CAPACT(R,P)*SUM(TS_ANN(S,SL),ACT_UPS(R,V,P,SL,BD)) *
     (VAR_BSON(R,V,T,P,S) + ((VAR_OFF(R,V,T,P,S)-VAR_OFF(R,V,T,P,TS) - (VAR_BSUPSR(R,V,T,P,S,BD)$SUM(BS_COMTS(BS_ANEG(R,C),S),1)))$BDLOX(BD))$RPS_UPS(R,P,S)) +
* dynamic ramp limits
     RS_STGPRD(R,S)*2/(G_YRFR(R,S)+G_YRFR(R,TS))/8760 *
     ({var}_ACT(R,V,T,P,S{sow})/G_YRFR(R,S)-{var}_ACT(R,V,T,P,TS{sow})/G_YRFR(R,TS) +
      ((VAR_OFF(R,V,T,P,S)-VAR_OFF(R,V,T,P,TS))*PRC_CAPACT(R,P)*ACT_MINLD(R,V,P))$RPS_UPS(R,P,S))*BDSIG(BD) - PRC_CAPACT(R,P)*SUM(BS_BSC(R,P,C)$BS_ABD(R,C,BD),VAR_BSFSP(R,V,T,P,C,S)$BS_COMTS(R,C,S)))
  =G= 0;
""",
        )

    def abs_eq_9(
        self: EquExtAbs,
        r_v_t: str,
        swx: str,
        swtx: str,
        mx: str,
        sow: str,
        var: str,
        rts: str,
    ) -> None:
        """Capacity margin constraints - positive"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS09(RTP_VINTYR({r_v_t},P),{rts},L('UP'){swx})$({swtx}BS_PRS(R,P,S)$(NOT RP_DP(R,P))$BS_SUPP(R,P))..
  SUM(BS_COMTS(BS_APOS(R,C),S)$BS_BSC(R,P,C),VAR_BSFSP(R,V,T,P,C,S))*PRC_CAPACT(R,P) +
  (PRC_CAPACT(R,P)*(COEF_AF{mx}(R,V,T,P,S,L)-ACT_MINLD(R,V,P))*V_U(UPS,R,V,T,P,S,L)*MIN(1,ACT_SDTIME(R,V,P,'HOT',L)/8760/(G_YRFR(R,S)/RS_STGPRD(R,S))))$RPS_UPS(R,P,S)
  =L=
  PRC_CAPACT(R,P)*COEF_AF{mx}(R,V,T,P,S,L)*VAR_BSON(R,V,T,P,S) -
  ({var}_ACT(R,V,T,P,S{sow})$RP_STD(R,P)+SUM(TOP(RPC_STG(R,P,C),'OUT'),V_U(SOUT,R,V,T,P,C,S)*STG_EFF(R,V,P))$RP_STG(R,P))/G_YRFR(R,S);

""",
        )

    def abs_eq_10(
        self: EquExtAbs, r_v_t: str, swx: str, swtx: str, sow: str, var: str, rts: str
    ) -> None:
        """Capacity margin constraints - negative"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS10(RTP_VINTYR({r_v_t},P),{rts}{swx})$({swtx}BS_PRS(R,P,S)$BS_NEGP(R,P)$BS_SUPP(R,P))..
  SUM(BS_COMTS(BS_ANEG(R,C),S)$BS_BSC(R,P,C),VAR_BSFSP(R,V,T,P,C,S)+VAR_BSFNSP(R,V,T,P,C,S)$RP_STD(R,P))*PRC_CAPACT(R,P)
  =L=
  ({var}_ACT(R,V,T,P,S{sow})$RP_STD(R,P)+SUM(TOP(RPC_STG(R,P,C),'OUT'),V_U(SOUT,R,V,T,P,C,S)*STG_EFF(R,V,P))$RP_STG(R,P))/G_YRFR(R,S) -
  PRC_CAPACT(R,P)*ACT_MINLD(R,V,P)*(VAR_BSON(R,V,T,P,S)-SUM(RPS_UPS(R,P,S),VAR_BSUPSR(R,V,T,P,S,'LO')$SUM(BS_COMTS(BS_ANEG(R,C),S),1)));

""",
        )

    def abs_eq_11_to_17(
        self: EquExtAbs, r_w_t: str, swx: str, swtx: str, rts: str
    ) -> None:
        """Limit reserve by type and sign according to BS_RMAX"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS11(RTP_VINTYR({r_w_t},P),C,{rts},BD{swx})$({swtx}BS_PRS(R,P,S)$BS_COMTS(R,C,S)$RPC_CONLY(R,V,P,C)$BS_ABD(R,C,BD))..
  SUM(BS_ABD(R,COM,BD)$(ABS(BS_RTYPE(R,COM))<=ABS(BS_RTYPE(R,C))),VAR_BSFSP(R,V,T,P,COM,S)$BS_BSC(R,P,COM)$BS_COMTS(R,COM,S))
  =L=  (VAR_BSON(R,V,T,P,S)-SUM(RPS_UPS(R,P,S)$BDLOX(BD),VAR_BSUPSR(R,V,T,P,S,BD))) * SUM(TS_ANN(S,TS),BS_RMAX(R,V,P,C,TS));

""",
        )

    def abs_eq_18_20(
        self: EquExtAbs, r_w_t: str, swx: str, swtx: str, rts: str
    ) -> None:
        """Limit the provision of TRT & RRR reserves according to quick start-up / shut-down capacity"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS18(RTP_VINTYR({r_w_t},P),{rts},BDNEQ(BD){swx})$({swtx}BS_PRS(R,P,S)$RPS_UPS(R,P,S)$ACT_MINLD(R,V,P)$BS_SUPP(R,P))..
  VAR_BSUPSR(R,V,T,P,S,BD)*ACT_MINLD(R,V,P)$BS_SBD(R,S,BD)
  =L=  SUM(BS_ABD(R,C,BD)$(ABS(BS_RTYPE(R,C))>2),VAR_BSFNSP(R,V,T,P,C,S)$BS_BSC(R,P,C)$BS_COMTS(R,C,S));

""",
        )

    def abs_eq_19_21(
        self: EquExtAbs, r_w_t: str, swx: str, swtx: str, rts: str
    ) -> None:
        """Limit the provision of TRT & RRR reserves according to quick start-up / shut-down capacity"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS19(RTP_VINTYR({r_w_t},P),C,{rts},BD{swx})$({swtx}(ABS(BS_RTYPE(R,C))>2)$BS_PRS(R,P,S)$BS_SUPP(R,P)$BS_BSC(R,P,C)$BS_ABD(R,C,BD))..
  SUM(BS_ABD(R,COM,BD)$(MOD(ABS(BS_RTYPE(R,COM))-1,BS_RTYPE(R,C))>1),VAR_BSFNSP(R,V,T,P,COM,S)$BS_BSC(R,P,COM)$BS_COMTS(R,COM,S))
  =L=  VAR_BSUPSR(R,V,T,P,S,BD)$RPS_UPS(R,P,S) * SUM(TS_ANN(S,TS),BS_RMAX(R,V,P,C,TS))$BS_COMTS(R,C,S);
""",
        )

    def abs_eq_22(
        self: EquExtAbs, r_w_t: str, swx: str, swtx: str, var: str, sow: str, rts: str
    ) -> None:
        """Ensure sufficient storage level when contracted to reserve"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS22(RTP_VINTYR({r_w_t},P),{rts}{swx})$({swtx}BS_STGP(R,P)$COEF_AFUPS(R,V,P,S)$RPS_STG(R,P,S))..
* storage: for single-day (true) activity divide by cycles under parent
  SUM(PRC_TS(R,P,TS)$RS_FR(R,TS,S),{var}_ACT(R,V,T,P,TS{sow})*RS_FR(R,TS,S)/RS_STGPRD(R,TS))$BS_SBD(R,S,'UP')
  =G=
  SUM(BS_COMTS(BS_APOS(R,C),S),PRC_CAPACT(R,P)/SQRT(STG_EFF(R,V,P)) / 8760 *
    VAR_BSFSP(R,V,T,P,C,S)*(BS_STIME(R,P,C,'LO')/2 +(BS_STIME(R,P,C,'UP')-BS_STIME(R,P,C,'LO'))*MAX(1,G_YRFR(R,S)/RS_STGPRD(R,S)*8760/(1+BS_STIME(R,P,C,'UP'))**0.5)));
""",
        )

    def abs_eq_23(
        self: EquExtAbs,
        r_v_t: str,
        swx: str,
        swtx: str,
        sow: str,
        var: str,
        tmp: str,
        rts: str,
    ) -> None:
        """Limit storage level by capacity and contracted reserve"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS23(RTP_VINTYR({r_v_t},P),{rts}{swx})$({swtx}BS_STGP(R,P)$COEF_AFUPS(R,V,P,S)$RPS_STG(R,P,S))..
* storage: for single-day (true) activity divide by cycles under parent
  SUM(PRC_TS(R,P,TS)$RS_FR(R,TS,S),{var}_ACT(R,V,T,P,TS{sow})*RS_FR(R,TS,S)/RS_STGPRD(R,TS))
  =L=
* available process capacity - vintaged or not
  (({tmp})*COEF_AFUPS(R,V,P,S) / EXP(PRC_SC(R,P)) * PRC_CAPACT(R,P)) -
  SUM(BS_COMTS(BS_ANEG(R,C),S),PRC_CAPACT(R,P)*SQRT(STG_EFF(R,V,P)) / 8760 *
    VAR_BSFSP(R,V,T,P,C,S)*(BS_STIME(R,P,C,'LO')/2 +(BS_STIME(R,P,C,'UP')-BS_STIME(R,P,C,'LO'))*MAX(1,G_YRFR(R,S)/RS_STGPRD(R,S)*8760/(1+BS_STIME(R,P,C,'UP'))**0.5)));
""",
        )

    def abs_eq_24(
        self: EquExtAbs,
        r_w_t: str,
        swx: str,
        swtx: str,
        var: str,
        mx: str,
        sow: str,
        rts: str,
    ) -> None:
        """End-use - negative"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS24(RTP_VINTYR({r_w_t},P),{rts}{swx})$({swtx}BS_PRS(R,P,S)$AFS(R,T,P,S,'UP')$BS_SBD(R,S,'LO')$BS_NEGP(R,P)$BS_ENDP(R,P))..
  SUM(BS_COMTS(BS_ANEG(R,C),S)$BS_BSC(R,P,C),VAR_BSFSP(R,V,T,P,C,S))
  =L=
* available process capacity - activity level
  (VAR_BSON(R,V,T,P,S)*COEF_AF{mx}(R,V,T,P,S,'UP') - {var}_ACT(R,V,T,P,S{sow})/PRC_CAPACT(R,P)/G_YRFR(R,S)) *
  SUM(TOP(R,P,C,'IN')$NRG_TMAP(R,'ELC',C),PRC_ACTFLO(R,V,P,C)$RPC_PG(R,P,C) +
    SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,TS,S),RS_FR(R,TS,S) *
      SUM(RPC_PG(R,P,COM),ACT_FLO(R,V,P,C,TS)$RPC_FFUNC(R,P,C) + PRC_ACTFLO(R,V,P,COM) *
       (SUM(RPG_1ACE(R,P,CG,C)$COEF_PTRAN(R,V,P,CG,C,COM,TS),1/COEF_PTRAN(R,V,P,CG,C,COM,TS)) +
        SUM((RPCC_FFUNC(RP_PG(R,P,CG),C),TS_MAP(R,SL,TS))$RPS_S1(R,P,SL),(ACT_FLO(R,V,P,C,SL)**1$RPC_AFLO(R,P,C))*COEF_PTRAN(R,V,P,CG,COM,C,S)))))$(NOT RPC_PG(R,P,C)));

""",
        )

    def abs_eq_25(
        self: EquExtAbs,
        r_w_t: str,
        swx: str,
        swtx: str,
        var: str,
        sow: str,
        rts: str,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        """End-use - positive"""

        cal_red = self.cal_red_func(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS25(RTP_VINTYR({r_w_t},P),{rts}{swx})$({swtx}BS_PRS(R,P,S)$BS_SBD(R,S,'UP')$BS_ENDP(R,P))..
  SUM(BS_COMTS(BS_APOS(R,C),S)$BS_BSC(R,P,C),VAR_BSFSP(R,V,T,P,C,S))*PRC_CAPACT(R,P)*G_YRFR(R,S)
  =L=
  SUM(TOP(R,P,C,'IN')$NRG_TMAP(R,'ELC',C),
    SUM(RTPCS_VARF(R,T,P,C,TS)$TS_MAP(R,S,TS),
{cal_red}
    )$RP_STD(R,P)+SUM(RPCS_VAR(RPC_STG(R,P,C),TS)$TS_MAP(R,S,TS),V_U(SIN,R,V,T,P,C,TS)$(PRC_NSTTS(R,P,TS)+PRC_STGTSS(R,P,C))));

""",
        )

    def abs_eq_26(self: EquExtAbs, r_t: str, swx: str, swtx: str, rts: str) -> None:
        """Bound on process reserve provision"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS26(RTP({r_t},P),C,{rts}{swx})$({swtx}BS_COMTS(R,C,S)$(BS_BSC(R,P,C)+YES$BS_STIME(R,P,C,'UP'))$BS_BNDPRS(RTP,C,S,'N'))..
  SUM((RTP_VINTYR(R,V,T,P),BS_PRS(R,P,TS))$RS_FR(R,TS,S),
    (VAR_BSFSP(R,V,T,P,C,TS)+VAR_BSFNSP(R,V,T,P,C,TS)$(ABS(BS_RTYPE(R,C))>2)$BS_SUPP(R,P))*RS_FR(R,TS,S))
  =E=  VAR_BSLACK(R,T,P,C,S);
""",
        )

    def abs_eq_27(
        self: EquExtAbs,
        r_v_t: str,
        swx: str,
        swtx: str,
        varm: str,
        sws: str,
        rcapsbm: str,
        mx: str,
        rts: str,
    ) -> None:
        """Maintenence 1 - entrance to maintenance"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ_BS27(RTP_VINTYR({r_v_t},P),{rts}{swx})$({swtx}(BS_MAINT(R,V,P,S)>=0)$BS_MAINT(R,V,P,S))..
  SUM(TS_MAP(R,S,TS)$RPS_UPS(R,P,TS),
    (VAR_BSMUP(R,V,T,P,TS)*MIN(1,ROUND(BS_MAINT(R,V,P,S),1)/8760*RS_STGPRD(R,TS)/G_YRFR(R,S)))$PRC_TS(R,P,TS) +
    (VAR_OFF(R,V,T,P,TS)*RS_FR(R,TS,S)$(BS_MAINT(R,V,P,S)=0))$TS_CYCLE(R,TS))
  =G=
* unavailable process capacity - vintaged or not
  SUM(MODLYEAR(K)$(COEF_VNT(R,T,P,K)$(PRC_VINT(R,P)->DIAG(V,K))),COEF_VNT(R,T,P,K)*({macro.VAR_NCAP(varm, "R", "K", "P", sws)}$T(K)+NCAP_PASTI(R,K,P){rcapsbm})*((1-COEF_AF{mx}(R,K,T,P,S,'UP'))$(ACT_UPS(R,T,P,S,'N')=0)+ACT_UPS(R,T,P,S,'N')));
""",
        )

    def abs_eq_28(
        self: EquExtAbs,
        r_v_t: str,
        swx: str,
        swtx: str,
        tmp: str,
        mx: str,
        rts: str,
    ) -> None:
        """Maintenence 2 - continuous duration"""

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 EQ_BS28(RTP_VINTYR({r_v_t},P),{rts}{swx})$({swtx}PRC_TS(R,P,S)$BS_MAINT(R,V,P,S))..
  SUM((RS_UP(R,S,JS),RJ_SL(R,JS,SL)),VAR_BSMUP(R,V,T,P,SL)$(RS_MODUS(R,S,JS,SL)<ABS(BS_MAINT(R,V,P,S))/8760))
  =L=  {tmp}*(1-COEF_AF{mx}(R,V,T,P,S,'UP'))-({macro.upscaps.render()}*COEF_AF{mx}(R,V,T,P,S,'UP'));
""",
        )
