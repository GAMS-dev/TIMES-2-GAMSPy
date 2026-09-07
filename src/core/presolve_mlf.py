# presolve_mlf.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Presolve.mlf - Prepare coefficients for full MLF model
# *------------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Ord, Parameter, Set, Smin, SpecialValues, Sum, sparse
from gamspy.math import Min, Round, abs, exp, log, sqrt

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PresolveMlf(GamsClass):
    """Translation unit for presolve.mlf."""

    # Instance attributes
    module_name: str = "presolve_mlf"
    gams_source: str = "presolve.mlf"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.comp1()
        self.tc.enqueue(self.exec1)

    def comp1(self: PresolveMlf) -> None:
        g = self.tc
        m = g.container
        g.TmDmas = Set(m, name="TM_DMAS", domain=[g.cg, g.cg])
        g.TmCes = Set(m, name="TM_CES", domain=[g.cg], records=["AKL", "YN"])
        g.TmRcj = Set(m, name="TM_RCJ", domain=[g.r, g.cg, g.j, g.bd])
        g.Logj = Set(m, name="LOGJ", domain=[g.j, g.bd])
        g.tm_logjot = Parameter(m, name="TM_LOGJOT", records=0)
        g.tm_lsc = Parameter(m, name="TM_LSC", records=0)
        g.tm_basepri = Parameter(m, name="TM_BASEPRI", domain=[g.r, g.t, g.cg])
        g.tm_baselev = Parameter(m, name="TM_BASELEV", domain=[g.r, g.t, g.cg])
        g.tm_pref = Parameter(m, name="TM_PREF", domain=[g.r, g.t, g.cg])
        g.tm_qref = Parameter(m, name="TM_QREF", domain=[g.r, g.t, g.cg])
        g.tm_shar = Parameter(m, name="TM_SHAR", domain=[g.r, g.t, g.cg, g.cg])
        g.tm_agg = Parameter(m, name="TM_AGG", domain=[g.r, g.t, g.cg, g.cg])
        g.tm_ceslev = Parameter(m, name="TM_CESLEV", domain=[g.r, g.t, g.cg])
        g.tm_agc = Parameter(m, name="TM_AGC", domain=[g.r, g.t, g.cg, g.cg, g.j, g.bd])
        g.tm_midcon = Parameter(m, name="TM_MIDCON", domain=[g.r, g.t])
        g.tm_logval = Parameter(m, name="TM_LOGVAL", domain=[g.j, g.bd])

    def exec1(self: PresolveMlf) -> None:
        g = self.tc
        # * Reset demand indicators
        rtcg = (g.r, g.t, g.cg)
        rtcg1 = (g.r, g.t, g.cg1)
        g.Dm.setRecords(None)
        g.Dm[g.c] = sparse(Sum(g.TmDm[g.Mr, g.c], 1.0))
        g.tm_basepri[g.Mr, g.t, g.Mag[g.c]] = (
            abs(
                g.eq_dd.m[g.Mr, g.t, g.c]
                * g.tm_aeeifac[g.Mr, g.t, g.c]
                / g.tm_scale_nrg
            )
            / g.tm_dfact[g.Mr, g.t]
        )
        g.tm_basepri[g.Mr, g.t, "LAB"] = (
            abs(g.eq_labor.m[g.Mr, g.t]) / g.tm_dfact[g.Mr, g.t]
        )
        g.tm_basepri[g.Mr, g.t, "KN"] = (
            abs(g.eq_kncap.m[g.Mr, g.t]) / g.tm_dfact[g.Mr, g.t]
        )
        g.tm_basepri[g.Mr, g.t, "AKL"] = (
            abs(g.eq_akl.m[g.Mr, g.t]) / g.tm_dfact[g.Mr, g.t]
        )
        g.tm_basepri[g.Mr, g.t, "YN"] = (
            abs(g.eq_prod_y.m[g.Mr, g.t]) / g.tm_dfact[g.Mr, g.t]
        )
        g.tm_baselev[g.Mr, g.t, g.Mag] = g.VAR_D.l[g.Mr, g.t, g.Mag]
        g.tm_baselev[g.Mr, g.t, "YN"] = g.par_y[g.Mr, g.t]
        g.tm_baselev[g.Mr, g.t, "CON"] = g.VAR_C.l[g.Mr, g.t]
        g.TmDmas["AKL", "KN"] = True
        g.TmDmas["AKL", "LAB"] = True
        g.TmDmas["YN", "AKL"] = True
        g.TmDmas["YN", "ACT"] = True
        # * Calculate CES parameters
        g.tm_pref[g.Mr[g.r], g.t, g.cg] = sparse(g.tm_basepri[*rtcg])
        g.tm_ceslev[g.Mr[g.r], g.t, g.TmCes[g.cg]] = Sum(
            g.TmDmas[g.cg, g.cg1], g.tm_baselev[*rtcg1]
        )
        g.tm_pref[g.Mr[g.r], g.t, g.TmCes[g.cg]] = (
            Sum(
                g.TmDmas[g.cg, g.cg1],
                g.tm_baselev[*rtcg1] * g.tm_pref[*rtcg1],
            )
            / g.tm_ceslev[*rtcg]
        )
        g.tm_agg[g.Mr[g.r], g.t, g.cg1, g.TmCes[g.cg]].where[g.TmDmas[g.cg, g.cg1]] = (
            1.0
            + (g.tm_basepri[*rtcg1] / g.tm_pref[*rtcg] - 1.0).where[g.tm_pref[*rtcg]]
        )
        # * Normalize TM_AGG
        g.tm_qref[g.Mr[g.r], g.t, g.TmCes[g.cg]] = Sum(
            g.TmDmas[g.cg, g.cg1],
            g.tm_agg[*rtcg1, g.cg] * g.tm_baselev[*rtcg1],
        )
        g.tm_agg[g.Mr[g.r], g.t, g.cg1, g.TmCes[g.cg]].where[g.tm_agg[*rtcg1, g.cg]] = (
            g.tm_agg[*rtcg1, g.cg] * g.tm_ceslev[*rtcg] / g.tm_qref[*rtcg]
        )
        # * Reset QREF and determine shares
        g.tm_qref[g.Mr[g.r], g.t, g.cg] = sparse(g.tm_baselev[*rtcg])
        g.tm_shar[g.Mr[g.r], g.t, g.cg, g.cg1].where[g.TmDmas[g.cg, g.cg1]] = (
            g.tm_baselev[*rtcg1] / g.tm_ceslev[*rtcg]
        )
        g.tm_cie[g.Mr[g.r], g.t, g.TmCes[g.cg]].where[g.tm_ceslev[*rtcg]] = (
            g.tm_qref[*rtcg] / g.tm_ceslev[*rtcg]
        )
        # * Reverse RD_SHAR for CES aggregation
        g.tm_shar[g.Mr[g.r], g.t, g.cg1, g.cg].where[g.tm_agg[*rtcg1, g.cg]] = (
            g.tm_agg[*rtcg1, g.cg] * g.tm_pref[*rtcg]
        )
        # * Prepare elasticity steps
        with Loop(g.TmDmas[g.cg, g.cg1]):
            g.z[...] = g.tm_defval["MACVOC"]
            g.tm_step[g.r, g.cg1, g.Bdneq] = g.tm_defval["MACSTEP"]
            g.tm_voc[g.Mr[g.r], g.t, g.cg1, g.Bdneq] = Min(
                g.z, g.z / 2.0 + (g.m[g.t] - g.miyr_v1) * 0.01
            )
            g.TmRcj[g.Mr[g.r], g.cg1, g.j, g.Bdneq].where[
                (Ord(g.j) <= g.tm_step[g.r, g.cg1, g.Bdneq])
            ] = True
        # * Cobb-Douglas function
        g.tm_agc[g.Mr[g.r], g.t, g.cg["AKL"], g.cg1, g.j, g.bd].where[
            (
                (g.tm_voc[*rtcg1, g.bd] > 0.0).where[
                    g.TmRcj[g.r, g.cg1, g.j, g.bd] & g.TmDmas[g.cg, g.cg1]
                ]
            )
        ] = (
            -g.bdsig[g.bd]
            * log(
                1.0
                - g.bdsig[g.bd]
                * Ord(g.j)
                * g.tm_voc[*rtcg1, g.bd]
                / g.tm_step[g.r, g.cg1, g.bd]
            )
            / (Ord(g.j) * g.tm_voc[*rtcg1, g.bd] / g.tm_step[g.r, g.cg1, g.bd])
        )
        # * CES Production function
        g.tm_agc[g.Mr[g.r], g.t, g.cg["YN"], g.cg1, g.j, g.bd].where[
            (
                (g.tm_voc[*rtcg1, g.bd] > 0.0).where[
                    g.TmRcj[g.r, g.cg1, g.j, g.bd] & g.TmDmas[g.cg, g.cg1]
                ]
            )
        ] = (
            g.bdsig[g.bd]
            * (
                1.0
                - (
                    (
                        1.0
                        - g.bdsig[g.bd]
                        * Ord(g.j)
                        * g.tm_voc[*rtcg1, g.bd]
                        / g.tm_step[g.r, g.cg1, g.bd]
                    )
                    ** (1.0 - 1.0 / g.tm_esub[g.r])
                )
            )
            / (Ord(g.j) * g.tm_voc[*rtcg1, g.bd] / g.tm_step[g.r, g.cg1, g.bd])
            / (1.0 - 1.0 / g.tm_esub[g.r])
        )
        # * Restore PREF to BASEPRI
        g.tm_pref[g.Mr[g.r], g.t, g.cg] = sparse(g.tm_basepri[*rtcg])
        # * Calculate demand parameters
        g.tm_pref[g.Mr[g.r], g.t, g.c].where[g.TmDm[g.r, g.c]] = g.ddf_pref[
            g.r, g.t, g.c
        ]
        g.tm_qref[g.Mr[g.r], g.t, g.c].where[g.TmDm[g.r, g.c]] = g.com_proj[
            g.r, g.t, g.c
        ]
        g.tm_agg[g.Mr[g.r], g.t, g.Dm[g.c], g.cg["ACT"]] = (
            g.tm_pref[g.r, g.t, g.c] / g.tm_dmc[*rtcg]
        )
        g.tm_shar[g.Mr[g.r], g.t, g.cg["ACT"], g.c].where[g.TmDm[g.r, g.c]] = (
            g.tm_qref[g.r, g.t, g.c] / g.tm_dem[*rtcg]
        )
        g.tm_shar[g.Mr[g.r], g.t, g.c, g.cg["ACT"]].where[g.TmDm[g.r, g.c]] = (
            g.tm_agg[g.r, g.t, g.c, g.cg] * g.tm_dmc[*rtcg]
        )
        # * Prepare elasticity steps
        g.z[...] = Smin(g.Pp[g.t], g.m[g.t])
        g.tm_step[g.TmDm[g.Rc], g.Bdneq[g.bd]].where[(~(g.tm_step[g.Rc, g.bd]))] = (
            55.0 - 5.0 * g.bdsig[g.bd]
        )
        g.tm_voc[g.Mr[g.r], g.t, g.c, "LO"].where[
            ((~(g.tm_voc[g.r, g.t, g.c, "LO"])).where[g.TmDm[g.r, g.c]])
        ] = Min(0.45, 0.15 + (g.m[g.t] - g.z) * 0.015)
        g.tm_voc[g.Mr[g.r], g.t, g.c, "UP"].where[
            ((~(g.tm_voc[g.r, g.t, g.c, "UP"])).where[g.TmDm[g.r, g.c]])
        ] = (
            0.3 / (1.0 - g.tm_voc[g.r, g.t, g.c, "LO"])
            + g.tm_voc[g.r, g.t, g.c, "LO"]
            - 0.3
        )
        g.TmRcj[g.TmDm[g.Mr, g.c], g.j, g.Bdneq[g.bd]].where[
            (Ord(g.j) <= g.tm_step[g.Mr, g.c, g.bd])
        ] = True
        # * Demand CES aggregation
        g.tm_agc[g.Mr[g.r], g.t, g.cg["ACT"], g.c, g.j, g.bd].where[
            (
                (g.tm_voc[g.r, g.t, g.c, g.bd] > 0.0).where[
                    g.TmRcj[g.r, g.c, g.j, g.bd] & g.TmDm[g.r, g.c]
                ]
            )
        ] = (
            g.bdsig[g.bd]
            * (
                1.0
                - (
                    (
                        1.0
                        - g.bdsig[g.bd]
                        * Ord(g.j)
                        * g.tm_voc[g.r, g.t, g.c, g.bd]
                        / g.tm_step[g.r, g.c, g.bd]
                    )
                    ** (1.0 - 1.0 / g.tm_desub[g.r])
                )
            )
            / (Ord(g.j) * g.tm_voc[g.r, g.t, g.c, g.bd] / g.tm_step[g.r, g.c, g.bd])
            / (1.0 - 1.0 / g.tm_desub[g.r])
        )
        # * Logarithmic utility from consumption
        g.z[...] = g.tm_defval["LOGSTEP"]
        g.Logj[g.j, g.Bdneq[g.bd]].where[(Ord(g.j) <= Round(g.z / 2.0))] = True
        g.tm_midcon[g.r, g.t] = (
            g.tm_baselev[g.r, g.t, "CON"] * 0.5 * sqrt(exp(log(2.0) * 1.1))
        )
        g.tm_logjot[...] = log(2.0) / Round(g.z / 1.1)
        g.tm_logval[g.Logj[g.j, g.Bdneq[g.bd]]] = (
            1.0 - exp(-g.bdsig[g.bd] * Ord(g.j) * g.tm_logjot)
        ) / (g.tm_logjot * Ord(g.j))
        g.tm_lsc[...] = Round((g.z**0.7), -1)
        # *------------------------------------------------------------------------------
        # * Reset bounds
        g.VAR_K.up[g.Mr, g.t] = SpecialValues.POSINF
        g.VAR_K.lo[g.Mr, g.t] = 0.0
        g.VAR_D.up[g.Mr, g.t, g.Mag] = SpecialValues.POSINF
        g.VAR_D.lo[g.Mr, g.t, g.Mag] = 0.0
        g.VAR_D.fx[g.Mr, g.t, "LAB"] = g.tm_l[g.Mr, g.t]
        g.VAR_C.up[g.Mr[g.r], g.t].where[(~(g.TmPp[g.r, g.t]))] = g.VAR_C.l[g.r, g.t]
        # NOTE: OPTION BRATIO=1 is a GAMS model-solve-option statement meant to
        # affect the next SOLVE elsewhere in the run. GAMSPy runs every
        # statement as its own job, so it cannot be captured natively here
        # (see dynslite_vda.py's exec_solve_stp docstring); kept as the one
        # raw fragment, emitted only for traceability, matching initmty_tm.py.
        self.tc.add_gams_code(module=self, phase="run", code="OPTION BRATIO=1;")
