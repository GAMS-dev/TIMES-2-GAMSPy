# prep_ext_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.tm oversees all the added inperpolation activities needed by MACRO *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtMlf(GamsClass):
    """Translation unit for prep_ext.mlf."""

    # Instance attributes
    module_name: str = "prep_ext_mlf"
    gams_source: str = "prep_ext.mlf"

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
        g = self.tc
        m = g.container

        if len(self.env.ctst):
            self.tc.enqueue(self.prep_ext_mlf_exec)
        # Interpolate MACRO-specific parameters
        # fmt: off
        batincludes = [
            ("TM_EXPBND", "R,", "P",     ",'','','','',''", "DATAYEAR", "T"),
            ("TM_EXPF",   "R,", "",      ",'','','','',''", "DATAYEAR", "T"),
            ("TM_VOC",    "R,", "C,,BD", ",'','','',''",    "YEAR",     "T"),
            ("TM_GR",     "R,", "",      ",'','','','',''", "YEAR",     "T"),
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
* Additions to support MACRO linear formulation
  SET MAG(CG) / ACT, AKL, LAB, KN, YN /;
  SET MR(R), PP(T), TLAST(T), DM(C), XCP(J) /1, 6, 12/;
  SET TM_DM(REG,COM);
  SET XTP(LL);
  """,
        )
        #   ALIAS (MIYR_1,T_1,TB);
        Alias(m, "T_1", alias_with=g.Miyr1)
        Alias(m, "TB", alias_with=g.Miyr1)
        #   ALIAS (T,TP);
        Alias(m, "TP", alias_with=g.t)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER NYPER(ALLYEAR);
  PARAMETER CM_LED(LL);
  PARAMETER TM_TAXREV(R,T) //;
  PARAMETER TM_HDF(R,T) //;
""",
        )
        self.tc.enqueue(self.period_stuff)

    def prep_ext_mlf_exec(self: PrepExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"MINYR = MIYR_V1;",
        )

    def period_stuff(self: PrepExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Periods stuff
  PP(T+1) = YES;
  TLAST(T--ORD(T)) = YES;
  NYPER(T) = LAGT(T);
  NYPER(TLAST(T+1)) = NYPER(T);
  CM_LED(T+1)=LAGT(T);
  XTP(LL)$=CM_LED(LL);
  XTP(T) = YES;
  TM_PP(R,PP)=YES;

  MR(R) $= SUM(T$TM_GR(R,T),YES);
  TM_GDPGOAL(R,TB) = TM_GDP0(R);
  LOOP(PP(T+1),TM_GDPGOAL(R,PP) = TM_GDPGOAL(R,T)*(1+TM_GR(R,T)/100)**NYPER(T));
* Save demand LIM for non-MR
  OPTION TM_DM < COM_PROJ;
  TM_STEP(TM_DM(R,C),'N') = NOT COM_LIM(R,C,'FX');
""",
        )
