# eqdamage_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * EQDAMAGE.mod - Extension for Linearized/Non-linear Damages
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.filparam_gms import FilparamGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqdamageMod(GamsClass):
    """Translation unit for eqdamage.mod."""

    # Instance attributes
    module_name: str = "eqdamage_mod"
    gams_source: str = "eqdamage.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        if self.arg1 == "E":
            self._label_lpdam()
            return

        if not self.tc.defined("DAM_ELAST"):
            self.tc.add_gams_code(
                module=self, phase="init", code="PARAMETER DAM_ELAST //;"
            )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Internal sets and parameters
  SET JSUBJ(J,J)           'All steps up to J' //;
  SET DAM_NUM(R,C,J,BD);
  SET DAMOBJ / DAM, DAS, DAM-EXT /;
  SET WWDAM /DELTA-ATM/, RTDAM(R,T,C,ALLSOW), SWW(ALLSOW,ALLSOW);
  PARAMETER DAM_SIZE(REG,T,COM,LIM) 'Size of emission steps' //;
""",
        )

        self.tc.enqueue(self.exec1)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                "DAM_TQTY",
                "'R",
                "' C \"",
                "'0'",
                "'0'",
                "'0'",
                "'0'\" DATAYEAR T '' '' '' \"YEAR",
                '"',
            )
        )

        self.tc.enqueue(self.exec2)

        if self.env.CLI == "YES":
            self.tc.enqueue(self.exec3)

        self.tc.enqueue(self.exec4, self.env.STAGES, self.env.SWX, self.env.SWTX)

        self.tc.add_gams_code(module=self, phase="run", code="SET OBV / OBJDAM /;")
        if self.env.DAMAGE == "NO":
            self.tc.enqueue(self.exec5)

        if self.env.VARMAC:
            self.env.set_scoped("VAR", self.env.VAS)

        if self.env.DAMAGE == "NO":
            self._label_finish()
            return

        self.tc.enqueue(
            self.emission_balance_equation,
            self.env.EQ,
            self.env.R_T,
            self.env.SOW,
            self.env.VART,
            self.env.SWX,
            self.env.VAR,
            self.env.CLI,
            self.env.SWS,
        )

        if self.env.DAMAGE == "NLP":
            self._label_nlpdam()
            return

        self._label_lpdam()

    def exec1(self):
        self.tc.add_gams_code(module=self, phase="run", code="OPTION CLEAR=RXX;")

    def exec2(self):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="DAM_TQTY(R,T,C)$(NOT DAM_TQTY(R,T,C)) $= DAM_BQTY(R,C);",
        )

    def exec3(self):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="RTC(R,T,C(CG(CM_VAR)))$((NOT RC(R,C))$DAM_TQTY(R,T,C)) = YES;",
        )

    def exec4(self, STAGES: str, SWX: str, SWTX: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="DAM_COST(R,T,C,CUR)$((DAM_COST(R,T,C,CUR) EQ 0)$DAM_COST(R,T,C,CUR)) = 0;",
        )

        if STAGES.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="OPTION SWW<=SW_TSW; LOOP(SOW,DAM_COST(R,T,C,CUR)$S_DAM_COST(R,T,C,CUR,'1',SOW) = DAM_COST(R,T,C,CUR)+EPS);",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
LOOP(RDCUR(R,CUR), RXX(RTC)$DAM_COST(RTC,CUR) = YES);
  LOOP(T,TRACKC(R,C)$RXX(R,T,C) = YES);
  DAM_TVOC(RXX(R,T,C),BD) $= DAM_VOC(R,C,BD);

  RHS_COMBAL(RTCS_VARC(RXX(R,T,C),S))$(NOT DAM_ELAST(R,C,'N')) = YES;
  RCS_COMBAL(RHS_COMBAL(RXX(R,T,C),S),'FX') = YES;

* If BQTY is zero set VOC to zero to, leading to constant cost
  DAM_TQTY(RXX(R,T,C))$(DAM_TQTY(R,T,C) LE 0) = MAX(0,DAM_TVOC(R,T,C,'LO'));
  DAM_TVOC(RXX(R,T,C),BD)$(NOT DAM_TQTY(R,T,C)) = 0;
  LOOP(T,DAM_ELAST(R,C,BD)$((NOT DAM_TQTY(R,T,C))$RXX(R,T,C)) = 0);
  DAM_STEP(TRACKC(R,C),'FX') = 0; Z = 100;
  DAM_STEP(TRACKC(R,C),BD)$((NOT DAM_STEP(R,C,BD))$DAM_ELAST(R,C,BD)) = 1;
  DAM_STEP(TRACKC(R,C),BD)$DAM_STEP(R,C,BD) = MIN(Z,ABS(ROUND(DAM_STEP(R,C,BD))));

* Ensure that elasticities are greater than or equal to 1:
  DAM_ELAST(TRACKC(R,C),'LO') = ABS(DAM_ELAST(R,C,'UP')$(NOT DAM_ELAST(R,C,'LO'))+DAM_ELAST(R,C,'LO'));
  DAM_ELAST(TRACKC(R,C),'UP') = ABS(DAM_ELAST(R,C,'LO')$(NOT DAM_ELAST(R,C,'UP'))+DAM_ELAST(R,C,'UP'));

* Adjust VOCs
  DAM_TVOC(RXX(R,T,C),BD)$(NOT DAM_TVOC(R,T,C,BD)) $= (DAM_STEP(R,C,BD)+.5)*DAM_VOC(R,C,'N')*DAM_TQTY(R,T,C);
  DAM_TVOC(RXX(R,T,C),'LO') = MIN(DAM_TQTY(R,T,C),DAM_TVOC(R,T,C,'LO')+INF$(NOT DAM_TVOC(R,T,C,'LO')));
  DAM_TVOC(RXX(R,T,C),'UP')$(NOT DAM_TVOC(R,T,C,'UP')) =
    DAM_TVOC(R,T,C,'LO')*(1+((DAM_STEP(R,C,'UP')+0.5)/(DAM_STEP(R,C,'LO')+0.5)-1)$DAM_STEP(R,C,'LO'));

  LOOP(RXX(R,T,C), F = DAM_STEP(R,C,'LO'); Z = DAM_STEP(R,C,'UP');
    FIRST_VAL = DAM_TVOC(R,T,C,'LO'); LAST_VAL = DAM_TVOC(R,T,C,'UP');
    IF(F, DAM_SIZE(R,T,C,'FX') = 2*(FIRST_VAL-(FIRST_VAL*(4*Z+1)-LAST_VAL)/(1+Z*(4+1/F)));
    ELSE  DAM_SIZE(R,T,C,'FX') = FIRST_VAL+0.5*LAST_VAL/(Z+0.5));
  );
  DAM_SIZE(RXX(R,T,C),BDNEQ(BD))$DAM_STEP(R,C,BD) = MAX(0,(DAM_TVOC(R,T,C,BD)-0.5*DAM_SIZE(R,T,C,'FX')))/DAM_STEP(R,C,BD);
  DAM_SIZE(RXX(R,T,C),'UP')$(NOT DAM_STEP(R,C,'LO')) = MAX(0,DAM_TVOC(R,T,C,'UP')/(DAM_STEP(R,C,'UP')+0.5));
  DAM_SIZE(RXX(R,T,C),'N') = DAM_TQTY(R,T,C)-DAM_TVOC(R,T,C,'LO')+0.5*DAM_SIZE(R,T,C,'LO')$DAM_ELAST(R,C,'N');

  DAM_COEF(RTCS_VARC(R,T,C,S))$((NOT DAM_COEF(R,T,C,S))$TRACKC(R,C)) = 1;
  JSUBJ(JJ,J)$((ORD(J) LE ORD(JJ))$(ORD(JJ)<=100)) = YES;
* Set number of FX steps (any non-zero DAM_STEP(R,C,'N') disables endogenous damage)
  DAM_STEP(TRACKC(R,C),'FX')$(DAM_STEP(R,C,'N') EQ 0) = 1+1$SUM(T$(DAM_SIZE(R,T,C,'N') GT 0),YES);
  IF(CARD(DAM_COST)=0,SUM_OBJ('OBJDAM',ITEM)=0);
  RTDAM(RXX(R,T,C){SWX})$({SWTX}YES+WWDAM(C)) = YES;
""",
        )

    def exec5(self):
        self.tc.add_gams_code(
            module=self, phase="run", code="SUM_OBJ('OBJDAM',ITEM)=0;"
        )

    def emission_balance_equation(
        self,
        EQ: str,
        R_T: str,
        SOW: str,
        VART: str,
        SWX: str,
        VAR: str,
        CLI: str,
        SWS: str,
    ):
        equation = rf"""
* Emission balance equation

  {EQ}_DAMAGE(RTC({R_T},C) {SOW})$(SUM(RDCUR(R,CUR)$DAM_COST(R,T,C,CUR),1)$RTDAM(RTC{SWX}))..

   SUM(DAM_NUM(R,C,JJ,BD),SUM(JSUBJ(JJ,J),{VAR}_DAM(R,T,C,BD,J {SOW})))

   =E= (
"""
        if CLI == "YES":
            equation += rf"""
SUM(CM_VAR(C),{VART}_CLITOT(CM_VAR,T{SWS})$CM_KIND(CM_VAR)+{VAR}_CLIBOX(CM_VAR,'ATM',T{SOW})$(NOT CM_KIND(CM_VAR)))$(NOT RC(R,C)) +
   SUM(COM_TS(RC(R,C),S),DAM_COEF(R,T,C,S)*{VAR}_COMNET(R,T,C,S {SOW})$(NOT DAM_ELAST(R,C,'N')) +
                         DAM_COEF(R,T,C,S)*{VAR}_COMPRD(R,T,C,S {SOW})$DAM_ELAST(R,C,'N'))
       )$DAM_STEP(R,C,'FX');
"""
        self.tc.add_gams_code(module=self, phase="run", code=equation)

    def _label_lpdam(self):
        self.tc.enqueue(
            self.damage_cost_equation,
            self.arg2,
            self.arg3,
            self.env.EQ,
            self.env.SOW,
            self.env.STAGES,
            self.env.VAR,
            self.env.SWD,
        )

        self._label_bound()

    def _label_nlpdam(self):
        self.tc.enqueue(
            self.damage_cost_equation_nlp,
            self.arg2,
            self.arg3,
            self.env.EQ,
            self.env.SOW,
            self.env.STAGES,
            self.env.VAR,
            self.env.SWD,
        )
        self._label_bound()

    def _label_bound(self):
        if self.env.DAMAGE == "NLP":
            self._label_bdnlp()
            return

        self.tc.enqueue(
            self.damage_var_bounds,
            self.env.VAR,
            self.env.SWD,
            self.env.SOW,
            self.env.SWX,
        )
        self._label_finish()

    def _label_bdnlp(self):
        self.tc.enqueue(
            self.damage_var_bounds_bdnlp,
            self.env.VAR,
            self.env.SWD,
            self.env.SOW,
            self.env.SWX,
        )
        self._label_finish()

    def _label_finish(self):
        self.tc.enqueue(self.finish)

    def finish(self):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  OPTION CLEAR=TRACKC,CLEAR=RXX,CLEAR=DAM_TVOC;
  DAM_TVOC(R,T,C,'N')$DAM_SIZE(R,T,C,'N') = ((DAM_SIZE(R,T,C,'N')/DAM_TQTY(R,T,C))**DAM_ELAST(R,C,'LO'))$DAM_ELAST(R,C,'N');
""",
        )

    def damage_var_bounds(self, VAR: str, SWD: str, SOW: str, SWX: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
LOOP(SAMEAS(J,'1'),DAM_NUM(TRACKC(R,C),J+(DAM_STEP(R,C,BD)-1),BD) = YES);
  {VAR}_DAM.UP(R,T,C,BD,J {SWD}) = INF;
  {VAR}_DAM.UP(RTC(R,T,C),'LO',J{SOW})$((ORD(J) LE DAM_STEP(R,C,'LO'))$RTDAM(RTC{SWX})) = DAM_SIZE(RTC,'LO');
  {VAR}_DAM.UP(RTC(R,T,C),'LO','1'{SOW})$(DAM_ELAST(R,C,'N')$RTDAM(RTC{SWX})) = DAM_SIZE(RTC,'LO')+DAM_TQTY(RTC)-DAM_TVOC(RTC,'LO');
  {VAR}_DAM.UP(RTC(R,T,C),'UP',J{SOW})$((ORD(J) LT DAM_STEP(R,C,'UP'))$RTDAM(RTC{SWX})) = DAM_SIZE(RTC,'UP');
  {VAR}_DAM.UP(RTC(R,T,C),'FX','1'{SOW})$(DAM_TVOC(RTC,'UP')$RTDAM(RTC{SWX})) = DAM_SIZE(RTC,'FX');
  {VAR}_DAM.UP(RTC(R,T,C),'FX','2'{SOW})$RTDAM(RTC{SWX}) = DAM_SIZE(RTC,'N')$(NOT DAM_ELAST(R,C,'N'));
""",
        )

    def damage_var_bounds_bdnlp(self, VAR: str, SWD: str, SOW: str, SWX: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  DAM_STEP(TRACKC,BDNEQ) = 1;
  LOOP(SAMEAS(J,'1'),DAM_NUM(TRACKC(R,C),J+(DAM_STEP(R,C,BD)-1),BD) = YES);
  {VAR}_DAM.UP(R,T,C,BD,J {SWD}) = INF;
  {VAR}_DAM.UP(RTC(R,T,C),'LO','1'{SOW})$RTDAM(RTC{SWX}) = (DAM_TQTY(RTC)-DAM_SIZE(RTC,'N'))$DAM_STEP(R,C,'LO');
  {VAR}_DAM.UP(RTC(R,T,C),'FX','1'{SOW})$RTDAM(RTC{SWX}) = EPS;
  {VAR}_DAM.UP(RTC(R,T,C),'FX','2'{SOW})$RTDAM(RTC{SWX}) = DAM_SIZE(RTC,'N');
""",
        )

    def damage_cost_equation(
        self, arg2: str, arg3: str, EQ: str, SOW: str, STAGES: str, VAR: str, SWD: str
    ):
        equation = rf"""
{arg2}  {EQ}_OBJDAM(RDCUR(R,CUR){SOW})..
    SUM(RTC(R,T,C)$(DAM_STEP(R,C,'FX')$DAM_COST(R,T,C,CUR)),
"""
        if STAGES.upper() == "YES":
            equation += """
SUM(SWW(SOW,WW)$(SW_TSW(SOW,T,WW)$(NOT WWDAM(C))+SWW(WW,SOW)$WWDAM(C)),
"""

        equation += rf"""
      (SUM((DAM_NUM(R,C,JJ,'LO'),JSUBJ(JJ,J)),
         ({VAR}_DAM(R,T,C,'LO',J{SWD}) + DAM_ELAST(R,C,'N')*{VAR}_DAM.UP(R,T,C,'LO',J{SWD}))*
         ((DAM_TQTY(R,T,C)-DAM_SIZE(R,T,C,'FX')/2-DAM_SIZE(R,T,C,'LO')*(ORD(JJ)-ORD(J)+.5))**DAM_ELAST(R,C,'LO') /
          DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'LO') + DAM_ELAST(R,C,'N')))$DAM_TQTY(R,T,C) +
       {VAR}_DAM(R,T,C,'FX','1'{SWD}) * (1 + DAM_ELAST(R,C,'N')) +
       SUM((DAM_NUM(R,C,JJ,'UP'),JSUBJ(JJ,J)),
         {VAR}_DAM(R,T,C,'UP',J{SWD}) *
         ((DAM_TQTY(R,T,C)+DAM_SIZE(R,T,C,'FX')/2+DAM_SIZE(R,T,C,'UP')*(ORD(J)-.5))**DAM_ELAST(R,C,'UP') /
          DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'UP') + DAM_ELAST(R,C,'N')))$DAM_TQTY(R,T,C)
      ) * OBJ_PVT(R,T,CUR) * S_DAM_COST(R,T,C,CUR,'1',WW))
"""

        if STAGES.upper() != "YES":
            equation += "DAM_COST(R,T,C,CUR)"
        else:
            equation += "  S_DAM_COST(R,T,C,CUR,'1',WW))"

        equation += rf"""
{arg3}  =E=  SUM(OBV,SUM_OBJ('OBJDAM',OBV)*{VAR}_OBJ(R,OBV,CUR {SOW}));
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)

    def damage_cost_equation_nlp(
        self, EQ: str, SOW: str, STAGES: str, VAR: str, SWD: str
    ):
        equation = rf"""
* Damage cost equation
  {EQ}_OBJDAM(RDCUR(R,CUR){SOW})..
    SUM(RTC(R,T,C)$(DAM_STEP(R,C,'FX')$DAM_COST(R,T,C,CUR)),
"""
        if STAGES.upper() == "YES":
            equation += """
SUM(SWW(SOW,WW)$(SW_TSW(SOW,T,WW)$(NOT WWDAM(C))+SWW(WW,SOW)$WWDAM(C)),
"""
        equation += rf"""
      (DAM_TVOC(R,T,C,'N')*({VAR}_DAM(R,T,C,'FX','2'{SWD})+DAM_SIZE(R,T,C,'N')*DAM_ELAST(R,C,'N')) +
       ((({VAR}_DAM(R,T,C,'LO','1'{SWD})+DAM_SIZE(R,T,C,'N'))**(DAM_ELAST(R,C,'LO')+1) +
* Subtract full LO costs if DAM_ELAST(N) = -1 (constant term)
         DAM_ELAST(R,C,'N')*DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'LO')+1) -
         DAM_SIZE(R,T,C,'N')**(DAM_ELAST(R,C,'LO')+1)) /
        (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'LO')*(DAM_ELAST(R,C,'LO')+1)))$DAM_STEP(R,C,'LO') +
       ((({VAR}_DAM(R,T,C,'UP','1'{SWD})+DAM_TQTY(R,T,C))**(DAM_ELAST(R,C,'UP')+1) -
         DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'UP')+1)) /
        (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'UP')*(DAM_ELAST(R,C,'UP')+1))) +
* Shift cost curve by DAM_ELAST(N) if applicable
       DAM_ELAST(R,C,'N')*(SUM(BDNEQ(BD),{VAR}_DAM(R,T,C,BD,'1'{SWD}))+DAM_ELAST(R,C,'N')*DAM_TQTY(R,T,C))
      ) * OBJ_PVT(R,T,CUR) *
"""
        if STAGES.upper() != "YES":
            equation += "DAM_COST(R,T,C,CUR)"
        else:
            equation += "  S_DAM_COST(R,T,C,CUR,'1',WW))"

        equation += rf"""
 =E=  SUM(OBV,SUM_OBJ('OBJDAM',OBV)*{VAR}_OBJ(R,OBV,CUR {SOW}));
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)
