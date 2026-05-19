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

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        # Handle automatic activation of discrete extension
        if self.tc.defined("PRC_DSCNCAP"):
            self.tc.enqueue(self.assign_ncap_disc)

        self.tc.enqueue(
            self.project_ncap_semi,
        )

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

        if self.tc.test_run:
            self.tc.save_test_state(env=self.env, checkpoint="init_ext_dsc_end")

    def assign_ncap_disc(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="NCAP_DISC(R,T--ORD(T),P,'0')$PRC_DSCNCAP(R,P) = EPS;",
        )

    def project_ncap_semi(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION PRC_SEMI<NCAP_SEMI; NCAP_SEMI(R,'0',P)$((NCAP_SEMI(R,'0',P)=0)$PRC_SEMI(R,P)) = 10;",
        )

    def assign_prc_semi(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="PRC_SEMI(R,P) $= NCAP_SEMI(R,'0',P); NCAP_DISC(R,LL,P,'0') $= NCAP_SEMI(R,LL,P);",
        )

    def project_prc_dsncap(self) -> None:
        self.tc.add_gams_code(
            module=self, phase="run", code="OPTION PRC_DSCNCAP < NCAP_DISC;"
        )
