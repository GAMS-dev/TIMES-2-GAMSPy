# dynslite_vda.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillparm_gms import fillparm
from core.pp_qaput_mod import pp_qaput_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class DynsliteVda(GamsClass):  # FilenameExt
    """Translation unit for dynslite.vda."""

    # Instance attributes
    module_name: str = "dynslite_vda"
    gams_source: str = "dynslite.vda"

    def __init__(
        self: DynsliteVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self: DynsliteVda) -> None:
        if self.env.rts == "S":
            return
        self.env.set_scoped("tmp", "$NORTS(R,T,S)")
        if self.arg1.upper() == "PRELEV":
            self.tc.enqueue(
                self.prelev_exec,
                ducyes=self.env.duc.upper == "YES",
                tmp=self.env.tmp,
            )
        elif self.arg1.upper() in ["PRELEV", "CLEAR"]:
            self.env.set_local("rts", "$(NORTS(R,V,S)+NORTS(R,T,S)$PASTMILE(V))")
            self.tc.enqueue(
                self.clear_exec,
                tmp=self.env.tmp,
                rts=self.env.rts,
            )
        elif self.arg1.upper() == "REDUCE":
            self.tc.enqueue(
                self.reduce_exec,
                tmp=self.env.tmp,
            )
        elif self.arg1.upper() == "POSTLEV":
            self.env.set_scoped("RESET", "0")
            self.tc.enqueue(
                self.postlev_exec,
                dflbl=self.env.dflbl,
                item=self.env.item,
                data=self.env.data,
                add=self.env.add,
                reset=self.env.reset,
            )
            self.env.set_local("rts", "$(NORTS(R,V,S)+NORTS(R,T,S)$PASTMILE(V))")
            self.tc.enqueue(
                self.clear_exec,
                tmp=self.env.tmp,
                rts=self.env.rts,
            )
        elif self.arg1.upper() == "BOUNDS":
            if self.env.stages == "YES":
                self.env.set_local("swt", f"SW_T(T{self.env.swd})$")
            self.env.set_local(
                "swt", f"{self.env.swd})$({self.env.swt}RT_PP(R,T){self.env.tmp}"
            )
            self.tc.enqueue(
                self.bounds_exec,
                tmp=self.env.tmp,
                swt=self.env.swt,
                model_name=self.env.model_name,
                var=self.env.var,
                var_uc_yes=self.env.var_uc == "YES",
            )

    def prelev_exec(
        self: DynsliteVda,
        ducyes: bool,
        tmp: str,
    ) -> None:
        if self.tc.container["NORTS"].number_records > 0:
            if ducyes:
                raise Exception("TS_OFF cannot be used with DUC")

            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf""""
* Re-calculate the leads for the SEASON timeslice cycle
  LOOP((R,ANNUAL(S),T), F=0;
   LOOP(RS_BELOW1(R,S,TS)$(NOT NORTS(R,T,TS)), IF(F, RS_STG(R,TS)=ORD(TS)-Z; Z=ORD(TS); ELSE Z=ORD(TS); F=Z));
   RS_STG(R,S+(F-ORD(S)))$F = F-Z);
* Re-calculate average residence time for storage activity for SEASON
  LOOP((TS_GROUP(R,'SEASON',S),TS(S--RS_STG(R,S)))$RS_STGPRD(R,S),RS_STGAV(R,S) = (G_YRFR(R,S)+G_YRFR(R,TS))/2/RS_STGPRD(R,S));
* QA Check
  PUTGRP=0;
  LOOP(RT_PP(R,T), Z=SUM((RS_BELOW1(R,ANNUAL,TS),S(TS--RS_STG(R,TS)))$((NOT NORTS(R,T,TS))$NORTS(R,T,S)),1);
    IF(Z,
{pp_qaput_mod("PUTOUT", "PUTGRP", "99", "Unsupported dynamic timeslice trees with overlap -- Fatal")}
     PUT QLOG ' FATAL ERROR   - Timeslice trees have shared branches (R.T)=',RT_PP.TE(RT_PP)));
*------------------------------
* Remove timeslices turned off
* Bounds+varcosts pre-cleared only
    ACT_BND(R,T,P,S,BD){tmp}=0;
    COM_BNDNET(R,T,C,S,BD){tmp}=0;
    COM_BNDPRD(R,T,C,S,BD){tmp}=0;
    FLO_BND(R,T,P,CG,S,BD){tmp}=0;
    FLO_FR(R,T,P,C,S,L){tmp} = 0;
    IRE_BND(R,T,C,S,ALL_R,IE,BD){tmp}=0;
    IRE_XBND(R,T,C,S,IE,BD){tmp}=0;
    STGIN_BND(R,T,P,C,S,BD){tmp}=0;
    STGOUT_BND(R,T,P,C,S,BD){tmp}=0;
    COM_BPRICE(R,T,C,S,CUR){tmp}=0;
""",
            )

    def clear_exec(
        self: DynsliteVda,
        tmp: str,
        rts: str,
    ) -> None:
        if self.tc.container["NORTS"].number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf""""
* Vintage-based cleared selectively
    RVP(RTP(R,T,P))$(NOT PRC_VINT(R,P))=YES;
    ACT_FLO(RVP(R,T,P),CG,S){tmp}=0;
    FLO_FUNC(RVP(R,T,P),CG,CG2,S){tmp}=0;
    FLO_SUM(RVP(R,T,P),CG,C,CG2,S){tmp}=0;
    NCAP_AF(RVP(R,T,P),S,BD){tmp}=0;
    FLO_SHAR(RVP(R,T,P),C,CG,S,BD){tmp}=0;
    FLO_ASHAR(RVP(R,T,P),C,CG,S,BD){tmp}=0;
    STG_LOSS(RVP(R,T,P),S){tmp}=0;
    IRE_FLO(RVP(R,T,P),C,ALL_R,COM,S){tmp}=0;
    ACT_EFF(RVP(R,T,P),CG,S){tmp}=0;
    OPTION CLEAR=RVP;
* Vintaged ANNUAL
    RVP(RTP(R,V,P))$PRC_VINT(R,P)$=PRC_TSL(R,P,'ANNUAL');
    LOOP(MIYR_1(T),
    ACT_FLO(RVP(R,V,P),CG,S)$(RPS_S1(R,P,'ANNUAL'){rts})=0;
    FLO_FUNC(RVP(R,V,P),CG,CG2,S){rts}=0;
    FLO_SUM(RVP(R,V,P),CG,C,CG2,S)$(RPCS_VAR(R,P,C,'ANNUAL'){rts})=0;
    NCAP_AF(RVP(R,V,P),S,BD){rts}=0;
    FLO_SHAR(RVP(R,V,P),C,CG,S,BD)$(RPCS_VAR(R,P,C,'ANNUAL'){rts})=0;
    FLO_ASHAR(RVP(R,V,P),C,CG,S,BD)$(RPS_S2(R,P,'ANNUAL'){rts})=0;
    STG_LOSS(RVP(R,V,P),S){rts}=0;
    IRE_FLO(RVP(R,V,P),C,ALL_R,COM,S){rts}=0);
    OPTION CLEAR=RVP;
* Milestonyr-based all cleared
    COM_IE(R,T,C,S){tmp}=0;
    COM_PKFLX(R,T,C,S){tmp}=0;
    COM_ELAST(R,T,C,S,L){tmp}=0;
    FLO_PKCOI(R,T,P,C,S){tmp}=0;
    STG_SIFT(R,T,P,C,S){tmp}=0;
    IRE_FLOSUM(R,T,P,C,S,IE,COM,IO){tmp}=0;
    UC_ACT(UCN,SIDE,R,T,P,S){tmp}=0;
    UC_FLO(UCN,SIDE,R,T,P,C,S){tmp}=0;
    UC_IRE(UCN,SIDE,R,T,P,C,S,IE){tmp}=0;
    UC_COM(UCN,COM_VAR,SIDE,R,T,C,S,UC_GRPTYPE){tmp}=0;
    UC_RHSRTS(R,UCN,T,S,L){tmp} = 0;
""",
            )

    def reduce_exec(
        self: DynsliteVda,
        tmp: str,
    ) -> None:
        if self.tc.container["NORTS"].number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
* Remove from sets timeslices turned off
    RTPS_OFF(RTP(R,T,P),S)$PRC_TS(R,P,S) $= NORTS(R,T,S);
    RTPCS_OUT(RTP(R,T,P),C,S)$RPCS_VAR(R,P,C,S) $= NORTS(R,T,S);
    RTCS_VARC(R,T,C,S){tmp} = NO;
    RCS_COMBAL(R,T,C,S,BD){tmp} = NO;
    RCS_COMPRD(R,T,C,S,BD){tmp} = NO;
    RHS_COMBAL(R,T,C,S){tmp} = NO;
    RHS_COMPRD(R,T,C,S){tmp} = NO;
    RTX_MARK(R,T,ITEM,C,BD,S){tmp} = NO;
""",
            )

    def run_fillparm(
        self: DynsliteVda,
        t: tuple,
    ) -> None:
        fillparm(self, *t)

    def postlev_exec(
        self: DynsliteVda,
        dflbl: str,
        item: str,
        data: str,
        add: str,
        reset: str,
    ) -> None:
        if self.tc.container["NORTS"].number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
    RVP(RTP(R,V,P))$PRC_VINT(R,P)$=PRC_TSL(R,P,'ANNUAL');
    OPTION FIL<DATAYEAR; DATAYEAR(LL)=LASTLL(LL);
    FLO_FUNC(R,LL--ORD(LL),P,CG,CG2,ANNUAL)$(FLO_FUNC(R,LL,P,CG,CG2,ANNUAL)$RVP(R,LL,P))=3;
""",
            )
            # fmt: off
            tl = [
                ( dflbl, item, data, add, reset, "FLO_FUNC", "R", "P,CG,CG2,ANNUAL",     ",'',''",    "V", "RVP(R,V,P)" ">0", "X_RPGGS",   "X_RPGGS"  )
                ( dflbl, item, data, add, reset, "ACT_EFF",  "R", "P,CG,ANNUAL",         ",'','',''", "V", "RVP(R,V,P)" ">0", "X_RPGS",    "X_RPGS"   )
                ( dflbl, item, data, add, reset, "ACT_FLO",  "R", "P,CG,ANNUAL",         ",'','',''", "V", "RVP(R,V,P)" ">0", "X_RPGS",    "X_RPGS"   )
                ( dflbl, item, data, add, reset, "FLO_SUM",  "R", "P,CG1,C,CG2,ANNUAL",  ",''",       "V", "RVP(R,V,P)" ">0", "X_RPGCGS",  "X_RPGCGS" )
            ]
            # fmt: on
            self.run_fillparm(tl[0])
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
    RVP(R,V,P)$(NOT RPS_S1(R,P,'ANNUAL')) = NO;
    ACT_EFF(R,LL--ORD(LL),P,CG,ANNUAL)$(ACT_EFF(R,LL,P,CG,ANNUAL)$RVP(R,LL,P))=3;
    ACT_FLO(R,LL--ORD(LL),P,CG,ANNUAL)$(ACT_FLO(R,LL,P,CG,ANNUAL)$RVP(R,LL,P))=3;
    FLO_SUM(R,LL--ORD(LL),P,CG,C,CG2,ANNUAL)$(FLO_SUM(R,LL,P,CG,C,CG2,ANNUAL)$RVP(R,LL,P))=3;
""",
            )
            for i in range(3):
                self.run_fillparm(tl[i + 1])
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"OPTION DATAYEAR<FIL;",
            )

    def bounds_exec(
        self: DynsliteVda,
        tmp: str,
        swt: str,
        model_name: str,
        var: str,
        var_uc_yes: bool,
    ) -> None:
        if self.tc.container["NORTS"].number_records > 0:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
   OPTION RTC_NET<RHS_COMBAL,RTC_PRD<RHS_COMPRD;
   {model_name}.HOLDFIXED=1;
   {model_name}.SOLVEOPT=1;
   {var}_ACT.FX(RTP_VINTYR(R,V,T,P),S{swt}$PRC_TS(R,P,S)) = 0;
   {var}_FLO.FX(RTP_VINTYR(R,V,T,P),C,S{swt}$RPCS_VAR(R,P,C,S)) = 0;
   {var}_IRE.FX(RTP_VINTYR(R,V,T,P),C,S,IE{swt}$RPCS_VAR(R,P,C,S)) = 0;
   {var}_SIN.FX(RTP_VINTYR(R,V,T,P),C,S{swt}$RPCS_VAR(R,P,C,S)) = 0;
   {var}_SOUT.FX(RTP_VINTYR(R,V,T,P),C,S{swt}$RPCS_VAR(R,P,C,S)) = 0;
   {var}_UPS.FX(RTP_VINTYR(R,V,T,P),S,L{swt}$RPS_UPS(R,P,S)) = 0;
   {var}_UPT.FX(RTP_VINTYR(R,V,T,P),S,UPT{swt}$RPS_UPS(R,P,S)$RP_DP(R,P)) = 0;
   {var}_UDP.FX(RTP_VINTYR(R,V,T,P),S,BD{swt}$PRC_TS(R,P,S)$RP_UPR(R,P,BD)) = 0;
   {var}_COMNET.FX(RTC_NET(R,T,C),S{swt}$COM_TS(R,C,S)) = 0;
   {var}_COMPRD.FX(RTC_PRD(R,T,C),S{swt}$COM_TS(R,C,S)) = 0;
   {f"UC_RHSMAP(R,T,UCN,UC_NUMBER,S){tmp} = NO;" if var_uc_yes else ""}
""",
            )
