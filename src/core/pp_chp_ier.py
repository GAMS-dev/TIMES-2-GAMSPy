# pp_chp_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------
# * Convert capacity related CHP data from electricity to input commodity
# *-----------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Sum, sparse
from gamspy.math import project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpChpIer(GamsClass):
    """Translation unit for pp_chp.ier."""

    # Instance attributes
    module_name: str = "pp_chp_ier"
    gams_source: str = "pp_chp.ier"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.electricity_commodity_pg)
        self.tc.enqueue(self.commodity_group)
        self.tc.enqueue(self.calculate_electricity_heat_ratio)
        self.tc.enqueue(self.convert_input_capacity)
        self.tc.enqueue(self.extrapolate_past_years)

    def electricity_commodity_pg(self: PpChpIer) -> None:
        g = self.tc
        # Assumption: electricity commodity is given by PG
        g.EctElc[g.RpPg[g.EctChp, g.c]] = True
        g.RpPg[g.EctElc[g.r, g.p, g.c]] = False

    def commodity_group(self: PpChpIer) -> None:
        g = self.tc
        r, p, c, cg, cg2, Com = g.r, g.p, g.c, g.cg, g.cg2, g.Com
        CgGrp, ComGmap, ComTmap, Top = g.CgGrp, g.ComGmap, g.ComTmap, g.Top
        EctElc, EctDht, EctCgout, EctCgin = g.EctElc, g.EctDht, g.EctCgout, g.EctCgin

        # Assumption only one commodity group exists on the ouput side with
        # electricity and heat as its members
        project(source=g.flo_func, target=CgGrp, direction="left")
        with (
            Loop(EctElc[r, p, Com]),
            Loop(
                Domain(CgGrp[r, p, cg, cg2], ComGmap[r, cg, Com]).where[
                    Sum(
                        Top[r, p, c, "OUT"].where[
                            ComGmap[r, cg, c] * ComTmap[r, "NRG", c]
                        ],
                        1,
                    )
                    == 2
                ]
            ),
        ):
            EctDht[r, p, c].where[
                ComGmap[r, cg, c] * ComTmap[r, "NRG", c] * ~EctElc[r, p, c]
            ] = True
            EctCgout[r, p, cg] = True
            EctCgin[r, p, cg2] = True

        # input CG is new PCG
        g.RpPg[EctCgin] = True
        CgGrp.setRecords(None)

    def calculate_electricity_heat_ratio(self: PpChpIer) -> None:
        g = self.tc
        r, t, p, cg1, Com = g.r, g.t, g.p, g.cg1, g.Com
        flo_shar = g.flo_shar

        # Calculation of Ratio of electricity to heat: REH
        g.ect_reh[r, t, p].where[g.EctChp[r, p]] = sparse(
            1
            / Sum(
                Domain(g.EctCgout[r, p, cg1], g.EctElc[r, p, Com]).where[
                    flo_shar[r, t, p, Com, cg1, "ANNUAL", "LO"]
                ],
                1 / flo_shar[r, t, p, Com, cg1, "ANNUAL", "LO"] - 1,
            )
        )

    def convert_input_capacity(self: PpChpIer) -> None:
        g = self.tc
        r, t, p, c, cg1, cg2, Com = g.r, g.t, g.p, g.c, g.cg1, g.cg2, g.Com
        flo_func, flo_shar, flo_sum = g.flo_func, g.flo_shar, g.flo_sum
        EctChp, EctCgin, EctCgout, EctElc, EctDht = (
            g.EctChp,
            g.EctCgin,
            g.EctCgout,
            g.EctElc,
            g.EctDht,
        )

        # Conversion factor from input capacity to electricity capacity in
        # backpressure point
        g.ect_inp2elc[r, t, p].where[EctChp[r, p]] = sparse(
            Sum(
                Domain(EctCgin[r, p, cg2], EctElc[r, p, c]),
                Sum(
                    EctCgout[r, p, cg1].where[flo_func[r, t, p, cg1, cg2, "ANNUAL"]],
                    flo_func[r, t, p, cg1, cg2, "ANNUAL"]
                    * (
                        1
                        + Sum(
                            EctDht[r, p, Com].where[
                                flo_shar[r, t, p, c, cg1, "ANNUAL", "LO"]
                            ],
                            flo_sum[r, t, p, cg1, Com, cg2, "ANNUAL"],
                        )
                        * (1 / flo_shar[r, t, p, c, cg1, "ANNUAL", "LO"] - 1)
                    ),
                ),
            )
        )
        g.ect_inp2elc[r, t, p].where[g.ect_inp2elc[r, t, p]] = sparse(
            1 / g.ect_inp2elc[r, t, p]
        )

        # Conversion factor from input capacity to electricity capacity in
        # condensing mode
        g.ect_inp2con[r, t, p].where[EctChp[r, p]] = sparse(
            Sum(
                Domain(EctCgout[r, p, cg1], EctCgin[r, p, cg2]).where[
                    flo_func[r, t, p, cg1, cg2, "ANNUAL"]
                ],
                1 / flo_func[r, t, p, cg1, cg2, "ANNUAL"],
            )
        )

        # Conversion factor from input capacity to heat capacity in backpressure point
        g.ect_inp2dht[r, t, p].where[EctChp[r, p] * g.ect_reh[r, t, p]] = sparse(
            g.ect_inp2elc[r, t, p] / g.ect_reh[r, t, p]
        )

    def extrapolate_past_years(self: PpChpIer) -> None:
        g = self.tc
        r, t, v, p, s, bd, cur = g.r, g.t, g.v, g.p, g.s, g.bd, g.cur
        EctChp, Miyr1 = g.EctChp, g.Miyr1
        ect_inp2elc, ect_inp2dht, ect_inp2con, ect_reh = (
            g.ect_inp2elc,
            g.ect_inp2dht,
            g.ect_inp2con,
            g.ect_reh,
        )
        ncap_pasti = g.ncap_pasti

        # Extrapolate backwards for pastyears
        ect_inp2elc[r, v, p].where[ncap_pasti[r, v, p]] = sparse(
            Sum(Miyr1[t], ect_inp2elc[r, t, p])
        )
        ect_inp2dht[r, v, p].where[ncap_pasti[r, v, p]] = sparse(
            Sum(Miyr1[t], ect_inp2dht[r, t, p])
        )
        ect_inp2con[r, v, p].where[ncap_pasti[r, v, p]] = sparse(
            Sum(Miyr1[t], ect_inp2con[r, t, p])
        )
        ect_reh[r, v, p].where[EctChp[r, p] * ncap_pasti[r, v, p]] = sparse(
            Sum(Miyr1[t], ect_reh[r, t, p])
        )

        with Loop(EctChp[r, p]):
            g.ncap_cost[r, t, p, cur] = sparse(
                g.ncap_cost[r, t, p, cur] * ect_inp2con[r, t, p]
            )
            g.ncap_fom[r, t, p, cur] = sparse(
                g.ncap_fom[r, t, p, cur] * ect_inp2con[r, t, p]
            )
            g.act_cost[r, t, p, cur] = sparse(
                g.act_cost[r, t, p, cur] * ect_inp2con[r, t, p]
            )
            g.act_bnd[r, t, p, s, bd] = sparse(
                g.act_bnd[r, t, p, s, bd] / ect_inp2elc[r, t, p]
            )
            g.cap_bnd[r, t, p, bd] = sparse(
                g.cap_bnd[r, t, p, bd] / ect_inp2elc[r, t, p]
            )
            g.ncap_bnd[r, t, p, bd] = sparse(
                g.ncap_bnd[r, t, p, bd] / ect_inp2elc[r, t, p]
            )
            ncap_pasti[r, v, p].where[ncap_pasti[r, v, p]] = sparse(
                ncap_pasti[r, v, p] / ect_inp2elc[r, v, p]
            )
            g.ncap_pkcnt[r, t, p, s] = sparse(ect_inp2elc[r, t, p])

        # Default values for condensing and backpressure mode efficiencies
        # [UR] 04/23/2003 removed default values because of numerical difficulties
        # in sensitivity analysis
        # ECT_AFCON(R,T,P,'UP')$(ECT_CHP(R,P)*(NOT SUM(BD,ECT_AFCON(R,T,P,BD)))) = 1;
        # ECT_AFBPT(R,T,P,'UP')$(ECT_CHP(R,P)*(NOT SUM(BD,ECT_AFBPT(R,T,P,BD)))) = 1;
