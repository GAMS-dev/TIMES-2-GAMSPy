# initmty_abs.py

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .interfaces import TimesModule

if TYPE_CHECKING:
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

GAMS_SOURCE = "initmty_abs.mod"


@dataclass(frozen=True)
class InitmtyAbsModule(TimesModule):
    """Translation unit for initmty_abs.mod."""

    def initialize_preload(self, tc: "TimesModelClass") -> None:
        # --- BEGIN GAMS (compile) ---
        tc.add_gams_code(
            module_name="initmty_abs",
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
            module_name="initmty_abs",
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
            module_name="initmty_abs",
            phase="run",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> execution-time GAMS code (preprocessing/solve/report)
""",
        )
        # --- END GAMS (execute) ---


module: TimesModule = InitmtyAbsModule()
