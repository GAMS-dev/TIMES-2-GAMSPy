# pp_lvlus_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLUS aggregate/inherit UC_N attributes if at different than target level
# *   arg1 - attribute name (UC_ACT, UC_FLO etc.)
# *   arg2 - other qualifying indexes before S index (e.g. ',C')
# *   arg3 - TS set shooting for (PRC_TS, RPCS etc.)
# *   arg4 - UNCD7 residual dimension
# *   arg5 - optional remaining indexes (e.g. 'IE')
# *   arg6 - optional UC_N qualifying indexes (e.g. COM_VAR)
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlusMod(GamsClass):
    """Translation unit for pp_lvlus.mod."""

    # Instance attributes
    module_name: str = "pp_lvlus_mod"
    gams_source: str = "pp_lvlus.mod"

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
        arg8: str = "",
        arg9: str = "",
        arg10: str = "",
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
        self.arg8 = arg8
        self.arg9 = arg9
        self.arg10 = arg10
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg9,
            arg10=self.arg10,
        )
        self.tc.enqueue(
            self.simultaneous_aggregation,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg10=self.arg10,
        )

    def exec1(
        self: PpLvlusMod,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        arg7: str,
        arg8: str,
        arg9: str,
        arg10: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=UNCD7;
  LOOP((UC_N{arg6},SIDE,R,T,{arg2},S{arg5})${arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5}),
    IF((NOT {arg3}(R,{arg7}{arg10},S))$STOA(S),Z=STOAL(R,S);
      IF(UNCD7(UC_N{arg6},SIDE,R,{arg2}{arg5},'OUT'{arg4}), IF(Z>F, F=9; UNCD7(UC_N{arg6},SIDE,R,{arg2}{arg5},'IN'{arg4})=YES);
      ELSE F=SMAX({arg7}{arg8}_TSL(R,{arg7},TSL),MAX({arg9}+EPS,ORD(TSL)-1));
        IF(Z>F, F=9; UNCD7(UC_N{arg6},SIDE,R,{arg2}{arg5},IO{arg4})=YES; ELSE UNCD7(UC_N{arg6},SIDE,R,{arg2}{arg5},'OUT'{arg4})=YES))));
""",
        )

    def simultaneous_aggregation(
        self: PpLvlusMod,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        arg7: str,
        arg10: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Simultaneous aggregation/inheritance to target timeslices
*-----------------------------------------------------------------------------
  LOOP(UNCD7(UC_N{arg6},SIDE,R,{arg2}{arg5},IO{arg4}),
    IF(IPS(IO), F=0;
*...Leveling by simultaneous aggregation/inheritance; but only if target level value is not present
    LOOP(T, TS_ARRAY(S) = {arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5});
      {arg1}(UC_N{arg6},SIDE,R,T,{arg2},TS{arg5})$((NOT TS_ARRAY(TS))${arg3}(R,{arg7}{arg10},TS)) $=
        SUM(RS_TREE(FINEST(R,S),TS), G_YRFR(R,S) * (TS_ARRAY(S) +
          SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
            TS_ARRAY(ALL_TS))))/G_YRFR(R,TS))
    ELSEIF F,
*...Inherit all from above
    LOOP(T, TS_ARRAY(S) = {arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5});
      LOOP(RJLVL(J,R,TSL)$(ORD(TSL)<4),
        LOOP(TS_GROUP(R,TSL,TS),TS_ARRAY(S)$(NOT TS_ARRAY(S)) $= TS_ARRAY(TS)$RS_BELOW(R,TS,S));
      {arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5})${arg3}(R,{arg7}{arg10},S) $= TS_ARRAY(S)));
    ELSE F=1));
*-----------------------------------------------------------------------------
  {arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5})$({arg3}(R,{arg7}{arg10},S)$(NOT {arg1}(UC_N{arg6},SIDE,R,T,{arg2},S{arg5}))) $= {arg1}(UC_N{arg6},SIDE,R,T,{arg2},'ANNUAL'{arg5});
  OPTION CLEAR=UNCD7;
""",
        )
