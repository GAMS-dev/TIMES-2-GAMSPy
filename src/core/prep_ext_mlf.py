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

from gamspy import Alias, Loop, Ord, Parameter, Set, Sum, sparse
from gamspy.math import project

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
        # * Additions to support MACRO linear formulation
        g.Mag = Set(
            m, name="MAG", domain=[g.cg], records=["ACT", "AKL", "LAB", "KN", "YN"]
        )
        g.Mr = Set(m, name="MR", domain=[g.r])
        g.Pp = Set(m, name="PP", domain=[g.t])
        g.Tlast = Set(m, name="TLAST", domain=[g.t])
        g.Dm = Set(m, name="DM", domain=[g.c])
        g.Xcp = Set(m, name="XCP", domain=[g.j], records=["1", "6", "12"])
        g.TmDm = Set(m, name="TM_DM", domain=[g.Reg, g.Com])
        g.Xtp = Set(m, name="XTP", domain=[g.ll])

        g.t1 = Alias(m, "T_1", alias_with=g.Miyr1)
        g.tb = Alias(m, "TB", alias_with=g.Miyr1)
        g.tp = Alias(m, "TP", alias_with=g.t)

        g.nyper = Parameter(m, name="NYPER", domain=[g.allyear])
        g.cm_led = Parameter(m, name="CM_LED", domain=[g.ll])
        g.tm_taxrev = Parameter(m, name="TM_TAXREV", domain=[g.r, g.t])
        g.tm_hdf = Parameter(m, name="TM_HDF", domain=[g.r, g.t])

        self.tc.enqueue(self.period_stuff)

    def prep_ext_mlf_exec(self: PrepExtMlf) -> None:
        g = self.tc
        g.minyr[...] = g.miyr_v1

    def period_stuff(self: PrepExtMlf) -> None:
        g = self.tc
        # * Periods stuff
        g.Pp[g.t + 1] = True
        g.Tlast[g.t.lag(Ord(g.t), "circular")] = True
        g.nyper[g.t] = g.lagt[g.t]
        g.nyper[g.Tlast[g.t + 1]] = g.nyper[g.t]
        g.cm_led[g.t + 1] = g.lagt[g.t]
        g.Xtp[g.ll] = sparse(g.cm_led[g.ll])
        g.Xtp[g.t] = True
        g.TmPp[g.r, g.Pp] = True
        g.Mr[g.r] = sparse(Sum(g.t.where[g.tm_gr[g.r, g.t]], True))
        g.tm_gdpgoal[g.r, g.tb] = g.tm_gdp0[g.r]
        with Loop(g.Pp[g.t + 1]):
            g.tm_gdpgoal[g.r, g.Pp] = g.tm_gdpgoal[g.r, g.t] * (
                (1.0 + g.tm_gr[g.r, g.t] / 100.0) ** g.nyper[g.t]
            )
        # * Save demand LIM for non-MR
        project(source=g.com_proj, target=g.TmDm)
        g.tm_step[g.TmDm[g.r, g.c], "N"] = ~(g.ComLim[g.r, g.c, "FX"])
