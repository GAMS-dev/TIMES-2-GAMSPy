# equ_ext_ecb.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * equ_ext.ecb - defines equations for the Market Share Mechanism
# *   %1 - mod
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation, Variable

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtEcb(GamsClass):
    """Translation unit for equ_ext.ecb."""

    # Instance attributes
    module_name: str = "equ_ext_ecb"
    gams_source: str = "equ_ext.ecb"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if not self.tc.defined("RTC_MS"):
            return

        self.tc.enqueue(self.exec1, self.env.pgprim, self.env.capjd, self.env.capwd)
        g = self.tc
        m = g.container
        r, c, p, year, item = g.r, g.c, g.p, g.year, g.item

        # Equations
        g.set_equation(
            f"{self.env.eq}_MSNCAP",
            Equation(
                m, name=f"{self.env.eq}_MSNCAP", domain=[r, year, c, *self.env.swd]
            ),
        )
        g.set_equation(
            f"{self.env.eq}_MSNCAPB",
            Equation(
                m, name=f"{self.env.eq}_MSNCAPB", domain=[r, year, c, p, *self.env.swd]
            ),
        )
        g.set_variable(
            f"{self.env.var}_XCAP",
            Variable(
                m,
                name=f"{self.env.var}_XCAP",
                domain=[r, year, item, *self.env.swd],
                type="POSITIVE",
            ),
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
        * Aggregate new capacity market by period
  {self.env.eq}_MSNCAP(RTC_MS({self.env.r_t},C) {self.env.swt})..
* Calculate size of market for new capacity
   SUM(TOP(PRC_CAP(R,P),C,'OUT')$(COEF_LMS(R,T,C,P)$RTP_VARA(R,T,P)),
     PRC_CAPACT(R,P) *
     ({macro.VAR_NCAP(self.env.var, "R", "T", "P", self.env.sow)}$(NOT RTP_OFF(R,T,P)+RVPT(R,T,P,T)) +
      SUM(RVPT(R,V,P,T),{macro.VAR_NCAP(self.env.varv, "R", "V", "P", self.env.sws)}*SQRT(COEF_CPT(R,V,T,P)))))
   =E= {macro.VAR_XCAP(self.env.var, "R", "T", "C", self.env.sow)};

* Maximum share in new capacity market by technology
  {self.env.eq}_MSNCAPB(RTC_MS({self.env.r_t},C),P {self.env.swt})$(RTP_VARA(R,T,P)$PRC_CAP(R,P)$COEF_LMS(R,T,C,P))..
   PRC_CAPACT(R,P) *
   ({macro.VAR_NCAP(self.env.var, "R", "T", "P", self.env.sow)}$(NOT RTP_OFF(R,T,P)+RVPT(R,T,P,T)) +
    SUM(RVPT(R,V,P,T),{macro.VAR_NCAP(self.env.varv, "R", "V", "P", self.env.sws)}*SQRT(COEF_CPT(R,V,T,P))))*SIGN(COEF_LMS(R,T,C,P))
   =L=
*  New capacity market multiplied by logit market share
   {macro.VAR_XCAP(self.env.var, "R", "T", "C", self.env.sow)} * COEF_LMS(R,T,C,P) + SUM(ANNUAL(S),{self.env.var}_FLO(R,T,T,P,'_MSVIOL_',S{self.env.sow}));

*-----------------------------------------------------------------------------
        """,
        )

    def exec1(self, pgprim: str, capjd: str, capwd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
          OPTION RVP < COEF_LMS;
* Calculate ceiling cost coefficients for dummy flow, according to NCAP_MSPRF(UP)
  PASTSUM(RVP(R,T,P)) = NCAP_MSPRF(R,T,'{pgprim}',P,'UP')/PRC_CAPACT(R,P);
  FLO_COST(RVP(R,T,P),C('_MSVIOL_'),ANNUAL(S),CUR)${macro.obj_fcost("R", "T", "P", "C", "S", "CUR")} =
    SUM(OBJ_SUMII(RVP,LIFE,K_EOH,JOT), {capjd} COR_SALVI(RVP,CUR) / OBJ_DIVI(RVP) *
      SUM(INVSPRED(K_EOH,JOT,Y,K), (1-SALV_INV(RVP,Y)$OBJ_SUMS(RVP)) * OBJ_DISC(R,K,CUR) * {macro.obj_icost("R", "K", "P", "CUR")}));
  FLO_DELIV(RVP(R,T,P),C('_MSVIOL_'),ANNUAL(S),CUR)${macro.obj_fdelv("R", "T", "P", "C", "S", "CUR")} =
    SUM(OBJ_SUMIV(K_EOH,RVP,JOT,LIFE),
       SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd} {macro.obj_fom("R", "K", "P", "CUR")}) / OBJ_DIVIV(RVP));
  {macro.obj_fcost("R", "Y_EOH", "P", 'C("_MSVIOL_")', "ANNUAL(S)", "CUR")}${macro.obj_fcost("R", "Y_EOH", "P", "C", "S", "CUR")} = SUM(PERIODYR(T,Y_EOH),FLO_COST(R,T,P,C,S,CUR)*PASTSUM(R,T,P)/OBJ_PVT(R,T,CUR));
  {macro.obj_fdelv("R", "Y_EOH", "P", 'C("_MSVIOL_")', "ANNUAL(S)", "CUR")}${macro.obj_fdelv("R", "Y_EOH", "P", "C", "S", "CUR")} = SUM(PERIODYR(T,Y_EOH),FLO_DELIV(R,T,P,C,S,CUR)*PASTSUM(R,T,P)/OBJ_PVT(R,T,CUR));
  OPTION CLEAR=PASTSUM,CLEAR=RVP;
        """,
        )
