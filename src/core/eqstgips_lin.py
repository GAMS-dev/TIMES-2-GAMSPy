# eqstgips_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGIPS Inter-Period Storage (IPS) and TIME-Slice Storage (TSS)            *
# *=============================================================================*
# *AL Questions/Comments:
# * v2.6.0: VART redefined locally for stochastic mode
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Set, Sum
from gamspy.math import power

from core.base_class import GamsClass
from core.utils import extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgipsLin(GamsClass):
    """Translation unit for eqstgips.lin."""

    # Instance attributes
    module_name: str = "eqstgips_lin"
    gams_source: str = "eqstgips.lin"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        g.RtpEqstk = Set(m, name="RTP_EQSTK", domain=[g.r, g.allyear, g.t, g.p, g.item])

        self.tc.enqueue(self.exec1)

        sow = self.env.sow_GP
        sws = self.env.sws_GP
        swt = self.env.swt_GP

        eq_stgips = g.get_equation(f"{self.env.eq}_STGIPS")

        var = self.env.var
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")

        var_id, domain = extract_var_domain(self.env.vartt_GP)
        VARTT_ACT = wrap_in_sum(
            target=g.get_variable(name=f"{var_id}_ACT"), domain=domain
        )
        VARTT_SIN = wrap_in_sum(
            target=g.get_variable(name=f"{var_id}_SIN"), domain=domain
        )
        VARTT_SOUT = wrap_in_sum(
            target=g.get_variable(name=f"{var_id}_SOUT"), domain=domain
        )

        eq_stgips[g.RtpEqstk[*self.env.r_v_t_GP, g.p, g.item], *swt].where[
            (Sum(g.PrcStgips[g.r, g.p, g.c], 1.0).where[g.PrcMap[g.r, "STK", g.p]])
        ] = (
            # * storage level at the milestone year T
            VAR_ACT[g.r, g.v, g.t, g.p, "ANNUAL", *sow].where[g.lim[g.item]]
            + Sum(
                Domain(g.io[g.item], g.Modlyear, g.Miyr1[g.ll]).where[
                    g.RtpVintyr[g.r, g.Modlyear, g.t, g.p]
                ],
                VAR_ACT[g.r, g.Modlyear, g.ll - g.lead[g.ll], g.p, "ANNUAL", *sow],
            )
            == Sum(
                g.Top[g.PrcStgips[g.r, g.p, g.c], g.io],
                Sum(
                    g.tt[g.t - 1],
                    # * storage level at the milestone year TT, corrected with storage losses
                    (
                        VARTT_ACT[g.r, g.v, g.tt, g.p, "ANNUAL", *sws]
                        * power(
                            1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"], g.lead[g.t]
                        ).where[g.ips[g.io]]
                        # * Add in- and output flows to/from storage related to period TT
                        + Sum(
                            g.Perdinv[g.t, g.YEoh],
                            g.tpulse[g.tt, g.YEoh]
                            * (
                                (1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"])
                                ** (g.m[g.t] - g.yearval[g.YEoh] + 0.5)
                            ),
                        )
                        / g.prc_actflo[g.r, g.v, g.p, g.c]
                        * (
                            VARTT_SIN[g.r, g.v, g.tt, g.p, g.c, "ANNUAL", *sws].where[
                                g.ips[g.io]
                            ]
                            - VARTT_SOUT[
                                g.r, g.v, g.tt, g.p, g.c, "ANNUAL", *sws
                            ].where[(~(g.ips[g.io]))]
                        )
                    ).where[
                        (g.RtpVintyr[g.r, g.v, g.tt, g.p].where[g.PrcVint[g.r, g.p]])
                    ]
                    + (
                        # * storage level at the milestone year TT, corrected with storage losses
                        VARTT_ACT[g.r, g.tt, g.tt, g.p, "ANNUAL", *sws]
                        * power(
                            1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"], g.lead[g.t]
                        ).where[g.ips[g.io]]
                        # * Add in- and output flows to/from storage related to period TT
                        + Sum(
                            g.Perdinv[g.t, g.YEoh],
                            g.tpulse[g.tt, g.YEoh]
                            * (
                                (1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"])
                                ** (g.m[g.t] - g.yearval[g.YEoh] + 0.5)
                            ),
                        )
                        / g.prc_actflo[g.r, g.tt, g.p, g.c]
                        * (
                            VARTT_SIN[g.r, g.tt, g.tt, g.p, g.c, "ANNUAL", *sws].where[
                                g.ips[g.io]
                            ]
                            - VARTT_SOUT[
                                g.r, g.tt, g.tt, g.p, g.c, "ANNUAL", *sws
                            ].where[(~(g.ips[g.io]))]
                        )
                    ).where[
                        (
                            g.RtpVintyr[g.r, g.tt, g.tt, g.p].where[
                                (~(g.PrcVint[g.r, g.p]))
                            ]
                        )
                    ],
                )
                # * in- and output flows to/from storage related to period T
                # * [AL] Summing over PERDINV years, as the activity is measured at M(T)
                # * [AL] Inflows and outflows occur, on average, at the mid-point of each year
                + Sum(
                    g.Perdinv[g.t, g.YEoh],
                    g.tpulse[g.t, g.YEoh]
                    * (
                        (1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"])
                        ** (g.m[g.t] - g.yearval[g.YEoh] + 0.5)
                    ),
                ).where[g.RtpVintyr[g.r, g.v, g.t, g.p]]
                * (
                    VAR_SIN[g.r, g.v, g.t, g.p, g.c, "ANNUAL", *sow].where[g.ips[g.io]]
                    - VAR_SOUT[g.r, g.v, g.t, g.p, g.c, "ANNUAL", *sow].where[
                        (~(g.ips[g.io]))
                    ]
                )
                / g.prc_actflo[g.r, g.v, g.p, g.c],
            ).where[g.lim[g.item]]
            # * [AL] In the first period VAR_ACT is not available, but exogenous charge can be used
            + Sum(
                g.Vnt[g.t, g.Miyr1[g.ll]],
                VAR_ACT[g.r, g.v, g.ll - g.lead[g.ll], g.p, "ANNUAL", *sow]
                * power(1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"], g.lead[g.t]),
            ).where[g.lim[g.item]]
            # * Exogenous charge at BOH
            + Sum(
                Domain(g.io[g.item], g.Miyr1[g.ll]),
                g.stg_chrg[g.r, g.ll - g.lead[g.ll], g.p, "ANNUAL"],
            )
            + (
                # * Minimum storage balance at end-of-period
                VAR_ACT[g.r, g.v, g.t, g.p, "ANNUAL", *sow]
                * power(1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"], g.e[g.t] - g.m[g.t])
                - Sum(
                    Domain(g.Miyr1[g.ll], g.YEoh[g.ll + (g.e[g.t] - g.yearval[g.ll])]),
                    VAR_ACT[g.r, g.v, g.YEoh, g.p, "ANNUAL", *sow],
                )
                # * in- and output flows to/from storage
                + Sum(
                    g.Top[g.PrcStgips[g.r, g.p, g.c], g.io],
                    Sum(
                        g.Periodyr[g.t, g.YEoh].where[(g.yearval[g.YEoh] > g.m[g.t])],
                        (
                            (1.0 - g.stg_loss[g.r, g.v, g.p, "ANNUAL"])
                            ** (g.e[g.t] - g.yearval[g.YEoh] + 0.5)
                        ),
                    )
                    * (
                        # * half year's correction if LAGT is even
                        1.0
                        + (
                            (g.lagt[g.t] - 1.0) / 2.0 / (g.e[g.t] - g.m[g.t]) - 1.0
                        ).where[(g.e[g.t] < g.miyr_vl)]
                    )
                    / g.prc_actflo[g.r, g.v, g.p, g.c]
                    * (
                        VAR_SIN[g.r, g.v, g.t, g.p, g.c, "ANNUAL", *sow].where[
                            g.ips[g.io]
                        ]
                        - VAR_SOUT[g.r, g.v, g.t, g.p, g.c, "ANNUAL", *sow].where[
                            (~(g.ips[g.io]))
                        ]
                    ),
                )
            ).where[g.j[g.item]]
        )

    def exec1(self: EqstgipsLin) -> None:
        g = self.tc
        # * Charge at beginning of horizon (BOH)
        g.RtpEqstk[g.r, g.Miyr1[g.t], g.t, g.p, "IN"].where[
            (g.Rtp[g.r, g.t, g.p].where[g.PrcMap[g.r, "STK", g.p]])
        ] = True
        # * Normal storage balance in each period (N)
        g.RtpEqstk[g.RtpVintyr[g.r, g.v, g.t, g.p], "N"].where[
            g.PrcMap[g.r, "STK", g.p]
        ] = True
        # * We must ensure that the storage level is non-negative at end of each period (1)
        g.RtpEqstk[g.RtpVintyr[g.r, g.v, g.t, g.p], "1"].where[
            ((g.e[g.t] > g.m[g.t]).where[g.PrcMap[g.r, "STK", g.p]])
        ] = True
