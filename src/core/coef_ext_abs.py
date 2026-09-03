# coef_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_EXT.vda oversees extended preprocessor activities after COEF_MAIN
# *   %1 - extension name
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Domain,
    Else,
    If,
    Loop,
    Number,
    Ord,
    Product,
    Set,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, abs, aggregate, project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def ncap_afac_reset_violations(g: TimesModelClass) -> Set:
    """BS_RMAX decreasing at slower reserve types - reset."""
    r, p, c = g.r, g.p, g.c
    Rtp, ncap_afac = g.Rtp, g.ncap_afac

    violations = Set(
        g.container, name="violations_r_v_p_c_ncap_afac", domain=[r, g.allyear, p, c]
    )
    violations[Rtp, c] = ncap_afac[Rtp, c]
    return violations


class CoefExtAbs(GamsClass):
    """Translation unit for coef_ext.abs."""

    # Instance attributes
    module_name: str = "coef_ext_abs"
    gams_source: str = "coef_ext.abs"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.exec1)

    def exec1(self: CoefExtAbs) -> None:
        g = self.tc
        # * Get storage, end-use and supply processes
        g.BsBsc[g.Rp, g.c].where[(~(g.PrcCap[g.Rp]))] = False
        project(source=g.bs_stime, target=g.Trackp)
        project(source=g.coef_afups, target=g.RpPrc)
        g.RpPrc[g.RpPrc] = g.Trackp[g.RpPrc]
        project(source=g.BsBsc, target=g.Trackp)
        g.Trackpc[g.Rpc[g.r, g.p, g.c]] = sparse(g.NrgTmap[g.r, "ELC", g.c])
        # * Storage with inflow
        g.BsEndp[g.RpStg[g.Rp]].where[
            Sum(g.Top[g.Trackpc[g.RpcStg[g.Rp, g.c]], "IN"], 1.0)
        ] = True
        # * Qualify as power storage
        g.BsStgp[g.RpPrc[g.Rp]].where[
            Sum(g.Top[g.RpcStg[g.Trackpc[g.Rp, g.c]], "OUT"], 1.0)
        ] = True
        g.BsStgp[g.RpPrc[g.Rp]].where[
            Sum(g.Top[g.RpcStg[g.Rp, g.c], "OUT"], ~(g.Trackpc[g.Rp, g.c]))
        ] = False
        g.BsStgp[g.RpPrc[g.Rp]].where[
            (((~(g.BsEndp[g.Rp])) + g.Trackp[g.Rp]).where[g.prc_sc[g.Rp]])
        ] = False
        g.bs_stime[g.BsStgp[g.r, g.p], g.c, "UP"].where[g.bs_rtype[g.r, g.c]] = Smax(
            g.bd, g.bs_stime[g.r, g.p, g.c, g.bd]
        )
        g.bs_stime[g.Rp, g.c, g.bd].where[
            ((~(g.BsStgp[g.Rp])).where[g.bs_stime[g.Rp, g.c, g.bd]])
        ] = False
        g.BsBsc[g.BsStgp, g.c] = False
        # * Qualify as power supply
        project(source=g.ncap_afcs, target=g.RpGrp)
        g.BsSupp[g.Trackp[g.RpStd[g.Rp]]].where[
            Sum(g.Top[g.RpcPg[g.Trackpc[g.Rp, g.c]], "OUT"], 1.0)
        ] = True
        g.BsSupp[g.Trackp[g.RpStg[g.Rp]]].where[
            Sum(g.Top[g.Trackpc[g.RpGrp[g.Rp, g.c]], "OUT"], 1.0)
        ] = True
        g.BsSupp[g.BsEndp[g.Rp]].where[
            Sum(g.Top[g.RpcStg[g.Rp, g.c], "OUT"], ~(g.Trackpc[g.Rp, g.c]))
        ] = False
        g.BsSupp[g.BsSupp[g.RpStd[g.Rp]]].where[
            Product(g.RpcSpg[g.Rp, g.c], g.Trackpc[g.Rp, g.c])
        ] = False
        g.BsSupp[g.BsStgp] = False
        # * Qualify as end-user process
        g.Trackp[g.RpStg] = True
        g.BsEndp[g.Trackp[g.RpFlo[g.Rp]]] = ~(g.BsSupp[g.Rp] + g.BsStgp[g.Rp])
        g.BsBsc[g.BsEndp[g.r, g.p], g.c].where[
            ((~(g.RpPgact[g.r, g.p])).where[g.BsAneg[g.r, g.c]])
        ] = False
        g.BsNegp[g.Trackp[g.r, g.p]] = Sum(
            g.BsBsc[g.r, g.p, g.c].where[g.BsAneg[g.r, g.c]], 1.0
        )
        g.BsNegp[g.BsSupp[g.Rp]].where[g.RpUpl[g.Rp, "FX"]] = True
        # *-----------------------------------------------------------------------------
        # * Levelization
        g.BsPrs[g.PrcTs[g.Trackp[g.Rp], g.s]].where[
            (g.RpStd[g.Rp] + g.RpsStg[g.Rp, g.s])
        ] = True
        # * Hold RMAX processes to be levelized
        g.vda_flop[
            g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.c, g.s + g.stoa[g.s]
        ].where[g.stoa[g.s]] = sparse(g.bs_rmax[g.r, g.ll, g.p, g.c, g.s])
        aggregate(source=g.vda_flop, target=g.prc_ymax)
        g.vda_flop.setRecords(None)
        g.prc_ymax[g.Rp].where[g.BsPrs[g.Rp, "ANNUAL"]] = False
        # * Reserve Commodity attributes
        with Loop(g.ComTsl[g.r, g.c, g.tslvl].where[g.bs_rtype[g.r, g.c]]):
            g.f[...] = Ord(g.tslvl) - 1.0
            with Loop(g.Rjlvl[g.j, g.r, g.tsl].where[(g.f >= Ord(g.tsl))]):  # noqa: SIM117
                with Loop(g.TsGroup[g.r, g.tsl, g.ts]):
                    g.bs_rtcs[g.Rsp, g.r, g.t, g.c, g.s].where[
                        (~(g.bs_rtcs[g.Rsp, g.r, g.t, g.c, g.s]))
                    ] = sparse(
                        g.bs_rtcs[g.Rsp, g.r, g.t, g.c, g.ts].where[
                            (g.stoal[g.r, g.s] == g.f) & g.RsBelow[g.r, g.ts, g.s]
                        ]
                    )
        # * Put-back
        g.bs_omega[g.Rtc, g.s] = sparse(g.bs_rtcs["OMEGA", g.Rtc, g.s])
        g.bs_delta[g.Rtc, g.s] = sparse(g.bs_rtcs["DELTA", g.Rtc, g.s])
        # * Reserve Process attributes
        project(source=g.bs_maint, target=g.RpPrc)
        g.RpPrc[g.RpPrc[g.Rp]] = g.PrcCap[g.Rp].where[g.RpStd[g.Rp]] + Sum(
            g.RpsCaflac[g.PrcTs[g.RpStg[g.Rp], g.s], g.bd], True
        )
        g.bs_maint[g.r, g.v, g.p, g.s].where[(~(g.RpPrc[g.r, g.p]))] = 0.0
        g.RpUpl[g.RpPrc, "FX"] = True
        g.act_ups[g.Rtp[g.r, g.t, g.p], g.s, "N"].where[g.bs_maint[g.Rtp, g.s]] = (
            g.bs_maint[g.Rtp, g.s]
            * Max(
                Number(1.0).where[(g.bs_maint[g.Rtp, g.s] <= 1.0)],
                (1.0 / g.g_yrfr[g.r, g.s] / 8760.0).where[
                    (~(g.coef_af[g.r, g.t, g.t, g.p, g.s, "UP"]))
                ],
            ).where[g.ts_cycle[g.r, g.s]]
        )
        with Loop(Domain(g.Rlup[g.r, g.tslvl, g.tsl], g.TsGroup[g.r, g.tsl, g.ts])):
            g.bs_maint[g.Rtp[g.r, g.v, g.p], g.ts].where[
                (
                    (~(g.bs_maint[g.Rtp, g.ts])).where[
                        g.PrcTsl[g.r, g.p, g.tslvl] & g.RpPrc[g.r, g.p]
                    ]
                )
            ] = -Max(0.0, Smax(g.RsBelow1[g.r, g.ts, g.s], g.bs_maint[g.Rtp, g.s]))
        with Loop(Domain(g.Rjlvl[g.j, g.r, g.tsl], g.Rlup[g.r, g.tslvl, g.tsl])):  # noqa: SIM117
            with Loop(g.TsGroup[g.r, g.tsl, g.ts]):
                g.bs_maint[g.Rtp[g.r, g.v, g.p], g.s].where[
                    ((~(g.bs_maint[g.Rtp, g.s])).where[g.bs_maint[g.Rtp, g.ts]])
                ] = -abs(g.bs_maint[g.Rtp, g.ts]).where[g.RsBelow[g.r, g.ts, g.s]]
                g.bs_rmax[g.Rtp[g.r, g.v, g.p], g.c, g.s].where[
                    (
                        (~(g.bs_rmax[g.Rtp, g.c, g.s])).where[
                            g.BsPrs[g.r, g.p, g.s] & g.prc_ymax[g.r, g.p]
                        ]
                    )
                ] = sparse(g.bs_rmax[g.Rtp, g.c, g.ts].where[g.RsBelow[g.r, g.ts, g.s]])
        # * Generation & load Variances
        with Loop(g.Rjlvl[g.j, g.r, g.tsl].where[(Ord(g.tsl) < 4.0)]):  # noqa: SIM117
            with Loop(g.TsGroup[g.r, g.tsl, g.ts]):
                g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s].where[
                    (
                        (~(g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s])).where[
                            g.Finest[g.r, g.s]
                        ]
                    )
                ] = sparse(
                    g.bs_sigma[g.r, g.t, g.c, g.BsK, g.ts].where[
                        g.RsBelow[g.r, g.ts, g.s]
                    ]
                )
        # * Default values
        g.bs_share[g.Rtc, g.Bdneq, "N"] = sparse(g.bs_lambda[g.Rtc])
        g.Rxx.setRecords(None)
        g.Rxx[g.BsApos[g.r, g.c], g.Com].where[
            (
                (g.bs_rtype[g.r, g.c] + g.bs_rtype[g.r, g.Com] == 0.0).where[
                    g.BsAneg[g.r, g.Com]
                ]
            )
        ] = True
        with Loop(g.Rxx[g.r, g.c, g.Com]):
            g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s].where[
                (~(g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s]))
            ] = sparse(g.bs_sigma[g.r, g.t, g.Com, g.BsK, g.s])
            g.bs_sigma[g.r, g.t, g.Com, g.BsK, g.s].where[
                (~(g.bs_sigma[g.r, g.t, g.Com, g.BsK, g.s]))
            ] = sparse(g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s])
            g.bs_delta[g.r, g.t, g.c, g.s].where[
                (~(g.bs_delta[g.r, g.t, g.c, g.s]))
            ] = sparse(g.bs_delta[g.r, g.t, g.Com, g.s])
            g.bs_delta[g.r, g.t, g.Com, g.s].where[
                (~(g.bs_delta[g.r, g.t, g.Com, g.s]))
            ] = sparse(g.bs_delta[g.r, g.t, g.c, g.s])
        # * Imbalance topology
        with Loop(
            Domain(g.Trackpc[g.RpFlo[g.r, g.p], g.c], g.BsK).where[
                g.gr_genmap[g.r, g.p, g.BsK]
            ]
        ):
            with If(g.gr_genmap[g.r, g.p, g.BsK] > 0.0):
                g.BsTop[g.Top[g.r, g.p, g.c, g.io]].where[
                    g.Top[g.r, g.p, g.c, "OUT"]
                ] = True
            with Else():
                g.BsTop[g.Top[g.r, g.p, g.c, g.io]].where[
                    (g.ips[g.io] + g.PrcMap[g.r, "STG", g.p])
                ] = True
        g.gr_genmap[g.r, g.p[g.BsK], g.p].where[
            Product(g.prc.where[g.gr_genmap[g.r, g.prc, g.p]], 0.0)
        ] = 1.0
        g.Rxx.setRecords(None)
        g.Trackp.setRecords(None)
        g.RpPrc.setRecords(None)
        g.RpGrp.setRecords(None)
        g.Trackpc.setRecords(None)
        # * Timeslices
        project(source=g.bs_omega, target=g.Rcs)
        with Loop(g.ComTs[g.Rcs[g.r, g.c, g.s]]):
            g.BsComts[g.r, g.c, g.ts].where[g.RsTree[g.r, g.s, g.ts]] = True
        g.bs_delta[g.RtcsVarc[g.Rtc, g.s]].where[
            ((~(g.bs_delta[g.Rtc, g.s])).where[g.bs_omega[g.Rtc, g.s]])
        ] = 1.0
        g.bs_sigma[g.Rtc[g.r, g.t, g.c], g.BsK, g.s].where[
            (
                (g.bs_lambda[g.Rtc].where[g.BsComts[g.r, g.c, g.s]] == 0.0).where[
                    g.bs_sigma[g.Rtc, g.BsK, g.s]
                ]
            )
        ] = 0.0
        with Loop(
            Domain(g.r, g.t, g.c, g.BsK, g.s).where[
                g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s]
            ]
        ):
            g.BsRtk[g.r, g.t, g.BsK] = True
        with Loop(g.ComLim[g.r, g.c, g.lA].where[g.bs_rtype[g.r, g.c]]):
            g.bs_omega[g.r, "0", g.c, g.s].where[g.BsComts[g.r, g.c, g.s]] = (
                g.Finest[g.r, g.s].where[g.ips[g.lA]]
                + g.ComTs[g.r, g.c, g.s].where[g.bd[g.lA]]
            )
        # * Activate COMNET, disable COMPRD
        g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.bs_rtype[g.r, g.c]] = (
            g.BsComts[g.r, g.c, g.s]
        )
        g.RcsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s], "FX"] = sparse(g.bs_rtype[g.r, g.c])
        g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.bs_rtype[g.r, g.c]] = False
        g.RcsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s], "FX"].where[
            g.bs_rtype[g.r, g.c]
        ] = False
        g.com_bndprd[g.RtcsVarc[g.r, g.t, g.c, g.s], "UP"].where[
            (
                (~(g.BsComts[g.r, g.c, g.s].where[g.bs_lambda[g.r, g.t, g.c]])).where[
                    g.bs_rtype[g.r, g.c]
                ]
            )
        ] = SpecialValues.EPS
        g.com_agg[g.r, g.t, g.c, g.c].where[g.bs_rtype[g.r, g.c]] = 1.0
        g.RcAgp[g.Rc, "FX"] = sparse(g.bs_rtype[g.Rc])
        # * Post-process RMAX; no reserve supply from multi-output AFC processes
        g.bs_rmax[g.r, g.v, g.p, g.c, g.s].where[
            (
                g.BsSupp[g.r, g.p].where[
                    g.RpStd[g.r, g.p] & g.RpsCaflac[g.r, g.p, g.s, "UP"]
                ]
            )
        ] = 0.0
        with Loop(Domain(g.Rc[g.r, g.c], g.bd).where[g.BsAbd[g.Rc, g.bd]]):
            g.vda_flop[g.Rtp[g.r, g.v, g.p], g.c, g.s].where[
                (
                    (
                        g.BsPrs[g.r, g.p, g.s].where[g.prc_ymax[g.r, g.p]]
                        + g.Annual[g.s]
                    ).where[g.BsBsc[g.r, g.p, g.c]]
                )
            ] = Smax(
                g.BsAbd[g.r, g.Com, g.bd].where[
                    ((g.bs_rtype[g.Rc] - g.bs_rtype[g.r, g.Com]) * g.bdsig[g.bd] <= 0.0)
                ],
                g.bs_rmax[g.Rtp, g.Com, g.s],
            )
        g.vda_flop[g.Rtp, g.c, g.s].where[
            (
                (g.bs_rmax[g.Rtp, g.c, g.s] == g.vda_flop[g.Rtp, g.c, g.s]).where[
                    g.bs_rmax[g.Rtp, g.c, g.s]
                ]
            )
        ] = 0.0
        g.bs_rmax[g.Rtp, g.c, g.s] = sparse(g.vda_flop[g.Rtp, g.c, g.s])
        aggregate(source=g.vda_flop, target=g.ncap_afac)
        violations = ncap_afac_reset_violations(g=g)
        g.pp_qaput_logger.log_violations(
            violations_df=violations.records,
            err_level=1,
            group_desc="BS_RMAX decreasing at slower reserve types - reset",
            message_template=(
                "WARNING       - Kept at preceding value,  R={R} P={P} V={ALLYEAR} C={C}"
            ),
        )
        g.bs_rmax[g.Rtp[g.r, g.v, g.p], g.c, g.Annual[g.s]].where[
            g.BsBsc[g.r, g.p, g.c]
        ] = g.bs_rmax[g.Rtp, g.c, g.s].where[(~(g.prc_ymax[g.r, g.p]))]

        # * Controls for reserve limits
        g.RpcConly[g.Rtp[g.r, g.v, g.p], g.c].where[
            (
                (
                    g.bs_rmax[g.Rtp, g.c, "ANNUAL"].where[g.BsSupp[g.r, g.p]]
                    < 1.0 - g.act_minld[g.Rtp].where[g.BsAbd[g.r, g.c, "UP"]]
                ).where[g.BsBsc[g.r, g.p, g.c]]
            )
        ] = True
        with Loop(  # noqa: SIM117
            Domain(g.BsAbd[g.Rc[g.r, g.Com], g.bd], g.c, g.Annual[g.s]).where[
                g.BsAbd[g.r, g.c, g.bd]
            ]
        ):
            with If((g.bs_rtype[g.Rc] - g.bs_rtype[g.r, g.c]) * g.bdsig[g.bd] < 0.0):
                g.RpcConly[g.Rtp[g.r, g.v, g.p], g.c].where[
                    (
                        (
                            g.bs_rmax[g.Rtp, g.c, g.s] >= g.bs_rmax[g.Rtp, g.Com, g.s]
                        ).where[g.bs_rmax[g.Rtp, g.Com, g.s]]
                    )
                ] = False
        with Loop(Domain(g.BsComts[g.r, g.c, g.s], g.BsAbd[g.r, g.c, g.lA])):
            g.BsSbd[g.r, g.s, g.lA] = True
        g.prc_ymax.setRecords(None)
        g.vda_flop.setRecords(None)
        g.ncap_afac.setRecords(None)
        g.Rcs.setRecords(None)
        # * Build UC map
        g.BsUcmap[g.UcMapFlo[g.ucn, g.side, g.r, g.p, g.c]].where[
            (
                g.BsBsc[g.r, g.p, g.c]
                + g.BsStgp[g.r, g.p].where[g.bs_stime[g.r, g.p, g.c, "UP"]]
            )
        ] = sparse(g.bs_rtype[g.r, g.c])
        # * Ensure existence of AF
        g.coef_af[g.RtpVintyr[g.r, g.t, g.t, g.p], g.s, "UP"].where[
            (~(g.RtpCptyr[g.r, g.t, g.t, g.p]))
        ] = sparse(g.ncap_af[g.r, g.t, g.p, g.s, "UP"].where[g.BsPrs[g.r, g.p, g.s]])
