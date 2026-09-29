# bnd_act_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_ACT.MOD set the actual bounds for non-vintage VAR_ACTs
# =============================================================================*
# GaG Questions/Comments:
#   - FX take precedence as is set last!!!
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number, SpecialValues, sparse

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitSet

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_act_mod_GP(
    *,
    g: TimesModelClass,
    var: str,
    stages: str,
    swd: tuple[Set | Alias] | tuple[()],
    swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
) -> None:
    VAR_ACT, RtpVintyr, r, v, t, p, s, PrcTs, PrcVint, RtpsOff, act_bnd = (
        g.get_variable(f"{var}_ACT"),
        g.RtpVintyr,
        g.r,
        g.v,
        g.t,
        g.p,
        g.s,
        g.PrcTs,
        g.PrcVint,
        g.RtpsOff,
        g.act_bnd,
    )
    # reset any existing bounds
    VAR_ACT.lo[r, v, t, p, s, *swd] = 0
    VAR_ACT.up[r, v, t, p, s, *swd] = SpecialValues.POSINF

    # $IF %STAGES%==YES $SETLOCAL SWT SW_T(T%SWD%)$
    swt = (g.SwT[t, *swd],) if stages == "YES" else swt
    # %SWT% is a `$`-prefix, so it guards the whole condition instead of
    # extending the domain. SWT must always be 0 or 1 elements here.
    swt_cond: Set | Alias | ImplicitSet | Number = (
        Number(1) if len(swt) == 0 else swt[0]
    )

    # assign from user data - only set bounds directly at the PRC_TS level
    not_vintaged = swt_cond * PrcTs[r, p, s] * ~PrcVint[r, p]

    VAR_ACT.lo[RtpVintyr[r, t, t, p], s, *swd].where[not_vintaged] = sparse(
        act_bnd[r, t, p, s, "LO"]
    )
    VAR_ACT.up[RtpVintyr[r, t, t, p], s, *swd].where[not_vintaged] = sparse(
        act_bnd[r, t, p, s, "UP"]
    )
    VAR_ACT.fx[RtpVintyr[*r_t, t, p], s, *swd].where[not_vintaged] = sparse(
        act_bnd[r, t, p, s, "FX"]
    )
    # for upper bounds of zero, activity variables of all vintages can be bounded to zero
    turned_off = swt_cond * PrcTs[r, p, s] * PrcVint[r, p].where[RtpsOff[r, t, p, s]]
    VAR_ACT.up[RtpVintyr[r, v, t, p], s, *swd].where[turned_off] = SpecialValues.EPS
