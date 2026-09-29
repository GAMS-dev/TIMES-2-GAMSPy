# bnd_macro_tm.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# ============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Ord, SpecialValues, Sum

if TYPE_CHECKING:
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_macro_tm_GP(g: TimesModelClass) -> None:
    # *  Set the Cut-off Point for Applying the Market Penetration Cost Penalty    *
    # *============================================================================*
    g.tm_captb[g.r, g.p] = Sum(g.Rtp[g.r, g.t, g.p], g.tm_expbnd[g.Rtp])
    # * set the bounds for the step variables for quad approx, * clearing them first
    g.VAR_XCAPP.up[g.Rtp, g.j] = SpecialValues.POSINF
    g.VAR_XCAPP.up[g.Rtp[g.r, g.t, g.p], g.Xcp[g.j]].where[
        ((Ord(g.j) < 7.0).where[g.tm_captb[g.r, g.p]])
    ] = g.tm_captb[g.r, g.p]
    # *============================================================================*
    # *  Set the Lower Bound and Fix the First Year                                *
    # *   - Demands                                                                *
    # *   - Investment                                                             *
    # *   - Capital                                                                *
    # *   - Marginal Costs of Demands                                              *
    # *============================================================================*
    # * user scalar (from CONSTANT table) to control lower bound on demands
    g.VAR_D.lo[g.Rtc[g.r, g.t, g.c]].where[g.Dem[g.r, g.c]] = (
        g.tm_dmtol[g.r] * g.tm_d0[g.r, g.c]
    )
    g.VAR_D.fx[g.Rtc[g.r, g.t, g.c]].where[(g.Dem[g.r, g.c] * (Ord(g.t) == 1.0))] = (
        g.tm_d0[g.r, g.c]
    )
    g.VAR_D.fx[g.Rtc[g.r, g.t, g.c]].where[
        ((g.com_proj[g.r, g.t, g.c] == 0.0).where[g.Dem[g.r, g.c]])
    ] = 0.0
    g.VAR_DEM.fx[g.Rtc[g.r, g.t, g.c]].where[
        ((g.tm_ddatpref[g.r, g.c] == 0.0).where[g.Dem[g.r, g.c]])
    ] = g.com_proj[g.r, g.t, g.c]
    g.VAR_INV.l[g.r, g.t] = g.tm_iv0[g.r] * g.tm_l[g.r, g.t]
    g.VAR_INV.fx[g.r, g.t[g.T1]] = g.tm_iv0[g.r]
    g.VAR_K.l[g.r, g.t] = g.tm_k0[g.r] * g.tm_l[g.r, g.t]
    # * user scalar (from CONSTANT table) to control investment tolerance
    g.VAR_K.lo[g.r, g.t] = g.tm_k0[g.r] * (
        g.tm_l[g.r, g.t] ** (g.tm_ivetol[g.r].where[(~(g.tm_sl))])
    )
    g.VAR_K.fx[g.r, g.t[g.T1]] = g.tm_k0[g.r]
    g.VAR_SP.fx[g.Rtc[g.r, g.t, g.c]].where[g.Dem[g.r, g.c]] = 0.0
    # *SK* V0.4 set MM_C for base year
    # * VAR_C.FX(R,T(MIYR_1)) = TM_C0(R);
    g.VAR_C.lo[g.r, g.tt] = g.tm_c0[g.r] * 0.5
