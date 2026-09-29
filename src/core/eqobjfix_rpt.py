# eqobjfix_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJFIX the objective functions capacity fixed costs
# *   arg1 - mod or v# for the source code to be used
# *   - fixed O&M, including surveillance during decommissioning
# *   - fixed taxes and subsidies
# *=============================================================================*

# *------------------------------------------------------------------------------
# * Cases IV - Fixed O&M including surveillance during decommissioning, V - Taxes
# *------------------------------------------------------------------------------
# * Fixed O&M Cost and Taxes

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjfixRpt(GamsClass):
    """Translation unit for eqobjfix.rpt."""

    # Instance attributes
    module_name: str = "eqobjfix_rpt"
    gams_source: str = "eqobjfix.rpt"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.exec1, condition=(self.env.validate == "YES"))

    def exec1(self: EqobjfixRpt, condition: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 LOOP(OBJ_FCUR(NCAP_YES(R,V,P),CUR),

{"F = (VAR_NCAP.L(R,V,P)$T(V)+NCAP_PASTI(R,V,P)$PYR(V)) / OBJ_DIVIV(R,V,P);" if not condition else ""}

* [UR] 07.10.2003: for validating MARKAL using VAR_CAP instead of VAR_NCAP+NCAP_PASTI, since it is possible
*                  in MARKAL to decommission capacity of demand devices (DMD)
{"F = VAR_CAP.L(R,V,P)$(T(V)$(OBJ_1A(R,V,P)+OBJ_1B(R,V,P)))+F$(OBJ_2A(R,V,P)+OBJ_2B(R,V,P));" if condition else ""}

*-------------------------------------------------------------------------------
    OPTION CLEAR=YKAGE;
    LOOP((OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE),INVSTEP(K_EOH,JOT,LL,JOT)),YKAGE(Y_EOH(LL+(ORD(AGE)-1)),LL,AGE)$OPYEAR(LIFE,AGE) = YES;);
*-------------------------------------------------------------------------------

   IF(RTP_ISHPR(R,V,P),
    PAR_OBJFIX(R,V,Y_EOH,P,CUR) =
      OBJ_DISC(R,Y_EOH,CUR) * F * (1+SUM(PERIODYR(T,Y_EOH),RTP_CPX(R,V,P,T))$NCAP_CPX(R,V,P)) *
      SUM(YKAGE(Y_EOH,K,AGE),
             (
                 {macro.obj_fom("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                 {macro.obj_ftx("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
                 {macro.obj_fsb("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
             )
{"              $(PERIODYR(V,Y_EOH)*T(V)+OBJ_2A(R,V,P)+OBJ_2B(R,V,P))" if condition else ""}
      );
   ELSE
    PAR_OBJFIX(R,V,Y_EOH,P,CUR) =
       OBJ_DISC(R,Y_EOH,CUR) * F *
       SUM(YKAGE(Y_EOH,K,AGE), ({macro.obj_fom("R", "K", "P", "CUR")}+{macro.obj_ftx("R", "K", "P", "CUR")}-{macro.obj_fsb("R", "K", "P", "CUR")}));
  ));

* Decommissioning Surveillance
 LOOP(OBJ_FCUR(NCAP_YES(R,V,P),CUR)${macro.obj_dlagc("R", "V", "P", "CUR")},
   OPTION YK1 < OBJ_SUMIVS;
   PAR_OBJFIX(R,V,Y,P,CUR) = PAR_OBJFIX(R,V,Y,P,CUR) +
      SUM(YK1(Y,K), OBJ_DISC(R,Y,CUR) * {macro.obj_dlagc("R", "K", "P", "CUR")} *
          (VAR_NCAP.L(R,V,P)$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)));
  );

 OBJ_C = SUM((R,V,Y,P,CUR)$PAR_OBJFIX(R,V,Y,P,CUR),PAR_OBJFIX(R,V,Y,P,CUR));
 OBJ_D = SUM(RDCUR(R,CUR),SUM(OBV,SUM_OBJ('OBJFIX',OBV)*VAR_OBJ.L(R,OBV,CUR)));
 DISPLAY OBJ_C,OBJ_D;
 """,
        )
