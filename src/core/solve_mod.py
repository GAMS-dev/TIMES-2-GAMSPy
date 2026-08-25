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
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Equation, Model, ModelStatus, Options, set_options

from core.base_class import GamsClass
from core.err_stat_mod import ErrStatMod
from core.pp_clean_mod import PpCleanMod, pp_clean_mod

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
        self.tc.enqueue(set_model_param, module=self, model_name=self.model_name)

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
                    solve_times,
                    module=self,
                    model_name=self.model_name,
                    method=self.env.method,
                    equations=self.equations,
                )
                # GOTO CHECK
            else:
                self.tc.enqueue(
                    solve_times_as_lp_mip,
                    module=self,
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


def set_model_param(module: GamsClass, model_name: str) -> None:
    module.tc.add_gams_code(
        module=module,
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


def write_run_solver_options(g: TimesModelClass, solver: str) -> None:
    """Make the run's solver option file visible to raw GAMS ``SOLVE`` statements.

    The emitted code sets ``<model>.optfile = 1``, so GAMS looks for ``<solver>.opt``
    in its own option directory -- for a GAMSPy-generated job that is a scratch
    directory, not the run's data directory the reference GAMS run receives via
    ``OptDir=``. Without this the solver silently falls back to its defaults, and on a
    degenerate LP that alone is enough to settle on a different (equally optimal)
    vertex. The solves GAMSPy owns get the same file through
    :func:`solve_times_as_lp_mip`.
    """
    option_file = Path(g.config.data_dir, f"{solver}.opt")
    if not option_file.is_file():
        logger.warning(
            "No %s option file at %s; the emitted SOLVE will use solver defaults.",
            solver,
            option_file,
        )
        return

    # Copied rather than routed through Container.writeSolverOptions(), which
    # validates entries and rejects files GAMS itself merely warns about (e.g.
    # cplex' "iis yes"). GAMS resolves optfile against its option directory, which
    # defaults to the working directory GAMSPy runs every generated job in.
    shutil.copyfile(option_file, Path(g.container.working_directory, option_file.name))


def convert_dump_gams_code(
    *, model_name: str, method: str, convert_gdx: Path, lp_solver: str
) -> str:
    """GAMS code that dumps the generated LP/MIP through the CONVERT solver.

    This is the translation of solve.mod lines 38-48: write a ``convert.opt``
    holding ``DumpGDX``, solve once with ``lp/mip=convert`` so CONVERT writes the
    matrix to that GDX, then restore the real solver for the solve that follows.

    Needed by the code paths that emit a raw GAMS ``SOLVE`` (the SOW loops in
    solve.stc). Where GAMSPy owns the solve it dumps natively instead, via
    ``model.solve(solver="convert", solver_options={"DumpGDX": ...})`` -- see
    :func:`solve_times_as_lp_mip`.

    The GDX path is made absolute because the emitted code runs in GAMS' own
    working directory, which is not the process' working directory.
    """
    # GAMS hardcodes `option lp=cplex, mip=cplex` here; restore what the run
    # actually configured instead.
    solver = lp_solver.lower()
    return rf"""
$onEcho > %gams.optDir%%system.dirSep%convert.opt
DumpGDX {Path(convert_gdx).resolve().as_posix()}
!dict {model_name}_dict.txt
$offEcho

{model_name}.optfile = 1;
*{model_name}.dictfile = 1;
option lp=convert, mip=convert;
SOLVE {model_name} MINIMIZING objZ USING {method};

option lp={solver}, mip={solver};
"""


def solve_times(
    module: GamsClass, model_name: str, method: str, equations: list[str]
) -> None:
    eqs: Sequence[Equation] = [module.tc.container[e] for e in equations]  # type: ignore[misc]
    model = Model(
        container=module.tc.container,
        name=model_name,
        problem=method,
        equations=eqs,
        sense="MAX",
        objective=module.tc.VAR_UTIL,
    )

    # dump the algebraic model representation before the real solve, mirroring
    # solve_times_as_lp_mip's convert step for the LP/MIP path
    model.solve(
        solver="convert",
        solver_options={"DumpGDX": module.tc.output_convert},
        output=sys.stdout,
    )

    # solve.mod hardcodes `option lp=cplex, nlp=conopt;` for this branch (unlike
    # the LP/MIP branch's `option lp=cplex, mip=cplex;`, which mirrors the
    # *configured* lp_solver) -- mirror that literally rather than assuming
    # config.lp_solver applies to an NLP method. Use write_run_solver_options
    # (copies the file into GAMS' own optDir) rather than model.solve's
    # solver_options=, which routes through GAMSPy's own stricter option-file
    # validation and hard-errors on entries GAMS itself merely warns about
    # (e.g. cplex' "iis yes").
    solver = "conopt" if "NL" in method else module.tc.config.lp_solver.lower()
    write_run_solver_options(module.tc, solver)
    model.solve(output=sys.stdout, options=module.tc.solve_options)


def solve_times_as_lp_mip(
    module: GamsClass, model_name: str, method: str, equations: list[str]
) -> None:
    """solve TIMES as an LP/MIP"""
    eqs: Sequence[Equation] = [module.tc.container[e] for e in equations]  # type: ignore[misc]
    obj = module.tc.OBJZ
    model = Model(
        container=module.tc.container,
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
        solver_options={
            "DumpGDX": module.tc.output_convert,
            # "dict": "dict.txt"
        },
        output=sys.stdout,
    )

    # regular solve
    if module.tc.solve:
        solver = module.tc.config.lp_solver.lower()
        model.solve(
            output=sys.stdout,
            options=module.tc.solve_options,
            solver_options=Path(module.tc.config.data_dir, f"{solver}.opt"),
        )
    else:
        model.solve(
            output=sys.stdout,
            options=Options(
                bypass_solver=True,
                loadpoint=Path(module.tc.config.data_dir, "times_p2.gdx"),
            ),
        )
        fake_file = Path(module.tc.config.data_dir, "times_modelstat.inc")
        # fake model status in GAMS
        module.tc.container.addGamsCode(f"$include {fake_file}")

        # fake model status in GAMSPy
        with open(fake_file) as f:
            s = f.read()
        match = re.search(r"=\s*(\d+);", s)
        if match:
            value = int(match.group(1))
            model._status = ModelStatus(value)


def solve_mod_GP(
    module: GamsClass,
    model_name: str,
    equations: list[str],
    memclean: str,
    solve_now: str,
    mixlp: str,
    nonlp: str,
    damage: str,
    micro: str,
    macro: str,
    etl: str,
    solmip: str,
) -> None:
    # Release some memory
    pp_clean_mod(tc=module.tc, memclean=memclean)
    set_model_param(module=module, model_name=model_name)

    if solve_now != "NO":
        # Evaluate mixlp and nonlp states
        mix_str = (
            "MI" if "YES" in (etl, solmip) else ("" if mixlp == "%MIXLP%" else mixlp)
        )
        non_str = (
            "NL"
            if (damage == "NLP" or "YES" in (micro, macro))
            else ("" if nonlp == "%NONLP%" else nonlp)
        )

        # Combine and resolve the optimization method type
        method = f"{mix_str}{non_str}P"
        method = "LP" if method == "P" else method

        if macro.upper() == "YES":
            solve_times(
                module=module,
                model_name=model_name,
                method=method,
                equations=equations,
            )
        else:
            solve_times_as_lp_mip(
                module=module, model_name=model_name, method=method, equations=equations
            )


def solve_mod(
    *,
    g: TimesModelClass,
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

    if macro.upper() == "YES":
        solve_stmt = (
            "SOLVE " + model_name + " MAXIMIZING VAR_UTIL USING " + method + ";"
        )

    else:
        solver = g.config.lp_solver.lower()
        write_run_solver_options(g, solver)
        convert_dump = convert_dump_gams_code(
            model_name=model_name,
            method=method,
            convert_gdx=g.output_convert,
            lp_solver=solver,
        )
        if g.solve:
            solve_stmt = f"""
{convert_dump}
* solve TIMES as an LP/MIP
SOLVE {model_name} MINIMIZING objZ USING {method};
"""
        else:
            savepoint_path = Path(g.config.data_dir, "times_p2.gdx").absolute()
            modelstat_path = Path(g.config.data_dir, "times_modelstat.inc").absolute()
            solve_stmt = f"""
{convert_dump}
* generate model but do not pass it to the solver
  {model_name}.JustScrDir=1;
  SOLVE {model_name} MINIMIZING objZ USING {method};
* load solution file and fake modelstatus from "real" solve
  execute_loadpoint '{savepoint_path}';
  $$include {modelstat_path}
"""

    # Release some memory
    pp_clean_mod(tc=g, memclean=memclean)
    return rf"""
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
