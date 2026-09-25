# eqflomrk_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================================================*
# * EQx_FLMRK is a market share constraint for a commodity flow of a process
# *   arg1 - equation declaration type
# *   arg2 - BOUND type for arg1
# *==================================================================================================*
# * Comments:
# *---------------------------------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Loop, Number, Ord, Product, Set, SpecialValues, Sum, sparse
from gamspy.math import power, project, same_as

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqflomrkMod(GamsClass):
    """Translation unit for eqflomrk.mod."""

    # Instance attributes
    module_name: str = "eqflomrk_mod"
    gams_source: str = "eqflomrk.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        # arg1 can only be empty if arg2 is empty
        arg1: Literal["E", "N", "L", "G", ""] = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc
        if self.arg2 == "":
            self.comp1()
            self.tc.enqueue(self.exec1)
        else:  # EQUDEF
            # Inter-regional exchange directionality assignment parameter tracking
            # first part in .where, second part addition
            ired: tuple[Expression | Number, Expression | Number] = (
                Number(1),
                Number(0),
            )
            VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
            if self.env.reduce == "YES":
                ired = (
                    ~g.RpcAire[g.r, g.p, g.c],
                    (
                        VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *self.env.sow_GP]
                        * g.prc_actflo[g.r, g.v, g.p, g.c].where[
                            g.RpcAire[g.r, g.p, g.c]
                        ]
                    ),
                )
            # * For IRE/STG: Output flow from process if PRC_MARK >= 0, Input flow if PRC_MARK <= 0
            # Output tracking switch handling environmental constraint emissions parameters.
            sigo = g.prc_mark[g.r, g.t, g.p, g.item, g.Com, self.arg2] >= 0.0
            # Input tracking switch handling environmental constraint emissions parameters.
            sigi = g.prc_mark[g.r, g.t, g.p, g.item, g.Com, self.arg2] <= 0.0

            if self.arg1 == "":
                raise ValueError("arg1 cannot be empty if arg2 is not empty.")

            self.equation_def(
                arg1=self.arg1,
                arg2=self.arg2,
                eq=self.env.eq,
                r_t=self.env.r_t_GP,
                swt=self.env.swt_GP,
                var=self.env.var,
                sow=self.env.sow_GP,
                ired=ired,
                sigo=sigo,
                sigi=sigi,
                cal_red=self.env.cal_red,
            )

    def comp1(self: EqflomrkMod) -> None:
        g = self.tc
        m = g.container
        r, t, c, s, p = g.r, g.t, g.c, g.s, g.p
        g.RtxMark = Set(m, name="RTX_MARK", domain=[r, t, g.item, c, g.bd, s])
        g.RxMark = Set(m, name="RX_MARK", domain=[r, g.year, g.item, c, g.bd])
        g.RtpMrk = Set(m, name="RTP_MRK", domain=[g.Reg, t, p, g.item, g.Com, g.bd])
        g.RtxMrk = Set(m, name="RTX_MRK", domain=[g.Reg, t, g.item, g.Com, g.bd])
        g.Rmkc = Set(m, name="RMKC", domain=[g.Reg, g.item, g.Com])

    def equation_def(
        self: EqflomrkMod,
        arg1: Literal["E", "N", "L", "G"],
        arg2: str,
        eq: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        ired: tuple[Expression | Number, Expression | Number],
        sigo: Expression,
        sigi: Expression,
        cal_red: str,
    ) -> None:
        g = self.tc
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=g.c,
                arg2=g.com1,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                arg10=Number(1),
                var=var,
                sow=sow,
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            ),
        )
        eq_flomrk = g.get_equation(f"{eq}{arg1}_FLOMRK")
        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")

        ired_condition, ired_addition = ired

        eq_flomrk[*r_t, g.item, g.Com, g.s, *swt].where[
            g.RtxMark[g.r, g.t, g.item, g.Com, arg2, g.s]
            # * Sum over all processes with PRC_MARK(COM) (not just capacity-related)
        ] = generate_equation(
            Sum(
                Domain(g.ComGmap[g.r, g.Com, g.c], g.Rpc[g.r, g.p, g.c]).where[
                    g.prc_mark[g.r, g.t, g.p, g.item, g.Com, arg2]
                ],
                power(
                    g.prc_mark[g.r, g.t, g.p, g.item, g.Com, arg2],
                    Number(1.0).where[g.RxMark[g.r, "0", g.item, g.Com, arg2]] - 1.0,
                )
                # * Sum over all COMPRD balance variables related to timeslice S
                * Sum(
                    g.RhsComprd[g.r, g.t, g.c, g.sl].where[g.rs_fr[g.r, g.s, g.sl]],
                    (
                        # * Sum over all flow variables related to balance timeslice
                        Sum(
                            g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts].where[
                                g.rs_fr[g.r, g.sl, g.ts]
                            ],
                            Sum(g.RtpVntbyr[g.r, g.t, g.p, g.v], include_cal_red)
                            # * Balance coarser than variable or balance finer than variable
                            * g.rs_fr[g.r, g.sl, g.ts]
                            * (
                                1.0
                                + macro.rtcs_fr.rtcs_fr_GP(
                                    g.r, g.t, g.c, g.sl, g.ts, sow
                                )
                            ),
                        )
                        * (
                            1.0
                            + (g.com_ie[g.r, g.t, g.c, g.sl] - 1.0).where[
                                g.Top[g.r, g.p, g.c, "OUT"]
                            ]
                        )
                    ).where[g.RpStd[g.r, g.p]]
                    # * Inter-regional trade contribution
                    + Sum(
                        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts].where[
                            g.rs_fr[g.r, g.sl, g.ts]
                        ],
                        Sum(
                            g.RtpVntbyr[g.r, g.t, g.p, g.v],
                            (
                                (
                                    VAR_IRE[
                                        g.r, g.v, g.t, g.p, g.c, g.ts, "IMP", *sow
                                    ].where[ired_condition]
                                    + ired_addition
                                )
                                * (
                                    1.0
                                    + g.ire_flosum[
                                        g.r, g.t, g.p, g.c, g.s, "IMP", g.c, "OUT"
                                    ]
                                )
                                * g.com_ie[g.r, g.t, g.c, g.sl]
                            ).where[(sigo.where[g.RpcIre[g.r, g.p, g.c, "IMP"]])]
                            - (
                                (
                                    VAR_IRE[
                                        g.r, g.v, g.t, g.p, g.c, g.ts, "EXP", *sow
                                    ].where[ired_condition]
                                    + ired_addition
                                )
                                * (
                                    1.0
                                    + g.ire_flosum[
                                        g.r, g.t, g.p, g.c, g.s, "EXP", g.c, "IN"
                                    ]
                                )
                            ).where[(sigi.where[g.RpcIre[g.r, g.p, g.c, "EXP"]])],
                        )
                        # * Balance coarser than variable or balance finer than variable
                        * g.rs_fr[g.r, g.sl, g.ts]
                        * (
                            1.0
                            + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.sl, g.ts, sow)
                        ),
                    ).where[g.RpIre[g.r, g.p]]
                    # * Storage contribution
                    + Sum(
                        g.RpcsVar[g.RpcStg[g.r, g.p, g.c], g.ts].where[
                            g.rs_fr[g.r, g.sl, g.ts]
                        ],
                        Sum(
                            g.RtpVntbyr[g.r, g.t, g.p, g.v],
                            (
                                (
                                    VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                                    * g.stg_eff[g.r, g.v, g.p]
                                    * g.com_ie[g.r, g.t, g.c, g.sl]
                                ).where[sigo]
                                - VAR_SIN[g.r, g.v, g.t, g.p, g.c, g.ts, *sow].where[
                                    sigi
                                ]
                            ),
                        )
                        # * Balance coarser than variable or balance finer than variable
                        * g.rs_fr[g.r, g.sl, g.ts]
                        * (
                            1.0
                            + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.sl, g.ts, sow)
                        ),
                    ).where[g.PrcMap[g.r, "STG", g.p]],
                ),
            ),
            arg1,
            # * Reference is the COMPRD variable
            Sum(
                Domain(
                    g.ComGmap[g.r, g.Com, g.c], g.RhsComprd[g.r, g.t, g.c, g.sl]
                ).where[g.rs_fr[g.r, g.s, g.sl]],
                VAR_COMPRD[g.r, g.t, g.c, g.sl, *sow],
            )
            * Product(
                g.RxMark[g.r, g.ll, g.p[g.item], g.Com, arg2],
                g.prc_mark[g.r, g.t, g.p, g.p, g.Com, arg2].where[g.Lastll[g.ll]],
            ),
        )

    def exec1(self: EqflomrkMod) -> None:
        g = self.tc
        # * Remove superfluous data points
        g.prc_mark[g.r, g.ll, g.p, g.item, g.c, g.Bdneq].where[
            g.prc_mark[g.r, g.ll, g.p, g.item, g.c, "FX"]
        ] = False
        g.prc_mark[g.r, g.ll, g.p, g.item, g.c, g.bd].where[
            (
                (~(g.RtpVara[g.r, g.ll, g.p])).where[
                    (~(same_as(g.p, g.item)))  # type: ignore
                    & g.prc_mark[g.r, g.ll, g.p, g.item, g.c, g.bd]
                ]
            )
        ] = False
        # * Partitioning flags by type
        with Loop(g.t):
            g.RxMark[g.r, "0", g.p, g.c, g.bd].where[
                (
                    (
                        g.prc_mark[g.r, g.t, g.p, g.p, g.c, g.bd].where[
                            g.RpStd[g.r, g.p]
                        ]
                        >= 0.0
                    ).where[g.prc_mark[g.r, g.t, g.p, g.p, g.c, g.bd]]
                )
            ] = True
        g.RxMark[g.r, g.t.lag(Ord(g.t), "circular"), g.p, g.c, g.bd] = sparse(
            g.prc_mark[g.r, g.t, g.p, g.p, g.c, g.bd].where[
                (~(g.RxMark[g.r, "0", g.p, g.c, g.bd]))
            ]
        )
        # * Eliminate zero values; For standard processes set flow bound
        g.RtpMrk[g.RtpVara[g.r, g.t, g.p], g.item, g.c, g.bd].where[
            (
                (g.prc_mark[g.r, g.t, g.p, g.item, g.c, g.bd] == 0.0).where[
                    g.prc_mark[g.r, g.t, g.p, g.item, g.c, g.bd]
                ]
            )
        ] = True
        g.RtpMrk[g.RtpVara[g.r, g.t, g.p], g.prc, g.c, g.bd].where[
            (
                g.prc_mark[g.r, g.t, g.prc, g.prc, g.c, g.bd].where[
                    g.RxMark[g.r, "0", g.prc, g.c, g.bd]
                ]
            )
        ] = False
        with Loop(
            g.RtpMrk[g.r, g.t, g.p, g.item, g.c, g.Bdupx[g.bd]].where[g.RpStd[g.r, g.p]]
        ):
            g.flo_bnd[g.r, g.t, g.p, g.c, g.Annual, g.bd] = SpecialValues.EPS
        g.prc_mark[g.RtpMrk] = 0.0
        # * Make sure that data for all PRC in group are forward extrapolated
        g.Rxx.setRecords(None)
        g.Yk1.setRecords(None)
        g.RtpMrk.setRecords(None)
        g.RtpMrk[g.RtpVara[g.r, g.t, g.p], g.item, g.c, g.bd].where[
            g.prc_mark[g.r, g.t, g.p, g.item, g.c, g.bd]
        ] = True
        g.Yk1[g.t, g.tt[g.t + 1]] = True
        with Loop(g.Yk1[g.tt, g.t]):
            g.prc_mark[g.RtpVara[g.r, g.t, g.p], g.item, g.c, g.bd].where[
                (~(g.prc_mark[g.r, g.t, g.p, g.item, g.c, g.bd]))
            ] = sparse(g.prc_mark[g.r, g.tt, g.p, g.item, g.c, g.bd])
        project(source=g.RtpMrk, target=g.RtxMrk, direction="left")
        project(source=g.RtxMrk, target=g.Rmkc, direction="left")
        project(source=g.Rmkc, target=g.Fin, direction="left")
        g.prc_mark[g.r, g.t, g.p, g.item, g.c, g.bd].where[
            (~(g.RtxMrk[g.r, g.t, g.item, g.c, g.bd]))
        ] = 0.0
        # * Add ANNUAL level for PRC_MARK group commodities not in TOP
        g.Fin[g.Rc] = False
        g.ComTsl[g.Fin, "ANNUAL"].where[(~(Sum(g.ComTsl[g.Fin, g.tsl], 1.0)))] = True
        # * Prepare the COMPRD variables for all PRC_MARK parameters:
        with Loop(g.Rmkc[g.r, g.item, g.c]):
            g.Trackc[g.Rc[g.r, g.Com]].where[g.ComGmap[g.r, g.c, g.Com]] = True
        g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[g.Trackc[g.r, g.c]] = True
        g.Rxx[g.Rmkc] = True
        g.Trackc.setRecords(None)
        g.Rmkc.setRecords(None)
        # * If ITEM is also P (ala FLO_MARK), or C is not in TOP, use commodity timeslices; else use ANNUAL
        g.Rmkc[g.Rxx[g.Rpc]] = True
        g.Rmkc[g.Rxx[g.r, g.item, g.c]] = sparse(g.Fin[g.r, g.c])
        g.Rmkc[g.r, g.item, g.c].where[g.ComTsl[g.r, g.c, "ANNUAL"]] = False
        project(source=g.Rmkc, target=g.Fin, direction="left")
        with Loop(g.ComTsl[g.Fin[g.r, g.c], g.tsl]):
            g.RtxMark[g.RtxMrk[g.r, g.t, g.item, g.c, g.bd], g.s].where[
                (g.Rmkc[g.r, g.item, g.c].where[g.TsGroup[g.r, g.tsl, g.s]])
            ] = True
        g.RtxMark[g.RtxMrk[g.r, g.t, g.item, g.c, g.bd], g.Annual].where[
            (~(g.Rmkc[g.r, g.item, g.c]))
        ] = True
        g.Rmkc[g.Rxx[g.r, g.item, g.c]] = True
        g.Fin.setRecords(None)
        g.RtxMrk.setRecords(None)
        g.RtpMrk.setRecords(None)
