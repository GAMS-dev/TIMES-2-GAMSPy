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
from core.utils import SET_OR_ALIAS

if TYPE_CHECKING:
    from gamspy import Alias, Set

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
        self._set_v_scope(cc.arg4, "VAR")

        self.tc.enqueue(
            self.exec1,
            config=self.config,
            pgprim=self.env.pgprim,
            sow=self.env.sow_GP,
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
        self: SolFloRed,
        config: SolFloRedConfig,
        pgprim: str,
        sow: tuple[Set | Alias, ...] | tuple[()],
        rtp_ffcs_defined: bool,
    ) -> None:
        sol_flo_red_GP(
            g=self.tc,
            config=config,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )


def sol_flo_red(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    # arg4: str = "", # not used
    arg5: str = "",
    arg6: str = "",
    pgprim: str,
    sow: str,
    rtp_ffcs_defined: bool,
) -> str:
    shp1 = ""
    # shp2 = "" # not used
    shp3 = ""
    tst = "$PRC_VINT(R,P)"
    v = "VAR"

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
    {v}_ACT{arg3}(R,V,T,P,TS{arg5}) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS)) *
    ( ACT_FLO(R,V,P,C,S){shp1} ));

* Emission flows
{arg1}{arg2}(RTP_VINTYR(R,V,T,P),C,S{arg5})$(RTPCS_VARF(R,T,P,C,S){arg6}$RPC_EMIS(R,P,C)) =
   SUM((FS_EMIT(R,P,C,CG1,COM),RS_TREE(R,S,TS))${arg1}{arg2}(R,V,T,P,COM,TS{arg5}),
         {arg1}{arg2}(R,V,T,P,COM,TS{arg5}) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS)) *
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
    pgprim: str,
    sow: tuple[Set | Alias, ...] | tuple[()] = (),
    rtp_ffcs_defined: bool,
) -> None:
    """Native GAMSPy counterpart of sol_flo_red()."""

    cc = config
    arg1 = cc.arg1
    arg2 = cc.arg2
    arg3 = cc.arg3
    arg5 = cc.arg5
    arg6 = cc.arg6

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
        VAR_FLO_ATTR = g.VAR_FLO.m if arg3 == ".M" else g.VAR_FLO.l
        target[*rvtpcs, *arg5] = sparse(VAR_FLO_ATTR[*rvtpcs, *arg5])

    # Activity flows
    if arg3 == ".L":
        act_term = g.VAR_ACT.l[*rvtp, g.s, *arg5] * g.prc_actflo[*rvpc]
        target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[g.PrcTs[g.r, g.p, g.s]] = (
            sparse(Sum(g.RpcAct[g.RpPgact[g.r, g.p], g.c], act_term))
        )
    elif arg3 == ".M":
        act_term = g.VAR_ACT.m[*rvtp, g.s, *arg5] * (1 / g.prc_actflo[*rvpc])
        target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[g.PrcTs[g.r, g.p, g.s]] = (
            sparse(Sum(g.RpcAct[g.RpPgact[g.r, g.p], g.c], act_term))
        )

    # Set NO_ACT flows to activity; they were not substituted
    if arg3 == ".L":
        no_act_domain = (g.RtpVintyr[*rvtp], g.s, *arg5)
        flo_term = g.VAR_FLO.l[*rvtpcs, *arg5] * (1 / g.prc_actflo[*rvpc])
        g.VAR_ACT.l[*no_act_domain] = sparse(
            Sum(g.RpcPg[g.RpFlo[g.NoAct[g.r, g.p]], g.c], flo_term)
        )

        ire_term = g.VAR_IRE.l[*rvtpcs, g.ie, *arg5] * (1 / g.prc_actflo[*rvpc])
        g.VAR_ACT.l[*no_act_domain] = sparse(
            Sum(
                g.RpcIre[g.RpcPg[g.NoAct[g.r, g.p], g.c], g.ie].where[
                    g.RpAire[g.r, g.p, g.ie]
                ],
                ire_term,
            )
        )
    elif arg3 == ".M":
        no_act_domain = (*rvtp, g.s, *arg5)
        flo_term = g.VAR_FLO.m[*rvtpcs, *arg5] * g.prc_actflo[*rvpc]
        g.VAR_ACT.m[*no_act_domain] = sparse(
            Sum(g.RpcPg[g.RpFlo[g.NoAct[g.r, g.p]], g.c], flo_term)
        )

        ire_term = g.VAR_IRE.m[*rvtpcs, g.ie, *arg5] * g.prc_actflo[*rvpc]
        g.VAR_ACT.m[*no_act_domain] = sparse(
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
    # arg3 != ".M" here (handled above), so the bare VAR_ACT reference is .L
    target[g.RtpVintyr[*rvtp], g.c, g.s, *arg5].where[
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s].where[arg6] & g.RpcFfunc[g.r, g.p, g.c]
    ] = Sum(
        Domain(g.RpcAct[g.r, g.p, g.Com], g.RsTree[g.r, g.s, g.ts]).where[
            g.VAR_ACT.l[*rvtp, g.ts, *arg5]
        ],
        g.VAR_ACT.l[*rvtp, g.ts, *arg5]
        * g.rs_fr[g.r, g.s, g.ts]
        * (1 + g.rtcs_fr[g.r, g.t, g.Com, g.s, g.ts])
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
        * (1 + g.rtcs_fr[g.r, g.t, g.Com, g.s, g.ts])
        * g.coef_ptran[g.r, g.v, g.p, g.cg1, g.Com, g.c, g.ts]
        * shp3,
    )
