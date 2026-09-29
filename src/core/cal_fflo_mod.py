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

from core.cal_red_red import CalRedRedConfig, cal_red_red_GP
from utils.macros import macro_config as macro

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
    # default Number(1)
    arg3: Condition | Expression | ImplicitParameter | MathOp | Number
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
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, cc.sow))
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
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, com2, s, ts, cc.sow)),
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
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, cc.sow))
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
        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, cc.sow)),
    )
