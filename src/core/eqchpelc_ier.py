# eqchpelc_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * Equation bounding the electricity production of extraction condensing CHP plant
# * by the available condensing resp. backpressure capacity
# *   arg1 - =L= or =E= qualifier
# *   arg2 - UP of FX bound for ECT_AFCON/ECT_AFCHP

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqchpelcIer(GamsClass):
    """Translation unit for eqchpelc.ier."""

    # Instance attributes
    module_name: str = "eqchpelc_ier"
    gams_source: str = "eqchpelc.ier"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        self.comp1(
            arg1=self.arg1,
            arg2=self.arg2,
            swx=self.env.swx,
            swtx=self.env.swtx,
            reduce=self.env.reduce,
            cal_red=self.env.cal_red,
            varm=self.env.varm,
            sws=self.env.sws,
            varv=self.env.varv,
            pgprim=self.env.pgprim,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            sow=self.env.sow,
            var=self.env.var,
        )

    def comp1(
        self: EqchpelcIer,
        arg1: str,
        arg2: str,
        swx: str,
        swtx: str,
        reduce: str,
        cal_red: str,
        varm: str,
        sws: str,
        varv: str,
        pgprim: str,
        def_rtp_ffcs: bool,
        sow: str,
        var: str,
    ) -> None:
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red as cal_red_func
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red = cal_red_func(
            arg1="C",
            arg2="COM",
            arg3="TS",
            arg4="P",
            arg5="T",
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
            sow=sow,
            var=var,
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
EQ{arg1}_CHPCON(RTP_VINTYR(R,V,T,P){swx})$({swtx}ECT_AFCON(R,T,P,'{arg2}')*SUM(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C),1)$ECT_CHP(R,P))..

  SUM(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C),
* [UR] model reduction {reduce} is set in *.run
{include_cal_red}
   )
-
  SUM(RTPCS_VARF(R,T,P,C,TS)$ECT_DHT(R,P,C), ECT_REH(R,T,P)*
* [UR] model reduction {reduce} is set in *.run
{include_cal_red}
   )

  ={arg1}=

* Case I if AFpcg
* process is not vintaged
        SUM(RTP_CPTYR(R,MODLYEAR(K),T,P),
             ECT_AFCON(R,T,P,'{arg2}') * ECT_INP2CON(R,T,P) * COEF_CPT(R,K,T,P) * PRC_CAPACT(R,P) * ({varm}_NCAP(R,K,P {sws})$T(K) + NCAP_PASTI(R,K,P))
            )$(NOT PRC_VINT(R,P)) +

* process is vintaged
        (ECT_AFCON(R,T,P,'{arg2}') * ECT_INP2CON(R,T,P) * COEF_CPT(R,V,T,P) * PRC_CAPACT(R,P) * ({varv}_NCAP(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P))
        )$PRC_VINT(R,P)
;

EQ{arg1}_CHPBPT(RTP_VINTYR(R,V,T,P){swx})$({swtx}ECT_AFBPT(R,T,P,'{arg2}')*SUM(RTPCS_VARF(R,T,P,C,TS)$ECT_DHT(R,P,C),1)$ECT_CHP(R,P))..

  SUM(RTPCS_VARF(R,T,P,C,TS)$ECT_DHT(R,P,C), ECT_REH(R,T,P)*
* [UR] model reduction {reduce} is set in *.run
{include_cal_red}
   )

  ={arg1}=

* Case I if AFpcg
* process is not vintaged
        SUM(RTP_CPTYR(R,MODLYEAR(K),T,P),
             ECT_AFBPT(R,T,P,'{arg2}') * ECT_INP2ELC(R,T,P) * COEF_CPT(R,K,T,P) * PRC_CAPACT(R,P) * ({varm}_NCAP(R,K,P {sws})$T(K) + NCAP_PASTI(R,K,P))
            )$(NOT PRC_VINT(R,P)) +

* process is vintaged
        (ECT_AFBPT(R,T,P,'{arg2}') * ECT_INP2ELC(R,T,P) * COEF_CPT(R,V,T,P) * PRC_CAPACT(R,P) * ({varv}_NCAP(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P))
        )$PRC_VINT(R,P)
;
""",
        )
