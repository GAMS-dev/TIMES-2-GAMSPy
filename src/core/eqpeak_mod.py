# eqpeak_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQPEAK is the basic commodity balance and the production limit constraint
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# * - NCAP_PKCNT uses the vintage period !
# * - Even annual level processes contribute to a seasonal peak according to PKCNT
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Product, Sum
from gamspy.math import Max

from core.base_class import GamsClass
from core.cal_cap_mod import CalCapModConfig, cal_cap_mod_GP
from core.cal_fflo_mod import CalFfloModConfig, cal_fflo_mod_GP
from core.cal_ire_mod import CalIreModConfig, cal_ire_mod_GP
from core.cal_stgn_mod import CalStgnModConfig, cal_stgn_mod_GP
from core.eqpk_ect_ier import eqpk_ect_ier_GP
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqpeakMod(GamsClass):
    """Translation unit for eqpeak.mod."""

    # Instance attributes
    module_name: str = "eqpeak_mod"
    gams_source: str = "eqpeak.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.env.set_scoped("swstmp", self.env.sws)
        self.env.set_scoped("swstmp_GP", self.env.sws_GP)
        # sws_local should be set to sws, however this can only be "" here so go with Number(1)
        sws_local: Product | Number = Number(1)
        if self.env.stages.upper() == "YES":
            sws_local = Product(
                g.SwMap[g.t, g.Sow, g.j, g.ww].where[
                    g.s_com_proj[g.r, g.t, g.c, g.j, g.ww]
                ],
                g.s_com_proj[g.r, g.t, g.c, g.j, g.ww],
            )

        self.comp1(
            eq=self.env.eq,
            r_t=self.env.r_t_GP,
            swt=self.env.swt_GP,
            varv=self.env.varv_GP,
            swstmp=self.env.swstmp_GP,
            rcapsub=self.env.rcapsub_GP,
            peakchp=self.env.peakchp,
            sws_local=sws_local,
            var=self.env.var,
            sow=self.env.sow_GP,
            condition=self.env.timesed == "YES",
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            is_ireauxbal=self.env.is_set("ireauxbal"),
            reduce=self.env.reduce,
            pgprim=self.env.pgprim,
        )

    def comp1(
        self: EqpeakMod,
        eq: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        varv: tuple[str, ImplicitSet | None],
        swstmp: tuple[Set | Alias, ...] | tuple[()],
        rcapsub: Condition | Expression | Number,
        peakchp: str,
        sws_local: Product | Number,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        condition: bool,
        is_rtp_ffcs_defined: bool,
        is_ireauxbal: bool,
        reduce: str,
        pgprim: str,
    ) -> None:
        g = self.tc
        r, v, t, p, c, s, sl, ts = g.r, g.v, g.t, g.p, g.c, g.s, g.sl, g.ts
        cg2, Com, j, bd, ble, opr = g.cg2, g.Com, g.j, g.bd, g.Ble, g.Opr

        eq_peak = g.get_equation(f"{eq}_PEAK")
        VAR_BLND = g.get_variable(f"{var}_BLND")
        VAR_DEM = g.get_variable(f"{var}_DEM")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
        VAR_ELAST = g.get_variable(f"{var}_ELAST")
        rts = macro.rts_GP(s=sl, g=self.tc, env=self.env)

        # NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C), the peak contribution of a process
        pkcnt_pkf = g.ncap_pkcnt[r, v, p, s] ** g.rpc_pkf[r, p, c]

        # *   inter-regional trade to region; processes with PKNO+PKCNT contribute by net imports
        cal_ire_1 = cal_ire_mod_GP(
            g=g,
            config=CalIreModConfig(
                var=var,
                sow=sow,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                is_ireauxbal=is_ireauxbal,
                arg1="IMP",
                arg2="OUT",
                arg3=g.ie,
                arg4=g.ncap_pkcnt[r, v, p, s],
                arg5="-",
            ),
        )
        cal_ire_2 = cal_ire_mod_GP(
            g=g,
            config=CalIreModConfig(
                var=var,
                sow=sow,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                is_ireauxbal=is_ireauxbal,
                arg1="EXP",
                arg2="IN",
                arg3=g.ie,
                arg4=(-g.ncap_pkcnt[r, v, p, s] / g.com_ie[r, t, c, s]).where[
                    g.com_ie[r, t, c, s] > 0
                ],
                arg5="-",
                arg6=g.PrcPkno,
            ),
        )
        # *   storage
        cal_stgn_1 = cal_stgn_mod_GP(
            g=g,
            config=CalStgnModConfig(
                var=var,
                sow=sow,
                arg1="OUT",
                arg2="IN",
                arg3=g.stg_eff[r, v, p],
                arg4=Number(1),
                arg5=~g.PrcNstts[r, p, ts],
                arg6=pkcnt_pkf.where[g.rpc_pkf[r, p, c]],
            ),
        )
        # *   individual flows
        cal_fflo_1 = cal_fflo_mod_GP(
            g=g,
            config=CalFfloModConfig(
                reduce=reduce,
                sow=sow,
                var=var,
                pgprim=pgprim,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                arg1="OUT",
                arg3=pkcnt_pkf,
                arg4=g.rpc_pkf[r, p, c],
            ),
        )
        # * [UR]: 04/22/2003: adjustment for extraction condensing CHP plants
        eqpk_ect: Sum | int = 0
        # from prep_ext.ier
        if peakchp == "eqpk_ect.ier":
            eqpk_ect = eqpk_ect_ier_GP(
                g=g,
                varv=varv,
                sws=self.env.sws_GP,
                reduce=reduce,
                sow=sow,
                var=var,
                pgprim=pgprim,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            )
        cal_fflo_2 = cal_fflo_mod_GP(
            g=g,
            config=CalFfloModConfig(
                reduce=reduce,
                sow=sow,
                var=var,
                pgprim=pgprim,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                arg1="IN",
                arg3=g.flo_pkcoi[r, t, p, c, ts],
                arg4=Number(1),
            ),
        )
        # *   inter-regional trade from region
        cal_ire_3 = cal_ire_mod_GP(
            g=g,
            config=CalIreModConfig(
                var=var,
                sow=sow,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
                is_ireauxbal=is_ireauxbal,
                arg1="EXP",
                arg2="IN",
                arg3=g.ie,
                arg4=g.flo_pkcoi[r, t, p, c, ts],
                arg5="-",
            ),
        )
        # * capacity related commodity flows
        # *   fixed commodity associated with installed capacity or investment
        cal_cap = cal_cap_mod_GP(
            g=g,
            config=CalCapModConfig(
                varv=varv,
                sws=self.env.sws_GP,
                rcapsub=rcapsub,
                arg1="IN",
                arg2="I",
                arg3=Number(1).where[~g.PrcPkno[r, p]],
            ),
        )
        cal_stgn_2 = cal_stgn_mod_GP(
            g=g,
            config=CalStgnModConfig(
                var=var,
                sow=sow,
                arg1="IN",
                arg2="OUT",
                arg3=Number(1),
                arg4=g.stg_eff[r, v, p] * pkcnt_pkf,
                arg5=~g.PrcMap[r, "NST", p] + g.PrcNstts[r, p, ts],
                arg6=Number(1).where[g.rpc_pkf[r, p, c]],
            ),
        )

        installed = (
            macro.VAR_NCAP_GP(varv, r, v, p, swstmp).where[g.Milestonyr[v]]
            + g.ncap_pasti[r, v, p].where[g.Pastyear[v]]
            + rcapsub
        )
        capacity = Sum(
            g.RpcPkc[r, p, c],
            g.g_yrfr[r, s]
            * g.prc_capact[r, p]
            * Sum(
                v.where[g.coef_vnt[r, t, p, v]],
                g.coef_vnt[r, t, p, v]
                * g.prc_actflo[r, v, p, c]
                * g.ncap_pkcnt[r, v, p, s]
                * installed,
            ),
        )

        # *   blending
        blending = Sum(
            g.BleOpr[r, ble, opr].where[g.BleInp[r, ble, c] * g.BleTp[r, t, ble]],
            g.g_yrfr[r, s]
            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, "ANNUAL", sow))
            * g.bl_inp[r, ble, c]
            * g.peakda_bl[r, ble, t]
            * VAR_BLND[r, t, ble, opr, *sow],
        )
        # *   demand projection
        demand = (
            (
                sws_local * g.com_proj[r, t, c].where[~g.rd_nlp[r, c]]
                + VAR_DEM[r, t, c, *sow].where[g.rd_nlp[r, c]]
                + Sum(
                    g.RdAgg[r, Com],
                    g.rd_shar[r, t, Com, c] * VAR_COMPRD[r, t, Com, "ANNUAL", *sow],
                )
            )
            * macro.com_fr.com_fr_GP(self.env.mx_GP, r, t, c, s)
        ).where[g.Dem[r, c]]
        # *   include the elasticity variables
        elast: Sum | int = 0
        if condition:
            elast = Sum(
                g.Rcj[r, c, j, g.Bdneq[bd]].where[g.com_elast[r, t, c, s, bd]],
                -g.bdsig[bd] * VAR_ELAST[r, t, c, s, j, bd, *sow],
            )

        peak_domain = Domain(g.ComGmap[r, cg2, c], g.ComTs[r, c, s]).where[
            g.rs_fr[r, sl, s]
        ]
        eq_peak[*r_t, cg2, rts, *swt].where[
            Sum(g.ComGmap[r, cg2, c].where[g.Rtc[r, t, c]], 1).where[
                g.ComPkts[r, cg2, sl]
            ]
        ] = Sum(
            peak_domain,
            g.rs_fr[r, sl, s]
            # * Apply maximum reserve among CG2 and C
            * (
                1
                / (1 + Max(Sum(Com[cg2], g.com_pkrsv[r, t, Com]), g.com_pkrsv[r, t, c]))
            )
            * g.com_ie[r, t, c, s]
            * (
                capacity
                # * production
                + cal_ire_1
                + cal_ire_2
                # *GG*PK no multiplier
                # * [UR] 25.04.2003 added NCAP_PKCNT multiplier to turn off contribution
                # *      by setting NCAP_PKCNT to zero; allow using PKNO to switch process
                # *      to production-based peak contribution
                + (cal_stgn_1 + cal_fflo_1)
                + eqpk_ect
            ),
        ) >= Sum(
            peak_domain,
            g.rs_fr[r, sl, s]
            # * Apply maximum flexibility among CG2 and C
            * (
                1
                + Max(
                    Sum(Com[cg2], g.com_pkflx[r, t, Com, sl]),
                    g.com_pkflx[r, t, c, s],
                )
            )
            # * consumption
            # *GG*PK pass TS as timeslice
            * (
                cal_fflo_2
                + cal_ire_3
                + cal_cap
                + cal_stgn_2
                + blending
                + demand
                + elast
            ),
        )
