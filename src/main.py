# main.py

import logging
import os
import sys
from pathlib import Path

from gamspy import Alias, Container, Options, Set, UniverseAlias

from core import demo12_dd, initmty_mod, initsys_mod, maindrv_mod
from core.compile_environment import CompileEnvironment
from core.times_model_class import TimesModelClass
from core.utils import EscapeStack

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


def load_data(model: TimesModelClass, gdx_file: Path) -> None:
    """Central data-loading step. (Loading .dd files)"""
    model.logger.info("Reading data...")

    m = model.container
    t = Container(load_from=gdx_file)

    for name, symbol in t.data.items():
        if not isinstance(symbol, (Alias, UniverseAlias)) and name in m.data:
            m[name].records = symbol.records

    model.logger.info("Data loading complete.")


def main(
    output_compile: Path = Path("compile_gamspy.gdx"),
    output_execute: Path = Path("execute_gamspy.gdx"),
    test: bool = False,
) -> None:
    logging.info("Starting TIMES.")

    # Initialize Core
    env = CompileEnvironment()
    model = TimesModelClass(env, output_compile, output_execute, test)

    # Set Options
    model._solve_options = Options(
        time_limit=50000,
        profile=1,
        merge_strategy="replace",
        iteration_limit=999999,
        equation_listing_limit=0,
        variable_listing_limit=0,
        report_solution=0,
        lp="CBC",
        basis_detection_threshold=1,
    )

    # User settings
    # reduction of equation system
    env.set_scoped("reduce", "YES")

    # initialize the environment variables
    env.set_scoped("dscauto", "YES")
    env.set_scoped("vda", "YES")
    env.set_scoped("debug", "NO")
    env.set_scoped("dumpsol", "NO")
    env.set_scoped("solve_now", "YES")
    env.set_scoped("xtqa", "YES")

    # VAR_UC being set so that non-binding constraints appear in results
    env.set_scoped("var_uc", "YES")
    env.set_scoped("obj", "MOD")
    env.set_scoped("solveda", "YES")
    env.set_scoped("datagdx", "YES")

    # load demo12ts.dd
    # the times-slices MUST come 1st to ensure ordering OK
    model.all_ts = Set(
        container=model.container,
        name="ALL_TS",
        records=[
            "ANNUAL",
            "S",
            "W",
            "SD",
            "SN",
            "WD",
            "WN",
        ],
    )

    env.set_scoped("botime", "1960")
    if model.test_run:
        model.save_test_state(
            env=env, checkpoint="demo12_run_prior_batinclude_initsys_mod"
        )

    # perform fixed declarations
    model.register_module(initsys_mod.InitsysMod(tc=model, env=env))

    if model.test_run:
        model.save_test_state(
            env=env, checkpoint="demo12_run_prior_batinclude_initmty_mod"
        )

    # declare the (system/user) empties
    model.register_module(initmty_mod.InitmtyMod(tc=model, env=env))

    if model.test_run:
        model.save_test_state(env=env, checkpoint="demo12_run_prior_dd_files")

    # Central data load (DD files)
    model.register_module(demo12_dd.Demo12DD(tc=model, env=env))

    # Reduced model to fit with GAMS community license
    # SET MILESTONYR /2005,2010,2015,2020,2030,2050/;
    milestonyr = model.container["MILESTONYR"]
    milestonyr.setRecords([2005, 2010, 2015, 2020, 2030, 2050])

    env.set_scoped("run_name", "demo12")
    env.set_scoped("vedavdd", "YES")

    if model.test_run:
        model.save_test_state(env=env, checkpoint="demo12_run_prior_maindrv_mod")

    try:
        model.register_module(maindrv_mod.MainDrvMod(tc=model, env=env, arg1="mod"))
    except EscapeStack as e:
        print("Escape Stack", e)

    # write GDX
    model.initialization()

    # execution code blocks
    model.run()

    # Debug: dump generated GAMS
    # model.dump_generated_gams("generated_times.gms")

    return model


if __name__ == "__main__":
    result = main()
