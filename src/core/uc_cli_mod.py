# uc_cli_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_CLI the UC code associated with climate variables
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
from typing import TYPE_CHECKING

from gamspy import Product, Sum
from gamspy.math import abs, power

from core.utils import BaseUcModConfig, SowGPType, extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Expression

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class UcCliModConfig(BaseUcModConfig):
    arg8: Expression  # -LEAD(T)


def inner_sum(
    g: TimesModelClass,
    var: str,
    sow_GP: SowGPType,
    config: UcCliModConfig,
) -> Sum:
    cc = config

    growth_term: Product | int
    if cc.arg6 == 1:
        growth_term = Product(
            g.UcAttr[g.r, g.ucn, cc.arg5, "CLI", "GROWTH"],
            power(
                abs(g.uc_cli[g.ucn, cc.arg5, g.r, cc.arg7, g.CmVar]),
                cc.arg8 * g.uc_sign[cc.arg5] - 1.0,
            ),
        )
    else:
        growth_term = 1

    var_id, domain = extract_var_domain(var)

    var_clitot = g.get_variable(name=f"{var_id}_CLITOT")
    var_clibox = g.get_variable(name=f"{var_id}_CLIBOX")

    return Sum(
        g.CmVar.where[g.uc_cli[g.ucn, cc.arg5, g.r, cc.arg7, g.CmVar]],
        g.uc_cli[g.ucn, cc.arg5, g.r, cc.arg7, g.CmVar]
        * (
            wrap_in_sum(var_clitot[g.CmVar, cc.arg4, *sow_GP], domain).where[
                g.CmKind[g.CmVar]
            ]
            + Sum(
                g.CmBoxmap[g.CmKind, g.CmVar, g.CmBox].where[
                    (~(g.CmAtmap[g.CmKind, g.CmVar].where[g.CmEmis[g.CmKind]]))
                ],
                wrap_in_sum(var_clibox[g.CmVar, g.CmBox, cc.arg4, *sow_GP], domain),
            )
            + Sum(
                g.CmBoxmap[g.CmEmis, g.CmHists, g.CmBox].where[
                    (
                        g.cm_phi[g.CmEmis, g.CmBox, g.CmEmis].where[
                            g.CmAtmap[g.CmEmis, g.CmVar]
                        ]
                    )
                ],
                wrap_in_sum(var_clibox[g.CmVar, g.CmBox, cc.arg4, *sow_GP], domain)
                / g.cm_ppm[g.CmEmis],
            ).where[(~(g.CmTkind[g.CmVar]))]
        )
        * Product(g.Annual, 1.0)
        * growth_term
        * Product(g.UcAttr[g.r, g.ucn, cc.arg5, "CLI", "PERIOD"], g.fpd[cc.arg4]),
    )


def uc_cli_mod(
    g: TimesModelClass,
    is_uc_cli_defined: bool,
    var: str,
    sow_GP: SowGPType,
    config: UcCliModConfig,
) -> Expression | Sum | int:
    if not is_uc_cli_defined:
        return 0
    cc = config

    expression: Expression | Sum
    expression = inner_sum(g, var, sow_GP, cc)
    args_to_sum = [arg for arg in [cc.arg3, cc.arg2, cc.arg1] if arg is not None]

    for arg in args_to_sum:
        expression = wrap_in_sum(target=expression, domain=arg)

    return expression
