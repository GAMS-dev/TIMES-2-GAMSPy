# globals_def.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * GLOBALS.DEF has all the declaration & defaults for SCALARS & Parameters      *
# *==============================================================================*


import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Globals(GamsClass):
    """Translation unit for globals.def."""

    # Instance attributes
    module_name: str = "globals"
    gams_source: str = "globals.def"

    def __init__(self, tc: "TimesModelClass", env: "CompileEnvironment"):
        self.env = env.fork()
        self.snapshot = None
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
* global initialization and other scalar defaults which may be changed here
*  or overwritten in the user *.DD
  SCALAR G_DYEAR     'Year to discount to'                          / 0 /;
  SCALAR G_ILEDNO    '1/threshold at which to ignore ILED'          / 10 /;
  SCALAR G_TLIFE     'Default technology life if not provided'      / 10 /;
  SCALAR G_VINT      '% annual change in input data for vintaging'  / .1 /;
  SCALAR G_NOINTERP  'Turn off interplation'                        / 0 /;
  PARAMETER G_CYCLE(TSLVL) 'Number of cycles in average year' / ANNUAL 1, SEASON 1, DAYNITE 365 /;
""",
        )
