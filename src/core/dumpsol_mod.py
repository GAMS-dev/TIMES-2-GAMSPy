# dumpsol_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * DUMPSOL.MOD displays selected solution results                              *
# *   %1 - mod or v# for the source code to be used                             *
# *   %2 - NO_EMTY if headers to be surpressed if no row                        *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.dumpsol1_mod import Dumpsol1Mod
from core.dumpsolv_mod import DumpsolvMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class DumpsolMod(GamsClass):
    """Translation unit for dumpsol.mod."""

    module_name: str = "dumpsol_mod"
    gams_source: str = "dumpsol.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        # TODO: we need a new phase after solving the model for reporting
        self.tc.enqueue(self.exec_begin_dump)

        self.env.set_scoped("no_emty", self.arg2)

        self.include(
            Dumpsol1Mod(
                self.tc,
                self.env,
                arg1="L",
                arg2="VAR_NCAP",
                arg3="VAR_CAP",
                arg4="VAR_COMPRD",
            )
        )
        self.include(
            DumpsolvMod(
                self.tc,
                self.env,
                arg1="L",
                arg2="VAR_ACT",
                arg3="VAR_FLO",
                arg4="VAR_IRE",
                arg5="VAR_SIN",
                arg6="VAR_SOUT",
            )
        )
        self.include(
            Dumpsol1Mod(
                self.tc,
                self.env,
                arg1="M",
                arg2="VAR_NCAP",
                arg3="VAR_CAP",
                arg4="VAR_COMPRD",
            )
        )
        self.include(
            DumpsolvMod(
                self.tc,
                self.env,
                arg1="M",
                arg2="VAR_ACT",
                arg3="VAR_FLO",
                arg4="VAR_IRE",
                arg5="VAR_SIN",
                arg6="VAR_SOUT",
            )
        )

        self.include(
            Dumpsol1Mod(
                self.tc,
                self.env,
                arg1="L",
                arg2="EQG_COMBAL",
                arg3="EQE_COMBAL",
                arg4="EQE_COMPRD",
            )
        )
        self.include(
            Dumpsol1Mod(
                self.tc,
                self.env,
                arg1="M",
                arg2="EQG_COMBAL",
                arg3="EQE_COMBAL",
                arg4="EQE_COMPRD",
            )
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="PARAMETER VARACT(R,T,P) / EMPTY.EMPTY.EMPTY 0 /;",
        )

        self.tc.enqueue(self.exec_varact)

        self.include(Dumpsol1Mod(self.tc, self.env, arg1="T", arg2="VARACT"))

        self.tc.enqueue(self.exec_end_dump)

    def exec_begin_dump(self: DumpsolMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
        FILE SOLDUMP / SOLDUMP.TXT /;
        PUT SOLDUMP;
        SOLDUMP.PW=255;
        """,
        )

    def exec_varact(self: DumpsolMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="VARACT(RTP(R,T,P)) = SUM((V,S), VAR_ACT.L(R,V,T,P,S));",
        )

    def exec_end_dump(self: DumpsolMod) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="PUTCLOSE SOLDUMP;")
