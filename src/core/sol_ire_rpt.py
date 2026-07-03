# sol_ire_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOL_FLO - code associated with the substitution of flow variables
# *	%1 - target parameter name
# *	%2 - parameter name suffix
# *	%3 - VAR_FLO suffix (.L or .M)
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolIreRpt(GamsClass):
    """Translation unit for sol_ire.rpt."""

    # Instance attributes
    module_name: str = "sol_ire_rpt"
    gams_source: str = "sol_ire.rpt"

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
        self._set_v_scope(self.arg1, "VAR")

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            v=self.env.v,
            sow=self.env.sow,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
        )

    def _set_v_scope(self, scope: str, value: str) -> None:
        scope_upper = scope.upper()
        if scope_upper == "LOCAL":
            self.env.set_local("v", value)
        elif scope_upper == "GLOBAL":
            self.env.set_global("v", value)
        else:
            self.env.set_scoped("v", value)

    def exec1(
        self: SolIreRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        v: str,
        sow: str,
        rtp_ffcs_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=sol_ire_rpt(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                v=v,
                sow=sow,
                rtp_ffcs_defined=rtp_ffcs_defined,
            ),
        )


def sol_ire_rpt(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    v: str,
    sow: str,
    rtp_ffcs_defined: bool,
) -> str:
    src = "PAR_IRE(R,V,T,P,C,S,IE)"

    sws = (
        f"{v}_IRE.L(R,V,T,P,C,S,IE{arg2})$(NOT RPC_AIRE(R,P,C))"
        f"+({v}_ACT.L(R,V,T,P,S{arg2})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)"
    )

    swd = (
        f"{v}_IRE.M(R,V,T,P,C,S,IE{arg2})$(NOT RPC_AIRE(R,P,C))"
        f"+({v}_ACT.M(R,V,T,P,S{arg2})/PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)"
    )

    if arg4 == ")":
        src = sws
        sws = "0"
        swd = "0"

    mx = ""
    if rtp_ffcs_defined:
        mx = f"(1+RTP_FFCS(R,V,P,COM,COM{sow}))*"

    return rf"""
  OPTION CLEAR=PAR_IRE,CLEAR=PAR_IREM;
  PAR_IRE(RTP_VINTYR(R,V,T,P),C,S,IE)$(RTPCS_VARF(R,T,P,C,S)$RPC_IRE(R,P,C,IE)) = {sws};
  PAR_IREM(RTP_VINTYR(R,V,T,P),C,S,IE)$(RTPCS_VARF(R,T,P,C,S)$RPC_IRE(R,P,C,IE)) = {swd};

* emissions & auxiliary flows from IRE
  F_INOUTS(F_IOSET(R,V,T,P,COM,S,IO)) = {arg3} {mx}
    SUM(RPC_IRE(R,P,C,IE),IRE_FLOSUM(R,T,P,C,S,IE,COM,IO)*({src}{arg4}));
"""
