# bnd_ire_vda.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_STG.MOD set the actual bounds for non-vintage VAR_SIN/OUT
#    %1 - which variable
#    %2 - which bound
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, Loop, Parameter, SpecialValues, Sum

from core.base_class import GamsClass
from core.fillcost_gms import FillcostGms, FillcostGmsConfig

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndIreVda(GamsClass):
    """Translation unit for bnd_ire.vda."""

    # Instance attributes
    module_name: str = "bnd_ire"
    gams_source: str = "bnd_ire.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        if not self.tc.defined(g.Premile):
            return

        self.tc.enqueue(self.exec1)

        g.flo_ire = Parameter(
            m, name="FLO_IRE", domain=[g.r, g.ll, g.p, g.c, g.s, g.ie]
        )

        self.tc.enqueue(self.exec2, var=self.env.var, swd=self.env.swd_GP)

        # fmt: off
        batincludes = [
            FillcostGmsConfig(arg1=g.flo_ire, arg2=g.r, arg3=(g.p,g.c,g.ts,g.ie), arg4=('0',), arg5=g.Fil, arg6=Card(g.Fil), bext=1, fext=1, arg9=g.flo_ire, arg10="X_IREFLO"),
            FillcostGmsConfig(arg1=g.par_ipric, arg2=g.r, arg3=(g.p,g.c,g.ts,g.ie), arg4=('0',), arg5=g.Fil, arg6=Card(g.Fil), bext=1, fext=1, arg9=g.par_ipric, arg10="X_IREFLO")
        ]
        # fmt: on

        for config in batincludes:
            self.include(FillcostGms(tc=self.tc, env=self.env, config=config))

        self.tc.enqueue(self.exec3, var=self.env.var, swd=self.env.swd_GP)

    def exec1(self: BndIreVda) -> None:
        g = self.tc
        r, v, t, p, c, ts, ie = g.r, g.v, g.t, g.p, g.c, g.ts, g.ie
        RpcIrein = g.RpcIrein

        RpcIrein[g.RpcIreio] = False
        g.par_ire[r, v, t, p, c, ts, ie].where[~RpcIrein[r, p, c, ie, "IN"]] = 0
        g.par_ipric[r, t, p, c, ts, ie].where[~RpcIrein[r, p, c, ie, "IN"]] = 0

    def exec2(self: BndIreVda, var: str, swd: tuple[Set | Alias] | tuple[()]) -> None:
        g = self.tc
        r, v, t, tt, p, c, ts, ie, ll = (
            g.r,
            g.v,
            g.t,
            g.tt,
            g.p,
            g.c,
            g.ts,
            g.ie,
            g.ll,
        )
        RpcIrein, RpcAire, RpcsVar, Premile = (
            g.RpcIrein,
            g.RpcAire,
            g.RpcsVar,
            g.Premile,
        )
        par_ire, flo_bnd, flo_ire = g.par_ire, g.flo_bnd, g.flo_ire
        VAR_IRE = g.get_variable(f"{var}_IRE")

        # IF(CARD(PAR_IRE), ...) -- a top-level GAMS IF becomes a Python if, since
        # gp.If only works inside a gp.Loop.
        if par_ire.number_records:
            VAR_IRE.fx[g.RtpVintyr[r, v, Premile[t], p], c, ts, ie, *swd].where[
                ((~RpcAire[r, p, c]) * RpcsVar[r, p, c, ts]).where[
                    RpcIrein[r, p, c, ie, "IN"]
                ]
            ] = SpecialValues.EPS + par_ire[r, v, t, p, c, ts, ie]
            with Loop(ie):
                flo_bnd[r, Premile[t], p, c, ts, "FX"].where[
                    (RpcAire[r, p, c] * g.RtpcsVarf[r, t, p, c, ts]).where[
                        RpcIrein[r, p, c, ie, "IN"]
                    ]
                ] = SpecialValues.EPS + Sum(
                    g.RtpVintyr[r, v, t, p], par_ire[r, v, t, p, c, ts, ie]
                )

        # Set target milestone years into FIL
        g.Fil.setRecords(None)
        with Loop(t.where[~Premile[t]]):
            g.Fil[tt].where[g.Yk[tt, t]] = True

        # Calculate total flows at milestone years
        flo_ire[r, Premile, p, c, ts, ie].where[
            RpcsVar[r, p, c, ts].where[RpcIrein[r, p, c, ie, "IN"]]
        ] = (
            Sum(
                g.Yk[Premile, ll].where[par_ire[r, ll, Premile, p, c, ts, ie]],
                par_ire[r, ll, Premile, p, c, ts, ie],
            )
            + SpecialValues.EPS
        )
        g.DmYear[Premile] = True

    def exec3(self: BndIreVda, var: str, swd: tuple[Set | Alias] | tuple[()]) -> None:
        g = self.tc
        r, t, p, c, ts, ie = g.r, g.t, g.p, g.c, g.ts, g.ie
        RpcIrein, RpcAire, RpcsVar, Trackpc = (
            g.RpcIrein,
            g.RpcAire,
            g.RpcsVar,
            g.Trackpc,
        )
        Fil, flo_ire, flo_bnd = g.Fil, g.flo_ire, g.flo_bnd
        VAR_IRE = g.get_variable(f"{var}_IRE")

        # Set bounds for T not in sync with PREMILE
        with Loop(ie.where[Card(Fil)]):  # type: ignore[index]
            Trackpc[r, p, c].where[
                (RpcAire[r, p, c] + g.PrcVint[r, p]).where[RpcIrein[r, p, c, ie, "IN"]]
            ] = True
        VAR_IRE.fx[g.RtpVintyr[r, Fil[t], t, p], c, ts, ie, *swd].where[
            ((~Trackpc[r, p, c]) * RpcsVar[r, p, c, ts]).where[
                RpcIrein[r, p, c, ie, "IN"]
            ]
        ] = SpecialValues.EPS + flo_ire[r, t, p, c, ts, ie]

        # Remove TRACKPC with either IMP or EXP internal, as FLO_BND will be applied
        # to the SUM
        with Loop(ie):
            Trackpc[r, p, c].where[
                (~RpcIrein[r, p, c, ie, "IN"]).where[g.RpcIre[r, p, c, ie]]
            ] = False
        flo_bnd[r, Fil[t], p, c, ts, "FX"].where[
            (RpcAire[r, p, c] * g.RtpcsVarf[r, t, p, c, ts]).where[Trackpc[r, p, c]]
        ] = SpecialValues.EPS + Sum(
            RpcIrein[r, p, c, ie, "IN"], flo_ire[r, t, p, c, ts, ie]
        )
        Trackpc.setRecords(None)
        flo_ire.setRecords(None)

        # Set the IRE prices
        with Loop(t.where[Card(g.par_ipric)]):  # type: ignore[index]
            g.obj_ipric[r, g.YEoh, p, c, ts, ie, g.cur].where[
                g.Periodyr[t, g.YEoh].where[
                    RpcsVar[r, p, c, ts].where[RpcIrein[r, p, c, ie, "IN"]]
                ]
            ] = g.par_ipric[r, t, p, c, ts, ie]
