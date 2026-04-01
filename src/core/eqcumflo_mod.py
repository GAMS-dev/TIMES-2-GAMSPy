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
from collections.abc import Callable
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
        self.env.set_local("SW1", "")
        self.env.set_local("SW2", "")
        if self.env.STAGES + self.env.SCUM == "YES":
            self.env.set_scoped("SOW", "',WW'")
            self.env.set_scoped("SWT", "',SOW'")
            self.env.set_scoped("SW1", "'S_'")
            self.env.set_scoped("SW2", ",'1',SOW")

        if self.env.CAL_RED == "cal_red.red":
            from core.cal_red_red import cal_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored as cal_red_func

        self.tc.enqueue(
            self.exec1,
            self.env.EQ,
            self.env.SOW,
            self.env.OBJ,
            self.env.STAGES,
            self.env.SWSW,
            cal_red_func,
            self.env.VAR,
            self.env.VARTT,
            self.env.SWS,
            self.env.PGPRIM,
            self.env.CUFSCAL,
            self.env.SWT,
            self.env.SW1,
            self.env.SW2,
        )

    def exec1(
        self,
        EQ: str,
        SOW: str,
        OBJ: str,
        STAGES: str,
        SWSW: str,
        cal_red_func: Callable,
        VAR: str,
        VARTT: str,
        SWS: str,
        PGPRIM: str,
        CUFSCAL: str,
        SWT: str,
        SW1: str,
        SW2: str,
    ):
        equation = rf"""
*$ONLISTING
    {EQ}_CUMFLO(RPC_CUMFLO(RP(R,P),C,ALLYEAR,LL) {SOW}) ..
* all commodity/activity flows within period range
                 SUM(TT(T)$
"""
        if OBJ.upper() != "LIN":
            equation += "((E(T) >= YEARVAL(ALLYEAR))$(B(T) <= YEARVAL(LL))),"
        else:
            equation += (
                "((M(T)+LAGT(T) > YEARVAL(ALLYEAR))$(M(T)-LEAD(T) < YEARVAL(LL))),"
            )

        equation += "SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS)),"

        if OBJ.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += "* ("

        if STAGES == "YES":
            equation += f"SUM({SWSW} ("

        equation += rf"""
$                        {cal_red_func("C", "COM", "TS", "P", "T")}
                         $RP_STD(R,P) +
                         (SUM(RPC_IRE(R,P,C,IE),{VAR}_IRE(R,V,T,P,C,TS,IE{SOW}))$(NOT RPC_AIRE(R,P,C)) +
                          ({VAR}_ACT(R,V,T,P,TS{SOW})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))$RP_IRE(R,P)
"""

        if STAGES == "YES":
            equation += "))"

        equation += """
                    ))$RPC(R,P,C) +
                    SUM((RTP_VINTYR(R,V,T,P),RTP_VARA(R,T,P),PRC_TS(R,P,TS)),
"""

        if OBJ.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += rf"""
                      * {VARTT}_ACT(R,V,T,P,TS {SWS})
                    )$SAMEAS({PGPRIM},C)

                 ) / {CUFSCAL}

    =E=

* bound range working on
    {VAR}_CUMFLO(R,P,C,ALLYEAR,LL {SWT})$(MAPVAL({SW1}FLO_CUM(R,P,C,ALLYEAR,LL,'UP'{SW2})) NE 8);
    ;

$OFFLISTING
"""

        self.tc.add_gams_code(module=self, phase="run", code=equation)
