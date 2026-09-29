# ppm_ext_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * ppm_ext.MLF oversees extended preprocessing activities for MLF
# *============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Ord, Smax, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, power, project

from core.base_class import GamsClass
from core.filparam_gms import FilparamGms, FilparamGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtMlf(GamsClass):
    """Translation unit for ppm_ext.mlf."""

    # Instance attributes
    module_name: str = "ppm_ext_mlf"
    gams_source: str = "ppm_ext.mlf"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.tc.enqueue(self.exec1)
        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.tm_dmc,
                    arg2=(g.r,),
                    tail1=(g.c,),
                    arg4=("", "", "", "", ""),
                    arg5=g.Datayear,
                    arg6=g.t,
                ),
            )
        )
        self.tc.enqueue(self.exec2)

    def exec1(self: PpmExtMlf) -> None:
        g = self.tc
        project(source=g.Dem, target=g.TmDm)
        g.tm_dmc.setRecords(None)
        with Loop(g.MiDmas[g.r, g.Com, g.c]):
            g.TmDm[g.r, g.c] = False
        # * Marginal costs of demands
        g.tm_dmc[g.Rtc[g.r, g.t, g.c]].where[g.Dem[g.r, g.c]] = Sum(
            [g.ComTs[g.r, g.c, g.s], g.Rdcur[g.r, g.cur]],
            g.com_bprice[g.Rtc, g.s, g.cur] * g.com_fr[g.Rtc, g.s],
        )
        g.tm_dmc[g.r, g.t, g.c].where[(g.tm_dmc[g.r, g.t, g.c] == 0.0)] = 0.0
        g.tm_amp[g.r, g.t] = (
            g.sol_acfr[g.r, "COST", g.t]
            * Sum(g.Dem[g.r, g.c], g.tm_dmc[g.r, g.t, g.c] * g.com_proj[g.r, g.t, g.c])
            + 1.0
            - 1.0
        )
        g.tm_amp[g.Mr, g.t].where[((g.m[g.t] > g.miyr_v1 + 9.0).where[g.Pp[g.t]])] = 0.0

    def exec2(self: PpmExtMlf) -> None:
        g = self.tc
        # * Demand levels audit
        g.tm_dem[g.Mr[g.r], g.t, g.c].where[
            ((g.com_proj[g.r, g.t, g.c] > 0.0).where[g.Dem[g.r, g.c]])
        ] = g.com_proj[g.r, g.t, g.c]
        with Loop(g.Pp[g.t]):
            g.TmDm[g.Dem[g.r, g.c]].where[(g.tm_dmc[g.r, g.t, g.c] == 0.0)] = False
            g.TmDm[g.Dem[g.r, g.c]].where[(g.tm_dem[g.r, g.t, g.c] == 0.0)] = False
        # * remove elasticity steps from demands, keeping aggregates elastic
        g.Rcj[g.TmDm[g.Mr, g.c], g.j, g.bd] = False
        g.com_elast[g.Mr[g.r], g.Pp, g.c, g.Annual, g.Bdneq].where[g.TmDm[g.r, g.c]] = (
            sparse(g.RdAgg[g.r, g.c])
        )
        g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
            ((~(g.TmDm[g.r, g.c].where[g.Pp[g.t]])).where[g.tm_step[g.r, g.c, "N"]])
        ] = sparse(g.RcsCombal[g.r, g.t, g.c, g.s, "FX"])
        # *-----------------------------------------------------------------------------
        # * Aggregate demand, expenditures and price
        g.Dm.setRecords(None)
        g.Dm["ACT"] = True
        g.tm_annc[g.Mr[g.r], g.t] = Sum(
            g.Dem[g.r, g.c], g.tm_dmc[g.r, g.t, g.c] * g.tm_dem[g.r, g.t, g.c]
        )
        g.tm_dem[g.Mr[g.r], g.t, g.Dm] = Sum(g.Dem[g.r, g.c], g.tm_dem[g.r, g.t, g.c])
        g.tm_dmc[g.Mr[g.r], g.t, g.Dm] = g.tm_annc[g.r, g.t] / g.tm_dem[g.r, g.t, g.Dm]
        with Loop(g.tb[g.tt[g.t - 1]]):
            g.tm_dmc[g.r, g.tt, g.Dm] = Max(
                g.tm_dmc[g.r, g.tt, g.Dm], g.tm_dmc[g.r, g.t, g.Dm] * 0.7
            )
        # * Annual costs and net taxes for MACRO
        g.tm_annc[g.Mr[g.r], g.t] = g.sol_acfr[g.r, "COST", g.t] * g.tm_annc[g.r, g.t]
        g.tm_annc[g.r, g.t] = sparse(g.tm_amp[g.r, g.t])
        g.tm_taxrev[g.Mr[g.r], g.t] = g.sol_acfr[g.r, "TAX", g.t] * g.tm_annc[g.r, g.t]
        # *-----------------------------------------------------------------------------
        # * Quadratic supply function
        g.tm_annc[g.r, g.t] = g.tm_annc[g.r, g.t] * g.tm_scale_cst
        with Loop(g.tb):
            g.tm_ec0[g.r] = g.tm_annc[g.r, g.tb]
            g.tm_ddatpref[g.r, g.Dm] = g.tm_dmc[g.r, g.tb, g.Dm]
        g.tm_qsfb[g.r, g.t, g.Dm].where[g.tm_dem[g.r, g.t, g.Dm]] = (
            0.5 * g.tm_dmc[g.r, g.t, g.Dm] * g.tm_scale_cst / g.tm_dem[g.r, g.t, g.Dm]
        )
        g.tm_qsfa[g.r, g.t] = g.tm_annc[g.r, g.t] - Sum(
            g.Dm, g.tm_qsfb[g.r, g.t, g.Dm] * (g.tm_dem[g.r, g.t, g.Dm] ** 2.0)
        )
        # *-----------------------------------------------------------------------------
        # * Process macro parameters
        g.tm_depr[g.r].where[(~(g.tm_depr[g.r]))] = g.tm_defval["DEPR"]
        g.tm_esub[g.r].where[(~(g.tm_esub[g.r]))] = g.tm_defval["ESUB"]
        g.tm_desub[g.r].where[(~(g.tm_desub[g.r]))] = g.tm_esub[g.r]
        g.tm_kgdp[g.r].where[(~(g.tm_kgdp[g.r]))] = g.tm_defval["KGDP"]
        g.tm_kpvs[g.r].where[(~(g.tm_kpvs[g.r]))] = g.tm_defval["KPVS"]
        g.tm_dmtol[g.r].where[(~(g.tm_dmtol[g.r]))] = g.tm_defval["DMTOL"]
        g.tm_ivetol[g.r].where[(~(g.tm_ivetol[g.r]))] = g.tm_defval["IVETOL"]
        # * Calculate cost amplifier
        g.tm_amp[g.Mr, g.t] = Max(
            0.0,
            Smax(
                g.Pp[g.tt].where[(Ord(g.tt) > Ord(g.t))],
                g.tm_annc[g.Mr, g.tt]
                / (g.tm_gdpgoal[g.Mr, g.tt] / g.tm_gdpgoal[g.Mr, g.t])
                * power(g.tm_defval["ESC"], g.yearval[g.t] - g.yearval[g.tt]),
            )
            - g.tm_annc[g.Mr, g.t],
        )
        # *============================================================================*
        # * Initialize the economic parameters
        # *============================================================================*
        g.tm_ddf[g.Mr, g.t, g.Dm] = SpecialValues.EPS
        g.tm_aeeiv[g.Mr, g.t, g.Dm] = SpecialValues.EPS
        g.tm_asrv[g.r] = 1.0 - g.tm_depr[g.r] / 100.0
        g.tm_growv[g.Mr, g.t] = g.tm_gr[g.Mr, g.t]
        g.tm_dfactcurr[g.r, g.Xtp] = 1.0 - (
            g.tm_kpvs[g.r] / g.tm_kgdp[g.r]
            - g.tm_depr[g.r] / 100.0
            - g.tm_growv[g.r, g.Xtp] / 100.0
        )
        g.tm_rho[g.r] = 1.0 - 1.0 / g.tm_esub[g.r]
        g.tm_tsrv[g.r, g.t] = g.tm_asrv[g.r] ** g.nyper[g.t]
        g.tm_k0[g.r] = g.tm_kgdp[g.r] * g.tm_gdp0[g.r]
        g.tm_iv0[g.r] = (
            g.tm_k0[g.r] * (g.tm_depr[g.r] + Sum(g.tb, g.tm_growv[g.r, g.tb])) / 100.0
        )
        g.tm_c0[g.r] = g.tm_gdp0[g.r] - g.tm_iv0[g.r]
        g.tm_y0[g.r] = g.tm_gdp0[g.r] + g.tm_ec0[g.r] + Sum(g.tb, g.tm_amp[g.r, g.tb])
        # *============================================================================*
        # * Calculate intermediate values
        # *============================================================================*
        g.tm_aeeifac[g.Mr, g.t, g.Dm] = 1.0
        g.tm_dfact[g.Mr, g.tb] = 1.0
        g.tm_l[g.Mr, g.tb] = 1.0
        with Loop(g.Pp[g.t + 1]):
            g.tm_dfact[g.r, g.Pp] = g.tm_dfact[g.r, g.t] * (
                g.tm_dfactcurr[g.r, g.t] ** g.nyper[g.t]
            )
            g.tm_l[g.r, g.Pp] = g.tm_l[g.r, g.t] * (
                (1.0 + g.tm_growv[g.r, g.t] / 100.0) ** g.nyper[g.t]
            )
        # * Arbitrary multiplier on utility in last time period
        g.tm_dfact[g.Mr[g.r], g.Tlast].where[(g.tm_arbm > 1.0)] = (
            g.tm_dfact[g.r, g.Tlast]
            * (
                1.0
                - (
                    Min(0.999, g.tm_dfactcurr[g.r, g.Tlast])
                    ** (g.nyper[g.Tlast] * g.tm_arbm)
                )
            )
            / (
                1.0
                - (Min(0.999, g.tm_dfactcurr[g.r, g.Tlast]) ** (g.nyper[g.Tlast] * 1.0))
            )
        )
        # * Weights for periods
        g.z[...] = Max(1.0, Smax(g.t, g.d[g.t]))
        g.tm_pwt[g.t] = g.d[g.t] / g.z
        g.tm_d0[g.Mr[g.r], g.Dm] = Sum(g.tb, g.tm_dem[g.r, g.tb, g.Dm]) * g.tm_scale_nrg
        g.tm_b[g.Mr[g.r], g.Dm] = (g.tm_d0[g.r, g.Dm] / g.tm_y0[g.r]) ** (
            1.0 - g.tm_rho[g.r]
        )
        g.tm_b[g.Mr[g.r], g.Dm] = (
            g.tm_scale_cst
            / g.tm_scale_nrg
            * g.tm_ddatpref[g.r, g.Dm]
            * g.tm_b[g.r, g.Dm]
        )
        g.tm_akl[g.Mr[g.r]] = (g.tm_y0[g.r] ** g.tm_rho[g.r]) - Sum(
            g.Dm, g.tm_b[g.r, g.Dm] * (g.tm_d0[g.r, g.Dm] ** g.tm_rho[g.r])
        )
        g.tm_akl[g.Mr[g.r]] = g.tm_akl[g.r] / (
            g.tm_k0[g.r] ** (g.tm_kpvs[g.r] * g.tm_rho[g.r])
        )
