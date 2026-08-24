# pp_chp_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * PP_CHP.MOD derives the FLO_SUM/SHARs/ACTFLOs for modeling CHPs from the inputs
# *   Upon completion all attributes are in place for handling by regular code
# *==============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, Set, Smax, Smin, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, abs, exp, log, power, project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def chp_unusual_operation_violations(g: TimesModelClass) -> Set:
    """CHP process with zero CEH but only upper bound on CHPR."""
    r, v, p, t = g.r, g.v, g.p, g.t
    Rvp, PrcVint = g.Rvp, g.PrcVint

    # MODLYEAR (and therefore V) is populated via a GAMS assignment statement
    # elsewhere in the model, which makes it an "assigned set" that GAMS
    # refuses to use as the domain of a newly declared set (error 187). RVP
    # itself is declared over ALLYEAR rather than V/MODLYEAR for the same
    # reason, so mirror that domain here.
    violations = Set(
        g.container, name="violations_chp_unusual", domain=[r, g.allyear, p]
    )
    violations[r, v, p].where[Rvp[r, v, p].where[(t[v] + PrcVint[r, p])]] = True
    return violations


class PpChpMod(GamsClass):
    """Translation unit for pp_chp.mod."""

    # Instance attributes
    module_name: str = "pp_chp_mod"
    gams_source: str = "pp_chp.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.ChpElc = Set(m, name="CHP_ELC", domain=[g.r, g.p, g.c])

        self.tc.enqueue(self.pp_chp_exec)

    def pp_chp_exec(self: PpChpMod) -> None:
        g = self.tc
        # * Back-pressure point should correspond to the maximum HEAT/POWER ratio
        rpc = (g.r, g.p, g.c)
        rvp = (g.r, g.v, g.p)
        g.ncap_chpr[g.Rtp, g.Bdneq].where[g.ncap_chpr[g.Rtp, "FX"]] = 0.0
        g.coef_rtp[g.Rtp[*rvp]].where[g.Chp[g.r, g.p]] = Max(
            0.0, Smax(g.bd, g.ncap_chpr[g.Rtp, g.bd])
        )
        # *-----------------------------------------------------------------------------
        # * calculate the slope: (CDEF/BPEF*(1+CHPR)-1)/CHPR
        g.ncap_ceh[g.Rtp].where[
            ((g.coef_rtp[g.Rtp] > 0.0).where[g.ncap_cdme[g.Rtp]])
        ] = Max(
            0.001,
            (g.ncap_cdme[g.Rtp] / g.ncap_bpme[g.Rtp] * (1.0 + g.coef_rtp[g.Rtp]) - 1.0)
            / g.coef_rtp[g.Rtp],
        )
        # * EQ_PTRANS control - overall efficiency
        g.flo_sum[g.Rtp[*rvp], g.c, g.Com, g.c, g.Annual].where[
            (
                g.RpcSpg[g.r, g.p, g.Com].where[
                    g.RpcPg[*rpc] & g.NrgTmap[g.r, "ELC", g.c]
                ]
            )
        ] = sparse(g.ncap_cdme[g.Rtp])
        # *-----------------------------------------------------------------------------
        # * Identify CHP processes using NCAP_CHPR
        if g.Chp.number_records:
            # * Get the ELC / HEAT outputs
            project(source=g.ncap_chpr, target=g.PrcAct)
            g.ChpElc[g.RpcPg[g.Chp[g.PrcAct[g.r, g.p]], g.c]].where[
                g.NrgTmap[g.r, "ELC", g.c]
            ] = True
            project(source=g.ChpElc, target=g.Trackp)
            g.Trackp[g.RpPgact] = False
            g.Rvp[*rvp].where[(g.coef_rtp[*rvp].where[g.Trackp[g.r, g.p]])] = True
            g.RpGrp[g.RpcPg[g.Trackp[g.Rp], g.c]].where[(~(g.ChpElc[g.Rp, g.c]))] = True
            g.RpGrp[g.RpPgact[g.Chp], g.c].where[
                (g.Top[g.Chp, g.c, "OUT"].where[(~(g.ChpElc[g.Chp, g.c]))])
            ] = True
            g.Trackpg[g.RpGrp[g.RpcPg[*rpc]]].where[g.ComLim[g.r, g.c, "N"]] = True
            project(source=g.Trackpg, target=g.RpPrc)
            g.ncap_ceh[g.Rvp[*rvp]].where[(g.ncap_ceh[g.Rvp] == 0.0)] = -Number(
                0.5
            ).where[g.RpPrc[g.r, g.p]]
            g.ncap_bpme[g.Rvp] = Min(
                0.0,
                Smin(g.bd.where[g.ncap_chpr[g.Rvp, g.bd]], g.ncap_chpr[g.Rvp, g.bd])
                * ((g.ncap_ceh[g.Rvp] + 1.0).where[g.ncap_ceh[g.Rvp]] - 1.0),
            )
            g.ncap_ceh[g.Rvp].where[(g.ncap_ceh[g.Rvp] < 0.0)] = -g.ncap_ceh[g.Rvp]
            # * If slope is different from 1, we should always have a maximum heat share:
            g.ncap_chpr[g.Rvp, "FX"].where[
                (
                    (abs(g.ncap_ceh[g.Rvp] - 1.0) > 0.01).where[
                        (~(g.ncap_chpr[g.Rvp, "UP"]))
                    ]
                )
            ] = g.coef_rtp[g.Rvp] + SpecialValues.EPS
        # *-----------------------------------------------------------------------------
        # * Calculate ACTFLOs for pg and elc
        g.prc_actflo[g.Rvp[*rvp], g.c].where[g.RpcPg[*rpc]] = (
            1.0
            + (
                (g.prc_actflo[g.Rvp, g.c] / g.coef_rtp[g.Rvp] + 1.0)
                / Max(
                    0.001,
                    exp(abs(log(g.ncap_ceh[g.Rvp]))) - g.prc_actflo[g.Rvp, g.c],
                )
                - 1.0
            ).where[g.Trackpg[*rpc]]
        )
        g.prc_actflo[g.Rvp[*rvp], g.c].where[
            ((g.ncap_ceh[g.Rvp] <= 1.0).where[g.RpcPg[*rpc]])
        ] = (
            power(
                g.ncap_ceh[g.Rvp],
                (Number(1.0).where[g.ChpElc[*rpc]] - 1.0).where[g.ncap_ceh[g.Rvp]],
            )
            * (1.0 - g.ncap_bpme[g.Rvp])
            * g.prc_actflo[g.Rvp, g.c]
        )
        g.prc_actflo[g.Rvp[*rvp], g.c].where[
            (((g.ncap_ceh[g.Rvp] > 1.0) * g.ncap_ceh[g.Rvp]).where[g.RpcPg[*rpc]])
        ] = (
            (1.0 + (1.0 / g.ncap_ceh[g.Rvp] - 1.0) / (1.0 + 1.0 / g.coef_rtp[g.Rvp]))
            * power(g.ncap_ceh[g.Rvp], 1.0 - Number(1.0).where[g.ChpElc[*rpc]])
            * g.prc_actflo[g.Rvp, g.c]
        )
        # * EQ_PTRANS control - low-temperature heat
        g.flo_sum[g.Rtp[*rvp], g.c, g.Com, g.c, g.Annual].where[
            (g.RpGrp[g.r, g.p, g.Com].where[g.ChpElc[*rpc] & g.ncap_cdme[g.Rtp]])
        ] = -1.0 / g.prc_actflo[g.Rtp, g.Com]
        # *-----------------------------------------------------------------------------
        # * EQ_OUTSHR controls: Set bound for the electricity output
        # * Define the share over PG if there is more than just ELC, otherwise NRG
        g.RpGrp[g.Trackpg] = False
        g.Trackp[g.RpPrc] = False
        g.Trackpg.setRecords(None)
        g.Trackpg[g.RpPg[g.Trackp, g.cg]] = True
        g.Trackpg[g.RpPgact[g.Chp[g.r, g.p]], g.cg["NRG"]] = sparse(
            Sum(g.RpGrp[*rpc].where[g.ComGmap[g.r, g.cg, g.c]], 1.0)
        )
        g.RpGrp[g.RpGrp[g.Rp, g.c]].where[Sum(g.Trackpg[g.Rp, g.cg], 1.0)] = False
        with Loop(Domain(g.ChpElc[*rpc], g.Trackpg[g.r, g.p, g.cg])):
            g.flo_shar[g.Rtp[*rvp], g.c, g.cg, g.s, "LO"].where[
                (g.PrcTs[g.r, g.p, g.s] * g.ncap_chpr[g.Rtp, "UP"])
            ] = 1.0 / (1.0 + g.ncap_chpr[g.Rtp, "UP"])
            g.flo_shar[g.Rtp[*rvp], g.c, g.cg, g.s, "FX"].where[
                (g.PrcTs[g.r, g.p, g.s] * g.ncap_chpr[g.Rtp, "FX"])
            ] = 1.0 / (1.0 + g.ncap_chpr[g.Rtp, "FX"])
            g.flo_shar[g.Rtp[*rvp], g.c, g.cg, g.s, "UP"].where[
                (g.PrcTs[g.r, g.p, g.s] * g.ncap_chpr[g.Rtp, "LO"])
            ] = 1.0 / (1.0 + g.ncap_chpr[g.Rtp, "LO"])
        # * Heat share
        g.flo_shar[g.Rtp[*rvp], g.c, g.cg, g.s, g.bd].where[
            (g.PrcTs[g.r, g.p, g.s].where[g.RpPg[g.r, g.p, g.cg] & g.RpGrp[*rpc]])
        ] = g.ncap_chpr[g.Rtp, g.bd] / (g.ncap_chpr[g.Rtp, g.bd] + 1.0)
        # * ACT flows
        g.flo_sum[g.Rvp, g.Com, g.c, g.Com, g.s].where[
            (
                (
                    g.ncap_bpme[g.Rvp].where[
                        g.ncap_ceh[g.Rvp] & g.prc_actflo[g.Rvp, g.c]
                    ]
                    < 0.0
                ).where[g.flo_eff[g.Rvp, g.Com, g.c, g.s]]
            )
        ] = g.flo_eff[g.Rvp, g.Com, g.c, g.s] / g.prc_actflo[g.Rvp, g.c]
        if Sum(g.Chp[g.RpXred], 1.0).toValue():
            g.prc_actflo[g.Rvp[*rvp], g.c].where[g.RpcAflo[*rpc]] = 1.0
            g.RpcAct[g.RpcAflo[g.Chp[g.RpXred], g.c]] = True
        # *-----------------------------------------------------------------------------
        # * Adjust PKCNT
        with Loop(g.RpcPkc[g.ChpElc[*rpc]]):
            g.ncap_pkcnt[g.Rvp[*rvp], g.s].where[g.ComTs[g.r, g.c, g.s]] = g.ncap_pkcnt[
                g.Rvp, g.s
            ] / Max(1.0, g.prc_actflo[g.Rvp, g.c])
        g.Rvp[g.Rvp].where[
            (
                g.ncap_ceh[g.Rvp]
                + Number(1.0).where[g.ncap_chpr[g.Rvp, "FX"]]
                + g.ncap_chpr[g.Rvp, "LO"]
                > 0.0
            )
        ] = False

        violations = chp_unusual_operation_violations(g=g)
        g.pp_qaput_logger.log_violations(
            violations_df=violations.records,
            err_level=1,
            group_desc="CHP process with zero CEH but only upper bound on CHPR.",
            message_template="WARNING       - Unusual CHP operation: R={R} P={P} V={V}",
        )

        g.PrcAct.setRecords(None)
        g.Rvp.setRecords(None)
        g.Trackp.setRecords(None)
        g.Trackpg.setRecords(None)
        g.RpPrc.setRecords(None)
        g.RpGrp.setRecords(None)
        g.coef_rtp.setRecords(None)
