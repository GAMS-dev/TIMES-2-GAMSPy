# main.py
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import tomllib
from pathlib import Path

from gamspy import Options, Set, set_options
from pydantic import ValidationError

from core.initmty_mod import InitmtyMod
from core.initsys_mod import InitsysMod
from core.maindrv_mod import MainDrvMod
from core.pp_qaput_mod import QALogger
from core.read_dd import read_dd_file
from core.utils import EscapeStack
from utils.compile_environment import CompileEnvironment
from utils.config import DEFAULT_OPTIONS, RunConfig, UserConfig
from utils.macros import macro_config as macro
from utils.run_registry import REGISTRY, load_run_file
from utils.times_model_class import TimesModelClass

# GAMSPy options
set_options(
    {
        "STRICT_POWER_OPERATOR": 1  # Maps ** to GAMS rPower for every exponent
    }
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Main logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def run_times(
    config: RunConfig,
    output_compile: Path = Path("compile_gamspy.gdx"),
    output_execute: Path = Path("execute_gamspy.gdx"),
    output_convert: Path = Path("convert_gamspy.gdx"),
    test: bool = False,
    solve: bool = True,
) -> TimesModelClass:
    logging.info(f"Starting TIMES Run: {config.run_name}")

    # Set Options, by their GAMS names: the run file's OPTION statements on top
    # of the defaults, then the solvers (None: the default) and the output files
    solve_options = Options.fromGams(
        {
            **DEFAULT_OPTIONS,
            **config.options,
            "lp": config.lp_solver,
            "mip": config.lp_solver,
            "nlp": config.nlp_solver,
            "logfile": f"{config.run_name}.log",
            "output": f"{config.run_name}.lst",
        }
    )

    # Initialize Core
    env = CompileEnvironment()
    model = TimesModelClass(
        env=env,
        output_compile=output_compile,
        output_execute=output_execute,
        output_convert=output_convert,
        test_run=test,
        solve=solve,
        solve_options=solve_options,
        config=config,
        pp_qaput_logger=QALogger(),
    )

    # Add Times Model Class to macros
    macro.bind(model)

    # Dynamically apply non default %<key>% Environment Variables
    validated_config = UserConfig.model_validate(config.env_vars)
    full_dump = validated_config.model_dump(by_alias=True)
    clean_dump = {}
    for alias_key, value in full_dump.items():
        if not env.is_default(key=alias_key, val=value):
            clean_dump[alias_key] = value
    for key, value in clean_dump.items():
        env.set_scoped(key, value)

    env.set_scoped("run_name", config.run_name)

    # Dynamically apply Time Slices
    read_dd_file(tc=model, dd_path=Path(config.data_dir, config.time_slices))
    all_ts = model.container["ALL_TS"]
    assert isinstance(all_ts, Set)
    model.allts = all_ts

    try:
        # perform fixed declarations
        model.register_module(InitsysMod(tc=model, env=env))

        # declare the (system/user) empties
        # IER has no %IER%==YES switch -- it's activated positionally, mirroring
        # `$BATINCLUDE initmty.mod IER` in the .run file.
        initmty_arg1 = "IER" if config.env_vars.ier.upper() == "YES" else ""
        model.register_module(InitmtyMod(tc=model, env=env, arg1=initmty_arg1))

        # Reduced model to fit with GAMS community license. Mirrors the .run
        # files' `SET MILESTONYR /.../;`, which is placed right after
        # `$BATINCLUDE initmty.mod` and before all the data BATINCLUDEs -- some
        # data modules assign over T (the alias of MILESTONYR) and require it
        # to already hold its final records.
        milestonyr = model.container["MILESTONYR"]
        assert isinstance(milestonyr, Set)
        milestonyr.setRecords(config.milestone_years)

        # Central data load (DD files)
        for file in config.data_modules:
            read_dd_file(tc=model, dd_path=Path(config.data_dir, file))

        model.register_module(MainDrvMod(tc=model, env=env, arg1="mod"))

    except EscapeStack as e:
        print("Escape Stack", e)

    # write GDX
    model.initialization()

    # execution code blocks
    model.run()

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a TIMES model instance.")
    parser.add_argument(
        "--run",
        type=str,
        required=True,
        help="Instance to execute: a name from the built-in registry or the path "
        "to a TOML run file (*.toml).",
    )
    parser.add_argument(
        "--skip-solve",
        action="store_false",
        help="Skip solve and use savepoint file.",
    )
    parser.add_argument(
        "--lp-solver",
        type=str,
        default=None,
        help="LP/MIP solver to use instead of the instance's lp_solver "
        "('default' for the system default).",
    )
    parser.add_argument(
        "--nlp-solver",
        type=str,
        default=None,
        help="NLP solver to use instead of the instance's nlp_solver "
        "('default' for the system default).",
    )
    args = parser.parse_args()

    if args.run.endswith(".toml"):
        try:
            run_config = load_run_file(Path(args.run))
        except (OSError, tomllib.TOMLDecodeError, ValidationError) as e:
            parser.error(f"cannot load run file {args.run}:\n{e}")
    elif args.run in REGISTRY:
        run_config = REGISTRY[args.run]
    else:
        parser.error(f"'{args.run}' is neither a registry instance nor a .toml file")
    for field in ("lp_solver", "nlp_solver"):
        if solver := getattr(args, field):
            solver = None if solver.lower() == "default" else solver
            run_config = run_config.model_copy(update={field: solver})

    start = time.time()
    result = run_times(config=run_config, solve=args.skip_solve)
    gamspy_time = time.time() - start

    print(f"GAMSPy Performance: {gamspy_time}s")
