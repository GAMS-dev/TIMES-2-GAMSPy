# initmty_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * INIT DECLARATIONS FOR THE DSC EXTENSION
# *=============================================================================
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyDsc(GamsClass):
    """Translation unit for initmty.dsc."""

    # Instance attributes
    module_name: str = "initmty_dsc"
    gams_source: str = "initmty.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        self.env.set_global("dsc", "YES")
        if not self.env.dsc == "YES":
            raise Exception("Activation of DSC extension failed")

        # Sets and parameters for discrete capacity extension
        g.unit = Set(
            m,
            name="UNIT",
            description="Number of different units",
            records=range(101),
        )
        g.PrcDscncap = Set(
            m,
            name="PRC_DSCNCAP",
            domain=[g.r, g.p],
            description="Processes with discrete capacity additions",
        )
        g.ncap_disc = Parameter(
            m,
            name="NCAP_DISC",
            domain=[g.r, g.allyear, g.p, g.unit],
            description="Unit size of discrete capacity addition",
        )
        g.ncap_semi = Parameter(
            m,
            name="NCAP_SEMI",
            domain=[g.r, g.allyear, g.p],
            description="Semi-continuous capacity, lower bound",
        )

        # g.ncap_cstd = Parameter(
        #     m,
        #     name="NCAP_CSTD",
        #     domain=[g.Reg, g.allyear, g.prc, g.cur, g.unit],
        #     description="Investment cost of unit",
        # )
        # g.ncap_fomd = Parameter(
        #     m,
        #     name="NCAP_FOMD",
        #     domain=[g.Reg, g.allyear, g.prc, g.cur, g.unit],
        #     description="Fixed operating and maintenace cost of unit",
        # )
