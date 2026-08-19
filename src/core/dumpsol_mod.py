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

from gamspy import Parameter, Sum, set_options

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
        # dumpsol.mod's `FILE SOLDUMP; PUT SOLDUMP; SOLDUMP.PW=255;` and the
        # closing `PUTCLOSE SOLDUMP;` are dropped: dumpsol1.mod and dumpsolv.mod
        # now write the dump from Python (see their `out=Path("SOLDUMP")`), so
        # nothing puts to the GAMS file handle any more.
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

        g = self.tc

        # No description: dumpsol1.mod prints the symbol text into the dump, and
        # the GAMS declaration carries none.
        g.varact = Parameter(g.container, name="VARACT", domain=[g.r, g.t, g.p])
        # / EMPTY.EMPTY.EMPTY 0 / seeds the phantom record so that the header of
        # the dump is written even when the parameter stays empty. 'EMPTY' is not
        # a member of R/T/P, which $ONWARNING (set by the .dd files) downgrades to
        # a warning in GAMS; VALIDATION is switched off for GAMSPy's own check.
        set_options({"VALIDATION": 0})  # TODO: Remove in future GAMSPY version
        g.varact["EMPTY", "EMPTY", "EMPTY"] = 0
        set_options({"VALIDATION": 1})  # TODO: Remove in future GAMSPY version

        self.tc.enqueue(self.exec_varact)

        self.include(Dumpsol1Mod(self.tc, self.env, arg1="T", arg2="VARACT"))

    def exec_varact(self: DumpsolMod) -> None:
        g = self.tc
        r, t, p, v, s = g.r, g.t, g.p, g.v, g.s

        g.varact[g.Rtp[r, t, p]] = Sum([v, s], g.VAR_ACT.l[r, v, t, p, s])
