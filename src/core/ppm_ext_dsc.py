# ppm_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPM_EXT.dsc oversees extended preprocessor activities
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number, SpecialValues

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtDsc(GamsClass):
    """Translation unit for ppm_ext.dsc."""

    # Instance attributes
    module_name: str = "ppm_ext_dsc"
    gams_source: str = "ppm_ext.dsc"

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
        if self.env.dsc.upper() == "YES":
            self.tc.enqueue(self.discrete_capacity_extensions)

    def discrete_capacity_extensions(self: PpmExtDsc) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        g.ncap_disc[g.Rtp[r, t, p], "0"].where[g.PrcDscncap[r, p]] = Number(
            SpecialValues.EPS
        ).where[~g.ncap_semi[r, t, p]]
