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
from typing import TYPE_CHECKING

from gamspy import Equation

from core.base_class import GamsClass
from core.eqchpelc_ier import EqchpelcIer, EqchpelcIerConfig
from core.eqmrkcom_ier import EqmrkcomIer, EqmrkcomIerConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


# TODO For now without dataclass because it gets called in a boundle
class EquExtIer(GamsClass):
    """Translation unit for equ_ext.ier."""

    # Instance attributes
    module_name: str = "equ_ext_ier"
    gams_source: str = "equ_ext.ier"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
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

        # *-----------------------------------------------------------------------------
        # * Equation bounding the electricity production of extraction condensing CHP plants
        # * by the available condensing resp. backpressure capacity
        # *-----------------------------------------------------------------------------
        g.eql_chpcon = Equation(
            m,
            name="EQL_CHPCON",
            domain=[g.r, g.year, g.year, g.p, g.allsow],
            description="Condensing capacity constraint (=L=)",
        )
        g.eql_chpbpt = Equation(
            m,
            name="EQL_CHPBPT",
            domain=[g.r, g.year, g.year, g.p, g.allsow],
            description="Backpressure capacity constraint (=L=)",
        )
        g.eqe_chpcon = Equation(
            m,
            name="EQE_CHPCON",
            domain=[g.r, g.year, g.year, g.p, g.allsow],
            description="Condensing capacity constraint (=E=)",
        )
        g.eqe_chpbpt = Equation(
            m,
            name="EQE_CHPBPT",
            domain=[g.r, g.year, g.year, g.p, g.allsow],
            description="Backpressure capacity constraint (=E=)",
        )
        # *----------------------------End of equations---------------------------------

        # * Call for Implementations
        # *-----------------------------------------------------------------------------
        # * Bound on the market share of a flow in the production/consumption of a commodity
        # *-----------------------------------------------------------------------------

        # fmt: off
        batincludes: list[EqmrkcomIerConfig] = [
            EqmrkcomIerConfig(arg1=self.arg1, arg2="L", arg3="LO", arg4="PRD", arg5="OUT"),
            EqmrkcomIerConfig(arg1=self.arg1, arg2="E", arg3="FX", arg4="PRD", arg5="OUT"),
            EqmrkcomIerConfig(arg1=self.arg1, arg2="G", arg3="UP", arg4="PRD", arg5="OUT"),
            EqmrkcomIerConfig(arg1=self.arg1, arg2="L", arg3="LO", arg4="CON", arg5="IN"),
            EqmrkcomIerConfig(arg1=self.arg1, arg2="E", arg3="FX", arg4="CON", arg5="IN"),
            EqmrkcomIerConfig(arg1=self.arg1, arg2="G", arg3="UP", arg4="CON", arg5="IN"),
        ]
        # fmt: on
        for config in batincludes:
            self.include(EqmrkcomIer(self.tc, self.env, config=config))

        # *-----------------------------------------------------------------------------
        # * Equation bounding the electricity production of extraction condensing CHP plants
        # * by the available condensing resp. backpressure capacity
        # *-----------------------------------------------------------------------------

        self.tc.enqueue(self.clear_ect_chp_without_capacity)

        if self.env.chp_mode == "YES":
            self.include(
                EqchpelcIer(self.tc, self.env, EqchpelcIerConfig(sense="L", arg2="UP"))
            )
            self.include(
                EqchpelcIer(self.tc, self.env, EqchpelcIerConfig(sense="E", arg2="FX"))
            )

    def clear_ect_chp_without_capacity(self: EquExtIer) -> None:
        g = self.tc
        g.EctChp[g.Rp].where[(~(g.PrcCap[g.Rp].where[g.RpStd[g.Rp]]))] = False
