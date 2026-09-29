# eqflofr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQFLOFR relationship between total flow and the flow in a specific timeslice
# *   %1 - equation declaration type
# *   %2 - LIM type of FLO_FR
# *=============================================================================*
# * Questions/Comments:
# *  - FLO_FR must be specified on TS-level of the flow or above; value below will be ignored
# *  - fraction of flows under parent timelice supported by a parent N (or negative) FLO_FR

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, SpecialValues, Sum
from gamspy.math import Min, abs

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import generate_equation

if TYPE_CHECKING:
    from gamspy import Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqflofrModConfig:
    arg1: Literal["L", "E", "G"]
    arg2: Literal["LO", "UP"] | Set


class EqflofrMod(GamsClass):
    """Translation unit for eqflofr.mod."""

    # Instance attributes
    module_name: str = "eqflofr_mod"
    gams_source: str = "eqflofr.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqflofrModConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.sense = config.arg1
        self.arg2 = config.arg2
        self.compile()

    def compile(self) -> None:
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        else:
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP

        g = self.tc
        sow = self.env.sow_GP
        flo_fr, lA, Rtpc = g.flo_fr, g.lA, g.Rtpc

        VAR_FLO = g.get_variable(name=f"{self.env.var}_FLO")
        cal_red_result = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                var=self.env.var,
                sow=sow,
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                arg1=g.c,
                arg2=g.Com,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
            ),
        )

        eq_flofr = g.get_equation(name=f"{self.env.eq}{self.sense}_FLOFR")
        eq_flofr[
            Rtpc[*self.env.r_t_GP, g.p, g.c], g.s, lA[self.arg2], *self.env.swt_GP
        ].where[
            (
                Sum(
                    g.RpcsVar[g.RpFlo[g.r, g.p], g.c, g.ts].where[
                        g.TsMap[g.r, g.s, g.ts]
                    ],
                    1.0,
                ).where[flo_fr[g.r, g.t, g.p, g.c, g.s, lA]]
            )
        ] = generate_equation(
            Sum(
                g.RtpVintyr[g.r, g.v, g.t, g.p],
                VAR_FLO[g.r, g.v, g.t, g.p, g.c, g.s, *sow].where[g.ips[lA]]
                + Sum(
                    g.RsBelow1[g.r, g.sl, g.s],
                    Sum(
                        g.TsAnn[g.sl, g.ts],
                        VAR_FLO[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                        * (flo_fr[Rtpc, g.ts, "N"] > 0.0),
                    ).where[flo_fr[Rtpc, g.sl, "N"]]
                    + Sum(
                        g.RtpcsVarf[Rtpc, g.ts].where[
                            (
                                flo_fr[Rtpc, g.s, lA]
                                > -Number(SpecialValues.POSINF).where[
                                    g.rs_fr[g.r, g.sl, g.ts]
                                ]
                            )
                        ],
                        cal_red_result,
                    ).where[(~(flo_fr[Rtpc, g.sl, "N"]))],
                ).where[g.bd[lA]],
            )
            * abs(flo_fr[Rtpc, g.s, lA]),
            self.sense,
            Sum(
                Domain(g.RtpVintyr[g.r, g.v, g.t, g.p], g.RtpcsVarf[Rtpc, g.ts]).where[
                    (g.stoa[g.ts].where[g.TsMap[g.r, g.s, g.ts]])
                ],
                cal_red_result,
            ).where[((~(Min(0.0, flo_fr[Rtpc, g.s, lA]))) | (g.bd[lA]))],
        )
