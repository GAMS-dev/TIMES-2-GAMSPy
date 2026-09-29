# pp_lvlff_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLFF set the level of FLO_FUNC attribute using aggregation/inheritance
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# * - Assumption is that values can be given at any levels
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gamspy.math as gmath
from gamspy import Domain, Loop, Set, Sum, sparse

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlffMod(GamsClass):  # FilenameExt
    """Translation unit for pp_lvlff.mod."""

    # Instance attributes
    module_name: str = "pp_lvlff_mod"
    gams_source: str = "pp_lvlff.mod"

    def __init__(
        self: PpLvlffMod,
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
        g.Ffcks = Set(m, name="FFCKS", domain=[g.Reg, g.prc, g.cg, g.cg, g.ts])

        self.tc.enqueue(self.pp_lvlff_exec)

    def pp_lvlff_exec(self: PpLvlffMod) -> None:
        g = self.tc
        r, p, cg, cg2, s, comgrp, stoa, v, allts, ts, sl = (
            g.r,
            g.p,
            g.cg,
            g.cg2,
            g.s,
            g.comgrp,
            g.stoa,
            g.v,
            g.allts,
            g.ts,
            g.sl,
        )
        Ffcks, CgGrp, PrcTs, Actcg, Annual = (
            g.Ffcks,
            g.CgGrp,
            g.PrcTs,
            g.Actcg,
            g.Annual,
        )
        flo_func, ts_array = g.flo_func, g.ts_array

        # * check all commodities in the groups of a process at other than PRC_TS level
        gmath.project(source=flo_func, target=Ffcks, direction="left")
        Ffcks[r, p, cg, cg2, s].where[(PrcTs[r, p, s] + Actcg[cg])] = False
        with Loop(
            Domain(r, p, cg, comgrp, s).where[Ffcks[r, p, cg, comgrp, s] & stoa[s] != 0]
        ):
            CgGrp[r, p, cg, comgrp] = True

        # *-----------------------------------------------------------------------------
        # * Leveling by simultaneous aggregation/inheritance
        # *-----------------------------------------------------------------------------
        with Loop(
            Domain(r, p, cg, comgrp, v).where[CgGrp[r, p, cg, comgrp] & g.Rtp[r, v, p]]
        ):
            ts_array[allts] = flo_func[r, v, p, cg, comgrp, allts]
            flo_func[r, v, p, cg, comgrp, ts].where[
                (~(ts_array[ts])).where[PrcTs[r, p, ts]]
            ] = (
                Sum(
                    s.where[g.RsTree[r, s, ts] & g.Finest[r, s]],
                    g.g_yrfr[r, s]
                    * (
                        ts_array[s]
                        + Sum(
                            g.RsBelow[r, allts, s].where[
                                (
                                    ~(
                                        Sum(
                                            g.TsMap[r, sl, s].where[
                                                g.RsBelow[r, allts, sl]
                                            ],
                                            ts_array[sl],
                                        )
                                    ).where[ts_array[allts]]
                                )
                            ],
                            ts_array[allts],
                        )
                    ),
                )
                / g.g_yrfr[r, ts]
            )

        # *-----------------------------------------------------------------------------
        # * Leveling by direct inheritance
        # *-----------------------------------------------------------------------------
        flo_func[r, v, p, cg, comgrp, ts].where[
            ~(flo_func[r, v, p, cg, comgrp, ts])
        ] = sparse(
            Sum(
                Ffcks[r, p, cg, comgrp, Annual].where[PrcTs[r, p, ts]],
                flo_func[r, v, p, cg, comgrp, Annual],
            )
        )

        # *-----------------------------------------------------------------------------
        # *UR* after inheritance aggregation delete all data that are not specified for elements of PRC_TS
        # * ? not a good idea since at least partially deleting the input of the user ?
        # *
        # *  FLO_FUNC(R,T,P,CG,COM_GRP,S)$(Ffcks(R,P,CG,COM_GRP,S)*(NOT PRC_TS(R,P,S))) = 0;

        Ffcks.setRecords(None)
        CgGrp.setRecords(None)
