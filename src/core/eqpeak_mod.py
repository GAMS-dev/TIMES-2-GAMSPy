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
from typing import TYPE_CHECKING

from core.cal_cap_mod import cal_cap_mod
from core.cal_fflo_mod import cal_fflo_mod
from core.cal_ire_mod import cal_ire_mod
from core.cal_stgn_mod import cal_stgn_mod
from core.eqpk_ect_ier import eqpk_ect_ier

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self.env.set_scoped("swstmp", self.env.sws)
        if self.env.stages.upper() == "YES":
            self.env.set_local(
                "sws",
                "PROD(SW_MAP(T,SOW,J,WW)$S_COM_PROJ(R,T,C,J,WW),S_COM_PROJ(R,T,C,J,WW))*",
            )

        self.comp1(
            eq=self.env.eq,
            r_t=self.env.r_t,
            swt=self.env.swt,
            varv=self.env.varv,
            swstmp=self.env.swstmp,
            rcapsub=self.env.rcapsub,
            peakchp=self.env.peakchp,
            sws=self.env.sws,
            var=self.env.var,
            sow=self.env.sow,
            mx=self.env.mx,
            condition=self.env.timesed == "YES",
            shff=self.env.shff,
            is_rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            is_ireauxbal=self.env.is_set("ireauxbal"),
            reduce=self.env.reduce,
        )

    def comp1(
        self: EqpeakMod,
        eq: str,
        r_t: str,
        swt: str,
        varv: str,
        swstmp: str,
        rcapsub: str,
        peakchp: str,
        sws: str,
        var: str,
        sow: str,
        mx: str,
        condition: bool,
        shff: str,
        is_rtp_ffcs_defined: bool,
        is_ireauxbal: bool,
        reduce: str,
    ):
        include_cal_ire_1 = cal_ire_mod(
            var=var,
            sow=sow,
            shff=shff,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            is_ireauxbal=is_ireauxbal,
            arg1="IMP",
            arg2="OUT",
            arg3="IE",
            arg4="*NCAP_PKCNT(R,V,P,S)",
            arg5="-",
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
            arg4="*(-NCAP_PKCNT(R,V,P,S)/COM_IE(R,T,C,S))$(COM_IE(R,T,C,S)>0)",
            arg5="-",
            # TODO is the splitting here correct?
            arg6="PRC_PKNO(",
            arg7=")",
        )
        include_cal_stgn_1 = cal_stgn_mod(
            var=var,
            sow=sow,
            arg1="OUT",
            arg2="IN",
            arg3="*STG_EFF(R,V,P)",
            arg4="",
            arg5="(NOT PRC_NSTTS(R,P,TS))",
            arg6="*(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))$RPC_PKF(R,P,C)",
        )
        include_cal_fflo_1 = cal_fflo_mod(
            reduce=reduce,
            shff=shff,
            sow=sow,
            var=var,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            arg1="OUT",
            # arg2="O", in cal_fflo_mod stated as no longer used
            arg3="*(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))",
            arg4="$RPC_PKF(R,P,C)",
        )
        include_eqpk_ect = ""
        # from prep_ext.ier
        if peakchp == "eqpk_ect.ier":
            include_eqpk_ect = eqpk_ect_ier(
                varv=varv,
                sws=sws,
                reduce=reduce,
                shff=shff,
                sow=sow,
                var=var,
                is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            )
        include_cal_fflo_2 = cal_fflo_mod(
            reduce=reduce,
            shff=shff,
            sow=sow,
            var=var,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            arg1="IN",
            # arg2="I", in cal_fflo_mod stated as no longer used
            arg3="*FLO_PKCOI(R,T,P,C,TS)",
            arg4="",
        )
        include_cal_ire_3 = cal_ire_mod(
            var=var,
            sow=sow,
            shff=shff,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            is_ireauxbal=is_ireauxbal,
            arg1="EXP",
            arg2="IN",
            arg3="IE",
            arg4="*FLO_PKCOI(R,T,P,C,TS)",
            arg5="-",
        )
        include_cal_cap = cal_cap_mod(
            varv=varv,
            sws=sws,
            rcapsub=rcapsub,
            arg1="IN",
            arg2="I",
            arg3="1$(NOT PRC_PKNO(R,P))*",
        )
        include_cal_stgn_2 = cal_stgn_mod(
            var=var,
            sow=sow,
            arg1="IN",
            arg2="OUT",
            arg3="",
            arg4="STG_EFF(R,V,P)*(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))*",
            arg5="((NOT PRC_MAP(R,'NST',P))+PRC_NSTTS(R,P,TS))",
            arg6="$RPC_PKF(R,P,C)",
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {eq}_PEAK({r_t},CG2,RTS(SL){swt})$(SUM(COM_GMAP(R,CG2,C)$RTC(R,T,C),1)$COM_PKTS(R,CG2,SL)) ..

     SUM((COM_GMAP(R,CG2,C),COM_TS(R,C,S))$RS_FR(R,SL,S),
       RS_FR(R,SL,S) *
* Apply maximum reserve among CG2 and C
       (1/(1+MAX(SUM(COM(CG2),COM_PKRSV(R,T,COM)),COM_PKRSV(R,T,C))))*COM_IE(R,T,C,S)*

       (SUM(RPC_PKC(R,P,C), G_YRFR(R,S) * PRC_CAPACT(R,P) *
           SUM(V$COEF_VNT(R,T,P,V),COEF_VNT(R,T,P,V)*PRC_ACTFLO(R,V,P,C)*NCAP_PKCNT(R,V,P,S)*
               ({varv}_NCAP(R,V,P {swstmp})$MILESTONYR(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V) {rcapsub}))
           ) +

*
* production
*
*   inter-regional trade to region; processes with PKNO+PKCNT contribute by net imports
{include_cal_ire_1}
{include_cal_ire_2}
           (

*GG*PK no multiplier
* [UR] 25.04.2003 added NCAP_PKCNT multiplier to turn off contribution by setting NCAP_PKCNT to zero
* allow using PKNO to switch process to production-based peak contribution (contributes only if PKCNT set by user)

*   storage
{include_cal_stgn_1}

*   individual flows
{include_cal_fflo_1}

           0)

* [UR]: 04/22/2003: adjustment for extraction condensing CHP plants
{include_eqpk_ect}
      ))

      =G=

     SUM((COM_GMAP(R,CG2,C),COM_TS(R,C,S))$RS_FR(R,SL,S),
         RS_FR(R,SL,S) *
* Apply maximum flexibility among CG2 and C
         (1+MAX(SUM(COM(CG2),COM_PKFLX(R,T,COM,SL)),COM_PKFLX(R,T,C,S)))*
         (
*
* consumption
*
*GG*PK pass TS as timeslice

*   individual flows
{include_cal_fflo_2}

*   inter-regional trade from region
{include_cal_ire_3}

* capacity related commodity flows
*   fixed commodity associated with installed capacity or investment
{include_cal_cap}
           +
*   storage
{include_cal_stgn_2}

*   blending
           SUM(BLE_OPR(R,BLE,OPR)$(BLE_INP(R,BLE,C)*BLE_TP(R,T,BLE)),G_YRFR(R,S)*(1+RTCS_FR(R,T,C,S,'ANNUAL'))*BL_INP(R,BLE,C)*PEAKDA_BL(R,BLE,T)*{var}_BLND(R,T,BLE,OPR {sow})) +

*   demand projection
      (({sws} COM_PROJ(R,T,C)$(NOT RD_NLP(R,C)) +{var}_DEM(R,T,C{sow})$RD_NLP(R,C) +SUM(RD_AGG(R,COM),RD_SHAR(R,T,COM,C)*{var}_COMPRD(R,T,COM,'ANNUAL'{sow}))) * COM_FR{mx}(R,T,C,S))$DEM(R,C) +

*   include the elasticity variables
{f"SUM(RCJ(R,C,J,BDNEQ(BD))$COM_ELAST(R,T,C,S,BD),-BDSIG(BD)*{var}_ELAST(R,T,C,S,J,BD {sow})) +" if condition else ""}

       0)) ;
""",
        )
