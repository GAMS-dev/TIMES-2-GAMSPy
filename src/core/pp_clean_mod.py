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

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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

        self.tc.enqueue(self.exec_pp_clean_mod, memclean=self.env.memclean)

        if not self.env.is_set("bencost"):
            self.env.set_global("bencost", "NO")
        if self.env.bencost.upper() != "NO" and Path("timesrng.inc").exists():
            # TODO: clarify what this file is about
            shutil.move("timesrng_inc.py", "timesrng_inc_bak.py")

    def exec_pp_clean_mod(self: PpCleanMod, memclean: str) -> None:
        pp_clean_mod(g=self.tc, memclean=memclean)


def pp_clean_mod(g: TimesModelClass, memclean: str) -> None:
    # TODO: in pp_clean.mod there is $IF NOT SET BENCOST $SETGLOBAL BENCOST NO
    # how should this be done in this string-returning function?
    if memclean == "NO":
        return

    (r, allyear, p, cg1, c, cg2, s, bd, cur) = (
        g.r,
        g.allyear,
        g.p,
        g.cg1,
        g.c,
        g.cg2,
        g.s,
        g.bd,
        g.cur,
    )

    g.flo_sum[r, allyear, p, cg1, c, cg2, s] = 0
    g.flo_func[r, allyear, p, cg1, cg2, s] = 0
    g.ncap_af[r, allyear, p, s, bd] = 0
    g.ncap_afa[r, allyear, p, bd] = 0
    g.ncap_afs[r, allyear, p, s, bd] = 0
    g.ncap_cost[r, allyear, p, cur] = 0
    g.ncap_fom[r, allyear, p, cur] = 0
    g.act_cost[r, allyear, p, cur] = 0
    g.flo_tax[r, allyear, p, c, s, cur] = 0
    g.flo_sub[r, allyear, p, c, s, cur] = 0
    g.flo_cost[r, allyear, p, c, s, cur] = 0
    g.flo_deliv[r, allyear, p, c, s, cur] = 0
