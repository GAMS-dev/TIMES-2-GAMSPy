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
from typing import TYPE_CHECKING, Literal

from core.base_class import GamsClass
from core.utils import apply_v_scope

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
        # sol_ire.rpt:8 `SET%1 V VAR`. Verified against real GAMS (see
        # sol_ire_rpt()'s docstring): a $SETGLOBAL is a no-op if an
        # ancestor's own env already has a scoped/local V - only
        # resolvable from this class's own (still-live) self.env, at
        # arg1=self.arg1,
        # compile time, before enqueueing exec1. LOCAL/scoped (the
        # non-GLOBAL default) never needs this: sol_ire_rpt always
        # resolves that case to VAR on its own.
        apply_v_scope(self.env, self.arg1, "VAR")

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            v=self.env.v,
            sow=self.env.sow,
            mx=self.env.mx,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
        )

    def exec1(
        self: SolIreRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        v: str,
        sow: str,
        mx: str,
        rtp_ffcs_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=sol_ire_rpt(
                arg1=arg1,  # type: ignore[arg-type]
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                v=v,
                sow=sow,
                mx=mx,
                rtp_ffcs_defined=rtp_ffcs_defined,
            ),
        )


def sol_ire_rpt(
    *,
    arg1: Literal["", "LOCAL", "GLOBAL"] = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    v: str,
    sow: str,
    mx: str,
    rtp_ffcs_defined: bool,
) -> str:
    """sol_ire.rpt:8's `SET%1 V VAR`.

    Verified against real GAMS (a minimal $SET/$BATINCLUDE repro, checked
    with $log): this unconditionally resolves V to the literal VAR whenever
    arg1 is "" or "LOCAL" - regardless of any caller state - so `v` is
    overridden to "VAR" here in that case, ignoring whatever the caller
    passed. But a $SETGLOBAL (arg1="GLOBAL") turned out to be a complete
    no-op whenever an ancestor file already has an active (local or scoped)
    V of its own: the ancestor's value wins outright, not just on return
    but even within sol_ire.rpt's own remaining body. Whether that's the
    case here depends on the CALLER's own CompileEnvironment (e.g.
    RptmainStc may have already scoped-set "v" before including SolIreRpt),
    which this stateless function has no access to - so for arg1="GLOBAL",
    the passed-in `v` is used as-is: it must already be pre-resolved by
    SolIreRpt.compile() (via apply_v_scope on its own self.env, before
    enqueuing exec1).
    """
    if arg1 != "GLOBAL":
        v = "VAR"
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
