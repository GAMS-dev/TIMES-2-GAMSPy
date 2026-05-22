# bnd_ire_vda.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_STG.MOD set the actual bounds for non-vintage VAR_SIN/OUT
#    %1 - which variable
#    %2 - which bound
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillcost_gms import FillcostGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndIreVda(GamsClass):
    """Translation unit for bnd_ire.vda."""

    # Instance attributes
    module_name: str = "bnd_ire"
    gams_source: str = "bnd_ire.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if not self.tc.defined("PREMILE"):
            return

        self.tc.enqueue(self.exec1)

        self.tc.add_gams_code(
            module=self, phase="init", code=" PARAMETER FLO_IRE(R,LL,P,C,S,IE);"
        )

        self.tc.enqueue(self.exec2, var=self.env.var, swd=self.env.swd)

        # fmt: off
        batincludes = [
            ("FLO_IRE", "R", 'P,C,TS,IE', ",'0'", "FIL", "CARD(FIL)", '', '', "FLO_IRE", "X_IREFLO"),
            ("PAR_IPRIC", "R", 'P,C,TS,IE', ",'0'", "FIL", "CARD(FIL)", '', '', "PAR_IPRIC", "X_IREFLO")
        ]
        # fmt: on

        for arg in batincludes:
            self.include(
                FillcostGms(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8],
                    arg10=arg[9],
                )
            )

        self.tc.enqueue(self.exec3, var=self.env.var, swd=self.env.swd)

    def exec1(self: BndIreVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
 RPC_IREIN(RPC_IREIO) = NO;
 PAR_IRE(R,V,T,P,C,TS,IE)$(NOT RPC_IREIN(R,P,C,IE,'IN')) = 0;
 PAR_IPRIC(R,T,P,C,TS,IE)$(NOT RPC_IREIN(R,P,C,IE,'IN')) = 0;

""",
        )

    def exec2(self: BndIreVda, var: str, swd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 IF(CARD(PAR_IRE),
  {var}_IRE.FX(RTP_VINTYR(R,V,PREMILE(T),P),C,TS,IE{swd})$(((NOT RPC_AIRE(R,P,C))*RPCS_VAR(R,P,C,TS))$RPC_IREIN(R,P,C,IE,'IN')) =
     EPS+PAR_IRE(R,V,T,P,C,TS,IE);
  LOOP(IE,FLO_BND(R,PREMILE(T),P,C,TS,'FX')$((RPC_AIRE(R,P,C)*RTPCS_VARF(R,T,P,C,TS))$RPC_IREIN(R,P,C,IE,'IN')) =
           EPS+SUM(RTP_VINTYR(R,V,T,P),PAR_IRE(R,V,T,P,C,TS,IE)));
 );
* Set target milestone years into FIL
 OPTION CLEAR=FIL; LOOP(T$(NOT PREMILE(T)),FIL(TT)$YK(TT,T) = YES);
* Calculate total flows at milestone years
 FLO_IRE(R,PREMILE,P,C,TS,IE)$(RPCS_VAR(R,P,C,TS)$RPC_IREIN(R,P,C,IE,'IN')) =
    SUM(YK(PREMILE,LL)$PAR_IRE(R,LL,PREMILE,P,C,TS,IE),PAR_IRE(R,LL,PREMILE,P,C,TS,IE))+EPS;
 DM_YEAR(PREMILE) = YES;
""",
        )

    def exec3(self: BndIreVda, var: str, swd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set bounds for T not in sync with PREMILE
 LOOP(IE$CARD(FIL),TRACKPC(R,P,C)$((RPC_AIRE(R,P,C)+PRC_VINT(R,P))$RPC_IREIN(R,P,C,IE,'IN')) = YES);
 {var}_IRE.FX(RTP_VINTYR(R,FIL(T),T,P),C,TS,IE{swd})$(((NOT TRACKPC(R,P,C))*RPCS_VAR(R,P,C,TS))$RPC_IREIN(R,P,C,IE,'IN')) =
     EPS+FLO_IRE(R,T,P,C,TS,IE);
* Remove TRACKPC with either IMP or EXP internal, as FLO_BND will be applied to the SUM
 LOOP(IE,TRACKPC(R,P,C)$((NOT RPC_IREIN(R,P,C,IE,'IN'))$RPC_IRE(R,P,C,IE)) = NO);
 FLO_BND(R,FIL(T),P,C,TS,'FX')$((RPC_AIRE(R,P,C)*RTPCS_VARF(R,T,P,C,TS))$TRACKPC(R,P,C)) =
      EPS+SUM(RPC_IREIN(R,P,C,IE,'IN'),FLO_IRE(R,T,P,C,TS,IE));
 OPTION CLEAR=TRACKPC,CLEAR=FLO_IRE;
* Set the IRE prices
 LOOP(T$CARD(PAR_IPRIC),
   OBJ_IPRIC(R,Y_EOH,P,C,TS,IE,CUR)$(PERIODYR(T,Y_EOH)$RPCS_VAR(R,P,C,TS)$RPC_IREIN(R,P,C,IE,'IN')) =
     PAR_IPRIC(R,T,P,C,TS,IE));
""",
        )
