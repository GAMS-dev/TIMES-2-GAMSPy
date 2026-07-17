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

from gamspy import Variable
from gamspy.math import Max

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        g = self.tc
        m = g.container

        self.env.set_global("semicont", "SEMICONT")

        # Investments
        g.VAR_DNCAP = Variable(
            m, "VAR_DNCAP", domain=[g.r, g.allyear, g.p, g.unit], type="SOS1"
        )
        g.VAR_SNCAP = Variable(
            m, "VAR_SNCAP", domain=[g.r, g.allyear, g.p], type="SEMICONT"
        )

        self.tc.enqueue(self.mod_vars_dsc_exec)

    def mod_vars_dsc_exec(self) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        g.VAR_SNCAP.lo[r, t, p].where[g.ncap_semi[r, t, p]] = g.ncap_semi[r, t, p]
        g.VAR_SNCAP.up[r, t, p].where[g.ncap_semi[r, t, p]] = Max(
            g.ncap_semi[r, t, p], g.ncap_bnd[r, t, p, "UP"]
        )
