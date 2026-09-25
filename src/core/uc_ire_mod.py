# uc_ire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_IRE the code associated with the IRE variable in the EQ_USERCON
# *     - %1 region summation index
# *     - %2 period summation index
# *     - %3 time-slice summation index
# *     - %4 'T' or 'T+1' index
# *     - %5 'LHS' or 'RHS'
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Domain, Number, Product, Sum
from gamspy.math import Max, Min, abs, power, same_as

from core.utils import BaseUcModConfig, SowGPType, extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class UcIreModConfig(BaseUcModConfig):
    arg8: ImplicitParameter | Expression | Literal[1] = 1  # LAGT(T), -LEAD(T)


def uc_ire_mod(
    g: TimesModelClass,
    var: str | tuple[str, Any],
    sow_GP: SowGPType,
    config: UcIreModConfig,
) -> Expression | Sum:
    cc = config

    var_id, domain = extract_var_domain(var=var)

    VAR_IRE = g.get_variable(f"{var_id}_IRE")
    VAR_ACT = g.get_variable(f"{var_id}_ACT")

    r, v, p, c, s, ts, sl = g.r, g.v, g.p, g.c, g.s, g.ts, g.sl
    ucn, t, ie, cur = g.ucn, g.t, g.ie, g.cur

    uc_ire = g.uc_ire[ucn, cc.arg5, r, cc.arg7, p, c, ts, ie]

    ire_term = wrap_in_sum(
        (
            VAR_IRE[r, v, cc.arg4, p, c, ts, ie, *sow_GP].where[~g.RpcAire[r, p, c]]
            + (VAR_ACT[r, v, cc.arg4, p, ts, *sow_GP] * g.prc_actflo[r, v, p, c]).where[
                g.RpcAire[r, p, c]
            ]
        )
        # *GG* use the derived multipier
        # * [AL] PROD operator is useful here, but must be activated due to a GAMS bug:
        * uc_ire
        * Product(g.Annual, 1)
        * Product(
            g.RsBelow[r, ts, s],
            g.rs_fr[r, s, ts]
            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg4, c, s, ts, sow=sow_GP)),
        ),
        domain,
    )

    if cc.arg6 == 1:
        ire_term = ire_term * Product(
            g.UcAttr[r, ucn, cc.arg5, "IRE", "GROWTH"],
            power(abs(uc_ire), cc.arg8 * g.uc_sign[cc.arg5] - 1),
        )
    if cc.arg6 == "S":
        ire_term = ire_term * (1 / g.g_yrfr[r, s])

    ire_term = ire_term * Product(
        g.UcAttr[r, ucn, cc.arg5, "IRE", g.UcPerds],
        g.fpd[cc.arg4]
        * Product(
            g.UcNewflo[g.UcPerds],
            Number(1).where[same_as(v, cc.arg4) + g.Rvpt[r, v, p, cc.arg4]]
            / g.fpd[cc.arg4],
        ),
    )

    # the UC_COST attributes, priced with the objective cost coefficients
    ire_term = ire_term * Product(
        g.Reg[r].where[Sum(g.UcAttr[r, ucn, cc.arg5, "IRE", g.UcCost], 1)],
        Sum(
            Domain(g.Rdcur[r, cur], g.TsAnn[ts, sl]),
            macro.obj_fcost_GP(r, cc.arg4, p, c, sl, cur).where[
                g.UcAttr[r, ucn, cc.arg5, "IRE", "COST"]
            ]
            + macro.obj_fdelv_GP(r, cc.arg4, p, c, sl, cur).where[
                g.UcAttr[r, ucn, cc.arg5, "IRE", "DELIV"]
            ]
            + Min(0, macro.obj_ftax_GP(r, cc.arg4, p, c, sl, cur)).where[
                g.UcAttr[r, ucn, cc.arg5, "IRE", "SUB"]
            ]
            + Max(0, macro.obj_ftax_GP(r, cc.arg4, p, c, sl, cur)).where[
                g.UcAttr[r, ucn, cc.arg5, "IRE", "TAX"]
            ],
        ),
    )

    # *[UR]: RPC_IRE control may be redundant, only necessary if UC_IRE given for
    # * non-exchange processes by mistake
    term: Expression | Sum
    term = Sum(
        Domain(
            g.RtpVintyr[r, v, cc.arg4, p],
            g.UcMapIre[ucn, r, p, c, ie],
            g.RtpcsVarf[r, cc.arg4, p, c, ts],
        ).where[g.rs_fr[r, s, ts]],
        ire_term,
    )

    term = wrap_in_sum(target=term, domain=cc.arg3)
    if cc.arg6 == 2:
        term = (
            1
            + (
                g.fpd[t]
                + (g.coef_pvt[r, t] - g.fpd[t]).where[
                    g.UcAttr[r, ucn, "LHS", "IRE", "PERDISC"]
                ]
                - 1
            ).where[g.UcDt[r, ucn]]
        ) * term

    args_to_sum = [arg for arg in [cc.arg2, cc.arg1] if arg is not None]
    for arg in args_to_sum:
        term = wrap_in_sum(target=term, domain=arg)

    return term
