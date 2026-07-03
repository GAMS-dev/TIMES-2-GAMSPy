# eqcaflac_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAFLAC - implements commodity-specific capacity utilization equations
# *   arg1 - equation declaration type
# *   arg2 - bound type for arg1
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT/COEF_AF are defined in COEF_CPT.MOD
# *  - shaping of COEF_AF is possible via NCAP_AFX
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcaflacVda(GamsClass):
    """Translation unit for eqcaflac.vda."""

    # Instance attributes
    module_name: str = "eqcaflac_vda"
    gams_source: str = "eqcaflac.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        self.comp1(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            swt=self.env.swt,
            sow=self.env.sow,
            rcapsbm=self.env.rcapsbm,
            upscap0=self.env.upscap0,
            varm=self.env.varm,
            sws=self.env.sws,
            var=self.env.var,
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
        )
        if self.arg3 == "$":  # L37: %3 EXIT arg3 could be either [$, *]
            return

        self.comp2(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t,
            rts=self.env.rts,
            swt=self.env.swt,
            sow=self.env.sow,
            rcapsbm=self.env.rcapsbm,
            upscap0=self.env.upscap0,
            varm=self.env.varm,
            sws=self.env.sws,
            var=self.env.var,
            cal_red=self.env.cal_red,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            arg1=self.arg1,
            arg2=self.arg2,
        )

    def comp1(
        self: EqcaflacVda,
        eq: str,
        r_v_t: str,
        swt: str,
        sow: str,
        rcapsbm: str,
        upscap0: str,
        varm: str,
        sws: str,
        var: str,
        arg1: str,
        arg2: str,
        arg4: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}{arg1}_CAFLAC(RTP_VINTYR({r_v_t},P),S{swt})$(AFS(R,T,P,S,{arg2})$RPS_CAFLAC(R,P,S,{arg2}))..

* Sum over flows in PG
    SUM((RPC_PG(R,P,C),COM_TMAP(R,COM_TYPE(CG),C)),
        (1/ABS(PRC_ACTFLO(R,V,P,C))) /
        (NCAP_AFCS(R,V,P,C,S)+PROD(XPT$NCAP_AFCS(R,V,P,CG,S),NCAP_AFCS(R,V,P,CG,S))$(NOT NCAP_AFCS(R,V,P,C,S))) *
        SUM(RPCS_VAR(R,P,C,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS) * ({var}_FLO(R,V,T,P,C,TS {sow})$RP_STD(R,P) +
          (SUM(TOP(RPC_STG(R,P,C),IO)$(NCAP_AFCS(R,V,P,C,S)+NCAP_AFCS(R,V,P,CG,S)),
            ({var}_SIN(R,V,T,P,C,TS {sow})*PROD(RPG_AFCX(R,P,C,IE)$NCAP_AFCS(R,V,P,C,S),(NCAP_AFCS(R,V,P,C,S)/NCAP_AFCS(R,V,P,CG,S))$NCAP_AFCS(R,V,P,CG,S)))$IPS(IO)+
            ({var}_SOUT(R,V,T,P,C,TS {sow})*STG_EFF(R,V,P)*(1+RTCS_FR(R,T,C,S,TS)))$(NOT IPS(IO))) +
           SUM(RPC_IRE(R,P,C,IE),{var}_IRE(R,V,T,P,C,TS,IE {sow})*PROD(RPG_AFCX(R,P,C,IE)$((NCAP_AFCS(R,V,P,C,S)$NCAP_AFCS(R,V,P,CG,S))**1$RP_AIRE(R,P,IE)),
             (NCAP_AFCS(R,V,P,C,S)/NCAP_AFCS(R,V,P,CG,S))$NCAP_AFCS(R,V,P,CG,S))+1$0))$(NOT RP_STD(R,P)))))

  ={arg1}=

* process capacity - vintaged or not
    (SUM(RVP_KMAP(R,V,P,MODLYEAR(K)),COEF_VNT(R,T,P,K) * COEF_AF{arg4}(R,K,T,P,S,{arg2}) *
       ({varm}_NCAP(R,K,P{sws})$T(K)+NCAP_PASTI(R,K,P)$PYR(K){rcapsbm}))+COEF_AF{arg4}(R,V,T,P,S,{arg2})*{upscap0}) *
* timeslice fraction of capacity
    PRC_CAPACT(R,P) * G_YRFR(R,S)
  ;
""",
        )

    def comp2(
        self: EqcaflacVda,
        eq: str,
        r_v_t: str,
        rts: str,
        swt: str,
        sow: str,
        rcapsbm: str,
        upscap0: str,
        varm: str,
        sws: str,
        var: str,
        cal_red: str,
        pgprim: str,
        def_rtp_ffcs: bool,
        arg1: str,
        arg2: str,
    ) -> None:
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red as cal_red_func
        else:
            raise ValueError(f"Unexpected value for cal_red: {self.env.cal_red}")

        include_cal_red = cal_red_func(
            var=var,
            sow=sow,
            pgprim=pgprim,
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            def_rtp_ffcs=def_rtp_ffcs,
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}L_CAPFLO(RTP_VINTYR({r_v_t},P),CG,SL(STL({rts})){swt})$(RS_TSLVL(R,S)$NCAP_AFC(R,V,P,CG,STL))..

* Sum over regular flows
    SUM(RPC(RP_FLO(R,P),C)$COM_GMAP(R,CG,C),
      SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))*
{include_cal_red}
       )) +
* storage: for activity multiply by number of storage cycles in a year
    SUM(PRC_TS(RP_STG(R,P),TS)$RS_FR(R,TS,S),({var}_ACT(R,V,T,P,TS{sow})+VAR_STS(R,V,T,P,TS,{arg2}))*RS_FR(R,TS,S)*EXP(PRC_SC(R,P))/RS_STGPRD(R,TS)*G_YRFR(R,S))$ACTCG(CG) +
    SUM(RPC_STG(R,P,C)$COM_GMAP(R,CG,C),
      SUM((TOP(R,P,C,IO),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))*
        ({var}_SIN(R,V,T,P,C,TS{sow})$(NOT TOP(R,P,C,'OUT'))$IPS(IO)+{var}_SOUT(R,V,T,P,C,TS{sow})*STG_EFF(R,V,P)*DIAG(IO,'OUT'))))

  ={arg1}=

* process capacity - vintaged or not
    (SUM(RVP_KMAP(R,V,P,MODLYEAR(K)),COEF_VNT(R,T,P,K) *
       ({varm}_NCAP(R,K,P{sws})$T(K)+NCAP_PASTI(R,K,P)$PYR(K){rcapsbm}))+{upscap0})*NCAP_AFC(R,V,P,CG,STL) *
* timeslice fraction of capacity
    PRC_CAPACT(R,P) * G_YRFR(R,S)
  ;
""",
        )
