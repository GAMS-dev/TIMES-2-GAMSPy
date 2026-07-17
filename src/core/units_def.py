# units_def.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UNITS.DEF has complete list of unit types                                   *
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Units(GamsClass):
    """Translation unit for units.def."""

    # Instance attributes
    module_name: str = "units_def"
    gams_source: str = "units.def"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # units by group
        g.units = Set(
            m,
            name="UNITS",
            description="Units",
            records=[
                "Bv-km",
                "Bv-kma",
                "GW",
                "MW",
                "Mt",
                "Mta",
                "kt",
                "kta",
                "kth",
                "t",
                "PJ",
                "PJa",
                "TJ",
                "TJa",
                "TWh",
                "GWh",
                "MWh",
                "uvol",
                "CUR",
                "GPKM",
                "GVKM",
                "Mcar",
                "UCU",
            ],
        )

        g.u = Alias(container=m, name="U", alias_with=g.units)

        g.UnitsCom = Set(
            m,
            name="UNITS_COM",
            domain=[g.units],
            description="Commodity Units",
            records=[
                "Bv-km",
                "Mt",
                "kt",
                "t",
                "PJ",
                "TJ",
                "uvol",
                "GPKM",
                "GVKM",
                "UCU",
            ],
        )
        g.UnitsCap = Set(
            m,
            name="UNITS_CAP",
            domain=[g.units],
            description="Capacity Units",
            records=["PJa", "GW", "MW", "Mta", "kta", "Bv-kma", "Mcar"],
        )
        g.UnitsAct = Set(
            m,
            name="UNITS_ACT",
            domain=[g.units],
            description="Activity Units",
            records=[
                "Mt",
                "kt",
                "kth",
                "PJ",
                "TJ",
                "TWh",
                "GWh",
                "MWh",
                "GPKM",
                "GVKM",
            ],
        )
        g.UnitsMony = Set(
            m,
            name="UNITS_MONY",
            domain=[g.units],
            description="Monatary Units",
            records=["CUR"],
        )

        # unit mapping table(s)
        g.g_unca = Parameter(
            m,
            name="G_UNCA",
            domain=[g.units, g.UnitsAct],
            description="Cap-to-Act conversions",
            records=[
                ("GW", "GWH", 8760),
                ("GW", "PJ", 31.536),
                ("GW", "TWH", 8.760),
                ("GWH", "PJ", 0.0036),
                ("GWH", "TJ", 3.6),
                ("GWH", "TWH", 0.001),
                ("MW", "GWH", 8.76),
                ("MW", "MWH", 8760),
                ("MW", "PJ", 0.031536),
                ("MW", "TJ", 31.536),
                ("MWH", "GWH", 0.001),
                ("MWH", "TJ", 0.0036),
                ("PJA", "PJ", 1),
                ("TJA", "TJ", 1),
                ("TWH", "PJ", 3.6),
                ("Mta", "Mt", 1),
                ("Mta", "kt", 1000),
                ("kta", "Mt", 0.001),
                ("kta", "kt", 1),
                ("kta", "kth", 8760),
            ],
        )
