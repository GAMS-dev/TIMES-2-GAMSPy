# eqcaflac_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAFLAC - implements commodity-specific capacity utilization equations
# *   arg1 - equation declaration type
# *   arg2 - bound type for arg1
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT/COEF_AF are defined in COEF_CPT.MOD
# *  - shaping of COEF_AF is possible via NCAP_AFX
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Domain, Expression, Number, Product, Set, Sum
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitSet
from gamspy.math import abs, diag, exp

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcaflacVda(GamsClass):
    """Translation unit for eqcaflac.vda."""

    # Instance attributes
    module_name: str = "eqcaflac_vda"
    gams_source: str = "eqcaflac.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal["E", "N", "L", "G"],
        arg4: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        self.comp1(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            sow=self.env.sow_GP,
            rcapsbm=self.env.rcapsbm_GP,
            upscap0=self.env.upscap0_GP,
            varm=self.env.varm_GP,
            sws=self.env.sws_GP,
            var=self.env.var,
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
        )
        if self.arg3 == "$":  # L37: %3 EXIT arg3 could be either [$, *]
            return

        self.comp2(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            rts=self.env.rts_GP(),
            swt=self.env.swt_GP,
            sow=self.env.sow_GP,
            rcapsbm=self.env.rcapsbm_GP,
            upscap0=self.env.upscap0_GP,
            varm=self.env.varm_GP,
            sws=self.env.sws_GP,
            var=self.env.var,
            cal_red=self.env.cal_red,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            sense=self.arg1,
            arg2=self.arg2,
        )

    def comp1(
        self: EqcaflacVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        rcapsbm: Expression | Condition | Number,
        upscap0: Condition,
        varm: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias, ...] | tuple[()],
        var: str,
        arg1: Literal["E", "N", "L", "G"],
        arg2: str,
        arg4: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc

        eq_caflac = g.get_equation(f"{eq}{arg1}_CAFLAC")
        VAR_FLO = g.get_variable(f"{var}_FLO")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        VAR_IRE = g.get_variable(f"{var}_IRE")

        eq_caflac[g.RtpVintyr[*r_v_t, g.p], g.s, *swt].where[
            (g.Afs[g.r, g.t, g.p, g.s, arg2].where[g.RpsCaflac[g.r, g.p, g.s, arg2]])
        ] = generate_equation(
            Sum(
                Domain(g.RpcPg[g.r, g.p, g.c], g.ComTmap[g.r, g.ComType[g.cg], g.c]),
                (1.0 / abs(g.prc_actflo[g.r, g.v, g.p, g.c]))
                / (
                    g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]
                    + Product(
                        g.xpt.where[g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]],
                        g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s],
                    ).where[(~(g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]))]
                )
                * Sum(
                    g.RpcsVar[g.r, g.p, g.c, g.ts].where[g.rs_fr[g.r, g.s, g.ts]],
                    g.rs_fr[g.r, g.s, g.ts]
                    * (
                        VAR_FLO[g.r, g.v, g.t, g.p, g.c, g.ts, *sow].where[
                            g.RpStd[g.r, g.p]
                        ]
                        + (
                            Sum(
                                g.Top[g.RpcStg[g.r, g.p, g.c], g.io].where[
                                    (
                                        g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]
                                        + g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]
                                    )
                                ],
                                (
                                    VAR_SIN[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                                    * Product(
                                        g.RpgAfcx[g.r, g.p, g.c, g.ie].where[
                                            g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]
                                        ],
                                        (
                                            g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]
                                            / g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]
                                        ).where[g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]],
                                    )
                                ).where[g.ips[g.io]]
                                + (
                                    VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                                    * g.stg_eff[g.r, g.v, g.p]
                                    * (
                                        1.0
                                        + macro.rtcs_fr.rtcs_fr_GP(
                                            g.r, g.t, g.c, g.s, g.ts, sow
                                        )
                                    )
                                ).where[(~(g.ips[g.io]))],
                            )
                            + Sum(
                                g.RpcIre[g.r, g.p, g.c, g.ie],
                                VAR_IRE[g.r, g.v, g.t, g.p, g.c, g.ts, g.ie, *sow]
                                * Product(
                                    g.RpgAfcx[g.r, g.p, g.c, g.ie].where[
                                        (
                                            (
                                                (
                                                    g.ncap_afcs[
                                                        g.r, g.v, g.p, g.c, g.s
                                                    ].where[
                                                        g.ncap_afcs[
                                                            g.r, g.v, g.p, g.cg, g.s
                                                        ]
                                                    ]
                                                )
                                                ** 1.0
                                            ).where[g.RpAire[g.r, g.p, g.ie]]
                                        )
                                    ],
                                    (
                                        g.ncap_afcs[g.r, g.v, g.p, g.c, g.s]
                                        / g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]
                                    ).where[g.ncap_afcs[g.r, g.v, g.p, g.cg, g.s]],
                                )
                                + Number(1.0).where[Number(0)],
                            )
                        ).where[(~(g.RpStd[g.r, g.p]))]
                    ),
                ),
            ),
            arg1,
            (
                Sum(
                    g.RvpKmap[g.r, g.v, g.p, g.Modlyear[g.k]],
                    g.coef_vnt[g.r, g.t, g.p, g.k]
                    * macro.coef_af_mx.coef_af_GP(arg4, g.r, g.k, g.t, g.p, g.s, arg2)
                    * (
                        macro.VAR_NCAP_GP(varm, g.r, g.k, g.p, sws).where[g.t[g.k]]
                        + g.ncap_pasti[g.r, g.k, g.p].where[g.pyr[g.k]]
                        + rcapsbm
                    ),
                )
                + macro.coef_af_mx.coef_af_GP(arg4, g.r, g.v, g.t, g.p, g.s, arg2)
                * upscap0
            )
            * g.prc_capact[g.r, g.p]
            * g.g_yrfr[g.r, g.s],
        )

    def comp2(
        self: EqcaflacVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        rts: Set | Alias,
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        rcapsbm: Expression | Condition | Number,
        upscap0: Condition,
        varm: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias, ...] | tuple[()],
        var: str,
        cal_red: str,
        pgprim: str,
        def_rtp_ffcs: bool,
        sense: Literal["L", "E", "N", "G"],
        arg2: str,
    ) -> None:
        g = self.tc

        eql_capflo = g.get_equation(f"{eq}L_CAPFLO")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")

        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red = cal_red_func_GP(
            g,
            CalRedRedConfig(
                var=var,
                sow=sow,
                pgprim=pgprim,
                arg1=g.c,
                arg2=g.Com,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
                def_rtp_ffcs=def_rtp_ffcs,
            ),
        )

        eql_capflo[g.RtpVintyr[*r_v_t, g.p], g.cg, g.sl[g.stl[rts]], *swt].where[
            (g.rs_tslvl[g.r, g.s].where[g.ncap_afc[g.r, g.v, g.p, g.cg, g.stl]])
        ] = generate_equation(
            # * Sum over regular flows
            Sum(
                g.Rpc[g.RpFlo[g.r, g.p], g.c].where[g.ComGmap[g.r, g.cg, g.c]],
                Sum(
                    g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts].where[
                        g.rs_fr[g.r, g.s, g.ts]
                    ],
                    g.rs_fr[g.r, g.s, g.ts]
                    * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.s, g.ts, sow))
                    * include_cal_red,
                ),
            )
            # * storage: for activity multiply by number of storage cycles in a year
            + Sum(
                g.PrcTs[g.RpStg[g.r, g.p], g.ts].where[g.rs_fr[g.r, g.ts, g.s]],
                (
                    VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow]
                    + macro.var_sts.render_GP(g.r, g.v, g.t, g.p, g.ts, arg2)
                )
                * g.rs_fr[g.r, g.ts, g.s]
                * exp(g.prc_sc[g.r, g.p])
                / g.rs_stgprd[g.r, g.ts]
                * g.g_yrfr[g.r, g.s],
            ).where[g.Actcg[g.cg]]
            + Sum(
                g.RpcStg[g.r, g.p, g.c].where[g.ComGmap[g.r, g.cg, g.c]],
                Sum(
                    Domain(
                        g.Top[g.r, g.p, g.c, g.io], g.RpcsVar[g.r, g.p, g.c, g.ts]
                    ).where[g.rs_fr[g.r, g.s, g.ts]],
                    g.rs_fr[g.r, g.s, g.ts]
                    * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.s, g.ts, sow))
                    * (
                        VAR_SIN[g.r, g.v, g.t, g.p, g.c, g.ts, *sow].where[
                            (~(g.Top[g.r, g.p, g.c, "OUT"])) & g.ips[g.io]
                        ]
                        + VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                        * g.stg_eff[g.r, g.v, g.p]
                        * diag(g.io, "OUT")
                    ),
                ),
            ),
            sense,
            (
                (
                    # * process capacity - vintaged or not
                    Sum(
                        g.RvpKmap[g.r, g.v, g.p, g.Modlyear[g.k]],
                        g.coef_vnt[g.r, g.t, g.p, g.k]
                        * (
                            macro.VAR_NCAP_GP(varm, g.r, g.k, g.p, sws).where[g.t[g.k]]
                            + g.ncap_pasti[g.r, g.k, g.p].where[g.pyr[g.k]]
                            + rcapsbm
                        ),
                    )
                    + upscap0
                )
                * g.ncap_afc[g.r, g.v, g.p, g.cg, g.stl]
                # * timeslice fraction of capacity
                * g.prc_capact[g.r, g.p]
                * g.g_yrfr[g.r, g.s]
            ),
        )
