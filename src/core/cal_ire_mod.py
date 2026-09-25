# cal_ire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_IRE the code associated with the inter-region trade variable in EQ_COMxxx
# *   arg1 - IMPort/EXPort indicator
# *   arg2 - IN/OUT nature of the aux/emissions
# *   arg3 - IE or ''
# *   arg4 - * Peak multiplier
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Sum

from core.powerflo_vda import powerflo_vda_ireaux_GP
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
class CalIreModConfig:
    """Strongly typed data contract for cal_ire_mod."""

    var: str
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()]
    is_rtp_ffcs_defined: bool
    is_ireauxbal: bool
    arg1: Literal["IMP", "EXP"]
    arg2: Literal["IN", "OUT"]
    arg4: (
        Condition | Expression | ImplicitParameter | MathOp | Number
    )  # defaulte Number(1)
    arg3: Set | Alias | None = None
    arg5: str = ""
    arg6: Set | None = None
    # arg7 not needed anymore, since it closed arg6


def cal_ire_mod_GP(
    g: TimesModelClass, config: CalIreModConfig
) -> Expression | ImplicitSet:
    """GAMSPy counterpart of cal_ire_mod().

    Returns the inter-regional trade terms of the commodity balance equations.

    arg3 is the IE set (or None for the '<arg1>' literal), arg4 the peak multiplier
    factor, and arg6 the set wrapping R,P inside RPC_IRE (GAMS %6/%7), if any.
    """
    cc = config
    r, v, t, p, c, s, ts, Com = g.r, g.v, g.t, g.p, g.c, g.s, g.ts, g.Com
    VAR_IRE: Variable = g.get_variable(f"{cc.var}_IRE")
    VAR_ACT: Variable = g.get_variable(f"{cc.var}_ACT")

    mx_val = (
        (1 + g.rtp_ffcs[r, v, p, c, c, *cc.sow])
        if cc.is_rtp_ffcs_defined
        else Number(1)
    )

    # *V0.9 022100 - handle the fact that called 2x for aux
    ie_val: Set | Alias | str = cc.arg3 if cc.arg3 is not None else cc.arg1
    # RPC_IRE(%6R,P%7,...)
    rp: tuple[ImplicitSet | Alias, ...] = (
        (cc.arg6[r, p],) if cc.arg6 is not None else (r, p)
    )

    terms: Expression | ImplicitSet | int = 0
    if f"{cc.arg1}{cc.arg2}" not in ["EXPOUT", "IMPIN"]:
        # * actual exchange
        # *V05c 981016 - change RTPCS_VARFs to ts
        terms = terms + Sum(
            Domain(g.RpcIre[*rp, c, cc.arg1], g.RtpVntbyr[r, t, p, v]),
            Sum(
                g.RtpcsVarf[r, t, p, c, ts].where[g.rs_fr[r, s, ts]],
                (
                    VAR_IRE[r, v, t, p, c, ts, cc.arg1, *cc.sow].where[
                        ~g.RpcAire[r, p, c]
                    ]
                    + (
                        VAR_ACT[r, v, t, p, ts, *cc.sow] * g.prc_actflo[r, v, p, c]
                    ).where[g.RpcAire[r, p, c]]
                )
                * cc.arg4
                * g.rs_fr[r, s, ts]
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, cc.sow)),
            ),
        )

    if cc.is_ireauxbal:
        # take arg1 from powerflow.vda since if this is called its always IREAUX
        # from `$ SETGLOBAL IREAUXBAL $BATINCLUDE powerflo.vda IREAUX` in powerflow.vda
        terms = terms + powerflo_vda_ireaux_GP(
            g=g, arg1="IREAUX", arg2=cc.arg2, arg3=cc.arg5, var=cc.var, sow=cc.sow
        )

    # AUXONLY
    # *V0.5b handle auxiliary commodity flows too
    # *** NOTE: assumes that attribute at the same level as the variable!!
    # *V0.9 022100 - do IN/OUT explicitly
    flosum = g.ire_flosum[r, t, p, Com, ts, ie_val, c, cc.arg2]
    return terms + Sum(
        Domain(g.RpcIre[*rp, Com, ie_val], g.RtpcsVarf[r, t, p, Com, ts]).where[
            flosum & g.rs_fr[r, s, ts]
        ],
        flosum
        * Sum(
            g.RtpVntbyr[r, t, p, v],
            mx_val
            * (
                VAR_IRE[r, v, t, p, Com, ts, ie_val, *cc.sow].where[
                    ~g.RpcAire[r, p, Com]
                ]
                + (VAR_ACT[r, v, t, p, ts, *cc.sow] * g.prc_actflo[r, v, p, Com]).where[
                    g.RpcAire[r, p, Com]
                ]
            )
            * cc.arg4,
        )
        * g.rs_fr[r, s, ts]
        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, Com, s, ts, cc.sow)),
    )
