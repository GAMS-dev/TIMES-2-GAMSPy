# coef_shp_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_SHP prepares the shapes for COEF_PTR and COEF_CPT
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Card,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, aggregate, mod, power, project, sign

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefShpMod(GamsClass):
    """Translation unit for coef_shp.mod."""

    # Instance attributes
    module_name: str = "coef_shp_mod"
    gams_source: str = "coef_shp.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.rtp_ffcx = Parameter(
            m, name="RTP_FFCX", domain=[g.Reg, g.allyear, g.allyear, g.prc, g.cg, g.cg]
        )

        g.Agej = Set(m, name="AGEJ", domain=[g.j, g.age], records=[("1", "1")])

        self.tc.enqueue(self.shaping_of_coef_ptrans)
        self.tc.enqueue(self.shaping_of_coef_cpt)

    def shaping_of_coef_ptrans(self) -> None:
        g = self.tc

        r, v, p, t, tt, j, life, age = g.r, g.v, g.p, g.t, g.tt, g.j, g.life, g.age
        c, cg, cg1, cg2, io = g.c, g.cg, g.cg1, g.cg2, g.io

        g.z[...] = Smax(t, Max(g.ipd[t], g.d[t]))

        g.Opyear[life, age].where[
            ((Ord(age) <= Ord(life)).where[(Ord(life) <= g.z)])
        ] = True

        g.RtpCgc[g.Rtp[r, v, p], cg, cg2].where[
            ((g.flo_funcx[g.Rtp, cg, cg2] <= 0).where[g.flo_funcx[g.Rtp, cg, cg2]])
        ] = g.PrcVint[r, p]

        # Remove FLO_FUNCX indexes that won't have any effect
        g.z[...] = Card(j) / 2 + 1
        g.flo_funcx[g.Rtp, cg, cg2].where[
            (
                abs(g.flo_funcx[g.Rtp, cg, cg2] - g.z)
                > g.z - 1.5 - Number(SpecialValues.POSINF).where[g.Actcg[cg]]
            )
        ] = 0
        project(source=g.flo_funcx, target=g.RpGrp, direction="left")
        aggregate(source=g.RpGrp, target=g.prc_ymin)
        g.prc_ymax.setRecords(None)

        g.Trackp[g.Rp].where[g.prc_ymin[g.Rp]] = sparse(
            g.PrcVint[g.Rp] + g.RpGrp[g.Rp, "CAPFLO"]
        )

        g.RtpCapyr[g.RtpCptyr[r, v, t, p]] = sparse(g.Trackp[r, p])

        with Loop(g.Agej[j, age].where[Card(g.Trackp)]):  # type: ignore[index]
            with Loop(v):
                # Set the starting and ending years taking into account NCAP_ILED:
                g.prc_ymin[g.Trackp[r, p]] = g.b[v] + Round(g.ncap_iled[r, v, p])
                g.prc_ymax[g.Trackp[r, p]] = (
                    g.prc_ymin[r, p] + Round(g.ncap_tlife[r, v, p]) - 1
                )
                # Calculate average SHAPE for plants still operating in each period:
                g.rtp_ffcx[g.RtpCapyr[r, v, t, p], cg1, cg2].where[
                    g.flo_funcx[r, v, p, cg1, cg2]
                ] = (
                    Sum(
                        g.Periodyr[t, g.Eohyears].where[
                            g.yearval[g.Eohyears] <= Max(g.b[t], g.prc_ymax[r, p])
                        ],
                        g.shape[
                            g.j + (g.flo_funcx[r, v, p, cg1, cg2] - 1),
                            age
                            + (
                                Min(g.yearval[g.Eohyears], g.prc_ymax[r, p])
                                - g.prc_ymin[r, p]
                            ),
                        ],
                    )
                    / (
                        Max(
                            1,
                            Min(g.e[t], g.prc_ymax[r, p])
                            - Max(g.b[t], g.prc_ymin[r, p])
                            + 1,
                        )
                    )
                    - 1
                )

            g.rvprl[g.Rtp[r, t, p]].where[(g.coef_rpti[g.Rtp] > 1) & g.Trackp[r, p]] = (
                Round(g.ncap_tlife[g.Rtp] - 1) + SpecialValues.EPS
            )

            g.rtp_ffcx[g.RtpCapyr[r, tt, t, p], cg1, cg2].where[
                g.rvprl[r, tt, p].where[g.flo_funcx[r, tt, p, cg1, cg2]]
            ] = (
                Sum(
                    g.Opyear[age + g.rvprl[r, tt, p], life],
                    g.shape[j + (g.flo_funcx[r, tt, p, cg1, cg2] - 1), life],
                )
                / (g.rvprl[r, tt, p] + 1)
                - 1
            )

        # Shapes for capacity-related commodity flows
        g.coef_cio[g.RtpCapyr[r, v, t, p], c, io].where[g.ncap_com[r, v, p, c, io]] = (
            sparse(g.rtp_ffcx[r, v, t, p, "CAPFLO", c])
        )

        g.coef_cio[g.RtpCptyr[r, v, t, p], c, io].where[g.ncap_clag[r, v, p, c, io]] = (
            sign(g.ncap_clag[r, v, p, c, io])  # type: ignore[arg-type]
            * (
                Max(
                    0,
                    g.e[t]
                    + 1
                    - Max(
                        g.b[v]
                        + g.ncap_iled[r, v, p]
                        + abs(g.ncap_clag[r, v, p, c, io]),
                        g.b[t],
                    ),
                )
                / Max(0.1, g.e[t] + 1 - Max(g.b[v] + g.ncap_iled[r, v, p], g.b[t]))
                - 1.0
            )
            - Number(1).where[(g.ncap_clag[r, v, p, c, io] < 0)]
        )

        g.rtp_ffcx[g.RtpCapyr, "CAPFLO", cg] = 0

        # Option for non-vintaged FLO_FUNC multipliers
        g.rtp_ffcx[g.RtpVintyr[r, v, t, p], cg, cg2].where[
            (
                (g.flo_func[r, v, p, cg, cg2, "ANNUAL"] > 0).where[
                    g.RtpCgc[r, v, p, cg, cg2]
                ]
            )
        ] = (
            g.flo_func[r, t, p, cg, cg2, "ANNUAL"]
            / g.flo_func[r, v, p, cg, cg2, "ANNUAL"]
            - 1
        )

        g.Trackp.setRecords(None)
        g.rvprl.setRecords(None)
        g.RpGrp.setRecords(None)

    def shaping_of_coef_cpt(self) -> None:
        g = self.tc
        v, r, p, t, tt, j, c = g.v, g.r, g.p, g.t, g.tt, g.j, g.c
        cg, age, cur, life = g.cg, g.age, g.cur, g.life

        # Remove NCAP_CPX indexes that won't have any effect
        g.z[...] = Card(j) / 2 + 1
        g.ncap_cpx[g.Rtp].where[(abs(g.ncap_cpx[g.Rtp] - g.z) > g.z - 1.5)] = 0
        aggregate(source=g.ncap_cpx, target=g.prc_ymin)
        g.prc_ymax.setRecords(None)

        with Loop(g.Agej[j, age].where[Card(g.ncap_cpx)]):  # type: ignore[index]
            g.Trackp[g.Rp] = sparse(g.prc_ymin[g.Rp])
            with Loop(v):
                # Set the starting and ending years taking into account NCAP_ILED:
                g.prc_ymin[g.Trackp[r, p]] = g.b[v] + Round(g.ncap_iled[r, v, p])
                g.prc_ymax[g.Trackp[r, p]] = g.prc_ymin[r, p] + g.ncap_tlife[r, v, p]
                # Calculate weighted average SHAPE for plants still operating in each period:
                with Loop(g.GRcur[r, cur]):
                    g.coef_cap[g.RtpCptyr[r, v, t, p]].where[g.ncap_cpx[r, v, p]] = (
                        Sum(
                            g.Periodyr[t, g.YEoh].where[
                                g.yearval[g.YEoh] < g.prc_ymax[r, p]
                            ],
                            Min(1, g.prc_ymax[r, p] - g.yearval[g.YEoh])
                            * g.obj_disc[r, g.YEoh, cur]
                            * g.shape[
                                j + (g.ncap_cpx[r, v, p] - 1),
                                age + (g.yearval[g.YEoh] - g.prc_ymin[r, p]),
                            ],
                        )
                        / g.coef_pvt[r, t]
                    )

            # For repeated investments, use the average SHAPE over lifetime:
            g.rvprl[g.Rtp].where[(g.coef_rpti[g.Rtp] > 1) & g.ncap_cpx[g.Rtp]] = (
                Round(g.ncap_tlife[g.Rtp] - 1) + SpecialValues.EPS
            )
            g.coef_cap[g.RtpCptyr[r, v[tt], t, p]].where[g.rvprl[r, v, p]] = Sum(
                g.Opyear[age + g.rvprl[r, v, p], life],
                g.shape[j + (g.ncap_cpx[r, v, p] - 1), life],
            ) / (g.rvprl[r, v, p] + 1)
            g.coef_cap[g.RtpCptyr[r, v, t, p]].where[g.ncap_cpx[r, v, p]] = (
                1 / Max(1, g.coef_cpt[r, v, t, p] / g.coef_cap[r, v, t, p])
            ).where[g.coef_cap[r, v, t, p]] - 1

        g.coef_cpt[r, v, t, p].where[g.coef_cap[r, v, t, p]] = g.coef_cpt[
            r, v, t, p
        ] * (g.coef_cap[r, v, t, p] + 1)

        g.prc_ymin.setRecords(None)
        g.prc_ymax.setRecords(None)
        g.Trackp.setRecords(None)
        g.RtpCgc.setRecords(None)
        aggregate(source=g.coef_cap, target=g.rtp_cpx, direction="left")
        g.coef_cap.setRecords(None)

        # Override COEF_OCOM if conditions met for using capacity transfer
        g.RtpCgc[g.Rtp[r, v, p], cg["CAPFLO"], c].where[
            (g.flo_funcx[r, "0", p, cg, c] == 3) & g.ncap_ocom[g.Rtp, c]
        ] = True

        with Loop(g.Agej[j, age].where[Card(g.RtpCgc)]):  # type: ignore[index]
            aggregate(source=g.RtpCgc, target=g.rvprl)
            g.pastsum[g.Rtp[r, v, p]].where[g.rvprl[g.Rtp]] = (
                g.b[v]
                + Round(g.ncap_iled[g.Rtp])
                + Round(g.ncap_dlag[g.Rtp] + g.ncap_dlife[g.Rtp] / 2)
            )
            g.rvprl[g.Rtp].where[g.rvprl[g.Rtp]] = g.pastsum[g.Rtp] + Round(
                g.coef_rpti[g.Rtp] * g.ncap_tlife[g.Rtp]
            )
            with Loop(g.GRcur[r, cur]):
                g.fil2[t] = (
                    g.coef_pvt[r, t]
                    * g.d[t]
                    / Sum(
                        g.Periodyr[t, g.YEoh],
                        (g.yearval[g.YEoh] - g.b[t] + 1) * g.obj_disc[r, g.YEoh, cur],
                    )
                )
                # .... Calculate remaining levelized capacity levels
                g.coef_cap[r, g.Vnt[v, t], p].where[
                    (
                        (Min(g.m[t] + 1, g.e[t]) < g.rvprl[r, v, p]).where[
                            g.rvprl[r, v, p]
                        ]
                    )
                ] = (
                    1
                    / g.coef_rpti[r, v, p]
                    * Max(
                        power(
                            g.shape[
                                j + (g.ncap_cpx[r, v, p] - 1),
                                age + (g.b[t] - g.pastsum[r, v, p] - 1),
                            ],
                            g.b[t] - g.pastsum[r, v, p] - 1 >= 0,
                        )
                        * (1 - g.fil2[t])
                        + Sum(
                            g.Periodyr[t, g.YEoh].where[
                                (g.yearval[g.YEoh] < g.rvprl[r, v, p])
                            ],
                            g.obj_disc[r, g.YEoh, cur]
                            * power(
                                g.shape[
                                    j + (g.ncap_cpx[r, v, p] - 1),
                                    age
                                    + mod(
                                        g.yearval[g.YEoh] - g.pastsum[r, v, p],
                                        Round(g.ncap_tlife[r, v, p]),
                                    ),
                                ],
                                g.yearval[g.YEoh] - g.pastsum[r, v, p] >= 0,
                            ),
                        )
                        / g.coef_pvt[r, t]
                        * g.fil2[t],
                        g.shape[
                            j + (g.ncap_cpx[r, v, p] - 1),
                            age + Max(0, g.e[t] - g.pastsum[r, v, p]),
                        ].where[(g.e[t] < g.rvprl[r, v, p])],
                    )
                )

            # ...Derive overriding COEF_OCOM coefficients
            g.coef_ocom[r, g.Vnt[v, t], p, c].where[g.RtpCgc[r, v, p, "CAPFLO", c]] = (
                g.coef_rpti[r, v, p]
                * (
                    Max(
                        0,
                        power(
                            g.shape[
                                j + (g.ncap_cpx[r, v, p] - 1),
                                age + (g.b[t] - g.pastsum[r, v, p] - 1),
                            ],
                            g.b[t] - g.pastsum[r, v, p] - 1 >= 0,
                        )
                        - g.coef_cap[r, v, t, p],
                    )
                    * g.ncap_ocom[r, v, p, c]
                    / g.fpd[t]
                ).where[(g.b[t] < g.rvprl[r, v, p])]
            )

            g.coef_ocom[r, v, t[tt + 1], p, c].where[
                (
                    (g.b[t] > g.pastsum[r, v, p])
                    & g.Vnt[v, tt]
                    & g.RtpCgc[r, v, p, "CAPFLO", c]
                )
            ] = (
                g.coef_rpti[r, v, p]
                * Max(0, g.coef_cap[r, v, tt, p] - g.coef_cap[r, v, t, p])
                * g.ncap_ocom[r, v, p, c]
                / g.fpd[t]
            )

        g.RtpCgc.setRecords(None)
        g.coef_cap.setRecords(None)
        g.pastsum.setRecords(None)
        g.rvprl.setRecords(None)
