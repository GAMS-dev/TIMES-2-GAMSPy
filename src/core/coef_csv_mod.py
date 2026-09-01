# coef_csv_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_CSV.mod oversees building simulated vintaging coefficients
# *=============================================================================*
# * Questions/Comments:
# * Load after all COEF*.mod
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Else,
    Equation,
    If,
    Loop,
    Parameter,
    Set,
    Smax,
    Smin,
    SpecialValues,
    sparse,
)
from gamspy.math import Max, Min, aggregate, floor, project, same_as

from core.base_class import GamsClass
from core.eqcapvac_mod import EqcapvacMod, EqcapvacModConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefCsvMod(GamsClass):
    """Translation unit for coef_csv.mod."""

    # Instance attributes
    module_name: str = "coef_csv_mod"
    gams_source: str = "coef_csv.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.Vtv = Set(m, name="VTV", domain=[g.ll, g.ll, g.t])
        # * SET RPS_CAFLAC(R,P,S,L) //;
        if not self.tc.declared("NCAP_AFCS"):
            g.ncap_afcs = Parameter(
                m, name="NCAP_AFCS", domain=[g.r, g.ll, g.p, g.cg, g.s]
            )

        g.Afsv = Set(m, name="AFSV", domain=[g.r, g.t, g.p, g.s, g.bd])
        g.coef_csv = Parameter(
            m, name="COEF_CSV", domain=[g.r, g.allyear, g.ll, g.p, g.allyear]
        )
        for sense in ("L", "E", "G"):
            g.set_equation(
                name=f"EQ{sense}_CAPVAC",
                eq=Equation(
                    m,
                    name=f"EQ{sense}_CAPVAC",
                    domain=[g.r, g.allyear, g.t, g.p, g.s, g.allsow],
                    description=f"Capacity Utilization (={sense}=)",
                ),
            )

        self.tc.enqueue(self.average_vintage_year)
        self.tc.enqueue(self.simplified_vintaging_processes)
        self.tc.enqueue(self.initialize_capacity_transfer)
        self.tc.enqueue(self.calculate_capacity_transfer)

        # fmt: off
        batincludes: list[EqcapvacModConfig] = [
            EqcapvacModConfig(sense="E", bound_type="FX"),
            EqcapvacModConfig(sense="L", bound_type="UP"),
            EqcapvacModConfig(sense="G", bound_type="LO"),
        ]
        # fmt: on
        for config in batincludes:
            self.include(EqcapvacMod(self.tc, self.env, config))

    def average_vintage_year(self) -> None:
        g = self.tc
        g.my_array[g.t] = g.yearval[g.t] - g.lead[g.t]

    def simplified_vintaging_processes(self, trivint: int = 6) -> None:
        g = self.tc
        # * Set vintages for simplified vintaging processes:
        g.prc_ymin.setRecords(None)
        g.PrcSimv[g.Rp].where[g.RpUpl[g.Rp, "FX"]] = False
        with Loop(g.t[g.ll]):
            g.my_f[...] = g.yearval[g.t]
            g.z[...] = Min(g.b[g.t], g.yearval[g.t] - floor(g.lead[g.t] / 2.0))
            # * Look up the first valid vintages for period T
            g.prc_ymin[g.PrcSimv[g.r, g.p]].where[g.RtpVara[g.r, g.t, g.p]] = Smin(
                g.RtpCptyr[g.r, g.tt, g.t, g.p].where[
                    (g.my_array[g.tt] + g.ncap_tlife[g.r, g.tt, g.p] > g.z)
                ],
                g.my_array[g.tt],
            )
            with Loop(g.PrcSimv[g.r, g.p].where[g.RtpVara[g.r, g.t, g.p]]):
                g.my_fyear[...] = g.prc_ymin[g.r, g.p]
                with If(g.my_fyear != SpecialValues.POSINF):
                    g.f[...] = g.my_fyear - 0.5
                    g.z[...] = g.my_f - 0.5
                    g.first_val[...] = (trivint - 0.5) * (trivint + 0.5)
                    # * Find the vintage maximizing the distance to first and last
                    g.my_fil2[g.tt] = (g.yearval[g.tt] - g.f) * (
                        g.z - g.yearval[g.tt]
                    ).where[g.Rtp[g.r, g.tt, g.p]]
                    g.z[...] = Smax(g.tt, g.my_fil2[g.tt])
                    with If(g.z > g.first_val):
                        g.z[...] = Smin(
                            g.tt.where[(g.my_fil2[g.tt] == g.z)], g.yearval[g.tt]
                        )
                        g.coef_cap[g.r, g.ll + (g.z - g.my_f), g.t, g.p] = -1.0
                        g.coef_cap[g.r, g.ll + (g.my_fyear - g.my_f), g.t, g.p] = 1.0
                    with Else():
                        g.coef_cap[g.r, g.ll + (g.my_fyear - g.my_f), g.t, g.p] = -1.0

    def initialize_capacity_transfer(self) -> None:
        g = self.tc
        # * Set still missing vintage indicators for year T:
        g.coef_cap[g.r, g.t, g.t, g.p].where[
            (g.RtpVara[g.r, g.t, g.p].where[g.PrcSimv[g.r, g.p]])
        ] = 1.0
        # * Initialize capacity transfer of simulated vintages for each TT
        g.coef_csv[g.RtpCptyr[g.r, g.tt, g.t, g.p], g.tt].where[
            g.coef_cap[g.r, g.tt, g.t, g.p]
        ] = 1.0
        # *-----------------------------------------------------------------------------
        g.Yk1.setRecords(None)
        if g.PrcSimv.number_records:
            with Loop(g.Miyr1[g.ll]):
                g.z[...] = g.lead[g.ll]
                project(source=g.t, target=g.Fil)
                g.Fil[g.ll - g.z] = True
                # * Add PASTI vintages
                g.coef_csv[g.RtpCptyr[g.r, g.Pastmile, g.t, g.p], g.ll - g.z].where[
                    (g.PrcSimv[g.r, g.p] * g.ncap_pasti[g.r, g.Pastmile, g.p])
                ] = 1.0
            # * Average effective vintage year for each MODLYEAR:
            g.Yk1[g.Fil, g.v].where[((~(same_as(g.Fil, g.v))).where[g.Fil[g.v]])] = True
            g.Vtv[g.Yk1[g.Fil, g.v], g.t].where[
                (
                    (g.yearval[g.t] - g.yearval[g.Fil] - 0.5)
                    * (g.yearval[g.v] - g.yearval[g.t] + 0.5)
                    > 0.0
                )
            ] = True
            # * Calculate effective average vintage year
            g.pastsum[g.Rtp[g.r, g.t, g.p]].where[g.PrcSimv[g.r, g.p]] = Min(
                g.m[g.t],
                floor(
                    Max(
                        g.yearval[g.t] - (g.lead[g.t] - 1.0) / 2.0,
                        g.b[g.t]
                        + Max(
                            g.ncap_iled[g.Rtp],
                            (g.d[g.t] + g.ncap_iled[g.Rtp] - g.ncap_tlife[g.Rtp]) / 2.0,
                        ),
                    )
                    + 0.5
                ),
            )

    def calculate_capacity_transfer(self) -> None:
        g = self.tc
        # * Calculate capacity transfer for each simulated vintage:
        with Loop(g.Yk1[g.ll, g.Fil]):
            g.z[...] = g.yearval[g.ll]
            g.f[...] = g.yearval[g.Fil]
            g.coef_csv[g.RtpCptyr[g.r, g.tt, g.t, g.p], g.Fil].where[
                (
                    (
                        g.coef_cap[g.r, g.ll, g.t, g.p]
                        * g.coef_cap[g.r, g.Fil, g.t, g.p]
                        < 0.0
                    ).where[g.Vtv[g.ll, g.Fil, g.tt]]
                )
            ] = (g.pastsum[g.r, g.tt, g.p] - g.z) / (g.f - g.z)
        # * Embed COEF_CPT in the coefficients
        g.coef_csv[g.RtpCptyr[g.r, g.v, g.t, g.p], g.Fil].where[g.PrcSimv[g.r, g.p]] = (
            g.coef_csv[g.r, g.v, g.t, g.p, g.Fil] * g.coef_cpt[g.r, g.v, g.t, g.p]
        )
        # *-----------------------------------------------------------------------------
        # * Clear unused vintages and ReSet RTP_VINTYR
        g.Yk1.setRecords(None)
        g.Vtv.setRecords(None)
        g.pastsum.setRecords(None)
        aggregate(source=g.coef_csv, target=g.coef_cap)
        g.RtpVintyr[g.r, g.v, g.t, g.p].where[g.PrcSimv[g.r, g.p]] = False
        g.RtpVintyr[g.r, g.v, g.t, g.p].where[g.coef_cap[g.r, g.v, g.t, g.p]] = True
        g.coef_cap.setRecords(None)
        # *-----------------------------------------------------------------------------
        g.Afsv[g.Afs[g.r, g.t, g.p, g.s, g.bd]] = sparse(g.PrcSimv[g.r, g.p])
        g.Afs[g.Afsv] = False
