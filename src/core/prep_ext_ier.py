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

from core.fillparm_gms import FillparmGms
from core.pp_chp_ier import PpChpIer

from .base_class import GamsClass

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
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        batincludes = [
            # fmt: off
            # ("FLO_MRKCON", "R", "P,C,TS,BD", ",'0','0'",         "MODLYEAR", "RTP(R,MODLYEAR,P)", "GE 0"),
            # ("FLO_MRKPRD", "R", "P,C,TS,BD", ",'0','0'",         "MODLYEAR", "RTP(R,MODLYEAR,P)", "GE 0"),
            (
                "ECT_AFCON",
                "R",
                "P,BD",
                ",'0','0','0','0'",
                "MODLYEAR",
                "RTP(R,MODLYEAR,P)",
                "GE 0",
            ),
            (
                "ECT_AFBPT",
                "R",
                "P,BD",
                ",'0','0','0','0'",
                "MODLYEAR",
                "RTP(R,MODLYEAR,P)",
                "GE 0",
            ),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                )
            )
        # *-----------------------------------------------------------------------------
        # * Convert capacity related data for extraction condensing turbines
        # * from electricity commodity to input commodity grooup
        # * Assumption: original PRC_ACTUNT contains the electricity commodity of this process
        # *-----------------------------------------------------------------------------
        if self.env.chp_mode == "YES":
            self.include(
                PpChpIer(
                    self.tc,
                    self.env,
                )
            )
        self.env.set_global("peakchp", "eqpk_ect.ier")
