# eqcpt_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCPT.MOD capacity transfer equation
# *  - %1 = equation type when VALIDATE
# *  - %2 = equation name adj (L) when VALIDATE (for DMDs in MARKAL)
# *  - %3 = control qualifier
# *  - %4 = RHS constant or VAR_CAP
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_CPT established in COEF_CPT.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Expression, Number, Sum

from core.base_class import GamsClass
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import (
        ImplicitParameter,
        ImplicitSet,
        ImplicitVariable,
    )

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqcptModConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""

    sense: Literal["E", "L", "G"]
    arg2: Literal["E", "L", "G"]
    arg3: Condition | Expression | Number | ImplicitSet
    arg4: ImplicitVariable | ImplicitParameter | Number


class EqcptMod(GamsClass):
    """Translation unit for eqcpt.mod."""

    # Instance attributes
    module_name: str = "eqcpt_mod"
    gams_source: str = "eqcpt.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqcptModConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        r, v, t, p = g.r, g.v, g.t, g.p

        swt = self.env.swt_GP
        sws = self.env.sws_GP
        rcapsub = self.env.rcapsub_GP

        eq, swt = macro.EQ_CPT_GP(self.env.eq, cc.arg2, swt)

        # GG V0.6a_3+ check whether used in UserConstraint
        eq[g.Rtp[r, t, p], *swt].where[cc.arg3] = generate_equation(  # type: ignore
            # VAR_CAP(r,t,p {self.env.sow}) or CAP_BND(r,t,p,bd):
            lhs=cc.arg4,
            type=cc.sense,
            rhs=Sum(
                v.where[g.coef_cpt[r, v, t, p]],
                g.coef_cpt[r, v, t, p]
                * (
                    macro.VAR_NCAP_GP(self.env.varv_GP, r, v, p, sws).where[
                        g.Milestonyr[v]
                    ]
                    + g.ncap_pasti[r, v, p].where[g.Pastyear[v]]
                    + rcapsub
                ),
            ),
        )
