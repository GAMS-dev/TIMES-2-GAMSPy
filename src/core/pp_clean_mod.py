# pp_clean_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------
# * PP_CLEAN.mod - Release memory by clearing items no longer used
# *-----------------------------------------------------------------------
# * Only items not used in any equations can be cleared; to be careful!

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpCleanMod(GamsClass):
    """Translation unit for pp_clean.mod."""

    module_name: str = "pp_clean_mod"
    gams_source: str = "pp_clean.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.env.memclean == "NO":
            return

        self.tc.enqueue(self.exec1)

        if not self.env.is_set("bencost"):
            self.env.set_global("bencost", "NO")
        if self.env.bencost.upper() != "NO" and Path("timesrng.inc").exists():
            # TODO: clarify what this file is about
            shutil.move("timesrng_inc.py", "timesrng_inc_bak.py")

    def exec1(self: PpCleanMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
FLO_SUM(R,ALLYEAR,P,CG1,C,CG2,S) = 0;
FLO_FUNC(R,ALLYEAR,P,CG1,CG2,S) = 0;
NCAP_AF(R,ALLYEAR,P,S,BD) = 0;
NCAP_AFA(R,ALLYEAR,P,BD) = 0;
NCAP_AFS(R,ALLYEAR,P,S,BD) = 0;
NCAP_COST(R,ALLYEAR,P,CUR) = 0;
NCAP_FOM(R,ALLYEAR,P,CUR) = 0;
ACT_COST(R,ALLYEAR,P,CUR) = 0;
FLO_TAX(R,ALLYEAR,P,C,S,CUR) = 0;
FLO_SUB(R,ALLYEAR,P,C,S,CUR) = 0;
FLO_COST(R,ALLYEAR,P,C,S,CUR) = 0;
FLO_DELIV(R,ALLYEAR,P,C,S,CUR) = 0;
""",
        )
