# ppmain.py

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base_class import TimesModule

if TYPE_CHECKING:
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

GAMS_SOURCE = "ppmain.mod"  #


@dataclass(frozen=True)
class ppmainModule(TimesModule):
    """Translation unit for ppmain.mod."""

    def compile(self, tc: "TimesModelClass") -> None:
        # --- BEGIN GAMS (compile) ---
        tc.add_gams_code(
            module_name="ppmain",
            phase="initialize_preload",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> compile-time GAMS code (before data load)
""",
        )
        # --- END GAMS (compile) ---

    def initialize_postload(self, tc: "TimesModelClass") -> None:
        # --- BEGIN GAMS (initialize_postload) ---
        tc.add_gams_code(
            module_name="ppmain",
            phase="initialize_postload",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> compile-time GAMS code (after data load)
""",
        )
        # --- END GAMS (initialize_postload) ---

    def run(self, tc: "TimesModelClass") -> None:
        # --- BEGIN GAMS (execute) ---
        tc.add_gams_code(
            module_name="ppmain",
            phase="run",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> execution-time GAMS code (preprocessing/solve/report)
""",
        )
        # --- END GAMS (execute) ---


module: TimesModule = ppmainModule()
