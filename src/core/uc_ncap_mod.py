# uc_ncap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_NCAP the code associated with the flow variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 'T' or 'T+1' index
# *     - arg4 'LHS' or 'RHS'
# *     - arg5 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*
# *UR Questions/Comments:
# *  -

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Product, Sum
from gamspy.math import abs, power

from core.utils import SET_OR_ALIAS, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._algebra.operation import Operation
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.times_model_class import TimesModelClass

    # Every term of uc_ncap.mod is one of these
    UcNcapTerm = Condition | Expression | ImplicitSet | Operation

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class UcNcapModConfig:
    var: tuple[str, ImplicitSet | None]
    sow: tuple[Literal["0", "1"] | Set | Alias, ...]
    varv: tuple[str, ImplicitSet | None]
    sws: tuple[Set | Alias, ...]
    arg1: Domain | ImplicitSet | None
    arg2: (
        None
        | SET_OR_ALIAS
        | Condition
        | tuple[Condition | ImplicitSet, ImplicitParameter]
    )
    arg3: SET_OR_ALIAS  # T or TT
    arg4: SET_OR_ALIAS | str  # SIDE or 'LHS'
    arg5: Literal["S", 1, 2, 0]
    arg6: SET_OR_ALIAS  # T, TT or LL
    arg7: ImplicitParameter | Expression | Literal[1] = (
        1  # LAGT(T), -LEAD(T) only when arg6 is 1
    )


def uc_ncap_mod(g: TimesModelClass, config: UcNcapModConfig) -> Expression | Sum:
    cc = config

    r, v, p, cur, ucn = g.r, g.v, g.p, g.cur, g.ucn

    uc_ncap = g.uc_ncap[ucn, cc.arg4, r, cc.arg6, p]
    ncap = macro.VAR_NCAP_GP(cc.var, r, cc.arg3, p, cc.sow)

    # * [AL] VAR_NCAP(R,arg3,P) can be active even if there is no RTP_CPTYR(R,V,T,P)
    # * (due to ILED)!
    # * [AL] Therefore, changed to check for RTP(R,arg3,P) without RTP_OFF(R,arg3,P)
    ncap_term: UcNcapTerm = uc_ncap * (
        ncap.where[~g.RtpOff[r, cc.arg3, p]]
        + (
            Sum(
                g.Rvpt[r, v, p, cc.arg3],
                macro.VAR_NCAP_GP(cc.varv, r, v, p, cc.sws),
            )
            + ncap
            * (
                g.coef_rpti[r, cc.arg3, p]
                - Product(g.Rvpt[r, cc.arg3, p, g.Milestonyr], 2)
            )
        ).where[g.UcAttr[r, ucn, cc.arg4, "NCAP", "PERIOD"]]
    )

    # * [AL] PROD operator is useful here, but needs to be 'tweaked' due to a bug in
    # * GAMS 21.3-21.4:
    if cc.arg5 == 1:
        ncap_term = ncap_term * Product(
            g.UcAttr[r, ucn, cc.arg4, "NCAP", "GROWTH"],
            power(abs(uc_ncap), cc.arg7 * g.uc_sign[cc.arg4] - 1),
        )

    # the investment costs of the UC_COST attributes
    costs: UcNcapTerm = (
        macro.obj_icost_GP(r, cc.arg3, p, cur).where[
            g.UcAttr[r, ucn, cc.arg4, "NCAP", "COST"]
        ]
        + macro.obj_itax_GP(r, cc.arg3, p, cur).where[
            g.UcAttr[r, ucn, cc.arg4, "NCAP", "TAX"]
        ]
        - macro.obj_isub_GP(r, cc.arg3, p, cur).where[
            g.UcAttr[r, ucn, cc.arg4, "NCAP", "SUB"]
        ]
    )
    # $IF NOT %3==%6: the annualised costs of a dynamic constraint
    if cc.arg3 is not cc.arg6:
        costs = (
            Sum(
                g.UcAttr[r, ucn, cc.arg4, "NCAP", g.UcAnnul],
                g.cst_annc[r, cc.arg3, p, cc.arg6, g.UcAnnul, cur],
            )
            + costs
        )

    ncap_term = (
        ncap_term
        * Product(g.UcAttr[r, ucn, cc.arg4, "NCAP", "BUILDUP"], 1 / g.lead[cc.arg3])
        * Product(
            g.lA["N"],
            Product(
                g.Reg[r].where[Sum(g.UcAttr[r, ucn, cc.arg4, "NCAP", g.UcCost], 1)],
                Sum(g.Rdcur[r, cur], costs),
            ),
        )
    )

    ncap_term = Sum(g.UcGmapP[r, ucn, "NCAP", p].where[g.Rtp[r, cc.arg3, p]], ncap_term)

    args_to_sum = [arg for arg in [cc.arg2, cc.arg1] if arg is not None]
    for arg in args_to_sum:
        ncap_term = wrap_in_sum(target=ncap_term, domain=arg)

    return ncap_term
