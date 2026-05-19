# bnd_set_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_SET.MOD set the actual bounds on variables
#   %1 - variable reference
#   %2 - primary index into variable
#   %3 - qualifier/bound expression
#   %4 - control index
#   %5 - stochastic qualifier
# =============================================================================*
# GaG Questions/Comments:
#   - FX take precedence as is set last!!!
#   - take primary index loop control criteria too, or reset all in case change
#     in data (e.g., process moves from 1 region to another?) LATTER!!!
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndSetMod(GamsClass):
    """Translation unit for bnd_set.mod."""

    module_name: str = "bnd_set"
    gams_source: str = "bnd_set.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_bnd_set_mod,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            stages=self.env.stages,
            swd=self.env.swd,
            sow=self.env.sow,
            stochastic_symbol_declared=(
                f"S_{self.arg3}" in self.tc.container.listSymbols()
            ),
        )

    def exec_bnd_set_mod(
        self: BndSetMod,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        stages: str,
        swd: str,
        sow: str,
        stochastic_symbol_declared: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=bnd_set_mod(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                arg6=arg6,
                stages=stages,
                swd=swd,
                sow=sow,
                stochastic_symbol_declared=stochastic_symbol_declared,
            ),
        )


def bnd_set_mod(
    *,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    stages: str,
    swd: str,
    sow: str,
    stochastic_symbol_declared: bool,
) -> str:
    if arg6 == "":
        stop = stages != "YES"
    elif arg6 == "I":
        stop = stages.upper() != "YES"
    else:
        raise ValueError(f"Unhandled argument arg6={arg6!r}.")

    stochastic_bounds = ""
    if not stop and stochastic_symbol_declared:
        stochastic_bounds = rf"""
*-----------------------------------------------------------------------------
* Stochastic bounds
  {arg1}.LO({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'LO','1',SOW);
  {arg1}.UP({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'UP','1',SOW);
  {arg1}.FX({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'FX','1',SOW);
"""

    return rf"""
* reset any existing bounds
  {arg1}.LO({arg2}{swd}) = 0;
  {arg1}.UP({arg2}{swd}) = INF;
* assign from user data
  {arg1}.LO({arg4}{sow}){arg5}  $=  {arg3}({arg2},'LO');
  {arg1}.UP({arg4}{sow}){arg5}  $=  {arg3}({arg2},'UP');
  {arg1}.FX({arg4}{sow}){arg5}  $=  {arg3}({arg2},'FX');
{stochastic_bounds}
"""
