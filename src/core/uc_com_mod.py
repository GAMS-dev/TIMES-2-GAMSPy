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

from gamspy import Alias, Domain, Product, Set, Sum
from gamspy.math import abs, diag, power

from core.utils import BaseUcModConfig, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Expression, Parameter
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class UcComModConfig(BaseUcModConfig):
    arg8: tuple[Literal["PRD", "BAL"]]
    arg9: tuple[Literal["PRD", "NET"]]
    arg10: tuple[Literal["NT", "PD"]]  # OBJ_COM...
    arg11: tuple[ImplicitParameter | Expression | Literal[1]] = (
        1,
    )  # LAGT(T), -LEAD(T) only when arg6 is 1


def inner_sum(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
    config: UcComModConfig,
) -> Sum:
    cc = config
    match cc:
        case UcComModConfig(
            arg4=(arg4,),
            arg5=(arg5,),
            arg6=(arg6,),
            arg7=(arg7,),
            arg8=(arg8,),
            arg9=(arg9,),
            arg10=(arg10,),
            arg11=(arg11,),
        ):
            pass
        case _:
            raise ValueError(
                "Config object did not match the expected single-element tuple structure."
            )

    rhs_com_set: Set = g.get_set(name=f"RHS_COM{arg8}")
    obj_com_param: Parameter = g.get_parameter(name=f"OBJ_COM{arg10}")
    if isinstance(var, tuple) and len(var) > 1:
        var_id, domain = var
    else:
        var_id = var
        domain = None

    VAR_COM = g.get_variable(name=f"{var_id}_COM{arg9}")
    VAR_COM_expr = Sum(domain, VAR_COM) if domain is not None else VAR_COM

    expr1: Expression | int
    if arg6 == 2:
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
    if arg6 == 1:
        expr2 = Product(
            g.UcAttr[g.r, g.ucn, arg5, g.ucgrptype, "GROWTH"],
            power(
                abs(g.uc_com[g.ucn, arg9, arg5, g.r, arg7, g.c, g.ts, g.ucgrptype]),
                arg11 * g.uc_sign[arg5] - 1.0,
            ),
        )
    else:
        expr2 = 1

    expr3 = 1.0 / g.g_yrfr[g.r, g.s] if arg6 == "S" else 1

    return Sum(
        g.UcGmapC[g.r, g.ucn, arg9, g.c, g.ucgrptype],
        expr1
        * Sum(
            rhs_com_set[g.r, arg4, g.c, g.ts].where[g.rs_fr[g.r, g.s, g.ts]],
            g.uc_com[g.ucn, arg9, arg5, g.r, arg7, g.c, g.ts, g.ucgrptype]
            * VAR_COM_expr[g.r, arg4, g.c, g.ts, *sow_GP]
            * (
                1.0
                + (1.0 / g.com_ie[g.r, arg4, g.c, g.ts] - 1.0).where[
                    (
                        (g.UcAttr[g.r, g.ucn, arg5, g.ucgrptype, "EFF"])
                        ^ (diag(g.ucgrptype, f"COM{arg9}"))
                    )
                ]
            )
            # * [AL] PROD operator is useful here
            * Product(g.Annual, 1.0)
            * Product(
                g.RsBelow[g.r, g.ts, g.s],
                g.rs_fr[g.r, g.s, g.ts] * (1.0 + g.rtcs_fr[g.r, arg4, g.c, g.s, g.ts]),
            )
            * expr2
            * expr3
            * Product(g.UcAttr[g.r, g.ucn, arg5, g.ucgrptype, "PERIOD"], g.fpd[arg4])
            * Product(
                g.Reg[g.r].where[
                    Sum(g.UcAttr[g.r, g.ucn, arg5, g.ucgrptype, g.UcCost], 1.0)
                ],
                Sum(
                    Domain(
                        g.UcAttr[g.r, g.ucn, arg5, g.ucgrptype, g.UcCost],
                        g.Rdcur[g.r, g.cur],
                    ),
                    obj_com_param[g.r, arg4, g.c, g.ts, g.UcCost, g.cur],
                ),
            ),
        ),
    )


def uc_com_mod(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
    config: UcComModConfig,
) -> str | Any:
    cc = config

    expression: Expression | Sum = inner_sum(g, var, sow_GP, config)

    args_to_sum = [arg for arg in [*cc.arg3, *cc.arg2, *cc.arg1] if arg is not None]
    for arg in args_to_sum:
        expression = wrap_in_sum(arg=arg, expression=expression)

    return expression.gamsRepr()  # type: ignore[no-untyped-call]
