# timslice_mod.py
#
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Timslice.mod - Auxiliary timeslice preprocessing
# *=============================================================================*
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Alias,
    Domain,
    Else,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Product,
    Set,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Round, aggregate, mod, project, same_as

from core.base_class import GamsClass
from core.pp_off_mod import pp_off_GP
from core.pp_qaput_mod import pp_qaput
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class TimsliceMod(GamsClass):
    """Translation unit for timslice.mod."""

    # Instance attributes
    module_name: str = "timslice_mod"
    gams_source: str = "timslice.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        self.compile()

    def compile(self: TimsliceMod) -> None:
        # complete timeslice declarations
        #  - all below ANNUAL
        #  - each individual to itself, including leaves
        #  - all TS below a node
        g = self.tc
        m = g.container

        g.Rjlvl = Set(m, name="RJLVL", domain=[g.j, g.r, g.tslvl])
        g.Rlup = Set(m, name="RLUP", domain=[g.r, g.tsl, g.tsl])
        g.rs_hr = Parameter(m, name="RS_HR", domain=[g.r, g.s])
        g.my_sum = Parameter(m, name="MY_SUM", records=0)
        g.norts = Parameter(m, name="NORTS", domain=[g.r, g.year, g.s])
        g.RsUp = Set(m, name="RS_UP", domain=[g.r, g.ts, g.j, g.ts])
        g.RjSl = Set(m, name="RJ_SL", domain=[g.r, g.j, g.ts, g.ts])
        g.Js = Set(m, name="JS", domain=[g.j, g.ts], records=[("1", "ANNUAL")])
        g.rs_modus = Parameter(m, name="RS_MODUS", domain=[g.r, g.s, g.j, g.ts, g.s])

        self.tc.enqueue(self.exec1)

        self.env.set_scoped("mx", "(MIYR_1)")
        self.env.set_scoped("mx_GP", (g.Miyr1,))
        self.env.set_global("rts", lambda s="S": s)
        self.env.set_global("rts_GP", lambda s=g.s: s)

        if (self.env.obmac + self.env.dynts).upper() == "YESYES" and self.tc.defined(
            "TS_OFF"
        ):
            self.env.set_scoped("mx", "")
            self.env.set_scoped("mx_GP", ())
            self.env.set_global("rts_GP", lambda s=g.s: s + g.norts[g.r, g.t, s])

        self.tc.add_gams_code(module=self, phase="init", code="SET TS_OFF //;")

        self.tc.enqueue(
            self.prepare_dynamic_timeslice_tree,
            mx=self.env.mx_GP,
        )

        if self.env.obmac == "YES":
            macro.rts_active = True
        else:
            g.rts = Alias(m, name="RTS", alias_with=g.allts)

        self.tc.enqueue(self.exec2)

    def exec1(self) -> None:
        g = self.tc
        g.TsGroup[g.allr, "ANNUAL", g.s] = g.Annual[g.s]
        aggregate(source=g.TsGroup, target=g.stoal)
        g.TsMap[g.r, g.Annual, g.s] = g.stoal[g.r, g.s]
        g.TsMap[g.r, g.allts, g.ts].where[
            Sum(g.TsMap[g.r, g.allts, g.s], g.TsMap[g.r, g.s, g.ts])
        ] = True
        g.TsMap[g.r, g.s, g.s] = g.stoal[g.r, g.s]
        g.stoal[g.allr, g.s].where[g.stoal[g.allr, g.s]] = g.stoal[g.allr, g.s] - 1.0
        if g.stoal.number_records:
            raise ValueError("Error: Timeslice on several levels.")
        # * Set for timeslices strictly below
        g.RsBelow[g.TsMap[g.r, g.s, g.ts]].where[(~(g.TsMap[g.r, g.ts, g.s]))] = True
        # * Set for timeslices strictly ONE level below
        g.RsBelow1[g.RsBelow[g.r, g.s, g.ts]].where[
            (
                Sum(
                    g.TsMap[g.r, g.s, g.allts].where[g.RsBelow[g.r, g.allts, g.ts]], 1.0
                )
                == 1.0
            )
        ] = True

    def prepare_dynamic_timeslice_tree(
        self: TimsliceMod, mx: tuple[Set] | tuple[()]
    ) -> None:
        g = self.tc
        # T%MX% / FIL%MX%: restricted to MIYR_1 unless dynamic timeslices are active
        tmx = g.t[mx[0]] if mx else g.t
        filmx = g.Fil[mx[0]] if mx else g.Fil
        with Loop(
            g.RsBelow1[g.r, g.Annual, g.s].where[
                Sum(g.TsOff[g.r, g.s, g.bohyear, g.eohyear], 1.0)
            ]
        ):
            pp_off_GP(g, g.TsOff, (g.s,), Number(1), g.norts[g.r, tmx, g.s], 1)
            with If(Product(tmx, g.Fil[g.t])):
                g.g_yrfr[g.r, g.ts].where[g.TsMap[g.r, g.s, g.ts]] = 0.0
            with Else():
                g.norts[g.r, g.t[filmx], g.ts].where[g.TsMap[g.r, g.s, g.ts]] = (
                    SpecialValues.NEGINF
                )

    def exec2(self: TimsliceMod) -> None:
        g = self.tc
        # * Set the annual year fraction to 1
        g.g_yrfr[g.allr, g.Annual] = 1.0
        # * Complete missing year fractions if non-zero fractions are given for timeslices right below:
        g.g_yrfr[g.r, g.s].where[
            ((g.g_yrfr[g.r, g.s] <= 0.0).where[g.TsGroup[g.r, "WEEKLY", g.s]])
        ] = sparse(Sum(g.RsBelow1[g.r, g.s, g.ts], g.g_yrfr[g.r, g.ts]))
        g.g_yrfr[g.r, g.s].where[
            ((g.g_yrfr[g.r, g.s] <= 0.0).where[g.TsGroup[g.r, "SEASON", g.s]])
        ] = sparse(Sum(g.RsBelow1[g.r, g.s, g.ts], g.g_yrfr[g.r, g.ts]))
        # *-----------------------------------------------------------------------------
        # * Remove timeslices that have a zero time fraction
        with Loop(g.tsl):
            g.Finest[g.r, g.s].where[
                ((g.g_yrfr[g.r, g.s] <= 0.0).where[g.TsGroup[g.r, g.tsl, g.s]])
            ] = True
        g.TsGroup[g.r, g.tsl, g.s].where[g.Finest[g.r, g.s]] = False
        g.TsMap[g.r, g.ts, g.s].where[g.Finest[g.r, g.s]] = False
        g.RsBelow[g.r, g.ts, g.s].where[g.Finest[g.r, g.s]] = False
        g.RsBelow1[g.r, g.ts, g.s].where[g.Finest[g.r, g.s]] = False
        g.norts[g.r, g.t, g.s].where[g.Finest[g.r, g.s]] = 0.0
        g.Finest.setRecords(None)
        # * Build a set for all timeslices in the same subtree
        g.RsTree[g.r, g.s, g.ts].where[
            ((g.TsMap[g.r, g.ts, g.s]) | (g.RsBelow[g.r, g.s, g.ts]))
        ] = True
        # * Define the set of the finest (highest) timeslices in use:
        g.Finest[g.r, g.s].where[(Sum(g.TsMap[g.r, g.s, g.ts], 1.0) == 1.0)] = True
        with Loop(g.j.where[same_as("5", g.j)]):
            g.Rjlvl[g.j - Ord(g.tsl), g.r, g.tsl] = Sum(g.TsGroup[g.r, g.tsl, g.s], 1.0)
        # * Define above-map for TSL levels
        with Loop(Domain(g.j, g.r, g.tsl).where[g.Rjlvl[g.j, g.r, g.tsl]]):
            g.z[...] = Ord(g.j)
            with Loop(g.Rjlvl[g.jj, g.r, g.tslvl].where[(Ord(g.jj) > g.z)]):
                g.Rlup[g.r, g.tsl, g.tslvl] = 1.0
                g.z[...] = 9.0
        # *-----------------------------------------------------------------------------
        # * Target accuracy of fractions: 1 second
        g.z[...] = 8760.0 * 3600.0
        g.putgrp[...] = 0.0

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Normalize year fractions if they do not sum up
  LOOP(TS_GROUP(R,TSL,S)$(NOT FINEST(R,S)),
   IF(ANNUAL(S)$CARD(NORTS), F=0;
     LOOP(T,MY_F=1-SUM(RS_BELOW1(R,S,TS)$(RS_HR(R,TS)$(NORTS(R,T,TS)=0)),RS_HR(R,TS));
       MY_SUM = SUM(RS_BELOW1(R,S,TS)$((NOT RS_HR(R,TS))$(NORTS(R,T,TS)=0)),G_YRFR(R,TS));
       IF(MY_SUM*MY_F>0,RS_HR(R,TS)$((NORTS(R,T,TS)=0)$(NOT RS_HR(R,TS))$RS_BELOW1(R,S,TS))=MY_F/MY_SUM*G_YRFR(R,TS);
       ELSEIF ABS(MY_F)>99/Z,ABORT 'Invalid dynamic Timeslice configuration'); F=MAX(F,ABS(MY_F-MY_SUM)));
     G_YRFR(R,TS) $= RS_HR(R,TS);
*  Get the year fraction of current timeslice and sum of those below
   ELSE MY_F=G_YRFR(R,S); MY_SUM=SUM(RS_BELOW1(R,S,TS),G_YRFR(R,TS));
     F=ABS(MY_F-MY_SUM); IF(F*Z>1,G_YRFR(R,TS)$RS_BELOW1(R,S,TS)=MY_F/MY_SUM*G_YRFR(R,TS)));
*  If the sum differs from the lump sum by over a second, do normalize:
   IF(F*Z > 1,
{pp_qaput("PUTOUT", "PUTGRP", "01", "User-provided G_YRFR values are not valid year fractions")}
     PUT QLOG ' WARNING       - TS fractions normalized,  (R.TSL.S)=',TS_GROUP.TE(TS_GROUP);
  ));
*-----------------------------------------------------------------------------
  """,
        )
        # * Calculate the number of storage periods for each timeslice
        g.g_cycle[g.tsl["WEEKLY"]].where[(g.g_cycle[g.tsl] == 0.0)] = 8760.0 / (
            24.0 * 7.0
        )
        g.ts_cycle[g.Finest] = 0.0
        with Loop(g.Rlup[g.r, g.tslvl, g.tsl]):
            g.ts_cycle[g.r, g.s].where[
                ((g.ts_cycle[g.r, g.s] < 1.0).where[g.TsGroup[g.r, g.tsl, g.s]])
            ] = 365.0 / g.g_cycle[g.tslvl]
        with Loop(g.tsl):
            g.rs_stgprd[g.r, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = Max(
                1.0,
                Sum(
                    g.RsBelow1[g.r, g.ts, g.s],
                    g.g_yrfr[g.r, g.ts] * 365.0 / g.ts_cycle[g.r, g.ts],
                ),
            )
        # * Timeslice level for all timeslices
        with Loop(g.tsl):
            g.rs_tslvl[g.r, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = g.tslvlnum[g.tsl]
        # * Calculate the lead from previous storage timeslice for each timeslice
        with Loop(g.TsMap[g.r, g.Annual, g.s]):
            g.f[...] = 0.0
            with Loop(g.RsBelow1[g.r, g.s, g.ts]):
                with If(g.f):
                    g.rs_stg[g.r, g.ts] = Ord(g.ts) - g.z
                    g.z[...] = Ord(g.ts)
                with Else():
                    g.z[...] = Ord(g.ts)
                    g.f[...] = g.z
            g.rs_stg[g.r, g.s + (g.f - Ord(g.s))].where[g.f] = g.f - g.z
        # * Calculate average residence time for storage activity in each timeslice
        with Loop(
            Domain(g.r, g.s, g.ts[g.s.lag(g.rs_stg[g.r, g.s], "circular")]).where[
                g.rs_stgprd[g.r, g.s]
            ]
        ):
            g.rs_stgav[g.r, g.s] = (
                (g.g_yrfr[g.r, g.s] + g.g_yrfr[g.r, g.ts]) / 2.0 / g.rs_stgprd[g.r, g.s]
            )
        g.rs_stgav[g.r, g.Annual] = 1.0
        aggregate(source=g.RsBelow1, target=g.stoal)
        g.rs_hr.setRecords(None)
        g.stoal[g.r, g.s].where[(g.stoal[g.r, g.s] == 1.0)] = 0.0

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(CARD(STOAL),PUTGRP=0;
    LOOP((R,S)$STOAL(R,S),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Duplicate parent timeslices - Fatal")}
    PUT QLOG ' FATAL ERROR   -    REG=',R.TL,' TS='S.TL));
*----------------------------------------------------------------------
""",
        )

        # * Define the lags to the ANNUAL timeslice for all S
        with Loop(g.Annual[g.ts]):
            g.stoa[g.s] = Ord(g.ts) - Ord(g.s)
        with Loop(g.tsl):
            g.stoal[g.r, g.s].where[g.TsGroup[g.r, g.tsl, g.s]] = Ord(g.tsl) - 1.0
        # *----------------------------------------------------------------------
        # * Define TS hours and map for TS within same cycle
        if g.RpUpr.number_records + g.RpUpt.number_records:
            with Loop(g.TsMap[g.r, g.Annual, g.ts]):
                g.f[...] = 0.0
                g.z[...] = 0.0
                with Loop(g.RsBelow1[g.r, g.ts, g.s]):
                    g.f[...] = g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s]
                    g.rs_hr[g.r, g.s] = mod(g.z + g.f / 2.0, 1.0)
                    g.z[...] = g.z + g.f
            with Loop(g.Js[g.j, g.Annual]):
                g.RjSl[
                    g.r,
                    g.j
                    + (
                        mod(Round((g.rs_hr[g.r, g.ts] * 8760.0) / 146.0, 0), 60.0) * 2.0
                    ),
                    g.s,
                    g.ts,
                ].where[g.RsBelow1[g.r, g.s, g.ts]] = True
                g.RjSl[
                    g.r,
                    g.j
                    + (
                        mod(
                            Round(
                                (g.rs_hr[g.r, g.ts] * 8760.0 - 73.0) / 146.0 + 60.0, 0
                            ),
                            60.0,
                        )
                        * 2.0
                        + 1.0
                    ),
                    g.s,
                    g.ts,
                ].where[g.RsBelow1[g.r, g.s, g.ts]] = True
                project(source=g.RjSl, target=g.RsUp)
        if g.RsUp.number_records:
            # *   Remove hours too far
            g.RsUp[g.r, g.ts, g.j, g.s].where[
                (
                    (
                        mod(
                            g.rs_hr[g.r, g.ts] - (Ord(g.j) - 2.0) * 73.0 / 8760.0 + 1.0,
                            1.0,
                        )
                        < 48.0 / 8760.0
                    )
                    | (
                        mod(Ord(g.j) * 73.0 / 8760.0 - g.rs_hr[g.r, g.ts] + 1.0, 1.0)
                        < 25.0 / 8760.0
                    )
                )
            ] = False
            project(source=g.RsUp, target=g.Js)
            g.RjSl[g.r, g.j, g.s, g.ts].where[(~(g.Js[g.j, g.s]))] = False
            # *   Cycles
            g.js_ccl[g.r, g.Js[g.j, g.s]] = Max(
                1.0 / g.g_yrfr[g.r, g.s], 365.0 / g.ts_cycle[g.r, g.s]
            )
            g.rs_modus[g.RsUp[g.r, g.s, g.Js], g.sl].where[g.RjSl[g.r, g.Js, g.sl]] = (
                mod(
                    g.rs_hr[g.r, g.s]
                    - g.rs_hr[g.r, g.sl]
                    + g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 2.0
                    + 2.0 / g.js_ccl[g.r, g.Js],
                    1.0 / g.js_ccl[g.r, g.Js],
                )
            )
