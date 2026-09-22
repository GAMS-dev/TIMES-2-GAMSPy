# uc_cap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_CAP the code associated with the VAR_CAP variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 'T' or 'T+1' or 'T-1' index
# *     - arg4 'LHS' or 'RHS'
# *     - arg5 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*
# *UR Questions/Comments:
# *  -

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Product, SpecialValues, Sum
from gamspy.math import abs, power

from core.utils import SET_OR_ALIAS, extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.times_model_class import TimesModelClass


logger = logging.getLogger(__name__)


@dataclass
class UcCapModConfig:
    var: tuple[str, ImplicitSet | None]
    sow: tuple[Literal["0", "1"] | Set | Alias, ...]
    vda: Literal["YES", "%vda%"]
    abs: Literal["YES", "NO", "%abs%"]
    arg1: Domain | ImplicitSet | None
    arg2: (
        SET_OR_ALIAS
        | Condition
        | tuple[Condition | ImplicitSet, ImplicitParameter]
        | None
    )
    arg3: SET_OR_ALIAS  # T or TT
    arg4: SET_OR_ALIAS | str  # SIDE or 'LHS'
    arg5: Literal["S", 1, 2, 0]
    arg6: SET_OR_ALIAS  # T, TT or LL
    arg7: ImplicitParameter | Expression | Literal[1] = (
        1  # LAGT(T), -LEAD(T) only when arg6 is 1
    )


def uc_cap_mod(g: TimesModelClass, config: UcCapModConfig) -> Expression | Sum:
    cc = config
    r, v, p, c, s, ts = g.r, g.v, g.p, g.c, g.s, g.ts
    ucn, lA, t = g.ucn, g.lA, g.t

    var_id, domain = extract_var_domain(cc.var)

    uc_cap = g.uc_cap[ucn, cc.arg4, r, cc.arg6, p]
    # * VAR_CAP can always be directly used for UC_CAP
    cap_term = macro.VAR_CAP_GP(cc.var, r, cc.arg3, p, cc.sow) * uc_cap

    # * PROD operator needs to be 'tweaked' due to bug in older GAMS versions
    if cc.arg5 == 1:
        cap_term = cap_term * Product(
            g.UcAttr[r, ucn, cc.arg4, "CAP", "GROWTH"],
            power(abs(uc_cap), cc.arg7 * g.uc_sign[cc.arg4] - 1),
        )

    cap_term = (
        cap_term
        * Product(g.UcAttr[r, ucn, cc.arg4, "CAP", "CAPACT"], g.prc_capact[r, p])
        * Product(lA["N"], 1)
    )

    term: Expression | Sum = Sum(
        g.Rtp[r, cc.arg3, p].where[g.UcGmapP[r, ucn, "CAP", p]], cap_term
    )

    args_to_sum = [arg for arg in [cc.arg2, cc.arg1] if arg is not None]
    for arg in args_to_sum:
        term = wrap_in_sum(target=term, domain=arg)

    if f"{cc.vda}{cc.arg5}" != "YESS":
        return term

    # * Subtract offline capacity if requested
    sub_expr = Sum(
        g.Rtp[r, cc.arg3, p].where[g.RpUpl[r, p, "FX"] & g.UcGmapP[r, ucn, "CAP", p]],
        Number(SpecialValues.EPS)
        + uc_cap
        * Product(g.UcAttr[r, ucn, cc.arg4, "CAP", "CAPACT"], g.prc_capact[r, p])
        * Sum(g.RtpVintyr[r, v, cc.arg3, p], macro.upscaps.render_GP()),
    ).where[g.UcAttr[r, ucn, cc.arg4, "CAP", "ONLINE"]]
    term += wrap_in_sum(target=sub_expr, domain=cc.arg2)

    if cc.abs.upper() != "YES":
        return term

    var_bsprs = g.get_variable(f"{var_id}_BSPRS")

    # * Add reserve flows if requested
    sub_expr2 = Sum(
        g.BsUcmap[ucn, cc.arg4, r, p, c].where[g.BsComts[r, c, s]],
        g.uc_flo[ucn, cc.arg4, r, cc.arg6, p, c, "ANNUAL"]
        * g.prc_capact[r, p]
        * Sum(
            Domain(g.RtpVintyr[r, v, cc.arg3, p], g.BsPrs[r, p, ts]).where[
                g.rs_fr[r, s, ts]
            ],
            g.rs_fr[r, ts, s]
            * Sum(
                g.Lnx[lA],
                wrap_in_sum(var_bsprs[r, v, t, p, c, ts, lA, *cc.sow], domain).where[
                    g.ips[lA] + g.BsSupp[r, p].where[abs(g.bs_rtype[r, c]) > 2]
                ],
            ),
        ),
    )
    return term + wrap_in_sum(target=sub_expr2, domain=cc.arg2)
