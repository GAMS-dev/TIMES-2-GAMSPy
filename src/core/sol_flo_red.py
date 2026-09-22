# sol_flo_red.py
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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Sum, sparse

from core.base_class import GamsClass
from core.utils import SET_OR_ALIAS, apply_v_scope
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Parameter, Set
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class SolFloRedConfig:
    arg1: str = ""  # target parameter name
    arg2: str = ""  # parameter name suffix
    arg3: Literal["", ".L", ".M"] = ""  # VAR_FLO suffix
    arg4: Literal["", "LOCAL", "GLOBAL"] = ""  # scope for compile-time var "V"
    arg5: tuple[SET_OR_ALIAS] | tuple[()] = ()
    arg6: SET_OR_ALIAS | Number = field(default_factory=lambda: Number(1))


class SolFloRed(GamsClass):
    """Translation unit for sol_flo.red."""

    module_name: str = "sol_flo_red"
    gams_source: str = "sol_flo.red"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: SolFloRedConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        cc = self.config

        # sol_flo.red:11 `SET%4 V VAR`. Verified against real GAMS (see
        # sol_flo_red_GP's docstring): a $SETGLOBAL is a no-op if an
        # ancestor's own env already has a scoped/local V - only
        # resolvable from this class's own (still-live) self.env, at
        # compile time, before enqueueing exec1. LOCAL/scoped (the
        # non-GLOBAL default) never needs this: sol_flo_red_GP always
        # resolves that case to VAR on its own.
        apply_v_scope(self.env, cc.arg4, "VAR")

        self.tc.enqueue(
            self.exec1,
            config=self.config,
            v=self.env.v,
            pgprim=self.env.pgprim,
            sow=self.env.sow_GP,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
        )

    def exec1(
        self: SolFloRed,
        config: SolFloRedConfig,
        v: str,
        pgprim: str,
        sow: tuple[Set | Alias, ...] | tuple[()],
        rtp_ffcs_defined: bool,
    ) -> None:
        sol_flo_red_GP(
            g=self.tc,
            config=config,
            arg4=config.arg4,
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )


def sol_flo_red(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: Literal["", "LOCAL", "GLOBAL"] = "",
    arg5: str = "",
    arg6: str = "",
    v: str,
    pgprim: str,
    sow: str,
    rtp_ffcs_defined: bool,
) -> str:
    # sol_flo.red:11 `SET%4 V VAR`. Verified against real GAMS (a minimal
    # $SET/$BATINCLUDE repro, checked with $log): this unconditionally
    # resolves V to the literal VAR whenever arg4 is "" or "LOCAL" -
    # regardless of any caller state - so this function derives that case
    # entirely on its own (see sol_flo_red_GP's docstring for the GLOBAL
    # case, which this simpler function refuses outright since it has no
    # CompileEnvironment and none of its current callers need it).
    if arg4 != "GLOBAL":  # type: ignore[comparison-overlap]
        v = "VAR"

    shp1 = ""
    # shp2 = "" # not used
    shp3 = ""
    tst = "$PRC_VINT(R,P)"

    shg1 = f",P,'{pgprim}',C"
    shg = ",P,CG1,C"

    if rtp_ffcs_defined:
        shp1 = f"*(1+RTP_FFCS(R,V{shg1}{sow}))"
        shp3 = f"*(1+RTP_FFCS(R,V{shg}{sow}))"

    shp1 = f"*(1+RTP_FFCX(R,V,T{shg1}){tst}){shp1}"
    shp3 = f"*(1+RTP_FFCX(R,V,T{shg}){tst}){shp3}"

    non_substituted = (
        f"{arg1}(R,V,T,P,C,S{arg5}) $= {v}_FLO{arg3}(R,V,T,P,C,S{arg5});"
        if arg2 == ""
        else ""
    )

    activity_flows = (
        f"{arg1}{arg2}(RTP_VINTYR(R,V,T,P),C,S{arg5})$PRC_TS(R,P,S) $= "
        f"SUM(RPC_ACT(RP_PGACT(R,P),C),{v}_ACT{arg3}(R,V,T,P,S{arg5})*PRC_ACTFLO(R,V,P,C));"
        if arg3 == ".L"
        else f"{arg1}{arg2}(RTP_VINTYR(R,V,T,P),C,S{arg5})$PRC_TS(R,P,S) $= "
        f"SUM(RPC_ACT(RP_PGACT(R,P),C),{v}_ACT{arg3}(R,V,T,P,S{arg5})*(1/PRC_ACTFLO(R,V,P,C)));"
        if arg3 == ".M"
        else ""
    )

    no_act_1 = (
        f"{v}_ACT{arg3}(RTP_VINTYR(R,V,T,P),S{arg5}) $= "
        f"SUM(RPC_PG(RP_FLO(NO_ACT(R,P)),C),{v}_FLO{arg3}(R,V,T,P,C,S{arg5})*(1/PRC_ACTFLO(R,V,P,C)));"
        if arg3 == ".L"
        else f"{v}_ACT{arg3}(R,V,T,P,S{arg5}) $= "
        f"SUM(RPC_PG(RP_FLO(NO_ACT(R,P)),C),{v}_FLO{arg3}(R,V,T,P,C,S{arg5})*PRC_ACTFLO(R,V,P,C));"
        if arg3 == ".M"
        else ""
    )

    no_act_2 = (
        f"{v}_ACT{arg3}(RTP_VINTYR(R,V,T,P),S{arg5}) $= "
        f"SUM(RPC_IRE(RPC_PG(NO_ACT(R,P),C),IE)$RP_AIRE(R,P,IE),{v}_IRE{arg3}(R,V,T,P,C,S,IE{arg5})*(1/PRC_ACTFLO(R,V,P,C)));"
        if arg3 == ".L"
        else f"{v}_ACT{arg3}(R,V,T,P,S{arg5}) $= "
        f"SUM(RPC_IRE(RPC_PG(NO_ACT(R,P),C),IE)$RP_AIRE(R,P,IE),{v}_IRE{arg3}(R,V,T,P,C,S,IE{arg5})*PRC_ACTFLO(R,V,P,C));"
        if arg3 == ".M"
        else ""
    )

    substituted = (
        ""
        if arg3 == ".M"
        else rf"""
*-------------------------------------------------------------------------------
* FFUNC substituted flows
{arg1}{arg2}(RTP_VINTYR(R,V,T,P),C,S{arg5})$(RTPCS_VARF(R,T,P,C,S){arg6}$RPC_FFUNC(R,P,C)) =
  SUM((RPC_ACT(R,P,COM),RS_TREE(R,S,TS))${v}_ACT{arg3}(R,V,T,P,TS{arg5}),
    {v}_ACT{arg3}(R,V,T,P,TS{arg5}) * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "COM", "S", "TS")}) *
    ( ACT_FLO(R,V,P,C,S){shp1} ));

* Emission flows
{arg1}{arg2}(RTP_VINTYR(R,V,T,P),C,S{arg5})$(RTPCS_VARF(R,T,P,C,S){arg6}$RPC_EMIS(R,P,C)) =
   SUM((FS_EMIT(R,P,C,CG1,COM),RS_TREE(R,S,TS))${arg1}{arg2}(R,V,T,P,COM,TS{arg5}),
         {arg1}{arg2}(R,V,T,P,COM,TS{arg5}) * RS_FR(R,S,TS)*(1+{macro.rtcs_fr.rtcs_fr("R", "T", "COM", "S", "TS")}) *
         COEF_PTRAN(R,V,P,CG1,COM,C,TS){shp3});
"""
    )

    return rf"""
* Non-substituted flows
{non_substituted}

* Activity flows
{activity_flows}

* Set NO_ACT flows to activity; they were not substituted
{no_act_1}
{no_act_2}
{substituted}
"""


def sol_flo_red_GP(
    *,
    g: TimesModelClass,
    config: SolFloRedConfig,
    arg4: Literal["", "LOCAL", "GLOBAL"] = "",
    v: str,
    pgprim: str,
    sow: tuple[Set | Alias, ...] | tuple[()] = (),
    rtp_ffcs_defined: bool,
) -> None:
    """Native GAMSPy counterpart of sol_flo_red().

    arg4 is this call's OWN scope-of-V arg (sol_flo.red's %4). Verified
    against real GAMS (a minimal $SET/$BATINCLUDE repro, checked with
    $log): sol_flo.red:11's `SET%4 V VAR` unconditionally resolves V to the
    literal VAR whenever arg4 is "" or "LOCAL" - regardless of any caller
    state - so `v` is overridden to "VAR" here in that case, ignoring
    whatever the caller passed. But a $SETGLOBAL (arg4="GLOBAL") turned out
    to be a complete no-op whenever an ancestor file already has an active
    (local or scoped) V of its own: the ancestor's value wins outright, not
    just on return but even within sol_flo.red's own remaining body.
    Whether that's the case here depends on the CALLER's own
    CompileEnvironment (e.g. RptmainStc may have already scoped-set "v"
    before including SolFloRed), which this stateless function has no
    access to - so for arg4="GLOBAL", the passed-in `v` is used as-is: it
    must already be pre-resolved by SolFloRed.compile() (via apply_v_scope
    on its own self.env, before enqueuing exec1).
    """
    if arg4 != "GLOBAL":
        v = "VAR"

    cc = config
    arg1 = cc.arg1
    arg2 = cc.arg2
    arg3 = cc.arg3
    arg5 = cc.arg5
    arg6 = cc.arg6

    v_act = g.get_variable(name=f"{v}_ACT")
    v_flo = g.get_variable(name=f"{v}_FLO")
    v_ire = g.get_variable(name=f"{v}_IRE")

    if arg2.startswith("."):
        var = g.get_variable(name=arg1)
        target: Parameter | ImplicitParameter = var.m if arg2 == ".M" else var.l
    else:
        target = g.get_parameter(name=f"{arg1}{arg2}")

    rvtp = (g.r, g.v, g.t, g.p)
    rvpc = (g.r, g.v, g.p, g.c)
    rvtpcs = (*rvtp, g.c, g.s)

    # FFUNC/emission substituted flows share this multiplicative shift
    shp1 = 1 + g.rtp_ffcx[*rvtp, pgprim, g.c].where[g.PrcVint[g.r, g.p]]
    shp3 = 1 + g.rtp_ffcx[*rvtp, g.cg1, g.c].where[g.PrcVint[g.r, g.p]]
    if rtp_ffcs_defined:
        shp1 = shp1 * (1 + g.rtp_ffcs[g.r, g.v, g.p, pgprim, g.c, *sow])
        shp3 = shp3 * (1 + g.rtp_ffcs[g.r, g.v, g.p, g.cg1, g.c, *sow])

    # Non-substituted flows
    if arg2 == "":
        v_flo_attr = v_flo.m if arg3 == ".M" else v_flo.l
        target[*rvtpcs, *arg5] = sparse(v_flo_attr[*rvtpcs, *arg5])

    # Activity flows
    if arg3 == ".L":
        act_term = v_act.l[*rvtp, g.s, *arg5] * g.prc_actflo[*rvpc]
        target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[g.PrcTs[g.r, g.p, g.s]] = (
            sparse(Sum(g.RpcAct[g.RpPgact[g.r, g.p], g.c], act_term))
        )
    elif arg3 == ".M":
        act_term = v_act.m[*rvtp, g.s, *arg5] * (1 / g.prc_actflo[*rvpc])
        target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[g.PrcTs[g.r, g.p, g.s]] = (
            sparse(Sum(g.RpcAct[g.RpPgact[g.r, g.p], g.c], act_term))
        )

    # Set NO_ACT flows to activity; they were not substituted
    if arg3 == ".L":
        no_act_domain = (g.RtpVintyr[*rvtp], g.s, *arg5)
        flo_term = v_flo.l[*rvtpcs, *arg5] * (1 / g.prc_actflo[*rvpc])
        v_act.l[*no_act_domain] = sparse(
            Sum(g.RpcPg[g.RpFlo[g.NoAct[g.r, g.p]], g.c], flo_term)
        )

        ire_term = v_ire.l[*rvtpcs, g.ie, *arg5] * (1 / g.prc_actflo[*rvpc])
        v_act.l[*no_act_domain] = sparse(
            Sum(
                g.RpcIre[g.RpcPg[g.NoAct[g.r, g.p], g.c], g.ie].where[
                    g.RpAire[g.r, g.p, g.ie]
                ],
                ire_term,
            )
        )
    elif arg3 == ".M":
        no_act_domain = (*rvtp, g.s, *arg5)
        flo_term = v_flo.m[*rvtpcs, *arg5] * g.prc_actflo[*rvpc]
        v_act.m[*no_act_domain] = sparse(
            Sum(g.RpcPg[g.RpFlo[g.NoAct[g.r, g.p]], g.c], flo_term)
        )

        ire_term = v_ire.m[*rvtpcs, g.ie, *arg5] * g.prc_actflo[*rvpc]
        v_act.m[*no_act_domain] = sparse(
            Sum(
                g.RpcIre[g.RpcPg[g.NoAct[g.r, g.p], g.c], g.ie].where[
                    g.RpAire[g.r, g.p, g.ie]
                ],
                ire_term,
            )
        )

    # Marginals for substituted flows currently not supported
    if arg3 == ".M":
        return

    # FFUNC substituted flows
    # arg3 != ".M" here (handled above), so the bare ACT reference is .L
    target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s].where[arg6] & g.RpcFfunc[g.r, g.p, g.c]
    ] = Sum(
        Domain(g.RpcAct[g.r, g.p, g.Com], g.RsTree[g.r, g.s, g.ts]).where[
            v_act.l[*rvtp, g.ts, *arg5]
        ],
        v_act.l[*rvtp, g.ts, *arg5]
        * g.rs_fr[g.r, g.s, g.ts]
        * (1 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow))
        * (g.act_flo[*rvpc, g.s] * shp1),
    )

    # Emission flows
    target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s].where[arg6] & g.RpcEmis[g.r, g.p, g.c]
    ] = Sum(
        Domain(g.FsEmit[g.r, g.p, g.c, g.cg1, g.Com], g.RsTree[g.r, g.s, g.ts]).where[
            target[*rvtp, g.Com, g.ts, *arg5]
        ],
        target[*rvtp, g.Com, g.ts, *arg5]
        * g.rs_fr[g.r, g.s, g.ts]
        * (1 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow))
        * g.coef_ptran[g.r, g.v, g.p, g.cg1, g.Com, g.c, g.ts]
        * shp3,
    )
