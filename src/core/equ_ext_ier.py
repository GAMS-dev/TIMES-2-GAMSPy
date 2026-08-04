# equ_ext_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQMAIN.EXT declarations & call for actual equations
# *  arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Equation

from core.base_class import GamsClass
from core.eqchpelc_ier import EqchpelcIer
from core.eqmrkcom_ier import EqmrkcomIer

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtIer(GamsClass):  # FilenameExt
    """Translation unit for equ_ext.ier."""

    # Instance attributes
    module_name: str = "equ_ext_ier"
    gams_source: str = "equ_ext.ier"

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
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # *-----------------------------------------------------------------------------
        # * Bound on the market share of a flow in the production/consumption of a commodity
        # *-----------------------------------------------------------------------------
        for sense, share in [
            ("E", "PRD"),
            ("L", "PRD"),
            ("G", "PRD"),
            ("E", "CON"),
            ("L", "CON"),
            ("G", "CON"),
        ]:
            name = f"EQ{sense}_MRK{share}"
            g.set_equation(
                name=name,
                eq=Equation(
                    m,
                    name=name,
                    domain=[g.r, g.t, g.p, g.c, g.s, g.allsow],
                    description=f"{'Production' if share == 'PRD' else 'Consumption'} share (={sense}=)",
                ),
            )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  EQUATIONS
*-----------------------------------------------------------------------------
* Equation bounding the electricity production of extraction condensing CHP plants
* by the available condensing resp. backpressure capacity
*-----------------------------------------------------------------------------
EQL_CHPCON(R,YEAR,YEAR,P,ALLSOW)      'Condensing capacity constraint (=L=)'
EQL_CHPBPT(R,YEAR,YEAR,P,ALLSOW)      'Backpressure capacity constraint (=L=)'
EQE_CHPCON(R,YEAR,YEAR,P,ALLSOW)      'Condensing capacity constraint (=E=)'
EQE_CHPBPT(R,YEAR,YEAR,P,ALLSOW)      'Backpressure capacity constraint (=E=)'
;
*----------------------------End of equations---------------------------------

""",
        )

        # * Call for Implementations
        # *-----------------------------------------------------------------------------
        # * Bound on the market share of a flow in the production/consumption of a commodity
        # *-----------------------------------------------------------------------------

        # fmt: off
        batincludes: list[tuple[str, Literal["E", "N", "L", "G"], str, str, str]] = [
            (f"{self.arg1}", "L", "LO", "PRD", "OUT"),
            (f"{self.arg1}", "E", "FX", "PRD", "OUT"),
            (f"{self.arg1}", "G", "UP", "PRD", "OUT"),
            (f"{self.arg1}", "L", "LO", "CON", "IN"),
            (f"{self.arg1}", "E", "FX", "CON", "IN"),
            (f"{self.arg1}", "G", "UP", "CON", "IN"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                EqmrkcomIer(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                )
            )

        # *-----------------------------------------------------------------------------
        # * Equation bounding the electricity production of extraction condensing CHP plants
        # * by the available condensing resp. backpressure capacity
        # *-----------------------------------------------------------------------------

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
ECT_CHP(RP)$(NOT PRC_CAP(RP)$RP_STD(RP)) = NO;
""",
        )
        if self.env.chp_mode == "YES":
            self.include(
                EqchpelcIer(
                    self.tc,
                    self.env,
                    arg1="L",
                    arg2="UP",
                )
            )
        if self.env.chp_mode == "YES":
            self.include(
                EqchpelcIer(
                    self.tc,
                    self.env,
                    arg1="E",
                    arg2="FX",
                )
            )
