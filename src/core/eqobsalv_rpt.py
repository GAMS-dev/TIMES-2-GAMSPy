# eqobsalv_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJSALV the objective functions for salvaging
# *   - Investment Costs
# *   - Taxes and subsidies on investments
# *   - Decommissioning
# *=============================================================================*
# *
# *==============================================================================
# * Generate Investment equation summing over all active indexes by region and currency
# *==============================================================================
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobsalvRpt(GamsClass):
    """Translation unit for eqobsalv.rpt."""

    # Instance attributes
    module_name: str = "eqobsalv_rpt"
    gams_source: str = "eqobsalv.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str = ""
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.exec1, etl=self.env.etl)

        g = self.tc
        m = g.container
        g.par_objcap = Parameter(
            m, name="PAR_OBJCAP", domain=[g.r, g.year, g.prc, g.cur]
        )
        g.coef_objinv = Parameter(m, name="COEF_OBJINV", domain=[g.r, g.year, g.prc])

        self.tc.enqueue(self.exec2, capjd=self.env.capjd)

    def exec1(self, etl: str) -> None:
        lhs = "PAR_OBJSAL(RTP(R,V,P),CUR)$RDCUR(R,CUR) ="
        rhs = """
*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in OBJSCC and OBJSIC

      SUM(OBJ_SUMS(R,T(V),P),   OBJSCC(R,T,P,CUR) * VAR_NCAP.L(R,T,P)) * OBJ_DCEOH(R,CUR) +
      SUM(OBJ_SUMS(R,PYR(V),P), OBJSCC(R,V,P,CUR) * NCAP_PASTI(R,V,P)) * OBJ_DCEOH(R,CUR) +
"""
        if etl == "YES":
            rhs += "      SUM(OBJ_SUMS(R,T(V),P)$TEG(P), OBJSIC(R,T,P) * VAR_IC.L(R,T,P)) * OBJ_DCEOH(R,CUR) +"

        rhs += f"""
*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in SALV_DEC

      SUM(OBJ_SUMS3(R,T(V),P),   VAR_NCAP.L(R,T,P) * SALV_DEC(R,T,P,CUR)) * OBJ_DCEOH(R,CUR) +
      SUM(OBJ_SUMS3(R,PYR(V),P), NCAP_PASTI(R,V,P) * SALV_DEC(R,V,P,CUR)) * OBJ_DCEOH(R,CUR) +

*------------------------------------------------------------------------------
* Cases IV - Decommissioning Surveillance
*------------------------------------------------------------------------------
* The same proportion SALV_INV is salvaged from investments and surveillance costs
      SUM(OBJ_SUMIVS(R,T(V),P,K,Y)$SALV_INV(R,T,P,K),
          OBJ_DISC(R,Y,CUR) * {macro.obj_dlagc("R", "K", "P", "CUR")} * SALV_INV(R,T,P,K) * VAR_NCAP.L(R,T,P)) +

      SUM(OBJ_SUMIVS(R,PYR(V),P,K,Y)$SALV_INV(R,V,P,K),
          OBJ_DISC(R,Y,CUR) * {macro.obj_dlagc("R", "K", "P", "CUR")} * SALV_INV(R,V,P,K) * NCAP_PASTI(R,V,P))
    ;

*------------------------------------------------------------------------------
* LATE REVENUES
*------------------------------------------------------------------------------
* [AL] LATEREVENUES identical to decommissioning, with DCOST replaced by OCOM*VALU
* Revenues are obtained in the proportion 1-SALV_INV of the total revenues

  PAR_OBJLAT(R,Y,P,CUR)$(YEARVAL(Y) GT MIYR_VL) =
    SUM((OBJ_SUMIII(R,V,P,LL,K,Y),COM)$(NCAP_OCOM(R,V,P,COM)*NCAP_VALU(R,K,P,COM,CUR)),
        (1-SALV_INV(R,V,P,LL)) *
        OBJ_DISC(R,Y,CUR) * (VAR_NCAP.L(R,V,P)$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)) *
        NCAP_VALU(R,K,P,COM,CUR) * NCAP_OCOM(R,V,P,COM) / OBJ_DIVIII(R,V,P))
     ;
"""

        self.tc.add_gams_code(module=self, phase="run", code=lhs + rhs)

    def exec2(self, capjd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Calculate the effect of a one unit of investment costs to the objective.
* The average undiscounted investment cost equivalent to the reduced cost can be
* calculated for each period by dividing the reduced cost by COEF_OBJINV
  OPTION CLEAR=PAR_OBJCAP;
  PAR_OBJCAP(OBJ_ICUR(R,T,P,CUR)) = COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) *
    SUM(OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,Y,K), (1-SALV_INV(R,T,P,Y)$OBJ_SUMS(R,T,P)) * OBJ_DISC(R,K,CUR)));
  COEF_OBJINV(RTP(R,T,P)) $= SUM(RDCUR(R,CUR),PAR_OBJCAP(RTP,CUR));

OPTION CLEAR=OBJ_SUMIV, CLEAR=OBJ_SUMIVS, CLEAR=OBJ_SUMIII;
OPTION CLEAR=OBJ_DIVI,  CLEAR=OBJ_DIVIV,  CLEAR=OBJ_DIVIII;
""",
        )
