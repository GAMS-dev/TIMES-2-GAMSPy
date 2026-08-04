# coef_alt_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_ALT.LIN do coefficient calculations for the linearized objective       *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefAltLin(GamsClass):
    """Translation unit for coef_alt.lin."""

    # Instance attributes
    module_name: str = "coef_alt_lin"
    gams_source: str = "coef_alt.lin"

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
        g = self.tc
        m = g.container

        if not self.tc.defined("TPULSE"):
            g.Perdinv = Set(m, name="PERDINV", domain=[g.allyear, g.allyear])
            g.Tpulseyr = Set(m, name="TPULSEYR", domain=[g.t, g.allyear])
            g.tpulse = Parameter(m, name="TPULSE", domain=[g.allyear, g.allyear])
            g.obj_lint = Parameter(
                m, name="OBJ_LINT", domain=[g.r, g.t, g.allyear, g.cur]
            )
            g.obj_altv = Parameter(m, name="OBJ_ALTV", domain=[g.r, g.t])
            g.rtp_capvl = Parameter(m, name="RTP_CAPVL", domain=[g.r, g.year, g.p])
            g.rb = Parameter(m, name="RB", domain=[g.r, g.t])
            g.r_df = Parameter(m, name="R_DF", domain=[g.r, g.allyear])
            g.obj_wd = Parameter(
                m, name="OBJ_WD", domain=[g.Reg, g.cur, g.allyear, g.age, g.allyear]
            )
            g.obj_jd = Parameter(
                m, name="OBJ_JD", domain=[g.Reg, g.cur, g.allyear, g.age]
            )

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
    SET PERDINV(ALLYEAR,ALLYEAR);
    SET TPULSEYR(T,ALLYEAR);
    PARAMETER TPULSE(ALLYEAR,ALLYEAR);
    PARAMETER OBJ_LINT(R,T,ALLYEAR,CUR);
    PARAMETER OBJ_ALTV(R,T);
    PARAMETER RTP_CAPVL(R,YEAR,P) //;
    PARAMETER RB(R,T);
    PARAMETER R_DF(R,ALLYEAR);
    PARAMETER OBJ_WD(REG,CUR,ALLYEAR,AGE,ALLYEAR);
    PARAMETER OBJ_JD(REG,CUR,ALLYEAR,AGE);
    """,
            )
        self._label_prepro()

    def _label_prepro(self) -> None:
        arg1 = self.arg1.upper()

        if arg1 == "FIX":
            self._label_dofix()
            return
        elif arg1 == "INV":
            self._label_doinv()
            return
        elif arg1 == "STP":
            self.tc.enqueue(self.exec1)

        self.env.set_scoped("iled", "$NCAP_ILED(R,V,P)")
        self.tc.enqueue(self.pre_establish_perdinv)

        # Complete OBJ_PVT and FPD:
        self.env.set_scoped("linflo", "0")
        self.env.set_scoped("linacc", "0")

        if self.env.obj.upper() == "LIN":
            self.env.set_scoped("linacc", "1")
        if self.env.ctst.upper() == "**EPS":
            self.env.set_scoped("linflo", "1")
        if f"{self.env.oblong}{self.env.obj}".upper() == "YESALT":
            self.env.set_scoped("varcost", "LIN")
            self.env.set_scoped("linacc", "1")
        if f"{self.env.oblong}{self.env.linflo}".upper() == "YES1":
            self.env.set_scoped("iled", "")

        self.tc.enqueue(self._complete_obj_pvt_and_fpd, linflo=self.env.linflo)

        self.tc.enqueue(
            self._prepare_linearized_cost_coeffs,
            obj=self.env.obj,
            linacc=self.env.linacc,
        )

        if arg1.upper() == "VAR":
            return

        self._label_cpt()

    def pre_establish_perdinv(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Pre-establish PERDINV (for T)
  PERDINV(YK(T,K))$(YEARVAL(K) > M(T)-LEAD(T)) = YES;
  OPTION CLEAR=YK1; YK1(T,Y_EOH)$(YEARVAL(T)<=YEARVAL(Y_EOH)) = YES;
* Initialize period pulse years and triangular functions
  TPULSEYR(PERDINV(T,Y_EOH)) = YES;
  TPULSE(TPULSEYR(T,Y_EOH)) = 1-((M(T)-YEARVAL(Y_EOH))/LEAD(T))$(NOT MIYR_1(T));
  TPULSEYR(YK1(T,Y_EOH))$(YEARVAL(Y_EOH) < M(T)+LAGT(T)) = YES;
  TPULSE(TPULSEYR(YK1(T,LL))) = 1-TPULSE(T+1,LL);
""",
        )

    def exec1(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION CLEAR=PERDINV,CLEAR=TPULSE,CLEAR=TPULSEYR;",
        )

    def exec2(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
INVSPRED(LL,JOT,K,K)$((NOT KAGE(LL,JOT))$INVSTEP(LL,JOT,K,JOT)) = YES;
INVSPRED(KAGE(LL,JOT),LL+FLOOR(ORD(JOT)/2),K)$INVSTEP(LL,JOT,K,JOT) = YES;
OBJ_JD(RDCUR(R,CUR),KAGE(LL,JOT)) = ORD(JOT)/SUM(INVSPRED(LL,JOT,YEAR,K),OBJ_DISC(R,K,CUR)/OBJ_DISC(R,YEAR,CUR));
""",
        )

    def exec3(self) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="OPTION CLEAR=INVSTEP;")

    def exec4(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OBJ_WD(RDCUR(R,CUR),LL,JOT,K)$((NOT KAGE(LL,JOT))$INVSTEP(LL,JOT,K,JOT)) = 1;
OBJ_WD(RDCUR(R,CUR),KAGE(LL,JOT),K) $= SUM(INVSPRED(LL,JOT,YEAR,K),OBJ_DISC(R,K,CUR)/OBJ_DISC(R,YEAR,CUR))*OBJ_JD(R,CUR,LL,JOT);
OPTION CLEAR=KAGE;
""",
        )

    def exec5(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OBJ_DIVIV(OBJ_YES(R,PASTMILE,P)) = 1;
OBJ_DIVIV(OBJ_YES(R,T,P)) = MAX(1,MIN(IPD(T),ROUND(NCAP_TLIFE(R,T,P)))$(OBJ_1B(R,T,P)+OBJ_1A(R,T,P)));
OBJ_DIVIV(OBJ_YES(R,T,P))$RTP_CAPVL(R,T,P) = OBJ_DIVIV(R,T,P) / (1+RTP_CAPVL(R,T,P));
""",
        )

    def exec6(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
LOOP(PYR_S(V),
LOOP((OBJ_SUMIV(V,R,V,P,JOT,LIFE),G_RCUR(R,CUR))$PRC_RESID(R,'0',P),
    OBJ_DIVIV(R,V,P) = NCAP_PASTI(R,V,P)*OBJ_LIFE(V,R,JOT,LIFE,CUR)/SUM(VNT(V,T)$PRC_RESID(R,T,P),PRC_RESID(R,T,P)*OBJ_PVT(R,T,CUR))));
""",
        )

    def exec7(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
LOOP(G_RCUR(R,CUR),
    FIL2(T) = R_DF(R,T);
    PASTSUM(RTP(R,Y_EOH(T),P))$((NOT NCAP_ILED(R,T,P))$PRC_CAP(R,P)) = (FIL2(T)**(RB(R,T)-B(T))-1) / (1-FIL2(T)**MIN(MIYR_VL+1-B(T),COEF_RPTI(R,T,P)*NCAP_TLIFE(R,T,P))));
RTP_CAPVL(R,T,P)$PASTSUM(R,T,P) = (1+RTP_CAPVL(R,T,P)) / (1+PASTSUM(R,T,P)) - 1;
""",
        )

    def exec8(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  OBJ_JD(RDCUR(R,CUR),K,JOT)$KAGE(K,JOT) = 1;
* The equation divisors for investments:
  OBJ_DIVI(OBJ_YES(R,V,P))$(NOT OBJ_I2(R,V,P)) = 1+MIN(IPD(V)-1,ROUND(NCAP_TLIFE(R,V,P))-1)$T(V);
  OBJ_DIVI(OBJ_YES(OBJ_1B(R,T,P)))$(ROUND(NCAP_TLIFE(R,T,P)) EQ 1) = NCAP_TLIFE(R,T,P);
  OBJ_DIVI(OBJ_YES(R,T,P))$RTP_CAPVL(R,T,P) = OBJ_DIVI(R,T,P) / (1+RTP_CAPVL(R,T,P));
* The equation divisors for decommissioning :
  OBJ_DIVIII(OBJ_SUMS3(R,V,P)) = OBJ_DIVI(R,V,P);
  OBJ_DIVIII(OBJ_SUMS3(OBJ_I2(R,V,P))) = ROUND(NCAP_DLIFE(R,V,P));
* Pastmile investments
  OBJ_CRFD(R,PASTMILE(V),P,CUR)$OBJ_PASTI(R,V,P,CUR) = SUM(OBJ_SUMII(R,V,P,LIFE,K,JOT),NCAP_PASTI(R,V,P)*OBJ_CRF(R,V,P,CUR)/OBJ_DISC(R,K,CUR));
  OBJ_PASTI(R,PASTMILE(V),P,CUR)$OBJ_CRFD(R,V,P,CUR) = SUM(VNT(V,T),COEF_CPT(R,V,T,P)*OBJ_PVT(R,T,CUR))*OBJ_CRFD(R,V,P,CUR)/COR_SALVI(R,V,P,CUR);
  OPTION CLEAR=OBJ_CRFD;
""",
        )

    def exec9(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  OBJ_DIVI(RTP(R,T,P)) = STP_DIV('1',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIV(RTP(R,T,P)) = STP_DIV('2',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIII(RTP(R,T,P)) = STP_DIV('3',R,T,P)*(1+RTP_CAPVL(R,T,P));
""",
        )

    def exec10(self) -> None:
        self.tc.add_gams_code(
            module=self, phase="run", code="OPTION CLEAR=PASTSUM,CLEAR=YK1;"
        )

    def _complete_obj_pvt_and_fpd(self, linflo: str) -> None:
        if linflo == "1":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="""
FPD(T) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH));
OBJ_PVT(R,T,CUR)$RDCUR(R,CUR) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)); COEF_PVT(R,T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR));
""",
            )
        if linflo == "1":
            loop_body = "OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR));"
        elif linflo == "0":
            loop_body = "OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
        else:
            raise Exception(linflo, "None of [0,1]")

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(ABS(ALTOBJ) EQ 2, LOOP(G_RCUR(R,CUR),
* Set up variable cost correction adjustment for ALT
{loop_body}
  ));""",
        )

    def _prepare_linearized_cost_coeffs(self, obj: str, linacc: str) -> None:
        param_definition = "OBJ_LINT(R,T,TT,CUR)$RDCUR(R,CUR) ="
        if obj.upper() == "ALT":
            param_definition += "  OBJ_ALTV(R,T) *"

        if linacc.upper() == "1":
            param_definition += "  SUM(TPULSEYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(T,Y_EOH)*TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
        elif linacc.upper() == "0":
            param_definition += "  SUM(PERIODYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"

        self.tc.add_gams_code(module=self, phase="run", code=param_definition)

    def _label_cpt(self) -> None:
        if self.arg1.upper() == "STP":
            self._label_stp()
            return

        linflo, iled, oblong = self.env.linflo, self.env.iled, self.env.oblong
        self.tc.enqueue(self._square_objective_formulation, linflo, iled, oblong)

    def _square_objective_formulation(
        self, linflo: str, iled: str, oblong: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
PASTSUM(RTP(R,V,P))$PRC_CAP(R,P) = B(V)+NCAP_ILED(R,V,P)+COEF_RPTI(R,V,P)*NCAP_TLIFE(R,V,P);
OPTION CLEAR=FIL2,CLEAR=MY_ARRAY,CLEAR=YK1;
LOOP(G_RCUR(R,CUR), R_DF(R,V) = 1/(1+G_DRATE(R,V,CUR)));
IF(INT_DEFAULT('PASTI'),
NCAP_ILED(R,PHYR(V),P)$(NCAP_ILED(R,V,P)>COEF_ILED(R,V,P)) = LOG(1-(1-R_DF(R,V))*(NCAP_ILED(R,V,P)-COEF_ILED(R,V,P)))/LOG(R_DF(R,V)));
RB(R,T) = B(T);
""",
        )

        if linflo == "1":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="YK1(T(LL),LL-FLOOR((LEAD(T)-1)/2)) = NOT MIYR_1(T);",
            )

        loop = """
LOOP(G_RCUR(R,CUR),
    FIL2(T) = R_DF(R,T);
"""
        if linflo == "1":
            loop += "  LOOP(YK1(T,YEAR), Z=OBJ_DISC(R,YEAR,CUR)/SUM(PERDINV(T,LL),OBJ_DISC(R,LL,CUR))*LEAD(T); RB(R,T)=B(T)-LOG(Z)/LOG(FIL2(T)));"

        loop += rf"""  MY_ARRAY(T) = E(T)+1; MY_ARRAY(TT(T-1)) = RB(R,T);
    MY_ARRAY(T) = 1-FIL2(T)**(MY_ARRAY(T)-RB(R,T)-1e-8);
    COEF_CPT(RTP_CPTYR(R,V,T,P))$PASTSUM(R,V,P) =
      MIN(1,(1-FIL2(T)**(PASTSUM(R,V,P)-RB(R,T)))/MY_ARRAY(T)) - ((1-FIL2(T)**MAX(0,B(V)+NCAP_ILED(R,V,P)-RB(R,T))) / MY_ARRAY(T)){iled});"""

        self.tc.add_gams_code(module=self, phase="run", code=loop)
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="COEF_CPT(R,T,TT,P)$((COEF_CPT(R,T,TT,P) LT 1/512)$COEF_CPT(R,T,TT,P)) = 0;",
        )

        if oblong.upper() == "YES" or self.env.is_set("timestep"):
            self._label_done()
            return

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Calculate additional cost due to trapezoidal periods
  PASTSUM(R,T,P)$NCAP_ILED(R,T,P) = NO;
  LOOP(G_RCUR(R,CUR),
    FIL2(T) = R_DF(R,T);
    RTP_CAPVL(R,T,P)$PASTSUM(R,T,P) = (FIL2(T)**(RB(R,T)-B(T))-1) / (1-FIL2(T)**(MIN(MIYR_VL+1,PASTSUM(R,T,P))-B(T))));
""",
        )
        self._label_done()

    def _label_dofix(self) -> None:
        self.env.set_global("capwd", "OBJ_WD(R,CUR,K_EOH,JOT,K)*")

        self.tc.enqueue(self.exec11)

        # Convert INVSTEP to INVSPRED
        self.tc.enqueue(self.exec2)

        if not self.arg2:
            self.tc.enqueue(self.exec3)
            return

        self.tc.enqueue(self.exec4)
        self.tc.enqueue(self.exec5)

        if not self.tc.defined("PRC_RESID"):
            return

        self.tc.enqueue(self.exec6)

    def exec11(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OPTION CLEAR=FIL; FIL(LL+(B(LL)-YEARVAL(LL)))$T(LL) = YES;
OPTION CLEAR=KAGE; KAGE(K,JOT)$((NOT FIL(K))$INVSTEP(K,JOT,K,JOT)) = YES;
KAGE(FIL(LL-FLOOR(ORD(JOT)/2)),JOT)$((ORD(JOT) GT 1)$INVSTEP(FIL,JOT,FIL,JOT)$FIL(LL)) = YES;
""",
        )

    def _calculate_change_in_capacity(self, iled: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Adjustments to Divisors when trapezoidal periods
* Calculate change in capacity value due to change in last period
  OPTION CLEAR=RTP_CAPVL;
  LOOP(T$(E(T) EQ MIYR_VL),
   PASTSUM(RTP(R,TT,P))$((COEF_CPT(R,TT,T,P) GT 0)$PRC_CAP(R,P)) = B(TT)+NCAP_ILED(R,TT,P)+COEF_RPTI(R,TT,P)*NCAP_TLIFE(R,TT,P);
   LOOP(G_RCUR(R,CUR), F = RB(R,T);
    MY_F = R_DF(R,T); Z = 1-MY_F**(MIYR_VL-F+1);
    RTP_CAPVL(R,TT(V),P)$PASTSUM(R,V,P) = COEF_PVT(R,T) *
      ((MIN(Z, 1-MY_F**(PASTSUM(R,V,P)-F)) - (1-MY_F**MAX(0,B(V)+NCAP_ILED(R,V,P)-F)){iled}) / Z - COEF_CPT(R,V,T,P))));
  RTP_CAPVL(R,TT,P)$RTP_CAPVL(R,TT,P) = RTP_CAPVL(R,TT,P)/SUM(VNT(TT,Y_EOH(T)),COEF_PVT(R,T)*MAX(0,COEF_CPT(R,TT,T,P)));
  OPTION CLEAR=PASTSUM;
""",
        )

    def _label_stp(self) -> None:
        if self.env.linflo != "1":
            self.tc.enqueue(self._label_done)
            return

        self.tc.enqueue(self._calculate_change_in_capacity, iled=self.env.iled)

        if self.env.oblong.upper() == "YES":
            self._label_update()
            self.tc.enqueue(self._label_done)
            return

        self.tc.enqueue(self.exec7)
        self._label_update()
        self.tc.enqueue(self._label_done)

    def _label_doinv(self) -> None:
        self.env.set_global("capjd", "OBJ_JD(R,CUR,K_EOH,JOT)*")
        self.tc.enqueue(self.exec8)
        self._label_dofix()

    def _label_update(self) -> None:
        self.tc.enqueue(self.exec9)
        self.tc.enqueue(self._label_done)

    def _label_done(self) -> None:
        self.exec10()


def coef_alt_lin_stp(
    *,
    obj: str,
    ctst: str,
    oblong: str,
) -> str:
    linflo = ctst.upper() == "**EPS"
    linacc = obj.upper() == "LIN"
    obj_is_alt = obj.upper() == "ALT"

    if f"{oblong}{obj}".upper() == "YESALT":
        linacc = True

    iled = "$NCAP_ILED(R,V,P)"
    if f"{oblong}{int(linflo)}".upper() == "YES1":
        iled = ""

    # ---- blocks ----

    fpd_block = ""
    if linflo:
        fpd_block = """
  FPD(T) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH));
  OBJ_PVT(R,T,CUR)$RDCUR(R,CUR) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)); COEF_PVT(R,T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR));
"""

    altv_block = (
        """
  OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR));
"""
        if linflo
        else """
  OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));
"""
    )

    lint_expr = (
        "  SUM(TPULSEYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(T,Y_EOH)*TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
        if linacc
        else "  SUM(PERIODYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
    )

    trapezoid_block = ""
    if linflo:
        extra_block = ""
        if oblong.upper() != "YES":
            extra_block = """
* Calculate additional cost due to trapezoidal periods
  LOOP(G_RCUR(R,CUR),
    FIL2(T) = R_DF(R,T);
    PASTSUM(RTP(R,Y_EOH(T),P))$((NOT NCAP_ILED(R,T,P))$PRC_CAP(R,P)) =
      (FIL2(T)**(RB(R,T)-B(T))-1) /
      (1-FIL2(T)**MIN(MIYR_VL+1-B(T),COEF_RPTI(R,T,P)*NCAP_TLIFE(R,T,P))));
  RTP_CAPVL(R,T,P)$PASTSUM(R,T,P) =
      (1+RTP_CAPVL(R,T,P)) / (1+PASTSUM(R,T,P)) - 1;
"""

        trapezoid_block = rf"""
* Adjustments to Divisors when trapezoidal periods
  OPTION CLEAR=RTP_CAPVL;
  LOOP(T$(E(T) EQ MIYR_VL),
   PASTSUM(RTP(R,TT,P))$((COEF_CPT(R,TT,T,P) GT 0)$PRC_CAP(R,P)) =
       B(TT)+NCAP_ILED(R,TT,P)+COEF_RPTI(R,TT,P)*NCAP_TLIFE(R,TT,P);
   LOOP(G_RCUR(R,CUR), F = RB(R,T);
    MY_F = R_DF(R,T); Z = 1-MY_F**(MIYR_VL-F+1);
    RTP_CAPVL(R,TT(V),P)$PASTSUM(R,V,P) =
      COEF_PVT(R,T) *
      ((MIN(Z, 1-MY_F**(PASTSUM(R,V,P)-F))
        - (1-MY_F**MAX(0,B(V)+NCAP_ILED(R,V,P)-F)){iled}) / Z
        - COEF_CPT(R,V,T,P))));
  RTP_CAPVL(R,TT,P)$RTP_CAPVL(R,TT,P) =
      RTP_CAPVL(R,TT,P) /
      SUM(VNT(TT,Y_EOH(T)),COEF_PVT(R,T)*MAX(0,COEF_CPT(R,TT,T,P)));
  OPTION CLEAR=PASTSUM;
{extra_block}
  OBJ_DIVI(RTP(R,T,P))   = STP_DIV('1',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIV(RTP(R,T,P))  = STP_DIV('2',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIII(RTP(R,T,P)) = STP_DIV('3',R,T,P)*(1+RTP_CAPVL(R,T,P));
"""

    # ---- final string ----

    return rf"""
  OPTION CLEAR=PERDINV,CLEAR=TPULSE,CLEAR=TPULSEYR;

  PERDINV(YK(T,K))$(YEARVAL(K) > M(T)-LEAD(T)) = YES;
  OPTION CLEAR=YK1; YK1(T,Y_EOH)$(YEARVAL(T)<=YEARVAL(Y_EOH)) = YES;

  TPULSEYR(PERDINV(T,Y_EOH)) = YES;
  TPULSE(TPULSEYR(T,Y_EOH)) = 1-((M(T)-YEARVAL(Y_EOH))/LEAD(T))$(NOT MIYR_1(T));
  TPULSEYR(YK1(T,Y_EOH))$(YEARVAL(Y_EOH) < M(T)+LAGT(T)) = YES;
  TPULSE(TPULSEYR(YK1(T,LL))) = 1-TPULSE(T+1,LL);

{fpd_block}

  IF(ABS(ALTOBJ) EQ 2, LOOP(G_RCUR(R,CUR),
{altv_block}
  ));

  OBJ_LINT(R,T,TT,CUR)$RDCUR(R,CUR) =
{"  OBJ_ALTV(R,T) *" if obj_is_alt else ""}
{lint_expr}

{trapezoid_block}

  OPTION CLEAR=PASTSUM,CLEAR=YK1;
"""
