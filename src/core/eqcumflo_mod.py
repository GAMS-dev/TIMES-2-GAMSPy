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
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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
        g = self.tc
        self.env.set_local("sw1", "")
        self.env.set_local("sw2", "")
        if self.env.stages + self.env.scum == "YES":
            self.env.set_scoped("sow", "',WW'")
            self.env.set_scoped("sow_GP", (g.ww,))
            self.env.set_scoped("swt", "',SOW'")
            self.env.set_scoped("sw1", "'S_'")
            self.env.set_scoped("sw2", ",'1',SOW")

        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red as cal_red_func

        equation = rf"""
*$ONLISTING
    {self.env.eq}_CUMFLO(RPC_CUMFLO(RP(R,P),C,ALLYEAR,LL) {self.env.sow}) ..
* all commodity/activity flows within period range
                 SUM(TT(T)$
"""
        if self.env.obj.upper() != "LIN":
            equation += "((E(T) >= YEARVAL(ALLYEAR))$(B(T) <= YEARVAL(LL))),"
        else:
            equation += (
                "((M(T)+LAGT(T) > YEARVAL(ALLYEAR))$(M(T)-LEAD(T) < YEARVAL(LL))),"
            )

        equation += "SUM((RTP_VINTYR(R,V,T,P),RTPCS_VARF(R,T,P,C,TS)),"

        if self.env.obj.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += "* ("

        if self.env.stages == "YES":
            equation += f"SUM({self.env.swsw} ("

        equation += rf"""
{cal_red_func(arg1="C", arg2="COM", arg3="TS", arg4="P", arg5="T", def_rtp_ffcs=self.tc.defined("RTP_FFCS"), var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim)}
                         $RP_STD(R,P) +
                         (SUM(RPC_IRE(R,P,C,IE),{self.env.var}_IRE(R,V,T,P,C,TS,IE{self.env.sow}))$(NOT RPC_AIRE(R,P,C)) +
                          ({self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))$RP_IRE(R,P)
"""

        if self.env.stages == "YES":
            equation += "))"

        equation += """
                    ))$RPC(R,P,C) +
                    SUM((RTP_VINTYR(R,V,T,P),RTP_VARA(R,T,P),PRC_TS(R,P,TS)),
"""

        if self.env.obj.upper() != "LIN":
            equation += "MAX(0,MIN(E(T),YEARVAL(LL))-MAX(B(T),YEARVAL(ALLYEAR))+1)"
        else:
            equation += "SUM(TPULSEYR(T,YEAR)$((ORD(YEAR) >= ORD(ALLYEAR))$(ORD(YEAR) <= ORD(LL))),TPULSE(T,YEAR))"

        equation += rf"""
                      * {self.env.vartt}_ACT(R,V,T,P,TS {self.env.sws})
                    )$SAMEAS('{self.env.pgprim}',C)

                 ) / {self.env.cufscal}

    =E=

* bound range working on
    {self.env.var}_CUMFLO(R,P,C,ALLYEAR,LL {self.env.swt})$(MAPVAL({self.env.sw1}FLO_CUM(R,P,C,ALLYEAR,LL,'UP'{self.env.sw2})) NE 8);
    ;

$OFFLISTING
"""

        self.tc.add_gams_code(module=self, phase="init", code=equation)
