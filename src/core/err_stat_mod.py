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

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        phase = "init"
        # $ IFI %SHELL%==ANSWER     $SET TMP END_GAMS.STA
        if self.env.shell == "ANSWER":
            self.env.set_scoped("tmp", "END_GAMS.STA")
        # $ IFI NOT %SHELL%==ANSWER $SET TMP END_GAMS
        else:
            self.env.set_scoped("tmp", "END_GAMS")

        done = False
        # $  IF "%1" == SOLVE        $GOTO SOLVE
        if self.arg1 == "SOLVE":
            done = self.queue_solve(tc=self.tc)

        # $ IF DEFINED SOLVESTAT    $GOTO ACTION
        elif "SOLVESTAT" in self.tc.container.listSymbols():
            solvestat = self.tc.container["SOLVESTAT"]
            if solvestat.number_records:
                done = self.queue_action(tc=self.tc)

        if not done:
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
            self.prep_file(self.tc, tmp)

    def queue_solve(self, tc):
        "No relevance to compilation"
        tc.enqueue(self.solve, tc=self.tc)
        return True  # Signal done

    def queue_action(self, tc):
        phase = "init"
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
        tc.add_gams_code(module=self, phase=phase, code=f"{self.arg4};")

        return True  # Signal done

    def prep_file(self, tc, tmp):
        phase = "run"
        tc.add_gams_code(
            module=self,
            phase=phase,
            code=rf"""
FILE SCREEN / '' /;
FILE END_GAMS / {tmp} /;
""",
        )

    def solve(self, tc, err_abort):
        phase = "run"
        tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
 Z = MIN(14,%MODEL_NAME%.MODELSTAT)-1; IF(Z > 18, Z=11);
 IF(Z>=0,PUT SCREEN /"--- TIMES Solve status: ";
   LOOP(SAMEAS(J,'1'), PUT SOLVESTAT.TE(J+Z));
   PUTCLOSE;
   PUT END_GAMS "Solve status: ";
   LOOP(SAMEAS(J,'1'), PUT SOLVESTAT.TE(J+Z) /);
   PUTCLOSE;
   Z = ABS(ABS(2*%MODEL_NAME%.MODELSTAT-9)-6));
 IF(Z>1.5 OR %MODEL_NAME%.MODELSTAT=7,execerror=1);
""",
        )

        z = tc.container["Z"]
        if not err_abort:
            z[...] = 0

        # * [UR] allow solution "optimal with unscaled infeasibilities"
        # * -- allow even "intermediate non-optimal" for investigation
        # *ABORT$((%MODEL_NAME%.MODELSTAT GT 1) OR (%MODEL_NAME%.SOLVESTAT GT 1)) '*** ERRORS IN OPTIMIZATION ***'
        # ABORT$(Z>1.5) '%2';
        if z.records.iloc[0] > 1.5:
            raise ValueError(self.arg2)
        tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
IF(execerror,execerror=0);
""",
        )
