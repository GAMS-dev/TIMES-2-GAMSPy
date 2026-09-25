# eqire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (c) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQIRE ensure that inter-regional imports/exports match up                   *
# *=============================================================================*
# * Questions/Comments:
# * UR 08/24/01: import flows have to be at PRC_TS(Reg,p,s), alternative would be to allow RtpcsVarf
# *              to be at a different level using RTCS_TSFR to bring it to the right TSLVL
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum
from gamspy.math import same_as

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqireMod(GamsClass):
    """Translation unit for eqire.mod."""

    # Instance attributes
    module_name: str = "eqire_mod"
    gams_source: str = "eqire.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        eq_ire = g.get_equation(f"{self.env.eq}_IRE")
        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        RtpSym = g.get_set(f"Rtp{self.env.rtpx}")
        Reg, Com, ie, s, RpcsVar, RpcEqire, p, t, v, r, c = (
            g.Reg,
            g.Com,
            g.ie,
            g.s,
            g.RpcsVar,
            g.RpcEqire,
            g.p,
            g.t,
            g.v,
            g.r,
            g.c,
        )
        RtpVntbyr, RtpcsVarf, RpcAire, prc_actflo = (
            g.RtpVntbyr,
            g.RtpcsVarf,
            g.RpcAire,
            g.prc_actflo,
        )
        xpt, TopIre, com1, RpcMarket = g.xpt, g.TopIre, g.com1, g.RpcMarket
        ts, RsTree, allts, ire_tscvt, ire_ccvt, imp = (
            g.ts,
            g.RsTree,
            g.allts,
            g.ire_tscvt,
            g.ire_ccvt,
            g.imp,
        )
        ire_flo, rs_fr = g.ire_flo, g.rs_fr

        tx = self.env.tx_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP

        eq_ire[RtpSym[Reg, *tx, p], Com, ie, s, *swt].where[
            RpcsVar[Reg, p, Com, s].where[RpcEqire[Reg, p, Com, ie]]
        ] = (
            Sum(  # the imports/exports of commodity Com into Reg at timeslice s
                RtpVntbyr[Reg, t, p, v].where[RtpcsVarf[Reg, t, p, Com, s]],
                VAR_IRE[Reg, v, t, p, Com, s, ie, *sow].where[~RpcAire[Reg, p, Com]]
                + (VAR_ACT[Reg, v, t, p, s, *sow] * prc_actflo[Reg, v, p, Com]).where[
                    RpcAire[Reg, p, Com]
                ],
            )
            * (1 - 2 * xpt[ie])
            + (
                Sum(  # sum also the imports in other regions in case of market-based equation
                    TopIre[Reg, com1, r, c, p].where[
                        (~same_as(Reg, r)).where[RpcMarket[Reg, p, com1, "EXP"]]
                    ],
                    Sum(
                        Domain(
                            RtpVntbyr[r, t, p, v],
                            RtpcsVarf[r, t, p, c, ts],
                            RsTree[r, allts, ts],
                        ).where[ire_tscvt[r, allts, Reg, s]],
                        (
                            VAR_IRE[r, v, t, p, c, ts, "imp", *sow].where[
                                ~RpcAire[r, p, c]
                            ]
                            + (
                                VAR_ACT[r, v, t, p, ts, *sow] * prc_actflo[r, v, p, c]
                            ).where[RpcAire[r, p, c]]
                        )
                        * ire_ccvt[r, c, Reg, com1]
                        * ire_tscvt[r, allts, Reg, s]
                        * rs_fr[r, allts, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, allts, ts, sow)),
                    )
                    * ire_ccvt[Reg, com1, Reg, Com],
                )
            ).where[RpcMarket[Reg, p, Com, "imp"]]
            + (
                Sum(  # sum also the imports in other regions in case of market-based equation: EXP case
                    TopIre[Reg, Com, r, c, p],
                    Sum(
                        Domain(
                            RtpVntbyr[r, t, p, v],
                            RtpcsVarf[r, t, p, c, ts],
                            RsTree[r, allts, ts],
                        ).where[ire_tscvt[r, allts, Reg, s]],
                        (
                            VAR_IRE[r, v, t, p, c, ts, "imp", *sow].where[
                                ~RpcAire[r, p, c]
                            ]
                            + (
                                VAR_ACT[r, v, t, p, ts, *sow] * prc_actflo[r, v, p, c]
                            ).where[RpcAire[r, p, c]]
                        )
                        / ire_flo[Reg, v, p, Com, r, c, ts]
                        * ire_tscvt[r, allts, Reg, s]
                        * rs_fr[r, allts, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, allts, ts, sow)),
                    )
                    * ire_ccvt[r, c, Reg, Com],
                )
            ).where[xpt[ie]]
            == (
                Sum(  # sum the associated exports
                    Domain(TopIre[r, c, Reg, Com, p], allts).where[
                        ire_tscvt[r, allts, Reg, s]
                    ],
                    Sum(
                        Domain(RtpVntbyr[r, t, p, v], RtpcsVarf[r, t, p, c, ts]).where[
                            rs_fr[r, allts, ts]
                        ],
                        (
                            VAR_IRE[r, v, t, p, c, ts, "EXP", *sow].where[
                                ~RpcAire[r, p, c]
                            ]
                            + (
                                VAR_ACT[r, v, t, p, ts, *sow] * prc_actflo[r, v, p, c]
                            ).where[RpcAire[r, p, c]]
                        )
                        # [AL] IRE_TSCVT converts from ALL_TS to S, and RTCS_TSFR from TS to ALL_TS:
                        * ire_flo[r, v, p, c, Reg, Com, s]
                        * ire_tscvt[r, allts, Reg, s]
                        * rs_fr[r, allts, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, allts, ts, sow)),
                    )
                    * ire_ccvt[r, c, Reg, Com],
                )
            ).where[imp[ie]]
        )
