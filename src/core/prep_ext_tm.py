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

from core.fillparm_gms import FillparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtTm(GamsClass):
    """Translation unit for prep_ext.tm."""

    # Instance attributes
    module_name: str = "prep_ext_tm"
    gams_source: str = "prep_ext.tm"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
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
        batincludes = [
            ("TM_DDF",    "R,", "C", ",'','','','',''", "DATAYEAR", "T"),
            ("TM_EXPBND", "R,", "P", ",'','','','',''", "DATAYEAR", "T"),
            ("TM_EXPF",   "R,", "",  ",'','','','',''", "DATAYEAR", "T"),
            ("TM_GR",     "R,", "",  ",'','','','',''", "DATAYEAR", "T"),
            ("TM_GROWV",  "R,", "",  ",'','','',''",    "DATAYEAR", "T"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                )
            )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Additions to support MACRO soft-link
  SCALAR TM_SL /0/;
  SETS MR(R), PP(T), TLAST(T), DM(C), XCP(J) /1, 6, 12/;
""",
        )

        m = self.tc.container
        # ALIAS (MIYR_1,T_1);
        miry_1 = m["MIYR_1"]
        Alias(m, "T_1", alias_with=miry_1)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER NYPER(ALLYEAR);
""",
        )
        self.tc.enqueue(self.prep_ext_tm_exec)

    def prep_ext_tm_exec(
        self: PrepExtTm,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PP(T+1) = YES;
  TLAST(T)$(ORD(T) EQ CARD(T)) = YES;
  TM_SL = (ROUND(TM_ARBM,1) EQ 1);
  IF(TM_SL,NYPER(T) = LAGT(T); ELSE NYPER(TT(T-1)) = (D(T)+D(TT))/2);
  NYPER(TLAST(T+1)) = LAGT(T);
  LOOP(R,DM(C)$DEM(R,C)=YES);
""",
        )
