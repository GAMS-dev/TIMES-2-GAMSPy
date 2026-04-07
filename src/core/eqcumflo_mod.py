# eqcumflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCUMFLO sets the cumulative upper limit on a flow or activity
# *   %1 - equation declaration type
# *=============================================================================*
# *AL Questions/Comments:
# * - scale both sides
# * - support arbitrary year range
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqcumfloMod(GamsClass):
    """Translation unit for eqcumflo.mod."""

    # Instance attributes
    module_name: str = "eqcumflo_mod"
    gams_source: str = "eqcumflo.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.env.set_local("sw1", "")
        self.env.set_local("sw2", "")
        if self.env.STAGES + self.env.SCUM == "YES":
            self.env.set_scoped("sow", "',WW'")
            self.env.set_scoped("swt", "',SOW'")
            self.env.set_scoped("sw1", "'S_'")
            self.env.set_scoped("sw2", ",'1',SOW")

        if self.env.CAL_RED == "cal_red.red":
            from core.cal_red_red import cal_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored as cal_red_func

        equation = rf"""
*$ONLISTING
    {self.env.EQ}_CUMFLO(RPC_CUMFLO(RP(R,P),C,ALLYEAR,LL) {self.env.SOW}) ..
* all commodity/activity flows within period range
                 SUM(TT(T)$
"""
        if self.env.OBJ.upper() != "LIN":
            equation += "((E(T) >= YEARVAL(ALLYEAR))$(B(T) <= YEARVAL(LL))),"
        else:
            equation += (
                "((M(T)+LAGT(T) > YEARVAL(ALLYEAR))$(M(T)-LEAD(T) < YEARVAL(LL))),"
            )

        equation += "SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS)),"

        if self.env.OBJ.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += "* ("

        if self.env.STAGES == "YES":
            equation += f"SUM({self.env.SWSW} ("

        equation += rf"""
{cal_red_func("C", "COM", "TS", "P", "T")}
                         $RP_STD(R,P) +
                         (SUM(RPC_IRE(R,P,C,IE),{self.env.VAR}_IRE(R,V,T,P,C,TS,IE{self.env.SOW}))$(NOT RPC_AIRE(R,P,C)) +
                          ({self.env.VAR}_ACT(R,V,T,P,TS{self.env.SOW})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))$RP_IRE(R,P)
"""

        if self.env.STAGES == "YES":
            equation += "))"

        equation += """
                    ))$RPC(R,P,C) +
                    SUM((RTP_VINTYR(R,V,T,P),RTP_VARA(R,T,P),PRC_TS(R,P,TS)),
"""

        if self.env.OBJ.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += rf"""
                      * {self.env.VARTT}_ACT(R,V,T,P,TS {self.env.SWS})
                    )$SAMEAS({self.env.PGPRIM},C)

                 ) / {self.env.CUFSCAL}

    =E=

* bound range working on
    {self.env.VAR}_CUMFLO(R,P,C,ALLYEAR,LL {self.env.SWT})$(MAPVAL({self.env.SW1}FLO_CUM(R,P,C,ALLYEAR,LL,'UP'{self.env.SW2})) NE 8);
    ;

$OFFLISTING
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)
