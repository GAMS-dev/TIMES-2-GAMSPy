# pp_lvlfs_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (c) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLFS set the level of flo_sum attribute using aggregation/inheritance
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Assumption is that values can be at any level
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, For, Loop, Set, Sum, sparse
from gamspy.math import project, same_as

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlfsMod(GamsClass):
    """Translation unit for pp_lvlfs.mod."""

    # Instance attributes
    module_name: str = "pp_lvlfs_mod"
    gams_source: str = "pp_lvlfs.mod"

    def __init__(
        self: PpLvlfsMod,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        g.Fstsl = Set(m, "FSTSL", domain=[g.tslvl, g.r, g.p, g.cg, g.cg, g.cg, g.s])
        self.tc.enqueue(self.pp_lvlfs_exec)

    def pp_lvlfs_exec(self: PpLvlfsMod) -> None:
        g = self.tc
        (
            coef_ptran,
            r,
            v,
            z,
            ll,
            p,
            cg,
            c,
            comgrp,
            s,
            RpcsVar,
            flo_sum,
            Fscks,
            Fsck,
            RpsPrcts,
            Annual,
            ts,
            tslvl,
            Fstsl,
            stoal,
            Rtp,
            allts,
            ts_array,
            Finest,
            RsTree,
            RsBelow,
            TsMap,
            sl,
            g_yrfr,
        ) = (
            g.coef_ptran,
            g.r,
            g.v,
            g.z,
            g.ll,
            g.p,
            g.cg,
            g.c,
            g.comgrp,
            g.s,
            g.RpcsVar,
            g.flo_sum,
            g.Fscks,
            g.Fsck,
            g.RpsPrcts,
            g.Annual,
            g.ts,
            g.tslvl,
            g.Fstsl,
            g.stoal,
            g.Rtp,
            g.allts,
            g.ts_array,
            g.Finest,
            g.RsTree,
            g.RsBelow,
            g.TsMap,
            g.sl,
            g.g_yrfr,
        )

        # check all commodities in the groups of a process at other than PRC_TS level
        coef_ptran[r, ll, p, cg, c, comgrp, s] = sparse(
            flo_sum[r, ll, p, cg, c, comgrp, s].where[~RpcsVar[r, p, c, s]]
        )

        project(source=coef_ptran, target=Fscks, direction="left")

        Fsck[r, p, cg, c, comgrp] = sparse(
            Sum(Fscks[r, p, cg, c, comgrp, s].where[~RpsPrcts[r, p, s]], 1)
        )

        with Loop(Annual[ts[tslvl]]):
            Fstsl[tslvl + stoal[r, s], Fscks[r, p, cg, c, comgrp, s]] = True

        # *-----------------------------------------------------------------------------
        # * Leveling by simultaneous aggregation/inheritance
        # *-----------------------------------------------------------------------------
        with Loop((Fsck[r, p, cg, c, comgrp], Rtp[r, v, p])):  # type: ignore[arg-type]
            ts_array[allts] = flo_sum[r, v, p, cg, c, comgrp, allts]
            flo_sum[r, v, p, cg, c, comgrp, ts].where[RpcsVar[r, p, c, ts]] = (
                Sum(
                    RsTree[Finest[r, s], ts],
                    g_yrfr[r, s]
                    * (
                        ts_array[s]
                        + Sum(
                            RsBelow[r, allts, s].where[
                                (
                                    ~Sum(
                                        TsMap[r, sl, s].where[RsBelow[r, allts, sl]],
                                        ts_array[sl],
                                    )
                                ).where[ts_array[allts]]
                            ],
                            ts_array[allts],
                        )
                    ),
                )
                / g_yrfr[r, ts]
            )

        # *-----------------------------------------------------------------------------
        # * Leveling by direct inheritance
        # *-----------------------------------------------------------------------------
        flo_sum[r, ll, p, cg, c, comgrp, s].where[
            coef_ptran[r, ll, p, cg, c, comgrp, s]
        ] = 0
        flo_sum[r, ll, p, cg, c, comgrp, s].where[~Rtp[r, ll, p]] = 0

        with For(z, Card(tslvl) - 2, 0, direction="downto"):  # type: ignore # noqa: SIM117
            with Loop(same_as(tslvl - z, "Annual")):
                flo_sum[Rtp[r, v, p], cg, c, comgrp, ts].where[
                    (~flo_sum[r, v, p, cg, c, comgrp, ts]) & g.RpcsVar[r, p, c, ts]
                ] = sparse(
                    Sum(
                        Fstsl[tslvl, r, p, cg, c, comgrp, s].where[RsBelow[r, s, ts]],
                        coef_ptran[r, v, p, cg, c, comgrp, s],
                    )
                )

        coef_ptran.setRecords(None)
        Fsck.setRecords(None)
        Fscks.setRecords(None)
        Fstsl.setRecords(None)
        flo_sum[r, ll, p, cg, c, cg, s].where[Fscks[r, p, cg, c, cg, s]] = 0
