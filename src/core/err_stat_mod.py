# err_stat_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * ERR_STAT.MOD checks/displays GAMS/Solver Errors
# *   %1 - Condition to be checked or 'SOLVE'  used
# *   %2 - Action or Condition to be checked
# *   %3 - Error Message if Not SOLVE
# *=============================================================================*
# *GaG Questions/Comments:
# *  - for %system.filesys% == UNIX file /dev/tty
# *  - does not affect stopping BAT
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class ErrStatMod(GamsClass):
    """Translation unit for err_stat.mod."""

    # Instance attributes
    module_name: str = "err_stat_mod"
    gams_source: str = "err_stat.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        # $ IFI %SHELL%==ANSWER     $SET TMP END_GAMS.STA
        if self.env.shell.upper() == "ANSWER":
            self.env.set_scoped("tmp", "END_GAMS.STA")
        # $ IFI NOT %SHELL%==ANSWER $SET TMP END_GAMS
        if self.env.shell.upper() != "ANSWER":
            self.env.set_scoped("tmp", "END_GAMS")

        # $  IF "%1" == SOLVE        $GOTO SOLVE
        if self.arg1 == "SOLVE":
            self.queue_solve()

        # $ IF DEFINED SOLVESTAT    $GOTO ACTION
        elif self.tc.defined("SOLVESTAT"):
            self.queue_action()

        else:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
SET SOLVESTAT(J) /
  1 "Optimal"
  2 "Locally optimal"
  3 "Unbounded"
  4 "Infeasible"
  5 "Locally infeasible"
  6 "Intermediate infeasible"
  7 "Intermediate nonoptimal"
  8 "Integer solution"
  9 "Intermediate non-integer"
 10 "Integer infeasible"
 11 "Lic problem"
 12 "Error unknown"
 13 "Error no solution"
 14 "No solution returned"
 15 "Solved unique"
 16 "Solved locally unique"
 17 "Solved singular"
 18 "Unbnd no solution"
 19 "Infes no solution"
/;
""",
            )
            tmp = self.env.tmp
            self.prep_file(tmp)
            self.queue_action()

    def queue_solve(self) -> None:
        "No relevance to compilation"
        self.tc.enqueue(
            self.exec_solve,
            arg1=self.arg1,
            arg2=self.arg2,
            model_name=self.env.model_name,
            err_abort="",
        )

    def exec_solve(
        self: ErrStatMod, arg1: str, arg2: str, model_name: str, err_abort: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=err_stat_solve(
                arg1=arg1, arg2=arg2, model_name=model_name, err_abort=err_abort
            ),
        )

    def queue_action(self) -> None:
        phase: GamsPhase = "init"
        """
        Most of the GAMS code is GAMSPy irrelevant.

        $ IF %ERR_ABORT%==NO  $GOTO DONE
        %4;
        * compile or GAMS execute error
        $IF NOT ERRORFREE $ECHO %3%5 > %TMP%
        IF(execerror,PUT END_GAMS "%3%5"; PUTCLOSE);
        %1 $%2  "%3"
        $GOTO DONE
        """

        self.tc.add_gams_code(module=self, phase=phase, code=f"{self.arg4};")

    def prep_file(self, tmp: str) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=rf"""
FILE SCREEN / '' /;
FILE END_GAMS / {tmp} /;
""",
        )


def err_stat_solve(
    *,
    arg1: str = "",
    arg2: str,
    model_name: str,
    err_abort: str,
) -> str:
    return rf"""
 Z = MIN(14,{model_name}.MODELSTAT)-1; IF(Z > 18, Z=11);
 IF(Z>=0,PUT SCREEN /"--- TIMES Solve status: ";
   LOOP(SAMEAS(J,'1'), PUT SOLVESTAT.TE(J+Z));
   PUTCLOSE;
   PUT END_GAMS "Solve status: ";
   LOOP(SAMEAS(J,'1'), PUT SOLVESTAT.TE(J+Z) /);
   PUTCLOSE;
   Z = ABS(ABS(2*{model_name}.MODELSTAT-9)-6));
 IF(Z>1.5 OR {model_name}.MODELSTAT=7,execerror=1);
 {"Z=0;" if err_abort == "NO" else ""}
* [UR] allow solution "optimal with unscaled infeasibilities"
* -- allow even "intermediate non-optimal" for investigation
*ABORT$(({model_name}.MODELSTAT GT 1) OR ({model_name}.SOLVESTAT GT 1)) '*** ERRORS IN OPTIMIZATION ***'
 ABORT$(Z>1.5) '{arg2}';
 IF(execerror,execerror=0);
"""
