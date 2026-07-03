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
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolFloRed(GamsClass):
    """Translation unit for sol_flo.red."""

    module_name: str = "sol_flo_red"
    gams_source: str = "sol_flo.red"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.compile()

    def compile(self) -> None:
        self._set_v_scope(self.arg4, "VAR")

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            v=self.env.v,
            pgprim=self.env.pgprim,
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
        self: SolFloRed,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        v: str,
        pgprim: str,
        sow: str,
        rtp_ffcs_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=sol_flo_red(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                arg6=arg6,
                v=v,
                pgprim=pgprim,
                sow=sow,
                rtp_ffcs_defined=rtp_ffcs_defined,
            ),
        )


def sol_flo_red(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    v: str,
    pgprim: str,
    sow: str,
    rtp_ffcs_defined: bool,
) -> str:
    tst = "$PRC_VINT(R,P)"
    shg1 = f",P,'{pgprim}',C"
    shg = ",P,CG1,C"

    shp1 = ""
    shp3 = ""

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
