# eqstgaux_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGAUX auxiliary commodities for storage
# *=============================================================================*
# *AL Questions/Comments:
# * Assumption is that all auxiliary flows are at PRC_TS level; NST primary flows can be also above
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgauxLin(GamsClass):
    """Translation unit for eqstgaux.lin."""

    # Instance attributes
    module_name: str = "eqstgaux_lin"
    gams_source: str = "eqstgaux.lin"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        rts = macro.rts_GP(g.s, g=self.tc, env=self.env)

        eq_stgaux = g.get_equation(f"{self.env.eq}_STGAUX")
        var = self.env.var
        VAR_FLO = g.get_variable(f"{var}_FLO")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")

        sow = self.env.sow_GP
        r_v_t = self.env.r_v_t_GP
        swt = self.env.swt_GP

        eq_stgaux[g.RtpVintyr[*r_v_t, g.p], g.c, rts, *swt].where[
            (
                (
                    g.RpcsVar[g.r, g.p, g.c, g.s]
                    * (~(g.RpcStg[g.r, g.p, g.c] + g.RpcEmis[g.r, g.p, g.c]))
                ).where[g.RpStg[g.r, g.p]]
            )
            # * Auxiliary flow variable
        ] = VAR_FLO[g.r, g.v, g.t, g.p, g.c, g.s, *sow] == Sum(
            # * flow depends on storage level in period T
            g.Annual[g.sl],
            g.prc_actflo[g.r, g.v, g.p, g.c]
            * (
                Sum(
                    g.PrcTs[g.r, g.p, g.ts].where[g.TsMap[g.r, g.ts, g.s]],
                    VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow] / g.rs_stgprd[g.r, g.ts],
                )
                * g.g_yrfr[g.r, g.s]
                # * subtract in- and output flows to/from storage during latter half of milestone year
                - Sum(
                    g.Top[g.PrcStgips[g.r, g.p, g.Com], g.io],
                    0.5
                    * (
                        VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.sl, *sow].where[
                            g.ips[g.io]
                        ]
                        - VAR_SOUT[g.r, g.v, g.t, g.p, g.Com, g.sl, *sow].where[
                            (~(g.ips[g.io]))
                        ]
                    )
                    / g.prc_actflo[g.r, g.v, g.p, g.Com]
                    # * storage losses (assume that Inflows and outflows occur at the mid-point of each year)
                    * ((1.0 - g.stg_loss[g.r, g.v, g.p, g.sl]) ** 0.5),
                )
            )
            # * For IPS, MID storage level is (1-LOSS)**(0.5) higher
            * (
                1.0
                + (((1.0 - g.stg_loss[g.r, g.v, g.p, g.sl]) ** (-0.5)) - 1.0).where[
                    g.PrcMap[g.r, "STK", g.p]
                ]
            ),
        ) + Sum(
            # * flow depends on storage in- or outflow in period T
            Domain(
                g.ComGmap[g.r, g.cg, g.Com],
                g.Top[g.RpcStg[g.r, g.p, g.Com], "IN"],
                g.RpcsVar[g.r, g.p, g.Com, g.ts],
            ).where[g.coef_ptran[g.r, g.v, g.p, g.cg, g.Com, g.c, g.ts]],
            (
                VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow]
                * g.coef_ptran[g.r, g.v, g.p, g.cg, g.Com, g.c, g.ts]
            ).where[((~(g.PrcMap[g.r, "NST", g.p])) + g.PrcNstts[g.r, g.p, g.ts])]
            * g.rs_fr[g.r, g.s, g.ts]
            * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.s, g.ts, sow)),
        ) + Sum(
            Domain(
                g.ComGmap[g.r, g.cg, g.c],
                g.Top[g.RpcStg[g.r, g.p, g.Com], "OUT"],
                g.RpcsVar[g.r, g.p, g.Com, g.ts],
            ).where[g.coef_ptran[g.r, g.v, g.p, g.cg, g.c, g.Com, g.s]],
            (
                VAR_SOUT[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow]
                * (1.0 / g.coef_ptran[g.r, g.v, g.p, g.cg, g.c, g.Com, g.s])
            ).where[
                (
                    (
                        (~(g.PrcNstts[g.r, g.p, g.ts]))
                        | (g.RpcStgn[g.r, g.p, g.Com, "OUT"])
                    )
                    & (
                        (~(g.RpcStgn[g.r, g.p, g.Com, "OUT"]))
                        | (g.PrcNstts[g.r, g.p, g.ts])
                    )
                )
            ]
            * g.rs_fr[g.r, g.s, g.ts]
            * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.s, g.ts, sow)),
        )
