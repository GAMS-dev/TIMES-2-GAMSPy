# bnd_flo_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_FLO.MOD set the actual bounds for non-vintage VAR_FLOs                  *
# =============================================================================*
# UR Questions/Comments:
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndFloMod(GamsClass):
    """Translation unit for bnd_flo.mod."""

    # Instance attributes
    module_name: str = "bnd_flo"
    gams_source: str = "bnd_flo.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_bnd_flo_mod,
            stages=self.env.stages,
            reduce=self.env.reduce,
            var=self.env.var,
            swd=self.env.swd,
            swt=(
                f"{self.env.swd})$SW_T(T{self.env.swd}"
                if self.env.reduce == "YES" and self.env.stages == "YES"
                else self.env.swt
            ),
        )

    def exec_bnd_flo_mod(
        self: "BndFloMod",
        stages: str,
        reduce: str,
        var: str,
        swd: str,
        swt: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=bnd_flo_mod(
                stages=stages,
                reduce=reduce,
                var=var,
                swd=swd,
                swt=swt,
            ),
        )


def bnd_flo_mod(
    *,
    stages: str,
    reduce: str,
    var: str,
    swd: str,
    swt: str,
) -> str:
    base_statement = rf"""
  {var}_FLO.LO(RTP_VINTYR(R,T,T,P),C,S{swd})$((RTPCS_VARF(R,T,P,C,S)*TRACKPC(R,P,C))$FLO_BND(R,T,P,C,S,'LO')) = FLO_BND(R,T,P,C,S,'LO');
  {var}_FLO.UP(RTP_VINTYR(R,T,T,P),C,S{swd})$((RTPCS_VARF(R,T,P,C,S)*TRACKPC(R,P,C))$FLO_BND(R,T,P,C,S,'UP')) = FLO_BND(R,T,P,C,S,'UP');
  {var}_FLO.FX(RTP_VINTYR(R,T,T,P),C,S{swd})$((RTPCS_VARF(R,T,P,C,S)*TRACKPC(R,P,C))$FLO_BND(R,T,P,C,S,'FX')) = FLO_BND(R,T,P,C,S,'FX');
"""
    return rf"""
* reset any existing bounds
  {var}_FLO.LO(R,V,T,P,C,S{swd}) = 0;
  {var}_FLO.UP(R,V,T,P,C,S{swd}) = INF;

* assign from user data
  FLO_BND(R,T,P,C,S,'LO')$((NOT RPC_EMIS(R,P,C))$(FLO_BND(R,T,P,C,S,'LO')=0)$RP_FLO(R,P))=0;
  LOOP((RTPC(R,T,P,C),S,BD)$FLO_BND(RTPC,S,BD),TRACKPC(RP_FLO(R,P),C)=YES);
  TRACKPC(PRC_VINT(R,P),C) = NO;
  TRACKPC(RPC_FFUNC(R,P,C))= NO;
  TRACKPC(RPC_EMIS(R,P,C)) = NO;
* Mark all tuples that definitely cannot be handled by VAR bounds
  LOOP(T,FLO_BND(R,'%DFLBL%',P,C,S,BD)$FLO_BND(R,T,P,C,S,BD) = EPS$(NOT TRACKPC(R,P,C));
         FLO_BND(R,'%DFLBL%',P,CG,S,BD)$((NOT C(CG))$FLO_BND(R,T,P,CG,S,BD)) = EPS);
  TRACKPC(RPC_ACT(R,P,C)) = NO;
{f"LOOP(SW_T(T{swd}), {base_statement} );" if stages == "YES" else base_statement}
OPTION CLEAR=TRACKPC;

{
        rf'''
* As BND_ACT has been set before this, MAX/MIN can be used; FX bound consistency cannot be guaranteed
 LOOP(RTPCS_VARF(R,T,P,C,S)$(((NOT PRC_VINT(R,P))*RPC_ACT(R,P,C))$FLO_BND(R,T,P,C,S,'LO')),{var}_ACT.LO(R,T,T,P,S{swt}) = MAX({var}_ACT.LO(R,T,T,P,S{swt}),FLO_BND(R,T,P,C,S,'LO')/PRC_ACTFLO(R,T,P,C)));
 LOOP(RTPCS_VARF(R,T,P,C,S)$(((NOT PRC_VINT(R,P))*RPC_ACT(R,P,C))$FLO_BND(R,T,P,C,S,'UP')),{var}_ACT.UP(R,T,T,P,S{swt}) = MIN({var}_ACT.UP(R,T,T,P,S{swt}),FLO_BND(R,T,P,C,S,'UP')/PRC_ACTFLO(R,T,P,C)));
 LOOP(RTPCS_VARF(R,T,P,C,S)$(((NOT PRC_VINT(R,P))*RPC_ACT(R,P,C))$FLO_BND(R,T,P,C,S,'FX')),{var}_ACT.FX(R,T,T,P,S{swt}) = FLO_BND(R,T,P,C,S,'FX')/PRC_ACTFLO(R,T,P,C));
'''
        if reduce == "YES"
        else ""
    }
"""
