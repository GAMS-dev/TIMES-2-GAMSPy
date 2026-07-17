# globals_def.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * GLOBALS.DEF has all the declaration & defaults for SCALARS & Parameters      *
# *==============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Globals(GamsClass):
    """Translation unit for globals.def."""

    # Instance attributes
    module_name: str = "globals"
    gams_source: str = "globals.def"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # * global initialization and other scalar defaults which may be changed here
        # *  or overwritten in the user *.DD

        g.g_dyear = Parameter(
            m, name="G_DYEAR", description="Year to discount to", records=0
        )
        g.g_iledno = Parameter(
            m,
            name="G_ILEDNO",
            description="1/threshold at which to ignore ILED",
            records=10,
        )
        g.g_tlife = Parameter(
            m,
            name="G_TLIFE",
            description="Default technology life if not provided",
            records=10,
        )
        g.g_vint = Parameter(
            m,
            name="G_VINT",
            description="% annual change in input data for vintaging",
            records=0.1,
        )
        g.g_nointerp = Parameter(
            m,
            name="G_NOINTERP",
            description="Turn off interplation",
            records=0,
        )
        g.g_cycle = Parameter(
            m,
            name="G_CYCLE",
            domain=[g.tslvl],
            description="Number of cycles in average year",
            records=[("ANNUAL", 1), ("SEASON", 1), ("DAYNITE", 365)],
        )
