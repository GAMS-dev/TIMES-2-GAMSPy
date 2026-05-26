# solve_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOLVE.MOD solver and solve controls
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from gamspy import Model, set_options

from core.err_stat_mod import ErrStatMod
from core.pp_clean_mod import PpCleanMod, pp_clean_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


# TODO: currently SolveMod and solve_mod() don't share any code, ie there is duplicated logic here.
# compile() could call solve_mod() instead
class SolveMod(GamsClass):
    """Translation unit for solve.mod."""

    # Instance attributes
    module_name: str = "solve_mod"
    gams_source: str = "solve.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        model_name: str,
        equations: list[str],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.model_name = model_name
        self.equations = equations
        self.compile()

    def compile(self) -> None:
        # * Release some memory
        self.include(PpCleanMod(self.tc, self.env))
        self.tc.enqueue(self.set_model_param, model_name=self.model_name)

        ### * MACRO: Loading solution from GDX file replaced by activating the SPOINT utility
        if self.env.solve_now != "NO":
            # * solve TIMES with appropriate METHOD
            if not self.env.is_set("mixlp"):
                self.env.set_local("mixlp", "")
            if not self.env.is_set("nonlp"):
                self.env.set_local("nonlp", "")
            # * if ETL or DSC with binary variables use MIP
            if self.env.damage == "NLP":
                self.env.set_local("nonlp", "NL")
            if self.env.micro == "YES":
                self.env.set_local("nonlp", "NL")
            if self.env.macro == "YES":
                self.env.set_local("nonlp", "NL")
            if self.env.etl == "YES":
                self.env.set_local("mixlp", "MI")
            if self.env.solmip == "YES":
                self.env.set_local("mixlp", "MI")
            self.env.set_local("method", f"{self.env.mixlp}{self.env.nonlp}P")
            if self.env.method == "P":
                self.env.set_local("method", "LP")

            if self.env.macro.upper() == "YES":
                self.tc.enqueue(
                    self.solve_times,
                    model_name=self.model_name,
                    method=self.env.method,
                )
                # GOTO CHECK
            else:
                self.tc.enqueue(
                    self.solve_times_as_lp_mip,
                    model_name=self.model_name,
                    method=self.env.method,
                    equations=self.equations,
                )

            # LABEL CHECK
            self.include(
                ErrStatMod(
                    self.tc,
                    self.env,
                    arg1="SOLVE",
                    arg2="*** ERRORS DURING SOLUTION ***",
                )
            )
            # NOTE: www_out.cgi does not exist. Skipping
            # * hook for GAMS-CGI WWW output
            # $  IF %GAMS_CGI% == WWW  $BATINCLUDE www_out.cgi

    def set_model_param(self: SolveMod, model_name: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*  get the optimizer directive file
{model_name}.OPTFILE = OPTFILEID;
{model_name}.PRIOROPT=(OPTFILEID=2);
* set the model solver status
{model_name}.MODELSTAT = 0;
{model_name}.TOLPROJ= 1e-8;
""",
        )

    def solve_times(self: SolveMod, model_name: str, method: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
SOLVE {model_name} MAXIMIZING VAR_UTIL USING {method};
""",
        )

    def solve_times_as_lp_mip(
        self: SolveMod, model_name: str, method: str, equations: list[str]
    ) -> None:
        """solve TIMES as an LP/MIP"""
        eqs = [self.tc.container[e] for e in equations]
        obj = self.tc.container["OBJZ"]
        model = Model(
            container=self.tc.container,
            name=model_name,
            problem=method,
            equations=eqs,
            sense="MIN",
            objective=obj,
        )

        set_options({"VALIDATION": 0})

        # solve with convert
        model.solve(
            solver="convert",
            solver_options={"DumpGDX": self.tc.output_convert},
            output=sys.stdout,
        )

        # regular solve
        model.solve(solver="cplex", output=sys.stdout, options=self.tc.solve_options)


def solve_mod(
    *,
    model_name: str,
    solve_now: str,
    damage: str,
    micro: str,
    macro: str,
    etl: str,
    solmip: str,
    memclean: str,
    err_abort: str,
    mixlp: str = "",
    nonlp: str = "",
    gams_cgi: str = "",
) -> str:
    uses_nlp = damage == "NLP" or micro == "YES" or macro == "YES"

    uses_mip = etl == "YES" or solmip == "YES"

    effective_nonlp = "NL" if uses_nlp else nonlp
    effective_mixlp = "MI" if uses_mip else mixlp

    method = f"{effective_mixlp}{effective_nonlp}P"
    if method == "P":
        method = "LP"

    solve_stmt = (
        "SOLVE " + model_name + " MAXIMIZING VAR_UTIL USING " + method + ";"
        if macro.upper() == "YES"
        else f"* solve TIMES as an LP/MIP\nSOLVE {model_name} MINIMIZING objZ USING {method};"
    )

    return rf"""
* Release some memory
{pp_clean_mod(memclean=memclean)}

*  get the optimizer directive file
{model_name}.OPTFILE = OPTFILEID;
{model_name}.PRIOROPT=(OPTFILEID=2);
* set the model solver status
{model_name}.MODELSTAT = 0;
{model_name}.TOLPROJ= 1e-8;

* MACRO: Loading solution from GDX file replaced by activating the SPOINT utility
{
        ""
        if solve_now == "NO"
        else rf'''
{solve_stmt}

* do an check on solution errors
'''
    }
"""


# TODO: that needs a standalone implementation!
# {
#             err_stat_solve(module=module,
#                 arg2="*** ERRORS DURING SOLUTION ***",
#                 model_name=model_name,
#                 err_abort=err_abort,
#             )
#         }
