# prep_ext_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.vtt oversees all the added inperpolation activities needed by IER  *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.pp_chp_ier import PpChpIer

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtIer(GamsClass):
    """Translation unit for prep_ext.ier."""

    # Instance attributes
    module_name: str = "prep_ext_ier"
    gams_source: str = "prep_ext.ier"

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
        self.compile()

    def compile(self) -> None:
        g = self.tc
        batincludes: list[FillparmGmsConfig] = [
            # ("FLO_MRKCON", "R", "P,C,TS,BD", ",'0','0'",         "MODLYEAR", "RTP(R,MODLYEAR,P)", "GE 0"),
            # ("FLO_MRKPRD", "R", "P,C,TS,BD", ",'0','0'",         "MODLYEAR", "RTP(R,MODLYEAR,P)", "GE 0"),
            FillparmGmsConfig(
                g.ect_afcon,
                (g.r,),
                (g.p, g.bd),
                ("0",) * 4,
                g.Modlyear,
                g.Rtp[g.r, g.Modlyear, g.p],
                Number(0),
            ),
            FillparmGmsConfig(
                g.ect_afbpt,
                (g.r,),
                (g.p, g.bd),
                ("0",) * 4,
                g.Modlyear,
                g.Rtp[g.r, g.Modlyear, g.p],
                Number(0),
            ),
        ]
        for config in batincludes:
            self.include(FillparmGms(self.tc, self.env, config))
        # *-----------------------------------------------------------------------------
        # * Convert capacity related data for extraction condensing turbines
        # * from electricity commodity to input commodity grooup
        # * Assumption: original PRC_ACTUNT contains the electricity commodity of this process
        # *-----------------------------------------------------------------------------
        if self.env.chp_mode == "YES":
            self.include(PpChpIer(self.tc, self.env))
        self.env.set_global("peakchp", "eqpk_ect.ier")
