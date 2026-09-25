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

from gamspy import Sum, sparse

from core.base_class import GamsClass
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        g = self.tc
        r, p, unit, Milestonyr = g.r, g.p, g.unit, g.Milestonyr

        if self.env.dsc.upper() == "YES":
            self.tc.enqueue(self.prepextdsc_exec)
            self.include(
                PrepparmGms(
                    self.tc,
                    self.env,
                    config=PrepparmGmsConfig(
                        arg1="NCAP_DISC",
                        arg2=(r,),
                        arg3=(p, unit),
                        arg4=("0", "0", "0"),
                        arg5=Milestonyr,
                        arg6=g.Rtp[r, Milestonyr, p],
                        arg7=1,
                    ),
                )
            )
            self.tc.enqueue(self.process_semicontinuous_requests)

    def process_semicontinuous_requests(self: PrepExtDsc) -> None:
        """Process semicontinuous requests"""
        g = self.tc
        r, t, p, j = g.r, g.t, g.p, g.j

        g.ncap_semi[g.Rtp[r, t, p]].where[g.PrcDscncap[r, p]] = (
            g.ncap_disc[g.Rtp, "0"] + 1
        ) - 1
        g.ncap_semi[g.Rtp].where[
            Sum(g.unit[j].where[g.ncap_disc[g.Rtp, g.unit]], 1)
        ] = 0

    def prepextdsc_exec(self: PrepExtDsc) -> None:
        g = self.tc
        r, p = g.r, g.p

        g.PrcDscncap[r, p] = sparse(g.prc_semi[r, p])
