# eqactflo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTFLO.MOD relationship between process activity & individual primary     *
# *              commodity flows                                                *
# *=============================================================================*
# *GaG Questions/Comments:
# *  - always created at the PRC_TS level as tied to the PCG
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Sum

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqactfloMod(GamsClass):
    """Translation unit for eqactflo.mod."""

    # Instance attributes
    module_name: str = "eqactflo_mod"
    gams_source: str = "eqactflo.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc

        # Sets
        r, v, t, p, s, c, ie = g.r, g.v, g.t, g.p, g.s, g.c, g.ie
        r_v_t = self.env.r_v_t_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP

        # Variables
        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        VAR_FLO = g.get_variable(f"{self.env.var}_FLO")
        VAR_IRE = g.get_variable(f"{self.env.var}_IRE")

        reduce_con = (~g.RtpsOff[r, t, p, s]) if self.env.reduce == "YES" else 1

        eq = g.get_equation(f"{self.env.eq}_ACTFLO")

        # adjust so VAR_FLO only when not IRE (or STG)
        eq[g.RtpVintyr[*r_v_t, p], s, *swt].where[
            g.PrcTs[r, p, s] * (reduce_con) * g.PrcAct[r, p]
        ] = VAR_ACT[r, v, t, p, s, *sow].where[g.RtpVara[r, t, p]] == (
            # handle both regular and IRE processes
            # need to ensure that said commodity handled in current timeslice
            Sum(
                c.where[g.RpcPg[r, p, c].where[g.RtpcsVarf[r, t, p, c, s]]],
                (
                    VAR_FLO[r, v, t, p, c, s, *sow].where[g.RpFlo[r, p]]
                    + Sum(
                        g.RpcIre[r, p, c, ie].where[g.RpAire[r, p, ie]],
                        VAR_IRE[r, v, t, p, c, s, ie, *sow],
                    ).where[g.RpIre[r, p]]
                )
                / g.prc_actflo[r, v, p, c],
            )
        )
