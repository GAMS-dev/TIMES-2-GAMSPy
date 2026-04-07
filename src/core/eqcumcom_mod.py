# eqcumcom_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCUMCOM sets the cumulative limit on a commodity
# *   %1 - equation declaration type
# *   %2 - NET/PRD indicator
# *=============================================================================*
# *GaG Questions/Comments:
# * - scale both sides!!!
# * [AL] Changed to support arbitrary year range
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcumcomMod(GamsClass):
    """Translation unit for eqcumcom.mod."""

    # Instance attributes
    module_name: str = "eqcumcom_mod"
    gams_source: str = "eqcumcom.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        equation = rf"""
*$ONLISTING
    {self.env.EQ}_CUM{self.arg2}(RC(R,C),ALLYEAR,LL {self.env.SOW})$RC_CUMCOM(R,'{self.arg2}',ALLYEAR,LL,C)..

* all commodity flows within period range
               SUM(RTC_{self.arg2}(R,TT(T),C)$
"""
        if self.env.OBJ.upper() != "LIN":
            equation += "((E(T) >= YEARVAL(ALLYEAR))$(B(T) <= YEARVAL(LL))),"
        else:
            equation += (
                "((M(T)+LAGT(T) > YEARVAL(ALLYEAR))$(M(T)-LEAD(T) < YEARVAL(LL))),"
            )

        equation += "SUM(RTCS_VARC(R,T,C,S),"

        if self.env.OBJ.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += rf"""
* {self.env.VARTT}_COM{self.arg2}(R,T,C,S {self.env.SWS})
                   )
               ) / {self.env.CUCSCAL}

    ={self.arg1}=

* bound range working on
    {self.env.VAR}_CUMCOM(R,C,'{self.arg2}',ALLYEAR,LL {self.env.SOW})
    ;

$OFFLISTING

"""
        self.tc.add_gams_code(module=self, phase="run", code=equation)
