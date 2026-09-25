# cal_stgn_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_STG the code associated with the storage flows in the EQ_COMxxx
# *   arg1 - 'IN/OUT' for consumption/production
# *   arg2 - 'OUT/IN' for consumption/production
# *   arg3 - STG_EFF for output
# *   arg4 - STG_EFF for output
# *   arg5 - for day-night storage indicator
# *=============================================================================*
# * Questions/Comments:
# * arg6 - NCAP_PKCNT multiplier

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Sum

if TYPE_CHECKING:
    from gamspy import Alias, Set, Variable
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CalStgnModConfig:
    """Strongly typed data contract for cal_stgn_mod."""

    var: str
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()]
    arg1: Literal["IN", "OUT"]
    arg2: Literal["IN", "OUT"]
    # all default Number(1)
    arg3: Condition | Expression | ImplicitParameter | MathOp | Number
    arg4: Condition | Expression | ImplicitParameter | MathOp | Number
    arg5: Condition | Expression | ImplicitSet | Number
    arg6: Condition | Expression | ImplicitParameter | MathOp | Number


def cal_stgn_mod_GP(g: TimesModelClass, config: CalStgnModConfig) -> Sum:
    """GAMSPy counterpart of cal_stgn_mod().

    arg3/arg4 are the STG_EFF multipliers of the arg1/arg2 storage flows, arg5 the
    day-night storage condition and arg6 the NCAP_PKCNT multiplier.
    """
    cc = config

    r, v, t, p, c, s, ts = g.r, g.v, g.t, g.p, g.c, g.s, g.ts
    VAR_SARG1: Variable = g.get_variable(f"{cc.var}_S{cc.arg1}")
    VAR_SARG2: Variable = g.get_variable(f"{cc.var}_S{cc.arg2}")

    stored = (VAR_SARG1[r, v, t, p, c, ts, *cc.sow] * cc.arg3) - (
        VAR_SARG2[r, v, t, p, c, ts, *cc.sow].where[g.RpcStgn[r, p, c, cc.arg2]]
        * cc.arg4
    )

    # *V05c 980923 - check that commodity not just capacity related
    return Sum(
        Domain(g.Top[g.RpcStg[r, p, c], cc.arg1], g.RpcsVar[r, p, c, ts]).where[
            cc.arg5
        ],
        # NB: gamspy's Sum() type hint omits Condition, which GAMS accepts
        Sum(g.RtpVntbyr[r, t, p, v], stored * cc.arg6).where[  # type: ignore[arg-type]
            ~g.RpcStgn[r, p, c, cc.arg1]
        ]
        # * equation coarser than variable or finer than variable
        * g.rs_fr[r, s, ts],
    )
