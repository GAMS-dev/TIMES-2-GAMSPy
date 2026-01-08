# main.py
# Orchestration:
#   1) Register modules (ORDER MATTERS)
#   2) model.initialize_preload()
#   3) load_data(model)
#   4) model.initialize_postload()
#   5) model.run()

import logging
import os
import sys

from gamspy import Alias, Container, UniverseAlias

from core import (
    initmty,
    initmty_abs,
    initmty_cli,
    initmty_dsc,
    initmty_etl,
    initmty_ier,
    initmty_mlf,
    initmty_msa,
    initmty_stc,
    initmty_tm,
    initmty_vda,
    initsys,
    setglobs,
)
from core.config import TimesConfig
from core.times_model_class import TimesModelClass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def register_modules(model: TimesModelClass, config: TimesConfig) -> None:
    # 1. Essential Base Modules
    base_modules = [initsys, initmty]
    for mod in base_modules:
        model.register_module(mod.module)

    # 2. Optional Feature Modules (Flag -> Module Mapping)
    feature_map = {
        "dsc": initmty_dsc,
        "vda": initmty_vda,
        "cli": initmty_cli,
        "stages": initmty_stc,
        "etl": initmty_etl,
        "abs": initmty_abs,
        "ier": initmty_ier,
    }

    for flag, mod in feature_map.items():
        if getattr(config, flag, False):
            model.register_module(mod.module)

    # 3. Macro Selection Logic
    macro_map = {
        "MSA": initmty_msa.module,
        "MLF": initmty_mlf.module,
        "YES": initmty_tm.module,
        "CSA": initmty_tm.module,
    }

    macro_version = (config.macro or "").upper()
    if macro_mod := macro_map.get(macro_version):
        model.register_module(macro_mod)

    # 4. Finalization
    model.register_module(setglobs.module)


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


def main() -> None:
    # Setup Config
    config = TimesConfig(run_name="demo12", botime=1960)
    logging.info(f"Starting TIMES {config.run_name}.")

    # Initialize Core
    model = TimesModelClass(config)

    register_modules(model, config)

    # Phase 1: pre-load
    model.initialize_preload()

    # Central data load
    load_data(model)

    # Phase 2: post-load compile-like steps
    model.initialize_postload()

    # Phase 3: execution code blocks / solve / reports
    model.run()

    # Debug: dump generated GAMS
    # model.dump_generated_gams("generated_times.gms")

    model.container.write("gamspy_output.gdx")


if __name__ == "__main__":
    main()
