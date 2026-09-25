# eqxbnd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQXBND limits the total exchange from internal + external regions
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *   %3 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - BND ts restricted to the PRC_TS level or above?
# *  - *** NOTE: IMPort SUMs all EXPorts and vise versa
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Expression, Number, Sum

from core.base_class import GamsClass
from core.utils import generate_equation

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass


logger = logging.getLogger(__name__)


@dataclass
class EqxbndModConfig:
    arg1: Literal["G", "E", "L"]
    arg2: Literal["LO", "FX", "UP"]
    arg3: Number | Expression


class EqxbndMod(GamsClass):
    """Translation unit for eqxbnd.mod."""

    module_name: str = "eqxbnd_mod"
    gams_source: str = "eqxbnd.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqxbndModConfig
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        allreg, c, s, ie, p, t, RpcIre, ire_xbnd, Reg, ts, v, r, Com = (
            g.allreg,
            g.c,
            g.s,
            g.ie,
            g.p,
            g.t,
            g.RpcIre,
            g.ire_xbnd,
            g.Reg,
            g.ts,
            g.v,
            g.r,
            g.Com,
        )

        swt = self.env.swt_GP

        eq = g.get_equation(name=f"{self.env.eq}{cc.arg1}_XBND")

        var_ire = g.get_variable(name=f"{self.env.var}_IRE")
        var_act = g.get_variable(name=f"{self.env.var}_ACT")

        # *V0.5b 980902 - avoid equations if LO=0/UP=INF
        cond = (Sum(RpcIre[allreg, p, c, ie], 1) * cc.arg3).where[
            ire_xbnd[allreg, t, c, s, ie, cc.arg2]
        ]
        eq[allreg, *self.env.tx_GP, c, s, ie, *swt].where[
            cond
            # *-----------------------------------------------------------------------------
            # * if region is internal then handle by
            # *-----------------------------------------------------------------------------
            # * sum over all possible at process TS-level
        ] = generate_equation(
            lhs=Sum(
                Domain(
                    RpcIre[Reg[allreg], p, c, ie],
                    g.RtpcsVarf[Reg, t, p, c, ts],
                ).where[g.RsTree[Reg, s, ts]],  # * sum all the existing activities
                Sum(
                    g.RtpVntbyr[Reg, t, p, v],
                    var_ire[Reg, v, t, p, c, ts, ie, *self.env.sow_GP].where[
                        (~(g.RpcAire[Reg, p, c]))
                    ]  # * [UR] model reduction REDUCE is set in *.run
                    + (
                        var_act[Reg, v, t, p, ts, *self.env.sow_GP]
                        * g.prc_actflo[Reg, v, p, c]
                    ).where[g.RpcAire[Reg, p, c]],
                )  # * bound coarser than variable or bound finer than variable
                * g.rs_fr[Reg, s, ts],
            )
            # *-----------------------------------------------------------------------------
            # * if region is external then handle the internal guys
            # *-----------------------------------------------------------------------------
            # * sum over all possible at process TS-level
            # *V05c 980811 - use IMP/EXP sets instead of ordering
            + Sum(
                RpcIre[r, p, Com, g.impexp[ie.lag(1, type="circular")]].where[
                    (
                        (g.TopIre[allreg, c, r, Com, p].where[g.xpt[ie]])
                        + (g.TopIre[r, Com, allreg, c, p].where[g.imp[ie]])
                    )
                ],
                # * sum all the existing activities
                Sum(
                    g.RsTree[r, g.allts, ts].where[
                        (
                            g.RtpcsVarf[r, t, p, Com, ts]
                            * g.ire_tscvt[r, g.allts, allreg, s]
                        )
                    ],
                    Sum(  # * [UR] model reduction REDUCE is set in *.run
                        g.RtpVntbyr[r, t, p, v],
                        (
                            var_ire[
                                r, v, t, p, Com, ts, g.impexp, *self.env.sow_GP
                            ].where[(~(g.RpcAire[r, p, Com]))]
                            + (
                                var_act[r, v, t, p, ts, *self.env.sow_GP]
                                * g.prc_actflo[r, v, p, Com]
                            ).where[g.RpcAire[r, p, Com]]
                        )
                        # * ALL_TS coarser than variable or finer than variable
                        * g.ire_tscvt[r, g.allts, allreg, s]
                        * g.rs_fr[r, g.allts, ts],
                    ),
                ),
            ).where[(~(Reg[allreg]))],
            type=cc.arg1,
            rhs=ire_xbnd[allreg, t, c, s, ie, cc.arg2],
        )
