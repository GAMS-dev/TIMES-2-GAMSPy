# bnd_ucv_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_UCV.MOD set the actual bounds for UC constraint slacks                  *
# =============================================================================*
#  %1 - UC variable name
#  %2 - "," or ""
#  %3 - "R" or ""
#  %4 - period
#  %5 - UCRHS attribute name
#  %6 - control sets (region, period EACH/SUM/SUCC)
#  %7 - optional LOOP
#  %8 - optional LOOP close
#  %9 - timeslice
#  %10 - multi-stage indicator
#  %11 - SPAR_UCSL residual dimension
# ------------------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, If, Loop, Number, Ord, SpecialValues, Sum, sparse
from gamspy.math import abs

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class BndUcvVariantConfig:
    """One UC-RHS variant's worth of bnd_ucv.mod's %1-%9/%11-%13 args.

    Built once per row by bnd_ucw_mod_GP's config matrix (UC/UCR/UCT/
    UCRT/UCTS/UCRTS) and passed through to bnd_ucv_mod_GP unchanged.
    bnd_ucv.mod's %-numbered args map onto these fields as follows (%10,
    the multi-stage indicator, isn't here -- it's bnd_ucv_mod_GP's own
    `arg10` parameter, shared across every variant, not a per-row value):

      %1  UC variable name               var_name (-> VAR = g.get_variable(...))
      %2  ","  or ""                     folded into var_domain/param_domain
      %3  "R"  or ""                     (region present) <=> not loop_region
      %4  period suffix (",TT" or "")    folded into var_domain/param_domain too
      %5  UC_RHS-family attribute name   param_name (-> PARAM, STOCH_PARAM = g.get_parameter(f"S_{...}"))
      %6  control-set condition          main_condition
      %7/%8  optional LOOP(R, ... );     loop_region (-> with Loop(g.r): ...)
      %9  timeslice suffix (",S" or "")  folded into var_domain/param_domain/set_var_domain
      %11 SPAR_UCSL residual dimension   spar_ucsl_padding (arg10=="I" restart block only)
      %12 extra $-condition on "clear"   clear_condition
      %13 T-slot lag when staged         folded into set_var_domain (the shifted-tt element)

    %2/%3/%4/%9 don't each get their own field because bnd_ucv.mod builds
    its domain lists by string concatenation (`UC_N{%2}{%3}{%4}{%9}`) --
    each macro independently contributes "nothing" or "one more
    dimension" to the text. A GAMSPy domain is a real tuple, so
    bnd_ucw_mod_GP's config matrix just constructs the finished tuple per
    UC variant directly (e.g. `(ucn, r, shifted_tt, s)` for UCRTS) instead
    of assembling it piecewise from four string flags. Concretely:
    `var_domain`/`param_domain` mirror bnd_ucv.mod's own %2%3%4%9
    (variable side) vs %3%2%4%9 (parameter side) domain-tuple order -- the
    variable always leads with UC_N, the parameter always leads with R
    (when R is part of the domain at all). `set_var_domain` is
    `var_domain` with any T-typed slot narrowed per %13
    (`TT(T-SUC_L(R,UC_N))` when staged) -- used only in the "Set the
    bounds"/"uncertain RHS" sections.
    """

    var_name: str
    param_name: str
    var_domain: tuple[SET_OR_ALIAS, ...]
    param_domain: tuple[SET_OR_ALIAS, ...]
    set_var_domain: tuple[SET_OR_ALIAS, ...]
    loop_region: bool
    main_condition: Condition | Expression | ImplicitSet
    clear_condition: Condition | Expression | ImplicitSet | Number
    spar_ucsl_padding: tuple[str, ...]


def bnd_ucv_mod_GP(
    *,
    g: TimesModelClass,
    config: BndUcvVariantConfig,
    swd_GP: tuple[SET_OR_ALIAS, ...],
    sow_GP: SowGPType,
    stages: str,
    arg10: str,
    defined: bool,
) -> None:
    """GAMSPy twin of :func:`bnd_ucv_mod`.

    `config` carries bnd_ucv.mod's %1-%9/%11-%13 args -- see
    `BndUcvVariantConfig`'s own docstring for the field-by-field mapping.
    `arg10` is bnd_ucv.mod's %10 (multi-stage indicator) and selects a
    whole branch, not a per-variant value.
    """
    if arg10 not in ("", "I", "M"):
        raise ValueError(f"Unhandled argument arg10={arg10!r} passed.")

    var_name = config.var_name
    param_name = config.param_name
    var_domain = config.var_domain
    param_domain = config.param_domain
    set_var_domain = config.set_var_domain
    loop_region = config.loop_region
    main_condition = config.main_condition
    clear_condition = config.clear_condition
    spar_ucsl_padding = config.spar_ucsl_padding

    VAR = g.get_variable(var_name)
    PARAM = g.get_parameter(param_name)
    STOCH_PARAM = g.get_parameter(f"S_{param_name}")

    if arg10 == "M":
        g.uncd1.setRecords(None)
        g.uncd1[g.ucn] = True
        g.uncd1["OBJ1"] = False

        unc_domain = (g.ucn[g.uncd1], *var_domain[1:])
        ww = g.ww

        def copy_deviation_forward() -> None:
            s_n = STOCH_PARAM[*param_domain, "N", "1", ww]

            # Copy old deviation bounds forward unless cleared
            PARAM[*param_domain, "N"].where[s_n] = 0
            VAR.lo[*unc_domain, g.allsow].where[PARAM[*param_domain, "N"]] = VAR.lo[
                *var_domain, ww
            ]
            VAR.up[*unc_domain, g.allsow].where[PARAM[*param_domain, "N"]] = VAR.up[
                *var_domain, ww
            ]

            # Add flags indicating the new deviation bounds in force
            has_s_n = (s_n >= 0).where[s_n]
            PARAM[*param_domain, "N"].where[has_s_n] = -1

            # Set deviation uncertain bounds for variables -- for SOW that
            # have a bound specified
            level = VAR.l[*var_domain, *sow_GP]
            deviation = abs(level * s_n)
            VAR.lo[*unc_domain, g.allsow].where[has_s_n] = level - deviation
            VAR.up[*unc_domain, g.allsow].where[has_s_n] = level + deviation

        with Loop(g.Sow[ww]):
            with If(Ord(ww) == 1):
                PARAM[*param_domain, "N"] = 0

            if loop_region:
                with Loop(g.r):
                    copy_deviation_forward()
            else:
                copy_deviation_forward()
        return

    # Clear the bounds for the variables
    if defined:
        VAR.lo[*var_domain, *swd_GP].where[clear_condition] = SpecialValues.NEGINF
    VAR.up[*var_domain, *swd_GP] = SpecialValues.POSINF

    # Set the bounds for the variables
    def set_bounds() -> None:
        VAR.lo[*set_var_domain, *sow_GP].where[main_condition] = sparse(
            PARAM[*param_domain, "LO"]
        )
        VAR.up[*set_var_domain, *sow_GP].where[main_condition] = sparse(
            PARAM[*param_domain, "UP"]
        )
        VAR.fx[*set_var_domain, *sow_GP].where[main_condition] = sparse(
            PARAM[*param_domain, "FX"]
        )

    if loop_region:
        with Loop(g.r):
            set_bounds()
    else:
        set_bounds()

    # Set INF upper bound for N type constraints to activate them (DYN too!)
    PARAM[*param_domain, "UP"].where[
        (~PARAM[*param_domain, "UP"]).where[PARAM[*param_domain, "N"]]
    ] = SpecialValues.POSINF

    if stages.upper() != "YES":
        return

    gate = g.sw_phase == -9
    g.cnt[...] = (
        g.cnt
        + Sum(
            Domain(*param_domain).where[
                (PARAM[*param_domain, "N"] >= 0).where[PARAM[*param_domain, "N"]]
            ],
            1,
        )
    ).where[gate]
    g.cnt[...] = (
        g.cnt
        + Sum(
            Domain(*param_domain, g.w).where[
                (STOCH_PARAM[*param_domain, "N", "1", g.w] >= 0).where[
                    STOCH_PARAM[*param_domain, "N", "1", g.w]
                ]
            ],
            1,
        )
    ).where[gate]

    # $IF%10 NOT %STAGES%==YES $EXIT
    exit_before_uncertain = stages != "YES" if arg10 == "" else stages.upper() != "YES"
    if exit_before_uncertain:
        return

    # Handle uncertain RHS if stochastic mode: Set uncertain bounds for
    # variables
    def uncertain_bounds() -> None:
        gate = main_condition * (g.sw_phase != -2)
        VAR.lo[*set_var_domain, *sow_GP].where[gate] = sparse(
            STOCH_PARAM[*param_domain, "LO", "1", g.Sow]
        )
        VAR.up[*set_var_domain, *sow_GP].where[gate] = sparse(
            STOCH_PARAM[*param_domain, "UP", "1", g.Sow]
        )
        VAR.fx[*set_var_domain, *sow_GP].where[gate] = sparse(
            STOCH_PARAM[*param_domain, "FX", "1", g.Sow]
        )

    if loop_region:
        with Loop(g.r):
            uncertain_bounds()
    else:
        uncertain_bounds()

    if arg10 == "I":
        gate = g.sw_phase == 2

        # Copy UC slack levels for missing first phase runs if necessary
        if stages == "YES":
            ww = g.ww

            with Loop(
                Domain(g.Sow[ww], g.w[ww.lag(1)]).where[
                    (g.s_ucobj["OBJ1", ww] == 4) * gate
                ]
            ):
                VAR.l[*var_domain, ww] = sparse(VAR.l[*var_domain, g.w])
        else:
            VAR.l[*var_domain, *sow_GP].where[gate] = sparse(
                g.spar_ucsl[g.Sow, *var_domain, *spar_ucsl_padding]
            )

        def deviation_bounds_restart() -> None:
            s_n = STOCH_PARAM[*param_domain, "N", "1", g.Sow]

            # Set the deviation bounds for the variables - copy
            # defaults to SOW if not specified
            STOCH_PARAM[*param_domain, "N", "1", g.Sow].where[(~s_n) * gate] = sparse(
                PARAM[*param_domain, "N"]
            )

            # Set deviation uncertain bounds for variables - for SOW
            # that have a bound specified
            has_s_n = (s_n >= 0).where[s_n]
            restart_gate = has_s_n * main_condition * gate
            level = VAR.l[*var_domain, *sow_GP]
            deviation = abs(level * s_n)
            VAR.lo[*set_var_domain, *sow_GP].where[restart_gate] = level - deviation
            VAR.up[*set_var_domain, *sow_GP].where[restart_gate] = level + deviation

        if loop_region:
            with Loop(g.r):
                deviation_bounds_restart()
        else:
            deviation_bounds_restart()


def bnd_ucv_mod(
    *,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg7: str,
    arg8: str,
    arg9: str,
    arg10: str,
    arg11: str,
    arg12: str,
    arg13: str,
    stages: str,
    swd: str,
    sow: str,
    arg1_defined: bool,
) -> str:
    if arg10 == "M":
        return rf"""
  OPTION CLEAR=UNCD1; UNCD1(UC_N)=YES; UNCD1('OBJ1') = NO;
* Initally clear any deterministic N RHS bounds
 LOOP(SOW(WW), IF(ORD(WW)=1, {arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N')=0);
{arg7}
* Copy old deviation bounds forward unless cleared
   {arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N')$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) = 0;
   {arg1}.LO(UC_N(UNCD1){arg2}{arg3}{arg4}{arg9},ALLSOW)${arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N') = {arg1}.LO(UC_N{arg2}{arg3}{arg4}{arg9},SOW);
   {arg1}.UP(UC_N(UNCD1){arg2}{arg3}{arg4}{arg9},ALLSOW)${arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N') = {arg1}.UP(UC_N{arg2}{arg3}{arg4}{arg9},SOW);
* Add flags indicating the new deviation bounds in force
   {arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N')$((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) GE 0)$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) = -1;
* Set deviation uncertain bounds for variables - for SOW that have bound specified
   {arg1}.LO(UC_N(UNCD1){arg2}{arg3}{arg4}{arg9},ALLSOW)$((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) GE 0)$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) =
      {arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})-ABS({arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})*S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW));
   {arg1}.UP(UC_N(UNCD1){arg2}{arg3}{arg4}{arg9},ALLSOW)$((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) GE 0)$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) =
      {arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})+ABS({arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})*S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW));
{arg8}
 );
"""

    if arg10 not in ("", "I"):
        raise ValueError(f"Unhandled argument arg10={arg10!r}.")

    code = rf"""
{
        rf'''* Clear the bounds for the variables
   {arg1}.LO(UC_N{arg2}{arg3}{arg4}{arg9}{swd}){arg12} = -INF;'''
        if arg1_defined
        else ""
    }
   {arg1}.UP(UC_N{arg2}{arg3}{arg4}{arg9}{swd})    =  INF;
*------------------------------------------------------------------------------
* Set the bounds for the variables
{arg7}
   {arg1}.LO(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= {arg5}({arg3}{arg2}UC_N{
        arg4
    }{arg9},'LO');
   {arg1}.UP(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= {arg5}({arg3}{arg2}UC_N{
        arg4
    }{arg9},'UP');
   {arg1}.FX(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= {arg5}({arg3}{arg2}UC_N{
        arg4
    }{arg9},'FX');
{arg8}
*------------------------------------------------------------------------------
* Set INF upper bound for N type constraints to activate them (DYN too!)
   {arg5}({arg3}{arg2}UC_N{arg4}{arg9},'UP')$((NOT {arg5}({arg3}{arg2}UC_N{arg4}{
        arg9
    },'UP'))${arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N')) = INF;
"""

    if stages.upper() != "YES":
        return code

    code += rf"""
 IF(SW_PHASE EQ -9,
   CNT=CNT+SUM(({arg3}{arg2}UC_N{arg4}{arg9})$(({arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N') GE 0)${arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N')),1);
   CNT=CNT+SUM(({arg3}{arg2}UC_N{arg4}{arg9},W)$((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',W) GE 0)$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',W)),1);
 );
"""

    # $IF%10 NOT %STAGES%==YES $EXIT
    if arg10 == "I":
        if stages.upper() != "YES":
            return code
    else:
        if stages != "YES":
            return code

    code += rf"""
* Handle uncertain RHS if stochastic mode: Set uncertain bounds for variables
  IF(SW_PHASE NE -2,
{arg7}
   {arg1}.LO(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'LO','1',SOW);
   {arg1}.UP(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'UP','1',SOW);
   {arg1}.FX(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow}){arg6} $= S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'FX','1',SOW);
{arg8}
  );
"""

    if arg10 == "I":
        code += rf"""
  IF(SW_PHASE EQ 2,
*------------------------------------------------------------------------------
* Copy UC slack levels for missing first phase runs if necessary
{f"LOOP((SOW(WW),W(WW-1))$(S_UCOBJ('OBJ1',SOW) EQ 4),{arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9},SOW) $= {arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9},W));" if stages == "YES" else f"{arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow}) $= SPAR_UCSL(SOW,UC_N{arg2}{arg3}{arg4}{arg9}{arg11});"}
*------------------------------------------------------------------------------
{arg7}
* Set the deviation bounds for the variables - copy defaults to SOW if not specified
   S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)$(NOT S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) $= {arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N');
*------------------------------------------------------------------------------
* Set deviation uncertain bounds for variables - for SOW that have bound specified
   {arg1}.LO(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow})$(((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) GE 0){arg6})$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) =
      {arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})-ABS({arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})*S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW));
   {arg1}.UP(UC_N{arg2}{arg3}{arg4}{arg13}{arg9}{sow})$(((S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW) GE 0){arg6})$S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW)) =
      {arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})+ABS({arg1}.L(UC_N{arg2}{arg3}{arg4}{arg9}{sow})*S_{arg5}({arg3}{arg2}UC_N{arg4}{arg9},'N','1',SOW));
{arg8}
*------------------------------------------------------------------------------
  );
"""

    return code
