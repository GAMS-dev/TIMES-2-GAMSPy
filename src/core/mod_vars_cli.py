# mod_vars_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.CLI lists the individual variables of CLI instances of the MODEL   *
# *=============================================================================*
# * Comments: For convenience, equations are declared here as well
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsCli(GamsClass):
    """Translation unit for mod_vars.cli."""

    # Instance attributes
    module_name: str = "mod_vars_cli"
    gams_source: str = "mod_vars.cli"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
POSITIVE VARIABLES
  {self.env.var}_CLITOT(CM_ITEM,LL {self.env.swd}) 'Total emissions or forcing by milestone year'
  {self.env.var}_CLIBOX(CM_ITEM,CM_BOX,LL {self.env.swd}) 'Quantities in the climate reservoirs'
;
*-----------------------------------------------------------------------------
EQUATIONS
  {self.env.eq}_CLITOT(CM_ITEM,T,LL {self.env.swd}) 'Balances for the total emissions or forcing'
  {self.env.eq}_CLICONC(CM_ITEM,CM_BOX,T {self.env.swd}) 'Balances for the concentration in the reservoirs'
  {self.env.eq}_CLITEMP(CM_ITEM,CM_BOX,T {self.env.swd}) 'Balances for the temperature in the reservoirs'
  {self.env.eq}_CLIBEOH(CM_ITEM,CM_BOX,T,LL {self.env.swd}) 'Balances for the quantities in the BEOH reservoirs'
  {self.env.eq}_CLIMAX(ALLYEAR,CM_ITEM {self.env.swd}) 'Constraint for maximum climate quantities'
;
""",
        )
        self.tc.enqueue(
            self.mod_vars_cli_exec,
            eq=self.env.eq,
            var=self.env.var,
            sow=self.env.sow,
        )

    def mod_vars_cli_exec(
        self: ModVarsCli,
        eq: str,
        var: str,
        sow: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
OPTION CLEAR={eq}_CLITOT;
*-----------------------------------------------------------------------------
* Allow some negative emissions
  {var}_CLITOT.LO(CM_VAR,LL {sow})$CM_LED(LL) = MIN(-15,CM_BEMI(CM_VAR,LL));
  {var}_CLITOT.LO(CM_VAR('FORCING'),LL{sow})$CM_LED(LL) = -2;
""",
        )
