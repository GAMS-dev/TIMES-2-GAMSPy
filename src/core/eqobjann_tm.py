# eqobjann_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJANN the objective function components for MACRO
# *   - Annualized costs for all components
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.eqobjcst_tm import EqobjcstTm
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjannTm(GamsClass):
    """Translation unit for eqobjann.tm."""

    # Instance attributes
    module_name: str = "eqobjann_tm"
    gams_source: str = "eqobjann.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.tc.defined(f"COEF_OBINV{self.arg1}"):
            self._label_coef()
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  PARAMETER COEF_OBINV{self.arg1}(R,YEAR,P,CUR) //;
  PARAMETER COEF_OBFIX{self.arg1}(R,YEAR,P,CUR) //;
  PARAMETER COEF_CRF(R,ALLYEAR,P,CUR) //;
""",
        )

        if self.arg1 == "N":
            self._label_coef()
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
SET OBVANN(OBV) / OBJINV, OBJFIX, OBJVAR /;
""",
        )

        self.tc.enqueue(self.exec1)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
  POSITIVE VARIABLES VAR_ANNCST(OBV,R,ALLYEAR,CUR);
  EQUATIONS
    EQ_OBJANN(OBVANN,REG,CUR)
    EQ_ANNFIX(REG,ALLYEAR,CUR)
    EQ_ANNINV(REG,ALLYEAR,CUR)
    EQ_ANNVAR(REG,ALLYEAR,CUR);
""",
        )

        self.tc.enqueue(self.exec2)

        self.include(EqobjcstTm(self.tc, self.env))

        self._label_coef()

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
SUM_OBJ(OBV('OBJSAL'),OBV)  =  0;
""",
        )

    def exec2(self) -> None:
        equation = """
  EQ_OBJANN(OBVANN,RDCUR(R,CUR))..
  VAR_OBJ(R,OBVANN,CUR) =E=  SUM(T, OBJ_PVT(R,T,CUR) * VAR_ANNCST(OBVANN,R,T,CUR))
  """
        if self.tc.defined("VNRET"):
            equation += """
  + SUM(OBJ_SUMS(R,V,P)$RVPRL(R,V,P),OBJSCC(R,V,P,CUR)*OBJ_DCEOH(R,CUR)*(VAR_NCAP(R,V,P)$T(V)+NCAP_PASTI(R,V,P)-VAR_SCAP(R,V,'0',P)))$DIAG(OBVANN,'OBJINV')
"""
        equation += ";"
        self.tc.add_gams_code(module=self, phase="run", code=equation)

    def exec3(self, arg1: str, capjd: str, arg2: str, anncost: str, capwd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 Calculate coefficients for annualized costs
* Investment costs: Commissioning years
  OPTION CLEAR=OBJ_SUMSI;
  FIL2(V) = B(V)-YEARVAL(V);
  OBJ_SUMSI(RTP(R,V(LL),P),LL+(FIL2(V)+NCAP_ILED(R,V,P))) = YES;

* Annualizing coefficient for investment costs over years of capacity transfer
  COEF_CRF(OBJ_ICUR(R,V,P,CUR)) =
    SUM(RTP_CPTYR(R,TT(V),T,P),COEF_CPT(R,V,T,P)*OBJ_PVT(R,T,CUR)) +
    SUM(OBJ_SUMSI(R,PASTMILE(V),P,K),OBJ_DISC(R,K,CUR)*(1-(1+G_DRATE(R,V,CUR))**(-NCAP_TLIFE(R,V,P)))/(1-(1/(1+G_DRATE(R,V,CUR)))));

* Investment cost coefficient

  COEF_OBINV{arg1}(OBJ_ICUR(R,V,P,CUR)) = (1/COEF_CRF(R,V,P,CUR))$COEF_CRF(R,V,P,CUR) * (

* Cases I - Investment Cost and II - Taxes/Subsidies

    SUM(OBJ_SUMII(R,V,P,LIFE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_DISC(R,K,CUR) * (1-SALV_INV(R,V,P,LL)$T(V)) *
        ({macro.obj_icost("R", "K", "P", "CUR")} + ({macro.obj_itax("R", "K", "P", "CUR")} - {macro.obj_isub("R", "K", "P", "CUR")}){arg2})) *
      COR_SALVI(R,V,P,CUR) / OBJ_DIVI(R,V,P))
       +
* Cases III - Decommissioning

    SUM(OBJ_SUMIII(R,V,P,LL,K,Y)${macro.obj_dcost("R", "V", "P", "CUR")},
      OBJ_DISC(R,Y,CUR) * COR_SALVD(R,V,P,CUR) * {macro.obj_dcost("R", "K", "P", "CUR")} / OBJ_DIVIII(R,V,P))
  );

  COEF_OBINV{arg1}(OBJ_ICUR(R,PASTMILE(V),P,CUR))$PRC_RESID(R,'0',P) =
      OBJ_CRF(R,V,P,CUR)*({macro.obj_icost("R", "V", "P", "CUR")}+({macro.obj_itax("R", "V", "P", "CUR")}-{macro.obj_isub("R", "V", "P", "CUR")}){arg2});

*------------------------------------------------------------------------------
* Fixed costs: Annualizing coefficient for costs over years of capacity transfer
  COEF_CRF(OBJ_FCUR(R,V,P,CUR)) = SUM(RTP_CPTYR(R,V,T,P),COEF_CPT(R,V,T,P)*OBJ_PVT(R,T,CUR));
""",
        )

        if anncost.upper() != "LEV":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="""
COEF_CRF(OBJ_FCUR(R,PASTMILE(V),P,CUR)) = SUM(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE),OBJ_LIFE(K_EOH,R,JOT,LIFE,CUR));
""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Fixed cost coefficient

  COEF_OBFIX{arg1}(OBJ_FCUR(R,V,P,CUR)) = (1/COEF_CRF(R,V,P,CUR))$COEF_CRF(R,V,P,CUR) * (

* Case IV - Fixed O&M Cost and Taxes

      SUM(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE)$(NOT RTP_ISHPR(R,V,P)),
       SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd}
        ({macro.obj_fom("R", "K", "P", "CUR")}+({macro.obj_ftx("R", "K", "P", "CUR")}-{macro.obj_fsb("R", "K", "P", "CUR")}){arg2})) / OBJ_DIVIV(R,V,P)) +

      SUM(OBJ_SUMIV(K_EOH,RTP_ISHPR(R,V,P),JOT,LIFE),
        SUM((INVSPRED(K_EOH,JOT,LL,K),OPYEAR(LIFE,AGE),Y_EOH(LL+(ORD(AGE)-1))),
             OBJ_DISC(R,Y_EOH,CUR) * (1+SUM(PERIODYR(T,Y_EOH),RTP_CPX(R,V,P,T))$NCAP_CPX(R,V,P)) * {capwd}
                (
                   {macro.obj_fom("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                   {macro.obj_ftx("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)){arg2} -
                   {macro.obj_fsb("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)){arg2}
                )
           ) / OBJ_DIVIV(R,V,P)
         ) +

* Case V - Decommissioning Surveillance
      SUM(OBJ_SUMIVS(R,V,P,K,Y), OBJ_DISC(R,Y,CUR) * {macro.obj_dlagc("R", "K", "P", "CUR")})
  );

  COEF_OBFIX{arg1}(OBJ_FCUR(R,PASTMILE(V),P,CUR))$PRC_RESID(R,'0',P) =
     COEF_OBFIX{arg1}(R,V,P,CUR) * COEF_CRF(R,V,P,CUR) /
     SUM(VNT(V,T)$PRC_RESID(R,T,P),PRC_RESID(R,T,P)/NCAP_PASTI(R,V,P)*OBJ_PVT(R,T,CUR));
*===============================================================================
  OPTION CLEAR=OBJ_SUMSI,CLEAR=COEF_CRF;
""",
        )

    def _label_coef(self) -> None:
        self.tc.enqueue(
            self.exec3,
            arg1=self.arg1,
            capjd=self.env.capjd,
            arg2=self.arg2,
            anncost=self.env.anncost,
            capwd=self.env.capwd,
        )
