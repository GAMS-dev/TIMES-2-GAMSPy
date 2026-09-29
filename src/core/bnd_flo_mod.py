# bnd_flo_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_FLO.MOD set the actual bounds for non-vintage VAR_FLOs                  *
# =============================================================================*
# UR Questions/Comments:
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, SpecialValues, sparse
from gamspy.math import Max, Min

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndFloMod(GamsClass):
    """Translation unit for bnd_flo.mod."""

    # Instance attributes
    module_name: str = "bnd_flo"
    gams_source: str = "bnd_flo.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_bnd_flo_mod,
            stages=self.env.stages,
            var=self.env.var,
            swd=self.env.swd_GP,
            reduce=self.env.reduce,
            dflbl=self.env.dflbl,
            swt=self.env.swt_GP,
        )

    def exec_bnd_flo_mod(
        self: BndFloMod,
        stages: str,
        reduce: str,
        var: str,
        swd: tuple[Set | Alias] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        dflbl: str,
    ) -> None:
        bnd_flo_mod_GP(
            g=self.tc,
            stages=stages,
            reduce=reduce,
            var=var,
            swd=swd,
            swt=swt,
            dflbl=dflbl,
        )


def bnd_flo_mod_GP(
    *,
    g: TimesModelClass,
    stages: str,
    reduce: str,
    var: str,
    swd: tuple[Set | Alias] | tuple[()],
    swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    dflbl: str,
) -> None:
    VAR_FLO, RtpVintyr, r, t, p, c, s, RtpcsVarf, Trackpc, flo_bnd = (
        g.get_variable(f"{var}_FLO"),
        g.RtpVintyr,
        g.r,
        g.t,
        g.p,
        g.c,
        g.s,
        g.RtpcsVarf,
        g.Trackpc,
        g.flo_bnd,
    )

    def bound_assign() -> None:
        VAR_FLO.lo[RtpVintyr[r, t, t, p], c, s, *swd].where[
            RtpcsVarf[r, t, p, c, s] * Trackpc[r, p, c]
        ] = sparse(flo_bnd[r, t, p, c, s, "LO"])
        VAR_FLO.up[RtpVintyr[r, t, t, p], c, s, *swd].where[
            RtpcsVarf[r, t, p, c, s] * Trackpc[r, p, c]
        ] = sparse(flo_bnd[r, t, p, c, s, "UP"])
        VAR_FLO.fx[RtpVintyr[r, t, t, p], c, s, *swd].where[
            RtpcsVarf[r, t, p, c, s] * Trackpc[r, p, c]
        ] = sparse(flo_bnd[r, t, p, c, s, "FX"])

    (v, RpcEmis, RpFlo, Rtpc, bd, PrcVint, RpcFfunc, cg, RpcAct, SwT) = (
        g.v,
        g.RpcEmis,
        g.RpFlo,
        g.Rtpc,
        g.bd,
        g.PrcVint,
        g.RpcFfunc,
        g.cg,
        g.RpcAct,
        g.SwT,
    )
    # reset any existing bounds
    VAR_FLO.lo[r, v, t, p, c, s, *swd] = 0
    VAR_FLO.up[r, v, t, p, c, s, *swd] = SpecialValues.POSINF
    # assign from user data
    flo_bnd[r, t, p, c, s, "LO"].where[
        (~RpcEmis[r, p, c]).where[
            (flo_bnd[r, t, p, c, s, "LO"] == 0).where[RpFlo[r, p]]
        ]
    ] = 0
    with Loop(Domain(Rtpc[r, t, p, c], s, bd).where[flo_bnd[Rtpc, s, bd]]):
        Trackpc[RpFlo[r, p], c] = True
    Trackpc[PrcVint[r, p], c] = False
    Trackpc[RpcFfunc[r, p, c]] = False
    Trackpc[RpcEmis[r, p, c]] = False
    # Mark all tuples that definitely cannot be handled by VAR bounds
    with Loop(t):
        flo_bnd[r, dflbl, p, c, s, bd].where[flo_bnd[r, t, p, c, s, bd]] = Number(
            SpecialValues.EPS
        ).where[~Trackpc[r, p, c]]
        flo_bnd[r, dflbl, p, cg, s, bd].where[
            (~c[cg]).where[flo_bnd[r, t, p, cg, s, bd]]
        ] = SpecialValues.EPS

    Trackpc[RpcAct[r, p, c]] = False

    if stages == "YES":
        with Loop(SwT[t, *swd]):
            bound_assign()
    else:
        bound_assign()

    Trackpc.setRecords(None)

    if reduce == "YES":
        VAR_ACT, prc_actflo = g.get_variable(f"{var}_ACT"), g.prc_actflo
        # $IF %STAGES%==YES $SETLOCAL SWT "%SWD%)$SW_T(T%SWD%" -- bnd_flo.mod's
        # own local SWT redefinition, only reached once REDUCE==YES (the $EXIT
        # above); it splices %SWD% into the domain and gates on SwT[t, *swd]
        # instead of spreading the outer swt into the domain directly.
        restrict = stages == "YES"

        # As BND_ACT has been set before this, MAX/MIN can be used; FX bound consistency cannot be guaranteed
        with Loop(
            RtpcsVarf[r, t, p, c, s].where[
                (~PrcVint[r, p] * RpcAct[r, p, c]) & flo_bnd[r, t, p, c, s, "LO"]
            ]
        ):
            if restrict:
                VAR_ACT.lo[r, t, t, p, s, *swd].where[SwT[t, *swd]] = Max(
                    VAR_ACT.lo[r, t, t, p, s, *swd].where[SwT[t, *swd]],
                    flo_bnd[r, t, p, c, s, "LO"] / prc_actflo[r, t, p, c],
                )
            else:
                VAR_ACT.lo[r, t, t, p, s, *swt] = Max(
                    VAR_ACT.lo[r, t, t, p, s, *swt],
                    flo_bnd[r, t, p, c, s, "LO"] / prc_actflo[r, t, p, c],
                )
        with Loop(
            RtpcsVarf[r, t, p, c, s].where[
                (~PrcVint[r, p] * RpcAct[r, p, c]) & flo_bnd[r, t, p, c, s, "UP"]
            ]
        ):
            if restrict:
                VAR_ACT.up[r, t, t, p, s, *swd].where[SwT[t, *swd]] = Min(
                    VAR_ACT.up[r, t, t, p, s, *swd].where[SwT[t, *swd]],
                    flo_bnd[r, t, p, c, s, "UP"] / prc_actflo[r, t, p, c],
                )
            else:
                VAR_ACT.up[r, t, t, p, s, *swt] = Min(
                    VAR_ACT.up[r, t, t, p, s, *swt],
                    flo_bnd[r, t, p, c, s, "UP"] / prc_actflo[r, t, p, c],
                )
        with Loop(
            RtpcsVarf[r, t, p, c, s].where[
                (~PrcVint[r, p] * RpcAct[r, p, c]) & flo_bnd[r, t, p, c, s, "FX"]
            ]
        ):
            if restrict:
                VAR_ACT.fx[r, t, t, p, s, *swd].where[SwT[t, *swd]] = (
                    flo_bnd[r, t, p, c, s, "FX"] / prc_actflo[r, t, p, c]
                )
            else:
                VAR_ACT.fx[r, t, t, p, s, *swt] = (
                    flo_bnd[r, t, p, c, s, "FX"] / prc_actflo[r, t, p, c]
                )
