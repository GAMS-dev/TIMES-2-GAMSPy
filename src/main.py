# main.py
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from gamspy import Options

from core.initmty_mod import InitmtyMod
from core.initsys_mod import InitsysMod
from core.maindrv_mod import MainDrvMod
from core.read_dd import read_dd_file
from core.utils import EscapeStack
from utils.compile_environment import CompileEnvironment
from utils.config import RunConfig
from utils.run_registry import REGISTRY
from utils.times_model_class import TimesModelClass

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Main logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Configure the 'gams_env' logger
file_handler = logging.FileHandler("logs/missing_macros.log")
file_handler.setLevel(logging.DEBUG)  # The file catches all the small DEBUG notes

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Attach handler to our specific logger
gams_logger = logging.getLogger("gams_env")
gams_logger.setLevel(logging.DEBUG)
gams_logger.addHandler(file_handler)
gams_logger.propagate = False  # Prevent logs from doubling up in the console


def run_times(
    config: RunConfig,
    output_compile: Path = Path("compile_gamspy.gdx"),
    output_execute: Path = Path("execute_gamspy.gdx"),
    output_convert: Path = Path("convert_gamspy.gdx"),
    test: bool = False,
) -> TimesModelClass:
    logging.info(f"Starting TIMES Run: {config.run_name}")

    # Set Options
    solve_options = Options(
        time_limit=50000,
        profile=1,
        merge_strategy="replace",
        iteration_limit=999999,
        equation_listing_limit=0,
        variable_listing_limit=0,
        report_solution=0,
        lp=config.lp_solver,
        basis_detection_threshold=1,
    )

    # Initialize Core
    env = CompileEnvironment()
    model = TimesModelClass(
        env=env,
        output_compile=output_compile,
        output_execute=output_execute,
        output_convert=output_convert,
        test_run=test,
        solve_options=solve_options,
    )

    # Dynamically apply Environment Variables
    for key, value in config.env_vars.items():
        env.set_scoped(key, value)

    # env.set_scoped("botime", config.botime)
    env.set_scoped("botimeGP", int(env.botime))
    env.set_scoped("run_name", config.run_name)

    # Dynamically apply Time Slices
    read_dd_file(tc=model, dd_path=config.time_slices)
    model.allts = model.container["ALL_TS"]

    try:
        # perform fixed declarations
        model.register_module(InitsysMod(tc=model, env=env))
        # raise EscapeStack('here')

        # declare the (system/user) empties
        model.register_module(InitmtyMod(tc=model, env=env))

        # Central data load (DD files)
        for file in config.data_modules:
            read_dd_file(tc=model, dd_path=file)

        # Reduced model to fit with GAMS community license
        milestonyr = model.container["MILESTONYR"]
        milestonyr.setRecords(config.milestone_years)

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
        choices=REGISTRY.keys(),
        help="Name of the run instance to execute",
    )
    args = parser.parse_args()

    run_config: RunConfig = REGISTRY[args.run]
    result = run_times(config=run_config)
