# cal_ire_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_IRE the code associated with the inter-region trade variable in EQ_COMxxx
# *   arg1 - IMPort/EXPort indicator
# *   arg2 - IN/OUT nature of the aux/emissions
# *   arg3 - IE or ''
# *   arg4 - * Peak multiplier
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.powerflo_vda import PowerfloVda

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CalIreMod(GamsClass):
    """Translation unit for cal_ire.mod."""

    # Instance attributes
    module_name: str = "cal_ire_mod"
    gams_source: str = "cal_ire.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.compile()

    def compile(self):
        if self.tc.defined("RTP_FFCS"):
            self.env.set_scoped("mx", f"({self.env.shff}S(R,V,P,C,C{self.env.sow}))*")

        # *V0.9 022100 - handle the fact that called 2x for aux
        self.env.set_scoped("ie", f"{self.arg3}")
        if self.env.ie == "":
            self.env.set_scoped("ie", f"'{self.env.arg1}'")

        help_str = r""
        if f"{self.arg1},{self.arg2}" in ["EXPOUT", "IMPIN"]:
            pass
        else:
            help_str += rf"""
* actual exchange
*V05c 981016 - change RTPCS_VARFs to ts
         SUM((RPC_IRE({self.arg6}R,P{self.arg7},C,'{self.arg1}'),RTP_VNTBYR(R,T,P,V)),
             SUM(RTPCS_VARF(R,T,P,C,TS)$RS_FR(R,S,TS),
                 ({self.env.var}_IRE(R,V,T,P,C,TS,'{self.arg1}'{self.env.sow})$(NOT RPC_AIRE(R,P,C))+({self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)
                 ){self.arg4} * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS)))
         ) +
"""
        if self.env.is_set("ireauxbal"):
            # take arg1 from powerflow.vda since if this is called its always IREAUX
            include_powerflow = self.include(
                PowerfloVda(
                    self.tc,
                    self.env,
                    arg1="IREAUX",
                    arg2=self.arg2,
                    arg3=self.arg5,
                )
            )
            help_str += include_powerflow

        # AUXONLY
        # *V0.5b handle auxiliary commodity flows too
        # *** NOTE: assumes that attribute at the same level as the variable!!
        # *V0.9 022100 - do IN/OUT explicitly

        help_str += rf"""
         SUM((RPC_IRE({self.arg6}R,P{self.arg7},COM,{self.env.ie}),RTPCS_VARF(R,T,P,COM,TS))$(IRE_FLOSUM(R,T,P,COM,TS,{self.env.ie},C,'{self.arg2}')$RS_FR(R,S,TS)),
             IRE_FLOSUM(R,T,P,COM,TS,{self.env.ie},C,'{self.arg2}') *
             SUM(RTP_VNTBYR(R,T,P,V), {self.env.mx}
                 ({self.env.var}_IRE(R,V,T,P,COM,TS,{self.env.ie}{self.env.sow})$(NOT RPC_AIRE(R,P,COM))+({self.env.var}_ACT(R,V,T,P,TS{self.env.sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)
                 ){self.arg4}
             ) * RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
         ) +
"""
        return help_str
