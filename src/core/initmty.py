# initmty.py

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .interfaces import TimesModule

if TYPE_CHECKING:
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

GAMS_SOURCE = "initmty.mod"


@dataclass(frozen=True)
class InitmtyModule(TimesModule):
    """Translation unit for initmty.mod."""

    def initialize_preload(self, tc: "TimesModelClass") -> None:
        tc.add_gams_code(
            module_name="initmty",
            phase="initialize_preload",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> GAMS code (before data load)
""",
        )

    def initialize_postload(self, tc: "TimesModelClass") -> None:
        tc.add_gams_code(
            module_name="initmty",
            phase="initialize_postload",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> GAMS code(after data load)
""",
        )

    def run(self, tc: "TimesModelClass") -> None:
        tc.add_gams_code(
            module_name="initmty",
            phase="run",
            gams_source=GAMS_SOURCE,
            code=r"""
* >>> execution-time GAMS code (preprocessing/solve/report)
""",
        )


module: TimesModule = InitmtyModule()
