# sol_ire_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * SOL_IRE - basic solution parameters for IRE flows and auxiliaries
# *==============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Number, Sum

from core.base_class import GamsClass
from core.utils import apply_v_scope, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class SolIreRptConfig:
    """Strongly typed data contract for sol_ire.rpt."""

    # %1 - scope for compile-time var "V"
    arg1: Literal["", "LOCAL", "GLOBAL"] = ""
    # %2 - extra trailing index of the VAR_IRE/VAR_ACT solution values, e.g. (g.Sow,)
    arg2: tuple[SET_OR_ALIAS, ...] | tuple[()] = ()
    # %3 - sum domain and multiplier of the F_INOUTS right-hand side,
    #      e.g. (g.SwT[g.t, g.Sow], g.sw_tprob[g.t, g.Sow]) for SUM(SW_T(T,SOW),SW_TPROB(T,SOW)*
    arg3: tuple[ImplicitSet, ImplicitParameter] | None = None
    # %4 - True where the legacy '%4' was ) (closing %3's SUM)
    arg4: bool = False


class SolIreRpt(GamsClass):
    """Translation unit for sol_ire.rpt."""

    # Instance attributes
    module_name: str = "sol_ire_rpt"
    gams_source: str = "sol_ire.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: SolIreRptConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        # sol_ire.rpt:8 `SET%1 V VAR`, see SolFloRed.compile() for why a
        # $SETGLOBAL has to be resolved on this class's own env here.
        apply_v_scope(self.env, self.config.arg1, "VAR")

        self.tc.enqueue(
            self.exec_sol_ire_rpt,
            config=self.config,
            v=self.env.v,
            sow=self.env.sow_GP,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
        )

    def exec_sol_ire_rpt(
        self: SolIreRpt,
        config: SolIreRptConfig,
        v: str,
        sow: SowGPType,
        rtp_ffcs_defined: bool,
    ) -> None:
        sol_ire_rpt_GP(
            g=self.tc,
            config=config,
            v=v,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )


def sol_ire_rpt_GP(
    g: TimesModelClass,
    config: SolIreRptConfig,
    v: str,
    sow: SowGPType,
    rtp_ffcs_defined: bool,
) -> None:
    """Native GAMSPy counterpart of sol_ire_rpt().

    As in sol_flo_red_GP, `SET%1 V VAR` resolves V to VAR unless %1 is GLOBAL,
    in which case `v` must already be resolved by the caller (SolIreRpt.compile()).
    """
    cc = config
    if cc.arg1 != "GLOBAL":
        v = "VAR"
    VAR_IRE = g.get_variable(f"{v}_IRE")
    VAR_ACT = g.get_variable(f"{v}_ACT")

    # $SET SRC 'PAR_IRE(R,V,T,P,C,S,IE)'
    src: ImplicitParameter | Expression | Number = g.par_ire[
        g.r, g.v, g.t, g.p, g.c, g.s, g.ie
    ]
    # $SET SWS / $SET SWD
    sws: Expression | Number = (
        VAR_IRE.l[g.r, g.v, g.t, g.p, g.c, g.s, g.ie, *cc.arg2].where[
            ~g.RpcAire[g.r, g.p, g.c]
        ]
        + (
            VAR_ACT.l[g.r, g.v, g.t, g.p, g.s, *cc.arg2]
            * g.prc_actflo[g.r, g.v, g.p, g.c]
        ).where[g.RpcAire[g.r, g.p, g.c]]
    )
    swd: Expression | Number = (
        VAR_IRE.m[g.r, g.v, g.t, g.p, g.c, g.s, g.ie, *cc.arg2].where[
            ~g.RpcAire[g.r, g.p, g.c]
        ]
        + (
            VAR_ACT.m[g.r, g.v, g.t, g.p, g.s, *cc.arg2]
            / g.prc_actflo[g.r, g.v, g.p, g.c]
        ).where[g.RpcAire[g.r, g.p, g.c]]
    )
    # $IF '%4'==) $SET SRC '%SWS%' SET SWS '0' SET SWD 0
    if cc.arg4:
        src, sws, swd = sws, Number(0), Number(0)

    g.par_ire.setRecords(None)
    g.par_irem.setRecords(None)
    g.par_ire[g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.s, g.ie].where[
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s].where[g.RpcIre[g.r, g.p, g.c, g.ie]]
    ] = sws
    g.par_irem[g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.s, g.ie].where[
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s].where[g.RpcIre[g.r, g.p, g.c, g.ie]]
    ] = swd

    # * emissions & auxiliary flows from IRE
    # $IF DEFINED RTP_FFCS $SET MX "(%SHFF%S(R,V,P,COM,COM%SOW%))*"
    mx = (
        (1 + g.rtp_ffcs[g.r, g.v, g.p, g.Com, g.Com, *sow])
        if rtp_ffcs_defined
        else Number(1)
    )
    g.f_inouts[g.FIoset[g.r, g.v, g.t, g.p, g.Com, g.s, g.io]] = wrap_in_sum(
        mx
        * Sum(
            g.RpcIre[g.r, g.p, g.c, g.ie],
            g.ire_flosum[g.r, g.t, g.p, g.c, g.s, g.ie, g.Com, g.io] * src,
        ),
        cc.arg3,
    )


# NOTE: The module-level raw-GAMS-string generator below is kept because
# rptlite_rpt, rptmain_stc, rpt_ext_mlf and solprep_msa still splice it into
# larger raw GAMS blocks. Delete it once those call sol_ire_rpt_GP instead.
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
