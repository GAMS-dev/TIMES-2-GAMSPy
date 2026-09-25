# eqbndcom_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCOMBND limits the total NET/PRD of a commodity at a level above COM_TS
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *   %4 - NET/PRD indicator
# *=============================================================================*
# *GaG Questions/Comments:
# * V0.5c added
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Sum

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Expression, Number

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

from core.utils import generate_equation

logger = logging.getLogger(__name__)


@dataclass
class EqbndcomModConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""

    arg1: Literal["E", "N", "L", "G"]
    arg2: str
    arg3: Expression | Number
    arg4: str


class EqbndcomMod(GamsClass):
    """Translation unit for eqbndcom.mod."""

    # Instance attributes
    module_name: str = "eqbndcom_mod"
    gams_source: str = "eqbndcom.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqbndcomModConfig
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config
        r, t, c, s, ts = g.r, g.t, g.c, g.s, g.ts

        eq = self.tc.get_equation(name=f"{self.env.eq}{cc.arg1}_BND{cc.arg4}")
        com_bnd_param = g.get_parameter(name=f"COM_BND{cc.arg4}")
        VAR_COM = g.get_variable(name=f"{self.env.var}_COM{cc.arg4}")

        r_t = self.env.r_t_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP

        eq[g.Rtc[*r_t, c], s, *swt].where[
            g.RcsComts[r, c, s].where[
                ~g.ComTs[r, c, s] & cc.arg3 & com_bnd_param[r, t, c, s, cc.arg2]
            ]
        ] = generate_equation(
            # sum over all possible commodity flow at/below TS-level
            Sum(
                g.RtcsVarc[r, t, c, ts].where[g.TsMap[r, s, ts]],
                VAR_COM[r, t, c, ts, *sow],
            ),
            cc.arg1,
            com_bnd_param[r, t, c, s, cc.arg2],
        )
