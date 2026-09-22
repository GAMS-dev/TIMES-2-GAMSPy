# uc_com_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_COMPD the code associated with the COMPRD variable in the EQ_USERCON
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

from gamspy import Domain, Product, Set, Sum
from gamspy.math import abs, diag, power

from core.utils import BaseUcModConfig, SowGPType, extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression, Parameter
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class UcComModConfig(BaseUcModConfig):
    arg8: Literal["PRD", "BAL"]
    arg9: Literal["PRD", "NET"]
    arg10: Literal["NT", "PD"]  # OBJ_COM...
    arg11: ImplicitParameter | Expression | Literal[1] = (
        1  # LAGT(T), -LEAD(T) only when arg6 is 1
    )


def inner_sum(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: SowGPType,
    config: UcComModConfig,
) -> Sum:
    cc = config

    rhs_com_set: Set = g.get_set(name=f"RHS_COM{cc.arg8}")
    obj_com_param: Parameter = g.get_parameter(name=f"OBJ_COM{cc.arg10}")
    var_id, domain = extract_var_domain(var)
    var_com = g.get_variable(name=f"{var_id}_COM{cc.arg9}")

    expr1: Expression | int
    if cc.arg6 == 2:
        expr1 = (
            1.0
            + (
                g.fpd[g.t]
                + (g.coef_pvt[g.r, g.t] - g.fpd[g.t]).where[
                    g.UcAttr[g.r, g.ucn, "LHS", g.ucgrptype, "PERDISC"]
                ]
                - 1.0
            ).where[g.UcDt[g.r, g.ucn]]
        )
    else:
        expr1 = 1

    expr2: Product | int
    if cc.arg6 == 1:
        expr2 = Product(
            g.UcAttr[g.r, g.ucn, cc.arg5, g.ucgrptype, "GROWTH"],
            power(
                abs(
                    g.uc_com[
                        g.ucn, cc.arg9, cc.arg5, g.r, cc.arg7, g.c, g.ts, g.ucgrptype
                    ]
                ),
                cc.arg11 * g.uc_sign[cc.arg5] - 1.0,
            ),
        )
    else:
        expr2 = 1

    expr3 = 1.0 / g.g_yrfr[g.r, g.s] if cc.arg6 == "S" else 1

    return Sum(
        g.UcGmapC[g.r, g.ucn, cc.arg9, g.c, g.ucgrptype],
        expr1
        * Sum(
            rhs_com_set[g.r, cc.arg4, g.c, g.ts].where[g.rs_fr[g.r, g.s, g.ts]],
            g.uc_com[g.ucn, cc.arg9, cc.arg5, g.r, cc.arg7, g.c, g.ts, g.ucgrptype]
            * wrap_in_sum(
                var_com[g.r, cc.arg4, g.c, g.ts, *sow_GP]
                * (
                    1.0
                    + (1.0 / g.com_ie[g.r, cc.arg4, g.c, g.ts] - 1.0).where[
                        (
                            (g.UcAttr[g.r, g.ucn, cc.arg5, g.ucgrptype, "EFF"])
                            ^ (diag(g.ucgrptype, f"COM{cc.arg9}"))
                        )
                    ]
                )
                # * [AL] PROD operator is useful here
                * Product(g.Annual, 1.0)
                * Product(
                    g.RsBelow[g.r, g.ts, g.s],
                    g.rs_fr[g.r, g.s, g.ts]
                    * (
                        1.0
                        + macro.rtcs_fr.rtcs_fr_GP(
                            g.r, cc.arg4, g.c, g.s, g.ts, sow=sow_GP
                        )
                    ),
                )
                * expr2
                * expr3
                * Product(
                    g.UcAttr[g.r, g.ucn, cc.arg5, g.ucgrptype, "PERIOD"],
                    g.fpd[cc.arg4],
                )
                * Product(
                    g.Reg[g.r].where[
                        Sum(g.UcAttr[g.r, g.ucn, cc.arg5, g.ucgrptype, g.UcCost], 1.0)
                    ],
                    Sum(
                        Domain(
                            g.UcAttr[g.r, g.ucn, cc.arg5, g.ucgrptype, g.UcCost],
                            g.Rdcur[g.r, g.cur],
                        ),
                        obj_com_param[g.r, cc.arg4, g.c, g.ts, g.UcCost, g.cur],
                    ),
                ),
                domain,
            ),
        ),
    )


def uc_com_mod(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: SowGPType,
    config: UcComModConfig,
) -> Expression | Sum:
    cc = config

    expression = inner_sum(g, var, sow_GP, config)

    args_to_sum = [arg for arg in [cc.arg3, cc.arg2, cc.arg1] if arg is not None]
    for arg in args_to_sum:
        expression = wrap_in_sum(target=expression, domain=arg)

    return expression
