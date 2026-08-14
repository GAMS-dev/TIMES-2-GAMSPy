# uc_pasti_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_PASTI code associated with first period capacity in GROWTH constraint
# *     - %1 region summation index
# *     - %2 period summation index (MIYR_1)
# *     - %3 T index
# *     - %4 'LHS' or 'RHS'
# *=============================================================================*
# *AL Questions/Comments:
# *  - Possible bound attributes are for now ignored for PASTI
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Product, Sum
from gamspy.math import abs, power

from core.utils import SET_OR_ALIAS, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Domain
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitSet

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class UcPastiModConfig:
    arg1: Domain | ImplicitSet | None
    arg2: SET_OR_ALIAS
    arg3: SET_OR_ALIAS
    arg4: Literal["RHS"]


def uc_pasti_mod(g: TimesModelClass, config: UcPastiModConfig) -> Condition:
    cc = config
    r, p, ucn, side, Pastyear = g.r, g.p, g.ucn, g.side, g.Pastyear

    uc_cap = g.uc_cap[ucn, cc.arg4, r, cc.arg3, p]

    # *[AL] Sum over RTP that have UC_CAP specified on current side
    term = Sum(
        g.Rtp[r, cc.arg3, p].where[g.UcGmapP[r, ucn, "CAP", p]],
        # * Sum of PASTI inherited to first period is used as a capacity value for
        # * T-1 of MIYR_1(T)
        # * UC_CAP coefficient is taken from MIYR_1, because UC_CAP is interpolated
        # * on T only
        Sum(
            g.RtpCptyr[r, Pastyear, cc.arg3, p],
            g.coef_cpt[r, Pastyear, cc.arg3, p] * g.ncap_pasti[r, Pastyear, p],
        )
        * uc_cap
        # * [AL] PROD operator is useful here, but needs to be 'initialized' due to a
        # * GAMS bug:
        * Product(
            side[cc.arg4],
            Product(
                g.UcAttr[r, ucn, side, "CAP", "GROWTH"],
                power(abs(uc_cap), g.m[cc.arg3] - g.b[cc.arg3]),
            ),
        ),
    )

    wrapped_term = wrap_in_sum(target=term, domain=cc.arg1)
    conditional_term = wrapped_term.where[Sum(cc.arg2[[cc.arg3]], 1)]
    return conditional_term
