# cal_red_red.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================================*
# * CAL_RED the code associated with the substitution of flow variables by activity variables
# *	arg1 - commodity of flow
# *	arg2 - commodity associated with the activity variable
# *	arg3 - timeslice index	of flow variable
# *	arg4 - process index of flow variable
# *	arg5 - period index of flow variable
# *	arg6 - for output routine '.L' suffix. otherwise nothing
# *	arg7 - optional T or V or '' (for non-vintaged / vintaged / general case)
# *	arg8 - optional 'SUM' (only if %7 is not T)
# *	arg9 - optional 'RTP_VINTYR(R,V,%5,%4),' (only if %7 is not T)
# *	arg10 - optional multiplier (NCAP_PKCNT)
# *=============================================================================================*

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Domain, Number, Sum

from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Variable
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import (
        ImplicitParameter,
        ImplicitSet,
        ImplicitVariable,
    )
    from gamspy.math import MathOp

    from core.utils import SET_OR_ALIAS
    from utils.times_model_class import TimesModelClass


@dataclass
class CalRedRedConfig:
    """Strongly typed data contract for cal_red_red."""

    var: str | tuple[str, Any]
    sow: tuple[Literal["0", "1"] | SET_OR_ALIAS, ...] | tuple[()]
    pgprim: str
    def_rtp_ffcs: bool
    arg1: SET_OR_ALIAS
    arg2: SET_OR_ALIAS
    arg3: SET_OR_ALIAS
    arg4: SET_OR_ALIAS
    arg5: SET_OR_ALIAS
    # multiplier or empty
    arg10: Condition | Expression | ImplicitParameter | MathOp | Number
    is_output: bool = False  # old arg6
    arg7: Literal["T", "V", ""] = ""
    # arg8 not needed anymore since it conatint the "SUM" corresponding to the domain in arg9
    index_set: ImplicitSet | None = None  # old arg9


def cal_red_red_GP(
    g: TimesModelClass, config: CalRedRedConfig
) -> Expression | ImplicitSet | Sum:
    """GAMSPy counterpart of cal_red_red().

    arg6 selects the '.L' suffix, arg9 the optional SUM domain (arg8 of the string
    version) and arg10 the optional multiplier.
    """
    cc = config

    r, v, allts, s2, cg1, com2 = g.r, g.v, g.allts, g.s2, g.cg1, g.com2

    # shp needs to be multiplied later!
    shp1: Number | Expression = Number(1)
    shp2: Number | Expression = Number(1)
    shp3: Number | Expression = Number(1)

    vnt: SET_OR_ALIAS = cc.arg5 if cc.arg7 == "T" else v

    # needs to be used in .where[] !!
    tst: Number | ImplicitSet = g.PrcVint[r, cc.arg4]

    shg1 = (cc.arg4, cc.pgprim, com2)
    shg2 = (cc.arg4, cc.pgprim, cc.arg1)
    shg = (cc.arg4, cg1, cc.arg1)

    if cc.def_rtp_ffcs:
        shp1 = 1 + g.rtp_ffcs[r, vnt, *shg1, *cc.sow]
        shp2 = 1 + g.rtp_ffcs[r, vnt, *shg2, *cc.sow]
        shp3 = 1 + g.rtp_ffcs[r, vnt, *shg, *cc.sow]

    if cc.arg7 == "V":
        tst = Number(1)

    if cc.arg7 != "T":
        shp1 = (1 + g.rtp_ffcx[r, v, cc.arg5, *shg1].where[tst]) * shp1
        shp2 = (1 + g.rtp_ffcx[r, v, cc.arg5, *shg2].where[tst]) * shp2
        shp3 = (1 + g.rtp_ffcx[r, v, cc.arg5, *shg].where[tst]) * shp3

    def total(
        expr: Expression | ImplicitParameter | ImplicitVariable,
    ) -> Expression | ImplicitParameter | ImplicitVariable | Sum:
        """arg8/arg9 of the string version: SUM(arg9, expr) or just expr."""
        return expr if cc.index_set is None else Sum(cc.index_set, expr)

    VAR_FLO: Variable = g.get_variable(f"{cc.var}_FLO")
    VAR_ACT: Variable = g.get_variable(f"{cc.var}_ACT")
    flo = VAR_FLO.l if cc.is_output else VAR_FLO
    act = VAR_ACT.l if cc.is_output else VAR_ACT

    # *  flow variable cannot be replaced
    flow_term = total(
        flo[r, vnt, cc.arg5, cc.arg4, cc.arg1, cc.arg3, *cc.sow] * cc.arg10
    ).where[~g.RpcEmis[r, cc.arg4, cc.arg1]]

    # *   emission flow = flow variable * emission factor
    traded = (
        flo[r, vnt, cc.arg5, cc.arg4, com2, allts, *cc.sow].where[
            # NB: in GAMS `not` binds looser than `+`, so NOT A+B means NOT (A+B)
            ~(g.RpcAct[r, cc.arg4, com2] + g.RpcFfunc[r, cc.arg4, com2])
        ]
        + (
            act[r, vnt, cc.arg5, cc.arg4, allts, *cc.sow]
            * g.prc_actflo[r, vnt, cc.arg4, com2]
        ).where[g.RpcAct[r, cc.arg4, com2]]
        + Sum(
            Domain(g.RpcAct[r, cc.arg4, cc.arg2], g.PrcTs2[r, cc.arg4, s2]).where[
                g.rs_fr[r, allts, s2]
            ],
            (
                act[r, vnt, cc.arg5, cc.arg4, s2, *cc.sow]
                * g.act_flo[r, vnt, cc.arg4, com2, allts]
                * shp1
            )
            * g.rs_fr[r, allts, s2]
            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg5, cc.arg2, allts, s2, cc.sow)),
        ).where[g.RpcFfunc[r, cc.arg4, com2]]
    )
    emis_term = Sum(
        Domain(g.FsEmit[r, cc.arg4, cc.arg1, cg1, com2], allts).where[
            g.RtpcsVarf[r, cc.arg5, cc.arg4, com2, allts] & g.rs_fr[r, cc.arg3, allts]
        ],
        total(
            (traded * g.coef_ptran[r, vnt, cc.arg4, cg1, com2, cc.arg1, allts] * shp3)
            * cc.arg10
        )
        * g.rs_fr[r, cc.arg3, allts]
        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg5, com2, cc.arg3, allts, cc.sow)),
    ).where[g.RpcEmis[r, cc.arg4, cc.arg1]]

    # *  flow variable equals activity variable
    act_term = total(
        act[r, vnt, cc.arg5, cc.arg4, cc.arg3, *cc.sow]
        * g.prc_actflo[r, vnt, cc.arg4, cc.arg1]
        * cc.arg10
    ).where[g.RpcAct[r, cc.arg4, cc.arg1]]

    ffunc_term = Sum(
        Domain(g.RpcAct[r, cc.arg4, cc.arg2], g.PrcTs2[r, cc.arg4, s2]).where[
            g.rs_fr[r, cc.arg3, s2]
        ],
        total(
            (act[r, vnt, cc.arg5, cc.arg4, s2, *cc.sow] * cc.arg10)
            * g.act_flo[r, vnt, cc.arg4, cc.arg1, cc.arg3]
            * shp2
        )
        * g.rs_fr[r, cc.arg3, s2]
        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg5, cc.arg2, cc.arg3, s2, cc.sow)),
    ).where[g.RpcFfunc[r, cc.arg4, cc.arg1]]

    return (
        (flow_term + emis_term).where[
            ~(g.RpcAct[r, cc.arg4, cc.arg1] + g.RpcFfunc[r, cc.arg4, cc.arg1])
        ]
        + act_term
        + ffunc_term
    )


def cal_red_red(
    var: str,
    sow: str,
    pgprim: str,
    def_rtp_ffcs: bool,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str = "",
    arg7: str = "",
    arg8: str = "",
    arg9: str = "",
    arg10: str = "",
) -> str:
    shp1 = ""
    shp2 = ""
    shp3 = ""
    vnt = arg5
    tst = f"$PRC_VINT(R,{arg4})"
    shg1 = f",{arg4},'{pgprim}',COM2"
    shg2 = f",{arg4},'{pgprim}',{arg1}"
    shg = f",{arg4},CG1,{arg1}"
    if arg7 != "T":
        vnt = "V"
    if def_rtp_ffcs:
        shp1 = f"*(1+RTP_FFCS(R,{vnt}{shg1}{sow}))"
        shp2 = f"*(1+RTP_FFCS(R,{vnt}{shg2}{sow}))"
        shp3 = f"*(1+RTP_FFCS(R,{vnt}{shg}{sow}))"
    if arg7 == "V":
        tst = ""
    if arg7 != "T":
        shp1 = f"*(1+RTP_FFCX(R,V,{arg5}{shg1}){tst}){shp1}"
        shp2 = f"*(1+RTP_FFCX(R,V,{arg5}{shg2}){tst}){shp2}"
        shp3 = f"*(1+RTP_FFCX(R,V,{arg5}{shg}){tst}){shp3}"

    return rf"""
(
*  flow variable cannot be replaced
   ({arg8}({arg9}{var}_FLO{arg6}(R,{vnt},{arg5},{arg4},{arg1},{arg3}{sow}){arg10})$(NOT RPC_EMIS(R,{arg4},{arg1}))
    +
*   emission flow = flow variable * emission factor
   SUM((FS_EMIT(R,{arg4},{arg1},CG1,COM2),ALL_TS)$(RTPCS_VARF(R,{arg5},{arg4},COM2,ALL_TS)$RS_FR(R,{arg3},ALL_TS)),
     {arg8}({arg9}
        (
*        flow variable cannot be replaced
         {var}_FLO{arg6}(R,{vnt},{arg5},{arg4},COM2,ALL_TS{sow})$(NOT RPC_ACT(R,{arg4},COM2)+RPC_FFUNC(R,{arg4},COM2))
         +
*        flow variable equals activity variable
         ({var}_ACT{arg6}(R,{vnt},{arg5},{arg4},ALL_TS{sow})*PRC_ACTFLO(R,{vnt},{arg4},COM2))$RPC_ACT(R,{arg4},COM2)
         +
         SUM((RPC_ACT(R,{arg4},{arg2}),PRC_TS2(R,{arg4},S2))$RS_FR(R,ALL_TS,S2),
             (
              {var}_ACT{arg6}(R,{vnt},{arg5},{arg4},S2{sow}) * ACT_FLO(R,{vnt},{arg4},COM2,ALL_TS){shp1}
             ) * RS_FR(R,ALL_TS,S2)*(1+{macro.rtcs_fr.rtcs_fr("R", arg5, arg2, "ALL_TS", "S2")})
            )$RPC_FFUNC(R,{arg4},COM2)
        ) * COEF_PTRAN(R,{vnt},{arg4},CG1,COM2,{arg1},ALL_TS){shp3} {arg10}
       ) * RS_FR(R,{arg3},ALL_TS)*(1+{macro.rtcs_fr.rtcs_fr("R", arg5, "COM2", arg3, "ALL_TS")})
      )$RPC_EMIS(R,{arg4},{arg1})
   )$(NOT RPC_ACT(R,{arg4},{arg1})+RPC_FFUNC(R,{arg4},{arg1}))
   +
*  flow variable equals activity variable
   {arg8}({arg9}{var}_ACT{arg6}(R,{vnt},{arg5},{arg4},{arg3}{sow})*PRC_ACTFLO(R,{vnt},{arg4},{arg1}){arg10})$RPC_ACT(R,{arg4},{arg1})
   +
   SUM((RPC_ACT(R,{arg4},{arg2}),PRC_TS2(R,{arg4},S2))$RS_FR(R,{arg3},S2),
       (
       {arg8}({arg9} {var}_ACT{arg6}(R,{vnt},{arg5},{arg4},S2{sow}) {arg10} * ACT_FLO(R,{vnt},{arg4},{arg1},{arg3}){shp2})
       ) * RS_FR(R,{arg3},S2)*(1+{macro.rtcs_fr.rtcs_fr("R", arg5, arg2, arg3, "S2")})
    )$RPC_FFUNC(R,{arg4},{arg1})
)
"""
