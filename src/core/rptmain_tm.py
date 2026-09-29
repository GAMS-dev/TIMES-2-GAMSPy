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
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass

# from core.rpt_chp_ire import RrpChpIre
from core.cost_ann_rpt import CostAnnRpt, CostAnnRptConfig, arg2_repr
from core.ddfupd_msa import ddfupd_msa
from core.par_uc_rpt import ParUcRpt, ParUcRptConfig
from core.rpt_obj_rpt import RptObjRpt
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.rptmisc_rpt import RptmiscRpt, RptmiscRptConfig
from core.sol_flo_red import SolFloRed, SolFloRedConfig
from core.sol_ire_rpt import SolIreRpt
from core.writeddf_msa import writeddf_msa

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptmainTm(GamsClass):
    """Translation unit for rptmain.tm."""

    # Instance attributes
    module_name: str = "rptmain_tm"
    gams_source: str = "rptmain.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: tuple[Set | Alias | str, ...] | tuple[()] = (),
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        # * Common reporting parameter declarations
        self.env.set_scoped("solveda", "1")
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(),
            )
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Scenario index not supported in current version, use SOW 1
  SET SOW / 1 /;
""",
        )

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
        self.include(SolIreRpt(self.tc, self.env))
        # * Calculation of annual cost terms
        # *-----------------------------------------------------------------------
        # * calculate discounting for the period
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
  PARAMETER VDA_DISC(R,ALLYEAR) //;
""",
        )
        self.tc.enqueue(self.exec_calc_shadow_price)
        self.include(
            RptObjRpt(
                self.tc,
                self.env,
                arg1=self.arg1,
                arg2=arg2_repr(self.arg3),
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
                config=CostAnnRptConfig(arg1=self.arg1, arg2=self.arg3),
            )
        )

        # * Miscellaneous reportings
        # $ BATINCLUDE rptmisc.rpt '%1' "%3"
        self.include(
            RptmiscRpt(
                self.tc,
                self.env,
                config=RptmiscRptConfig(arg1=self.arg1, arg2=self.arg3),
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
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* [UR]: Calculation of shadow prices in MACRO
  VDA_DISC(R,T) = -EQ_ESCOST.M(R,T) * TM_SCALE_CST;
  LOOP(MIYR_1(TT(T-1)),VDA_DISC(R,TT)$(VDA_DISC(R,TT) LE 0) = COEF_PVT(R,TT)/COEF_PVT(R,T)*VDA_DISC(R,T));
  COEF_PVT(R,T) = VDA_DISC(R,T);
  OPTION CLEAR=VAR_OBJ;
""",
        )

    def exec_miscellaneous_reportings(self: RptmainTm) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  VAR_UTIL.UP = INF;
  OBJz.L = VAR_UTIL.L;
*-----------------------------------------------------------------------

*-----------------------------------------------------------------------
* Include explicit EPS values for zero flows
*-----------------------------------------------------------------------
  PAR_FLO(RTP_VINTYR(R,V,T,P),C,S)$(RTPCS_VARF(R,T,P,C,S)*RP_FLO(R,P)) $= EPS$(NOT PAR_FLO(R,V,T,P,C,S));
  PAR_IRE(RTP_VINTYR(R,V,T,P),C,TS,IE)$(RTPCS_VARF(R,T,P,C,TS)$RPC_IRE(R,P,C,IE)) $= EPS$(NOT PAR_IRE(R,V,T,P,C,TS,IE));

*-----------------------------------------------------------------------
* Discounted objective values by cost type(INV, FIX, VAR etc.)
*-----------------------------------------------------------------------
* Discounted objective value by region
  REG_OBJ(R) = SUM((OBVANN,T,RDCUR(R,CUR)), OBJ_PVT(R,T,CUR) * VAR_ANNCST.L(OBVANN,R,T,CUR));
  REG_WOBJ(R,'INV',CUR) = SUM(T, OBJ_PVT(R,T,CUR) * VAR_ANNCST.L('OBJINV',R,T,CUR));
  REG_WOBJ(R,'FIX',CUR) = SUM(T, OBJ_PVT(R,T,CUR) * VAR_ANNCST.L('OBJFIX',R,T,CUR));
  REG_WOBJ(R,'VAR',CUR) = SUM(T, OBJ_PVT(R,T,CUR) * VAR_ANNCST.L('OBJVAR',R,T,CUR));

* [UR]: undiscounting of dual variable of VAR_NCAP
* [AL]: COEF_OBJINV includes the full effect of one unit of NCAP_ICOST on the objective:
* PAR_NCAPM(R,T,P)$(VAR_NCAP.M(R,T,P)*SUM(RDCUR(R,CUR),COEF_OBJINV(R,T,P,CUR)))
*    = VAR_NCAP.M(R,T,P)/SUM(RDCUR(R,CUR),COEF_OBJINV(R,T,P,CUR));

""",
        )

    def exec_option(self: RptmainTm) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OPTION CLEAR=F_INOUT, CLEAR=F_INOUTS, CLEAR=F_IOSET;
""",
        )

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
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
IF(CARD(TM_GR), DONE=1;
ELSE DONE=0; TM_GR(R,T)$=TM_GROWV(R,T));
MR(R)$=SUM(T$TM_GR(R,T),1);
PAR_GRGDP(R,T) = TM_GR(R,T);
PAR_GRY(R,T)   = TM_GR(R,T);
TM_GDPGOAL(R,T_1) = TM_GDP0(R);

LOOP(TT(T+1),TM_GDPGOAL(R,TT) = TM_GDPGOAL(R,T)*(1+TM_GR(R,T)/100)**NYPER(T));
PAR_Y(R,T(T_1))  = TM_Y0(R);   PAR_Y(R,T(TT+1)) = VAR_C.L(R,T) + VAR_INV.L(R,T) + VAR_EC.L(R,T);
TM_GDP(R,T(T_1)) = TM_GDP0(R); TM_GDP(R,T(TT+1)) = PAR_Y(R,T) - VAR_EC.L(R,T);

PAR_GRY(R,TT(T-1))   = 100*((PAR_Y(R,T)/PAR_Y(R,TT))**(1/NYPER(TT))-1);
PAR_GRGDP(R,TT(T-1)) = 100*((TM_GDP(R,T)/TM_GDP(R,TT))**(1/NYPER(TT))-1);

TM_EC0(R) = SUM(T_1, VAR_OBJCOST.L(R,T_1)*TM_SCALE_CST);
PAR_MC(R,T_1,C) $= TM_DDATPREF(R,C);
PAR_MC(R,T(TT+1),C)$DEM(R,C) = - VAR_SP.M(R,T,C) / EQ_ESCOST.M(R,T) * (TM_SCALE_NRG/TM_SCALE_CST);

* Eliminate zero or non-smooth marginals in first period
LOOP(T_1(T(TT-1)),PAR_MC(R,T,C)$((PAR_MC(R,T,C)<PAR_MC(R,TT,C)*.7)$DEM(R,C)) = PAR_MC(R,TT,C)*.7);
TM_DEM(R,T,C)$((PAR_MC(R,T,C)>0)$(COM_PROJ(R,T,C)>0)$DEM(R,C)) = COM_PROJ(R,T,C);

TM_ERR('DEM') = SMAX((R,T,C)$TM_DEM(R,T,C),ABS(TM_DEM(R,T,C)-VAR_DEM.L(R,T,C))/TM_DEM(R,T,C));
TM_ERR('GDP') = SMAX((REG,T),ABS(TM_GDPGOAL(REG,T)-TM_GDP(REG,T))/TM_GDPGOAL(REG,T));


""",
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

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{ddfupd_msa()}
{writeddf_msa(arg1="DDFNEW", arg2="TM_GR")}
""",
        )
