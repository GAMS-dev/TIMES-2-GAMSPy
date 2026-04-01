# eqcpt_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCPT.MOD capacity transfer equation
# *  - %1 = equation type when VALIDATE
# *  - %2 = equation name adj (L) when VALIDATE (for DMDs in MARKAL)
# *  - %3 = control qualifier
# *  - %4 = RHS constant or VAR_CAP
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_CPT established in COEF_CPT.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcptMod(GamsClass):
    """Translation unit for eqcpt.mod."""

    # Instance attributes
    module_name: str = "eqcpt_mod"
    gams_source: str = "eqcpt.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec1,
            self.env.EQ,
            self.arg2,
            self.env.SWT,
            self.arg3,
            self.env.sow,
            self.arg4,
            self.arg1,
            self.env.VARV,
            self.env.SWS,
            self.env.RCAPSUB,
        )

    def exec1(
        self,
        EQ: str,
        arg2: str,
        SWT: str,
        arg3: str,
        sow: str,
        arg4: str,
        arg1: str,
        VARV: str,
        SWS: str,
        RCAPSUB: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*GG*V0.6a_3+ check whether used in UserConstraint
*$onlisting

  {EQ}{arg2}_CPT(RTP(R,T,P) {SWT})$({arg3}) ..

*  VAR_CAP(r,t,p {sow}) or CAP_BND(r,t,p,bd):
       {arg4}

  ={arg1}=

      SUM(V$COEF_CPT(R,V,T,P), COEF_CPT(R,V,T,P) *
          ({VARV}_NCAP(R,V,P {SWS})$MILESTONYR(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V){RCAPSUB}))
  ;
*$offlisting

""",
        )
