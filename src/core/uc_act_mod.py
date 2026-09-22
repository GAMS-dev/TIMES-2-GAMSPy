# uc_act_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_ACT the code associated with the activity variable in the EQ_USERCON
# *     - %1 region summation index
# *     - %2 period summation index
# *     - %3 time-slice summation index
# *     - %4 'T' or 'T+1' index
# *     - %5 'LHS' or 'RHS'
# *     - %6 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Number, Product, Sum
from gamspy.math import abs, power, same_as

from core.utils import BaseUcModConfig, SowGPType, extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._symbols.implicits import ImplicitParameter

    from core.utils import SET_OR_ALIAS
    from utils.times_model_class import TimesModelClass

from utils.macros import macro_config as macro

logger = logging.getLogger(__name__)


@dataclass
class UcActModConfig(BaseUcModConfig):
    arg8: ImplicitParameter | Expression | Literal[1] = (
        1  # LAGT(T), -LEAD(T) only when arg6 is 1
    )


def inner_sum(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow: tuple[Literal["0", "1"] | SET_OR_ALIAS] | tuple[()],
    config: UcActModConfig,
) -> Sum:
    cc = config

    var_id, domain = extract_var_domain(var)
    var_act = g.get_variable(name=f"{var_id}_ACT")

    expr2: Product | int
    if cc.arg6 == 1:
        expr2 = Product(
            g.UcAttr[g.r, g.ucn, cc.arg5, "ACT", "GROWTH"],
            power(
                abs(g.uc_act[g.ucn, cc.arg5, g.r, cc.arg7, g.p, g.ts]),
                cc.arg8 * g.uc_sign[cc.arg5] - 1.0,
            ),
        )
    else:
        expr2 = 1

    expr3 = 1.0 / g.g_yrfr[g.r, g.s] if cc.arg6 == "S" else 1

    obj_acost = macro.obj_acost_GP(g.r, cc.arg4, g.p, g.cur)

    return Sum(
        g.RtpVintyr[g.r, g.v, cc.arg4, g.p].where[g.UcGmapP[g.r, g.ucn, "ACT", g.p]],
        (
            # *V0.9a S reference should be TS
            Sum(
                g.PrcTs[g.r, g.p, g.ts].where[
                    (g.rs_fr[g.r, g.s, g.ts] * g.RtpVara[g.r, cc.arg4, g.p])
                ],
                wrap_in_sum(var_act[g.r, g.v, cc.arg4, g.p, g.ts, *sow], domain)
                * g.uc_act[g.ucn, cc.arg5, g.r, cc.arg7, g.p, g.ts]
                * Product(
                    g.Annual, g.rs_fr[g.r, g.s, g.ts]
                )  # * [AL] PROD operator is useful here:
                * expr2
                * expr3
                * Product(
                    g.UcAttr[g.r, g.ucn, cc.arg5, "ACT", g.UcPerds],
                    g.fpd[cc.arg4]
                    * Product(
                        g.UcNewflo[g.UcPerds],
                        Number(1.0).where[
                            (same_as(g.v, cc.arg4) + g.Rvpt[g.r, g.v, g.p, cc.arg4])
                        ]
                        / g.fpd[cc.arg4],
                    ),
                ),
            )
        )
        * Product(
            g.UcAttr[g.r, g.ucn, cc.arg5, "ACT", "COST"],
            Sum(g.Rdcur[g.r, g.cur], obj_acost),
        ),
    )


def uc_act_mod(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: SowGPType,
    config: UcActModConfig,
) -> Expression | Sum:
    cc = config

    expression: Expression | Sum
    expression = inner_sum(g, var, sow_GP, cc)

    sub_expr1 = (
        (
            1.0
            + (
                g.fpd[g.t]
                + (g.coef_pvt[g.r, g.t] - g.fpd[g.t]).where[
                    g.UcAttr[g.r, g.ucn, "LHS", "ACT", "PERDISC"]
                ]
                - 1.0
            ).where[g.UcDt[g.r, g.ucn]]
        )
        if cc.arg6 == 2
        else 1
    )

    expression = sub_expr1 * wrap_in_sum(target=expression, domain=cc.arg3)

    args_to_sum = [arg for arg in [cc.arg2, cc.arg1] if arg is not None]

    for arg in args_to_sum:
        expression = wrap_in_sum(target=expression, domain=arg)

    return expression
