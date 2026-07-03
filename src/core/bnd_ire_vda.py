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

from gamspy import Card, Parameter

from core.base_class import GamsClass
from core.fillcost_gms import FillcostGms, FillcostGmsConfig

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
        g = self.tc
        m = g.container

        if not self.tc.defined_assigned(g.Premile):
            return

        self.tc.enqueue(self.exec1)

        g.flo_ire = Parameter(
            m, name="FLO_IRE", domain=[g.r, g.ll, g.p, g.c, g.s, g.ie]
        )

        self.tc.enqueue(self.exec2, var=self.env.var, swd=self.env.swd)

        # fmt: off
        batincludes = [
            FillcostGmsConfig(arg1=g.flo_ire, arg2=g.r, arg3=(g.p,g.c,g.ts,g.ie), arg4=('0',), arg5=g.Fil, arg6=Card(g.Fil), bext=1, fext=1, arg9=g.flo_ire, arg10="X_IREFLO"),
            FillcostGmsConfig(arg1=g.par_ipric, arg2=g.r, arg3=(g.p,g.c,g.ts,g.ie), arg4=('0',), arg5=g.Fil, arg6=Card(g.Fil), bext=1, fext=1, arg9=g.par_ipric, arg10="X_IREFLO")
        ]
        # fmt: on

        for config in batincludes:
            self.include(FillcostGms(tc=self.tc, env=self.env, config=config))

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
