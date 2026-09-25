# pp_lvlif_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLIF set the level of a IRE_FLO attribute using aggregation/inheritance
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Assumption is that values can be at any level
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlifMod(GamsClass):
    """Translation unit for pp_lvlif.mod."""

    # Instance attributes
    module_name: str = "pp_lvlif_mod"
    gams_source: str = "pp_lvlif.mod"

    def __init__(
        self,
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
        self.tc.enqueue(self.exec1, rl=self.env.rl, pl=self.env.pl)

    def exec1(self: PpLvlifMod, rl: str, pl: str) -> None:
        include_pp_qaput = pp_qaput(
            "PUTOUT", "PUTGRP", "02", "IRE_FLO import commodity not in TOP_IRE"
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION CLEAR=UNCD7; PUTGRP = 0;
*-----------------------------------------------------------------------------
  LOOP((REG,V,P,COM,R,C,S)$IRE_FLO(REG,V,P,COM,R,C,S),
    IF((NOT RPCS_VAR(R,P,C,S))$STOA(S),
      IF(NOT UNCD7(REG,V,P,COM,R,C,'N'),
        IF(NOT RPC_IRE(R,P,C,'IMP'),TRACKPC(R,P,C)=YES;
        ELSE UNCD7(REG,V,P,COM,R,C,'N') = YES))));
  LOOP(TRACKPC(R,P,C),
{include_pp_qaput}
     PUT QLOG ' WARNING        -    R=',{rl},' P=',{pl},' C=',C.TL );
*-----------------------------------------------------------------------------
* Aggregation/inheritance to target timeslices
*-----------------------------------------------------------------------------
  LOOP(UNCD7(REG,V,P,COM,R,C,L),
* Leveling by simultaneous aggregation/inheritance; but only if target level value not present
     TS_ARRAY(S) = IRE_FLO(REG,V,P,COM,R,C,S);
     IRE_FLO(REG,V,P,COM,R,C,TS)$((NOT TS_ARRAY(TS))$PRC_TS(R,P,TS)) $=
         SUM(RS_TREE(FINEST(R,S),TS), G_YRFR(R,S) * (TS_ARRAY(S) +
           SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
             TS_ARRAY(ALL_TS))))/G_YRFR(R,TS));
*-----------------------------------------------------------------------------
* Simple direct inheritance down
  IRE_FLO(RTP(REG,V,P),COM,R,C,S)$((NOT IRE_FLO(REG,V,P,COM,R,C,S))$PRC_TS(R,P,S)) $= IRE_FLO(REG,V,P,COM,R,C,'ANNUAL');
  OPTION CLEAR=TRACKPC, CLEAR=UNCD7;

""",
        )
