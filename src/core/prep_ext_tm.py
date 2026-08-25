# prep_ext_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.tm oversees all the added inperpolation activities needed by MACRO *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*
# * Comments: If TM_EC0 not defined, try loading MSADDF
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias

from core.base_class import GamsClass
from core.filparam_gms import FilparamGms, FilparamGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtTm(GamsClass):
    """Translation unit for prep_ext.tm."""

    # Instance attributes
    module_name: str = "prep_ext_tm"
    gams_source: str = "prep_ext.tm"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        # TODO:
        # hard to translate there is no msaddf.dd
        # GAMS "exist" looks in idir
        # the last statement makes no sense in GAMSPy because a symbols is always defined. So if not defined we define it by clearing
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
$IF NOT DEFINED TM_EC0
$IF EXIST msaddf.dd $INCLUDE msaddf.dd
$IF NOT DEFINED TM_EC0 OPTION CLEAR=TM_EC0;
""",
        )
        # Interpolate MACRO-specific parameters
        # fmt: off
        batincludes: list[FilparamGmsConfig] = [
            FilparamGmsConfig(g.tm_ddf,    (g.r,), (g.c,), ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_expbnd, (g.r,), (g.p,), ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_expf,   (g.r,), (),     ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_gr,     (g.r,), (),     ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_growv,  (g.r,), (),     ("",) * 4, g.Datayear, g.t),
        ]
        # fmt: on
        for config in batincludes:
            self.include(FilparamGms(self.tc, self.env, config))
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Additions to support MACRO soft-link
  SCALAR TM_SL /0/;
  SETS MR(R), PP(T), TLAST(T), DM(C), XCP(J) /1, 6, 12/;
""",
        )

        # ALIAS (MIYR_1,T_1);
        Alias(m, "T_1", alias_with=g.Miyr1)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER NYPER(ALLYEAR);
""",
        )
        self.tc.enqueue(self.prep_ext_tm_exec)

    def prep_ext_tm_exec(self: PrepExtTm) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  PP(T+1) = YES;
  TLAST(T)$(ORD(T) EQ CARD(T)) = YES;
  TM_SL = (ROUND(TM_ARBM,1) EQ 1);
  IF(TM_SL,NYPER(T) = LAGT(T); ELSE NYPER(TT(T-1)) = (D(T)+D(TT))/2);
  NYPER(TLAST(T+1)) = LAGT(T);
  LOOP(R,DM(C)$DEM(R,C)=YES);
""",
        )
