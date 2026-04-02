# prep_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_EXT.dsc oversees extended preprocessor activities for DSC
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# * The default option for NCAP_DISC is 10 (no interpolation/extrapolation, but migrate to milestone years)
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.prepparm_gms import PrepparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtDsc(GamsClass):
    """Translation unit for prep_ext.dsc."""

    # Instance attributes
    module_name: str = "prep_ext_dsc"
    gams_source: str = "prep_ext.dsc"

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
        if self.env.dsc.upper() == "YES":
            self.tc.enqueue(self.prepextdsc_exec)
            self.include(
                PrepparmGms(
                    self.tc,
                    self.env,
                    arg1="NCAP_DISC",
                    arg2="R",
                    arg3="P,UNIT",
                    arg4=",'0','0','0'",
                    arg5="MILESTONYR",
                    arg6="RTP(R,MILESTONYR,P)",
                    arg7="1",
                )
            )
            self.tc.enqueue(self.process_semicontinuous_requests)

    def process_semicontinuous_requests(self: PrepExtDsc):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Process semicontinuous requests
  NCAP_SEMI(RTP(R,T,P))$PRC_DSCNCAP(R,P) = (NCAP_DISC(RTP,'0')+1)-1;
  NCAP_SEMI(RTP)$SUM(UNIT(J)$NCAP_DISC(RTP,UNIT),1) = 0;
""",
        )

    def prepextdsc_exec(self: PrepExtDsc):
        self.tc.add_gams_code(
            module=self, phase="run", code="PRC_DSCNCAP(R,P) $= PRC_SEMI(R,P);"
        )
