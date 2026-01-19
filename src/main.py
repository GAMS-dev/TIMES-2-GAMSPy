# main.py

import logging
import os
import sys
from pathlib import Path

from gamspy import Alias, Container, Options, Set, UniverseAlias

from core import initsys_mod
from core.compile_environment import CompileEnvironment
from core.times_model_class import TimesModelClass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def register_modules(model: TimesModelClass, env: CompileEnvironment) -> None:
    # 1. Essential Base Modules
    base_modules = [
        initsys_mod
        # , initmty
    ]
    for mod in base_modules:
        model.register_module(mod.module)

    # 2. Optional Feature Modules (Flag -> Module Mapping)
    # feature_map = {
    #     "dsc": initmty_dsc,
    #     "vda": initmty_vda,
    #     "cli": initmty_cli,
    #     "stages": initmty_stc,
    #     "etl": initmty_etl,
    #     "abs": initmty_abs,
    #     "ier": initmty_ier,
    # }

    # for flag, mod in feature_map.items():
    #     if getattr(env, flag, False):
    #         model.register_module(mod.module)

    # 3. Macro Selection Logic
    # macro_map = {
    #     "MSA": initmty_msa.module,
    #     "MLF": initmty_mlf.module,
    #     "YES": initmty_tm.module,
    #     "CSA": initmty_tm.module,
    # }

    # macro_version = (env.macro or "").upper()
    # if macro_mod := macro_map.get(macro_version):
    #     model.register_module(macro_mod)

    # 4. Finalization
    # model.register_module(setglobs.module)


def load_data(model: TimesModelClass) -> None:
    """Central data-loading step."""
    model.logger.info("Reading data...")

    gdx_path = os.path.join(os.getcwd(), "src", "data", "demo12_data.gdx")
    tmp = Container(gdx_path)

    known_symbols = model.container.listSymbols()
    symbols_in_gdx = tmp.listSymbols()
    common_symbols = set(known_symbols) & set(symbols_in_gdx)

    # UniverseAlias symbols cannot load records
    symbols_to_load = [
        name
        for name in common_symbols
        if not isinstance(model.container[name], (UniverseAlias, Alias))
    ]

    model.container.loadRecordsFromGdx(gdx_path, symbol_names=symbols_to_load)
    model.logger.info("Data loading complete.")


def main(
    output_compile: Path = Path("compile_gamspy.gdx"),
    output_execute: Path = Path("execute_gamspy.gdx"),
) -> None:
    logging.info("Starting TIMES.")

    # Initialize Core
    env = CompileEnvironment()
    model = TimesModelClass(env, output_compile, output_execute)

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
    env.set_scoped("reduce", True)

    # initialize the environment variables
    env.set_scoped("dscauto", True)
    env.set_scoped("vda", True)
    env.set_scoped("debug", False)
    env.set_scoped("dumpsol", False)
    env.set_scoped("solve_now", True)
    env.set_scoped("xtqa", True)

    # VAR_UC being set so that non-binding constraints appear in results
    env.set_scoped("var_uc", True)
    env.set_scoped("obj", "MOD")
    env.set_scoped("solveda", True)
    env.set_scoped("datagdx", True)

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

    env.set_scoped("botime", 1960)

    model.register_module(initsys_mod.InitsysMod(tc=model, env=env))
    model.initialization()

    # # Central data load
    # load_data(model)

    # # Phase 2: post-load compile-like steps
    # model.initialize_postload()

    # Phase 3: execution code blocks / solve / reports
    model.run()

    # Debug: dump generated GAMS
    model.dump_generated_gams("generated_times.gms")


if __name__ == "__main__":
    main()
