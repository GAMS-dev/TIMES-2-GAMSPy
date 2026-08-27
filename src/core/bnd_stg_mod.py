# bnd_stg_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_STG.MOD set the actual bounds for non-vintage VAR_SIN/OUT
#    %1 - which variable
#    %2 - which bound
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, SpecialValues, sparse

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_stg_mod_GP(
    *,
    g: TimesModelClass,
    var: str,
    arg1: str,
    arg2: str,
    arg3: float,
    swd: tuple[Set | Alias] | tuple[()],
    pgprim: str,
    stages: str,
) -> None:
    """GAMSPy twin of :func:`bnd_stg_mod`."""
    r, v, t, p, c, s, bd = g.r, g.v, g.t, g.p, g.c, g.s, g.bd
    VAR_X = g.get_variable(f"{var}_{arg1}")
    STG_BND = g.get_parameter(f"STG{arg2}_BND")

    # reset any existing bounds
    VAR_X.lo[r, v, t, p, c, s, *swd].where[g.PrcMap[r, "STG", p]] = 0
    VAR_X.up[r, v, t, p, c, s, *swd].where[g.PrcMap[r, "STG", p]] = SpecialValues.POSINF
    VAR_X.lo[g.RtpVintyr[r, v, t, p], pgprim, s, *swd].where[
        (~g.RpsStg[r, p, s]).where[g.RpSts[r, p]]
    ] = arg3

    # set bounds at process activity level
    g.Trackp[g.Rp[r, p]].where[(~g.PrcVint[r, p]).where[g.PrcMap[r, "STG", p]]] = True
    STG_BND[r, t, p, c, s, bd].where[(~g.Top[r, p, c, arg2]).where[g.RpStg[r, p]]] = 0

    def bound_assign() -> None:
        vintyr = g.RtpVintyr[r, t, t, p]
        cond = g.RpcsVar[r, p, c, s].where[g.Trackp[r, p]]
        VAR_X.lo[vintyr, c, s, *swd].where[cond] = sparse(STG_BND[r, t, p, c, s, "LO"])
        VAR_X.up[vintyr, c, s, *swd].where[cond] = sparse(STG_BND[r, t, p, c, s, "UP"])
        VAR_X.fx[vintyr, c, s, *swd].where[cond] = sparse(STG_BND[r, t, p, c, s, "FX"])

    if stages == "YES":
        with Loop(g.SwT[t, *swd]):
            bound_assign()
    else:
        bound_assign()

    g.Trackp.setRecords(None)
