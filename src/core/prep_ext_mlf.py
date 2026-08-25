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
from core.filparam_gms import FilparamGms, FilparamGmsConfig

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
        arg2: str = "",
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
        batincludes: list[FilparamGmsConfig] = [
            FilparamGmsConfig(g.tm_expbnd, (g.r,), (g.p,),             ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_expf,   (g.r,), (),                 ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_voc,    (g.r,), (g.c, g.bd),        ("",) * 4, g.year,     g.t),
            FilparamGmsConfig(g.tm_gr,     (g.r,), (),                 ("",) * 5, g.year,     g.t),
        ]
        # fmt: on
        for config in batincludes:
            self.include(FilparamGms(self.tc, self.env, config))
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
