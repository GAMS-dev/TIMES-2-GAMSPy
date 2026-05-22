# pp_shapr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_SHPRC.MOD shape a process based attribute
# *   %1 - attribute name
# *   %2 - driving indexes
# *   %3 - any qualifiers to help narrow loop (if none, set to YES)
# *   %4 - mapped coefficient
# *   %5 - optional -M(R,V,P) or 1
# *=============================================================================*
# *AL Comments:
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpShaprMod(GamsClass):
    """Translation unit for filename.extension."""

    # Instance attributes
    module_name: str = "pp_shapr"
    gams_source: str = "pp_shapr.mod"

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
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
SET RTP_SHAPI(REG,ALLYEAR,PRC,BD,J,J,LL,LL) //;
""",
        )

        self.env.set_local("pass", self.arg3)
        if self.arg3 == "":
            self.env.set_local("pass", "YES")
        self.tc.enqueue(
            self.exec_start_end,
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            pass_var=self.env.__getattr__("pass"),
        )

    def exec_start_end(
        self: PpShaprMod,
        arg1: str,
        arg2: str,
        arg4: str,
        arg5: str,
        arg6: str,
        pass_var: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(BD,RTP_ISHPR(RTP(R,V,P))$(({arg1}{arg6}X(RTP,BD) GE 1.5)${arg1}{arg6}X(RTP,BD)) = YES);
  RTP_ISHPR(RTP(R,V,P))$(({arg5} GE 1.5)${arg5}) = YES;

* Prepare for start and end years
  OPTION CLEAR=FIL2; FIL2(V) = B(V)-YEARVAL(V);
  PASTSUM(RTP_ISHPR(R,V,P)) = FIL2(V)+NCAP_ILED(R,V,P)+NCAP_TLIFE(R,V,P)-1;

* Shape attributes only for processes around for > 1 period
  {arg1}{arg6}X(RTP_ISHPR(R,V,P),BD)$(PASTSUM(R,V,P)-FIL2(V)+1 < D(V)) = 0;

* Get hold of the shape and multi index J,JJ for each RVP, as well as start and end years
  LOOP(SAMEAS(J,'1'),
   RTP_SHAPI(RTP_ISHPR(R,V(LL),P),BD,J+MAX(0,{arg1}{arg6}X(R,V,P,BD)-1),J+MAX(0,{arg5}-1),LL+(FIL2(V)+NCAP_ILED(R,V,P)),LL+PASTSUM(R,V,P)) = YES;
  );

  LOOP(SAMEAS(AGE,'1'),
* Calculate average SHAPE for plants still operating in each period:
    {arg4}$(({pass_var})$RTP_ISHPR(R,V,P)) = {arg1}{arg2} *
       SUM(RTP_SHAPI(R,V,P,BD,J,JJ,LL,YEAR), EPS+MULTI(JJ,T) *
         SUM(PERIODYR(T,EOHYEARS)$(YEARVAL(EOHYEARS) LE MAX(B(T),YEARVAL(YEAR))),
             SHAPE(J,AGE+(MIN(YEARVAL(EOHYEARS),YEARVAL(YEAR))-YEARVAL(LL)))) /
         (MAX(1,MIN(E(T),YEARVAL(YEAR))-MAX(B(T),YEARVAL(LL))+1))));

* If no shape index is specified, set the BASE value for the attribute
  RTP_ISHPR(RTP(R,V,P)) = (NOT RTP_ISHPR(RTP));
  {arg4}$(RTP_ISHPR(R,V,P)$({pass_var})) = {arg1}{arg2};
* Clear the temporary sets
  OPTION CLEAR=RTP_SHAPI,CLEAR=RTP_ISHPR,CLEAR=PASTSUM;

""",
        )
