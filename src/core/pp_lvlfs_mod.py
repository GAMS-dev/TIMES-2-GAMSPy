# pp_lvlfs_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLFS set the level of FLO_SUM attribute using aggregation/inheritance
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Assumption is that values can be at any level
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlfsMod(GamsClass):  # FilenameExt
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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"SET FSTSL(TSLVL,R,P,CG,CG,CG,S) //;",
        )
        self.tc.enqueue(self.pp_lvlfs_exec)

    def pp_lvlfs_exec(self: PpLvlfsMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* check all commodities in the groups of a process at other than PRC_TS level
  COEF_PTRAN(R,LL,P,CG,C,COM_GRP,S) $= FLO_SUM(R,LL,P,CG,C,COM_GRP,S)$(NOT RPCS_VAR(R,P,C,S));
  OPTION FSCKS <= COEF_PTRAN;
  FSCK(R,P,CG,C,COM_GRP) $= SUM(FSCKS(R,P,CG,C,COM_GRP,S)$(NOT RPS_PRCTS(R,P,S)),1);
  LOOP(ANNUAL(TS(TSLVL)),FSTSL(TSLVL+STOAL(R,S),FSCKS(R,P,CG,C,COM_GRP,S)) = YES);
*-----------------------------------------------------------------------------
* Leveling by simultaneous aggregation/inheritance
*-----------------------------------------------------------------------------
  LOOP((FSCK(R,P,CG,C,COM_GRP),RTP(R,V,P)),
    TS_ARRAY(ALL_TS) = FLO_SUM(R,V,P,CG,C,COM_GRP,ALL_TS);
    FLO_SUM(R,V,P,CG,C,COM_GRP,TS)$RPCS_VAR(R,P,C,TS) =
      SUM(RS_TREE(FINEST(R,S),TS), G_YRFR(R,S) * (TS_ARRAY(S) +
           SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
               TS_ARRAY(ALL_TS))))/G_YRFR(R,TS));
*-----------------------------------------------------------------------------
* Leveling by direct inheritance
*-----------------------------------------------------------------------------
* after mixed aggregation/inheritance delete all data that are not specified at PRC_TS
  FLO_SUM(R,LL,P,CG,C,COM_GRP,S)$COEF_PTRAN(R,LL,P,CG,C,COM_GRP,S) = 0;
  FLO_SUM(R,LL,P,CG,C,COM_GRP,S)$(NOT RTP(R,LL,P)) = 0;
  FOR(Z=CARD(TSLVL)-2 DOWNTO 0,
   LOOP(SAMEAS(TSLVL-Z,'ANNUAL'),
    FLO_SUM(RTP(R,V,P),CG,C,COM_GRP,TS)$((NOT FLO_SUM(R,V,P,CG,C,COM_GRP,TS))$RPCS_VAR(R,P,C,TS)) $=
       SUM(FSTSL(TSLVL,R,P,CG,C,COM_GRP,S)$RS_BELOW(R,S,TS),COEF_PTRAN(R,V,P,CG,C,COM_GRP,S));
  ));
*-----------------------------------------------------------------------------
  OPTION CLEAR=COEF_PTRAN, CLEAR = FSCK, CLEAR = FSCKS, CLEAR=FSTSL;
  FLO_SUM(R,LL,P,CG,C,CG,S)$FSCKS(R,P,CG,C,CG,S) = 0;
""",
        )
