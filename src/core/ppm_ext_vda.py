# ppm_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPM_EXT.VDA oversees extended preprocessor activities
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, Domain, If, Loop, Number, Set, Smax, SpecialValues, Sum, sparse
from gamspy.math import Max, aggregate, floor, log, mod, project

from core.base_class import GamsClass
from core.dynslite_vda import DynsliteVda
from core.equcrtp_vda import EqucrtpVda, EqucrtpVdaConfig
from core.pp_actef_vda import PpActefVda
from core.pp_qaput_mod import pp_qaput
from core.resloadc_vda import ResloadcVda

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtVda(GamsClass):
    """Translation unit for ppm_ext.vda."""

    # Instance attributes
    module_name: str = "ppm_ext_vda"
    gams_source: str = "ppm_ext.vda"

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
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        self.tc.enqueue(self.display)

        if self.tc.defined("GR_VARGEN"):
            self.include(ResloadcVda(self.tc, self.env, arg1="COEF"))

        self.tc.enqueue(self.exec1, pgprim=self.env.pgprim)

        self.include(PpActefVda(self.tc, self.env, arg1="LVL"))
        self.tc.enqueue(self.catch_shape_indexes, pgprim=self.env.pgprim)

        if self.tc.defined("RP_FFSGG"):
            self.tc.enqueue(self.prepare_map)

        self.tc.enqueue(
            self.add_acteff_to_rpc_func,
            condition=self.env.reduce != "YES",
        )

        g.RpgAfcx = Set(m, name="RPG_AFCX", domain=[g.r, g.p, g.c, g.ie])

        self.tc.register_assignment(self.tc.RpsCaflac)
        self.tc.enqueue(self.prep_commodity_factors, pgprim=self.env.pgprim)

        self.include(EqucrtpVda(self.tc, self.env, EqucrtpVdaConfig(arg1="PPM_EXT")))

        if self.env.rts() != "S":
            self.include(DynsliteVda(self.tc, self.env, arg1="POSTLEV"))

    def display(self: PpmExtVda) -> None:
        print("PPM_EXT Invoked")

    def exec1(self: PpmExtVda, pgprim: str) -> None:
        g = self.tc
        project(source=g.act_ups, target=g.RpUpl)
        g.RpUpl[g.Rp, g.lA].where[(~(g.PrcCap[g.Rp] * g.RpStd[g.Rp]))] = False
        g.RpPl[g.r, g.p, g.Lnx] = sparse(
            Sum(g.v.where[g.act_lospl[g.r, g.v, g.p, "FX"]], 1.0)
        )
        # *-----------------------------------------------------------------------------
        # * Prepare FLO_SUMs for VDA_EMCB emissions
        g.FsEmcb[g.RpIre[g.r, g.p], g.Com, g.c] = False
        project(source=g.flo_sum, target=g.Fsck, direction="left")
        g.flo_sum[g.Rtp[g.r, g.v, g.p], g.Com, g.c, g.Com, g.s].where[
            (
                (~(g.flo_sum[g.Rtp, g.Com, g.c, g.Com, g.s])).where[
                    g.RpcsVar[g.r, g.p, g.c, g.s] & g.FsEmcb[g.r, g.p, g.Com, g.c]
                ]
            )
        ] = g.vda_emcb[g.r, g.v, g.c, g.Com]
        g.vda_emcb[g.r, g.allyear, g.c, g.Com] = 0.0
        # *-----------------------------------------------------------------------------
        # * Auxiliary flow variable can be replaced by term (source flow x coefficient)
        g.CgGrp[g.r, g.p, g.c, g.Com].where[g.Fsck[g.r, g.p, g.c, g.Com, g.c]] = True
        g.CgGrp[g.FsEmcb] = True
        g.Trackpg[g.Rpc[g.RpFlo, g.c]] = sparse(Sum(g.CgGrp[g.Rpc, g.Com], 1.0))
        g.Trackpg[g.RpcPg] = False
        g.Trackpg[g.RpcFfunc] = False
        g.Trackpg[g.RpcEmis] = False
        with Loop(g.CgGrp[g.r, g.p, g.c, g.Com].where[g.RpcEmis[g.r, g.p, g.Com]]):
            g.Trackpg[g.r, g.p, g.c] = False
        g.FsEmis[g.CgGrp[g.Trackpg[g.r, g.p, g.c], g.Com], g.c] = True
        # * Prevent reduction of source commodity if target reduced
        project(source=g.FsEmis, target=g.FsEmit)
        project(source=g.FsEmis, target=g.Trackpc)
        g.Trackpg[g.Trackpc] = False
        g.CgGrp.setRecords(None)
        g.Trackpc.setRecords(None)
        g.FsEmis.setRecords(None)
        g.FsEmcb.setRecords(None)
        g.Fsck.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * ACT_EFF preparation, inheritance and aggregation
        g.Trackpc[g.RpcAce[g.Rpc]] = True
        g.Trackpc[g.RpcSpg[g.Rp, g.c]].where[g.RpcAce[g.Rp, pgprim]] = True
        g.Rxx.setRecords(None)
        g.Rxx[g.RpcAce] = True
        g.Rxx[g.Trackpc] = False
        g.RpgAce[g.Rxx[g.r, g.p, g.cg], g.io].where[
            (
                Sum(
                    g.Top[g.r, g.p, g.c, g.io].where[g.ComGmap[g.r, g.cg, g.c]], 1.0
                ).where[(~(g.RpInout[g.r, g.p, g.io]))]
            )
        ] = True
        g.Rxx.setRecords(None)
        # * Mark groups that have ACT_EFF for PG commodities
        with Loop(g.Trackpc[g.RpcPg[g.r, g.p, g.c]]):
            g.Trackp[g.r, g.p] = True
        with Loop(
            g.RpgAce[g.Trackp[g.r, g.p], g.cg, g.io].where[
                (
                    ~(
                        Sum(
                            g.Top[g.r, g.p, g.c, g.io].where[
                                (
                                    g.ComGmap[g.r, g.cg, g.c]
                                    * (~(g.RpcSpg[g.r, g.p, g.c]))
                                )
                            ],
                            1.0,
                        )
                    )
                )
            ]
        ):
            g.RpgPace[g.r, g.p, g.cg] = True
        with Loop(g.RpgPace[g.r, g.p, g.cg]):
            g.Trackp[g.r, g.p] = False
        # * Mark commodities in groups as handled; Next, try to use shadow group
        with Loop(g.RpgAce[g.r, g.p, g.cg, g.io]):
            g.Trackpc[g.r, g.p, g.c].where[g.ComGmap[g.r, g.cg, g.c]] = False
        g.Rxx[g.PrcSpg[g.r, g.p, g.cg]].where[
            (g.Trackp[g.r, g.p] + Sum(g.Trackpc[g.RpcSpg[g.r, g.p, g.c]], True))
        ] = True
        g.RpgPace[g.Rxx[g.Trackp, g.cg]] = True
        g.Trackpc[g.RpcSpg] = False
        # * Convert any ACT_EFF for 'ACT' to SPG if ACT_EFF not provided for SPG
        g.act_eff[g.Rtp[g.r, g.v, g.p], g.cg, g.s].where[g.Rxx[g.r, g.p, g.cg]] = (
            sparse(g.act_eff[g.Rtp, pgprim, g.s])
        )
        g.act_eff[g.r, g.ll, g.p, pgprim, g.s] = 0.0
        # * Set the commodity type as the Group for remaining commodities
        with Loop(
            Domain(
                g.Top[g.Trackpc[g.r, g.p, g.c], g.io], g.ComTmap[g.r, g.ComType, g.c]
            ).where[(~(g.RpInout[g.r, g.p, g.io]))]
        ):
            g.Rxx[g.r, g.p, g.ComType] = True
        g.RpgAce[g.Rxx[g.r, g.p, g.cg], g.io.lag(1, "circular")].where[
            g.RpInout[g.r, g.p, g.io]
        ] = True
        # * Set default ACT_EFF for group to 1 if none specified
        with Loop(g.io):
            g.act_eff[g.Rtp[g.r, g.v, g.p], g.cg, g.Annual].where[
                (
                    (g.act_eff[g.Rtp, g.cg, g.Annual] == 0.0).where[
                        g.RpgAce[g.r, g.p, g.cg, g.io]
                    ]
                )
            ] = 1.0

    def catch_shape_indexes(self: PpmExtVda, pgprim: str) -> None:
        g = self.tc
        # * Catch shape indexes for shadow group
        if ((Card(g.flo_funcx)) * 1).toValue():
            g.flo_funcx[g.r, g.v, g.p, g.cg1, g.Actcg[g.cg]].where[
                g.PrcSpg[g.r, g.p, g.cg1]
            ] = sparse(g.flo_funcx[g.r, g.v, g.p, g.cg, g.cg])
            g.flo_funcx[g.r, g.v, g.p, g.cg, g.Com].where[
                (g.RpcPg[g.r, g.p, g.Com].where[g.RpGrp[g.r, g.p, g.cg]])
            ] = sparse(g.flo_funcx[g.r, g.v, g.p, g.cg, pgprim])
            g.flo_funcx[g.r, g.v, g.p, g.cg, g.Actcg].where[
                (g.Actcg[g.cg] + g.RpGrp[g.r, g.p, g.cg])
            ] = 0.0
            g.flo_funcx[g.r, g.v, g.p, g.cg, g.cg2].where[g.RpPg[g.r, g.p, g.cg]] = (
                sparse(g.flo_funcx[g.r, g.v, g.p, pgprim, g.cg2])
            )
        # * Ensure that ACT_EFF modeled flows are not reduced:
        project(source=g.RpgAce, target=g.Trackp)
        with Loop(
            g.RpcgPtran[g.Trackp[g.r, g.p], g.c, g.Com, g.cg, g.cg2].where[
                (g.RpcAce[g.r, g.p, g.c] + g.RpcAce[g.r, g.p, g.Com])
            ]
        ):
            g.RpccFfunc[g.r, g.p, g.cg, g.cg2] = False
        g.RpcgPtran[g.Trackp, g.c, g.Com, g.cg, g.cg2].where[
            (~(g.RpccFfunc[g.Trackp, g.cg, g.cg2]))
        ] = False
        g.RpcFfunc[g.RpcAce[g.r, g.p, g.c]] = False
        g.RpcNoflo[g.RpcAce[g.r, g.p, g.c]] = False
        g.Trackp[g.RpPgflo] = False
        g.PrcAct[g.NoAct[g.Trackp]] = True
        g.NoAct[g.Trackp] = False
        g.Trackp.setRecords(None)

    def prepare_map(self: PpmExtVda) -> None:
        g = self.tc
        # * Prepare map for uncertain efficiencies
        g.RpFfsgg[g.PrcSpg[g.r, g.p, g.cg1], g.Actcg[g.cg]].where[
            g.RpFfsgg[g.r, g.p, g.cg, g.cg]
        ] = 0.0
        g.RpFfsggm[g.RpGrp[g.PrcSpg[g.r, g.p, g.cg1]], g.c, g.Actcg[g.cg], g.cg].where[
            g.RpcPg[g.r, g.p, g.c]
        ] = sparse(g.RpFfsgg[g.r, g.p, g.cg, g.cg])
        g.RpFfsggm[g.RpGrp[g.r, g.p, g.cg], g.Com, g.cg, g.Actcg].where[
            g.RpcPg[g.r, g.p, g.Com]
        ] = sparse(g.RpFfsgg[g.r, g.p, g.cg, g.Actcg])
        g.RpGrp[g.r, g.p, g.Actcg] = sparse(Sum(g.RpGrp[g.PrcSpg[g.r, g.p, g.cg]], 1.0))
        g.RpFfsgg[g.RpGrp, g.Actcg] = 0.0
        g.RpFfsggm[g.PrcSpg[g.r, g.p, g.cg1], g.Actcg[g.cg], g.cg, g.cg].where[
            g.RpFfsgg[g.r, g.p, g.cg, g.cg]
        ] = True

    def add_acteff_to_rpc_func(self: PpmExtVda, condition: bool) -> None:
        # TODO still needs transaltion, since ontop of pp_qaput
        # there are direct PUT calls in the loops
        include_pp_qaput_1 = pp_qaput(
            "PUTOUT",
            "PUTGRP",
            "01",
            "ACT_EFF shadow group contains only an auxiliary flow",
        )
        include_pp_qaput_2 = pp_qaput(
            "PUTOUT",
            "PUTGRP",
            "09",
            "Inconsistent/spurious process transformation parameters",
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Add singleton ACT_EFFs to RPC_FFUNC
  OPTION TRACKPC < RPG_1ACE; RPC_NOFLO(TRACKPC) = NO; PUTGRP=0;
  LOOP(TRACKPC(KEEP_FLOF(R,P,C)),
   IF(RPC_FFUNC(R,P,C)+TRACKPG(R,P,C),RPG_1ACE(R,P,CG,C) = NO; ELSE
{include_pp_qaput_1}
    PUT ' WARNING       - ACT_EFF is applied to the auxiliary flow: R.P.C= 'TRACKPC.TE(TRACKPC)));
  TRACKPC(KEEP_FLOF) = NO; PUTGRP=0;
  LOOP(RPC_FFUNC(TRACKPC),
{include_pp_qaput_2}
    PUT ' SEVERE ERROR  - Same process flow definitions in conflict: R.P.C= ',TRACKPC.TE(TRACKPC));
* Complete reduced emission flow & FFUNC indicators
  TRACKPG(RPC_ACE) = NO; TRACKPG(TRACKPC) = NO;
  RPC_EMIS(TRACKPG)=YES; RPCC_FFUNC(TRACKPG(RP,C),C) = YES;
{"OPTION CLEAR=TRACKPC;" if condition else ""}
  OPTION KEEP_FLOF < RPC_FFUNC; TRACKPC(RP_SGS,C) = NO;
  RPC_FFUNC(TRACKPC)$(NOT RPC_ACE(TRACKPC)) = YES;
  OPTION CLEAR=RP_GRP,CLEAR=TRACKPC,CLEAR=TRACKPG;
""",
        )

    def prep_commodity_factors(self: PpmExtVda, pgprim: str) -> None:
        g = self.tc
        # * Prepare commodity-specific availability factors
        project(source=g.ncap_afc, target=g.RpGrp)
        project(source=g.RpGrp, target=g.RpXred)
        g.RpGrp[g.RpPg[g.r, g.p, g.cg]].where[(~(g.c[g.cg] + g.ComType[g.cg]))] = False
        g.prc_sc[g.RpStg[g.RpXred[g.Rp]]] = Sum(
            g.PrcTsl[g.Rp, g.tsl], log(g.g_cycle[g.tsl])
        )
        with Loop(g.tsl[g.stl]):
            g.ncap_afcs[g.r, g.ll, g.p, g.cg, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = (
                sparse(
                    g.ncap_afc[g.r, g.ll, g.p, g.cg, g.stl].where[
                        g.RpGrp[g.r, g.p, g.cg]
                    ]
                )
            )
        g.ncap_afcs[g.r, g.ll, g.p, g.cg, g.s[g.stl]].where[g.RpGrp[g.r, g.p, g.cg]] = (
            sparse(g.ncap_afc[g.r, g.ll, g.p, g.cg, g.stl])
        )
        g.ncap_afc.setRecords(None)
        g.ncap_afcs[g.r, g.ll, g.p, g.cg, g.s].where[(~(g.PrcCap[g.r, g.p]))] = 0.0
        # * Handle independent AFCs
        with Loop(g.RpGrp[g.RpFlo[g.r, g.p], g.cg]):  # noqa: SIM117
            with If(
                Sum(g.Rc[g.r, g.c[g.cg]].where[(~(g.RpcPg[g.r, g.p, g.c]))], 1.0)
                + Number(1.0).where[(~(g.RpPgtype[g.r, g.p, g.cg] + g.c[g.cg]))]
            ):
                g.Trackpg[g.r, g.p, g.cg] = True
        g.Trackpg[g.RpGrp[g.RpStg, pgprim]] = True
        g.ncap_afc[g.r, g.v, g.p, g.cg, g.stl[g.s]].where[g.Trackpg[g.r, g.p, g.cg]] = (
            sparse(g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s])
        )
        g.ncap_afc[g.r, g.v, g.p, g.c, g.stl[g.s]].where[
            (g.Rc[g.r, g.c].where[g.ncap_afcs[g.r, "0", g.p, pgprim, g.s]])
        ] = sparse(g.ncap_afcs[g.r, g.v, g.p, g.c, g.s])
        g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s].where[
            (g.RpStd[g.r, g.p].where[g.Trackpg[g.r, g.p, g.cg]])
        ] = 0.0
        g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s].where[
            (g.ncap_afcs[g.r, "0", g.p, pgprim, g.s].where[g.RpFlo[g.r, g.p]])
        ] = 0.0
        g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s].where[
            ((~(g.RpStg[g.r, g.p])).where[g.RpPgtype[g.r, g.p, g.cg]])
        ] = sparse(g.ncap_afcs[g.r, g.v, g.p, pgprim, g.s])
        # * Set into RTPS_BD tuples to be searched
        project(source=g.ncap_afcs, target=g.Rvps)
        # * Processes with no ACTFLO are not supported:
        g.Rvps[g.r, g.v, g.p, g.s].where[
            ((~(g.Rtp[g.r, g.v, g.p])) | (g.RpStd[g.r, g.p].where[g.RpPgact[g.r, g.p]]))
        ] = False
        # * Set into RTPS_BD availability tuples found
        g.RtpsBd[g.Rvps[g.r, g.v, g.p, g.s], g.Bdupx[g.bd]].where[
            (g.PrcTs[g.r, g.p, g.s] * g.ncap_af[g.r, g.v, g.p, g.s, g.bd])
        ] = True
        g.RtpsBd[g.Rvps[g.r, g.v, g.p, g.s], g.Bdupx[g.bd]].where[
            g.ncap_afs[g.r, g.v, g.p, g.s, g.bd]
        ] = True
        g.RtpsBd[g.Rvps[g.r, g.v, g.p, g.Annual], g.Bdupx[g.bd]].where[
            g.ncap_afa[g.r, g.v, g.p, g.bd]
        ] = True
        # * Clear tuples to be searched according to found ones
        with Loop(g.Bdupx):
            g.Rvps[g.r, g.v, g.p, g.s].where[g.RtpsBd[g.r, g.v, g.p, g.s, g.Bdupx]] = (
                False
            )
        # * Accept remaining tuples of type UP/LO only, and set missing AFS
        g.RtpsBd[g.Rvps, "UP"] = True
        g.ncap_afs[g.Rvps, "UP"] = 1.0
        project(source=g.RtpsBd, target=g.RpsCaflac)
        g.ncap_afc[g.Rtp, g.c, g.stl[g.s]].where[
            (g.ncap_afcs[g.Rtp, g.c, g.s] == 0.0)
        ] = sparse(g.ncap_afcs[g.Rtp, g.c, g.s])
        g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s].where[
            (
                (g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s] <= 0.0).where[
                    g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]
                ]
            )
        ] = (
            1.0
            + Number(SpecialValues.POSINF).where[((g.RpStd[g.r, g.p]) | (~(g.c[g.cg])))]
        )
        # * Prepare IRE/STG with both sides
        g.RpgAfcx[g.RpcIre[g.Rp, g.c, g.ie["EXP"]]].where[
            (g.RpcIre[g.Rp, g.c, "IMP"] + (~(g.RpAire[g.Rp, g.ie])))
        ] = True
        g.RpgAfcx[g.RpcStg, g.ie[g.xpt]] = sparse(g.Top[g.RpcStg, "OUT"])
        # * Enable flexible STS only where AF on activity
        g.Trackp[g.RpSts[g.Rp]] = sparse(
            Sum(g.RpsCaflac[g.RpsStg[g.Rp, g.s], g.bd], 1.0)
        )
        project(source=g.ncap_afc, target=g.RpGrp)
        g.RpStl[g.PrcCap[g.RpSts[g.Rp]], g.tsl, "UP"].where[
            ((~(g.Trackp[g.Rp])) | (g.RpGrp[g.Rp, pgprim]))
        ] = sparse(g.RpStl[g.Rp, g.tsl, "N"])
        g.Trackp.setRecords(None)
        g.RpGrp.setRecords(None)
        g.Trackpg.setRecords(None)
        g.Rvps.setRecords(None)
        g.RtpsBd.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * Automatic generation of NCAP_AFC for ECT CHP
        g.Rvp[g.Rtp[g.r, g.v, g.p]].where[
            (
                (~(g.RpsCaflac[g.r, g.p, "ANNUAL", "UP"])).where[
                    (g.ncap_chpr[g.Rtp, "UP"] * g.ncap_afa[g.Rtp, "UP"] > 0.0)
                    & g.Chp[g.r, g.p]
                ]
            )
        ] = True
        g.Rvp[g.Rtp].where[(g.ncap_ceh[g.Rtp] < 1.5)] = False
        # * The maximum of the technical AF for ELC, corrected with ACTFLO:
        g.vda_ceh[g.Rvp[g.r, g.v, g.p]] = Max(
            0.0,
            Smax(
                [g.PrcTs[g.r, g.p, g.s], g.ChpElc[g.r, g.p, g.c]],
                g.ncap_af[g.Rvp, g.s, "UP"] * g.prc_actflo[g.Rvp, g.c],
            ),
        )
        g.Rvp[g.Rtp].where[(g.vda_ceh[g.Rtp] <= 0.0)] = False
        g.RpsCaflac[g.r, g.p, g.Annual, "UP"] = sparse(
            Sum(g.Rvp[g.r, g.v, g.p].where[g.vda_ceh[g.Rvp]], 1.0)
        )
        # * AFAC for heat = (heat share)/(1/AFA-(elec share)/AF):
        g.ncap_afcs[g.Rvp[g.r, g.v, g.p], g.c, g.Annual].where[
            g.RpcPg[g.r, g.p, g.c]
        ] = (
            (1.0 / (1.0 + 1.0 / g.ncap_chpr[g.Rvp, "UP"]))
            / g.ncap_afa[g.Rvp, "UP"]
            / g.prc_actflo[g.Rvp, g.c]
            / (
                1.0 / g.ncap_afa[g.Rvp, "UP"]
                - (1.0 - 1.0 / (1.0 + 1.0 / g.ncap_chpr[g.Rvp, "UP"]))
                / g.vda_ceh[g.Rvp]
            )
        )
        g.ncap_afcs[g.Rvp[g.r, g.v, g.p], g.c, g.Annual].where[
            g.ChpElc[g.r, g.p, g.c]
        ] = g.vda_ceh[g.Rvp] / g.ncap_afa[g.Rvp, "UP"] / g.prc_actflo[g.Rvp, g.c]
        g.Rvp.setRecords(None)
        aggregate(source=g.ncap_ceh, target=g.vda_ceh)
        # *-----------------------------------------------------------------------------
        # * Have NCAP_AFSX / NCAP_AFSM by control option
        g.Fil[g.ll] = g.v[g.ll] + g.Lastll[g.ll]
        g.prc_ymin[g.r, g.p].where[g.ncap_afx[g.r, "0", g.p]] = floor(
            g.ncap_afx[g.r, "0", g.p] / 1000.0
        )
        g.ncap_afsx[g.r, g.Fil[g.ll], g.p, g.bd].where[
            (
                (g.ncap_afsx[g.r, g.ll, g.p, g.bd] == 0.0).where[
                    (
                        (mod(g.prc_ymin[g.r, g.p], 2.0) * 2.0 - 1.0)
                        * (1.0 - Number(2.0).where[g.Bdupx[g.bd]])
                        < 0.0
                    )
                    & mod(g.prc_ymin[g.r, g.p], 7.0 - Number(4.0).where[g.v[g.ll]])
                ]
            )
        ] = sparse(g.ncap_afx[g.r, g.ll, g.p])
        g.rp_afb[g.r, g.p, g.bd].where[
            (
                (
                    mod(
                        g.prc_ymin[g.r, g.p].where[
                            (
                                (mod(g.prc_ymin[g.r, g.p], 2.0) * 2.0 - 1.0)
                                * (1.0 - Number(2.0).where[g.Bdupx[g.bd]])
                                < 0.0
                            )
                        ],
                        5.0,
                    )
                    == 0.0
                ).where[g.prc_ymin[g.r, g.p]]
            )
        ] = -1.0
        g.ncap_afsm[g.r, g.Fil[g.ll], g.p].where[
            mod(
                floor(g.ncap_afm[g.r, g.ll, g.p] / 1000.0),
                7.0 - Number(4.0).where[g.v[g.ll]],
            )
        ] = sparse(g.ncap_afm[g.r, g.ll, g.p])
        g.ncap_afm[g.Rtp[g.r, g.v, g.p]].where[
            (
                (
                    mod(
                        Max(1.0, floor(g.ncap_afm[g.r, "0", g.p] / 1000.0)),
                        5.0,
                    )
                    == 0.0
                ).where[g.ncap_afm[g.Rtp]]
            )
        ] = 0.0
