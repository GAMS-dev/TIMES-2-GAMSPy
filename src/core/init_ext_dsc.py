# init_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INIT_EXT.xtd oversees initial preprocessor activities                       *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gamspy.math as gmath
from gamspy import Ord, SpecialValues

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtDsc(GamsClass):
    """Translation unit for init_ext.dsc."""

    # Instance attributes
    module_name: str = "init_ext_dsc"
    gams_source: str = "init_ext.dsc"

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
        # Handle automatic activation of discrete extension
        if self.tc.defined("PRC_DSCNCAP"):
            self.tc.enqueue(self.assign_ncap_disc)

        self.tc.enqueue(self.project_ncap_semi)

        if self.tc.defined("NCAP_SEMI"):
            self.tc.enqueue(self.assign_prc_semi)

        self.env.set_scoped("dsc", "NO")

        if self.env.dscauto.upper() == "YES" and self.tc.defined("NCAP_DISC"):
            self.tc.enqueue(self.project_prc_dsncap)

        if self.tc.defined("PRC_DSCNCAP"):
            self.env.set_scoped("dsc", "YES")

        if self.tc.defined("RCAP_BLK"):
            self.env.set_global("solmip", "YES")

        if self.env.dsc == "YES":
            self.env.set_global("solmip", "YES")

        if not self.tc.defined("NCAP_DISC"):
            self.tc.add_gams_code(module=self, phase="init", code="$CLEAR NCAP_DISC")

        if not self.tc.defined("RCAP_BLK"):
            self.tc.add_gams_code(module=self, phase="init", code="$CLEAR RCAP_BLK")

        self.env.set_global("dsc", self.env.dsc)

    def assign_ncap_disc(self) -> None:
        g = self.tc
        g.ncap_disc[g.r, g.t.lag(Ord(g.t), "circular"), g.p, "0"].where[
            g.PrcDscncap[g.r, g.p]
        ] = SpecialValues.EPS

    def project_ncap_semi(self) -> None:
        g = self.tc
        r, p = g.r, g.p
        gmath.aggregate(source=g.ncap_semi[r, g.allyear, p], target=g.prc_semi[r, p])

        g.ncap_semi[r, "0", p].where[
            (g.ncap_semi[r, "0", p] == 0) & (g.prc_semi[r, p])
        ] = 10

    def assign_prc_semi(self) -> None:
        g = self.tc
        r, p = g.r, g.p

        rhs = g.ncap_semi[r, "0", p]
        g.prc_semi[r, p].where[rhs] = rhs

        rhs = g.ncap_semi[r, g.ll, p]
        g.ncap_disc[r, g.ll, p, "0"].where[rhs] = rhs

    def project_prc_dsncap(self) -> None:
        g = self.tc
        r, p = g.r, g.p

        gmath.project(
            source=g.ncap_disc[r, g.allyear, p, g.unit], target=g.PrcDscncap[g.r, g.p]
        )
