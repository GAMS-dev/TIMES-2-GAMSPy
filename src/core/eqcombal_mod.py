# eqcombal_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCOMBAL is the basic commodity balance and the production limit constraint
# *   arg1 - mod or v# for the source code to be used
# *   arg2 - equation declaration type
# *   arg3 - COM_LIM type for arg2
# *   arg4 - BAL/PRD indicator
# *   arg5 - condition for PRD
# *=============================================================================*
# *GaG Questions/Comments:
# *   - need more control over VAR_COMX so only generate when really OK (=>either COMX_BND/PRICE/UC required)
# *   - apply RS_FR/RTCS_FR whenever process has a COM_TS commodity but the variable is not at that level

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Number, Product, Sum

from core.base_class import GamsClass
from core.cal_cap_mod import CalCapModConfig, cal_cap_mod_GP
from core.cal_fflo_mod import CalFfloModConfig, cal_fflo_mod_GP
from core.cal_ire_mod import CalIreModConfig, cal_ire_mod_GP
from core.cal_stgn_mod import CalStgnModConfig, cal_stgn_mod_GP
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Equation, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcombalMod(GamsClass):
    """Translation unit for eqcombal.mod."""

    # Instance attributes
    module_name: str = "eqcombal_mod"
    gams_source: str = "eqcombal.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg2: Literal["E", "N", "L", "G"],
        arg5: ImplicitSet | Number,  # default Number(1)
        # arg1 is always "mod"
        arg1: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.compile()

    def compile(self) -> None:
        g = self.tc

        sws_local: Product | Number = Number(1)
        if self.arg4 == "BAL" and self.env.stages.upper() == "YES":
            sws_local = Product(
                g.SwMap[g.t, g.Sow, g.j, g.ww].where[
                    g.s_com_proj[g.r, g.t, g.c, g.j, g.ww]
                ],
                g.s_com_proj[g.r, g.t, g.c, g.j, g.ww],
            )

        self.define_equation(
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            eq=self.env.eq,
            r_t=self.env.r_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            sws_local=sws_local,
            condition1=self.arg4 == "BAL",
            condition2=self.arg4 == "PRD",
            condition3=self.env.timesed == "YES",
            condition4=f"{self.arg4}{self.arg3}" == "BALFX",
        )

    def define_equation(
        self: EqcombalMod,
        arg2: Literal["E", "N", "L", "G"],
        arg3: str,
        arg4: str,
        arg5: Condition | Expression | ImplicitSet | Number,
        eq: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        sws_local: Product | Number,
        condition1: bool,
        condition2: bool,
        condition3: bool,
        condition4: bool,
    ) -> None:
        g = self.tc
        r, v, t, p, c, s, ts = g.r, g.v, g.t, g.p, g.c, g.s, g.ts
        Com, ble, opr, j, bd = g.Com, g.Ble, g.Opr, g.j, g.bd

        eq_combal: Equation = g.get_equation(f"{eq}{arg2}_COM{arg4}")
        RcsCom: Set = g.get_set(f"RCS_COM{arg4}")
        varv = self.env.varv_GP
        sws = self.env.sws_GP
        rcapsub = self.env.rcapsub_GP
        reduce = self.env.reduce
        pgprim = self.env.pgprim
        is_rtp_ffcs_defined = self.tc.defined("RTP_FFCS")
        is_ireauxbal = self.env.is_set("ireauxbal")
        VAR_BLND = g.get_variable(f"{var}_BLND")
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
        VAR_DEM = g.get_variable(f"{var}_DEM")
        VAR_ELAST = g.get_variable(f"{var}_ELAST")

        # RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')), the annual blending spread
        annual = g.rs_fr[r, s, "ANNUAL"] * (
            1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, "ANNUAL", sow)
        )
        # * include the elasticity variables
        elast = Sum(
            g.Rcj[r, c, j, g.Bdneq[bd]].where[g.com_elast[r, t, c, s, bd]],
            g.bdsig[bd] * VAR_ELAST[r, t, c, s, j, bd, *sow],
        )

        # *
        # * production
        # *
        production: Expression | ImplicitSet = (
            # * individual flows
            cal_fflo_mod_GP(
                g=g,
                config=CalFfloModConfig(
                    reduce=reduce,
                    sow=sow,
                    var=var,
                    pgprim=pgprim,
                    is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                    arg1="OUT",
                    arg3=Number(1),
                    arg4=Number(1),
                ),
            )
            # *V07_1b blending flows
            + Sum(
                g.BleOpr[r, c, opr],
                annual * g.ble_bal[r, t, c, opr] * VAR_BLND[r, t, c, opr, *sow],
            )
            # *V07_1b emissions due to blending operations
            + Sum(
                g.BleEnv[r, c, ble, opr],
                g.rs_fr[r, s, "ANNUAL"]
                * g.env_bl[r, c, ble, opr, t]
                * VAR_BLND[r, t, ble, opr, *sow],
            )
            # *   inter-regional trade to region
            # *V0.9 022100 - exports could also produce aux
            + cal_ire_mod_GP(
                g=g,
                config=CalIreModConfig(
                    var=var,
                    sow=sow,
                    is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                    is_ireauxbal=is_ireauxbal,
                    arg1="IMP",
                    arg2="OUT",
                    arg3=g.ie,
                    arg4=Number(1),
                ),
            )
            # *   storage
            + cal_stgn_mod_GP(
                g=g,
                config=CalStgnModConfig(
                    var=var,
                    sow=sow,
                    arg1="OUT",
                    arg2="IN",
                    arg3=g.stg_eff[r, v, p],
                    arg4=Number(1),
                    arg5=~g.PrcNstts[r, p, ts],
                    arg6=Number(1),
                ),
            )
            # * (+25-May-2005) Add commodity aggregation to production side
            + Sum(
                Com.where[g.com_agg[r, t, Com, c]],
                g.com_agg[r, t, Com, c]
                * Sum(
                    g.RtcsVarc[r, t, Com, ts].where[g.RsTree[r, s, ts]],
                    g.rs_fr[r, s, ts]
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, Com, s, ts, sow))
                    * (
                        VAR_COMNET[r, t, Com, ts, *sow].where[g.RcAgp[r, Com, "LO"]]
                        + VAR_COMPRD[r, t, Com, ts, *sow].where[g.RcAgp[r, Com, "FX"]]
                    ),
                ),
            )
            # * capacity related commodity flows
            # * fixed commodity associated with installed capacity or retirement
            + cal_cap_mod_GP(
                g=g,
                config=CalCapModConfig(
                    varv=varv,
                    sws=sws,
                    rcapsub=rcapsub,
                    arg1="OUT",
                    arg2="O",
                    arg3=Number(1),
                ),
            )
            # * apply commodity infastructure efficiency
        ) * g.com_ie[r, t, c, s]

        # * If production is summed into variable, use it directly
        if condition1:
            production = (
                production.where[~g.RhsComprd[r, t, c, s]]
                + VAR_COMPRD[r, t, c, s, *sow].where[g.RhsComprd[r, t, c, s]]
            )

        lhs: Expression | ImplicitSet = production
        # *
        # * consumption
        # *
        # * when doing FLO then need NET otherwise only want production component
        if not condition2:
            # * include the elasticity variables (moved to consumption side)
            if condition3:
                lhs = lhs + elast
            lhs = lhs - (
                # * individual flows
                cal_fflo_mod_GP(
                    g=g,
                    config=CalFfloModConfig(
                        reduce=reduce,
                        sow=sow,
                        var=var,
                        pgprim=pgprim,
                        is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                        arg1="IN",
                        arg3=Number(1),
                        arg4=Number(1),
                    ),
                )
                # *V07_1a blending flows
                + Sum(
                    g.BleTp[r, t, ble].where[g.BleOpr[r, ble, c]],
                    annual * VAR_BLND[r, t, ble, c, *sow],
                )
                + Sum(
                    g.BleOpr[r, ble, opr].where[
                        g.BleInp[r, ble, c] * g.BleTp[r, t, ble]
                    ],
                    annual * g.bl_inp[r, ble, c] * VAR_BLND[r, t, ble, opr, *sow],
                )
                # *   inter-regional trade from region
                # *V0.9 022100 - imports could also require aux
                + cal_ire_mod_GP(
                    g=g,
                    config=CalIreModConfig(
                        var=var,
                        sow=sow,
                        is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                        is_ireauxbal=is_ireauxbal,
                        arg1="EXP",
                        arg2="IN",
                        arg3=g.ie,
                        arg4=Number(1),
                    ),
                )
                # *   storage
                + cal_stgn_mod_GP(
                    g=g,
                    config=CalStgnModConfig(
                        var=var,
                        sow=sow,
                        arg1="IN",
                        arg2="OUT",
                        arg3=Number(1),
                        arg4=g.stg_eff[r, v, p],
                        arg5=~g.PrcMap[r, "NST", p] + g.PrcNstts[r, p, ts],
                        arg6=Number(1),
                    ),
                )
                # * capacity related commodity flows
                # * fixed commodity associated with installed capacity or investment
                + cal_cap_mod_GP(
                    g=g,
                    config=CalCapModConfig(
                        varv=varv,
                        sws=sws,
                        rcapsub=rcapsub,
                        arg1="IN",
                        arg2="I",
                        arg3=Number(1),
                    ),
                )
            )

        if not condition1:
            # *    production bound/cost/tax/sub/cum
            rhs: Condition | Expression | ImplicitSet | int = VAR_COMPRD[
                r, t, c, s, *sow
            ].where[g.RhsComprd[r, t, c, s]]
            if condition3:
                # DDF_PREF / MI_AGC come with the elastic demand extension
                ddf_pref = g.ddf_pref
                mi_agc = g.mi_agc
                rhs = (
                    rhs
                    + (
                        Sum(
                            g.Rcj[r, Com, j, bd].where[g.MiDmas[r, c, Com]],
                            (
                                ddf_pref[r, t, Com] * (mi_agc[r, t, c, Com, j, bd] - 1)
                                + g.rd_shar[r, t, Com, c]
                            )
                            * g.bdsig[bd]
                            * Sum(
                                g.RtcsVarc[r, t, Com, ts],
                                VAR_ELAST[r, t, Com, ts, j, bd, *sow],
                            ),
                        )
                        - VAR_COMPRD[r, t, c, s, *sow]
                    ).where[(g.com_elast[r, t, c, s, "N"] > 0).where[g.RdAgg[r, c]]]
                )
        else:
            # *    set the RHS according to the type of equation and/or commodity
            # *    net bound/cost/tax/sub/cum
            rhs = 0
            if condition4:
                rhs = VAR_COMNET[r, t, c, s, *sow].where[g.RhsCombal[r, t, c, s]]
            # *    demand projection
            projection: Condition | Expression = g.com_proj[r, t, c].where[
                ~g.rd_nlp[r, c]
            ]

            rhs = (
                rhs
                + (
                    (
                        sws_local * projection
                        + VAR_DEM[r, t, c, *sow].where[g.rd_nlp[r, c]]
                        + Sum(
                            g.MiDmas[g.RdAgg[r, Com], c],
                            g.rd_shar[r, t, Com, c]
                            * VAR_COMPRD[r, t, Com, "ANNUAL", *sow],
                        )
                    )
                    * macro.com_fr.com_fr_GP(self.env.mx_GP, r, t, c, s)
                ).where[g.Dem[r, c]]
            )

        eq_combal[*r_t, c, s, *swt].where[RcsCom[r, t, c, s, arg3] * arg5] = (
            generate_equation(
                lhs=lhs,
                type=arg2,
                rhs=rhs,
            )
        )
