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

from core.base_class import GamsClass
from core.bnd_ucv_mod import bnd_ucv_mod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        var = self.env.var

        self.tc.enqueue(
            self.exec_bnd_ucw_mod,
            arg1=self.arg1,
            arg2=self.arg2,
            var=var,
            stages=self.env.stages,
            swd=self.env.swd,
            sow=self.env.sow,
            defined_symbols={
                f"{var}_UC": self.tc.defined(f"{var}_UC"),
                f"{var}_UCR": self.tc.defined(f"{var}_UCR"),
                f"{var}_UCT": self.tc.defined(f"{var}_UCT"),
                f"{var}_UCRT": self.tc.defined(f"{var}_UCRT"),
                f"{var}_UCTS": self.tc.defined(f"{var}_UCTS"),
                f"{var}_UCRTS": self.tc.defined(f"{var}_UCRTS"),
            },
        )

    def exec_bnd_ucw_mod(
        self: BndUcwMod,
        arg1: str,
        arg2: str,
        var: str,
        stages: str,
        swd: str,
        sow: str,
        defined_symbols: dict[str, bool],
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=bnd_ucw_mod(
                arg1=arg1,
                arg2=arg2,
                var=var,
                stages=stages,
                swd=swd,
                sow=sow,
                defined_symbols=defined_symbols,
            ),
        )


def bnd_ucw_mod(
    *,
    arg1: str,
    arg2: str,
    var: str,
    stages: str,
    swd: str,
    sow: str,
    defined_symbols: dict[str, bool],
) -> str:
    tmp = "(T-SUC_L(R,UC_N))" if stages == "YES" else ""

    # fmt: off
    batincludes: list[tuple[str, str, str, str, str, str, str, str, str, str, str, str, str]] = [
        (f"{var}_UC", "", "", "", "UC_RHS", "$UC_ON(R,UC_N)", "LOOP(R,", ");", '', arg2, ",'','',''", "", ""),
        (f"{var}_UCR", ",", "R", "", "UC_RHSR", "$UC_ON(R,UC_N)", '', '', '', arg2, ",'',''", "$UC_R_EACH(R,UC_N)", ""),
        (f"{var}_UCT", "", "", ",TT", "UC_RHST", f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){arg1})", "LOOP(R,", ");", '', arg2, ",'',''", '', tmp),
        (f"{var}_UCRT", ",", "R", ",TT", "UC_RHSRT", f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){arg1})", '', '', '', arg2, ",''", "$UC_T_EACH(R,UC_N,TT)", tmp),
        (f"{var}_UCTS", "", "", ",TT", "UC_RHSTS", f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){arg1})", "LOOP(R,", ");", ",S", arg2, ",''", '', tmp),
        (f"{var}_UCRTS", ",", "R", ",TT", "UC_RHSRTS", f"$(UC_ON(R,UC_N)*UC_T_EACH(R,UC_N,TT){arg1})", '', '', ",S", arg2, "", "$UC_T_EACH(R,UC_N,TT)", tmp),
    ]
    # fmt: on

    body = "".join(
        bnd_ucv_mod(
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
            stages=stages,
            swd=swd,
            sow=sow,
            arg1_defined=defined_symbols.get(a1, False),
        )
        for a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13 in batincludes
    )

    return rf"""
  CNT=0;
  UC_T_EACH(UC_T_SUCC) = YES;
{body}
 UC_T_EACH(UC_T_SUCC) = NO;
*-------------------------------------------------------------------------------
{"IF(SW_PHASE EQ -9," if stages.upper() == "YES" else ""}
{"CNT$((SW_PARM GT 0)$CNT) = EPS;" if stages == "YES" else ""}
{"SW_PHASE=-1; SW_PARM = (-2+4$(CNT GT 0))$CNT;);" if stages.upper() == "YES" else ""}
"""
