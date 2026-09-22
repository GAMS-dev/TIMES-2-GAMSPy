# eqfloshr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQIN/OUTSHR is the market/product share limit constraint
# *   %1 - equation declaration type
# *   %2 - FLO_SHAR type for %1
# *   %3 - IN/OUT indicator
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Needs to be adjusted to handle attribute TS-level diff. the operation level
# *    - for now FLO_SHAR moved down to S1 level in PP_MAIN (which may be OK)
# *  - [AL] Changed level of equation to be that of RPCS_VAR; RP_STD control added
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, Number, Sum

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import EquationSenseTypes, generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqfloshrModConfig:
    sense: EquationSenseTypes
    arg2: str
    arg3: str


class EqfloshrMod(GamsClass):
    """Translation unit for eqfloshr.mod."""

    # Instance attributes
    module_name: str = "eqfloshr_mod"
    gams_source: str = "eqfloshr.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqfloshrModConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        cc = self.config
        g = self.tc
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif self.env.cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {self.env.cal_red}")

        include_cal_red1: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                var=self.env.var,
                sow=self.env.sow_GP,
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                arg1=g.Com,
                arg2=g.com1,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
            ),
        )

        include_cal_red2: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                var=self.env.var,
                sow=self.env.sow_GP,
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                arg1=g.c,
                arg2=g.Com,
                arg3=g.s,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
            ),
        )
        eq_shr = g.get_equation(f"{self.env.eq}{cc.sense}_{cc.arg3}SHR")
        VAR_FLO = g.get_variable(f"{self.env.var}_FLO")

        sow = self.env.sow_GP

        eq_shr[
            g.RtpVintyr[*self.env.r_v_t_GP, g.p], g.c, g.cg, g.s, *self.env.swt_GP
        ].where[
            (
                (
                    g.RpStd[g.r, g.p]
                    * g.Top[g.r, g.p, g.c, cc.arg3]
                    * g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s]
                ).where[g.flo_shar[g.r, g.v, g.p, g.c, g.cg, g.s, cc.arg2]]
            )
        ] = generate_equation(
            # * all flows in the group
            g.flo_shar[g.r, g.v, g.p, g.c, g.cg, g.s, cc.arg2]
            * (
                # *V0.5a 980729 - RPCS_VAR: com not c
                # * [AL] Handle reduced/non-reduced groups separately
                Sum(
                    Domain(
                        g.Top[g.r, g.p, g.Com, cc.arg3],
                        g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                    ).where[g.ComGmap[g.r, g.cg, g.Com]],
                    VAR_FLO[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow]
                    * g.rs_fr[g.r, g.s, g.ts]
                    * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow)),
                ).where[(~(g.RpgRed[g.r, g.p, g.cg, cc.arg3]))]
                + Sum(
                    Domain(
                        g.Top[g.r, g.p, g.Com, cc.arg3],
                        g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                    ).where[g.ComGmap[g.r, g.cg, g.Com]],
                    include_cal_red1
                    # * share-ts coarser than variable or share finer than variable
                    * g.rs_fr[g.r, g.s, g.ts]
                    * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow)),
                ).where[g.RpgRed[g.r, g.p, g.cg, cc.arg3]]
            ).where[(g.flo_shar[g.r, g.v, g.p, g.c, g.cg, g.s, cc.arg2] > 0.0)],
            cc.sense,
            # * commodity working on, summed for all
            (
                VAR_FLO[g.r, g.v, g.t, g.p, g.c, g.s, *sow].where[
                    (~(g.RpgRed[g.r, g.p, g.cg, cc.arg3]))
                ]
                + (include_cal_red2).where[g.RpgRed[g.r, g.p, g.cg, cc.arg3]]  # type: ignore
            ),
        )
