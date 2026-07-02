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
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndUcvMod(GamsClass):
    """Translation unit for bnd_ucv.mod."""

    # Instance attributes
    module_name: str = "bnd_ucv"
    gams_source: str = "bnd_ucv.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
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
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.arg8 = arg8
        self.arg9 = arg9
        self.arg10 = arg10
        self.arg11 = arg11
        self.arg12 = arg12
        self.arg13 = arg13

        self._sub_modules = {}
        self.compile()

    def compile(self: BndUcvMod) -> None:
        self.tc.enqueue(
            self.exec_bnd_ucv_mod,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg9,
            arg10=self.arg10,
            arg11=self.arg11,
            arg12=self.arg12,
            arg13=self.arg13,
            stages=self.env.stages,
            swd=self.env.swd,
            sow=self.env.sow,
            arg1_defined=self.tc.defined_assigned(self.arg1),
        )

    def exec_bnd_ucv_mod(
        self: BndUcvMod,
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
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=bnd_ucv_mod(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                arg6=arg6,
                arg7=arg7,
                arg8=arg8,
                arg9=arg9,
                arg10=arg10,
                arg11=arg11,
                arg12=arg12,
                arg13=arg13,
                stages=stages,
                swd=swd,
                sow=sow,
                arg1_defined=arg1_defined,
            ),
        )


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
