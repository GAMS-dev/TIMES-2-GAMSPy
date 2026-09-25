# spoint_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SPOINT.mod is the code for handling solution point saving/loading
# *   %1 - 1 or 0 (1: before solve, 0: renaming after solve)
# * Note: Using Posix utility mv for renaming for portability
# *=============================================================================*

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.clearsol_stc import ClearsolStc
from core.eqobsalv_mod import EqobsalvMod, EqobsalvModConfig
from core.pp_clean_mod import PpCleanMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SpointMod(GamsClass):
    """Translation unit for spoint.mod."""

    module_name: str = "spoint_mod"
    gams_source: str = "spoint.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.env.set_local("path", self.env.gdxpath)
        self.env.set_local("pnt1", "_p")
        self.env.set_local("pnt2", "")
        if self.env.is_set("fixboh"):
            self.env.set_local("pnt1", "")
            self.env.set_local("pnt2", "_p")

        if self.env.is_set("spoint"):
            if self.env.spoint.upper() == "YES":
                self.env.set_scoped("spoint", "1")

            self.tc.enqueue(
                self.exec1,
                arg1=self.arg1,
                spoint=self.env.spoint,
                model_name=self.env.model_name,
                path=self.env.path,
                run_name=self.env.run_name,
            )

        if self.arg1 == "0":
            return

        if self.env.stages == "YES":
            self.include(ClearsolStc(self.tc, self.env, arg1="ALL"))

        if self.env.rpoint != "NO":
            if self.env.rpoint.upper() != "YES":
                self.env.set_scoped("lpoint", self.env.rpoint)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
$CLEAR EQ_IRE EQE_CPT EQ_PEAK EQE_UCRTP EQE_COMBAL EQG_COMBAL EQE_COMPRD VAR_UPS VAR_UPT VAR_UDP
$CLEAR EQE_UC EQE_UCR EQE_UCT EQE_UCRT EQE_UCTS EQE_UCRTS EQE_UCRS EQE_UCSU EQE_UCSUS EQE_UCRSU EQE_UCRSUS
""",
            )

            if self.env.var_uc != "YES":
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=r"""
$CLEAR EQG_UC EQG_UCR EQG_UCT EQG_UCRT EQG_UCTS EQG_UCRTS EQG_UCRS EQG_UCSU EQG_UCSUS EQG_UCRSU EQG_UCRSUS
$CLEAR EQL_UC EQL_UCR EQL_UCT EQL_UCRT EQL_UCTS EQL_UCRTS EQL_UCRS EQL_UCSU EQL_UCSUS EQL_UCRSU EQL_UCRSUS
""",
                )

            self.tc.enqueue(
                self.exec2,
                eq_clitot_defined=self.tc.defined("EQ_CLITOT"),
                timesed_yes=(self.env.timesed == "YES"),
            )

            if self.env.merge.upper() == "YES":
                raise FileNotFoundError("clears.mrg does not exist in TIMES source.")
                # self.include(ClearsMrg(self.tc, self.env))

            if self.env.is_set("timestep"):
                self.include(
                    EqobsalvMod(
                        self.tc,
                        self.env,
                        config=EqobsalvModConfig(arg1="STP", arg2="EXIT"),
                    )
                )

            self.include(PpCleanMod(self.tc, self.env))

        self.env.set_scoped("load", "0")
        if self.env.is_set("lpoint"):
            if Path(f"{self.env.path}{self.env.lpoint}{self.env.pnt1}.gdx").exists():
                self.env.set_scoped("load", "2")

            if self.env.load == "2":
                self.tc.enqueue(
                    self.exec3,
                    file=f"{self.env.path}{self.env.lpoint}{self.env.pnt1}.gdx",
                )
                self._label_finish()
                return

            if Path(f"{self.env.path}{self.env.lpoint}{self.env.pnt2}.gdx").exists():
                self.env.set_scoped("load", "2")
            if self.env.load == "2":
                self.tc.enqueue(
                    self.exec3,
                    file=f"{self.env.path}{self.env.lpoint}{self.env.pnt2}.gdx",
                )
                self._label_finish()
                return

            if self.env.is_set("fixboh"):
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=rf"$ABORT Could not load gdx file {self.env.lpoint}",
                )
                return

        if (
            not self.env.is_set("spoint")
        ) or self.env.lpoint.upper() == self.env.run_name.upper():
            self._label_finish()
            return

        if self.env.spoint == "2" or self.env.spoint == "3":
            self.env.set_scoped("load", "1")
        if self.env.load == "0":
            self._label_finish()
            return

        if Path(f"{self.env.path}{self.env.run_name}_P.gdx").exists():
            self.env.set_scoped("load", "2")

        if self.env.load == "2":
            self.tc.enqueue(
                self.exec3, file=f"{self.env.path}{self.env.run_name}_p.gdx"
            )
            self._label_finish()
            return

        if Path(f"{self.env.path}{self.env.run_name}.gdx").exists():
            self.env.set_scoped("load", "2")
        if self.env.load == "2":
            self.tc.enqueue(self.exec3, file=f"{self.env.path}{self.env.run_name}.gdx")
            self._label_finish()
            return

    def exec1(
        self: SpointMod,
        arg1: str,
        spoint: str,
        model_name: str,
        path: str,
        run_name: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(J('{spoint}'), Z = SUM(SAMEAS('{spoint}',J),ORD(J));
    IF(MOD(Z,2), OPTION SAVEPOINT=1;
* Reset GDX file to ensure it will always be written if SAVEPOINT=1
      IF({arg1},execute_unload '{model_name}_p.gdx',IMP;
      ELSE  execute 'mv -uf {model_name}_p.gdx {path}{run_name}_p.gdx')));
""",
        )

    def exec2(self: SpointMod, eq_clitot_defined: bool, timesed_yes: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{"OPTION CLEAR=EQ_CLITOT,CLEAR=EQ_CLIMAX; VAR_CLIBOX.L(CM_VAR,CM_BOX,LL)$NO=0;" if eq_clitot_defined else ""}
  VAR_BLND.L(R,T,BLE,OPR)$NO = 0;
{"VAR_OBJELS.L(R,BD,CUR)$NO = 0;" if timesed_yes else ""}
""",
        )

    def exec3(self: SpointMod, file: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"execute_loadpoint '{file}';",
        )

    def exec_finish1(self: SpointMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  REG_BDNCAP(R,BDNEQ)$REG_BDNCAP(R,'FX')=MAX(REG_BDNCAP(R,BDNEQ),REG_BDNCAP(R,'FX'))$SUM(BD,REG_BDNCAP(R,BD)$BDSIG(BD));
  REG_BDNCAP(R,'FX')$SUM(BDNEQ$REG_BDNCAP(R,BDNEQ),1)=0;
  LOOP((R,BD)$REG_BDNCAP(R,BD),Z=REG_BDNCAP(R,BD); RT_NO(R,T)$(M(T)<=Z)=YES);
* Determine which milestones available
  RTCS(RTC,S--ORD(S))$=EQG_COMBAL.M(RTC,S);
  RTCS(RTC,S--ORD(S))$=EQE_COMBAL.M(RTC,S);
  OPTION FIL < RTCS;
  PASTSUM(RTP(RT_NO(R,T(FIL)),P))$PRC_CAP(R,P)=EPS;
  PASTSUM(RTP(RT_NO,P)) $= VAR_NCAP.L(RTP);
  RTPS_BD(RTP(RT_NO(R,T),P),ANNUAL,BD)$((M(T)<=REG_BDNCAP(R,BD))$PASTSUM(RTP)) = YES;
  RTPS_BD(RTP(RT_NO(R,T),P),ANNUAL(S),BDNEQ)$(RTPS_BD(RTP,S,'LO')$RTPS_BD(RTP,S,'UP')) = BDSIG(BDNEQ)-NCAP_BND(R,'0',P,'N');
  NCAP_BND(RTP(RT_NO(R,T),P),BD)$RTPS_BD(RTP,'ANNUAL',BD) = MAX(EPS,PASTSUM(RTP),NCAP_BND(RTP,BD)$BDLOX(BD));
  NCAP_BND(RTP(RT_NO,P),'UP')$(NCAP_BND(RTP,'LO')$NCAP_BND(RTP,'UP')) = SMAX(BDNEQ,NCAP_BND(RTP,BDNEQ));
""",
        )

    def exec_finish2(self: SpointMod, var: str, sow: str, swt: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {var}_NCAP.LO(RTP(RT_NO(R,T),P){sow}){swt}  $= NCAP_BND(RTP,'LO');
  {var}_NCAP.UP(RTP(RT_NO(R,T),P){sow}){swt}  $= NCAP_BND(RTP,'UP');
  {var}_NCAP.FX(RTP(RT_NO(R,T),P){sow}){swt}  $= NCAP_BND(RTP,'FX');
  VAR_NCAP.L(RTP(RT_NO,P)) $= PASTSUM(RTP);
  OPTION CLEAR=PASTSUM,CLEAR=RTCS,CLEAR=FIL,CLEAR=RTPS_BD,CLEAR=RT_NO;
""",
        )

    def _label_finish(self) -> None:
        g = self.tc

        if not self.tc.defined("REG_BDNCAP"):
            self.env.set_scoped("load", "0")
        if self.env.load != "2":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="$CLEAR REG_BDNCAP",
            )
            return
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Fix new capacities to previous solution if requested
  SET RT_NO(R,T), RTCS(R,ALLYEAR,C,S);
""",
        )
        self.tc.enqueue(self.exec_finish1)
        if self.env.stages == "YES":
            self.env.set_local("swt", f"$SW_T(T{self.env.sow})")
            self.env.set_local(
                "swt_GP", (g.SwT[g.t, *self.env.sow_GP])
            )  # Todo: move $ to main code

        self.tc.enqueue(
            self.exec_finish2, var=self.env.var, sow=self.env.sow, swt=self.env.swt
        )
