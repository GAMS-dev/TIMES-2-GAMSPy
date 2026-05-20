# coef_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * COEF_EXT.cli - Coefficients for the Climate Module Extension
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillsow_stc import FillsowStc, exec_fillsow_stc

# from core.fillparm_gms import FillparmGms
from core.filparam_gms import FilparamGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefExtCli(GamsClass):
    """Translation unit for coef_ext.cli."""

    # Instance attributes
    module_name: str = "coef_ext_cli"
    gams_source: str = "coef_ext.cli"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        if self.arg1 == "SLOPE":
            self.tc.enqueue(self.exec_slope)
            return

        self.tc.enqueue(self.exec1)

        if self.env.cm_calib.upper() == "B":
            self.tc.enqueue(self.exec2)

        if self.env.cm_calib.upper() == "M":
            self.tc.enqueue(self.exec3)

        self.tc.enqueue(self.exec4)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                arg1="CM_HISTORY",
                arg2="",
                arg3="CM_HISTS",
                arg4=",'','','','','',''",
                arg5="LL",
                arg6="FIL",
                arg7="",
            )
        )

        self.tc.enqueue(self.exec4_2)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                arg1="CM_STATS",
                arg2="CM_HISTS,",
                arg3="CM_BOX",
                arg4=",'','','','',''",
                arg5="LL",
                arg6="FIL",
            )
        )

        self.tc.enqueue(self.exec5)

        if self.env.stages.upper() == "YES":
            self.tc.enqueue(self.exec6)

        if self.tc.defined("DAM_COST"):
            self.tc.enqueue(self.exec7)

        self.tc.enqueue(self.exec8)

        if self.env.stages.upper() == "YES":
            self.tc.enqueue(self.exec9)

        self.tc.enqueue(self.exec10)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                arg1="CM_BEMI",
                arg2="CM_EMIS,",
                arg3="",
                arg4=",'','','','',''",
                arg5="LL",
                arg6="FIL",
                arg7="",
                arg8="",
            )
        )

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                arg1="CM_BEMI",
                arg2="CM_EVAR,",
                arg3="",
                arg4=",'','','','',''",
                arg5="LL",
                arg6="FIL",
                arg7="",
                arg8="",
            )
        )

        cm_kind = self.tc.container["CM_KIND"]
        forcing_in_cm_kind = "FORCING" in cm_kind.toList()
        self.tc.enqueue(self.exec11, forcing=forcing_in_cm_kind, stages=self.env.stages)

        self.tc.enqueue(self.exec12)

        # * Prepare input parameters
        # *-----------------------------------------------------------------------------
        # * Interpolate parameters by default or if requested by user:
        batincludes = [
            (
                "CM_LINFOR",
                "",
                "CM_VAR,LIM",
                ",'','','','',''",
                "DATAYEAR",
                "FIL",
                "",
                "",
            ),
            ("CM_MAXCO2C", "", "", ",'','','','','',''", "LL", "T", "", "", "-1"),
            ("CM_MAXC", "", "CG", ",'','','','','',''", "LL", "FIL", "", "", "-1"),
            ("CM_EXOFORC", "", "", ",'','','','','',''", "LL", "MY_FIL", "", ""),
            ("UC_CLI", "UC_N,SIDE,R,", "CM_VAR", ",'','',''", "DATAYEAR", "T"),
        ]

        if self.env.stages.upper() == "YES":
            batincludes.append(
                (
                    "S_CM_MAXCO2C",
                    "",
                    "J,WW",
                    ",'','','','',''",
                    "DATAYEAR",
                    "T",
                    "SW_TSTG(T,J)$",
                    "",
                    "-1",
                )
            )
            batincludes.append(
                (
                    "S_CM_MAXC",
                    "",
                    "CG,J,WW",
                    ",'','','',''",
                    "DATAYEAR",
                    "T",
                    "SW_TSTG(T,J)$",
                    "",
                    "-1",
                )
            )

        for arg in batincludes:
            self.include(
                FilparamGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                    arg9=arg[8] if len(arg) > 8 else "",
                )
            )

        self.tc.enqueue(self.exec15)

        if self.env.stages.upper() != "YES":
            self.tc.enqueue(self.exec_slope)
            return

        self.tc.enqueue(self.exec16)

        self.include(
            FillsowStc(
                self.tc,
                self.env,
                arg1="CM_MAXC",
                arg2="",
                arg3="CG",
                arg4="LL",
                arg5="YES",
                arg6="SUPERYR(T,LL)",
                arg7="YES",
            )
        )

    def exec_slope(self: CoefExtCli) -> None:
        self.tc.add_gams_code(module=self, phase="run", code=coef_ext_cli_slope())

    def exec1(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Set up the history calibration values

* If calibration values are not provided by user, use the defaults:
CM_CONST(CM_HISTS) = 0;
LOOP((LL,CM_HISTS)$CM_HISTORY(LL,CM_HISTS),CM_CONST(CM_HISTS) = EPS);
CM_HISTORY(LL,CM_HISTS)$(NOT CM_CONST(CM_HISTS)) $= CM_DEFAULT(LL,CM_HISTS);

* Pick up the appropriate calibration values for the calibration year;
CM_CALIB=1;

""",
        )

    def exec2(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
CM_CALIB = SUM(MIYR_1(T),M(T)-B(T))+1;
""",
        )

    def exec3(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
CM_CALIB = EPS;
""",
        )

    def exec4(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Inter-/extrapolate calibration values
OPTION CLEAR=FIL; LOOP(MIYR_1(LL),FIL(LL-CM_CALIB) = YES);
""",
        )

    def exec4_2(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
 CM_STAT0(CM_HISTS,CM_BOX) = 0;
 CM_USUBS(CM_HISTS)=CM_EMIS(CM_HISTS)$(NOT SAMEAS(CM_HISTS,'CO2-GTC'));
 LOOP((CM_HISTS,LL,CM_BOX)$CM_STATS(CM_HISTS,LL,CM_BOX),CM_STAT0(CM_HISTS,CM_BOX) = EPS);
 LOOP(CM_BOXMAP(CM_HISTS,CM_VAR,CM_BOX(CM_Q))$(NOT CM_STAT0(CM_HISTS,CM_Q)),
   CM_STATS(CM_HISTS,LL,CM_Q)$CM_HISTORY(LL,CM_VAR) = CM_HISTORY(LL,CM_VAR)*POWER(CM_PPM(CM_HISTS),-1$CM_USUBS(CM_HISTS)));
""",
        )

    def exec5(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Pick the history values
 LOOP((MIYR_1(LL),YEAR(LL-CM_CALIB)),
   CM_STAT0(CM_HISTS,CM_BOX) = CM_STATS(CM_HISTS,YEAR,CM_BOX)*POWER(CM_PPM(CM_HISTS),1$CM_USUBS(CM_HISTS)));
 CM_STAT0(CM_HISTS,'N') = 0;
*-----------------------------------------------------------------------------
* Preprocess concentration decays
 CM_DECAY('CH4-MT','ATM') = CM_CONST('PHI-CH4');
 CM_DECAY('N2O-MT','ATM') = CM_CONST('PHI-N2O');
 CM_DECAY(CM_EMIS,'ATM') $= CM_DECAY(CM_EMIS,'N');
 CM_DECAY(CM_EMIS,CM_Q(L)) = 0;
 CM_DECAY(CM_EMIS,CM_BOX)$CM_STAT0(CM_EMIS,CM_BOX) = CM_DECAY(CM_EMIS,CM_BOX)+EPS;
 CM_ATMAP(CM_EMIS,CM_EMIS)$(NOT SUM(CM_ATMAP(CM_EMIS,CM_VAR),1)) = YES;
 LOOP(CM_EMIS$(NOT SUM(CM_BOXMAP(CM_EMIS,CM_VAR,CM_BOX),1)),CM_BOXMAP(CM_ATMAP(CM_EMIS,CM_VAR),CM_BOX)$CM_DECAY(CM_EMIS,CM_BOX)=YES);
* Coupled concentrations
 LOOP(CM_COUPMAP(CM_VAR,CM_EMIS,'ATM')$CM_STAT0(CM_EMIS,'UP'),
   CM_DECAY(CM_EMIS,'N')=CM_DECAY(CM_EMIS,'ATM'); CM_BOXMAP(CM_EMIS,CM_EMIS,'N')=YES);
* Reference concentration
 CM_COUPLE(CM_VAR,T,CM_EMIS,'FX')$((CM_COUPLE(CM_VAR,T,CM_EMIS,'FX')<=0)$CM_COUPLE(CM_VAR,T,CM_EMIS,'ATM')) =
   CM_STAT0(CM_EMIS,'ATM')*CM_DECAY(CM_EMIS,'ATM');
* Reference life and final unit life coefficient
 CM_COUPLE(CM_VAR,T,CM_EMIS,'N')$CM_COUPLE(CM_VAR,T,CM_EMIS,'ATM') =
   (CM_COUPLE(CM_VAR,T,CM_EMIS,'FX')+CM_STAT0(CM_EMIS,'UP')/CM_STAT0(CM_EMIS,'LIFE'))*CM_DECAY(CM_EMIS,'ATM')/CM_PPM(CM_VAR);
 OPTION CM_COUPMAP < CM_COUPLE;
*-----------------------------------------------------------------------------
* Set up the 3x3 PHI matrix for emissions
IF(NOT SUM((CM_BOX,CM_BUCK),CM_PHI('CO2-GTC',CM_BOX,CM_BUCK)),
* Set up the 3x3 PHI matrix
  CM_PHI('CO2-GTC','ATM','UP') = CM_CONST('PHI-UP-AT');
  CM_PHI('CO2-GTC','UP','ATM') = CM_CONST('PHI-AT-UP');
  CM_PHI('CO2-GTC','UP','LO') = CM_CONST('PHI-LO-UP');
  CM_PHI('CO2-GTC','LO','UP') = CM_CONST('PHI-UP-LO');
);
* Default first-order decay models for CH4 and N2O
LOOP(CM_USUBS(CM_EMIS),
IF(NOT SUM((CM_BOX,CM_BUCK),CM_PHI(CM_EMIS,CM_BOX,CM_BUCK)),
  CM_PHI(CM_EMIS,CM_BOX,CM_BOX)$CM_DECAY(CM_EMIS,CM_BOX) = 1-CM_DECAY(CM_EMIS,CM_BOX)+EPS;
  CM_PHI(CM_EMIS,'UP',CM_EMIS) = EPS$CM_STAT0(CM_EMIS,'UP'));
);
*-----------------------------------------------------------------------------
* Set emission kinds and FORCING to CM_KIND when active
 CM_KIND(CM_VAR)$(SUM((CM_BOX,CM_BUCK)$CM_PHI(CM_VAR,CM_BOX,CM_BUCK),1)$CM_EMIS(CM_VAR)) = YES;
 CM_EMIS(CM_VAR) = CM_KIND(CM_VAR)$CM_PPM(CM_VAR);
 CM_KIND('FORCING') = YES$(SUM(LL$CM_MAXC(LL,'DELTA-ATM'),1)+(CARD(CM_EMIS) GT 1));
 IF(CARD(UC_CLI),CM_KIND('FORCING') = YES);
 CM_TKIND(CM_KIND) = YES; LOOP(CM_FORCMAP(CM_VAR,CM_HISTS)$SUM(LL$CM_MAXC(LL,CM_VAR),1),CM_TKIND(CM_VAR)=YES);
 CM_FORCMAP('FORC-KYO',CM_VAR)$(NOT CM_FORCMAP(CM_VAR,CM_VAR)) $= CM_PPM(CM_VAR);
 CM_FORCMAP('FORCING',CM_VAR) $= CM_PPM(CM_VAR);
 CM_FORCMAP(CM_HISTS,CM_VAR)$(SUM(CM_EMIS$CM_FORCMAP(CM_VAR,CM_EMIS),1)$(NOT CM_EMIS(CM_VAR))) = NO;
""",
        )

    def exec6(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
CM_KIND('FORCING')$SUM((LL,J,W)$S_CM_MAXC(LL,'DELTA-ATM',J,W),1) = YES;
""",
        )

    def exec7(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
DAM_COST CM_KIND('FORCING')$SUM(R$(DAM_BQTY(R,'FORCING')+DAM_BQTY(R,'DELTA-ATM')),1) = YES;
""",
        )

    def exec8(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Establish set of years beyond EOH
* Set extended EOH (EXT-EOH) year into FIL; -1 deactivates EOH extension
  OPTION CLEAR=FIL; YR_VL = 0; FIRST_VAL = CM_CONST('EXT-EOH');
  IF(FIRST_VAL GT 0, FIRST_VAL = ROUND(MAX(MIYR_VL,FIRST_VAL));
    LOOP(MIYR_1(LL), F = FIRST_VAL-YEARVAL(LL); FIL(LL+F) = YES);
    CM_BEMI(CM_EMIS,FIL) = EPS; CM_EVAR(CM_EMIS,FIL) = 1;
* Set all MAXC year beyond EOH into FIL
""",
        )

    def exec9(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CM_MAXC_M < S_CM_MAXC;
""",
        )

    def exec10(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
    F = SMAX(T(LL),ORD(LL)); CM_MAXC_M(CM_VAR,LL)$CM_MAXC(LL,CM_VAR)=EPS;
    LOOP((LL,CM_VAR(CG))$((ORD(LL) GT F)$CM_MAXC_M(CG,LL)),
      IF((YEARVAL(LL) GT FIRST_VAL OR NOT(CM_EMIS(CM_VAR)))$YEARVAL(LL), YR_VL = ORD(LL); FIL(LL) = YES));
    FIL(LL)$(ORD(LL) GT YR_VL) = NO;
* Set BEMI to MAXC emissions for years beyond EXT-EOH and zero at EXT-EOH
    CM_BEMI(CM_EMIS(CM_HISTS(CG)),FIL(LL))$(YEARVAL(LL) GT FIRST_VAL) = CM_MAXC(LL,CG);
    CM_EVAR(CM_EMIS,FIL(LL))$(YEARVAL(LL) GT FIRST_VAL) = EPS$CM_BEMI(CM_EMIS,LL);
* Set EOH contribution to zero at final year (deactivated for now)
*   LOOP(MIYR_1(YEAR), CM_EVAR(CM_EMIS,YEAR+(YR_VL-ORD(YEAR))) = EPS);
* Set all years Modulo BEOHMOD to FIL
    MY_F = ROUND(MAX(1,CM_CONST('BEOHMOD')));
    FIL(LL)$((ORD(LL) LT YR_VL)$(MOD(YEARVAL(LL),MY_F) = 0)) = YES$(ORD(LL) GT F);
  );
  CM_MAXC(LL,CM_EMIS(CM_HISTS(CG)))$(YEARVAL(LL) GT MIYR_VL) = 0;
* Complete CM_LED
  LOOP(FIL(LL), Z = ORD(LL); CM_LED(LL) = Z-F; F = Z);
  CM_LED(T) = LEAD(T); CM_LED(MIYR_1) = CM_CALIB;
  PRET(T,T-1)=YES;
* Interpolate BEMI and BEOH over FIL (mucks-up F, Z, MY_F, MY_FYEAR, FIRST_VAL, LAST_VAL)

""",
        )

    def exec11(self: CoefExtCli, forcing: bool, stages: str) -> None:
        if forcing:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
    CM_SIG1(SOW) = CM_CONST('SIGMA1');
    """,
            )

            # * Set up the 2x2 SIG matrix for forcing
            if stages.upper() == "YES":
                # fmt: off
                batincludes = [
                    ("CM_CONST", "CM_STCC", '', '', "YES", "YES", "YES"),
                    ("DAM_COST", 'R,', '"DELTA-ATM",CUR', "TT", "YES", "YES", "NO")
                ]
                # fmt: on
                for arg in batincludes:
                    exec_fillsow_stc(
                        module=self,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                    )

            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"""
    {"CM_SIG1(SOW)=S_CM_CONST('SIGMA1','1',SOW);" if stages.upper() == "YES" else ""}
    {"CM_SIG(SOW,'ATM','ATM') = 1-CM_SIG1(SOW)*(CM_CONST('GAMMA')/S_CM_CONST('CS','1',SOW)+CM_CONST('SIGMA2'));" if stages.upper() == "YES" else ""}
    {"CM_SIG('1','ATM','ATM') = 1-CM_SIG1('1')*(CM_CONST('LAMBDA')+CM_CONST('SIGMA2'));" if stages.upper() != "YES" else ""}
    CM_SIG(SOW,'ATM','LO') = CM_SIG1(SOW)*CM_CONST('SIGMA2');
    CM_SIG(SOW,'LO','ATM') = CM_CONST('SIGMA3');
    CM_SIG(SOW,'LO','LO') = 1-CM_CONST('SIGMA3');
    CM_PHI('FORCING','ATM','FORCING') = 1;
    * Intialize CM_AA to the identity matrix, CM_BB to zero
    CM_AA('FORCING',LL,SOW,CM_BUCK,CM_BOX)$CM_LED(LL) = DIAG(CM_BUCK,CM_BOX);
    CM_BB('FORCING',LL,SOW,CM_BUCK)$CM_LED(LL) = 0; CNT=0;
    * Assume linear evolution of forcing between milestone years
    LOOP((CM_VAR('FORCING'),LL)$CM_LED(LL),
    IF(CNT, CNT=1; Z = CM_LED(LL); ELSE CNT=EPS; Z=CM_CALIB);
        FOR(F = 0 TO Z-1, MY_F = F/Z*CNT;
        CM_BB(CM_VAR,LL,SOW,CM_BOX) = CM_BB(CM_VAR,LL,SOW,CM_BOX) + CM_SIG1(SOW)*(1-MY_F)*CM_AA(CM_VAR,LL,SOW,CM_BOX,'ATM');
        CM_CC(CM_VAR,LL,SOW,CM_BOX) = CM_CC(CM_VAR,LL,SOW,CM_BOX) + CM_SIG1(SOW)*   MY_F *CM_AA(CM_VAR,LL,SOW,CM_BOX,'ATM');
        CM_AA(CM_VAR,LL,SOW,CM_BUCK,CM_BOX) = SUM(CM_Q$CM_BOX(CM_Q),CM_AA(CM_VAR,LL,SOW,CM_BUCK,CM_Q)*CM_SIG(SOW,CM_Q,CM_BOX));
    ));
    """,
            )

    def exec12(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Set up control set CM_CONC for the BOX equations; complete PHI
  OPTION CM_CONC <= CM_BOXMAP;
  CM_PHI(CM_KIND,CM_BOX,CM_BOX)$(NOT CM_PHI(CM_KIND,CM_BOX,CM_BOX)) = 1$CM_STAT0(CM_KIND,CM_BOX)-SUM(CM_BUCK$(NOT SAMEAS(CM_BOX,CM_BUCK)),CM_PHI(CM_KIND,CM_BUCK,CM_BOX));
*-----------------------------------------------------------------------------
* Calculate the ith powers of PHI, i=1...Z, where Z = LEAD(T)
* First intialize CM_AA to the identity matrix, and CM_BB(T,1) to 0:
LOOP(CM_EMIS(CM_VAR),
 CM_PHI(CM_VAR,'ATM',CM_VAR)$(NOT SUM(CM_BOX$CM_PHI(CM_VAR,'ATM',CM_VAR),1)) = 1;
 CM_AA(CM_VAR,LL,'1',CM_BUCK,CM_BOX)$CM_LED(LL) = DIAG(CM_BUCK,CM_BOX);
 CM_BB(CM_VAR,LL,'1',CM_BUCK)$CM_LED(LL) = 0; CNT = (ALTOBJ NE 3);
* Loop over MILESTONYR and calculate rest of the powers of PHI
 LOOP(T$(ALTOBJ NE 3),
  IF(ORD(T) GT 1, MY_F = M(T)-B(T)+1; Z = LEAD(T); ELSE MY_F=CM_CALIB; Z=MY_F);
   FOR(F = 1 TO Z,
     IF(F LE MY_F, CM_BB(CM_VAR,T,'1',CM_BOX) = CM_BB(CM_VAR,T,'1',CM_BOX) + SUM(CM_BUCK,CM_PHI(CM_VAR,CM_BUCK,CM_VAR)*CM_AA(CM_VAR,T,'1',CM_BOX,CM_BUCK));
     ELSE          CM_CC(CM_VAR,T,'1',CM_BOX) = CM_CC(CM_VAR,T,'1',CM_BOX) + SUM(CM_BUCK,CM_PHI(CM_VAR,CM_BUCK,CM_VAR)*CM_AA(CM_VAR,T,'1',CM_BOX,CM_BUCK)));
     CM_AA(CM_VAR,T,'1',CM_BUCK,CM_BOX) = SUM(CM_Q$CM_BOX(CM_Q),CM_AA(CM_VAR,T,'1',CM_BUCK,CM_Q)*CM_PHI(CM_VAR,CM_Q,CM_BOX));
 ));
* If linear evolution formulation, assume linear evolution of emissions
 LOOP(LL$(((ALTOBJ EQ 3) OR NOT T(LL))$CM_LED(LL)),
  IF(CNT, CNT=1; Z = CM_LED(LL); ELSE CNT=EPS; Z=CM_CALIB);
   FOR(F = 0 TO Z-1, MY_F = F/Z*CNT;
     CM_BB(CM_VAR,LL,'1',CM_BOX) = CM_BB(CM_VAR,LL,'1',CM_BOX) + (1-MY_F)*SUM(CM_BUCK,CM_PHI(CM_VAR,CM_BUCK,CM_VAR)*CM_AA(CM_VAR,LL,'1',CM_BOX,CM_BUCK));
     CM_CC(CM_VAR,LL,'1',CM_BOX) = CM_CC(CM_VAR,LL,'1',CM_BOX) +    MY_F *SUM(CM_BUCK,CM_PHI(CM_VAR,CM_BUCK,CM_VAR)*CM_AA(CM_VAR,LL,'1',CM_BOX,CM_BUCK));
     CM_AA(CM_VAR,LL,'1',CM_BUCK,CM_BOX) = SUM(CM_Q$CM_BOX(CM_Q),CM_AA(CM_VAR,LL,'1',CM_BUCK,CM_Q)*CM_PHI(CM_VAR,CM_Q,CM_BOX));
 ));
);
*-----------------------------------------------------------------------------
* Prepare commodity variables for emissions:
  CM_GHGMAP(R,C,'CO2-GTC') $= CM_CO2GTC(R,C);
  LOOP((R,C,CM_KIND(CM_VAR(CG)))$CM_GHGMAP(R,C,CG),
    RHS_COMBAL(RTCS_VARC(R,T,C,S)) = YES;
    RCS_COMBAL(RTCS_VARC(R,T,C,S),'FX') = YES);
*-----------------------------------------------------------------------------
* Construct SUPERYR (needed in MAX constraints)
  SUPERYR(PERIODYR(T,LL))$(YEARVAL(LL) LE YEARVAL(T)) = YES;
  SUPERYR(T+1,LL)$((YEARVAL(LL) GT YEARVAL(T))$PERIODYR(T,LL)) = YES;
  LOOP(MIYR_1(T++1),SUPERYR(T,LL)$(YEARVAL(LL) GT M(T)) = YES);
  OPTION FIL < CM_LED, MY_FIL < Y;
  MY_FIL(LL)$((YEARVAL(LL)>MIYR_VL)$(ORD(LL) LE YR_VL)) = YES;
*=============================================================================
""",
        )

    def exec15(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Convert all concentration bounds to PPM basis
  CM_MAXC(LL,CG('CO2-PPM'))$CM_MAXCO2C(LL) = MIN(CM_MAXC(LL,CG)+INF$(NOT CM_MAXC(LL,CG)),CM_MAXCO2C(LL)/CM_PPM('CO2-GTC'));
  CM_MAXC(LL,CG('CO2-PPM'))$CM_MAXC(LL,'CO2-ATM') = MIN(CM_MAXC(LL,CG)+INF$(NOT CM_MAXC(LL,CG)),CM_MAXC(LL,'CO2-ATM')*CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC'));
  CM_MAXC(LL,CG('CO2-PPM'))$(CM_MAXC(LL,'FORCING')*(NOT CM_KIND('FORCING'))) =
     MIN(CM_MAXC(LL,CG)+INF$(NOT CM_MAXC(LL,CG)),CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC')*
         EXP((CM_MAXC(LL,'FORCING')-CM_EXOFORC(LL))*LOG(2)/CM_CONST('GAMMA')));
* Remove bounds from years with undefined concentration
  F = SMIN(T,YEARVAL(T));  CM_MAXC(LL,CG)$(YEARVAL(LL) LT F) = 0;
  """,
        )

    def exec16(self: CoefExtCli) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  S_CM_MAXC(LL,CG('CO2-PPM'),J,W)$S_CM_MAXCO2C(LL,J,W) = MIN(S_CM_MAXC(LL,CG,J,W)+INF$(NOT S_CM_MAXC(LL,CG,J,W)),S_CM_MAXCO2C(LL,J,W)/CM_PPM('CO2-GTC'));
  S_CM_MAXC(LL,CG('CO2-PPM'),J,W)$S_CM_MAXC(LL,'CO2-ATM',J,W) = MIN(S_CM_MAXC(LL,CG,J,W)+INF$(NOT S_CM_MAXC(LL,CG,J,W)),S_CM_MAXC(LL,'CO2-ATM',J,W)*CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC'));
  S_CM_MAXC(LL,CG('CO2-PPM'),J,W)$(S_CM_MAXC(LL,'FORCING',J,W)*(NOT CM_KIND('FORCING'))) =
     MIN(S_CM_MAXC(LL,CG,J,W)+INF$(NOT S_CM_MAXC(LL,CG,J,W)),CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC')*
         EXP((S_CM_MAXC(LL,'FORCING',J,W)-CM_EXOFORC(LL))*LOG(2)/CM_CONST('GAMMA')));
  S_CM_MAXC(LL,CG,J,W)$(YEARVAL(LL) LT F) = 0;
  """,
        )


def coef_ext_cli_slope() -> str:
    return r"""
*-----------------------------------------------------------------------------
* Calculate linear slope for FORCING from CO2
IF(CM_KIND('FORCING'),OPTION FIL<CM_LED;
LOOP(CM_ATMAP(CM_EMIS,CM_VAR),CM_LINFOR(FIL(LL),CM_EMIS,L) $= CM_LINFOR(LL,CM_VAR,L));
CM_LINFOR(FIL(LL),'CO2-GTC',BDNEQ) $= CM_LINFOR(LL,'CO2-ATM',BDNEQ)*CM_CONST('CO2-PREIND')*(1/CM_PPM('CO2-GTC'));
MY_ARRAY(FIL(LL)) = MAX(CM_LINFOR(LL,'CO2-GTC','LO'),
    ((CM_LINFOR(LL,'CO2-GTC','UP')-CM_LINFOR(LL,'CO2-GTC','LO')) /
    LOG(MAX(1.001,CM_LINFOR(LL,'CO2-GTC','UP')/CM_LINFOR(LL,'CO2-GTC','LO')))))$(CM_LINFOR(LL,'CO2-GTC','LO') GT 0);
CM_LINFOR(FIL(LL),'CO2-GTC','N')$MY_ARRAY(LL) = CM_CONST('GAMMA')/MY_ARRAY(LL)/LOG(2);
CM_LINFOR(FIL(LL),'CO2-GTC','FX')$MY_ARRAY(LL) =
    (CM_CONST('GAMMA')/LOG(2) *
    LOG(MY_ARRAY(LL)*CM_LINFOR(LL,'CO2-GTC','LO')/POWER(CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC'),2)) -
    CM_LINFOR(LL,'CO2-GTC','N')*(MY_ARRAY(LL)+CM_LINFOR(LL,'CO2-GTC','LO')))/2);
*-----------------------------------------------------------------------------
* If EXOFORCING is not provided by the user, use default values
IF(NOT SUM(T,CM_EXOFORC(T)),CM_EXOFORC(MY_FIL(LL)) = MIN(1.15, -0.1965 + 0.013465 * (YEARVAL(LL)-1995)));
"""
