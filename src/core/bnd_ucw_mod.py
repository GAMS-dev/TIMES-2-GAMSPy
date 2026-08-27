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

from gamspy import Number, SpecialValues

from core.bnd_ucv_mod import BndUcvVariantConfig, bnd_ucv_mod, bnd_ucv_mod_GP

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_ucw_mod_GP(
    *,
    g: TimesModelClass,
    arg1: Set | Alias | ImplicitSet | Number,
    arg2: str = "",
    var: str,
    stages: str,
    swd_GP: tuple[Set | Alias] | tuple[()],
    sow_GP: SowGPType,
    defined_symbols: dict[str, bool],
) -> None:
    """GAMSPy twin of :func:`bnd_ucw_mod`."""
    r, t, tt, s, ucn = g.r, g.t, g.tt, g.s, g.ucn

    g.cnt[...] = 0
    g.UcTEach[g.UcTSucc] = True

    on = g.UcOn[r, ucn]
    t_each = g.UcTEach[r, ucn, tt]
    period_cond = on * t_each * arg1
    # tmp = "(T-SUC_L(R,UC_N))" if stages == "YES" else ""
    shifted_tt = tt[t.lag(g.suc_l[r, ucn])] if stages == "YES" else tt

    # spar_ucsl_padding mirrors bnd_ucv.mod's own %11 (bnd_ucv_mod's arg11
    # in the legacy string version -- ",'','',''" down to "" per variant):
    # empty-string dims needed to fill out SPAR_UCSL's 3 residual slots
    # after UC_N, given how many of them var_domain already supplies
    # (R/TT/S).
    batincludes: list[BndUcvVariantConfig] = [
        BndUcvVariantConfig(
            var_name=f"{var}_UC",
            param_name="UC_RHS",
            var_domain=(ucn,),
            param_domain=(ucn,),
            set_var_domain=(ucn,),
            loop_region=True,
            main_condition=on,
            clear_condition=Number(1),
            spar_ucsl_padding=("",) * 3,
        ),
        BndUcvVariantConfig(
            var_name=f"{var}_UCR",
            param_name="UC_RHSR",
            var_domain=(ucn, r),
            param_domain=(r, ucn),
            set_var_domain=(ucn, r),
            loop_region=False,
            main_condition=on,
            clear_condition=g.UcREach[r, ucn],
            spar_ucsl_padding=("",) * 2,
        ),
        BndUcvVariantConfig(
            var_name=f"{var}_UCT",
            param_name="UC_RHST",
            var_domain=(ucn, tt),
            param_domain=(ucn, tt),
            set_var_domain=(ucn, shifted_tt),
            loop_region=True,
            main_condition=period_cond,
            clear_condition=Number(1),
            spar_ucsl_padding=("",) * 2,
        ),
        BndUcvVariantConfig(
            var_name=f"{var}_UCRT",
            param_name="UC_RHSRT",
            var_domain=(ucn, r, tt),
            param_domain=(r, ucn, tt),
            set_var_domain=(ucn, r, shifted_tt),
            loop_region=False,
            main_condition=period_cond,
            clear_condition=t_each,
            spar_ucsl_padding=("",) * 1,
        ),
        BndUcvVariantConfig(
            var_name=f"{var}_UCTS",
            param_name="UC_RHSTS",
            var_domain=(ucn, tt, s),
            param_domain=(ucn, tt, s),
            set_var_domain=(ucn, shifted_tt, s),
            loop_region=True,
            main_condition=period_cond,
            clear_condition=Number(1),
            spar_ucsl_padding=("",) * 1,
        ),
        BndUcvVariantConfig(
            var_name=f"{var}_UCRTS",
            param_name="UC_RHSRTS",
            var_domain=(ucn, r, tt, s),
            param_domain=(r, ucn, tt, s),
            set_var_domain=(ucn, r, shifted_tt, s),
            loop_region=False,
            main_condition=period_cond,
            clear_condition=t_each,
            spar_ucsl_padding=("",) * 0,
        ),
    ]

    for config in batincludes:
        bnd_ucv_mod_GP(
            g=g,
            config=config,
            swd_GP=swd_GP,
            sow_GP=sow_GP,
            stages=stages,
            arg10=arg2,
            defined=defined_symbols.get(config.var_name, False),
        )

    g.UcTEach[g.UcTSucc] = False

    # *-------------------------------------------------------------------------------
    if stages.upper() == "YES":
        gate = g.sw_phase == -9
        if stages == "YES":
            g.cnt[...].where[gate * (g.sw_parm > 0).where[g.cnt]] = SpecialValues.EPS
        g.sw_parm[...].where[gate] = (-2 + Number(4).where[g.cnt > 0]).where[g.cnt]
        g.sw_phase[...].where[gate] = -1


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
