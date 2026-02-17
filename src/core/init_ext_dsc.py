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

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtDsc(GamsClass):
    """Translation unit for init_ext.abs."""

    # Instance attributes
    module_name: str = "init_ext_dsc"
    gams_source: str = "init_ext.dsc"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        m = tc.container

        # Handle automatic activation of discrete extension
        if m["PRC_DSCNCAP"].number_records:
            tc.enqueue(self.assign_ncap_disc, tc=tc)

        tc.enqueue(self.project_ncap_semi, tc=tc)

        if m["NCAP_SEMI"].number_records:
            tc.enqueue(self.assign_prc_semi, tc=tc)

        self.env.set_scoped("dsc", "NO")

        if self.env.dscauto.upper() == "YES":
            if m["NCAP_DISC"].number_records:
                tc.enqueue(self.project_prc_dsncap, tc=tc)

        if m["PRC_DSCNCAP"].number_records:
            self.env.set_scoped("dsc", "YES")

        if m["RCAP_BLK"].number_records:
            self.env.set_global("solmip", "YES")

        if self.env.dsc == "YES":
            self.env.set_global("solmip", "YES")

        if not m["NCAP_DISC"].number_records:
            tc.enqueue(self.clear_ncap_disc, tc=tc)

        if not m["RCAP_BLK"].number_records:
            tc.enqueue(self.clear_rcap_blk, tc=tc)

        self.env.set_global("dsc", self.env.dsc)

        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="init_ext_dsc_end")

    def assign_ncap_disc(self, tc):
        tc.add_gams_code(
            module=self,
            phase="run",
            code="NCAP_DISC(R,T--ORD(T),P,'0')$PRC_DSCNCAP(R,P) = EPS;",
        )

    def project_ncap_semi(self, tc):
        tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION PRC_SEMI<NCAP_SEMI; NCAP_SEMI(R,'0',P)$((NCAP_SEMI(R,'0',P)=0)$PRC_SEMI(R,P)) = 10;",
        )

    def assign_prc_semi(self, tc):
        tc.add_gams_code(
            module=self,
            phase="run",
            code="PRC_SEMI(R,P) $= NCAP_SEMI(R,'0',P); NCAP_DISC(R,LL,P,'0') $= NCAP_SEMI(R,LL,P);",
        )

    def project_prc_dsncap(self, tc):
        tc.add_gams_code(module=self, phase="run", code="PRC_DSCNCAP < NCAP_DISC;")

    def clear_ncap_disc(self, tc):
        tc.add_gams_code(module=self, phase="run", code="$CLEAR NCAP_DISC")

    def clear_rcap_blk(self, tc):
        tc.add_gams_code(module=self, phase="run", code="$CLEAR RCAP_BLK")
