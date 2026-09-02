# pp_micro_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_MICRO.MOD coefficient calculations for the Micro extension
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Card,
    Loop,
    Ord,
    Parameter,
    Product,
    SpecialValues,
    Sum,
    While,
    sparse,
)
from gamspy.math import Max, Round, abs, aggregate, project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpMicroMod(GamsClass):
    """Translation unit for pp_micro.mod"""

    # Instance attributes
    module_name: str = "pp_micro_mod"
    gams_source: str = "pp_micro.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.ddf_qref = Parameter(m, name="DDF_QREF", domain=[g.r, g.t, g.c])
        g.ddf_pref = Parameter(m, name="DDF_PREF", domain=[g.r, g.t, g.c])
        g.mi_agc = Parameter(
            m,
            name="MI_AGC",
            domain=[g.r, g.t, g.c, g.c, g.j, g.lA],
            description="integral demand prices",
        )
        g.mi_dope = Parameter(
            m,
            name="MI_DOPE",
            domain=[g.r, g.t, g.c],
            description="demand own price elasticity",
        )
        g.mi_esub = Parameter(
            m,
            name="MI_ESUB",
            domain=[g.r, g.t, g.c],
            description="elasticity of substitution",
        )
        g.mi_rho = Parameter(
            m,
            name="MI_RHO",
            domain=[g.r, g.t, g.c],
            description="measure of substitutability",
        )

        if self.arg1.upper() == "PRE":
            self.tc.enqueue(self.pre_exec)
        elif self.arg1.upper() == "NLP":
            if self.env.stages == "YES":
                raise Exception("Non-linear Micro not available with stochastics")
            g.mi_elasp = Parameter(
                m,
                name="MI_ELASP",
                domain=[g.r, g.t, g.c],
                description="consumer surplus elasticity",
            )
            g.mi_ccons = Parameter(
                m,
                name="MI_CCONS",
                domain=[g.r, g.t, g.c],
                description="constant of the demand function",
            )
            self.tc.enqueue(self.nlp_exec)
        else:
            raise Exception(f"No label {self.arg1.upper()} in PpMicroMod")

    def pre_exec(self: PpMicroMod) -> None:
        g = self.tc
        r, t, c, com, s, cur = g.r, g.t, g.c, g.Com, g.s, g.cur

        # Identify aggregation groups
        project(source=g.com_agg, target=g.MiDmas)
        aggregate(source=g.sol_bprice, target=g.obj_pvt)
        g.RdAgg[g.Rc[r, c]].where[g.Dem[r, c] + g.ComTmap[r, "DEM", c]] = True
        g.MiDmas[r, c, com].where[
            ~(g.RdAgg[r, c] & g.RdAgg[r, com] & g.ComTsl[r, c, "ANNUAL"])
        ] = False
        g.ddf_pref[r, t, c].where[g.Dem[r, c]] = Sum(
            (g.ComTs[r, c, s], g.Rdcur[r, cur]),
            g.sol_bprice[r, t, c, s, cur] * g.com_fr[r, t, c, s],
        )

        # Handle nested CES structures
        g.MiDmas[r, c, com].where[Sum(g.Rpc[g.RpFlo, c], 1.0)] = False

        def refresh_rd_agg() -> None:
            project(source=g.MiDmas, target=g.RdAgg, direction="left")
            g.RdAgg[g.Dem] = False
            with Loop(g.MiDmas[r, c, com].where[~(g.Dem[r, com])]):
                g.RdAgg[r, c] = False

        refresh_rd_agg()
        with While(Card(g.RdAgg)):  # type: ignore[arg-type]
            g.Dem[g.RdAgg] = True
            #   Get base prices and set price ratio
            g.ddf_pref[r, t, c].where[g.RdAgg[r, c]] = Sum(
                g.MiDmas[r, c, com], g.com_proj[r, t, com] * g.ddf_pref[r, t, com]
            ) / Sum(g.MiDmas[r, c, com], g.com_proj[r, t, com])
            g.com_agg[r, t, com, c].where[
                (g.com_agg[r, t, com, c] == 0) & g.MiDmas[r, c, com] & g.RdAgg[r, c]
            ] = (
                1
                + (
                    (g.ddf_pref[r, t, com] / g.ddf_pref[r, t, c] - 1).where[
                        g.ddf_pref[r, t, c]
                    ]
                )
            )
            #   Normalize COM_AGG
            g.ddf_qref[r, t, c].where[g.RdAgg[r, c]] = Sum(
                g.MiDmas[r, c, com], g.com_agg[r, t, com, c] * g.com_proj[r, t, com]
            )
            g.com_proj[r, t, c].where[g.RdAgg[r, c]] = Sum(
                g.MiDmas[r, c, com], g.com_proj[r, t, com]
            )
            g.com_agg[r, t, com, c].where[
                g.com_agg[r, t, com, c].where[g.RdAgg[r, c]]
            ] = g.com_agg[r, t, com, c] * g.com_proj[r, t, c] / g.ddf_qref[r, t, c]
            #   Check for next nested level
            refresh_rd_agg()

        g.MiDmas[r, c, com].where[~(g.Dem[r, c] & g.Dem[r, com])] = False
        project(source=g.MiDmas, target=g.RdAgg, direction="left")
        g.RpcsVar[r, g.p, c, s].where[g.RdAgg[r, c]] = False

        # Preprocess elasticities
        g.mi_esub[r, t, c].where[g.RdAgg[r, c]] = abs(
            g.com_elast[r, t, c, "ANNUAL", "N"]
        )
        g.com_elast[g.Rtc, s, g.Bdneq].where[~(g.com_elast[g.Rtc, s, g.Bdneq])] = (
            sparse(g.com_elast[g.Rtc, s, "FX"])
        )
        with Loop(g.MiDmas[r, com, c]):
            g.com_elast[r, t, c, s, g.bd].where[g.ComTs[r, c, s] + g.Annual[s]] = Max(
                abs(g.com_elast[r, t, c, s, g.bd]), g.mi_esub[r, t, com]
            )

        # Finalize values with COM_AGG
        g.ddf_qref[r, t, c] = sparse(g.com_proj[r, t, c])
        g.ddf_pref[r, t, c].where[g.RdAgg[r, c]] = (
            Sum(g.MiDmas[r, c, com], g.ddf_qref[r, t, com] * g.ddf_pref[r, t, com])
            / g.ddf_qref[r, t, c]
        )
        g.com_bprice[r, t, c, "ANNUAL", cur].where[
            g.obj_pvt[r, t, cur].where[g.RdAgg[r, c]]
        ] = g.ddf_pref[r, t, c]
        g.rd_shar[r, t, c, com].where[g.MiDmas[r, c, com]] = (
            g.ddf_qref[r, t, com] / g.ddf_qref[r, t, c]
        )

        project(source=g.rd_shar, target=g.Trackc)
        g.com_proj[r, t, c].where[g.Trackc[r, c]] = 0
        g.com_bndnet[g.RtcsVarc[r, t, c, s], "UP"].where[g.Trackc[r, c]] = (
            SpecialValues.EPS
        )
        g.RhsComprd[r, t, c, "ANNUAL"] = sparse(g.RdAgg[r, c])
        g.Trackc.setRecords(None)
        g.obj_pvt.setRecords(None)

    def nlp_exec(self: PpMicroMod) -> None:
        g = self.tc
        r, t, c, com, cur, bd, bdneq, j = (
            g.r,
            g.t,
            g.c,
            g.Com,
            g.cur,
            g.bd,
            g.Bdneq,
            g.j,
        )

        # Take NLP elasticities from the FX type COM_ELAST
        g.mi_dope[r, t, c].where[g.Dem[r, c]] = abs(
            g.com_elast[r, t, c, "ANNUAL", "FX"]
        )

        # Initialize NLP indicator for demands
        g.rd_nlp[g.Dem] = 1
        g.Fil[t] = Ord(t) > 1
        with Loop(g.Fil[t]):
            g.rd_nlp[r, c].where[
                (g.ddf_qref[r, t, c] * g.ddf_pref[r, t, c] * g.mi_dope[r, t, c]) == 0
            ] = 0
        g.Trackc[g.RdAgg[g.Rc]] = sparse(g.rd_nlp[g.Rc])
        g.RdAgg[g.Rc].where[g.rd_nlp[g.Rc]] = False

        # -----------------------------------------------------------------------------
        g.mi_esub[r, t, c].where[g.Trackc[r, c]] = Round(
            g.mi_esub[r, t, c] * (1 - 5e-6), 5
        ) * (1 + 5e-6)
        g.mi_rho[r, t, c].where[(g.mi_esub[r, t, c] > 0).where[g.Trackc[r, c]]] = (
            1 - 1 / g.mi_esub[r, t, c]
        )
        g.rd_nlp[g.Trackc[r, c]].where[Product(g.Fil[t], g.mi_rho[r, t, c])] = 3
        with Loop(g.MiDmas[r, c, com].where[g.rd_nlp[r, c] > 2]):
            g.rd_nlp[r, com] = -1
        g.Rcj[g.Rc, j, bd].where[g.rd_nlp[r, c]] = False
        g.Trackc.setRecords(None)
        # -----------------------------------------------------------------------------
        # Calculate demand function parameters
        g.rd_shar[r, t, c, com].where[
            g.Fil[t] & g.MiDmas[r, c, com] & g.rd_nlp[r, c]
        ] = (
            g.com_agg[r, t, com, c]
            * g.ddf_qref[r, t, com]
            / g.ddf_qref[r, t, c]
            * (g.ddf_pref[r, t, com] / g.com_agg[r, t, com, c] / g.ddf_pref[r, t, c])
            ** g.mi_esub[r, t, c]
        )
        g.mi_elasp[r, t, c].where[g.Fil[t] & (g.rd_nlp[r, c] > 1) & g.Dem[r, c]] = (
            1 - 1 / g.mi_dope[r, t, c]
        )
        g.mi_ccons[r, t, c].where[g.Fil[t] & (g.rd_nlp[r, c] > 1) & g.Dem[r, c]] = (
            g.ddf_pref[r, t, c]
            * (1 / g.mi_elasp[r, t, c])
            * g.ddf_qref[r, t, c] ** (1 / g.mi_dope[r, t, c])
        )

        # -----------------------------------------------------------------------------
        # Bounds section
        g.com_voc[r, t, c, bdneq[bd]].where[
            (~(g.com_voc[r, t, c, bd])) & g.rd_nlp[r, c]
        ] = 1
        g.VAR_DEM.l[r, t, c].where[g.rd_nlp[r, c]] = g.ddf_qref[r, t, c]
        g.VAR_DEM.up[r, t, c].where[g.rd_nlp[r, c]] = g.ddf_qref[r, t, c] * (
            1 + g.com_voc[r, t, c, "UP"]
        )
        g.VAR_DEM.lo[r, t, c].where[g.rd_nlp[r, c]] = g.ddf_qref[r, t, c] * Max(
            0.1, 1 - g.com_voc[r, t, c, "LO"]
        )
        g.VAR_DEM.fx[r, t, c].where[g.Miyr1[t] & g.rd_nlp[r, c]] = g.ddf_qref[r, t, c]
        g.VAR_OBJELS.lo[r, "FX", cur].where[g.Rdcur[r, cur]] = SpecialValues.NEGINF
