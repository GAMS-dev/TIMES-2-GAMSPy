# timesrng_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SPOINT.mod is the code for handling solution point saving/loading
# *   %1 - 1 or 0 (1: before solve, 0: renaming after solve)
# * Note: Using Posix utility mv for renaming for portability
# *=============================================================================*

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class TimesrngGms(GamsClass):
    """Translation unit for timesrng.gms."""

    module_name: str = "timesrng_gms"
    gams_source: str = "timesrng.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
$ONWARNING
$ONMULTI
$OFFLISTING
$PHANTOM EMPTY
ALIAS (*,R,REG,ALLYEAR,P,RNGLIM);
ALIAS (*,C,COM,J,S,T,ALL_REG,IE,CUR,BD,OBV,LL);
ALIAS (*,COM_GRP,CG,ITEM,IO,UC_N,CM_VAR,CM_BOX);
ALIAS (*,PRC,KP,UNIT);
PARAMETER  VAR_NCAPRNG(R,ALLYEAR,P,RNGLIM) / EMPTY.EMPTY.EMPTY.EMPTY 0 /;
""",
        )

        if Path("timesrng_inc.py").exists():
            raise NotImplementedError("timesrng_inc")
            # TODO: clarify what this file is about
            # from core.timesrng_inc import TimesrngInc

            # self.include(TimesrngInc(tc=self.tc, env=self.env))
        self.tc.enqueue(self.exec1)

    def exec1(self: TimesrngGms) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="EXECUTE_UNLOAD 'timesrng',VAR_NCAPRNG;",
        )
