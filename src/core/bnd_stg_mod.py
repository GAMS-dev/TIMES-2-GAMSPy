# bnd_stg_mod.py
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

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndStgMod(GamsClass):
    """Translation unit for bnd_stg.mod."""

    # Instance attributes
    module_name: str = "bnd_stg"
    gams_source: str = "bnd_stg.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.reset_any_existing_bounds,
            arg1=self.arg1,
            arg3=self.arg3,
            var=self.env.var,
            swd=self.env.swd,
            pgprim=self.env.pgprim,
        )

        self.tc.enqueue(
            self.set_bounds_at_process_activity_level,
            arg1=self.arg1,
            arg2=self.arg2,
            var=self.env.var,
            swd=self.env.swd,
            stages=self.env.stages,
        )

    def reset_any_existing_bounds(
        self: BndStgMod, arg1: str, arg3: str, var: str, swd: str, pgprim: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* reset any existing bounds

  {var}_{arg1}.LO(R,V,T,P,C,S{swd})$PRC_MAP(R,'STG',P) = 0;
  {var}_{arg1}.UP(R,V,T,P,C,S{swd})$PRC_MAP(R,'STG',P) = INF;
  {var}_{arg1}.LO(RTP_VINTYR(R,V,T,P),'{pgprim}',S{swd})$((RPS_STG(R,P,S)->0)$RP_STS(R,P)) = {arg3};
""",
        )

    def set_bounds_at_process_activity_level(
        self: BndStgMod, arg1: str, arg2: str, var: str, swd: str, stages: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* set bounds at process activity level
  TRACKP(RP(R,P))$((NOT PRC_VINT(R,P))$PRC_MAP(R,'STG',P)) = YES;
  STG{arg2}_BND(R,T,P,C,S,BD)$((NOT TOP(R,P,C,'{arg2}'))$RP_STG(R,P)) = 0;
""",
        )

        gams_statement = rf"""
  {var}_{arg1}.LO(RTP_VINTYR(R,T,T,P),C,S{swd})$(RPCS_VAR(R,P,C,S)$TRACKP(R,P)) $= STG{arg2}_BND(R,T,P,C,S,'LO');
  {var}_{arg1}.UP(RTP_VINTYR(R,T,T,P),C,S{swd})$(RPCS_VAR(R,P,C,S)$TRACKP(R,P)) $= STG{arg2}_BND(R,T,P,C,S,'UP');
  {var}_{arg1}.FX(RTP_VINTYR(R,T,T,P),C,S{swd})$(RPCS_VAR(R,P,C,S)$TRACKP(R,P)) $= STG{arg2}_BND(R,T,P,C,S,'FX');
"""
        if stages == "YES":
            code_block = f"LOOP(SW_T(T{swd}),\n{gams_statement});"
        else:
            code_block = gams_statement

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=code_block,
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION CLEAR=TRACKP;",
        )
