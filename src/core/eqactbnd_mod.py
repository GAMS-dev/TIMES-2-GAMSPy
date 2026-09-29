# eqactbnd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTBND limits the activity of vintage processes or higher TS-level bounds
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *=============================================================================*
# * Questions/Comments:
# *  - ACT_BND ts restricted to the PRC_TS level or above
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Expression, Number, Sum

from core.base_class import GamsClass
from core.utils import generate_equation

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqactbndModConfig:
    sense: Literal["G", "E", "L"]
    arg2: Literal["LO", "FX", "UP"]
    arg3: Expression | Number


class EqactbndMod(GamsClass):
    """Translation unit for eqactbnd.mod."""

    # Instance attributes
    module_name: str = "eqactbnd_mod"
    gams_source: str = "eqactbnd.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqactbndModConfig
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config
        (
            RtpVara,
            p,
            s,
            PrcTs,
            r,
            ts,
            RtpVintyr,
            v,
            t,
            TsMap,
            act_bnd,
            RpsPrcts,
            PrcVint,
        ) = (
            g.RtpVara,
            g.p,
            g.s,
            g.PrcTs,
            g.r,
            g.ts,
            g.RtpVintyr,
            g.v,
            g.t,
            g.TsMap,
            g.act_bnd,
            g.RpsPrcts,
            g.PrcVint,
        )

        swt = self.env.swt_GP
        sow = self.env.sow_GP
        r_t = self.env.r_t_GP

        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")

        # V0.5b 980902 - avoid equations if LO=0/UP=INF
        # $ONLISTING
        # [UR] 21.07.2003 tightended control for generation of equation to RTP_VARA

        eqe_actbnd = g.get_equation(f"{self.env.eq}{cc.sense}_ACTBND")

        eqe_actbnd[RtpVara[*r_t, p], s, *swt].where[
            (
                RpsPrcts[r, p, s] * (PrcVint[r, p] + (~PrcTs[r, p, s])).where[cc.arg3]
            ).where[act_bnd[r, t, p, s, cc.arg2]]
        ] = generate_equation(
            # sum over all possible at process TS-level
            Sum(
                PrcTs[r, p, ts].where[TsMap[r, s, ts]],
                # sum all the existing activities
                Sum(RtpVintyr[r, v, t, p], VAR_ACT[r, v, t, p, ts, *sow]),
            ),
            cc.sense,
            act_bnd[r, t, p, s, cc.arg2],
        )
