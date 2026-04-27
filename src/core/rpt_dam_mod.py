# rpt_dam_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptDamMod(GamsClass):
    """Translation unit for rpt_dam.mod."""

    # Instance attributes
    module_name: str = "rpt_dam_mod"
    gams_source: str = "rpt_dam.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.env.set_local("swp", "")
        self.env.set_local("sw1", "")
        if self.env.solveda == "1":
            self.env.set_local("swp", "S")
            self.env.set_local("sw1", "'1',")

        if self.env.stages.upper() == "YES":
            self.env.set_local("swp", "S")
            self.env.set_local("sw1", "SOW,")

        self.tc.enqueue(
            self.exec1,
            stages=self.env.stages,
            var=self.env.var,
            cli=self.env.cli,
            swp=self.env.swp,
            vart=self.env.vart,
            sws=self.env.sws,
            sow=self.env.sow,
            sw1=self.env.sw1,
        )

        if self.env.scum == "1":
            self.env.set_local("sw1", "'1',")
            self.tc.add_gams_code(module=self, phase="init", code=self.env.sw_notags)

        self.tc.enqueue(
            self.exec2,
            stages=self.env.stages,
            var=self.env.var,
            swp=self.env.swp,
            sow=self.env.sow,
            sw1=self.env.sw1,
            scum=self.env.scum,
        )

    def exec1(
        self,
        stages: str,
        var: str,
        cli: str,
        swp: str,
        vart: str,
        sws: str,
        sow: str,
        sw1: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{var}_OBJ.M(R,'OBJDAM',CUR {sow})$RDCUR(R,CUR) = 0;
*------------------------------------------------------------------------------
* Always report the accurate non-linear costs
  OPTION CLEAR=RXX; LOOP(RDCUR(R,CUR), RXX(RTC)$DAM_COST(RTC,CUR) = YES);
*------------------------------------------------------------------------------
""",
        )

        # If using climate module, enable damages for total emissions/concentration
        if cli == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
{swp}CST_DAM({sw1}R,T,C(CG(CM_VAR)))$((NOT RC(R,C))$RXX(R,T,C)) =
    {vart}_CLITOT.L(CM_VAR,T{sws})$CM_KIND(CM_VAR)+{var}_CLIBOX.L(CM_VAR,'ATM',T{sow})$(NOT CM_KIND(CM_VAR));
""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
   {swp}CST_DAM({sw1}RXX(R,T,C))$RC(R,C) =
     SUM(COM_TS(R,C,S),DAM_COEF(R,T,C,S) *
       ({vart}_COMNET.L(R,T,C,S{sws})$(NOT DAM_ELAST(R,C,'N'))+{vart}_COMPRD.L(R,T,C,S{sws})$DAM_ELAST(R,C,'N')));
   {swp}DAM_OBJ({sw1}RXX(R,T,C),CUR)$RDCUR(R,CUR) =
    {"DAM_COST(R,T,C,CUR) *" if stages != "YES" else "SUM(SWW(SOW,W)$(SW_TSW(SOW,T,W)$(NOT WWDAM(C))+SWW(W,SOW)$WWDAM(C)),S_DAM_COST(R,T,C,CUR,'1',W)) *"}
    (DAM_TVOC(R,T,C,'N')*(MIN({swp}CST_DAM({sw1}R,T,C),DAM_SIZE(R,T,C,'N'))+DAM_SIZE(R,T,C,'N')*DAM_ELAST(R,C,'N')) +
     ((MIN(DAM_TQTY(R,T,C),{swp}CST_DAM({sw1}R,T,C))**(DAM_ELAST(R,C,'LO')+1) +
* Subtract full LO costs if DAM_ELAST(N) = -1 (constant term)
       DAM_ELAST(R,C,'N')*(DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'LO')+1)-DAM_SIZE(R,T,C,'N')**(DAM_ELAST(R,C,'LO')+1)) -
       MIN(DAM_SIZE(R,T,C,'N'),{swp}CST_DAM({sw1}R,T,C))**(DAM_ELAST(R,C,'LO')+1)) /
      (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'LO')*(DAM_ELAST(R,C,'LO')+1))) +
     (({swp}CST_DAM({sw1}R,T,C)**(DAM_ELAST(R,C,'UP')+1) -
       DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'UP')+1)) /
      (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'UP')*(DAM_ELAST(R,C,'UP')+1)))$({swp}CST_DAM({sw1}R,T,C) GT DAM_TQTY(R,T,C)) +
* Shift cost curve by DAM_ELAST(N) if applicable
     DAM_ELAST(R,C,'N')*({swp}CST_DAM({sw1}R,T,C)+DAM_ELAST(R,C,'N')*DAM_TQTY(R,T,C))
    );
""",
        )

    def exec2(
        self, stages: str, var: str, swp: str, sow: str, sw1: str, scum: str
    ) -> None:
        if scum == "1":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
SDAM_OBJ({sw1}RXX(R,T,C),CUR)$RDCUR(R,CUR) = SUM(W,SW_PROB(W)*SDAM_OBJ(W,R,T,C,CUR));
""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{swp}CST_DAM({sw1}RXX(R,T,C)) = SUM(RDCUR(R,CUR),{swp}DAM_OBJ({sw1}R,T,C,CUR));
  {swp}REG_ACOST({sw1}R,T,'DAM') = SUM(RXX(R,T,C),{swp}CST_DAM({sw1}R,T,C));
  {swp}CST_PVC({sw1}'DAM',R,C)$DAM_STEP(R,C,'FX') = SUM(T,{swp}CST_DAM({sw1}R,T,C)*COEF_PVT(R,T));
* Complete also reporting of discounted costs
  {swp}REG_WOBJ({sw1}R,'DAM',CUR) = SUM(RXX(R,T,C)$((NOT DAM_ELAST(R,C,'N'))$DAM_STEP(R,C,'FX')),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR));
  {swp}REG_WOBJ({sw1}R,'DAS',CUR) = SUM(RXX(R,T,C)$(DAM_ELAST(R,C,'N')$DAM_STEP(R,C,'FX')),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR));
  {swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) = {swp}REG_WOBJ({sw1}R,'DAM',CUR)+{swp}REG_WOBJ({sw1}R,'DAS',CUR);
  {swp}REG_WOBJ({sw1}R,'DAM',CUR) = ({swp}REG_WOBJ({sw1}R,'DAM',CUR)/{swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR)*{var}_OBJ.L(R,'OBJDAM',CUR{sow}))$({swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) GT 0);
  {swp}REG_WOBJ({sw1}R,'DAS',CUR) = {var}_OBJ.L(R,'OBJDAM',CUR{sow}) - {swp}REG_WOBJ({sw1}R,'DAM',CUR);
* Complete also reporting of discounted external damages
  {swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) = SUM(RXX(R,T,C),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR)) - {var}_OBJ.L(R,'OBJDAM',CUR{sow});
""",
        )

        if stages + scum == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="""
REG_WOBJ(R,DAMOBJ,CUR) = SUM(W,SW_PROB(W)*SREG_WOBJ(W,R,DAMOBJ,CUR));
""",
            )
