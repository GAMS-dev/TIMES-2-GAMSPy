# rpt_ext_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * CHP reporting for the IER extension
# *=============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtIer(GamsClass):
    """Translation unit for rpt_ext.ier."""

    # Instance attributes
    module_name: str = "rpt_ext_ier"
    gams_source: str = "rpt_ext.ier"

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
        if self.env.stages == "YES":
            return
        if self.env.vda == "YES":
            self.env.set_scoped("sow", ",'0'")
            self.env.set_scoped("sow_GP", ("0",))

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
 PARAMETER PAR_BPTL(R,T,P);
 PARAMETER PAR_BPTM(R,T,P);
 PARAMETER PAR_CONDL(R,T,P) //;
 PARAMETER PAR_CONDM(R,T,P) //;
 PARAMETER PAR_HEATL(R,T,P) //;
 PARAMETER PAR_HEATM(R,T,P) //;
 PARAMETER ELE_CONDL(R,YEAR,YEAR,P,C,S) //;
 PARAMETER ELE_CONDM(R,YEAR,YEAR,P,C,S) //;
 PARAMETER ELE_BPTL(R,YEAR,YEAR,P,C,TS) //;
 PARAMETER ELE_BPTM(R,YEAR,YEAR,P,C,TS) //;
""",
        )

        self.tc.enqueue(self.exec1, self.env.sow)

    def exec1(self: RptExtIer, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* PAR_ACTL(R,V,T,P,S)$ECT_CHP(R,P)                       $= PAR_ACTL(R,V,T,P,S)*ECT_INP2ELC(R,V,P);
* PAR_ACTM(R,V,T,P,S)$(PAR_ACTM(R,V,T,P,S)$ECT_CHP(R,P)) $= PAR_ACTM(R,V,T,P,S)/ECT_INP2ELC(R,V,P);

*---------------------------------------------------------------------
* Output of VAR_CAP
*---------------------------------------------------------------------

 PAR_BPTL(RTP(R,T,P))$ECT_CHP(R,P)  = SUM(RTP_CPTYR(R,V,T,P), ECT_INP2ELC(R,V,P)*COEF_CPT(R,V,T,P) * (VAR_NCAP.L(R,V,P)$T(V) + NCAP_PASTI(R,V,P)));
 PAR_BPTM(RTP(R,T,P))$ECT_CHP(R,P)  = SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P)/ECT_INP2ELC(R,V,P)* ((VAR_NCAP.M(R,V,P)/VDA_DISC(R,V))$T(V)));

 PAR_CAPL(RTP(R,T,P))$ECT_CHP(R,P)  = SUM(RTP_CPTYR(R,V,T,P), ECT_INP2ELC(R,V,P) * COEF_CPT(R,V,T,P) * (VAR_NCAP.L(R,V,P)$T(V) + NCAP_PASTI(R,V,P)));
 PAR_PASTI(RTP(R,T,P){sow})$ECT_CHP(R,P) = SUM(RTP_CPTYR(R,V,T,P), ECT_INP2ELC(R,V,P) * COEF_CPT(R,V,T,P) * NCAP_PASTI(R,V,P));
 PAR_CAPM(RTP(R,T,P))$ECT_CHP(R,P)  = SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P) /ECT_INP2ELC(R,V,P)* ((VAR_NCAP.M(R,V,P)/VDA_DISC(R,V))$T(V)));

 PAR_NCAPL(RTP(R,V,P))$ECT_CHP(R,P) = VAR_NCAP.L(R,V,P) * ECT_INP2ELC(R,V,P);
 PAR_NCAPM(RTP(R,T,P))$ECT_CHP(R,P) = (VAR_NCAP.M(R,T,P) / ECT_INP2ELC(R,T,P)/COEF_OBJINV(R,T,P))$COEF_OBJINV(R,T,P);

*---------------------------------------------------------------------
* ONLY for extraction condensing CHP plants
*---------------------------------------------------------------------

 PAR_CONDL(RTP(R,T,P))$ECT_CHP(R,P) = SUM(RTP_CPTYR(R,V,T,P), ECT_INP2CON(R,V,P)*COEF_CPT(R,V,T,P) * (VAR_NCAP.L(R,V,P)$T(V) + NCAP_PASTI(R,V,P)));
 PAR_CONDM(RTP(R,T,P))$ECT_CHP(R,P) = SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P)/ECT_INP2CON(R,V,P) * (VAR_NCAP.M(R,V,P)$T(V)));
 PAR_HEATL(RTP(R,T,P))$ECT_CHP(R,P) = SUM(RTP_CPTYR(R,V,T,P), ECT_INP2DHT(R,V,P)*COEF_CPT(R,V,T,P) * (VAR_NCAP.L(R,V,P)$T(V) + NCAP_PASTI(R,V,P)));
 PAR_HEATM(RTP(R,T,P))$ECT_CHP(R,P) = SUM(RTP_CPTYR(R,V,T,P), COEF_CPT(R,V,T,P)/ECT_INP2DHT(R,V,P) * (VAR_NCAP.M(R,V,P)$T(V)));

 ELE_BPTL(RTP_VINTYR(R,V,T,P),C,TS)$(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C)) $= SUM(ECT_DHT(R,P,COM), ECT_REH(R,V,P)*VAR_FLO.L(R,V,T,P,COM,TS));
 ELE_BPTM(RTP_VINTYR(R,V,T,P),C,TS)$(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C)) $= SUM(ECT_DHT(R,P,COM), VAR_FLO.M(R,V,T,P,COM,TS)/ECT_REH(R,V,P));
 ELE_CONDL(RTP_VINTYR(R,V,T,P),C,TS)$(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C)) = VAR_FLO.L(R,V,T,P,C,TS) - SUM(ECT_DHT(R,P,COM), ECT_REH(R,V,P)*VAR_FLO.L(R,V,T,P,COM,TS));
 ELE_CONDM(RTP_VINTYR(R,V,T,P),C,TS)$(RTPCS_VARF(R,T,P,C,TS)$ECT_ELC(R,P,C)) = VAR_FLO.M(R,V,T,P,C,TS) - SUM(ECT_DHT(R,P,COM), VAR_FLO.M(R,V,T,P,COM,TS)/ECT_REH(R,V,P));
""",
        )
