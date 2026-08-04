# cal_fflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_FFLO the code associated with the flow variable in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# **  arg2 - 'I/O' for invest/decommission checks (no longer used)
# *   arg3 - * Peak multiplier
# *   arg4 - Peak by flow contribution
# *=============================================================================*
# *GaG Questions/Comments:
# *  - VAR_FLOs according to whether c-in-PCG otherwise RPS_S1
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Sum

from core.cal_red_red import CalRedRedConfig, cal_red_red, cal_red_red_GP

if TYPE_CHECKING:
    from gamspy import Alias, Set, Variable
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CalFfloModConfig:
    """Strongly typed data contract for cal_fflo_mod."""

    reduce: str
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()]
    var: str
    pgprim: str
    is_rtp_ffcs_defined: bool
    arg1: Literal["IN", "OUT"]
    arg3: (
        Condition | Expression | ImplicitParameter | MathOp | Number
    )  # default Number(1)
    arg4: Condition | Expression | ImplicitParameter | Number


def cal_fflo_mod_GP(
    g: TimesModelClass, config: CalFfloModConfig
) -> Expression | ImplicitSet:
    """GAMSPy counterpart of cal_fflo_mod().

    arg3 is the peak multiplier, arg4 the peak-by-flow contribution condition.
    """
    cc = config
    r, v, t, p, c, s, ts, Com = g.r, g.v, g.t, g.p, g.c, g.s, g.ts, g.Com
    cg3, com2 = g.cg3, g.com2

    if cc.reduce.upper() != "YES":
        shg = (p, cg3, c)
        shp1_inner: Expression | ImplicitSet | Number = Number(1)

        if cc.is_rtp_ffcs_defined:
            shp1_inner = 1 + g.rtp_ffcs[r, v, *shg, *cc.sow]

        shp1_val = 1 + g.rtp_ffcx[r, v, t, *shg].where[g.PrcVint[r, p]] * shp1_inner

        VAR_FLO: Variable = g.get_variable(f"{cc.var}_FLO")

        # *V05c 980923 - check that commodity not just capacity related
        return Sum(
            g.Top[g.RpFlo[r, p], c, cc.arg1].where[~g.RpcEmis[r, p, c]],
            Sum(
                Domain(g.RtpVntbyr[r, t, p, v], g.RtpcsVarf[r, t, p, c, ts]).where[
                    cc.arg4
                ],
                # * equation coarser than variable or equation finer than variable
                # * consider COM_TS shape too, so both TS_MAP and RS_BELOW embedded
                (
                    VAR_FLO[r, v, t, p, c, ts, *cc.sow]
                    * g.rs_fr[r, s, ts]
                    * (1 + g.rtcs_fr[r, t, c, s, ts])
                    * cc.arg3
                ),
            ),
            # * Handle RPC_EMIS flows separately; They cannot be NOFLO
        ) + Sum(
            g.Top[g.RpcEmis[g.RpFlo[r, p], c], cc.arg1].where[cc.arg4],
            Sum(
                Domain(
                    g.FsEmit[r, p, c, cg3, com2], g.RtpcsVarf[r, t, p, com2, ts]
                ).where[g.rs_fr[r, s, ts]],
                Sum(
                    g.RtpVntbyr[r, t, p, v],
                    (
                        VAR_FLO[r, v, t, p, com2, ts, *cc.sow]
                        * g.coef_ptran[r, v, p, cg3, com2, c, ts]
                        * shp1_val
                        * cc.arg3
                    ),
                )
                * g.rs_fr[r, s, ts]
                * (1 + g.rtcs_fr[r, t, com2, s, ts]),
            ),
        )

    def reduced_cal_red_red(
        arg10: Condition | Expression | ImplicitParameter | MathOp | Number,
        arg7: Literal["T", "V", ""],
        arg9: ImplicitSet | None = None,
    ) -> Condition | Expression | ImplicitSet | Sum:
        return cal_red_red_GP(
            g=g,
            config=CalRedRedConfig(
                var=cc.var,
                sow=cc.sow,
                pgprim=cc.pgprim,
                def_rtp_ffcs=cc.is_rtp_ffcs_defined,
                arg1=c,
                arg2=Com,
                arg3=ts,
                arg4=p,
                arg5=t,
                arg7=arg7,
                index_set=arg9,
                arg10=arg10,
            ),
        )

    # * [UR] model reduction %REDUCE% is set in *.run
    # * Sum over non-vintaged processes
    return Sum(
        g.Top[g.RpFlo[r, p], c, cc.arg1].where[~g.PrcVint[r, p]],
        Sum(
            g.RtpcsVarf[r, v[t], p, c, ts].where[cc.arg4],
            (
                reduced_cal_red_red(arg7="T", arg10=Number(1))
                # * equation coarser than variable or equation finer than variabl
                * g.rs_fr[r, s, ts]
                * (1 + g.rtcs_fr[r, t, c, s, ts])
                * cc.arg3
            ),
        ),
        # * Sum over vintaged processes
    ) + Sum(
        Domain(
            g.Top[g.PrcVint[g.RpFlo[r, p]], c, cc.arg1], g.RtpcsVarf[r, t, p, c, ts]
        ).where[cc.arg4],
        reduced_cal_red_red(arg7="V", arg9=g.RtpVntbyr[r, t, p, v], arg10=cc.arg3)
        # * equation coarser than variable or equation finer than variable
        * g.rs_fr[r, s, ts]
        * (1 + g.rtcs_fr[r, t, c, s, ts]),
    )


def cal_fflo_mod(
    reduce: str,
    sow: str,
    var: str,
    pgprim: str,
    is_rtp_ffcs_defined: bool,
    arg1: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    """Translation unit for cal_fflo.mod."""
    if reduce.upper() != "YES":
        shg = ",P,CG3,C"
        shp1_inner = ""

        if is_rtp_ffcs_defined:
            shp1_inner = f"*1+RTP_FFCS(R,V{shg}{sow}))"

        shp1_val = f"*(1+RTP_FFCX(R,V,T{shg})$PRC_VINT(R,P)){shp1_inner}"

        return rf"""
*V05c 980923 - check that commodity not just capacity related
         SUM(TOP(RP_FLO(R,P),C,'{arg1}')$(NOT RPC_EMIS(R,P,C)),
             SUM((RTP_VNTBYR(R,T,P,V),RTPCS_VARF(R,T,P,C,TS)),
* equation coarser than variable or equation finer than variable
* consider COM_TS shape too, so both TS_MAP and RS_BELOW embedded
               {var}_FLO(R,V,T,P,C,TS {sow}) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {arg3}){arg4}
         ) +
* Handle RPC_EMIS flows separately; They cannot be NOFLO
         SUM(TOP(RPC_EMIS(RP_FLO(R,P),C),'{arg1}'){arg4},
           SUM((FS_EMIT(R,P,C,CG3,COM2),RTPCS_VARF(R,T,P,COM2,TS))$RS_FR(R,S,TS),
             SUM(RTP_VNTBYR(R,T,P,V),{var}_FLO(R,V,T,P,COM2,TS {sow}) *
                COEF_PTRAN(R,V,P,CG3,COM2,C,TS) {shp1_val} {arg3}) *
             RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM2,S,TS)))) +
"""

    else:
        include_cal_red_1 = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            arg6="",
            arg7="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_rtp_ffcs_defined,
        )
        include_cal_red_2 = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            arg6="",
            arg7="V",
            arg8="SUM",
            arg9="RTP_VNTBYR(R,T,P,V),",
            arg10=f"{arg3}",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_rtp_ffcs_defined,
        )

        return rf"""
* [UR] model reduction %REDUCE% is set in *.run
* Sum over non-vintaged processes
         SUM(TOP(RP_FLO(R,P),C,'{arg1}')$(NOT PRC_VINT(R,P)),
             SUM(RTPCS_VARF(R,V(T),P,C,TS),
{include_cal_red_1}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)) {arg3}){arg4}
         ) +

* Sum over vintaged processes
         SUM((TOP(PRC_VINT(RP_FLO(R,P)),C,'{arg1}'),RTPCS_VARF(R,T,P,C,TS)){arg4},
{include_cal_red_2}
* equation coarser than variable or equation finer than variable
               * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))
         ) +
"""
