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
from typing import TYPE_CHECKING

from core.cal_cap_mod import cal_cap_mod
from core.cal_fflo_mod import cal_fflo_mod
from core.cal_ire_mod import cal_ire_mod
from core.cal_stgn_mod import cal_stgn_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
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
        if self.arg4 == "BAL":
            if self.env.stages.upper() == "YES":
                self.env.set_local(
                    "sws",
                    "PROD(SW_MAP(T,SOW,J,WW)$S_COM_PROJ(R,T,C,J,WW),S_COM_PROJ(R,T,C,J,WW))*",
                )

        self.define_equation(
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            eq=self.env.eq,
            r_t=self.env.r_t,
            swt=self.env.swt,
            var=self.env.var,
            sow=self.env.sow,
            sws=self.env.sws,
            mx=self.env.mx,
            condition1=self.arg4 == "BAL",
            condition2=self.arg4 == "PRD",
            condition3=self.env.timesed == "YES",
            condition4=f"{self.arg4},{self.arg3}" == "BALFX",
        )

    def define_equation(
        self: EqcombalMod,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        eq: str,
        r_t: str,
        swt: str,
        var: str,
        sow: str,
        sws: str,
        mx: str,
        condition1: bool,
        condition2: bool,
        condition3: bool,
        condition4: bool,
    ):
        include_cal_fflo_1 = cal_fflo_mod(
            reduce=self.env.reduce,
            shff=self.env.shff,
            sow=self.env.sow,
            var=self.env.var,
            pgprim=self.env.pgprim,
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            arg1="OUT",
            arg3="",
            arg4="",
        )
        include_cal_ire_1 = cal_ire_mod(
            var=self.env.var,
            sow=self.env.sow,
            shff=self.env.shff,
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            is_ireauxbal=self.env.is_set("ireauxbal"),
            arg1="IMP",
            arg2="OUT",
            arg3="IE",
            arg4="",
            arg5="",
            arg6="",
            arg7="",
        )
        include_cal_stgn_1 = cal_stgn_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1="OUT",
            arg2="IN",
            arg3="*STG_EFF(R,V,P)",
            arg4="",
            arg5="(NOT PRC_NSTTS(R,P,TS))",
        )
        include_cal_cap_1 = cal_cap_mod(
            varv=self.env.varv,
            sws=self.env.sws,
            rcapsub=self.env.rcapsub,
            arg1="OUT",
            arg2="O",
        )
        include_cal_fflo_2 = cal_fflo_mod(
            reduce=self.env.reduce,
            shff=self.env.shff,
            sow=self.env.sow,
            var=self.env.var,
            pgprim=self.env.pgprim,
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            arg1="IN",
            arg3="",
            arg4="",
        )
        include_cal_ire_2 = cal_ire_mod(
            var=self.env.var,
            sow=self.env.sow,
            shff=self.env.shff,
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            is_ireauxbal=self.env.is_set("ireauxbal"),
            arg1="EXP",
            arg2="IN",
            arg3="IE",
            arg4="",
            arg5="",
            arg6="",
            arg7="",
        )
        include_cal_stgn_2 = cal_stgn_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1="IN",
            arg2="OUT",
            arg3="",
            arg4="STG_EFF(R,V,P)*",
            arg5="((NOT PRC_MAP(R,'NST',P))+PRC_NSTTS(R,P,TS))",
        )
        include_cal_cap_2 = cal_cap_mod(
            varv=self.env.varv,
            sws=self.env.sws,
            rcapsub=self.env.rcapsub,
            arg1="IN",
            arg2="I",
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {eq}{arg2}_COM{arg4}({r_t},C,S {swt})$(RCS_COM{arg4}(R,T,C,S,'{arg3}') {arg5}) ..
*
* production
*
   (
      (

* individual flows
{include_cal_fflo_1}

*V07_1b blending flows
  SUM(BLE_OPR(R,C,OPR),
    RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * BLE_BAL(R,T,C,OPR) * {
                var
            }_BLND(R,T,C,OPR {sow})
  ) +
*V07_1b emissions due to blending operations
  SUM(BLE_ENV(R,C,BLE,OPR), RS_FR(R,S,'ANNUAL') * ENV_BL(R,C,BLE,OPR,T) * {
                var
            }_BLND(R,T,BLE,OPR {sow})
  ) +

*   inter-regional trade to region
*V0.9 022100 - exports could also produce aux
{include_cal_ire_1}

*   storage
{include_cal_stgn_1}

* (+25-May-2005) Add commodity aggregation to production side
  SUM(COM$COM_AGG(R,T,COM,C), COM_AGG(R,T,COM,C) *
    SUM(RTCS_VARC(R,T,COM,TS)$RS_TREE(R,S,TS),RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))*
      ({var}_COMNET(R,T,COM,TS {sow})$RC_AGP(R,COM,'LO') + {var}_COMPRD(R,T,COM,TS {
                sow
            })$RC_AGP(R,COM,'FX')))) +

* capacity related commodity flows
* fixed commodity associated with installed capacity or retirement
{include_cal_cap_1}

* apply commodity infastructure efficiency
      )  *  COM_IE(R,T,C,S)

* If production is summed into variable, use it directly
{
                f")$(NOT RHS_COMPRD(R,T,C,S)) + {var}_COMPRD(R,T,C,S {sow})$(RHS_COMPRD(R,T,C,S)"
                if condition1
                else ""
            }
   )

*
* consumption
*
* when doing FLO then need NET otherwise only want production component
{
                (
                    rf'''
* include the elasticity variables (moved to consumption side)
{f"+ SUM(RCJ(R,C,J,BDNEQ(BD))$COM_ELAST(R,T,C,S,BD),BDSIG(BD)*{var}_ELAST(R,T,C,S,J,BD {sow}))" if condition3 else ""}

    - (

* individual flows
{include_cal_fflo_2}

*V07_1a blending flows
  SUM(BLE_TP(R,T,BLE)$BLE_OPR(R,BLE,C),
    RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * {var}_BLND(R,T,BLE,C {sow})
  ) +
  SUM(BLE_OPR(R,BLE,OPR)$(BLE_INP(R,BLE,C) * BLE_TP(R,T,BLE)),
    RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * BL_INP(R,BLE,C) * {var}_BLND(R,T,BLE,OPR {sow})
  ) +

*   inter-regional trade from region
*V0.9 022100 - imports could also require aux
{include_cal_ire_2}

*   storage
{include_cal_stgn_2}

* capacity related commodity flows
* fixed commodity associated with installed capacity or investment
{include_cal_cap_2}

      )
'''
                )
                if not condition2
                else ""
            }

      ={arg2}=

{
                (
                    rf'''
*    production bound/cost/tax/sub/cum
          {var}_COMPRD(R,T,C,S {sow})$RHS_COMPRD(R,T,C,S)
{f"+(SUM(RCJ(R,COM,J,BD)$MI_DMAS(R,C,COM),(DDF_PREF(R,T,COM)*(MI_AGC(R,T,C,COM,J,BD)-1)+RD_SHAR(R,T,COM,C))*BDSIG(BD)*SUM(RTCS_VARC(R,T,COM,TS),{var}_ELAST(R,T,COM,TS,J,BD{sow})))-{var}_COMPRD(R,T,C,S {sow}))$(COM_ELAST(R,T,C,S,'N')>0)$RD_AGG(R,C)" if condition3 else ""}
'''
                )
                if not condition1
                else (
                    rf'''
*    set the RHS according to the type of equation and/or commodity net bound/cost/tax/sub/cum
{f"{var}_COMNET(R,T,C,S {sow})$RHS_COMBAL(R,T,C,S) +" if condition4 else ""}

*    demand projection
      (({sws} COM_PROJ(R,T,C)$(NOT RD_NLP(R,C)) +{var}_DEM(R,T,C{sow})$RD_NLP(R,C) +SUM(MI_DMAS(RD_AGG(R,COM),C),RD_SHAR(R,T,COM,C)*{var}_COMPRD(R,T,COM,'ANNUAL'{sow}))) * COM_FR{mx}(R,T,C,S))$DEM(R,C)

'''
                )
            }
     ;
""",
        )
