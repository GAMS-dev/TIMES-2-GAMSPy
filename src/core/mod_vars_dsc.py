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

from gamspy import Alias, Set, Variable, sparse
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

        var = self.env.var
        swd = self.env.swd_GP

        # Investments
        g.set_variable(
            name=f"{var}_DNCAP",
            var=Variable(
                m,
                name=f"{var}_DNCAP",
                domain=[g.r, g.allyear, g.p, *swd, g.unit],
                type="SOS1",
            ),
        )
        g.set_variable(
            name=f"{var}_SNCAP",
            var=Variable(
                m,
                name=f"{var}_SNCAP",
                domain=[g.r, g.allyear, g.p, *swd],
                type="SEMICONT",
            ),
        )

        self.tc.enqueue(self.mod_vars_dsc_exec, var=var, sow=self.env.sow_GP)

    def mod_vars_dsc_exec(self, var: str, sow: tuple[Set | Alias, ...]) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        VAR_SNCAP = g.get_variable(f"{var}_SNCAP")

        # Bounds for semicont
        VAR_SNCAP.lo[r, t, p, *sow] = sparse(g.ncap_semi[r, t, p])
        VAR_SNCAP.up[r, t, p, *sow].where[g.ncap_semi[r, t, p]] = Max(
            g.ncap_semi[r, t, p], g.ncap_bnd[r, t, p, "UP"]
        )
