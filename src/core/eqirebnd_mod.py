# eqirebnd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQIREBND limits the activity of inter-regional exchange process
# *   %1 - equation declaration type
# *   %2 - bound type for {%1}
# *   %3 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - BND ts restricted to the PRC_TS level or above?
# *UR* /12/09/99 commodity names can be different in the two regions
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Expression, Number, Sum

from core.base_class import GamsClass
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqirebndModConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""

    arg1: Literal["E", "L", "G"]
    arg2: str
    arg3: Expression | Number


class EqirebndMod(GamsClass):
    """Translation unit for eqirebnd.mod."""

    # Instance attributes
    module_name: str = "eqirebnd_mod"
    gams_source: str = "eqirebnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqirebndModConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        r, t, v, p, c, s = g.r, g.t, g.v, g.p, g.c, g.s
        ie, sl, ts, allts = g.ie, g.sl, g.ts, g.allts
        allreg, com = g.allreg, g.Com

        tx = self.env.tx_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP

        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")

        eq = g.get_equation(f"{self.env.eq}{cc.arg1}_IREBND")

        # V0.5b 980902 - avoid equations if LO=0/UP=INF
        # V0.6a 990301
        eq[r, *tx, c, s, allreg, ie, *swt].where[
            ((g.RcsComts[r, c, s] * Sum(g.RpcIre[r, p, c, ie], 1)) & cc.arg3).where[
                g.ire_bnd[r, t, c, s, allreg, ie, cc.arg2]
            ]
        ] = generate_equation(
            (
                # For imports from internal non-marketplace region, sum the associated exports
                Sum(
                    (g.TopIre[g.Reg[allreg], com, r, c, p]).where[
                        g.RpcEqire[r, p, c, "IMP"]
                    ],
                    Sum(
                        sl.where[g.RtpcsVarf[r, t, p, c, sl] * g.RsTree[r, s, sl]],
                        Sum(
                            Domain(
                                g.RtpVntbyr[g.Reg, t, p, v],
                                g.RtpcsVarf[g.Reg, t, p, com, ts],
                                g.RsTree[g.Reg, allts, ts],
                            ).where[g.ire_tscvt[g.Reg, allts, r, sl]],
                            (
                                VAR_IRE[g.Reg, v, t, p, com, ts, "EXP", *sow].where[
                                    ~g.RpcAire[g.Reg, p, com]
                                ]
                                + (
                                    VAR_ACT[g.Reg, v, t, p, ts, *sow]
                                    * g.prc_actflo[g.Reg, v, p, com]
                                ).where[g.RpcAire[g.Reg, p, com]]
                            )
                            * g.ire_flo[g.Reg, v, p, com, r, c, sl]
                            * g.ire_ccvt[g.Reg, com, r, c]
                            * g.ire_tscvt[g.Reg, allts, r, sl]
                            * g.rs_fr[g.Reg, allts, ts]
                            # bound coarser than variable or bound finer than variable
                            * (
                                1
                                + macro.rtcs_fr.rtcs_fr_GP(
                                    g.Reg, t, com, allts, ts, sow
                                )
                            ),
                        )
                        * (
                            Number(1).where[g.TsMap[r, s, sl]]
                            + (g.g_yrfr[r, s] / g.g_yrfr[r, sl]).where[
                                g.RsBelow[r, sl, s]
                            ]
                        ),
                    ),
                )
                +
                # For imports from external regions or marketplace, sum the flows directly in region R
                Sum(
                    g.RpcIre[r, p, c, ie].where[
                        (~g.RpcEqire[r, p, c, "IMP"])
                        * Sum(g.TopIre[allreg, com, r, c, p], 1)
                    ],
                    Sum(
                        Domain(
                            g.RtpVntbyr[r, t, p, v],
                            g.RtpcsVarf[r, t, p, c, ts],
                        ).where[g.RsTree[r, s, ts]],
                        (
                            VAR_IRE[r, v, t, p, c, ts, ie, *sow].where[
                                ~g.RpcAire[r, p, c]
                            ]
                            + (
                                VAR_ACT[r, v, t, p, ts, *sow] * g.prc_actflo[r, v, p, c]
                            ).where[g.RpcAire[r, p, c]]
                        )
                        # bound coarser than variable or bound finer than variable
                        * (
                            Number(1).where[g.TsMap[r, s, ts]]
                            + (g.g_yrfr[r, s] / g.g_yrfr[r, ts]).where[
                                g.RsBelow[r, ts, s]
                            ]
                        ),
                    ),
                )
            ).where[g.imp[ie]]
            + (
                # For exports from market region to internal region REG, sum the associated imports into REG
                Sum(
                    Domain(
                        g.RpcMarket[r, p, c, "EXP"],
                        g.TopIre[r, c, g.Reg[allreg], com, p],
                    ),
                    Sum(
                        Domain(
                            g.RtpVntbyr[g.Reg, t, p, v],
                            g.RtpcsVarf[g.Reg, t, p, com, ts],
                            g.RsTree[g.Reg, allts, ts],
                        ).where[g.ire_tscvt[g.Reg, allts, r, s]],
                        (
                            VAR_IRE[g.Reg, v, t, p, com, ts, "IMP", *sow].where[
                                ~g.RpcAire[g.Reg, p, com]
                            ]
                            + (
                                VAR_ACT[g.Reg, v, t, p, ts, *sow]
                                * g.prc_actflo[g.Reg, v, p, com]
                            ).where[g.RpcAire[g.Reg, p, com]]
                        )
                        * g.ire_ccvt[g.Reg, com, r, c]
                        * g.ire_tscvt[g.Reg, allts, r, s]
                        * g.rs_fr[g.Reg, allts, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(g.Reg, t, com, allts, ts, sow)),
                    ),
                )
                +
                # For all other exports, sum the flows directly in region R
                # *UR* /12/09/99 commodity names can be different in the two regions
                Sum(
                    g.RpcIre[r, p, c, ie].where[
                        (~g.RpcMarket[r, p, c, "EXP"])
                        * Sum(g.TopIre[r, c, allreg, com, p], 1)
                    ],
                    Sum(
                        Domain(
                            g.RtpVntbyr[r, t, p, v],
                            g.RtpcsVarf[r, t, p, c, ts],
                        ).where[g.RsTree[r, s, ts]],
                        (
                            VAR_IRE[r, v, t, p, c, ts, ie, *sow].where[
                                ~g.RpcAire[r, p, c]
                            ]
                            + (
                                VAR_ACT[r, v, t, p, ts, *sow] * g.prc_actflo[r, v, p, c]
                            ).where[g.RpcAire[r, p, c]]
                        )
                        # bound coarser than variable or bound finer than variable
                        * (
                            Number(1).where[g.TsMap[r, s, ts]]
                            + (g.g_yrfr[r, s] / g.g_yrfr[r, ts]).where[
                                g.RsBelow[r, ts, s]
                            ]
                        ),
                    ),
                )
            ).where[g.xpt[ie]],
            cc.arg1,
            g.ire_bnd[r, t, c, s, allreg, ie, cc.arg2],
        )
