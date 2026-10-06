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
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Alias, Card, Loop, Ord, Parameter, Set
from gamspy.math import Round

from core.base_class import GamsClass
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.read_dd import read_dd_file

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
        if not g.defined(g.tm_ec0):
            # NOTE inlcude not yet covered by instances
            # $IF EXIST msaddf.dd $INCLUDE msaddf.dd
            msaddf = Path(g.config.data_dir, "msaddf.dd")
            if msaddf.exists():
                read_dd_file(tc=g, dd_path=msaddf)
            # $IF NOT DEFINED TM_EC0 OPTION CLEAR=TM_EC0;
            if not g.defined(g.tm_ec0):
                g.register_assignment(g.tm_ec0)
        # Interpolate MACRO-specific parameters
        # fmt: off
        batincludes: list[FilparamGmsConfig] = [
            FilparamGmsConfig(g.tm_ddf,    (g.r,), (g.c,), ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_expbnd, (g.r,), (g.p,), ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_expf,   (g.r,), (),     ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_gr,     (g.r,), (),     ("",) * 5, g.Datayear, g.t),
            FilparamGmsConfig(g.tm_growv,  (g.r,), (),     ("",) * 5, g.Datayear, g.t),
        ]
        # fmt: on
        for config in batincludes:
            self.include(FilparamGms(self.tc, self.env, config))
        # * Additions to support MACRO soft-link
        g.tm_sl = Parameter(m, name="TM_SL", records=0)
        g.Mr = Set(m, name="MR", domain=[g.r])
        g.Pp = Set(m, name="PP", domain=[g.t])
        g.Tlast = Set(m, name="TLAST", domain=[g.t])
        g.Dm = Set(m, name="DM", domain=[g.c])
        g.Xcp = Set(m, name="XCP", domain=[g.j], records=["1", "6", "12"])

        g.t1 = Alias(m, "T_1", alias_with=g.Miyr1)
        g.nyper = Parameter(m, name="NYPER", domain=[g.allyear])

        self.tc.enqueue(self.prep_ext_tm_exec)

    def prep_ext_tm_exec(self: PrepExtTm) -> None:
        g = self.tc
        g.Pp[g.t + 1] = True
        g.Tlast[g.t].where[(Ord(g.t) == Card(g.t))] = True
        g.tm_sl[...] = Round(g.tm_arbm, 1) == 1.0
        if ((g.tm_sl) * 1).toValue():
            g.nyper[g.t] = g.lagt[g.t]
        else:
            g.nyper[g.tt[g.t - 1]] = (g.d[g.t] + g.d[g.tt]) / 2.0
        g.nyper[g.Tlast[g.t + 1]] = g.lagt[g.t]
        with Loop(g.r):
            g.Dm[g.c].where[g.Dem[g.r, g.c]] = True
