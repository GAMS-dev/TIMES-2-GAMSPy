# bnd_elas_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_ELAS.MOD establishes bounds on demand elasticity variables
#   %1 - LO/UP step limit
# =============================================================================*
# Questions/Comments:
# - RCJ includes testing for COM_STEP
# - May want elasticity without COM_PROJ - may use COM_BQTY
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, Ord, Product, SpecialValues, Sum
from gamspy.math import Max, Min, Round, abs, log

if TYPE_CHECKING:
    from core.utils import SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_elas_mod_GP(
    *,
    g: TimesModelClass,
    stages: str,
    var: str,
    mx: str,
    sow_GP: SowGPType,
) -> None:
    """GAMSPy twin of :func:`bnd_elas_mod`."""
    r, t, tt, c, com, s, j, jj, bd, bdneq = (
        g.r,
        g.t,
        g.tt,
        g.c,
        g.Com,
        g.s,
        g.j,
        g.jj,
        g.bd,
        g.Bdneq,
    )

    g.mi_dope.setRecords(None)
    with Loop(Domain(g.Annual[s], g.MiDmas[g.RdAgg[r, c], com])):
        g.rd_shar[r, t, com, c] = g.com_agg[r, t, com, c] * g.ddf_pref[r, t, c]
        g.com_agg[r, t, com, c].where[g.com_elast[r, t, c, s, "N"] > 0] = 0
        g.com_elast[r, g.Miyr1[t], com, g.ts, bd] = 0
        g.com_voc[g.Rtc[r, t, com], "LO"].where[g.mi_esub[r, t, c]] = Min(
            g.com_voc[r, t, com, "LO"],
            1 - 9e9 ** (-g.com_elast[r, t, com, s, "FX"]),
        )
        g.mi_dope[r, t, com].where[g.mi_esub[r, t, c]] = Max(
            abs(g.com_elast[r, t, com, s, "FX"]), g.mi_esub[r, t, c]
        ).where[Sum(bdneq.where[g.com_elast[r, t, c, s, bdneq]], 1)]

    def elast_bound() -> None:
        com_fr = g.get_parameter(f"COM_FR{mx}")
        VAR_ELAST = g.get_variable(f"{var}_ELAST")
        VAR_ELAST.up[g.RtcsVarc[r, t, c, s], j, bdneq[bd], *sow_GP].where[
            g.Rcj[r, c, j, bd]
        ] = (
            Number(SpecialValues.POSINF).where[g.mi_dope[r, t, c]]
            + Max(g.ddf_qref[r, t, c] * com_fr[r, t, c, s], g.com_bqty[r, c, s])
            * g.com_voc[r, t, c, bd]
            / g.com_step[r, c, bd]
        )

    if stages == "YES":
        with Loop(g.SwT[t, *sow_GP]):
            elast_bound()
    else:
        elast_bound()

    # Price levels for CES (marginal / average)
    g.mi_rho[r, t, c].where[g.mi_dope[r, t, c]] = Round(1 - 1 / g.mi_dope[r, t, c], 6)

    g.mi_agc[r, t[tt + 1], com, c, j, bdneq[bd]].where[
        g.Rcj[r, c, j, bd] * g.MiDmas[r, com, c] * g.mi_esub[r, t, com]
    ] = (
        1 - g.bdsig[bd] * (Ord(j) - 0.5) * g.com_voc[r, t, c, bd] / g.com_step[r, c, bd]
    ) ** (-1 / g.com_elast[r, t, c, "ANNUAL", "FX"])

    voc_step = g.com_voc[r, t, c, bd] / g.com_step[r, c, bd]
    term_pos = (
        (1 - (1 - g.bdsig[bd] * Ord(j) * voc_step) ** g.mi_rho[r, t, c])
        / g.mi_rho[r, t, c]
    ).where[g.mi_rho[r, t, c]]
    term_zero = log(1 - g.bdsig[bd] * Ord(j) * voc_step).where[g.mi_rho[r, t, c] == 0]
    g.mi_agc[r, t, com, c, j, bd].where[
        (g.com_voc[r, t, c, bd] > 0)
        * g.mi_agc[r, t, com, c, j, bd]
        * g.mi_dope[r, t, c]
    ] = g.bdsig[bd] / (Ord(j) * voc_step) * (term_pos - term_zero)

    # Fix redundancies
    with Loop(g.RdAgg[r, com]):
        g.Fil[t] = ~Product(
            bdneq,
            Sum(
                g.ComTs[r, c, s].where[g.MiDmas[r, com, c]],
                g.com_elast[r, t, c, s, bdneq],
            ),
        )
        g.com_elast[g.RtcsVarc[r, g.Fil, c, s], bd].where[g.MiDmas[r, com, c]] = 0
        g.RcsComprd[r, g.Fil, com, s, bd] = False

    g.com_elastx[r, t, c, bdneq].where[g.mi_dope[r, t, c]] = 1
    g.RtcShed[r, t, c, bd, jj].where[g.mi_dope[r, t, c]] = False
