# eqstgflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGFLO limits the flow of storage process at flow TS-level or higher
# *   arg1 - IN/OUT
# *   arg2 - equation declaration type
# *   arg3 - bound type for arg2
# *   arg4 - qualifier that bound exists
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Bound TS restricted to the PRC_TS level or above
# *  - avoid equations if LO=0/UP=INF

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Sum

from core.base_class import GamsClass
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqstgfloModConfig:
    arg1: Literal["IN", "OUT"]
    arg2: Literal["G", "E", "L"]
    arg3: Literal["LO", "FX", "UP"]
    arg4: float


class EqstgfloMod(GamsClass):
    """Translation unit for eqstgflo.mod."""

    # Instance attributes
    module_name: str = "eqstgflo_mod"
    gams_source: str = "eqstgflo.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqstgfloModConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config
        PrcMap, r, p = g.PrcMap, g.r, g.p

        self.env.set_scoped("tmp", "(NOT PRC_MAP(R,'NST',P))+")
        if cc.arg1 == "OUT":
            self.env.set_scoped("tmp", "NOT")

        (
            Rtpc,
            c,
            s,
            RpcsVar,
            ts,
            RtpVintyr,
            v,
            t,
            rs_fr,
            PrcNstts,
            PrcVint,
            RpsPrcts,
            RpcStg,
        ) = (
            g.Rtpc,
            g.c,
            g.s,
            g.RpcsVar,
            g.ts,
            g.RtpVintyr,
            g.v,
            g.t,
            g.rs_fr,
            g.PrcNstts,
            g.PrcVint,
            g.RpsPrcts,
            g.RpcStg,
        )

        sow = self.env.sow_GP
        swt = self.env.swt_GP
        r_t = self.env.r_t_GP

        VAR_S = g.get_variable(f"{self.env.var}_S{cc.arg1}")
        stginout_bnd = g.get_parameter(f"STG{cc.arg1}_BND")

        multiplier = (
            ~PrcNstts[r, p, ts]
            if cc.arg1 == "OUT"
            else ~PrcMap[r, "NST", p] + PrcNstts[r, p, ts]
        )

        eq_stg = g.get_equation(f"{self.env.eq}{cc.arg2}_STG{cc.arg1}")

        eq_stg[Rtpc[*r_t, p, c], s, *swt].where[
            (stginout_bnd[r, t, p, c, s, cc.arg3] != cc.arg4).where[
                PrcVint[r, p] + (~RpcsVar[r, p, c, s])
                & RpsPrcts[r, p, s]
                & RpcStg[r, p, c]
                & stginout_bnd[r, t, p, c, s, cc.arg3]
            ]
        ] = generate_equation(
            Sum(  # sum over all possible flow variables at process TS-level
                RpcsVar[r, p, c, ts].where[rs_fr[r, s, ts] * multiplier],
                Sum(RtpVintyr[r, v, t, p], VAR_S[r, v, t, p, c, ts, *sow])
                * rs_fr[r, s, ts]
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow)),
            ),
            cc.arg2,
            stginout_bnd[r, t, p, c, s, cc.arg3],
        )
