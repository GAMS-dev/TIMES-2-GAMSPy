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

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass
from core.pp_off_mod import pp_off
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
            mx=self.env.mx,
        )

        if self.env.obmac == "YES":
            macro.rts_active = True
        else:
            g.rts = Alias(m, name="RTS", alias_with=g.allts)

        self.tc.enqueue(self.exec2)

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  TS_GROUP(ALL_R,'ANNUAL',S) = ANNUAL(S);
  OPTION STOAL < TS_GROUP;
  TS_MAP(R,ANNUAL,S) = STOAL(R,S);
  TS_MAP(R,ALL_TS,TS)$SUM(TS_MAP(R,ALL_TS,S),TS_MAP(R,S,TS)) = YES;
  TS_MAP(R,S,S) = STOAL(R,S);
  STOAL(ALL_R,S)$STOAL(ALL_R,S) = STOAL(ALL_R,S)-1;
  IF(CARD(STOAL),ABORT "Error: Timeslice on several levels.");
* Set for timeslices strictly below
  RS_BELOW(TS_MAP(R,S,TS))$(NOT TS_MAP(R,TS,S)) = YES;
* Set for timeslices strictly ONE level below
  RS_BELOW1(RS_BELOW(R,S,TS))$(SUM(TS_MAP(R,S,ALL_TS)$RS_BELOW(R,ALL_TS,TS),1)=1) = YES;
  """,
        )

    def prepare_dynamic_timeslice_tree(self: TimsliceMod, mx: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(RS_BELOW1(R,ANNUAL,S)$SUM(TS_OFF(R,S,BOHYEAR,EOHYEAR),1),
{pp_off("TS_OFF", "S", "", f"NORTS(R,T{mx},S)$(", "1")}
    IF(PROD(T{mx},FIL(T)),G_YRFR(R,TS)$TS_MAP(R,S,TS) = 0;
    ELSE NORTS(R,T(FIL{mx}),TS)$TS_MAP(R,S,TS) = -INF));
""",
        )

    def exec2(self: TimsliceMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set the annual year fraction to 1
  G_YRFR(ALL_R,ANNUAL) = 1;
* Complete missing year fractions if non-zero fractions are given for timeslices right below:
  G_YRFR(R,S)$((G_YRFR(R,S)<=0)$TS_GROUP(R,'WEEKLY',S)) $= SUM(RS_BELOW1(R,S,TS),G_YRFR(R,TS));
  G_YRFR(R,S)$((G_YRFR(R,S)<=0)$TS_GROUP(R,'SEASON',S)) $= SUM(RS_BELOW1(R,S,TS),G_YRFR(R,TS));

*-----------------------------------------------------------------------------
* Remove timeslices that have a zero time fraction
  LOOP(TSL,FINEST(R,S)$((G_YRFR(R,S)<=0)$TS_GROUP(R,TSL,S)) = YES);
  TS_GROUP(R,TSL,S)$FINEST(R,S) = NO;
  TS_MAP(R,TS,S)$FINEST(R,S) = NO;
  RS_BELOW(R,TS,S)$FINEST(R,S) = NO;
  RS_BELOW1(R,TS,S)$FINEST(R,S) = NO;
  NORTS(R,T,S)$FINEST(R,S) = 0;
  OPTION CLEAR=FINEST;
* Build a set for all timeslices in the same subtree
  RS_TREE(R,S,TS)$(TS_MAP(R,TS,S) OR RS_BELOW(R,S,TS)) = YES;
* Define the set of the finest (highest) timeslices in use:
  FINEST(R,S)$(SUM(TS_MAP(R,S,TS),1)=1) = YES;
  LOOP(SAMEAS('5',J),RJLVL(J-ORD(TSL),R,TSL)=SUM(TS_GROUP(R,TSL,S),1));
* Define above-map for TSL levels
  LOOP((J,R,TSL)$RJLVL(J,R,TSL),Z=ORD(J);LOOP(RJLVL(JJ,R,TSLVL)$(ORD(JJ)>Z),RLUP(R,TSL,TSLVL)=1;Z=9));
*-----------------------------------------------------------------------------

* Target accuracy of fractions: 1 second
  Z = 8760*3600; PUTGRP=0;
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
* Calculate the number of storage periods for each timeslice
  G_CYCLE(TSL('WEEKLY'))$(G_CYCLE(TSL)=0)=8760/(24*7); TS_CYCLE(FINEST)=0;
  LOOP(RLUP(R,TSLVL,TSL),TS_CYCLE(R,S)$((TS_CYCLE(R,S)<1)$TS_GROUP(R,TSL,S)) = 365/G_CYCLE(TSLVL));
  LOOP(TSL,RS_STGPRD(R,S)$TS_GROUP(R,TSL,S) = MAX(1,SUM(RS_BELOW1(R,TS,S),G_YRFR(R,TS)*365/TS_CYCLE(R,TS))));

* Timeslice level for all timeslices
  LOOP(TSL, RS_TSLVL(R,S)$TS_GROUP(R,TSL,S) = TSLVLNUM(TSL));
* Calculate the lead from previous storage timeslice for each timeslice
  LOOP(TS_MAP(R,ANNUAL,S), F=0;
   LOOP(RS_BELOW1(R,S,TS), IF(F, RS_STG(R,TS)=ORD(TS)-Z; Z=ORD(TS); ELSE Z=ORD(TS); F=Z));
   RS_STG(R,S+(F-ORD(S)))$F = F-Z;);
* Calculate average residence time for storage activity in each timeslice
  LOOP((R,S,TS(S--RS_STG(R,S)))$RS_STGPRD(R,S),RS_STGAV(R,S) = (G_YRFR(R,S)+G_YRFR(R,TS))/2/RS_STGPRD(R,S));
  RS_STGAV(R,ANNUAL) = 1;

  OPTION STOAL<RS_BELOW1,CLEAR=RS_HR; STOAL(R,S)$(STOAL(R,S)=1)=0;
  IF(CARD(STOAL),PUTGRP=0;
    LOOP((R,S)$STOAL(R,S),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Duplicate parent timeslices - Fatal")}
    PUT QLOG ' FATAL ERROR   -    REG=',R.TL,' TS='S.TL));
* Define the lags to the ANNUAL timeslice for all S
  LOOP(ANNUAL(TS), STOA(S) = ORD(TS)-ORD(S));
  LOOP(TSL,STOAL(R,S)$TS_GROUP(R,TSL,S) = ORD(TSL)-1);
*----------------------------------------------------------------------
* Define TS hours and map for TS within same cycle
  IF(CARD(RP_UPR)+CARD(RP_UPT),LOOP(TS_MAP(R,ANNUAL,TS),F=0;Z=0;LOOP(RS_BELOW1(R,TS,S),F=G_YRFR(R,S)/RS_STGPRD(R,S);RS_HR(R,S)=MOD(Z+F/2,1);Z=Z+F));
  LOOP(JS(J,ANNUAL),
    RJ_SL(R,J+(MOD(ROUND((RS_HR(R,TS)*8760)/146,0),60)*2),S,TS)$RS_BELOW1(R,S,TS) = YES;
    RJ_SL(R,J+(MOD(ROUND((RS_HR(R,TS)*8760-73)/146+60,0),60)*2+1),S,TS)$RS_BELOW1(R,S,TS) = YES;
    OPTION RS_UP < RJ_SL;
  ));
  IF(CARD(RS_UP),
*   Remove hours too far
    RS_UP(R,TS,J,S)$((MOD(RS_HR(R,TS)-(ORD(J)-2)*73/8760+1,1)<48/8760) OR (MOD(ORD(J)*73/8760-RS_HR(R,TS)+1,1)<25/8760)) = NO;
    OPTION JS < RS_UP; RJ_SL(R,J,S,TS)$(NOT JS(J,S)) = NO;
*   Cycles
    JS_CCL(R,JS(J,S)) = MAX(1/G_YRFR(R,S),365/TS_CYCLE(R,S));
    RS_MODUS(RS_UP(R,S,JS),SL)$RJ_SL(R,JS,SL) = MOD(RS_HR(R,S)-RS_HR(R,SL)+G_YRFR(R,S)/RS_STGPRD(R,S)/2+2/JS_CCL(R,JS),1/JS_CCL(R,JS));
  );
""",
        )
