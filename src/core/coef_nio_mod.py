# coef_nio_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_NIO.MOD coefficient calculations for the flow equations I/OCOM on new  *
# *              capacity                                                       *
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *[AL] Corrected bugs in the end of commodity flows in the OCOM case
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Else, For, If, Loop, Number, sparse
from gamspy.math import Max, Min, abs, ceil

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefNioMod(GamsClass):
    """Translation unit for coef_nio.mod."""

    # Instance attributes
    module_name: str = "coef_nio_mod"
    gams_source: str = "coef_nio.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.commodity_flows_tied_to_new_capacity)
        self.tc.enqueue(self.commodity_flows_tied_to_decommissioning_of_capacity)
        self.tc.enqueue(self.modifications)
        self.tc.enqueue(self.allow_using_ncap_cled)

    def commodity_flows_tied_to_new_capacity(self: CoefNioMod) -> None:
        g = self.tc
        r, v, p, c, t = g.r, g.v, g.p, g.c, g.t

        # V0.5b 980828 re-adjust v,t handling to capture enclosed periods & condition to handle period of length 1
        g.RpcCapflo[r, v, p, c].where[~g.Rtp[r, v, p]] = 0
        g.Fil[v] = g.yearval[v] >= g.miyr_v1

        # V05c 980923 - use the capacity flow control set
        with Loop(g.RpcCapflo[r, g.Fil[v], p, c].where[g.ncap_icom[r, v, p, c]]):
            g.dfunc[...] = g.coef_rpti[r, v, p]
            g.my_f[...] = g.ncap_iled[r, v, p]
            g.f[...] = g.coef_iled[r, v, p]
            g.cnt[...] = abs(g.ncap_cled[r, v, p, c])
            g.z[...] = g.b[v] + Max(Number(1).where[g.cnt.where[g.my_f] == 0], g.my_f)
            g.f[...] = g.z - Max(1, Min(g.cnt, g.f))

            with If(g.dfunc > 1):
                # repeated investment
                g.coef_icom[r, t[v], t, p, c] = (
                    g.dfunc * g.ncap_icom[r, v, p, c] / g.fpd[t]
                )
            with Else():  # type: ignore[no-untyped-call]  # noqa: SIM117
                with Loop(t.where[(g.e[t] >= g.f) * (g.b[t] < g.z)]):
                    g.coef_icom[r, v, t, p, c] = (
                        # some part of consumption in T
                        # V0.5 980718 - beginning of commodity flow is NCAP_ILED - NCAP_CLED!
                        Max(
                            0,
                            ((Min(g.z - 1, g.e[t]) - Max(g.f, g.b[t]) + 1) / g.fpd[t]),
                        )
                        * g.ncap_icom[r, v, p, c]
                        / (g.z - g.f)
                    )

    def commodity_flows_tied_to_decommissioning_of_capacity(self: CoefNioMod) -> None:
        g = self.tc
        r, v, p, c, t = g.r, g.v, g.p, g.c, g.t

        with Loop(g.RpcCapflo[r, v, p, c].where[g.ncap_ocom[r, v, p, c]]):
            g.f[...] = g.ncap_iled[r, v, p] + g.ncap_dlag[r, v, p]
            g.my_f[...] = g.ncap_tlife[r, v, p]
            g.z[...] = Max(1, g.ncap_dlife[r, v, p])
            g.dfunc[...] = g.coef_rpti[r, v, p]

            with If(g.dfunc > 1):  # noqa: SIM117
                with For(g.cnt, start=1, end=ceil(g.dfunc)):
                    g.coef_ocom[r, v, t, p, c].where[g.yearval[t] >= g.yearval[v]] = (
                        g.coef_ocom[r, v, t, p, c]
                        + Min(1, g.dfunc - g.cnt + 1)
                        * Max(
                            0,
                            (
                                Min(g.b[v] + g.f + (g.cnt * g.my_f) + g.z, g.e[t] + 1)
                                - Max(g.b[v] + g.f + (g.cnt * g.my_f), g.b[t])
                            )
                            / g.fpd[t],
                        )
                        * (g.ncap_ocom[r, v, p, c] / g.z)
                    )

            with Else():  # type: ignore[no-untyped-call]
                g.coef_ocom[r, v, t, p, c].where[g.yearval[t] >= g.yearval[v]] = (
                    # some part of release in T
                    Max(
                        0,
                        (
                            Min(g.b[v] + g.f + g.my_f + g.z, g.e[t] + 1)
                            - Max(g.b[v] + g.f + g.my_f, g.b[t])
                        )
                        / g.fpd[t],
                    )
                    * (g.ncap_ocom[r, v, p, c] / g.z)
                )

        g.cnt.setRecords(None)

    def modifications(self: CoefNioMod) -> None:
        """
        Modification: Convert negative ICOM to OCOM so that NCAP-related outputs can also be modeled
        Modification: Convert negative OCOM to ICOM so that DECOM-related inputs can also be modeled
        """
        g = self.tc
        r, v, p, c, t = g.r, g.v, g.p, g.c, g.t

        g.coef_ocom[r, v, t, p, c].where[
            ((g.coef_icom[r, v, t, p, c] < 0).where[g.coef_icom[r, v, t, p, c]])
        ] = g.coef_ocom[r, v, t, p, c] - g.coef_icom[r, v, t, p, c]
        g.coef_icom[r, v, t, p, c].where[
            ((g.coef_icom[r, v, t, p, c] < 0).where[g.coef_icom[r, v, t, p, c]])
        ] = 0
        g.coef_icom[r, v, t, p, c].where[
            ((g.coef_ocom[r, v, t, p, c] < 0).where[g.coef_ocom[r, v, t, p, c]])
        ] = g.coef_icom[r, v, t, p, c] - g.coef_ocom[r, v, t, p, c]
        g.coef_ocom[r, v, t, p, c].where[
            ((g.coef_ocom[r, v, t, p, c] < 0).where[g.coef_ocom[r, v, t, p, c]])
        ] = 0

    def allow_using_ncap_cled(self: CoefNioMod) -> None:
        "Allow using NCAP_CLED as NCAP_CLAG, if no NCAP_ICOM"
        g = self.tc
        r, v, p, c, io = g.r, g.v, g.p, g.c, g.io

        g.ncap_clag[g.Rtp, c, io].where[
            (~g.ncap_icom[g.Rtp, c]).where[g.ncap_com[g.Rtp, c, io]]
        ] = sparse(g.ncap_cled[g.Rtp, c])
        g.ncap_cled[r, v, p, c].where[~g.ncap_icom[r, v, p, c]] = 0
