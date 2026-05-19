# eqfloshr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQIN/OUTSHR is the market/product share limit constraint
# *   %1 - equation declaration type
# *   %2 - FLO_SHAR type for %1
# *   %3 - IN/OUT indicator
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Needs to be adjusted to handle attribute TS-level diff. the operation level
# *    - for now FLO_SHAR moved down to S1 level in PP_MAIN (which may be OK)
# *  - [AL] Changed level of equation to be that of RPCS_VAR; RP_STD control added
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqfloshrMod(GamsClass):
    """Translation unit for eqfloshr.mod."""

    # Instance attributes
    module_name: str = "eqfloshr_mod"
    gams_source: str = "eqfloshr.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
        arg3: str,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
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
    {self.env.eq}{self.arg1}_{self.arg3}SHR(RTP_VINTYR({self.env.r_v_t},P),C,CG,S {self.env.swt})$((RP_STD(R,P)*TOP(R,P,C,'{self.arg3}')*RTPCS_VARF(R,T,P,C,S))$FLO_SHAR(R,V,P,C,CG,S,'{self.arg2}'))..

* all flows in the group
        FLO_SHAR(R,V,P,C,CG,S,'{self.arg2}') *
*V0.5a 980729 - RPCS_VAR: com not c
* [AL] Handle reduced/non-reduced groups separately
        (SUM((TOP(R,P,COM,'{self.arg3}'),RTPCS_VARF(R,T,P,COM,TS))$COM_GMAP(R,CG,COM),
             {self.env.var}_FLO(R,V,T,P,COM,TS {self.env.sow})*RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
            )$(NOT RPG_RED(R,P,CG,'{self.arg3}')) +

         SUM((TOP(R,P,COM,'{self.arg3}'),RTPCS_VARF(R,T,P,COM,TS))$COM_GMAP(R,CG,COM),
{cal_red_func(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim, shff=self.env.shff, def_rtp_ffcs=self.tc.defined("RTP_FFCS"), arg1="COM", arg2="COM1", arg3="TS", arg4="P", arg5="T")}
                      *
* share-ts coarser than variable or share finer than variable
             RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
            )$RPG_RED(R,P,CG,'{self.arg3}')
        )$(FLO_SHAR(R,V,P,C,CG,S,'{self.arg2}') > 0)

    ={self.arg1}=

* commodity working on, summed for all
        {self.env.var}_FLO(R,V,T,P,C,S {self.env.sow})$(NOT RPG_RED(R,P,CG,'{self.arg3}')) +
        (
{cal_red_func(var=self.env.var, sow=self.env.sow, pgprim=self.env.pgprim, shff=self.env.shff, def_rtp_ffcs=self.tc.defined("RTP_FFCS"), arg1="C", arg2="COM", arg3="S", arg4="P", arg5="T")}
        )$RPG_RED(R,P,CG,'{self.arg3}')
    ;
""",
        )
