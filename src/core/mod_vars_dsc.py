# mod_vars_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.EXT EXTENSION VARIABLES
# * called from MAINDRV.MOD
# *=============================================================================*
# *-----------------------------------------------------------------------------*
# * Discrete capacity extensions
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsDsc(GamsClass):
    """Translation unit for mod_vars.dsc."""

    # Instance attributes
    module_name: str = "mod_vars_dsc"
    gams_source: str = "mod_vars.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        self.env.set_global("semicont", "SEMICONT")
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Investments
SOS1 VARIABLE {self.env.var}_DNCAP(R,ALLYEAR,P{self.env.swd},UNIT);
{self.env.semicont} VARIABLE {self.env.var}_SNCAP(R,ALLYEAR,P{self.env.swd});
""",
        )
        self.tc.enqueue(
            self.mod_vars_dsc_exec,
            var=self.env.var,
            sow=self.env.sow,
        )

    def mod_vars_dsc_exec(
        self: ModVarsDsc,
        var: str,
        sow: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Bounds for semicont
{var}_SNCAP.LO(R,T,P{sow}) $= NCAP_SEMI(R,T,P);
{var}_SNCAP.UP(R,T,P{sow})$NCAP_SEMI(R,T,P) = MAX(NCAP_SEMI(R,T,P),NCAP_BND(R,T,P,'UP'));
""",
        )
