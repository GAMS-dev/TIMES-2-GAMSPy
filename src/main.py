# main.py
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from gamspy import Options, Set

from core.initmty_mod import InitmtyMod
from core.initsys_mod import InitsysMod
from core.maindrv_mod import MainDrvMod
from core.read_dd import read_dd_file
from core.utils import EscapeStack
from utils.compile_environment import CompileEnvironment
from utils.config import RunConfig, UserConfig
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


def run_times(
    config: RunConfig,
    output_compile: Path = Path("compile_gamspy.gdx"),
    output_execute: Path = Path("execute_gamspy.gdx"),
    output_convert: Path = Path("convert_gamspy.gdx"),
    test: bool = False,
    solve: bool = True,
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
        solve=solve,
        solve_options=solve_options,
        config=config,
    )

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
        model.register_module(InitmtyMod(tc=model, env=env))

        # Central data load (DD files)
        for file in config.data_modules:
            read_dd_file(tc=model, dd_path=Path(config.data_dir, file))

        # Reduced model to fit with GAMS community license
        milestonyr = model.container["MILESTONYR"]
        assert isinstance(milestonyr, Set)
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

    start = time.time()
    result = run_times(config=run_config)
    gamspy_time = time.time() - start

    print(f"GAMSPy Performance: {gamspy_time}s")
