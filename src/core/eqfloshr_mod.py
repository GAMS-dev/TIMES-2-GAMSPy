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
from collections.abc import Callable
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
        if self.env.CAL_RED == "cal_red.red":
            from core.cal_red_red import cal_red as cal_red_func
        else:
            from core.cal_nored_red import cal_nored as cal_red_func

        self.tc.enqueue(
            self.exec1,
            self.env.EQ,
            self.arg2,
            self.env.SWT,
            self.env.VAR,
            self.env.SOW,
            cal_red_func,
            self.arg1,
            self.arg3,
            self.env.R_V_T,
        )

    def exec1(
        self,
        EQ: str,
        arg2: str,
        SWT: str,
        VAR: str,
        SOW: str,
        cal_red_func: Callable,
        arg1: str,
        arg3: str,
        R_V_T: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
    {EQ}{arg1}_{arg3}SHR(RTP_VINTYR({R_V_T},P),C,CG,S {SWT})$((RP_STD(R,P)*TOP(R,P,C,'{arg3}')*RTPCS_VARF(R,T,P,C,S))$FLO_SHAR(R,V,P,C,CG,S,'{arg2}'))..

* all flows in the group
        FLO_SHAR(R,V,P,C,CG,S,'{arg2}') *
*V0.5a 980729 - RPCS_VAR: com not c
* [AL] Handle reduced/non-reduced groups separately
        (SUM((TOP(R,P,COM,'{arg3}'),RTPCS_VARF(R,T,P,COM,TS))$COM_GMAP(R,CG,COM),
             {VAR}_FLO(R,V,T,P,COM,TS {SOW})*RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
            )$(NOT RPG_RED(R,P,CG,'{arg3}')) +

         SUM((TOP(R,P,COM,'{arg3}'),RTPCS_VARF(R,T,P,COM,TS))$COM_GMAP(R,CG,COM),
{cal_red_func("COM", "COM1", "TS", "P", "T")}
                      *
* share-ts coarser than variable or share finer than variable
             RS_FR(R,S,TS)*(1+RTCS_FR(R,T,COM,S,TS))
            )$RPG_RED(R,P,CG,'{arg3}')
        )$(FLO_SHAR(R,V,P,C,CG,S,'{arg2}') > 0)

    ={arg1}=

* commodity working on, summed for all
        {VAR}_FLO(R,V,T,P,C,S {SOW})$(NOT RPG_RED(R,P,CG,'{arg3}')) +
        (
{cal_red_func("C", "COM", "S", "P", "T")}
        )$RPG_RED(R,P,CG,'{arg3}')
    ;
""",
        )
