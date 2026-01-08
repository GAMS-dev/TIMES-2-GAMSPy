# initsys.py

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import globals, maplists, units
from .interfaces import TimesModule

if TYPE_CHECKING:
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

GAMS_SOURCE = "initsys.mod"


@dataclass(frozen=True)
class InitsysModule(TimesModule):
    """Translation unit for INITSYS.MOD."""

    def initialize_preload(self, tc: "TimesModelClass") -> None:
        # Embed original GAMS file (kept 1:1, with $BATINCLUDE and YEARVAL assignment commented out).
        tc.add_gams_code(
            module_name="initsys",
            phase="initialize_preload",
            gams_source=GAMS_SOURCE,
            code=r"""*test""",
        )

        # get list of default units
        units.module.initialize_preload(tc)

        # get list of default mapping group lists
        maplists.module.initialize_preload(tc)

        # get default global scalars and parameters
        globals.module.initialize_preload(tc)

    def initialize_postload(self, tc: "TimesModelClass") -> None:
        return

    def run(self, tc: "TimesModelClass") -> None:
        return


module: TimesModule = InitsysModule()
