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

from core.bnd_ucv_mod import bnd_ucv_mod

logger = logging.getLogger(__name__)


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
