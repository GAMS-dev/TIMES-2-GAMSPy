# bnd_act_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_ACT.MOD set the actual bounds for non-vintage VAR_ACTs
# =============================================================================*
# GaG Questions/Comments:
#   - FX take precedence as is set last!!!
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndActMod(GamsClass):
    """Translation unit for bnd_act.mod."""

    # Instance attributes
    module_name: str = "bnd_act"
    gams_source: str = "bnd_act.mod"

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
            self.reset_any_existing_bounds,
            var=self.env.var,
            swd=self.env.swd,
            swt=self.env.swt,
            r_t=self.env.r_t,
        )

        # assign from user data - only set bounds directly at the PRC_TS level
        if self.env.stages == "YES":
            self.env.set_local("swt", f"SW_T(T{self.env.swd})$")

        self.tc.enqueue(
            self.reset_any_existing_bounds2,
            var=self.env.var,
            swd=self.env.swd,
            swt=self.env.swt,
            r_t=self.env.r_t,
        )

    def reset_any_existing_bounds(self: BndActMod, var: str, swd: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* reset any existing bounds
  {var}_ACT.LO(R,V,T,P,S{swd}) = 0;
  {var}_ACT.UP(R,V,T,P,S{swd}) = INF;
""",
        )

    def reset_any_existing_bounds2(
        self: BndActMod, var: str, swd: str, swt: str, r_t: str
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {var}_ACT.LO(RTP_VINTYR(R,T,T,P),S{swd})$({swt} PRC_TS(R,P,S) * (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'LO');
  {var}_ACT.UP(RTP_VINTYR(R,T,T,P),S{swd})$({swt} PRC_TS(R,P,S) * (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'UP');
  {var}_ACT.FX(RTP_VINTYR({r_t},T,P),S{swd})$({swt}PRC_TS(R,P,S)* (NOT PRC_VINT(R,P))) $= ACT_BND(R,T,P,S,'FX');
* for upper bounds of zero, activity variables of all vintages can be bounded to zero
  {var}_ACT.UP(RTP_VINTYR(R,V,T,P),S{swd})$({swt} PRC_TS(R,P,S) * PRC_VINT(R,P)$RTPS_OFF(R,T,P,S)) = EPS;
""",
        )
