# eqmrkcom_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQMRKCOM Bound on the market share of flow in the production/consumption of commodity
# *   arg1 - mod or v# for the source code to be used
# *   arg2 - equation declaration type
# *   arg3 - bound type for arg1
# *   arg4 - PRD/CON indicator
# *   arg5 - IN/OUT indicator
# *=============================================================================*
# *Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Number, Sum

from core.base_class import GamsClass
from core.cal_cap_mod import CalCapModConfig, cal_cap_mod_GP
from core.cal_fflo_mod import CalFfloModConfig, cal_fflo_mod_GP
from core.cal_ire_mod import CalIreModConfig, cal_ire_mod_GP
from core.cal_red_red import CalRedRedConfig
from core.cal_stgn_mod import CalStgnModConfig, cal_stgn_mod_GP
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqmrkcomIerConfig:
    arg2: Literal["E", "N", "L", "G"]
    arg1: str = ""
    arg3: str = ""
    arg4: str = ""
    arg5: str = ""


class EqmrkcomIer(GamsClass):
    """Translation unit for eqmrkcom.ier."""

    # Instance attributes
    module_name: str = "eqmrkcom_ier"
    gams_source: str = "eqmrkcom.ier"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqmrkcomIerConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        r, t, v, p, prc, c, s, ts = g.r, g.t, g.v, g.p, g.prc, g.c, g.s, g.ts
        Com, ble, opr, j, bd = g.Com, g.Ble, g.Opr, g.j, g.bd

        var = self.env.var
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        varv = self.env.varv_GP
        rcapsub = self.env.rcapsub_GP
        reduce = self.env.reduce
        pgprim = self.env.pgprim
        is_rtp_ffcs_defined = self.tc.defined("RTP_FFCS")
        is_ireauxbal = self.tc.defined("IS_IREAUXBAL")

        eq = g.get_equation(f"EQ{cc.arg2}_MRK{cc.arg4}")
        flo_mrk = g.get_parameter(f"FLO_MRK{cc.arg4}")
        VAR_BLND = g.get_variable(f"{var}_BLND")
        VAR_ELAST = g.get_variable(f"{var}_ELAST")

        # RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')), the annual blending spread
        annual = g.rs_fr[r, s, "ANNUAL"] * (
            1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, "ANNUAL", sow)
        )
        share = flo_mrk[r, t, prc, c, s, cc.arg3]

        if cc.arg4 != "CON":
            # * production of commodity
            # * -----------------------
            terms = (
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
                    opr.where[g.BleOpr[r, c, opr]],
                    annual * g.ble_bal[r, t, c, opr] * VAR_BLND[r, t, c, opr, *sow],
                )
                # *V07_1b emissions due to blending operations
                + Sum(
                    g.BleEnv[r, c, ble, opr],
                    g.rs_fr[r, s, "ANNUAL"]
                    * g.env_bl[r, c, ble, opr, t]
                    * VAR_BLND[r, t, ble, opr, *sow],
                )
                # * inter-regional trade to region
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
                # * storage
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
                # * capacity related commodity flows
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
            )
        else:
            # * consumption of commodity
            # * ------------------------
            terms = (
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
                    # NB: `+ VAR_BLND` rather than `*` is what eqmrkcom.ier does
                    annual * g.bl_inp[r, ble, c] + VAR_BLND[r, t, ble, opr, *sow],
                )
                # * inter-regional trade from region
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
                # * storage
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
                # * include the elasticity variables
                - Sum(
                    g.Rcj[r, c, j, g.Bdneq[bd]].where[g.com_elast[r, t, c, s, bd]],
                    g.bdsig[bd] * VAR_ELAST[r, t, c, s, j, bd, *sow],
                )
            )

        cal_red = self.env.cal_red
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=c,
                arg2=Com,
                arg3=ts,
                arg4=prc,
                arg5=t,
                arg10=Number(1),
                pgprim=pgprim,
                def_rtp_ffcs=is_rtp_ffcs_defined,
                sow=sow,
                var=var,
            ),
        )

        eq[g.Rtp[r, t, prc], c, s, *self.env.swx_GP].where[
            self.env.swtx_GP * g.Top[r, prc, c, cc.arg5] * share
        ] = generate_equation(
            lhs=share * terms,
            type=cc.arg2,
            rhs=Sum(
                g.RtpcsVarf[r, t, prc, c, ts].where[
                    g.Top[r, prc, c, cc.arg5].where[g.RpFlo[r, prc]]
                ],
                Sum(
                    g.RtpVintyr[r, v, t, prc],
                    include_cal_red
                    * g.rs_fr[r, s, ts]
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow)),
                ),
            ),
        )
