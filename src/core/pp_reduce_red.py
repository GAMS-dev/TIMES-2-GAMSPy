# pp_reduce_red.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Domain,
    Else,
    ElseIf,
    If,
    Loop,
    Number,
    Ord,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import aggregate, project

from core.base_class import GamsClass
from core.dynslite_vda import DynsliteVda

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpReduceRed(GamsClass):
    """Translation unit for pp_reduce.red."""

    # Instance attributes
    module_name: str = "pp_reduce_red"
    gams_source: str = "pp_reduce.red"

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
        self.tc.enqueue(self.reduction_of_model_size)
        self.env.set_global("cal_red", "cal_nored.red")
        if self.env.reduce == "NO":  # L15: GOTO reddone
            self.tc.enqueue(self.reddone)
        else:
            self.tc.enqueue(self.determine_capacity_variables)
            self.tc.enqueue(self.determine_emission_flow_variables)
            if self.env.reduce != "YES":  # L58: GOTO reddone
                self.tc.enqueue(self.reddone)
            else:
                self.env.set_global("cal_red", "cal_red.red")
                self.tc.enqueue(self.update_rpc_act, pgprim=self.env.pgprim)
                self.tc.enqueue(self.get_flo_func)
                self.tc.enqueue(self.check_flo_sum_order)

                self.tc.enqueue(
                    self.check_commodity_processes_in_flo_sum, pgprim=self.env.pgprim
                )
                self.tc.enqueue(self.check_shadow_group)
                self.tc.enqueue(self.update_rpc_ffunc)
                self.tc.enqueue(self.add_to_rpc_ffunc)
                self.tc.enqueue(self.check_act_bnd_level)
                self.tc.enqueue(self.varf_early_clear)
                self.tc.enqueue(self.track_commodities)
                self.tc.enqueue(self.check_commodity)
                self.tc.enqueue(self.set_eps_bounds_prc_ts)
                self.tc.enqueue(
                    self.reddone,
                )

        if self.env.rts() != "S":
            self.include(DynsliteVda(self.tc, self.env, arg1="REDUCE"))

    def reduction_of_model_size(self: PpReduceRed) -> None:
        g = self.tc
        # Reduction of model size
        # -----------------------------------------------------------------------------
        # when no reduction all processes have capacity variables and activity equations
        g.PrcCap[g.Rp] = True
        g.PrcAct[g.Rp] = g.RpStd[g.Rp] + g.RpIre[g.Rp]
        aggregate(g.ncap_af, g.rp_afb)

    def reddone(self: PpReduceRed) -> None:
        g = self.tc
        # Mark emissions to be handled by substitution
        with Loop(g.FsEmis[g.r, g.p, g.cg, g.c, g.Com]):
            g.RpccFfunc[g.r, g.p, g.cg, g.Com] = True
        g.Trackpc.setRecords(None)
        g.Fsck.setRecords(None)
        g.PrcTs2[g.PrcTs[g.RpXred[g.r, g.p], g.s]] = True
        g.RpcPkc[g.Rp, g.c].where[~g.PrcCap[g.Rp]] = False
        g.rpc_pkf[g.RpcPkc] = 0

    def determine_capacity_variables(self: PpReduceRed) -> None:
        g = self.tc

        # -----------------------------------------------------------------------------
        # limiting the number of capacity variables
        # -----------------------------------------------------------------------------
        # determining processes that need capacity variables
        g.PrcCap[g.Rp] = False
        if self.tc.defined("PRC_DSCNCAP"):
            g.PrcCap[g.PrcDscncap] = True

        with Loop(Domain(g.r, g.ucn, g.p).where[g.UcGmapP[g.r, g.ucn, "CAP", g.p]]):
            g.PrcCap[g.r, g.p] = True

        with Loop(Domain(g.r, g.ucn, g.p).where[g.UcGmapP[g.r, g.ucn, "NCAP", g.p]]):
            g.PrcCap[g.r, g.p] = True

        with Loop(g.Rtp[g.r, g.pyr, g.p].where[g.ncap_pasti[g.r, g.pyr, g.p]]):
            g.PrcCap[g.r, g.p] = True

        with Loop(
            Domain(g.Rtp[g.r, g.t, g.p], g.bd).where[g.cap_bnd[g.r, g.t, g.p, g.bd]]
        ):
            g.PrcCap[g.r, g.p] = True
        with Loop(
            Domain(g.Rtp[g.r, g.t, g.p], g.bd).where[g.ncap_bnd[g.r, g.t, g.p, g.bd]]
        ):
            g.PrcCap[g.r, g.p] = True

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_cost[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_fom[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_isub[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_itax[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_fsub[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_ftax[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_dcost[g.r, g.ll, g.p, g.cur] != 0.0)

        g.ObjIcur[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.cur].where[
            g.DmYear[g.ll]
        ] = sparse(g.ncap_dlagc[g.r, g.ll, g.p, g.cur] != 0.0)

        with Loop(g.ObjIcur[g.r, g.ll, g.p, g.cur]):
            g.PrcCap[g.r, g.p] = True

        # [UR]: added checks for fixed availabilities
        g.PrcCap[g.Rp[g.r, g.p]] = sparse(g.rp_afb[g.Rp, "FX"])

        g.RtpsBd[
            g.r, g.t.lag(Ord(g.t), "circular"), g.p, g.s.lag(Ord(g.s), "circular"), "FX"
        ] = sparse(g.ncap_afs[g.r, g.t, g.p, g.s, "FX"])

        g.RtpsBd[g.r, g.t.lag(Ord(g.t), "circular"), g.p, g.Annual, "FX"] = sparse(
            g.ncap_afa[g.r, g.t, g.p, "FX"]
        )

        with Loop(g.RtpsBd[g.r, g.t, g.p, g.s, g.bd]):
            g.PrcCap[g.r, g.p] = True

        g.ObjIcur.setRecords(None)
        g.RtpsBd.setRecords(None)

        if self.env.etl == "YES":
            g.PrcCap[g.r, g.p].where[g.seg[g.r, g.p]] = True

    def determine_emission_flow_variables(self: PpReduceRed) -> None:
        g = self.tc

        # Occurence of emission flow variable can be replaced by term (source flow x emission factor)
        # -------------------------------------------------------------------------------------------
        g.Trackpc.setRecords(None)
        # Get emission commodity candidates:
        g.Trackpc[g.RpStd[g.r, g.p], g.c].where[
            (g.Top[g.r, g.p, g.c, "OUT"].where[g.Env[g.r, g.c]])
        ] = True
        g.Trackpc[g.r, g.p, g.c].where[
            g.RpcPg[g.r, g.p, g.c] + g.RpcAflo[g.r, g.p, g.c]
        ] = False
        # Select only those emissions that have been modeled with FLO_SUM on input flows
        project(g.flo_sum, g.Fsck, "left")
        g.FsEmis[g.Fsck[g.r, g.p, g.cg, g.c, g.Com]].where[
            g.ComGmap[g.r, g.cg, g.c].where[g.Top[g.r, g.p, g.c, "IN"]]
            & g.Trackpc[g.r, g.p, g.Com]
        ] = True
        with Loop(g.FsEmis[g.r, g.p, g.cg, g.c, g.Com]):
            g.RpcEmis[g.r, g.p, g.Com] = True

    def update_rpc_act(self: PpReduceRed, pgprim: str) -> None:
        g = self.tc

        # --------------------------------------------------------------
        # only 1 commodity in PCG
        # => corresponding VAR_FLO can be replaced by VAR_ACT indicated
        #    these cases are stored in RPC_ACT
        # --------------------------------------------------------------
        g.RpcAct[g.RpcPg[g.RpPgact[g.RpStd], g.c]] = True
        # VAR_IRE can be replaced by VAR_ACT if only 1 import or export commodity
        g.RpcAire[g.RpcPg[g.RpIre[g.RpPgact], g.c]] = True
        # If activity is substituted for the primary flow, EQ_ACTFLO is not needed
        g.PrcAct[g.RpPgact] = False
        # --------------------------------------------------------------------------------------------
        # Process without capacity variable and without activity related parameters
        # does not need activity variable
        # --------------------------------------------------------------------------------------------
        g.NoAct[g.PrcAct[g.r, g.p]].where[~g.PrcCap[g.r, g.p]] = True
        # LOOP((RTP(R,T,P),S,BD)$((ACT_BND(RTP,S,BD)>-INF$BDUPX(BD))$ACT_BND(RTP,S,BD)),
        #    NO_ACT(R,P) = NO);
        with Loop(
            Domain(g.Rtp[g.r, g.t, g.p], g.s, g.bd).where[
                (
                    (
                        g.act_bnd[g.Rtp, g.s, g.bd]
                        > Number(SpecialValues.NEGINF).where[g.Bdupx[g.bd]]
                    ).where[g.act_bnd[g.Rtp, g.s, g.bd]]
                )
            ]
        ):
            g.NoAct[g.r, g.p] = False
        with Loop(
            Domain(g.r, g.DmYear, g.p, g.cur).where[
                g.act_cost[g.r, g.DmYear, g.p, g.cur]
            ]
        ):
            g.NoAct[g.r, g.p] = False
        with Loop(Domain(g.r, g.ucn, g.p).where[g.UcGmapP[g.r, g.ucn, "ACT", g.p]]):
            g.NoAct[g.r, g.p] = False
        g.NoAct[g.r, g.p].where[
            Sum(g.RpcCumflo[g.r, g.p, pgprim, g.year, g.ll], 1) > 0
        ] = False
        # Remove activity equation from processes that didn't have activity attributes
        g.PrcAct[g.NoAct] = False
        # Keep RTP_VARA even when no VAR_ACT is needed
        # *RTP_VARA(R,T,P)$NO_ACT(R,P) = NO;
        g.RpXred[g.RpPgflo] = False
        g.RpcAct[g.RpXred[g.RpStd[g.PrcAct]], g.Actcg] = True

    def get_flo_func(self: PpReduceRed) -> None:
        g = self.tc

        # --------------------------------------------------------------------------------------------
        #  If FLO_FUNC between two flow variables and one flow variable defines the activity,
        #  the other flow variable can be expressed by the activity variable
        # --------------------------------------------------------------------------------------------
        #  check whether commodity defining activity is involved in FLO_FUNC
        #  Get all FLO_FUNCs between single-commodity groups
        project(g.flo_func, g.CgGrp, direction="left")
        project(g.CgGrp, g.RpXred)
        g.CgGrp[g.r, g.p, g.cg, g.cg] = False
        g.CgGrp[g.r, g.p, g.cg, g.cg2].where[
            (Sum(g.Rpc[g.r, g.p, g.c].where[g.ComGmap[g.r, g.cg, g.c]], 1) != 1)
        ] = False
        g.CgGrp[g.r, g.p, g.cg1, g.cg].where[
            (
                Sum(
                    g.Rpc[g.RpPgact[g.r, g.p], g.c].where[g.ComGmap[g.r, g.cg, g.c]],
                    1,
                )
                != 1
            )
        ] = False
        g.RpcgPtran[g.Rpc[g.r, g.p, g.c], g.Com, g.cg1, g.cg2].where[
            (
                (
                    g.ComGmap[g.r, g.cg1, g.c]
                    * g.Rpc[g.r, g.p, g.Com]
                    * g.ComGmap[g.r, g.cg2, g.Com]
                ).where[g.CgGrp[g.r, g.p, g.cg1, g.cg2]]
            )
        ] = True

    def check_flo_sum_order(self: PpReduceRed) -> None:
        g = self.tc

        # Ensure that possible reverse ordering due to FLO_SUM is taken into account
        with Loop(
            g.Fsck[g.r, g.p, g.cg1, g.c, g.cg2].where[g.CgGrp[g.r, g.p, g.cg2, g.cg1]]
        ):
            g.RpcgPtran[g.r, g.p, g.c, g.Com, g.cg1, g.cg2].where[
                g.ComGmap[g.r, g.cg2, g.Com]
            ] = True
        g.RpcgPtran[g.r, g.p, g.c, g.Com, g.cg1, g.cg2].where[
            ~(g.RpcAct[g.r, g.p, g.c] + g.RpcAct[g.r, g.p, g.Com])
        ] = False
        project(g.RpcgPtran, g.Trackpc)

    def check_commodity_processes_in_flo_sum(self: PpReduceRed, pgprim: str) -> None:
        g = self.tc

        # Check all processes for commodity-to-commodity FLO_SUM:
        project(g.Fsck, g.RpCgg)
        g.RpcgPtran[g.RpCgg[g.RpcAct[g.r, g.p, g.Com], g.c, g.cg], g.c].where[
            (g.RpPg[g.r, g.p, g.cg] + g.RpcAct[g.r, g.p, g.cg])
        ] = True
        g.RpcgPtran[g.RpCgg[g.Rpc[g.r, g.p, g.Com], g.c, g.Com], g.c].where[
            g.RpcAct[g.r, g.p, g.c]
        ] = True
        g.RpcgPtran[g.RpcAct[g.Rp, pgprim], g.c, g.cg, g.c].where[
            (g.RpPg[g.Rp, g.cg].where[g.RpcAflo[g.Rp, g.c]])
        ] = True

    def check_shadow_group(self: PpReduceRed) -> None:
        g = self.tc

        # If shadow group has special level, don't substitute
        g.RpcgPtran[g.RpSgs, g.c, g.Com, g.cg, g.cg2] = False
        with Loop(g.RpcgPtran[g.RpFlo[g.r, g.p], g.c, g.Com, g.cg, g.cg2]):
            with If(g.RpcAct[g.r, g.p, g.c]):  # type: ignore[arg-type]
                g.RpcFfunc[g.r, g.p, g.Com] = True
            with Else():  # type: ignore[no-untyped-call]
                g.RpcFfunc[g.r, g.p, g.c] = True

    def update_rpc_ffunc(self: PpReduceRed) -> None:
        g = self.tc

        # Remove activity flows and emission flows from RPC_FFUNC
        g.RpcFfunc[g.Rpc].where[(g.RpcAct[g.Rpc] + g.RpcEmis[g.Rpc])] = False
        g.RpcFfunc[g.RpcAflo[g.RpXred[g.Rp], g.c]].where[
            (~g.RpPgact[g.Rp]) | g.Trackpc[g.Rp, g.c]
        ] = False

    def add_to_rpc_ffunc(self: PpReduceRed) -> None:
        g = self.tc

        # Add to RPCC_FFUNC all the CG1-CG2 PTRANS equations that are to be eliminated:
        g.RpcgPtran[g.r, g.p, g.c, g.Com, g.cg, g.cg2].where[
            ~(g.RpcFfunc[g.r, g.p, g.c] + g.RpcFfunc[g.r, g.p, g.Com])
        ] = False
        with Loop(g.RpcgPtran[g.r, g.p, g.c, g.Com, g.cg, g.cg2]):
            g.RpccFfunc[g.r, g.p, g.cg, g.cg2] = True
        g.CgGrp.setRecords(None)
        project(g.RpcAct, g.RpXred)
        g.RpCgg.setRecords(None)

    def check_act_bnd_level(self: PpReduceRed) -> None:
        g = self.tc

        # --------------------------------------------------------------------------------------------
        #  If upper/fixed ACT_BND of zero at a higher TS-level than PRC_TS,
        #  do not generate EQL/E_ACTBND equation but add upper/fixed bound
        #  of zero to the VAR_ACT variables in bnd_act.mod
        # --------------------------------------------------------------------------------------------
        #  (RTP_VARA(r,t,p) will be deleted if only all PRC_TS are fixed to zero in t)
        with Loop(
            Domain(g.r, g.t, g.p, g.s, g.Bdupx).where[
                (
                    (g.act_bnd[g.r, g.t, g.p, g.s, g.Bdupx] == 0.0).where[
                        g.act_bnd[g.r, g.t, g.p, g.s, g.Bdupx]
                    ]
                )
            ]
        ):
            g.RtpsOff[g.r, g.t, g.p, g.s].where[g.RpsPrcts[g.r, g.p, g.s]] = True

    def varf_early_clear(self: PpReduceRed) -> None:
        g = self.tc

        # Handle any earlier clearing of VARF
        with Loop(
            Domain(
                g.RtpcsOut[g.r, g.t, g.p, g.c, g.s],
                g.RpcsVar[g.RpStd[g.r, g.p], g.c, g.s],
            )
        ):
            with If(g.RpcFfunc[g.r, g.p, g.c]):  # type: ignore[arg-type]
                g.RtpsOff[g.r, g.t, g.p, g.ts].where[
                    g.PrcTs[g.r, g.p, g.ts] * g.RsTree[g.r, g.s, g.ts]
                ] = True
            with ElseIf(g.RpcAct[g.r, g.p, g.c]):  # type: ignore[arg-type]
                g.RtpsOff[g.r, g.t, g.p, g.s] = True

    def track_commodities(self: PpReduceRed) -> None:
        g = self.tc

        # --------------------------------------------------------------------------------------------
        # Process with upper/fixed activity of zero cannot be used in current period
        # --------------------------------------------------------------------------------------------
        g.Rxx.setRecords(None)
        # Track commodities turned off by some process, by T, timeslice and IO:
        with Loop(g.RtpsOff[g.r, g.t, g.p, g.s]):
            with If(g.RpStd[g.r, g.p]):  # type: ignore[arg-type]
                g.RtcsSing[g.r, g.t, g.c, g.s, g.io].where[
                    g.Top[g.r, g.p, g.c, g.io]
                ] = True
            with Else():  # type: ignore[no-untyped-call]
                g.RtcsSing[g.r, g.t, g.c, g.s, "OUT"].where[
                    g.RpcIre[g.r, g.p, g.c, "IMP"]
                ] = True
        # Track commodities turned off by some process, by IO only:
        with Loop(g.RtcsSing[g.r, g.t, g.c, g.s, g.io]):
            g.Rxx[g.r, g.c, g.io] = True
        g.Rxx[g.Env, "IN"] = False
        g.Rxx[g.Dem, "IN"] = False
        g.Rxx[g.r, g.c, "IN"].where[g.RcAgp[g.r, g.c, "LO"]] = False
        with Loop(
            Domain(g.r, g.t, g.Com, g.c).where[
                (g.Rxx[g.r, g.c, "OUT"].where[g.com_agg[g.r, g.t, g.Com, g.c]])
            ]
        ):
            g.Trackc[g.r, g.c] = True
        g.Rxx[g.Trackc, "OUT"] = False
        g.RcIop[g.Rxx[g.r, g.c, g.io], g.p].where[g.Top[g.r, g.p, g.c, g.io]] = True
        g.RcIop[g.Rxx[g.r, g.c, "IN"], g.p].where[g.RpcIre[g.r, g.p, g.c, "EXP"]] = True
        g.RcIop[g.Rxx[g.r, g.c, "OUT"], g.p].where[g.RpcIre[g.r, g.p, g.c, "IMP"]] = (
            True
        )

    def check_commodity(self: PpReduceRed) -> None:
        g = self.tc

        # Check whether commodity is produced by only one process (including STG, consider e.g. STG_CHRG)
        g.Rxx[g.Rxx[g.r, g.c, g.io]].where[
            (Sum(g.RcIop[g.r, g.c, g.io, g.p], 1) != 1.0)
        ] = False
        g.RtcsSing[g.r, g.t, g.c, g.s, g.io].where[~(g.Rxx[g.r, g.c, g.io])] = False

        # turning off all processes in linking to RTCS_SING
        with (
            Loop(g.RtcsSing[g.r, g.t, g.c, g.s, g.io.lag(1, "circular")]),
            Loop(
                g.Top[g.r, g.p, g.c, g.io].where[
                    (Sum(g.Com.where[g.Top[g.r, g.p, g.Com, g.io]], 1) == 1.0)
                ]
            ),
        ):
            g.RtpsOff[g.r, g.t, g.p, g.s].where[g.RpsPrcts[g.r, g.p, g.s]] = True
        # turn off RHS_COMPRD if single producer is turned off
        g.RhsComprd[g.r, g.t, g.c, g.s].where[g.RtcsSing[g.r, g.t, g.c, g.s, "OUT"]] = (
            False
        )
        g.Trackc.setRecords(None)
        g.RcIop.setRecords(None)
        # --------------------------------------------------------------------------------------------
        g.RtpsOff[g.RtpsOff[g.r, g.t, g.p, g.s]].where[g.PrcMap[g.r, "STG", g.p]] = (
            False
        )
        g.RtpsOff[g.r, g.t, g.p, g.ts] = sparse(
            Sum(g.RsBelow[g.r, g.s, g.ts].where[g.RtpsOff[g.r, g.t, g.p, g.s]], 1)
        )

    def set_eps_bounds_prc_ts(self: PpReduceRed) -> None:
        g = self.tc

        # Set EPS bounds for PRC_TS timeslices, removing the EPS bounds above
        g.act_bnd[g.RtpsOff[g.RtpVara[g.r, g.t, g.p], g.s], "UP"].where[
            g.PrcTs[g.r, g.p, g.s]
        ] = SpecialValues.EPS
        g.act_bnd[g.RtpsOff[g.r, g.t, g.p, g.s], g.bd].where[
            ~(g.PrcTs[g.r, g.p, g.s])
        ] = 0.0

        # all flows of process with RTPS_OFF entry are forced to zero
        # hence flow variable is not required
        g.RtpcsOut[g.Rtpc[g.Rtp[g.r, g.t, g.p], g.c], g.s].where[
            g.RtpsOff[g.r, g.t, g.p, g.s]
        ] = True
        g.RtpVara[g.r, g.t, g.p].where[
            (
                Sum(
                    g.PrcTs[g.r, g.p, g.ts].where[~(g.RtpsOff[g.r, g.t, g.p, g.ts])],
                    1,
                )
                == 0.0
            )
        ] = False
