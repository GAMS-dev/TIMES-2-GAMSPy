# cal_cap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_CAP the code for capacity dependent commodity flows in EQ_COMxxx
# *   arg1 - IN/OUT indicator
# *   arg2 - I/O indicator
# *   arg3 - cost expression for EQOBJVAR
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_CPT derived in COEF_CPT.MOD

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CalCapMod(GamsClass):  # FilenameExt
    """Translation unit for cal_cap.mod."""

    # Instance attributes
    module_name: str = "cal_cap_mod"
    gams_source: str = "cal_cap.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self):
        return rf"""
         SUM(RTP_CPTYR(R,V,T,P)$NCAP_COM(R,V,P,C,'{self.arg1}'),
*V05b 980902 - need to apply seasonal fraction
             COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,'{self.arg1}') * G_YRFR(R,S) *
             {self.arg3}
             ({self.env.varv}_NCAP{self.arg}(R,V,P {self.env.sws})$T(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V) {self.env.rcapsub}) *
* Adjust for lagged commodity flows
             (1 + COEF_CIO(R,V,T,P,C,'{self.arg1}'))
         ) +
* CAL_NCOM: the term associated with invest/decommission commodities in the EQ_COMxxx
         SUM(RPC_CAPFLO(R,V,P,C)$COEF_{self.arg2}COM(R,V,T,P,C), COEF_{self.arg2}COM(R,V,T,P,C) *
             {self.arg3}
             G_YRFR(R,S) * ({self.env.varv}_NCAP{self.arg4}(R,V,P {self.env.sws})$T(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V))
         )
"""
