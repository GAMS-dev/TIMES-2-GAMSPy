# eqcapvac_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAPVAC is the capacity utilization equation for vintage-simulated processes
# *   sense      - equation lim type
# *   bound_type - bound type for sense
# *=============================================================================*
# * Questions/Comments:
# * - COEF_CSV is defined in COEF_CSV.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Product, Sum

from core.base_class import GamsClass
from core.utils import extract_var_domain, generate_equation, wrap_in_sum

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqcapvacModConfig:
    """Strongly typed data contract replacing the positional batch-include args."""

    sense: Literal["E", "L", "G"]
    bound_type: Literal["FX", "UP", "LO"]


class EqcapvacMod(GamsClass):
    """Translation unit for eqcapvac.mod."""

    # Instance attributes
    module_name: str = "eqcapvac_mod"
    gams_source: str = "eqcapvac.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqcapvacModConfig,
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        r, v, t, p, c, s, ts, cg, ie, k = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.ts,
            g.cg,
            g.ie,
            g.k,
        )
        ncap_afcs, prc_actflo = g.ncap_afcs, g.prc_actflo
        var = self.env.var
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_FLO = g.get_variable(f"{var}_FLO")
        VAR_IRE = g.get_variable(f"{var}_IRE")

        varm_id, varm_set = extract_var_domain(self.env.varm_GP)
        VARM_NCAP = g.get_variable(f"{varm_id}_NCAP")

        # Activity level at timeslice S
        activity = Sum(
            g.PrcTs[r, p, ts].where[g.TsMap[r, s, ts]],
            VAR_ACT[r, v, t, p, ts, *sow],
        ).where[~g.RpsCaflac[r, p, s, cc.bound_type]]

        # Flow levels when commodity-specific availabilities
        flows = Sum(
            Domain(g.RpcPg[r, p, c], g.ComTmap[r, g.ComType[cg], c]),
            (1 / prc_actflo[r, v, p, c])
            / (
                ncap_afcs[r, v, p, c, s]
                + Product(
                    g.xpt.where[ncap_afcs[r, v, p, cg, s]],
                    ncap_afcs[r, v, p, cg, s],
                ).where[~ncap_afcs[r, v, p, c, s]]
            )
            * Sum(
                g.RpcsVar[r, p, c, ts].where[g.TsMap[r, s, ts]],
                VAR_FLO[r, v, t, p, c, ts, *sow].where[g.RpStd[r, p]]
                + Sum(g.RpcIre[r, p, c, ie], VAR_IRE[r, v, t, p, c, ts, ie, *sow]),
            ),
        ).where[g.RpsCaflac[r, p, s, cc.bound_type]]

        # process is vintaged
        capacity = (
            Sum(
                g.Modlyear[k].where[g.coef_csv[r, k, t, p, v]],
                g.coef_csv[r, k, t, p, v]
                * g.coef_af[r, k, t, p, s, cc.bound_type]
                * wrap_in_sum(VARM_NCAP[r, k, p, *sws], varm_set).where[t[k]]
                + g.ncap_pasti[r, k, p],
            )
            * g.prc_capact[r, p]
            * g.g_yrfr[r, s]
        )

        eq = g.get_equation(f"EQ{cc.sense}_CAPVAC")
        eq[g.RtpVintyr[*self.env.r_v_t_GP, p], s, *self.env.swx_GP].where[
            self.env.swtx_GP * g.Afsv[r, t, p, s, cc.bound_type]
        ] = generate_equation(
            lhs=activity + flows,
            type=cc.sense,
            rhs=capacity,
        )
