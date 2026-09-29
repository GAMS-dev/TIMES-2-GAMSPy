# prep_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.abs oversees all the added interpolation activities needed by ABS
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, Ord, sparse
from gamspy.math import Round, aggregate, project

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtAbs(GamsClass):
    """Translation unit for prep_ext.abs."""

    # Instance attributes
    module_name: str = "prep_ext_abs"
    gams_source: str = "prep_ext.abs"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",  # NOTE: This is required upstream
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        self.tc.enqueue(self.add_reserve_commodities)
        # fmt: off
        batincludes: list[FillparmGmsConfig] = [
            FillparmGmsConfig(arg1=g.bs_lambda, arg2=(g.r,),      arg3=(g.c,),              arg4=("0",) * 5, arg5=g.t, arg6=Number(1),            arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_detwt,  arg2=(g.r,),      arg3=(g.c,),              arg4=("0",) * 5, arg5=g.t, arg6=Number(1),            arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_sigma,  arg2=(g.r,),      arg3=(g.c,g.BsK,g.s),     arg4=("0",) * 3, arg5=g.t, arg6=Number(1),            arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_share,  arg2=(g.r,),      arg3=(g.c,g.BsK,g.bd),    arg4=("0",) * 3, arg5=g.t, arg6=Number(1),            arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_rtcs,   arg2=(g.Rsp,g.r), arg3=(g.c,g.s),           arg4=("0",) * 3, arg5=g.t, arg6=Number(1),            arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_maint,  arg2=(g.r,),      arg3=(g.p,g.s),           arg4=("0",) * 4, arg5=g.v, arg6=g.Rtp[g.r, g.v, g.p], arg7=Number(0)),
            FillparmGmsConfig(arg1=g.bs_rmax,   arg2=(g.r,),      arg3=(g.p,g.c,g.s),       arg4=("0",) * 3, arg5=g.v, arg6=g.Rtp[g.r, g.v, g.p], arg7=Number(0)),
        ]
        # fmt: on
        for config in batincludes:
            self.include(FillparmGms(self.tc, self.env, config))

        self.include(
            PrepparmGms(
                self.tc,
                self.env,
                PrepparmGmsConfig(
                    arg1="BS_BNDPRS",
                    arg2=(g.r,),
                    arg3=(g.p, g.c, g.s, g.bd),
                    arg4=("0",) * 1,
                    arg5=g.t,
                    arg6=g.Rtp[g.r, g.t, g.p],
                    arg7=1,
                ),
            )
        )
        self.tc.enqueue(self.intermediate_qa_clean_up)

    def add_reserve_commodities(self: PrepExtAbs) -> None:
        g = self.tc
        # * Add reserve commodities to RC
        g.Rc[g.r, g.c] = sparse(g.bs_rtype[g.r, g.c])
        with Loop(Domain(g.Rp, g.item).where[g.gr_genmap[g.Rp, g.item]]):
            g.BsK[g.item] = True
        with Loop(
            Domain(g.r, g.t, g.c, g.p, g.bd).where[g.bs_share[g.r, g.t, g.c, g.p, g.bd]]
        ):
            g.BsK[g.p] = True

        # * Bulk processing
        aggregate(source=g.bs_demdet, target=g.bs_rtcs)
        g.bs_rtcs["OMEGA", g.r, g.year, g.c, g.s] = sparse(
            g.bs_omega[g.r, g.year, g.c, g.s]
        )
        g.bs_rtcs["DELTA", g.r, g.year, g.c, g.s] = sparse(
            g.bs_delta[g.r, g.year, g.c, g.s]
        )

    def intermediate_qa_clean_up(self: PrepExtAbs) -> None:
        g = self.tc
        # * Intermediate QA clean-up
        g.bs_rtcs[g.Rsp["OMEGA"], g.r, g.t, g.c, g.s].where[
            g.bs_rtcs[g.Rsp, g.r, g.t, g.c, g.s]
        ] = Round(g.bs_rtcs[g.Rsp, g.r, g.t, g.c, g.s])
        g.bs_sigma[g.r, g.t, g.c, g.BsK, g.s].where[g.bs_lambda[g.r, g.t, g.c] == 0] = 0
        g.bs_rmax[g.r, g.ll.lag(Ord(g.ll), "circular"), g.p, g.c, g.s + g.stoa[g.s]] = (
            sparse(g.bs_rmax[g.r, g.ll, g.p, g.c, g.s] > 0)
        )
        g.bs_rmax[g.r, g.ll, g.p, g.c, g.s].where[
            ~g.bs_rmax[g.r, "0", g.p, g.c, "ANNUAL"]
        ] = 0
        g.bs_bndprs[g.r, g.t, g.p, g.c, g.s, g.bd].where[
            (g.bs_lambda[g.r, g.t, g.c] == 0)
            & g.bs_bndprs[g.r, g.t, g.p, g.c, g.s, g.bd]
        ] = 0
        project(source=g.bs_rmax, target=g.BsBsc)
        g.bs_omega.setRecords(None)
