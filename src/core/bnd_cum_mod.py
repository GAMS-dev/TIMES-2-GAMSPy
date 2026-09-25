# bnd_cum_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_CUM.MOD set the actual bounds for cumulative variables
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, SpecialValues, Sum, sparse
from gamspy.math import Min, abs, diag, same_as

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_cum_mod_GP(
    *,
    g: TimesModelClass,
    arg1: SET_OR_ALIAS,
    stages: str,
    eotime: int | str,
    var: str,
    sow: SowGPType,
    cufscal: int,
    cucscal: int,
    macro: str,
) -> None:
    """GAMSPy twin of :func:`bnd_cum_mod`."""
    # $SETLOCAL SW1 '' SETLOCAL SW2 ""
    # $IF %STAGES%==YES $SETLOCAL SW1 'S_' SETLOCAL SW2 ",'1'%SOW%"
    sw1 = ""
    sw2: tuple[str | Set | Alias, ...] = ()
    if stages == "YES":
        sw1 = "S_"
        sw2 = ("1", *sow)

    (r, p, c, year, ll, bd, lA, j, jj, s, t, cur, allyear) = (
        g.r,
        g.p,
        g.c,
        g.year,
        g.ll,
        g.bd,
        g.lA,
        g.j,
        g.jj,
        g.s,
        g.t,
        g.cur,
        g.allyear,
    )
    (Bdneq, RpcCumflo, RcCumcom, MiyrL, Uncd7, Rtc, Annual) = (
        g.Bdneq,
        g.RpcCumflo,
        g.RcCumcom,
        g.MiyrL,
        g.Uncd7,
        g.Rtc,
        g.Annual,
    )
    flo_cum, com_cum, multi, yearval = g.flo_cum, g.com_cum, g.multi, g.yearval
    sw1_flo_cum = g.get_parameter(f"{sw1}FLO_CUM")
    sw1_com_cum = g.get_parameter(f"{sw1}COM_CUM")
    VAR_CUMFLO = g.get_variable(f"{var}_CUMFLO")
    VAR_CUMCOM = g.get_variable(f"{var}_CUMCOM")
    eoh_year = str(eotime)

    # Ignore negative bounds; reset any N bounds at specific years
    sw1_flo_cum[r, p, c, year, ll, bd, *sw2].where[
        (sw1_flo_cum[r, p, c, year, ll, bd, *sw2] < 0).where[
            sw1_flo_cum[r, p, c, year, ll, bd, *sw2]
        ]
    ] = 0
    flo_cum[r, p, c, year, "EOH", "N"] = sparse(flo_cum[r, p, c, year, eoh_year, "N"])
    flo_cum[RpcCumflo[r, p, c, year, ll], "N"] = 0

    sw1_flo_cum[r, p, c, year, ll, bd, *sw2].where[
        sw1_flo_cum[r, p, c, year, ll, "FX", *sw2]
    ] = sw1_flo_cum[r, p, c, year, ll, "FX", *sw2].where[Bdneq[bd]]

    # Get modifiers for flexible model horizon
    with Loop(Domain(j, MiyrL).where[same_as(j, "1")]):
        Uncd7.setRecords(None)
        Uncd7[
            RpcCumflo[r, p, c, year, eoh_year],
            j + (flo_cum[r, p, c, year, "EOH", "N"] - 1),
            "",
        ] = True
        with Loop(Uncd7[r, p, c, year, ll, jj, ""]):
            flo_cum[r, p, c, year, ll, "N"] = Min(0, abs(multi[jj, MiyrL]) - 1).where[
                multi[jj, MiyrL]
            ]

    # Set bounds
    VAR_CUMFLO.lo[r, p, c, year, ll, *sow].where[
        sw1_flo_cum[r, p, c, year, ll, "LO", *sw2]
    ] = (
        sw1_flo_cum[r, p, c, year, ll, "LO", *sw2]
        * (1 / cufscal)
        * (flo_cum[r, p, c, year, ll, "N"] + 1)
    )
    VAR_CUMFLO.up[r, p, c, year, ll, *sow].where[
        sw1_flo_cum[r, p, c, year, ll, "UP", *sw2]
    ] = (
        sw1_flo_cum[r, p, c, year, ll, "UP", *sw2]
        * (1 / cufscal)
        * (flo_cum[r, p, c, year, ll, "N"] + 1)
    )

    # Reset any N bounds at specific years
    com_cum[r, arg1, year, "0", c, "N"] = sparse(
        com_cum[r, arg1, year, eoh_year, c, "N"]
    )
    com_cum[RcCumcom[r, arg1, year, ll, c], "N"] = 0

    sw1_com_cum[r, arg1, year, ll, c, bd, *sw2].where[
        sw1_com_cum[r, arg1, year, ll, c, "FX", *sw2]
    ] = sw1_com_cum[r, arg1, year, ll, c, "FX", *sw2].where[Bdneq[bd]]
    sw1_com_cum[RcCumcom[r, arg1, ll, year, c], bd, *sw2].where[
        yearval[ll] > g.miyr_vl
    ] = SpecialValues.EPS
    RcCumcom[r, arg1, ll, year, c].where[yearval[ll] > g.miyr_vl] = False

    # Get modifiers for flexible model horizon
    with Loop(Domain(j, MiyrL).where[same_as(j, "1")]):
        Uncd7.setRecords(None)
        Uncd7[
            RcCumcom[r, arg1, year, eoh_year, c],
            j + (com_cum[r, arg1, year, "0", c, "N"] - 1),
            "",
        ] = True
        with Loop(Uncd7[r, arg1, year, ll, c, jj, ""]):
            com_cum[r, arg1, year, ll, c, "N"] = Min(
                0, abs(multi[jj, MiyrL]) - 1
            ).where[multi[jj, MiyrL]]

    # Set bounds
    sw1_com_cum[RcCumcom[r, arg1, year, ll, c], lA["LO"], *sw2].where[
        ~sw1_com_cum[RcCumcom, lA, *sw2]
    ] = Number(SpecialValues.NEGINF).where[
        Sum(
            Domain(Rtc[r, t, c], Annual[s]),
            Min(
                0,
                g.com_bndprd[Rtc, s, lA].where[diag(arg1, "PRD")]
                + g.com_bndnet[Rtc, s, lA].where[diag(arg1, "NET")]
                + 1
                - 1,
            ),
        )
    ]
    VAR_CUMCOM.lo[r, c, arg1, year, ll, *sow].where[
        sw1_com_cum[r, arg1, year, ll, c, "LO", *sw2]
    ] = (
        sw1_com_cum[r, arg1, year, ll, c, "LO", *sw2]
        * (1 / cucscal)
        * (com_cum[r, arg1, year, ll, c, "N"] + 1)
    )
    VAR_CUMCOM.up[r, c, arg1, year, ll, *sow].where[
        sw1_com_cum[r, arg1, year, ll, c, "UP", *sw2]
    ] = (
        sw1_com_cum[r, arg1, year, ll, c, "UP", *sw2]
        * (1 / cucscal)
        * (com_cum[r, arg1, year, ll, c, "N"] + 1)
    )

    # $IFI %MACRO%==YES $EXIT
    if macro.upper() == "YES":
        return

    (costcat, costagg, costype, CostGmap, reg_cumcst) = (
        g.costcat,
        g.costagg,
        g.costype,
        g.CostGmap,
        g.reg_cumcst,
    )
    VAR_CUMCST = g.get_variable(f"{var}_CUMCST")

    # Set lower bound for combined costs to -INF
    with Loop(CostGmap[costcat, costagg, costype]):
        VAR_CUMCST.lo[r, year, allyear, costcat, cur, *sow].where[
            reg_cumcst[r, year, allyear, costcat, cur, "UP"]
        ] = SpecialValues.NEGINF
    VAR_CUMCST.up[r, year, allyear, costcat, cur, *sow] = sparse(
        reg_cumcst[r, year, allyear, costcat, cur, "UP"]
    )
    VAR_CUMCST.lo[r, year, allyear, costcat, cur, *sow] = sparse(
        reg_cumcst[r, year, allyear, costcat, cur, "LO"]
    )
    VAR_CUMCST.fx[r, year, allyear, costcat, cur, *sow] = sparse(
        reg_cumcst[r, year, allyear, costcat, cur, "FX"]
    )
