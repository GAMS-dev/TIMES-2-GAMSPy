# pp_lvlbr_mod.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlbrMod(GamsClass):
    """Translation unit for pp_lvlbr.mod."""

    # Instance attributes
    module_name: str = "pp_lvlbr_mod"
    gams_source: str = "pp_lvlbr.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.pp_lvlbr_exec,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            rl=self.env.rl,
            pl=self.env.pl,
        )

    def pp_lvlbr_exec(
        self: PpLvlbrMod,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
        rl: str = "",
        pl: str = "",
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR=UNCD7;
*-----------------------------------------------------------------------------
LOOP((RTP(R,V,P){arg2},S,BD)$((NOT {arg3}(R,P,{arg7}S))${arg1}(R,V,P{arg2},S,BD)),
  F = 0; Z = 1;
  LOOP(RS_BELOW(R,TS,S)$Z,
* If value is below target level, aggregate only if value not found at target level
    IF({arg1}(R,V,P{arg2},TS,BD), F = 1;
      IF({arg3}(R,P,{arg7}TS), Z = 0; IF(NOT UNCD7(R,TS,P{arg2},TS,BD{arg4}),
{pp_qaput("PUTOUT", "PUTGRP", "01", f"{arg1} Bounds conflict: Bound at {arg3} level and below, lower ignored")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' TS=',TS.TL ;
         UNCD7(R,TS,P{arg2},TS,BD{arg4}) = YES));
    ELSEIF {arg3}(R,P,{arg7}TS), Z = 0; UNCD7(R,V,P{arg2},TS,BD{arg4}) = YES));
  IF(Z, Z = SUM(RS_BELOW(R,S,TS)${arg1}(R,V,P{arg2},TS,BD),EPS+({arg1}(R,V,P{arg2},TS,BD) > EPS)${arg3}(R,P,{arg7}TS));
* If value above target level and no values found below or above, mark to be inherited down:
    IF(NOT (F+Z), UNCD7(R,V,P{arg2},S,BD{arg4}) = YES;
* If value is above targets and all other values in the subtree are at non-target slices, mark to be leveled:
    ELSE Z=Z<1; UNCD7(R,V,P{arg2},TS,BD{arg4})$(RS_BELOW(R,S,TS)*{arg3}(R,P,{arg7}TS)*(Z+(NOT {arg1}(R,V,P{arg2},TS,BD))${arg5})) = YES)));
*-----------------------------------------------------------------------------
* Aggregation/inheritance to target timeslices
*-----------------------------------------------------------------------------
LOOP(UNCD7(R,V,P{arg2},TS,BD{arg4}),
 IF({arg3}(R,P,{arg7}TS),
* Leveling by simultaneous aggregation/inheritance
   TS_ARRAY(ALL_TS) = {arg1}(R,V,P{arg2},ALL_TS,BD);
    {arg1}(R,V,P{arg2},TS,BD) $=
      SUM(RS_TREE(FINEST(R,S),TS), G_YRFR(R,S) * (TS_ARRAY(S) +
           SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
               TS_ARRAY(ALL_TS))))/G_YRFR(R,TS);
* Otherwise just simple direct inheritance down
  ELSE Z = {arg1}(R,V,P{arg2},TS,BD); {arg1}(R,V,P{arg2},S,BD)$(RS_BELOW(R,TS,S)${arg3}(R,P,{arg7}S)) = Z));
*-----------------------------------------------------------------------------
OPTION CLEAR=UNCD7;
IF({arg6}, PUTGRP = 0;
  LOOP((R,V,P{arg2},S)${arg1}(R,V,P{arg2},S,'FX'),
* check to see if both LO/FX and UP/FX at same S
    IF({arg3}(R,P,{arg7}S) AND ({arg1}(R,V,P{arg2},S,'UP') + {arg1}(R,V,P{arg2},S,'LO')),
{pp_qaput("PUTOUT", "PUTGRP", "01", f"{arg1} Bounds conflict: FX + LO/UP at same TS-level, latter ignored")}
      PUT QLOG ' WARNING       -     R=',{rl},' Y=',V.TL,' P=',{pl},' S=',S.TL ;
      UNCD7(R,V,P{arg2},S,'0'{arg4}) = YES;));
  IF(PUTGRP, {arg1}(R,V,P{arg2},S,BDNEQ)$UNCD7(R,V,P{arg2},S,'0'{arg4}) = 0;
    OPTION CLEAR=UNCD7));
""",
        )
