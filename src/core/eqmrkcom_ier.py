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


class EqmrkcomIer(GamsClass):
    """Translation unit for eqmrkcom.ier."""

    # Instance attributes
    module_name: str = "eqmrkcom_ier"
    gams_source: str = "eqmrkcom.ier"

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
        self.comp1()

    def comp1(
        self: EqmrkcomIer,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        swx: str,
        swtx: str,
        var: str,
        sow: str,
        cal_red: str,
        pgprim: str,
        def_rtp_ffcs: str,
        shff: str,
        is_rtp_ffcs_defined: str,
        is_ireauxbal: str,
        reduce: str,
        varv: str,
        sws: str,
        rcapsub: str,
    ):
        include_cal_fflo_1 = cal_fflo_mod(
            reduce=reduce,
            shff=shff,
            sow=sow,
            var=var,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            arg1="OUT",
            # arg2="O", in cal_fflo_mod stated as no longer used
        )

        include_cal_ire_1 = cal_ire_mod(
            var=var,
            sow=sow,
            shff=shff,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            is_ireauxbal=is_ireauxbal,
            arg1="IMP",
            arg2="OUT",
            arg3="IE",
        )

        include_cal_stgn_1 = cal_stgn_mod(
            var=var,
            sow=sow,
            arg1="OUT",
            arg2="IN",
            arg3="*STG_EFF(R,V,P)",
            arg4="",
            arg5="(NOT PRC_NSTTS(R,P,TS))",
        )

        include_cal_cap_1 = cal_cap_mod(
            varv=varv,
            sws=sws,
            rcapsub=rcapsub,
            arg1="OUT",
            arg2="O",
        )

        include_cal_fflo_2 = cal_fflo_mod(
            reduce=reduce,
            shff=shff,
            sow=sow,
            var=var,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            arg1="IN",
            # arg2="I", in cal_fflo_mod stated as no longer used
        )

        include_cal_ire_2 = cal_ire_mod(
            var=var,
            sow=sow,
            shff=shff,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            is_ireauxbal=is_ireauxbal,
            arg1="EXP",
            arg2="IN",
            arg3="IE",
        )

        include_cal_stgn_2 = cal_stgn_mod(
            var=var,
            sow=sow,
            arg1="IN",
            arg2="OUT",
            arg3="",
            arg4="STG_EFF(R,V,P)*",
            arg5="((NOT PRC_MAP(R,'NST',P))+PRC_NSTTS(R,P,TS))",
        )

        include_cal_cap_2 = cal_cap_mod(
            varv=varv,
            sws=sws,
            rcapsub=rcapsub,
            arg1="IN",
            arg2="I",
        )

        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red as cal_red_func
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red = cal_red_func(
            arg1="C",
            arg2="COM",
            arg3="S",
            arg4="PRC",
            arg5="T",
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
            shff=shff,
            sow=sow,
            var=var,
        )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  EQ{arg2}_MRK{arg4}(RTP(R,T,PRC),C,S {swx})$({swtx}TOP(R,PRC,C,'{arg5}')*FLO_MRK{
                arg4
            }(R,T,PRC,C,S,'{arg3}')) ..

  FLO_MRK{arg4}(R,T,PRC,C,S,'{arg3}') *

$IF '{arg4}'=='CON' $GOTO CONS
{
                (
                    rf'''
  (

* production of commodity
* -----------------------
      (
* individual flows
{include_cal_fflo_1}

*V07_1b blending flows
        SUM(OPR$BLE_OPR(R,C,OPR),
            RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * BLE_BAL(R,T,C,OPR) * {var}_BLND(R,T,C,OPR {sow})
        ) +
*V07_1b emissions due to blending operations
        SUM(BLE_ENV(R,C,BLE,OPR), RS_FR(R,S,'ANNUAL') * ENV_BL(R,C,BLE,OPR,T) * {var}_BLND(R,T,BLE,OPR {sow})
        ) +

* inter-regional trade to region
{include_cal_ire_1}

* storage
{include_cal_stgn_1}

* capacity related commodity flows
{include_cal_cap_1}
      )
  )

'''
                )
                if not arg4 == "CON"
                else (
                    rf'''
  (
* consumption of commodity
* ------------------------

* individual flows
{include_cal_fflo_2}

*V07_1a blending flows
      SUM(BLE_TP(R,T,BLE)$BLE_OPR(R,BLE,C),
         RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * {var}_BLND(R,T,BLE,C {sow})
      ) +
      SUM(BLE_OPR(R,BLE,OPR)$(BLE_INP(R,BLE,C) * BLE_TP(R,T,BLE)),
         RS_FR(R,S,'ANNUAL')*(1+RTCS_FR(R,T,C,S,'ANNUAL')) * BL_INP(R,BLE,C) + {
                        var
                    }_BLND(R,T,BLE,OPR {sow})
      ) +

* inter-regional trade from region
{include_cal_ire_2}

* storage
{include_cal_stgn_2}

* capacity related commodity flows
{include_cal_cap_2}

* include the elasticity variables
      - SUM(RCJ(R,C,J,BDNEQ(BD))$COM_ELAST(R,T,C,S,BD),BDSIG(BD)*{
                        var
                    }_ELAST(R,T,C,S,J,BD {sow}))

  )
'''
                )
            }

  ={arg2}=

  SUM(RTPCS_VARF(R,T,PRC,C,TS)$(TOP(R,PRC,C,'{arg5}')$RP_FLO(R,PRC)),
     SUM(RTP_VINTYR(R,V,T,PRC),
{include_cal_red}
         *RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))
     )
  )
  ;
""",
        )
