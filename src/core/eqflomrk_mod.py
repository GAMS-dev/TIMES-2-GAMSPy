# eqflomrk_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================================================*
# * EQx_FLMRK is a market share constraint for a commodity flow of a process
# *   arg1 - equation declaration type
# *   arg2 - BOUND type for arg1
# *==================================================================================================*
# * Comments:
# *---------------------------------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqflomrkMod(GamsClass):
    """Translation unit for eqflomrk.mod."""

    # Instance attributes
    module_name: str = "eqflomrk_mod"
    gams_source: str = "eqflomrk.mod"

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
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        if self.arg2 == "":
            self.comp1()
            self.tc.enqueue(
                self.exec1,
            )
        else:  # EQUDEF
            self.env.set_local("ired", "")
            if self.env.reduce == "YES":
                self.env.set_local(
                    "ired",
                    f"$(NOT RPC_AIRE(R,P,C))+{self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,C)$RPC_AIRE(R,P,C)",
                )
            # * For IRE/STG: Output flow from process if PRC_MARK >= 0, Input flow if PRC_MARK <= 0
            self.env.set_local("sigo", f"(PRC_MARK(R,T,P,ITEM,COM,'{self.arg2}') GE 0)")
            self.env.set_local("sigi", f"(PRC_MARK(R,T,P,ITEM,COM,'{self.arg2}') LE 0)")
            self.equation_def(
                arg1=self.arg1,
                arg2=self.arg2,
                eq=self.env.eq,
                r_t=self.env.r_t,
                swt=self.env.swt,
                var=self.env.var,
                sow=self.env.sow,
                ired=self.env.ired,
                sigo=self.env.sigo,
                sigi=self.env.sigi,
            )

    def comp1(self: EqflomrkMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
SET RTX_MARK(R,T,ITEM,C,BD,S) //;
SET RX_MARK(R,YEAR,ITEM,C,BD) //;
SET RTP_MRK(REG,T,P,ITEM,COM,BD);
SET RTX_MRK(REG,T,ITEM,COM,BD);
SET RMKC(REG,ITEM,COM) //;
""",
        )

    def equation_def(
        self: EqflomrkMod,
        arg1: str,
        arg2: str,
        eq: str,
        r_t: str,
        swt: str,
        var: str,
        sow: str,
        ired: str,
        sigo: str,
        sigi: str,
    ) -> None:
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red as cal_red_func

        include_cal_red = cal_red_func(
            arg1="C",
            arg2="COM1",
            arg3="TS",
            arg4="P",
            arg5="T",
            var=self.env.var,
            sow=self.env.sow,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}{arg1}_FLOMRK({r_t},ITEM,COM,S {swt})$RTX_MARK(R,T,ITEM,COM,'{arg2}',S)..

* Sum over all processes with PRC_MARK(COM) (not just capacity-related)

    SUM((COM_GMAP(R,COM,C),RPC(R,P,C))$PRC_MARK(R,T,P,ITEM,COM,'{arg2}'),
      POWER(PRC_MARK(R,T,P,ITEM,COM,'{arg2}'),1$RX_MARK(R,'0',ITEM,COM,'{arg2}')-1) *

* Sum over all COMPRD balance variables related to timeslice S
      SUM(RHS_COMPRD(R,T,C,SL)$RS_FR(R,S,SL),

* Sum over all flow variables related to balance timeslice
         (SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,SL,TS),
              SUM(RTP_VNTBYR(R,T,P,V),
{include_cal_red}
                 ) *
* Balance coarser than variable or balance finer than variable
              RS_FR(R,SL,TS)*(1+RTCS_FR(R,T,C,SL,TS))
         )*(1+(COM_IE(R,T,C,SL)-1)$TOP(R,P,C,'OUT')))$RP_STD(R,P)

* Inter-regional trade contribution
       + SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,SL,TS),
           SUM(RTP_VNTBYR(R,T,P,V),
             (({var}_IRE(R,V,T,P,C,TS,'IMP'{sow}){ired})*(1+IRE_FLOSUM(R,T,P,C,S,'IMP',C,'OUT'))*COM_IE(R,T,C,SL))$({sigo}$RPC_IRE(R,P,C,'IMP'))-
             (({var}_IRE(R,V,T,P,C,TS,'EXP'{sow}){ired})*(1+IRE_FLOSUM(R,T,P,C,S,'EXP',C,'IN')))$({sigi}$RPC_IRE(R,P,C,'EXP'))) *
* Balance coarser than variable or balance finer than variable
           RS_FR(R,SL,TS)*(1+RTCS_FR(R,T,C,SL,TS)))$RP_IRE(R,P)

* Storage contribution
       + SUM(RPCS_VAR(RPC_STG(R,P,C),TS)$RS_FR(R,SL,TS),
             SUM(RTP_VNTBYR(R,T,P,V),
               (({var}_SOUT(R,V,T,P,C,TS {sow})*STG_EFF(R,V,P)*COM_IE(R,T,C,SL))${sigo}-{var}_SIN(R,V,T,P,C,TS {sow})${sigi})) *
* Balance coarser than variable or balance finer than variable
             RS_FR(R,SL,TS)*(1+RTCS_FR(R,T,C,SL,TS)))$PRC_MAP(R,'STG',P)

       ))

      ={arg1}=

* Reference is the COMPRD variable
  SUM((COM_GMAP(R,COM,C),RHS_COMPRD(R,T,C,SL))$RS_FR(R,S,SL),{var}_COMPRD(R,T,C,SL {sow})) *
  PROD(RX_MARK(R,LL,P(ITEM),COM,'{arg2}'),PRC_MARK(R,T,P,P,COM,'{arg2}')$LASTLL(LL))

;
""",
        )

    def exec1(self: EqflomrkMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Remove superfluous data points
 PRC_MARK(R,LL,P,ITEM,C,BDNEQ)$PRC_MARK(R,LL,P,ITEM,C,'FX') = NO;
 PRC_MARK(R,LL,P,ITEM,C,BD)$((NOT RTP_VARA(R,LL,P))$(NOT SAMEAS(P,ITEM))$PRC_MARK(R,LL,P,ITEM,C,BD)) = NO;

* Partitioning flags by type
 LOOP(T,RX_MARK(R,'0',P,C,BD)$((PRC_MARK(R,T,P,P,C,BD)$RP_STD(R,P)>=0)$PRC_MARK(R,T,P,P,C,BD)) = YES);
 RX_MARK(R,T--ORD(T),P,C,BD) $= PRC_MARK(R,T,P,P,C,BD)$(NOT RX_MARK(R,'0',P,C,BD));
* Eliminate zero values; For standard processes set flow bound
 RTP_MRK(RTP_VARA(R,T,P),ITEM,C,BD)$((PRC_MARK(R,T,P,ITEM,C,BD)=0)$PRC_MARK(R,T,P,ITEM,C,BD)) = YES;
 RTP_MRK(RTP_VARA(R,T,P),PRC,C,BD)$(PRC_MARK(R,T,PRC,PRC,C,BD)$RX_MARK(R,'0',PRC,C,BD)) = NO;
 LOOP(RTP_MRK(R,T,P,ITEM,C,BDUPX(BD))$RP_STD(R,P),FLO_BND(R,T,P,C,ANNUAL,BD) = EPS);
 PRC_MARK(RTP_MRK) = 0;
* Make sure that data for all PRC in group are forward extrapolated
 OPTION CLEAR=RXX, CLEAR=YK1, CLEAR=RTP_MRK;
 RTP_MRK(RTP_VARA(R,T,P),ITEM,C,BD)$PRC_MARK(R,T,P,ITEM,C,BD) = YES;
 YK1(T,TT(T+1)) = YES;
 LOOP(YK1(TT,T),PRC_MARK(RTP_VARA(R,T,P),ITEM,C,BD)$(NOT PRC_MARK(R,T,P,ITEM,C,BD)) $= PRC_MARK(R,TT,P,ITEM,C,BD));
 OPTION RTX_MRK <= RTP_MRK, RMKC <= RTX_MRK, FIN <= RMKC;
 PRC_MARK(R,T,P,ITEM,C,BD)$(NOT RTX_MRK(R,T,ITEM,C,BD)) = 0;

* Add ANNUAL level for PRC_MARK group commodities not in TOP
 FIN(RC) = NO; COM_TSL(FIN,'ANNUAL')$(NOT SUM(COM_TSL(FIN,TSL),1)) = YES;
* Prepare the COMPRD variables for all PRC_MARK parameters:
 LOOP(RMKC(R,ITEM,C),TRACKC(RC(R,COM))$COM_GMAP(R,C,COM) = YES);
 RHS_COMPRD(RTCS_VARC(R,T,C,S))$TRACKC(R,C) = YES;
 RXX(RMKC)=YES; OPTION CLEAR=TRACKC,CLEAR=RMKC;
* If ITEM is also P (ala FLO_MARK), or C is not in TOP, use commodity timeslices; else use ANNUAL
 RMKC(RXX(RPC)) = YES; RMKC(RXX(R,ITEM,C)) $= FIN(R,C);
 RMKC(R,ITEM,C)$COM_TSL(R,C,'ANNUAL') = NO; OPTION FIN <= RMKC;
 LOOP(COM_TSL(FIN(R,C),TSL),RTX_MARK(RTX_MRK(R,T,ITEM,C,BD),S)$(RMKC(R,ITEM,C)$TS_GROUP(R,TSL,S)) = YES);
 RTX_MARK(RTX_MRK(R,T,ITEM,C,BD),ANNUAL)$(NOT RMKC(R,ITEM,C))=YES;
 RMKC(RXX(R,ITEM,C))=YES; OPTION CLEAR=FIN,CLEAR=RTX_MRK,CLEAR=RTP_MRK;
""",
        )
