# eqflobnd_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  EQFLOBND limits the flow variable at higher TS-leves
#    %1 - equation declaration type
#    %2 - bound type for %1
#    %3 - qualifier that bound exists
# =============================================================================*
# UR Questions/Comments:
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Sum

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import EquationSenseTypes, generate_equation

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitVariable

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqflobndModConfig:
    """Strongly typed data contract for eqflobnd_mod."""

    sense: EquationSenseTypes
    arg2: Literal["LO", "FX", "UP"]
    arg3: Condition | Number


class EqflobndMod(GamsClass):
    """Translation unit for eqflobnd.mod."""

    # Instance attributes
    module_name: str = "eqflobnd_mod"
    gams_source: str = "eqflobnd.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqflobndModConfig
    ):
        """
        Captures eq, r_t at registration time.
        #    arg1 - equation declaration type
        #    arg2 - bound type for arg1
        #    arg3 - qualifier that bound exists
        """
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        cc = self.config
        g = self.tc

        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func

        sow = self.env.sow_GP

        eq_flobnd = g.get_equation(f"{self.env.eq}{cc.sense}_FLOBND")
        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")

        VAR_IRE_expr: ImplicitVariable | Expression
        if self.env.reduce == "YES":
            VAR_IRE_expr = (
                VAR_IRE[
                    g.r,
                    g.v,
                    g.t,
                    g.p,
                    g.c,
                    g.ts,
                    g.ie,
                    *sow,
                ].where[~g.RpcAire[g.r, g.p, g.c]]
                + (
                    VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow]
                    * g.prc_actflo[g.r, g.v, g.p, g.c]
                ).where[g.RpcAire[g.r, g.p, g.c]]
            )
        else:
            VAR_IRE_expr = VAR_IRE[g.r, g.v, g.t, g.p, g.c, g.ts, g.ie, *sow]

        eq_flobnd[g.RtpVara[*self.env.r_t_GP, g.p], g.cg, g.s, *self.env.swt_GP].where[
            (
                # Make an equation of the bound if there are flow variables for commodities in CG that are strictly below S,
                # ...or the tuple has been otherwise rejected for VAR bound (process is vintaged or IRE, or flow is reduced):
                Sum(
                    g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts].where[
                        (g.TsMap[g.r, g.s, g.ts] * g.ComGmap[g.r, g.cg, g.c])
                    ],
                    (g.RsBelow[g.r, g.s, g.ts])
                    | (g.flo_bnd[g.r, self.env.dflbl, g.p, g.cg, g.s, cc.arg2]),
                ).where[g.flo_bnd[g.r, g.t, g.p, g.cg, g.s, cc.arg2]]
            )
        ] = generate_equation(
            (
                # sum over all flows that are either at S or below it
                Sum(
                    Domain(
                        g.ComGmap[g.r, g.cg, g.c], g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts]
                    ).where[g.TsMap[g.r, g.s, g.ts]],
                    # sum all the existing flows
                    Sum(
                        g.RtpVintyr[g.r, g.v, g.t, g.p],
                        # [UR] model reduction %REDUCE% is set in *.run
                        cal_red_func(
                            g,
                            CalRedRedConfig(
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
                        ).where[g.RpFlo[g.r, g.p]]
                        # [AL] add support for IRE
                        + Sum(
                            g.RpcIre[g.r, g.p, g.c, g.ie],
                            VAR_IRE_expr
                            # apply IRE bound on net flow if group used, otherwise on sum of IMP/EXP
                            * (1.0 - Number(2.0).where[g.xpt[g.ie] & (~g.Com[g.cg])]),
                        ).where[g.RpIre[g.r, g.p]],
                    ),
                )
                - g.flo_bnd[g.r, g.t, g.p, g.cg, g.s, cc.arg2]
            ).where[cc.arg3],
            cc.sense,
            0.0,
        )
