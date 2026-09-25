# initmty_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * INIT DECLARATIONS FOR THE IER EXTENSION
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


class InitmtyIer(GamsClass):
    """Translation unit for initmty.ier."""

    # Instance attributes
    module_name: str = "initmty_ier"
    gams_source: str = "initmty.ier"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        # * Parameters used in EQx_MRKCON
        g.flo_mrkcon = Parameter(
            m,
            name="FLO_MRKCON",
            domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.bd],
            description="Bound on the share of a flow in the total consumption of a commmodity",
        )
        g.flo_mrkprd = Parameter(
            m,
            name="FLO_MRKPRD",
            domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.bd],
            description="Bound on the share of a flow in the total production of a commmodity",
        )
        # * Sets and parameters used for CHP plants
        g.EctChp = Set(
            m,
            name="ECT_CHP",
            domain=[g.Reg, g.prc],
            description="Set of extraction condensing CHP plants",
        )
        g.EctElc = Set(
            m,
            name="ECT_ELC",
            domain=[g.Reg, g.prc, g.Com],
            description="Electricity commodity of extraction condensing CHP plants",
        )
        g.EctDht = Set(
            m,
            name="ECT_DHT",
            domain=[g.Reg, g.prc, g.Com],
            description="Heat commodity of extraction condensing CHP plants",
        )
        g.EctCgout = Set(
            m,
            name="ECT_CGOUT",
            domain=[g.Reg, g.prc, g.comgrp],
            description="Output commodity group ELC+HEAT of ECT CHP plant",
        )
        g.EctCgin = Set(
            m,
            name="ECT_CGIN",
            domain=[g.Reg, g.prc, g.comgrp],
            description="Fuel input commodity group of ECT CHP plant",
        )
        g.ect_inp2elc = Parameter(
            m,
            name="ECT_INP2ELC",
            domain=[g.Reg, g.allyear, g.prc],
            description="Conversion factor from input capacity to ELC capacity in BPT point",
        )
        g.ect_inp2dht = Parameter(
            m,
            name="ECT_INP2DHT",
            domain=[g.Reg, g.allyear, g.prc],
            description="Conversion factor from input capacity to heat capacity in BPT point",
        )
        g.ect_inp2con = Parameter(
            m,
            name="ECT_INP2CON",
            domain=[g.Reg, g.allyear, g.prc],
            description="Conversion factor from input capacity to heat capacity in BPT point",
        )
        g.ect_reh = Parameter(
            m,
            name="ECT_REH",
            domain=[g.Reg, g.allyear, g.prc],
            description="Ratio of electricity to heat in brackpressure point",
        )
        g.ect_afcon = Parameter(
            m,
            name="ECT_AFCON",
            domain=[g.Reg, g.allyear, g.prc, g.bd],
            description="Availability of condensing mode operation of extraction condensing CHP",
        )
        g.ect_afbpt = Parameter(
            m,
            name="ECT_AFBPT",
            domain=[g.Reg, g.allyear, g.prc, g.bd],
            description="Availability of backpressure mode operation of extraction condensing CHP",
        )
