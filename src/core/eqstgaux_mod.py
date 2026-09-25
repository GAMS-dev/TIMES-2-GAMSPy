# eqstgaux_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTG Inter-Period Storage (IPS) and TIME-Slice Storage (TSS)               *
# *=============================================================================*
# *UR Questions/Comments:
# *
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum
from gamspy.math import Max, Min

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgauxMod(GamsClass):
    """Translation unit for eqstgaux.mod."""

    # Instance attributes
    module_name: str = "eqstgaux_mod"
    gams_source: str = "eqstgaux.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        rts = macro.rts_GP(s=g.s, g=g, env=self.env)
        r_v_t = self.env.r_v_t_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP

        eq = g.get_equation(f"{self.env.eq}_STGAUX")
        VAR_FLO = g.get_variable(f"{self.env.var}_FLO")
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        VAR_SIN = g.get_variable(f"{self.env.var}_SIN")
        VAR_SOUT = g.get_variable(f"{self.env.var}_SOUT")

        eq[g.RtpVintyr[*r_v_t, g.p], g.c, rts, *swt].where[
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
                - Sum(
                    # * subtract in- and output flows to/from storage during latter half of period (from middle of M(T))
                    g.Top[g.PrcStgips[g.r, g.p, g.Com], g.io],
                    (
                        VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.sl, *sow].where[
                            g.ips[g.io]
                        ]
                        - VAR_SOUT[g.r, g.v, g.t, g.p, g.Com, g.sl, *sow].where[
                            (~(g.ips[g.io]))
                        ]
                    )
                    / g.prc_actflo[g.r, g.v, g.p, g.Com],
                )
                * Sum(
                    g.Periodyr[g.t, g.YEoh].where[(g.yearval[g.YEoh] >= g.m[g.t])],
                    # * storage losses (assume that Inflows and outflows occur at the mid-point of each year)
                    Min(
                        1.0,
                        g.yearval[g.YEoh]
                        - g.m[g.t]
                        + Max(0.0, g.m[g.t] + g.d[g.t] / 2.0 - g.e[g.t]),
                    )
                    # * For IPS, MID storage level is (1-LOSS)**(E(T)-M(T)+0.5) higher
                    * (
                        (1.0 - g.stg_loss[g.r, g.v, g.p, g.sl])
                        ** (g.e[g.t] - g.yearval[g.YEoh] + 0.5)
                    ),
                )
            )
            * (
                1.0
                + (
                    (
                        (1.0 - g.stg_loss[g.r, g.v, g.p, g.sl])
                        ** (
                            g.m[g.t]
                            - g.e[g.t]
                            - Min(
                                0.5,
                                Max(0.0, g.m[g.t] + g.d[g.t] / 2.0 - g.e[g.t]),
                            )
                        )
                    )
                    - 1.0
                ).where[g.PrcMap[g.r, "STK", g.p]]
            ),
            # * flow depends on storage in- or outflow in period T
        ) + Sum(
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
