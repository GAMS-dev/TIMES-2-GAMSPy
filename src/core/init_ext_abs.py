# init_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INIT_EXT.xtd oversees initial preprocessor activities
# *   arg11 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Card, Domain, Loop, Set, Sum, sparse
from gamspy.math import Min, Round, abs, diag, project, sign

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtAbs(GamsClass):
    """Translation unit for init_ext.abs."""

    # Instance attributes
    module_name: str = "init_ext_abs"
    gams_source: str = "init_ext.abs"

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
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        g.BsRvt = Set(m, name="BS_RVT", domain=[g.r, g.year, g.t])

        self.tc.enqueue(self.proc_allowed)

    def proc_allowed(self) -> None:
        g = self.tc
        # * Get processes allowed to participate in the reserve markets per region
        project(source=g.bs_rmax, target=g.BsBsc)
        project(source=g.BsBsc, target=g.Trackp)
        g.z[...] = Card(g.Trackp)
        g.bs_rtype[g.r, g.c].where[g.bs_rtype[g.r, g.c]] = sign(
            g.bs_rtype[g.r, g.c]
        ) * Round(Min(5.0, abs(g.bs_rtype[g.r, g.c])))
        # * Remove reserve commodities from topology
        with Loop(g.Trackp[g.r, g.p].where[g.z]):
            g.RpUpr[g.r, g.p, "FX"] = g.z
            g.z[...] = 0.0
        g.Trackp[g.r, g.p] = sparse(
            Sum(Domain(g.c, g.bd).where[g.bs_stime[g.r, g.p, g.c, g.bd]], 1.0)
        )
        g.Top[g.Trackp[g.r, g.p], g.c, g.io].where[g.bs_rtype[g.r, g.c]] = False
        g.NrgTmap[g.r, g.nrgtype, g.c].where[g.bs_rtype[g.r, g.c]] = diag(
            g.nrgtype, "RATE"
        )
        g.Trackp.setRecords(None)
        # *-----------------------------------------------------------------------------
        # * Make A-sets
        g.BsAbd[g.r, g.c, "LO"].where[(g.bs_rtype[g.r, g.c] < 0.0)] = sparse(
            g.bs_rtype[g.r, g.c]
        )
        g.BsAbd[g.r, g.c, "UP"].where[(g.bs_rtype[g.r, g.c] > 0.0)] = sparse(
            g.bs_rtype[g.r, g.c]
        )
        g.BsAneg[g.r, g.c] = sparse(g.BsAbd[g.r, g.c, "LO"])
        g.BsApos[g.r, g.c] = sparse(g.BsAbd[g.r, g.c, "UP"])
        # * Remove invalid values
        g.bs_demdet[g.r, g.year, g.Rsp, g.c, g.s].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_omega[g.r, g.year, g.c, g.s].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_delta[g.r, g.year, g.c, g.s].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_lambda[g.r, g.year, g.c].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_detwt[g.r, g.year, g.c].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_sigma[g.r, g.year, g.c, g.item, g.s].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_rmax[g.r, g.year, g.p, g.c, g.s].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
        g.bs_stime[g.r, g.p, g.c, g.bd].where[(~(g.bs_rtype[g.r, g.c]))] = 0.0
