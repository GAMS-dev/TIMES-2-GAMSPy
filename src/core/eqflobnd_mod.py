# eqflobnd_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  EQFLOBND limits the flow variable at higher TS-leves
#    %1 - equation declaration type
#    %2 - bound type for %1
#    %3 - qualifier that bound exists
# =============================================================================*
# UR Questions/Comments:
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqflobndMod(GamsClass):
    """Translation unit for eqflobnd.mod."""

    # Instance attributes
    module_name: str = "eqflobnd_mod"
    gams_source: str = "eqflobnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        """
        Captures eq, r_t at registration time.
        #    arg1 - equation declaration type
        #    arg2 - bound type for arg1
        #    arg3 - qualifier that bound exists
        """
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.env.cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored_red as cal_red_func

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{self.env.eq}{self.arg1}_FLOBND(RTP_VARA({self.env.r_t},P),CG,S {self.env.swt})$(
* Make an equation of the bound if there are flow variables for commodities in CG that are strictly below S,
* ...or the tuple has been otherwise rejected for VAR bound (process is vintaged or IRE, or flow is reduced):
                                SUM(RTPCS_VARF(R,T,P,C,TS)$(TS_MAP(R,S,TS)*COM_GMAP(R,CG,C)),
                                    RS_BELOW(R,S,TS) OR FLO_BND(R,'{self.env.dflbl}',P,CG,S,'{self.arg2}')
                                   )$FLO_BND(R,T,P,CG,S,'{self.arg2}')
                                ) ..

* sum over all flows that are either at S or below it
       (SUM((COM_GMAP(R,CG,C),RTPCS_VARF(R,T,P,C,TS))$TS_MAP(R,S,TS),
* sum all the existing flows
           SUM(RTP_VINTYR(R,V,T,P),
* [UR] model reduction self.reduce is set in *.run
            (
            {cal_red_func(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim, def_rtp_ffcs=self.tc.defined("RTP_FFCS"), arg1="C", arg2="COM", arg3="TS", arg4="P", arg5="T")}

            )$RP_FLO(R,P) +

* [AL] add support for IRE
            SUM(RPC_IRE(R,P,C,IE),({self.env.var}_IRE(R,V,T,P,C,TS,IE{self.env.sow})

            {f"$(NOT RPC_AIRE(R,P,C))+({self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)" if self.env.reduce == "YES" else ""}

* apply IRE bound on net flow if group used, otherwise on sum of IMP/EXP
            )*(1-2$XPT(IE)$(NOT COM(CG))))$RP_IRE(R,P)
           )
         )

     -  FLO_BND(R,T,P,CG,S,'{self.arg2}'))${self.arg3}

  ={self.arg1}= 0;
""",
        )
