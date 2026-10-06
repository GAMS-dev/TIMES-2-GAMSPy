# rptmain_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------
# * RPTMAIN.RPT
# *-----------------------------------------------------------------------
# * Output routine for TIMES-MACRO
# *-----------------------------------------------------------------------
# *  - creating flat dump paramaters for VEDA-BE file RUN_NAME.vd
# *  - parameters PAR_FLO/PAR_IRE contain the values of the flow variables
# *    in the reduced model plus the recalculated values of substituted flows
# *  - calculation of annual cost terms for the *.vd file

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import gamspy.math as gams_math
from gamspy import Domain, Loop, Number, Parameter, Smax, SpecialValues, Sum, sparse

from core.base_class import GamsClass

# from core.rpt_chp_ire import RrpChpIre
from core.cost_ann_rpt import CostAnnRpt, CostAnnRptConfig
from core.ddfupd_msa import ddfupd_msa_GP
from core.par_uc_rpt import ParUcRpt, ParUcRptConfig
from core.rpt_obj_rpt import RptObjRpt
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.rptmisc_rpt import RptmiscRpt, RptmiscRptConfig
from core.sol_flo_red import SolFloRed, SolFloRedConfig
from core.sol_ire_rpt import SolIreRpt, SolIreRptConfig
from core.utils import expand_set, str_repr_for_gms
from core.writeddf_msa import writeddf_msa

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class RptmainTmConfig:
    """Strongly typed data contract for rptmain.tm."""

    # %1 - Prefix for parameter names (optional)
    arg1: str = ""
    # %2 - NO_EMTY (not read by rptmain.tm)
    arg2: str = ""
    # %3 - SOW, (optional): never passed by any caller of rptmain.tm
    arg3: tuple[()] = ()


class RptmainTm(GamsClass):
    """Translation unit for rptmain.tm."""

    # Instance attributes
    module_name: str = "rptmain_tm"
    gams_source: str = "rptmain.tm"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: RptmainTmConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        cc = self.config
        # * Common reporting parameter declarations
        self.env.set_scoped("solveda", "1")
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(),
            )
        )
        # * Scenario index not supported in current version, use SOW 1
        expand_set(g.Sow, ["1"])

        # * Calculation of solution values for (due to reduction) substituted flows
        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(arg1="PAR_FLO", arg2="", arg3=".L"),
            )
        )
        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(arg1="PAR_FLO", arg2="M", arg3=".M"),
            )
        )
        self.include(SolIreRpt(self.tc, self.env, config=SolIreRptConfig()))
        # * Calculation of annual cost terms
        # *-----------------------------------------------------------------------
        # * calculate discounting for the period
        if not g.declared(g.vda_disc):
            g.vda_disc = Parameter(m, name="VDA_DISC", domain=[g.r, g.allyear])
        self.tc.enqueue(self.exec_calc_shadow_price)
        self.include(
            RptObjRpt(
                self.tc,
                self.env,
                arg1=cc.arg1,
                arg2=str_repr_for_gms(cc.arg3),
                arg3="",
                arg4="",
                arg5="0",
            )
        )
        # $ BATINCLUDE cost_ann.rpt '%1' "%3"
        self.include(
            CostAnnRpt(
                self.tc,
                self.env,
                config=CostAnnRptConfig(arg1=cc.arg1, arg2=cc.arg3),
            )
        )

        # * Miscellaneous reportings
        # $ BATINCLUDE rptmisc.rpt '%1' "%3"
        self.include(
            RptmiscRpt(
                self.tc,
                self.env,
                config=RptmiscRptConfig(arg1=cc.arg1, arg2=cc.arg3),
            )
        )
        self.tc.enqueue(self.exec_miscellaneous_reportings)

        # * CHP-related reporting parameters
        if self.env.chp_mode == "YES":
            # self.include(RptChpIre(self.tc, self.env))
            raise FileNotFoundError("rpt_chp.ier is not part of the TIMES source.")

        # * Shadow prices of user constraints
        # *---------------------------------------------------------------------
        # * Note: undiscounting only done for user constraints having region and period as index
        if self.env.var_uc != "YES":
            for config in (
                ParUcRptConfig(arg1="SM", arg2="EQE"),
                ParUcRptConfig(arg1="SM", arg2="EQG"),
                ParUcRptConfig(arg1="SM", arg2="EQL"),
            ):
                self.include(ParUcRpt(self.tc, self.env, config=config))

        self.tc.enqueue(self.exec_option)

        if self.env.merge.upper() == "YES":
            return

        self.comp_params()

        # GAMS registers these literals as UELs at compile time
        self.add_records_to_universe_item(
            records=[
                "GDP",
                "TM_GDP-REF",
                "TM_GDP-ACT",
                "TM_PRD-Y",
                "TM_CON-C",
                "TM_CAP-K",
                "TM_INV-I",
                "TM_ESCOST",
                "TM_GDPLOS",
            ]
        )
        self.tc.enqueue(self.exec_report_params)

    def exec_calc_shadow_price(self: RptmainTm) -> None:
        g = self.tc

        # * [UR]: Calculation of shadow prices in MACRO
        g.vda_disc[g.r, g.t] = -g.eq_escost.m[g.r, g.t] * g.tm_scale_cst
        with Loop(g.Miyr1[g.tt[g.t - 1]]):
            g.vda_disc[g.r, g.tt].where[g.vda_disc[g.r, g.tt] <= 0] = (
                g.coef_pvt[g.r, g.tt] / g.coef_pvt[g.r, g.t] * g.vda_disc[g.r, g.t]
            )
        g.coef_pvt[g.r, g.t] = g.vda_disc[g.r, g.t]
        g.VAR_OBJ.setRecords(None)

    def exec_miscellaneous_reportings(self: RptmainTm) -> None:
        g = self.tc

        g.VAR_UTIL.up[...] = SpecialValues.POSINF
        g.OBJZ.l[...] = g.VAR_UTIL.l
        # *-----------------------------------------------------------------------

        # *-----------------------------------------------------------------------
        # * Include explicit EPS values for zero flows
        # *-----------------------------------------------------------------------
        g.par_flo[g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.s].where[
            g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s] * g.RpFlo[g.r, g.p]
        ] = sparse(
            Number(SpecialValues.EPS).where[~g.par_flo[g.r, g.v, g.t, g.p, g.c, g.s]]
        )
        g.par_ire[g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.ts, g.ie].where[
            g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts].where[g.RpcIre[g.r, g.p, g.c, g.ie]]
        ] = sparse(
            Number(SpecialValues.EPS).where[
                ~g.par_ire[g.r, g.v, g.t, g.p, g.c, g.ts, g.ie]
            ]
        )

        # *-----------------------------------------------------------------------
        # * Discounted objective values by cost type(INV, FIX, VAR etc.)
        # *-----------------------------------------------------------------------
        # * Discounted objective value by region
        g.reg_obj[g.r] = Sum(
            [g.Obvann, g.t, g.Rdcur[g.r, g.cur]],
            g.obj_pvt[g.r, g.t, g.cur] * g.VAR_ANNCST.l[g.Obvann, g.r, g.t, g.cur],
        )
        g.reg_wobj[g.r, "INV", g.cur] = Sum(
            g.t, g.obj_pvt[g.r, g.t, g.cur] * g.VAR_ANNCST.l["OBJINV", g.r, g.t, g.cur]
        )
        g.reg_wobj[g.r, "FIX", g.cur] = Sum(
            g.t, g.obj_pvt[g.r, g.t, g.cur] * g.VAR_ANNCST.l["OBJFIX", g.r, g.t, g.cur]
        )
        g.reg_wobj[g.r, "VAR", g.cur] = Sum(
            g.t, g.obj_pvt[g.r, g.t, g.cur] * g.VAR_ANNCST.l["OBJVAR", g.r, g.t, g.cur]
        )

        # * [UR]: undiscounting of dual variable of VAR_NCAP
        # * [AL]: COEF_OBJINV includes the full effect of one unit of NCAP_ICOST on the objective:
        # * PAR_NCAPM(R,T,P)$(VAR_NCAP.M(R,T,P)*SUM(RDCUR(R,CUR),COEF_OBJINV(R,T,P,CUR)))
        # *    = VAR_NCAP.M(R,T,P)/SUM(RDCUR(R,CUR),COEF_OBJINV(R,T,P,CUR));

    def exec_option(self: RptmainTm) -> None:
        g = self.tc
        g.f_inout.setRecords(None)
        g.f_inouts.setRecords(None)
        g.FIoset.setRecords(None)

    def comp_params(
        self: RptmainTm,
    ) -> None:
        g = self.tc
        m = g.container
        # *---------------------------------------------------------------------
        # * Report parameters for TIMES-MACRO
        # *---------------------------------------------------------------------
        g.par_y = Parameter(
            m, name="PAR_Y", domain=[g.r, g.t], description="Production parameter"
        )
        g.par_gry = Parameter(
            m,
            name="PAR_GRY",
            domain=[g.r, g.t],
            description="Growth rate of production",
        )
        g.par_grgdp = Parameter(
            m, name="PAR_GRGDP", domain=[g.r, g.t], description="Growth rate of GDP"
        )
        g.par_mc = Parameter(
            m,
            name="PAR_MC",
            domain=[g.r, g.ll, g.c],
            description="Marginal cost demand commodity",
        )
        g.tm_gdp = Parameter(
            m, name="TM_GDP", domain=[g.r, g.t], description="Current GDP parameter"
        )
        g.tm_gdpgoal = Parameter(
            m, name="TM_GDPGOAL", domain=[g.r, g.ll], description="Baseline GDP"
        )
        g.tm_dem = Parameter(m, name="TM_DEM", domain=[g.r, g.year, g.c])
        g.tm_ddf_y = Parameter(m, name="TM_DDF_Y", domain=[g.r, g.t])
        g.tm_ddf_dm = Parameter(m, name="TM_DDF_DM", domain=[g.r, g.t, g.c])
        g.tm_ddf_sp = Parameter(m, name="TM_DDF_SP", domain=[g.r, g.t, g.c])
        g.tm_f2 = Parameter(m, name="TM_F2", domain=[g.r, g.t, g.c])
        g.tm_err = Parameter(m, name="TM_ERR", domain=[g.item])

    def exec_report_params(self: RptmainTm) -> None:
        g = self.tc

        if g.tm_gr.number_records:
            g.done[...] = 1
        else:
            g.done[...] = 0
            g.tm_gr[g.r, g.t] = sparse(g.tm_growv[g.r, g.t])
        g.Mr[g.r] = sparse(Sum(g.t.where[g.tm_gr[g.r, g.t]], 1))
        g.par_grgdp[g.r, g.t] = g.tm_gr[g.r, g.t]
        g.par_gry[g.r, g.t] = g.tm_gr[g.r, g.t]
        g.tm_gdpgoal[g.r, g.t1] = g.tm_gdp0[g.r]

        with Loop(g.tt[g.t + 1]):
            g.tm_gdpgoal[g.r, g.tt] = g.tm_gdpgoal[g.r, g.t] * (
                (1 + g.tm_gr[g.r, g.t] / 100) ** g.nyper[g.t]
            )
        g.par_y[g.r, g.t[g.t1]] = g.tm_y0[g.r]
        g.par_y[g.r, g.t[g.tt + 1]] = (
            g.VAR_C.l[g.r, g.t] + g.VAR_INV.l[g.r, g.t] + g.VAR_EC.l[g.r, g.t]
        )
        g.tm_gdp[g.r, g.t[g.t1]] = g.tm_gdp0[g.r]
        g.tm_gdp[g.r, g.t[g.tt + 1]] = g.par_y[g.r, g.t] - g.VAR_EC.l[g.r, g.t]

        g.par_gry[g.r, g.tt[g.t - 1]] = 100 * (
            (g.par_y[g.r, g.t] / g.par_y[g.r, g.tt]) ** (1 / g.nyper[g.tt]) - 1
        )
        g.par_grgdp[g.r, g.tt[g.t - 1]] = 100 * (
            (g.tm_gdp[g.r, g.t] / g.tm_gdp[g.r, g.tt]) ** (1 / g.nyper[g.tt]) - 1
        )

        g.tm_ec0[g.r] = Sum(g.t1, g.VAR_OBJCOST.l[g.r, g.t1] * g.tm_scale_cst)
        g.par_mc[g.r, g.t1, g.c] = sparse(g.tm_ddatpref[g.r, g.c])
        g.par_mc[g.r, g.t[g.tt + 1], g.c].where[g.Dem[g.r, g.c]] = (
            -g.VAR_SP.m[g.r, g.t, g.c]
            / g.eq_escost.m[g.r, g.t]
            * (g.tm_scale_nrg / g.tm_scale_cst)
        )

        # * Eliminate zero or non-smooth marginals in first period
        with Loop(g.t1[g.t[g.tt - 1]]):
            g.par_mc[g.r, g.t, g.c].where[
                (g.par_mc[g.r, g.t, g.c] < g.par_mc[g.r, g.tt, g.c] * 0.7).where[
                    g.Dem[g.r, g.c]
                ]
            ] = g.par_mc[g.r, g.tt, g.c] * 0.7
        g.tm_dem[g.r, g.t, g.c].where[
            (g.par_mc[g.r, g.t, g.c] > 0).where[
                (g.com_proj[g.r, g.t, g.c] > 0).where[g.Dem[g.r, g.c]]
            ]
        ] = g.com_proj[g.r, g.t, g.c]

        g.tm_err["DEM"] = Smax(
            Domain(g.r, g.t, g.c).where[g.tm_dem[g.r, g.t, g.c]],
            gams_math.abs(g.tm_dem[g.r, g.t, g.c] - g.VAR_DEM.l[g.r, g.t, g.c])
            / g.tm_dem[g.r, g.t, g.c],
        )
        g.tm_err["GDP"] = Smax(
            [g.Reg, g.t],
            gams_math.abs(g.tm_gdpgoal[g.Reg, g.t] - g.tm_gdp[g.Reg, g.t])
            / g.tm_gdpgoal[g.Reg, g.t],
        )

        # * Reporting parameters
        g.tm_result["TM_GDP-REF", g.Mr, g.t] = g.tm_gdpgoal[g.Mr, g.t].where[g.done]
        g.tm_result["TM_GDP-ACT", g.Mr, g.t] = g.tm_gdp[g.Mr, g.t]
        g.tm_result["TM_PRD-Y", g.Mr, g.t] = g.par_y[g.Mr, g.t]
        g.tm_result["TM_CON-C", g.Mr, g.t] = g.VAR_C.l[g.Mr, g.t]
        g.tm_result["TM_CAP-K", g.Mr, g.t] = g.VAR_K.l[g.Mr, g.t]
        g.tm_result["TM_INV-I", g.Mr, g.t] = g.VAR_INV.l[g.Mr, g.t]
        g.tm_result["TM_ESCOST", g.Mr, g.t] = g.VAR_EC.l[g.Mr, g.t]
        g.tm_result["TM_GDPLOS", g.Mr, g.t].where[g.done] = (
            100.0
            * (g.tm_gdpgoal[g.Mr, g.t] - g.tm_gdp[g.Mr, g.t])
            / g.tm_gdpgoal[g.Mr, g.t]
        )

        ddfupd_msa_GP(g)
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=writeddf_msa(arg1="DDFNEW", arg2="TM_GR"),
        )
