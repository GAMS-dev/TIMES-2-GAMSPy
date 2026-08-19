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

from gamspy import Equation, Variable
from gamspy.math import Min

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Set

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
        g = self.tc
        m = g.container

        eq = self.env.eq
        var = self.env.var
        swd = self.env.swd_GP

        # *-----------------------------------------------------------------------------
        # POSITIVE VARIABLES
        # *-----------------------------------------------------------------------------
        g.set_variable(
            name=f"{var}_CLITOT",
            var=Variable(
                m,
                name=f"{var}_CLITOT",
                type="Positive",
                domain=[g.cmitem, g.ll, *swd],
                description="Total emissions or forcing by milestone year",
            ),
        )
        g.set_variable(
            name=f"{var}_CLIBOX",
            var=Variable(
                m,
                name=f"{var}_CLIBOX",
                type="Positive",
                domain=[g.cmitem, g.CmBox, g.ll, *swd],
                description="Quantities in the climate reservoirs",
            ),
        )

        # *-----------------------------------------------------------------------------
        # EQUATIONS
        # *-----------------------------------------------------------------------------
        g.set_equation(
            name=f"{eq}_CLITOT",
            eq=Equation(
                m,
                name=f"{eq}_CLITOT",
                domain=[g.cmitem, g.t, g.ll, *swd],
                description="Balances for the total emissions or forcing",
            ),
        )
        g.set_equation(
            name=f"{eq}_CLICONC",
            eq=Equation(
                m,
                name=f"{eq}_CLICONC",
                domain=[g.cmitem, g.CmBox, g.t, *swd],
                description="Balances for the concentration in the reservoirs",
            ),
        )
        g.set_equation(
            name=f"{eq}_CLITEMP",
            eq=Equation(
                m,
                name=f"{eq}_CLITEMP",
                domain=[g.cmitem, g.CmBox, g.t, *swd],
                description="Balances for the temperature in the reservoirs",
            ),
        )
        g.set_equation(
            name=f"{eq}_CLIBEOH",
            eq=Equation(
                m,
                name=f"{eq}_CLIBEOH",
                domain=[g.cmitem, g.CmBox, g.t, g.ll, *swd],
                description="Balances for the quantities in the BEOH reservoirs",
            ),
        )
        g.set_equation(
            name=f"{eq}_CLIMAX",
            eq=Equation(
                m,
                name=f"{eq}_CLIMAX",
                domain=[g.allyear, g.cmitem, *swd],
                description="Constraint for maximum climate quantities",
            ),
        )

        self.tc.enqueue(
            self.mod_vars_cli_exec,
            eq=self.env.eq,
            var=self.env.var,
            sow=self.env.sow_GP,
        )

    def mod_vars_cli_exec(
        self: ModVarsCli,
        eq: str,
        var: str,
        sow: tuple[Set | Alias, ...] | tuple[()],
    ) -> None:
        g = self.tc

        CmVar, ll = g.CmVar, g.ll
        cm_led, cm_bemi = g.cm_led, g.cm_bemi

        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")

        g.get_equation(f"{eq}_CLITOT").setRecords(None)

        # *-----------------------------------------------------------------------------
        # * Allow some negative emissions
        VAR_CLITOT.lo[CmVar, ll, *sow].where[cm_led[ll]] = Min(-15, cm_bemi[CmVar, ll])
        VAR_CLITOT.lo[CmVar["FORCING"], ll, *sow].where[cm_led[ll]] = -2
