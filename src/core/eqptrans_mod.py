# eqptrans_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQPTRANS is the flow-to-flow transformation constraint
# *=============================================================================*
# * Questions/Comments:
# *  - EQ_PTRANS is dropped if substition for FLO_FUNC activated
# *  - EQ level according to RPS_S1, VAR_FLOs according RPCS_VAR
# *  - COEF_PTRAN created in coef_ptr.mod

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Number, Sum

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqptransMod(GamsClass):
    """Translation unit for eqptrans.mod."""

    # Instance attributes
    module_name: str = "eqptrans_mod"
    gams_source: str = "eqptrans.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        r, v, t, p, c, s, ts = g.r, g.v, g.t, g.p, g.c, g.s, g.ts
        Com, comgrp, cg = g.Com, g.comgrp, g.cg
        RsTree, RtpcsVarf, coef_ptran, rs_fr = (
            g.RsTree,
            g.RtpcsVarf,
            g.coef_ptran,
            g.rs_fr,
        )

        cal_red = self.env.cal_red
        r_v_t = self.env.r_v_t_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP
        def_rtp_ffcs = self.tc.defined("RTP_FFCS")

        self.env.set_scoped("shg", (p, comgrp, cg))
        base_shp1 = 1 + g.rtp_ffcx[r, v, t, *self.env.shg].where[g.PrcVint[r, p]]

        if def_rtp_ffcs:
            self.env.set_scoped(
                "shp1",
                base_shp1 * (1 + g.rtp_ffcs[r, v, *self.env.shg, *sow]),
            )
        else:
            self.env.set_scoped("shp1", base_shp1)

        shp1 = self.env.shp1

        # only set in pp_reduce.red
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        # $BATINCLUDE %cal_red% C COM TS P T
        include_cal_red: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=c,
                arg2=Com,
                arg3=ts,
                arg4=p,
                arg5=t,
                arg10=Number(1),
                pgprim=self.env.pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                sow=sow,
                var=self.env.var,
            ),
        )
        rts = macro.rts_GP(s=s, g=self.tc, env=self.env)
        eq_ptrans = g.get_equation(f"{self.env.eq}_PTRANS")

        eq_ptrans[g.RtpVintyr[*r_v_t, p], comgrp, cg, rts, *swt].where[
            (
                g.RpsS1[r, p, s]
                * g.RpStd[r, p]
                # * All valid tuples are in RPCC_FFUNC (REDUCE taken into account); all STG excluded
                * Sum(
                    Domain(g.Rpc[r, p, c], RsTree[r, s, ts]).where[
                        coef_ptran[r, v, p, comgrp, c, cg, ts]
                    ],
                    1,
                )
            ).where[g.RpccFfunc[r, p, comgrp, cg]]
        ] = (
            # * dependent commodities - consider that the commodity may have a COM_TS shape
            Sum(
                Domain(g.ComGmap[r, cg, c], RsTree[r, s, ts]).where[
                    RtpcsVarf[r, t, p, c, ts]
                ],
                rs_fr[r, s, ts]
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow))
                # * [UR] model reduction %REDUCE% is set in *.run
                * include_cal_red,
            )
            ==
            # * control commodities
            Sum(
                Domain(RtpcsVarf[r, t, p, c, ts], RsTree[r, s, ts]).where[
                    coef_ptran[r, v, p, comgrp, c, cg, ts]
                ],
                coef_ptran[r, v, p, comgrp, c, cg, ts]
                * rs_fr[r, s, ts]
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow))
                # * [UR] model reduction %REDUCE% is set in *.run
                * include_cal_red,
            )
            * shp1
            * (
                1
                + (
                    g.act_flo[r, v, p, cg, s]
                    - Number(1).where[g.act_flo[r, v, p, cg, s]]
                ).where[g.PrcCg[r, p, comgrp]]
            )
        )
