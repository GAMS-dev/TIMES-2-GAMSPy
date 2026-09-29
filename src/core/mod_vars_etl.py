# mod_vars_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.ETL endogenous technology change variables
# *=============================================================================*
# * args1 - source code extension
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation, Variable

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsEtl(GamsClass):
    """Translation unit for mod_vars.etl."""

    # Instance attributes
    module_name: str = "mod_vars_etl"
    gams_source: str = "mod_vars.etl"

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

        var = self.env.var
        eq = self.env.eq
        swd = self.env.swd_GP
        swtd = self.env.swtd_GP

        # VARIABLES
        # -----------------------------------------------------------------------------
        g.set_variable(
            f"{var}_LAMBD",
            Variable(
                m,
                name=f"{var}_LAMBD",
                domain=[g.r, g.allyear, g.prc, g.kp, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_CCAP",
            Variable(
                m,
                name=f"{var}_CCAP",
                domain=[g.r, g.allyear, g.prc, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_CCOST",
            Variable(
                m,
                name=f"{var}_CCOST",
                domain=[g.r, g.allyear, g.prc, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_IC",
            Variable(
                m,
                name=f"{var}_IC",
                domain=[g.r, g.allyear, g.prc, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_DELTA",
            Variable(
                m,
                name=f"{var}_DELTA",
                domain=[g.r, g.allyear, g.prc, g.kp, *swd],
                type="BINARY",
            ),
        )
        # *-----------------------------------------------------------------------------
        # *  EQUATIONS
        # *-----------------------------------------------------------------------------
        g.set_equation(
            f"{eq}_CUINV",
            Equation(
                m,
                name=f"{eq}_CUINV",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Cumulative Capacity Definition",
            ),
        )
        g.set_equation(
            f"{eq}_CC",
            Equation(
                m,
                name=f"{eq}_CC",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Cumulative Capacity Interpolation",
            ),
        )
        g.set_equation(
            f"{eq}_DEL",
            Equation(
                m,
                name=f"{eq}_DEL",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Delta to 1",
            ),
        )
        g.set_equation(
            f"{eq}_COS",
            Equation(
                m,
                name=f"{eq}_COS",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Cumulative Cost",
            ),
        )
        g.set_equation(
            f"{eq}_LA1",
            Equation(
                m,
                name=f"{eq}_LA1",
                domain=[g.r, g.allyear, g.prc, g.kp, *swtd],
                description="Constraints on lambda 1",
            ),
        )
        g.set_equation(
            f"{eq}_LA2",
            Equation(
                m,
                name=f"{eq}_LA2",
                domain=[g.r, g.allyear, g.prc, g.kp, *swtd],
                description="Constraints on lambda 2",
            ),
        )
        g.set_equation(
            f"{eq}_EXPE1",
            Equation(
                m,
                name=f"{eq}_EXPE1",
                domain=[g.r, g.allyear, g.prc, g.kp, *swtd],
                description="Experience grows 1",
            ),
        )
        g.set_equation(
            f"{eq}_EXPE2",
            Equation(
                m,
                name=f"{eq}_EXPE2",
                domain=[g.r, g.allyear, g.prc, g.kp, *swtd],
                description="Experience grows 2",
            ),
        )
        g.set_equation(
            f"{eq}_IC1",
            Equation(
                m,
                name=f"{eq}_IC1",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Investments tech. change 1st period",
            ),
        )
        g.set_equation(
            f"{eq}_IC2",
            Equation(
                m,
                name=f"{eq}_IC2",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Investments tech. change other periods",
            ),
        )
        # * cluster
        g.set_equation(
            f"{eq}_CLU",
            Equation(
                m,
                name=f"{eq}_CLU",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Cluster",
            ),
        )
        g.set_equation(
            f"{eq}_MRCLU",
            Equation(
                m,
                name=f"{eq}_MRCLU",
                domain=[g.r, g.allyear, g.prc, *swtd],
                description="Multi-regional Cluster",
            ),
        )
