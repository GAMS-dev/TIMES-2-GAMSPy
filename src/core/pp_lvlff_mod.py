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

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"SET FFCKS(REG,PRC,CG,CG,TS)  //;",
        )
        self.tc.enqueue(self.pp_lvlff_exec)

    def pp_lvlff_exec(self: PpLvlffMod):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* check all commodities in the groups of a process at other than PRC_TS level
  OPTION FFCKS <= FLO_FUNC; FFCKS(R,P,CG,CG2,S)$(PRC_TS(R,P,S)+ACTCG(CG))=NO;
  LOOP(FFCKS(R,P,CG,COM_GRP,S)$STOA(S),CG_GRP(R,P,CG,COM_GRP) = YES);
*-----------------------------------------------------------------------------
* Leveling by simultaneous aggregation/inheritance
*-----------------------------------------------------------------------------
  LOOP((CG_GRP(R,P,CG,COM_GRP),RTP(R,V,P)),
    TS_ARRAY(ALL_TS) = FLO_FUNC(R,V,P,CG,COM_GRP,ALL_TS);
    FLO_FUNC(R,V,P,CG,COM_GRP,TS)$((NOT TS_ARRAY(TS))$PRC_TS(R,P,TS)) =
      SUM(RS_TREE(FINEST(R,S),TS), G_YRFR(R,S) * (TS_ARRAY(S) +
           SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
               TS_ARRAY(ALL_TS))))/G_YRFR(R,TS));
*-----------------------------------------------------------------------------
* Leveling by direct inheritance
*-----------------------------------------------------------------------------
  FLO_FUNC(R,V,P,CG,COM_GRP,TS)$(NOT FLO_FUNC(R,V,P,CG,COM_GRP,TS)) $=
      SUM(FFCKS(R,P,CG,COM_GRP,ANNUAL)$PRC_TS(R,P,TS),FLO_FUNC(R,V,P,CG,COM_GRP,ANNUAL));
*-----------------------------------------------------------------------------

*UR* after inheritance aggregation delete all data that are not specified for elements of PRC_TS
* ? not a good idea since at least partially deleting the input of the user ?
*
*  FLO_FUNC(R,T,P,CG,COM_GRP,S)$(FFCKS(R,P,CG,COM_GRP,S)*(NOT PRC_TS(R,P,S))) = 0;

  OPTION CLEAR = FFCKS, CLEAR = CG_GRP;
""",
        )
