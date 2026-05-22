# eqxbnd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQXBND limits the total exchange from internal + external regions
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - BND ts restricted to the PRC_TS level or above?
# *  - *** NOTE: IMPort SUMs all EXPorts and vise versa
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqxbndMod(GamsClass):
    """Translation unit for eqxbnd.mod."""

    module_name: str = "eqxbnd_mod"
    gams_source: str = "eqxbnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*V0.5b 980902 - avoid equations if LO=0/UP=INF
  {self.env.eq}{self.arg1}_XBND(ALL_REG,{self.env.tx},C,S,IE {self.env.swt})$((SUM(RPC_IRE(ALL_REG,P,C,IE),1)*{self.arg3})$IRE_XBND(ALL_REG,T,C,S,IE,'{self.arg2}'))..

*-----------------------------------------------------------------------------
* if region is internal then handle by
*-----------------------------------------------------------------------------
* sum over all possible at process TS-level
       SUM((RPC_IRE(REG(ALL_REG),P,C,IE),RTPCS_VARF(REG,T,P,C,TS))$RS_TREE(REG,S,TS),
* sum all the existing activities
            SUM(RTP_VNTBYR(REG,T,P,V),
* [UR] model reduction REDUCE is set in *.run
              ({self.env.var}_IRE(REG,V,T,P,C,TS,IE{self.env.sow})$(NOT RPC_AIRE(REG,P,C)) +
               ({self.env.var}_ACT(REG,V,T,P,TS{self.env.sow})*PRC_ACTFLO(REG,V,P,C))$RPC_AIRE(REG,P,C)) *
* bound coarser than variable or bound finer than variable
              RS_FR(REG,S,TS)
            )
       ) +

*-----------------------------------------------------------------------------
* if region is external then handle the internal guys
*-----------------------------------------------------------------------------
* sum over all possible at process TS-level
*V05c 980811 - use IMP/EXP sets instead of ordering
       SUM(RPC_IRE(R,P,COM,IMPEXP(IE--1))$((TOP_IRE(ALL_REG,C,R,COM,P)$XPT(IE)) +
                                           (TOP_IRE(R,COM,ALL_REG,C,P)$IMP(IE))),
* sum all the existing activities
            SUM(RS_TREE(R,ALL_TS,TS)$(RTPCS_VARF(R,T,P,COM,TS)*IRE_TSCVT(R,ALL_TS,ALL_REG,S)),
                SUM(RTP_VNTBYR(R,T,P,V),
* [UR] model reduction REDUCE is set in *.run
                  ({self.env.var}_IRE(R,V,T,P,COM,TS,IMPEXP{self.env.sow})$(NOT RPC_AIRE(R,P,COM)) +
                   ({self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)) *
* ALL_TS coarser than variable or finer than variable
                  IRE_TSCVT(R,ALL_TS,ALL_REG,S) * RS_FR(R,ALL_TS,TS)
                )
            )
       )$(NOT REG(ALL_REG))

  ={self.arg1}=

       IRE_XBND(ALL_REG,T,C,S,IE,'{self.arg2}')
  ;
""",
        )
