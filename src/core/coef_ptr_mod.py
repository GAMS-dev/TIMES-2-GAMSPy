# coef_ptr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_PTR is the coef and control with regard to which VAR_FLOs to create    *
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------*
# * hold on to the most granular specification for the p/c/s dealing with

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, Set, Sum, sparse
from gamspy.math import project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefPtrMod(GamsClass):
    """Translation unit for coef_ptr.mod."""

    # Instance attributes
    module_name: str = "coef_ptr_mod"
    gams_source: str = "coef_ptr.mod"

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
        self.build_test_set()

        self.tc.enqueue(self.exec1)

    def build_test_set(self: CoefPtrMod) -> None:
        g = self.tc
        m = g.container

        Reg, allyear, prc, cg, c = g.Reg, g.allyear, g.prc, g.cg, g.c

        # build intermediate test sets
        g.Cgtest = Set(m, name="CGTEST", domain=[Reg, allyear, prc, cg, c, cg])
        g.Cgtes2 = Set(m, name="CGTES2", domain=[Reg, allyear, prc, cg, c, cg])

    def exec1(self: CoefPtrMod) -> None:
        g = self.tc
        (
            flo_sum,
            Cgtest,
            r,
            v,
            p,
            comgrp,
            c,
            cg,
            Rpc,
            s,
            flo_func,
            CgGrp,
            Cgtes2,
            Rtp,
            ComGmap,
            Com,
            coef_ptran,
            RpcsVar,
            PrcTsl,
            tsl,
            TsGroup,
            ts,
            TsMap,
            cg2,
            KeepFlof,
            RpcAflo,
            act_flo,
            RpcgPtran,
            RpcAct,
            cg4,
            PrcTs,
            prc_actflo,
            RpccFfunc,
            RpGrp,
            PrcCg,
            Rc,
        ) = (
            g.flo_sum,
            g.Cgtest,
            g.r,
            g.v,
            g.p,
            g.comgrp,
            g.c,
            g.cg,
            g.Rpc,
            g.s,
            g.flo_func,
            g.CgGrp,
            g.Cgtes2,
            g.Rtp,
            g.ComGmap,
            g.Com,
            g.coef_ptran,
            g.RpcsVar,
            g.PrcTsl,
            g.tsl,
            g.TsGroup,
            g.ts,
            g.TsMap,
            g.cg2,
            g.KeepFlof,
            g.RpcAflo,
            g.act_flo,
            g.RpcgPtran,
            g.RpcAct,
            g.cg4,
            g.PrcTs,
            g.prc_actflo,
            g.RpccFfunc,
            g.RpGrp,
            g.PrcCg,
            g.Rc,
        )

        # Add FLO_SUM tuples; Accept any RPC for the single commodity
        project(source=flo_sum, target=Cgtest, direction="left")
        Cgtest[r, v, p, comgrp, c, cg].where[~Rpc[r, p, c]] = False

        # Add reverse FLO_FUNCs for matching FLO_SUM (cg2=cg1)
        with Loop(
            Domain(Cgtest[r, v, p, comgrp, c, cg], s).where[
                flo_func[r, v, p, cg, comgrp, s]
            ]
        ):
            CgGrp[r, p, comgrp, cg] = True

        Cgtes2[Rtp[r, v, p], comgrp, c, cg].where[
            (ComGmap[r, comgrp, c] * Rpc[r, p, c]).where[CgGrp[r, p, comgrp, cg]]
        ] = True

        # Add forward FLO_FUNCs including all RPC in CG1
        project(source=flo_func, target=CgGrp, direction="left")
        Cgtes2[Rtp[r, v, p], comgrp, c, cg].where[
            ComGmap[r, comgrp, c].where[Rpc[r, p, c].where[CgGrp[r, p, comgrp, cg]]]
        ] = sparse(Sum(s.where[flo_func[Rtp, comgrp, cg, s]], 1))
        Cgtes2[Cgtest[Rtp, c, Com, cg]] = sparse(Cgtes2[Rtp, c, c, cg])
        project(source=Cgtest, target=CgGrp, direction="left")
        coef_ptran[Cgtes2[r, v, p, comgrp, c, cg], s].where[
            (Number(1).where[flo_sum[Cgtes2, s]] + (~CgGrp[r, p, cg, comgrp])).where[
                RpcsVar[r, p, c, s]
            ]
        ] = Sum(
            Domain(PrcTsl[r, p, tsl], TsGroup[r, tsl, ts]).where[TsMap[r, ts, s]],
            (
                (
                    1
                    + (1 / flo_func[r, v, p, cg, comgrp, ts] - 1).where[
                        flo_func[r, v, p, cg, comgrp, ts]
                    ]
                ).where[~flo_func[r, v, p, comgrp, cg, ts]]
                + flo_func[r, v, p, comgrp, cg, ts]
            )
            * ((Number(1)).where[~flo_sum[Cgtes2, s]] + flo_sum[Cgtes2, s]),
        )
        coef_ptran[Cgtest[r, v, p, cg, c, cg2], s].where[
            (~Cgtes2[Cgtest]).where[RpcsVar[r, p, c, s]]
        ] = sparse(flo_sum[Cgtest, s])
        KeepFlof[RpcAflo[r, p, c]] = False
        act_flo[Rtp[r, v, p], c, s].where[RpcsVar[r, p, c, s] & KeepFlof[r, p, c]] = (
            Sum(
                Domain(RpcgPtran[RpcAct[r, p, Com], c, cg, cg4], PrcTs[r, p, ts]).where[
                    TsMap[r, ts, s]
                ],
                prc_actflo[Rtp, Com] * coef_ptran[Rtp, cg, Com, cg4, ts],
            )
            + Sum(
                RpcgPtran[r, p, c, Com, cg, cg4].where[coef_ptran[Rtp, cg, c, cg4, s]],
                prc_actflo[Rtp, Com] / coef_ptran[Rtp, cg, c, cg4, s],
            )
        )
        Cgtest[Cgtes2] = True
        coef_ptran[Cgtest[r, v, p, cg, c, Com], s].where[
            RpcgPtran[r, p, c, Com, cg, Com]
        ] = 0
        project(source=Cgtest, target=CgGrp, direction="left")
        CgGrp[RpccFfunc] = False
        project(source=CgGrp, target=RpccFfunc, direction="left")
        project(source=CgGrp, target=RpGrp, direction="left")
        PrcCg[RpGrp] = True
        project(source=CgGrp, target=RpGrp)
        PrcCg[RpGrp] = True
        RpccFfunc[r, p, cg, c].where[Rc[r, c] & ~Rpc[r, p, c]] = False
        CgGrp.setRecords(None)
        RpGrp.setRecords(None)
        Cgtest.setRecords(None)
        Cgtes2.setRecords(None)
