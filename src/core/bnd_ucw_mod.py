# bnd_ucw_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * BND_UCW.MOD Wrapper for setting bounds on UC RHS variables                  *
# *=============================================================================*
# * %1 - Stochastic dollar control or ''
# * %2 - I or ''
# *------------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.bnd_ucv_mod import BndUcvMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndUcwMod(GamsClass):
    """Translation unit for bnd_ucw.mod."""

    # Instance attributes
    module_name: str = "bnd_ucw_mod"
    gams_source: str = "bnd_ucw.mod"

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
        self._sub_modules: dict[str, GamsClass] = {}
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("tmp", "")
        if self.env.stages == "YES":
            self.env.set_scoped("tmp", "(T-SUC_L(R,UC_N))")

        self.tc.enqueue(self.exec1)

        var = self.env.var
        # fmt: off
        bnducvs: list[tuple[str, str, str, str, str, str, str, str, str, str, str, str, str]] = [
            (f"{var}_UC",    "",  "", "",     "UC_RHS",    "$UC_ON(R,UC_N)", "LOOP(R,", ");", '', self.arg2, ",'','',''", "", ""),
            (f"{var}_UCR",   ",", "R", "",    "UC_RHSR",   "$UC_ON(R,UC_N)", '', '', '', self.arg2, ",'',''", "$UC_R_EACH(R,UC_N)", ""),
            (f"{var}_UCT",   "", "", ",TT",   "UC_RHST",   f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){self.arg1})", "LOOP(R,", ");", '', self.arg2, ",'',''", '', ""),
            (f"{var}_UCRT",  ",", "R", ",TT", "UC_RHSRT",  f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){self.arg1})", '', '', '', self.arg2, ",''", "$UC_T_EACH(R,UC_N,TT)", self.env.tmp),
            (f"{var}_UCTS",  "", "", ",TT",   "UC_RHSTS",  f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){self.arg1})", "LOOP(R,", ");", ",S", self.arg2, ",''", '',  self.env.tmp),
            (f"{var}_UCRTS", ",", "R", ",TT", "UC_RHSRTS", f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){self.arg1})", '', '', ",S", self.arg2, "", "$UC_T_EACH(R,UC_N,TT)", self.env.tmp),
        ]
        # fmt: on

        for a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13 in bnducvs:
            self.include(
                BndUcvMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=a1,
                    arg2=a2,
                    arg3=a3,
                    arg4=a4,
                    arg5=a5,
                    arg6=a6,
                    arg7=a7,
                    arg8=a8,
                    arg9=a9,
                    arg10=a10,
                    arg11=a11,
                    arg12=a12,
                    arg13=a13,
                )
            )

        self.tc.enqueue(self.exec2, stages=self.env.stages)

    def exec1(self: BndUcwMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  CNT=0;
  UC_T_EACH(UC_T_SUCC) = YES;
""",
        )

    def exec2(self: BndUcwMod, stages: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 UC_T_EACH(UC_T_SUCC) = NO;
*-------------------------------------------------------------------------------
{"IF(SW_PHASE EQ -9," if stages.upper() == "YES" else ""}
{"CNT$((SW_PARM GT 0)$CNT) = EPS;" if stages == "YES" else ""}
{"SW_PHASE=-1; SW_PARM = (-2+4$(CNT GT 0))$CNT;);" if stages.upper() == "YES" else ""}
""",
        )
