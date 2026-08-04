# pp_lvlpk_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLPK - levelization of NCAP_PKCNT
# *   arg1 - Default value for leveling
# *=============================================================================*
# * Questions/Comments:
# *  -
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Else,
    If,
    Loop,
    Number,
    Parameter,
    Set,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlpkMod(GamsClass):
    """Translation unit for pp_lvlpk.mod."""

    # Instance attributes
    module_name: str = "pp_lvlpk_mod"
    gams_source: str = "pp_lvlpk.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Number,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.RpcPkc = Set(m, name="RPC_PKC", domain=[g.r, g.p, g.c])
        g.rpc_pkf = Parameter(m, name="RPC_PKF", domain=[g.r, g.p, g.c])

        self.tc.enqueue(self.pp_lvlpk_exec, arg1=self.arg1)

    def pp_lvlpk_exec(self: PpLvlpkMod, arg1: Number) -> None:
        g = self.tc
        (
            ComPkts,
            r,
            cg,
            s,
            Rcs,
            ComTs,
            c,
            ts,
            RsTree,
            ComGmap,
            Trackc,
            ncap_pkcnt,
            RtpIshpr,
            flo_pkcoi,
            Rtp,
            t,
            p,
            PrcPkno,
            Trackpc,
            Rpc,
            Top,
            RpcIre,
            RtpGrp,
            v,
            io,
            ips,
            ts_array,
            f,
            RsBelow,
            Annual,
            TsMap,
            g_yrfr,
            allts,
            sl,
            Finest,
            Trackp,
            PrcPkaf,
            Rp,
            rpc_pkf,
            RpFlo,
            PrcTs2,
            year,
            PrcTs,
            bd,
            ncap_af,
            RpcPkc,
            RpcAct,
            RpStd,
            RpcPg,
            RpPgact,
            RpPg,
            NrgTmap,
        ) = (
            g.ComPkts,
            g.r,
            g.cg,
            g.s,
            g.Rcs,
            g.ComTs,
            g.c,
            g.ts,
            g.RsTree,
            g.ComGmap,
            g.Trackc,
            g.ncap_pkcnt,
            g.RtpIshpr,
            g.flo_pkcoi,
            g.Rtp,
            g.t,
            g.p,
            g.PrcPkno,
            g.Trackpc,
            g.Rpc,
            g.Top,
            g.RpcIre,
            g.RtpGrp,
            g.v,
            g.io,
            g.ips,
            g.ts_array,
            g.f,
            g.RsBelow,
            g.Annual,
            g.TsMap,
            g.g_yrfr,
            g.allts,
            g.sl,
            g.Finest,
            g.Trackp,
            g.PrcPkaf,
            g.Rp,
            g.rpc_pkf,
            g.RpFlo,
            g.PrcTs2,
            g.year,
            g.PrcTs,
            g.bd,
            g.ncap_af,
            g.RpcPkc,
            g.RpcAct,
            g.RpStd,
            g.RpcPg,
            g.RpPgact,
            g.RpPg,
            g.NrgTmap,
        )
        # *-----------------------------------------------------------------------------
        # * Collect PKTS for all COM_PEAK commodities
        with Loop(ComPkts[r, cg, s]):
            Rcs[ComTs[r, c, ts]].where[RsTree[r, s, ts] & ComGmap[r, cg, c]] = True
        Trackc[r, c] = sparse(Sum(Rcs[r, c, s], 1))
        # *-----------------------------------------------------------------------------
        # * Levelization of NCAP_PKCNT
        project(source=ncap_pkcnt, target=RtpIshpr)
        flo_pkcoi[Rtp[r, t, p], c, s].where[Trackc[r, c] & PrcPkno[r, p]] = 0
        Trackpc[Rpc[r, p, c]].where[
            Top[Rpc, "OUT"] + RpcIre[Rpc, "IMP"] & Trackc[r, c]
        ] = True

        RtpGrp[RtpIshpr[Rtp[r, v, p]], c, io[ips]].where[
            Sum(Rcs[r, c, s].where[~ncap_pkcnt[r, v, p, s]], 1) & Trackpc[r, p, c]
        ] = True
        # *-----------------------------------------------------------------------------
        # * Aggregation/inheritance to target timeslices
        # *-----------------------------------------------------------------------------
        with Loop(RtpGrp[r, v, p, c, io]):
            ts_array[s] = ncap_pkcnt[r, v, p, s]
            f[...] = ts_array["ANNUAL"]
            with If((~Sum(RsBelow[r, Annual, s].where[ts_array[s]], 1)).where[f]):
                ncap_pkcnt[r, v, p, s].where[Rcs[r, c, s]] = f
            with Else():  # type: ignore[no-untyped-call]
                # * Set leveling default = %1;
                with If(~f):
                    ts_array[Annual] = arg1
                # * Simultaneous inheritance/aggregation; but only if target level value is not present
                with Loop(Rcs[r, c, ts].where[~ts_array[ts]]):
                    ncap_pkcnt[r, v, p, ts] = sparse(
                        Sum(
                            TsMap[r, ts, s].where[Finest[r, s]],
                            g_yrfr[r, s]
                            / g_yrfr[r, ts]
                            * (
                                ts_array[s]
                                + Sum(
                                    RsBelow[r, allts, s].where[
                                        ~Sum(
                                            sl.where[RsBelow[r, allts, sl]],
                                            TsMap[r, sl, s] * ts_array[sl],
                                        )
                                        & ts_array[allts]
                                    ],
                                    ts_array[allts],
                                )
                            ),
                        )
                    )
        # *-----------------------------------------------------------------------------
        # * Peak contribution
        # * If PRC_PKAF, apply PKCNT only for capacity
        Trackp[PrcPkaf[Rp]] = ~PrcPkno[Rp]
        Trackpc[PrcPkno[Rp], c] = False
        rpc_pkf[Rpc[RpFlo[r, p], c]].where[Trackc[r, c]] = (
            SpecialValues.EPS ** (Number(1)).where[Trackp[r, p]]
        )
        # * If no PKCNT provided, copy NCAP_AF if PRC_PKAF; otherwise set default 1
        with Loop(Trackpc[r, p, c]):
            PrcTs2[r, p, s].where[
                ~Sum(Rtp[r, v, p], ncap_pkcnt[Rtp, s]) & Rcs[r, c, s]
            ] = True
        ncap_pkcnt[r, year, p, s].where[ncap_pkcnt[r, year, p, s] == 0] = 0
        ncap_pkcnt[Rtp[r, v, p], s].where[PrcTs2[r, p, s]] = (Number(1)).where[
            ~PrcPkaf[r, p]
        ] + (
            Sum(
                PrcTs[r, p, ts].where[RsTree[r, s, ts]],
                Smax(bd, ncap_af[Rtp, ts, bd])
                * (1 + (g_yrfr[r, ts] / g_yrfr[r, s] - 1).where[RsBelow[r, s, ts]]),
            )
        ).where[PrcPkaf[r, p]]
        # *-----------------------------------------------------------------------------
        # * RPC_PKC indicator for peak contribution by capacity
        RpcPkc[Trackpc[RpcAct[Trackp[RpStd], c]]] = True
        Trackpc[Rp, c].where[~(RpcPg[Rp, c] * RpFlo[Rp])] = False
        RpcPkc[Trackpc[RpPgact[Rp], c]].where[RpPg[Rp, c] + Trackp[Rp]] = True
        with Loop(NrgTmap[r, "ELC", c].where[Trackc[r, c]]):
            RpcPkc[Trackpc[Trackp[r, p], c]] = True
            Trackp[r, p].where[Trackpc[r, p, c]] = False
        Trackp.setRecords(None)
        Trackc.setRecords(None)
        Trackpc.setRecords(None)
        RtpGrp.setRecords(None)
        Rcs.setRecords(None)
        RtpIshpr.setRecords(None)
        PrcTs2.setRecords(None)
