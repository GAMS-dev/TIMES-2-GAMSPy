# main_ext_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MAIN_EXT.mod is the extension driver
# *=============================================================================*
# * %1 is the name of the extension module to be called, e.g. 'rpt_ext' for reporting extensions
# * Different extensions are identified by file extensions given in %2, %3, %4....%9
# * Example: $BATINCLUDE rpt_ext ETL RP1 RP2
# *          This would include the reporting extensions for ETL and two custom
# *          reporting routines rpt_ext.RP1 and rpt_ext.RP2
# *-----------------------------------------------------------------------------


import logging
from typing import TYPE_CHECKING, List

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class MainExtMod(GamsClass):
    """Translation unit for main_ext.mod."""

    # Instance attributes
    module_name: str = "main_ext_mod"
    gams_source: str = "main_ext.mod"

    def __init__(
        self, tc: "TimesModelClass", env: "CompileEnvironment", extensions: List
    ):
        self.env = env.fork()
        self.extension_list = extensions
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        tc.add_gams_code(
            module=self, phase=phase, code=r"$SETNAMES '%SYSTEM.INCPARENT%' . TMP ."
        )

        # Include extensions
        for ext in self.extension_list:
            self.include(ext(tc=tc, env=self.env))
