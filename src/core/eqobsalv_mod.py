# eqobsalv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJSALV the objective functions for salvaging
# *   - Investment Costs
# *   - Taxes and subsidies on investments
# *   - Decommissioning
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobsalvMod(GamsClass):
    """Translation unit for eqobsalv.mod."""

    # Instance attributes
    module_name: str = "eqobsalv_mod"
    gams_source: str = "eqobsalv.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str = "",
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.tc.defined("OBJSCC"):
            self._label_prepro()
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
  PARAMETER SALV_DEC(REG,ALLYEAR,PRC,CUR) //;
  PARAMETER OBJSCC(REG,ALLYEAR,PRC,CUR)   //;
  PARAMETER OBJSIC(REG,ALLYEAR,PRC)       //;
  PARAMETER OBJ_DCEOH(REG,CUR)            //;
  SET OBJ_SALI(R,ALLYEAR,P,AGE,YEAR,AGE,ALLYEAR,YEAR) //;
""",
        )

        self._label_prepro()

    def _label_prepro(self) -> None:
        self.env.set_scoped("pft", "")
        if self.env.is_set("TIMESTEP"):
            self.tc.enqueue(self.check_stepped_mode)

        if self.env.stepped == "+" and self.arg1.upper() == "mod":
            self._label_equa(
                arg2=self.arg2,
                eq=self.env.eq,
                sow=self.env.sow,
                vart=self.env.vart,
                validate=self.env.validate,
                etl=self.env.etl,
                sws=self.env.sws,
                varv=self.env.varv,
                var=self.env.var,
            )
            return

        if not self.tc.defined("VNRET") and self.env.ctst != "":
            self.env.set_scoped("pft", "(T)")

        self.tc.enqueue(
            self.salvage_investments,
            self.env.pft,
            self.env.capjd,
            self.env.etl,
            self.env.ctst,
            self.env.declif,
        )

        self._label_equa(
            arg2=self.arg2,
            eq=self.env.eq,
            sow=self.env.sow,
            vart=self.env.vart,
            validate=self.env.validate,
            etl=self.env.etl,
            sws=self.env.sws,
            varv=self.env.varv,
            var=self.env.var,
        )

    def check_stepped_mode(self: EqobsalvMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
    OPTION CLEAR=OBJ_SUMS,CLEAR=OBJ_SUMS3,CLEAR=SALV_INV,CLEAR=OBJSCC;
    """,
        )

    def salvage_investments(
        self: EqobsalvMod, pft: str, capjd: str, etl: str, ctst: str, declif: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Salvaging of Investments; LL is investment year, K is commissioning year
*[UR] 19.12.2003 added -1 in line below, since lifetime starts at the beginning of year K
  OBJ_SALI(OBJ_SUMII(R,V{pft},P,AGE,K_EOH,JOT),K,LL--ORD(LL))$((YEARVAL(K)+NCAP_TLIFE(R,V,P)-1>MIYR_VL)$INVSPRED(K_EOH,JOT,K,LL))=YES;
  OPTION OBJ_SUMSI <= OBJ_SALI, CLEAR=OBJ_SALI;

* No retrofit salvage
  LOOP((RP(R,PRC),P)$PRC_REFIT(RP,P),IF(PRC_REFIT(RP,P)<0, OBJ_SUMSI(R,T,P,K)=NO));
  OPTION OBJ_SUMS <= OBJ_SUMSI;

* Salvaging of Decommissioning
  LOOP(OBJ_SUMIII(OBJ_SUMS(R,V,P),LL,K,Y), OBJ_SUMS3(R,V,P) = YES);
* Salvaging of Decommissioning surveillance
  LOOP(OBJ_SUMIVS(R,V,P,K,Y)$(YEARVAL(K)+NCAP_TLIFE(R,V,P)-1 GT MIYR_VL),
    OBJ_SUMS3(R,V,P) = YES; OBJ_SUMSI(R,V,P,K) = YES);

*===============================================================================
  LOOP(RDCUR(R,CUR),
* Salvage proportion of investments at the commissioning year K:
   SALV_INV(OBJ_SUMSI(R,V,P,K))$OBJ_ICUR(R,V,P,CUR) =
       MIN(1,(((1+G_DRATE(R,V,CUR))*EXP(NCAP_FDR(R,V,P)))**(NCAP_TLIFE(R,V,P)+YEARVAL(K)-MIYR_VL-1)-1) /
             (((1+G_DRATE(R,V,CUR))*EXP(NCAP_FDR(R,V,P)))**NCAP_TLIFE(R,V,P)-1));
  );
* Discount factors for the year EOH+1:
  LOOP(MIYR_1(LL), F = MIYR_VL+1-YEARVAL(MIYR_1); OBJ_DCEOH(RDCUR(R,CUR)) = OBJ_DISC(R,LL+F,CUR));
* Shape-reduced salvage at EOH+1:
  Z = SMAX(T$(B(T)<=MIYR_VL+1),ORD(T)-1);
  LOOP(MIYR_1(T-Z), SALV_INV(OBJ_SUMSI(RTP,K))$NCAP_CPX(RTP) = SALV_INV(RTP,K)*(1+RTP_CPX(RTP,T)));

  OPTION CLEAR = OBJ_SUMSI;
*===============================================================================
* Salvage value of investments at year EOH+1:
* Note that in Cases 2a and 2b investment costs are paid before K
  OBJSCC(OBJ_ICUR(OBJ_SUMS(R,V,P),CUR)) = COR_SALVI(R,V,P,CUR) / OBJ_DCEOH(R,CUR) / OBJ_DIVI(R,V,P) *
    SUM((OBJ_SUMII(R,V,P,AGE,K_EOH,JOT),INVSPRED(K_EOH,JOT,LL,K))$SALV_INV(R,V,P,LL),{capjd}
        (OBJ_ICOST(R,K,P,CUR)+OBJ_ITAX(R,K,P,CUR)-OBJ_ISUB(R,K,P,CUR)) * SALV_INV(R,V,P,LL) * OBJ_DISC(R,K,CUR));
""",
        )

        # Handle ETL in similar fashion
        if etl == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
LOOP((OBJ_SUMS(R,T(V),P),G_RCUR(R,CUR))$SEG(R,P),
  OBJSIC(R,T,P) = COR_SALVI(R,T,P,CUR) / OBJ_DCEOH(R,CUR) / OBJ_DIVI(R,T,P) *
    SUM((OBJ_SUMII(R,V,P,AGE,K_EOH,JOT),INVSPRED(K_EOH,JOT,LL,K)),{capjd} SALV_INV(R,T,P,LL)*OBJ_DISC(R,K,CUR)));
""",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Additional constant term
  OBJ_IAD(RDCUR(R,CUR)) = SUM(OBJ_ICUR(OBJ_SUMS(R,PASTMILE(V),P),CUR)$((OBJ_PASTI(R,V,P,CUR)=0)+0{ctst}),OBJSCC(R,V,P,CUR)*NCAP_PASTI(R,V,P)*OBJ_DCEOH(R,CUR));
*===============================================================================
*GG* only if decommissioning lifetime provided by user
  COR_SALVD(RTP(R,V,P),CUR)$OBJ_DCOST(R,V,P,CUR) =
                   (((1-1/(1+NCAP_DRATE(R,V,P)))*(1-1/(1+OBJ_RFR(R,V,CUR))**NCAP_DELIF(R,V,P)))/
                    ((1-1/(1+OBJ_RFR(R,V,CUR)))*(1-1/(1+NCAP_DRATE(R,V,P))**NCAP_DELIF(R,V,P)))
                    )$(NCAP_DRATE(R,V,P) GT 0) + 1$(NCAP_DRATE(R,V,P) EQ 0);
  OBJ_CRFD(RTP(R,V,P),CUR)$OBJ_DCOST(R,V,P,CUR) = COR_SALVD(R,V,P,CUR) * (1-(1/(1+G_DRATE(R,V,CUR)))) / (1-(1+G_DRATE(R,V,CUR))**(-ROUND(NCAP_{declif}(R,V,P))));
*------------------------------------------------------------------------------
* Salvage value of Decommissioning at year EOH+1:
* Documentation defines the value for each decommissioning year Y; here aggregated by vintage
  SALV_DEC(OBJ_SUMS3(R,V,P),CUR)$COR_SALVD(R,V,P,CUR) = COR_SALVD(R,V,P,CUR) / OBJ_DIVIII(R,V,P) / OBJ_DCEOH(R,CUR) *
      SUM(OBJ_SUMIII(R,V,P,LL,K,Y)$SALV_INV(R,V,P,LL),SALV_INV(R,V,P,LL)*OBJ_DCOST(R,K,P,CUR)*OBJ_DISC(R,Y,CUR));
""",
        )

    def _label_equa(
        self,
        arg2: str,
        eq: str,
        sow: str,
        vart: str,
        validate: str,
        etl: str,
        sws: str,
        varv: str,
        var: str,
    ) -> None:
        if arg2 == "EXIT":
            return

        self.generate_salvage_equation(eq, sow, vart, validate, etl, sws, varv, var)

    def generate_salvage_equation(
        self,
        eq: str,
        sow: str,
        vart: str,
        validate: str,
        etl: str,
        sws: str,
        varv: str,
        var: str,
    ) -> None:
        lhs = rf"    {eq}_OBJSALV(RDCUR(R,CUR) {sow}) .."
        rhs = rf"""
*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in OBJSCC and OBJSIC

      SUM(OBJ_SUMS(R,T,P), OBJSCC(R,T,P,CUR) * {vart}_NCAP(R,T,P {sws})) * OBJ_DCEOH(R,CUR) +
"""
        if validate != "YES":
            rhs += "      SUM(OBJ_SUMS(R,PYR(V),P), OBJSCC(R,V,P,CUR) * NCAP_PASTI(R,V,P)) * OBJ_DCEOH(R,CUR) +"

        if etl == "YES":
            rhs += rf"""      SUM((OBJ_SUMS(R,T,TEG(P)),G_RCUR(R,CUR)), OBJSIC(R,T,P) * {vart}_IC(R,T,P {sws})) * OBJ_DCEOH(R,CUR) +
"""

        if self.tc.defined("VNRET"):
            rhs += "OBSALV"

        rhs += rf"""
*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------
* [AL] Note that discounting to EOH+1 is imbedded in SALV_DEC

      SUM(OBJ_SUMS3(R,T,P), {vart}_NCAP(R,T,P {sws}) * SALV_DEC(R,T,P,CUR)) * OBJ_DCEOH(R,CUR)
      +
* Past investments
      SUM(OBJ_SUMS3(R,PYR,P), NCAP_PASTI(R,PYR,P) * SALV_DEC(R,PYR,P,CUR)) * OBJ_DCEOH(R,CUR)
      +

*------------------------------------------------------------------------------
* Cases IV - Decommissioning Surveillance
*------------------------------------------------------------------------------
* The same proportion SALV_INV is salvaged from investments and surveillance costs
      SUM(OBJ_SUMIVS(R,V,P,K,Y)$SALV_INV(R,V,P,K),
            OBJ_DISC(R,Y,CUR) * OBJ_DLAGC(R,K,P,CUR) * SALV_INV(R,V,P,K) *
            ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)))
      +
*------------------------------------------------------------------------------
* LATE REVENUES
*------------------------------------------------------------------------------
* [AL] LATEREVENUES identical to decommissioning, with DCOST replaced by OCOM*VALU
* Revenues are obtained in the proportion 1-SALV_INV of the total revenues

    SUM((OBJ_SUMIII(R,V,P,LL,K,Y),COM)$((NOT Y_EOH(Y))$NCAP_OCOM(R,V,P,COM)),
        (1-SALV_INV(R,V,P,LL)) * NCAP_VALU(R,K,P,COM,CUR) * OBJ_DISC(R,Y,CUR) *
        ({varv}_NCAP(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V)) *
        NCAP_OCOM(R,V,P,COM) / OBJ_DIVIII(R,V,P))


    =E=

      {var}_OBJ(R,'OBJSAL',CUR {sow});
"""
        equation = lhs + rhs
        self.tc.add_gams_code(module=self, phase="init", code=equation)
