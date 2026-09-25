# coef_alt_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_ALT.LIN do coefficient calculations for the linearized objective       *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Ord, Parameter, Set, Sum, sparse
from gamspy.math import Max, Min, Round, floor, log

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Expression

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefAltLin(GamsClass):
    """Translation unit for coef_alt.lin."""

    # Instance attributes
    module_name: str = "coef_alt_lin"
    gams_source: str = "coef_alt.lin"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str = "",
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        if not self.tc.defined("TPULSE"):
            g.Perdinv = Set(m, name="PERDINV", domain=[g.allyear, g.allyear])
            g.Tpulseyr = Set(m, name="TPULSEYR", domain=[g.t, g.allyear])
            g.tpulse = Parameter(m, name="TPULSE", domain=[g.allyear, g.allyear])
            g.obj_lint = Parameter(
                m, name="OBJ_LINT", domain=[g.r, g.t, g.allyear, g.cur]
            )
            g.obj_altv = Parameter(m, name="OBJ_ALTV", domain=[g.r, g.t])
            g.rtp_capvl = Parameter(m, name="RTP_CAPVL", domain=[g.r, g.year, g.p])
            g.rb = Parameter(m, name="RB", domain=[g.r, g.t])
            g.r_df = Parameter(m, name="R_DF", domain=[g.r, g.allyear])
            g.obj_wd = Parameter(
                m, name="OBJ_WD", domain=[g.Reg, g.cur, g.allyear, g.age, g.allyear]
            )
            g.obj_jd = Parameter(
                m, name="OBJ_JD", domain=[g.Reg, g.cur, g.allyear, g.age]
            )

        self._label_prepro()

    def _label_prepro(self) -> None:
        arg1 = self.arg1.upper()

        if arg1 == "FIX":
            self._label_dofix()
            return
        elif arg1 == "INV":
            self._label_doinv()
            return
        elif arg1 == "STP":
            self.tc.enqueue(self.exec1)

        self.env.set_scoped("iled", "$NCAP_ILED(R,V,P)")
        self.env.set_scoped("iled_GP", True)
        self.tc.enqueue(self.pre_establish_perdinv)

        # Complete OBJ_PVT and FPD:
        self.env.set_scoped("linflo", "0")
        self.env.set_scoped("linacc", "0")

        if self.env.obj.upper() == "LIN":
            self.env.set_scoped("linacc", "1")
        if self.env.ctst.upper() == "**EPS":
            self.env.set_scoped("linflo", "1")
        if f"{self.env.oblong}{self.env.obj}".upper() == "YESALT":
            self.env.set_scoped("varcost", "LIN")
            self.env.set_scoped("linacc", "1")
        if f"{self.env.oblong}{self.env.linflo}".upper() == "YES1":
            self.env.set_scoped("iled", "")
            self.env.set_scoped("iled_GP", False)

        self.tc.enqueue(self._complete_obj_pvt_and_fpd, linflo=self.env.linflo)

        self.tc.enqueue(
            self._prepare_linearized_cost_coeffs,
            obj=self.env.obj,
            linacc=self.env.linacc,
        )

        if arg1.upper() == "VAR":
            return

        self._label_cpt()

    def pre_establish_perdinv(self) -> None:
        g = self.tc
        t, k, ll = g.t, g.k, g.ll

        # Pre-establish PERDINV (for T)
        g.Perdinv[g.Yk[t, k]].where[g.yearval[k] > g.m[t] - g.lead[t]] = True
        g.Yk1.setRecords(None)
        g.Yk1[t, g.YEoh].where[g.yearval[t] <= g.yearval[g.YEoh]] = True
        # Initialize period pulse years and triangular functions
        g.Tpulseyr[g.Perdinv[t, g.YEoh]] = True
        g.tpulse[g.Tpulseyr[t, g.YEoh]] = (
            1 - ((g.m[t] - g.yearval[g.YEoh]) / g.lead[t]).where[~g.Miyr1[t]]
        )
        g.Tpulseyr[g.Yk1[t, g.YEoh]].where[g.yearval[g.YEoh] < g.m[t] + g.lagt[t]] = (
            True
        )
        g.tpulse[g.Tpulseyr[g.Yk1[t, ll]]] = 1 - g.tpulse[t.lead(1), ll]

    def exec1(self) -> None:
        g = self.tc
        g.Perdinv.setRecords(None)
        g.tpulse.setRecords(None)
        g.Tpulseyr.setRecords(None)

    def exec2(self) -> None:
        g = self.tc
        ll, jot, k, r, cur = g.ll, g.jot, g.k, g.r, g.cur

        g.Invspred[ll, jot, k, k].where[
            (~g.Kage[ll, jot]).where[g.Invstep[ll, jot, k, jot]]
        ] = True
        g.Invspred[g.Kage[ll, jot], ll.lead(floor(Ord(jot) / 2)), k].where[
            g.Invstep[ll, jot, k, jot]
        ] = True
        g.obj_jd[g.Rdcur[r, cur], g.Kage[ll, jot]] = Ord(jot) / Sum(
            g.Invspred[ll, jot, g.year, k],
            g.obj_disc[r, k, cur] / g.obj_disc[r, g.year, cur],
        )

    def exec3(self) -> None:
        self.tc.Invstep.setRecords(None)

    def exec4(self) -> None:
        g = self.tc
        ll, jot, k, r, cur = g.ll, g.jot, g.k, g.r, g.cur

        g.obj_wd[g.Rdcur[r, cur], ll, jot, k].where[
            (~g.Kage[ll, jot]).where[g.Invstep[ll, jot, k, jot]]
        ] = 1
        g.obj_wd[g.Rdcur[r, cur], g.Kage[ll, jot], k] = sparse(
            Sum(
                g.Invspred[ll, jot, g.year, k],
                g.obj_disc[r, k, cur] / g.obj_disc[r, g.year, cur],
            )
            * g.obj_jd[r, cur, ll, jot]
        )
        g.Kage.setRecords(None)

    def exec5(self) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        # The equation divisors for fixed costs:
        g.obj_diviv[g.ObjYes[r, g.Pastmile, p]] = 1
        g.obj_diviv[g.ObjYes[r, t, p]] = Max(
            1,
            Min(g.ipd[t], Round(g.ncap_tlife[r, t, p])).where[
                g.Obj1b[r, t, p] + g.Obj1a[r, t, p]
            ],
        )
        g.obj_diviv[g.ObjYes[r, t, p]].where[g.rtp_capvl[r, t, p]] = g.obj_diviv[
            r, t, p
        ] / (1 + g.rtp_capvl[r, t, p])

    def exec6(self) -> None:
        g = self.tc
        r, v, t, p, cur, jot, life = g.r, g.v, g.t, g.p, g.cur, g.jot, g.life

        # Resids
        with (
            Loop(g.PyrS[v]),
            Loop(
                Domain(g.ObjSumiv[v, r, v, p, jot, life], g.GRcur[r, cur]).where[
                    g.prc_resid[r, "0", p]
                ]
            ),
        ):
            g.obj_diviv[r, v, p] = (
                g.ncap_pasti[r, v, p]
                * g.obj_life[v, r, jot, life, cur]
                / Sum(
                    g.Vnt[v, t].where[g.prc_resid[r, t, p]],
                    g.prc_resid[r, t, p] * g.obj_pvt[r, t, cur],
                )
            )

    def exec7(self) -> None:
        g = self.tc
        r, t, p, cur = g.r, g.t, g.p, g.cur

        # Calculate additional cost due to trapezoidal periods
        with Loop(g.GRcur[r, cur]):
            g.fil2[t] = g.r_df[r, t]
            g.pastsum[g.Rtp[r, g.YEoh[t], p]].where[
                (~g.ncap_iled[r, t, p]).where[g.PrcCap[r, p]]
            ] = (g.fil2[t] ** (g.rb[r, t] - g.b[t]) - 1) / (
                1
                - g.fil2[t]
                ** Min(
                    g.miyr_vl + 1 - g.b[t],
                    g.coef_rpti[r, t, p] * g.ncap_tlife[r, t, p],
                )
            )
        g.rtp_capvl[r, t, p].where[g.pastsum[r, t, p]] = (1 + g.rtp_capvl[r, t, p]) / (
            1 + g.pastsum[r, t, p]
        ) - 1

    def exec8(self) -> None:
        g = self.tc
        r, v, t, p, cur, k, jot, life = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.cur,
            g.k,
            g.jot,
            g.life,
        )

        g.obj_jd[g.Rdcur[r, cur], k, jot].where[g.Kage[k, jot]] = 1
        # The equation divisors for investments:
        g.obj_divi[g.ObjYes[r, v, p]].where[~g.ObjI2[r, v, p]] = (
            1 + Min(g.ipd[v] - 1, Round(g.ncap_tlife[r, v, p]) - 1).where[t[v]]
        )
        g.obj_divi[g.ObjYes[g.Obj1b[r, t, p]]].where[
            Round(g.ncap_tlife[r, t, p]) == 1
        ] = g.ncap_tlife[r, t, p]
        g.obj_divi[g.ObjYes[r, t, p]].where[g.rtp_capvl[r, t, p]] = g.obj_divi[
            r, t, p
        ] / (1 + g.rtp_capvl[r, t, p])
        # The equation divisors for decommissioning :
        g.obj_diviii[g.ObjSums3[r, v, p]] = g.obj_divi[r, v, p]
        g.obj_diviii[g.ObjSums3[g.ObjI2[r, v, p]]] = Round(g.ncap_dlife[r, v, p])
        # Pastmile investments
        g.obj_crfd[r, g.Pastmile[v], p, cur].where[g.obj_pasti[r, v, p, cur]] = Sum(
            g.ObjSumii[r, v, p, life, k, jot],
            g.ncap_pasti[r, v, p] * g.obj_crf[r, v, p, cur] / g.obj_disc[r, k, cur],
        )
        g.obj_pasti[r, g.Pastmile[v], p, cur].where[g.obj_crfd[r, v, p, cur]] = (
            Sum(g.Vnt[v, t], g.coef_cpt[r, v, t, p] * g.obj_pvt[r, t, cur])
            * g.obj_crfd[r, v, p, cur]
            / g.cor_salvi[r, v, p, cur]
        )
        g.obj_crfd.setRecords(None)

    def exec9(self) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        g.obj_divi[g.Rtp[r, t, p]] = g.stp_div["1", r, t, p] * (
            1 + g.rtp_capvl[r, t, p]
        )
        g.obj_diviv[g.Rtp[r, t, p]] = g.stp_div["2", r, t, p] * (
            1 + g.rtp_capvl[r, t, p]
        )
        g.obj_diviii[g.Rtp[r, t, p]] = g.stp_div["3", r, t, p] * (
            1 + g.rtp_capvl[r, t, p]
        )

    def exec10(self) -> None:
        g = self.tc
        g.pastsum.setRecords(None)
        g.Yk1.setRecords(None)

    def _complete_obj_pvt_and_fpd(self, linflo: str) -> None:
        g = self.tc
        r, t, cur = g.r, g.t, g.cur

        if linflo not in {"0", "1"}:
            raise ValueError(linflo, "None of [0,1]")

        if linflo == "1":
            g.fpd[t] = Sum(g.Tpulseyr[t, g.YEoh], g.tpulse[t, g.YEoh])
            g.obj_pvt[r, t, cur].where[g.Rdcur[r, cur]] = Sum(
                g.Tpulseyr[t, g.YEoh],
                g.tpulse[t, g.YEoh] * g.obj_disc[r, g.YEoh, cur],
            )
            g.coef_pvt[r, t] = Sum(g.GRcur[r, cur], g.obj_pvt[r, t, cur])

        if abs(g.altobj.toValue()) == 2:
            with Loop(g.GRcur[r, cur]):
                # Set up variable cost correction adjustment for ALT
                if linflo == "1":
                    g.obj_altv[r, t] = g.coef_pvt[r, t] / Sum(
                        g.Periodyr[t, g.YEoh], g.obj_disc[r, g.YEoh, cur]
                    )
                else:
                    g.obj_altv[r, t] = g.coef_pvt[r, t] / Sum(
                        g.Tpulseyr[t, g.YEoh],
                        g.tpulse[t, g.YEoh] * g.obj_disc[r, g.YEoh, cur],
                    )

    def _prepare_linearized_cost_coeffs(self, obj: str, linacc: str) -> None:
        g = self.tc
        r, t, tt, cur = g.r, g.t, g.tt, g.cur

        # Prepare linearized cost coefficients
        if linacc.upper() == "1":
            definition: Expression | Sum = Sum(
                g.Tpulseyr[t, g.YEoh].where[g.Tpulseyr[tt, g.YEoh]],
                g.tpulse[t, g.YEoh] * g.tpulse[tt, g.YEoh] * g.obj_disc[r, g.YEoh, cur],
            )
        elif linacc.upper() == "0":
            definition = Sum(
                g.Periodyr[t, g.YEoh].where[g.Tpulseyr[tt, g.YEoh]],
                g.tpulse[tt, g.YEoh] * g.obj_disc[r, g.YEoh, cur],
            )
        else:
            raise ValueError(linacc, "None of [0,1]")

        if obj.upper() == "ALT":
            definition = g.obj_altv[r, t] * definition

        g.obj_lint[r, t, tt, cur].where[g.Rdcur[r, cur]] = definition

    def _label_cpt(self) -> None:
        if self.arg1.upper() == "STP":
            self._label_stp()
            return

        linflo, iled, oblong = self.env.linflo, self.env.iled_GP, self.env.oblong
        self.tc.enqueue(self._square_objective_formulation, linflo, iled, oblong)

    def _square_objective_formulation(
        self, linflo: str, iled: bool, oblong: str
    ) -> None:
        g = self.tc
        r, v, t, tt, p, cur, ll = g.r, g.v, g.t, g.tt, g.p, g.cur, g.ll

        # Adjustments to COEF_CPT for square objective formulation
        g.pastsum[g.Rtp[r, v, p]].where[g.PrcCap[r, p]] = (
            g.b[v] + g.ncap_iled[r, v, p] + g.coef_rpti[r, v, p] * g.ncap_tlife[r, v, p]
        )
        g.fil2.setRecords(None)
        g.my_array.setRecords(None)
        g.Yk1.setRecords(None)
        with Loop(g.GRcur[r, cur]):
            g.r_df[r, v] = 1 / (1 + g.g_drate[r, v, cur])
        if g.intdefault["PASTI"].toValue():
            g.ncap_iled[r, g.Phyr[v], p].where[
                g.ncap_iled[r, v, p] > g.coef_iled[r, v, p]
            ] = log(
                1 - (1 - g.r_df[r, v]) * (g.ncap_iled[r, v, p] - g.coef_iled[r, v, p])
            ) / log(g.r_df[r, v])
        g.rb[r, t] = g.b[t]

        if linflo == "1":
            g.Yk1[t[ll], ll.lag(floor((g.lead[t] - 1) / 2))] = ~g.Miyr1[t]

        with Loop(g.GRcur[r, cur]):
            g.fil2[t] = g.r_df[r, t]
            if linflo == "1":
                with Loop(g.Yk1[t, g.year]):
                    g.z[...] = (
                        g.obj_disc[r, g.year, cur]
                        / Sum(g.Perdinv[t, ll], g.obj_disc[r, ll, cur])
                        * g.lead[t]
                    )
                    g.rb[r, t] = g.b[t] - log(g.z) / log(g.fil2[t])
            g.my_array[t] = g.e[t] + 1
            g.my_array[tt[t.lag(1)]] = g.rb[r, t]
            g.my_array[t] = 1 - g.fil2[t] ** (g.my_array[t] - g.rb[r, t] - 1e-8)
            iled_term = (
                1 - g.fil2[t] ** Max(0, g.b[v] + g.ncap_iled[r, v, p] - g.rb[r, t])
            ) / g.my_array[t]
            if iled:
                iled_term = iled_term.where[g.ncap_iled[r, v, p]]
            g.coef_cpt[g.RtpCptyr[r, v, t, p]].where[g.pastsum[r, v, p]] = (
                Min(
                    1,
                    (1 - g.fil2[t] ** (g.pastsum[r, v, p] - g.rb[r, t]))
                    / g.my_array[t],
                )
                - iled_term
            )

        g.coef_cpt[r, t, tt, p].where[
            (g.coef_cpt[r, t, tt, p] < 1 / 512).where[g.coef_cpt[r, t, tt, p]]
        ] = 0

        if oblong.upper() == "YES" or self.env.is_set("timestep"):
            self._label_done()
            return

        # Calculate additional cost due to trapezoidal periods
        g.pastsum[r, t, p].where[g.ncap_iled[r, t, p]] = 0
        with Loop(g.GRcur[r, cur]):
            g.fil2[t] = g.r_df[r, t]
            g.rtp_capvl[r, t, p].where[g.pastsum[r, t, p]] = (
                g.fil2[t] ** (g.rb[r, t] - g.b[t]) - 1
            ) / (1 - g.fil2[t] ** (Min(g.miyr_vl + 1, g.pastsum[r, t, p]) - g.b[t]))
        self._label_done()

    def _label_dofix(self) -> None:
        g = self.tc
        self.env.set_global("capwd", "OBJ_WD(R,CUR,K_EOH,JOT,K)*")
        self.env.set_global("capwd_GP", g.obj_wd[g.r, g.cur, g.KEoh, g.jot, g.k])

        self.tc.enqueue(self.exec11)

        # Convert INVSTEP to INVSPRED
        self.tc.enqueue(self.exec2)

        if not self.arg2:
            self.tc.enqueue(self.exec3)
            return

        self.tc.enqueue(self.exec4)
        self.tc.enqueue(self.exec5)

        if not self.tc.defined("PRC_RESID"):
            return

        self.tc.enqueue(self.exec6)

    def exec11(self) -> None:
        g = self.tc
        ll, k, jot, t = g.ll, g.k, g.jot, g.t

        # Collect all JOT headers whether or not genuine spreads
        # Genuine OBJ_1A / OBJ_1B spreads (JOT>1) for period T cannot start at B(T)
        g.Fil.setRecords(None)
        g.Fil[ll.lead(g.b[ll] - g.yearval[ll])].where[t[ll]] = True
        g.Kage.setRecords(None)
        g.Kage[k, jot].where[(~g.Fil[k]).where[g.Invstep[k, jot, k, jot]]] = True
        g.Kage[g.Fil[ll.lag(floor(Ord(jot) / 2))], jot].where[
            (Ord(jot) > 1).where[g.Invstep[g.Fil, jot, g.Fil, jot].where[g.Fil[ll]]]
        ] = True

    def _calculate_change_in_capacity(self, iled: bool) -> None:
        g = self.tc
        r, v, t, tt, p, cur = g.r, g.v, g.t, g.tt, g.p, g.cur

        # Adjustments to Divisors when trapezoidal periods
        # Calculate change in capacity value due to change in last period
        g.rtp_capvl.setRecords(None)
        with Loop(t.where[g.e[t] == g.miyr_vl]):
            g.pastsum[g.Rtp[r, tt, p]].where[
                (g.coef_cpt[r, tt, t, p] > 0).where[g.PrcCap[r, p]]
            ] = (
                g.b[tt]
                + g.ncap_iled[r, tt, p]
                + g.coef_rpti[r, tt, p] * g.ncap_tlife[r, tt, p]
            )
            with Loop(g.GRcur[r, cur]):
                g.f[...] = g.rb[r, t]
                g.my_f[...] = g.r_df[r, t]
                g.z[...] = 1 - g.my_f ** (g.miyr_vl - g.f + 1)
                iled_term = 1 - g.my_f ** Max(0, g.b[v] + g.ncap_iled[r, v, p] - g.f)
                if iled:
                    iled_term = iled_term.where[g.ncap_iled[r, v, p]]
                g.rtp_capvl[r, tt[v], p].where[g.pastsum[r, v, p]] = g.coef_pvt[
                    r, t
                ] * (
                    (Min(g.z, 1 - g.my_f ** (g.pastsum[r, v, p] - g.f)) - iled_term)
                    / g.z
                    - g.coef_cpt[r, v, t, p]
                )
        g.rtp_capvl[r, tt, p].where[g.rtp_capvl[r, tt, p]] = g.rtp_capvl[
            r, tt, p
        ] / Sum(
            g.Vnt[tt, g.YEoh[t]], g.coef_pvt[r, t] * Max(0, g.coef_cpt[r, tt, t, p])
        )
        g.pastsum.setRecords(None)

    def _label_stp(self) -> None:
        if self.env.linflo != "1":
            self.tc.enqueue(self._label_done)
            return

        self.tc.enqueue(self._calculate_change_in_capacity, iled=self.env.iled_GP)

        if self.env.oblong.upper() == "YES":
            self._label_update()
            self.tc.enqueue(self._label_done)
            return

        self.tc.enqueue(self.exec7)
        self._label_update()
        self.tc.enqueue(self._label_done)

    def _label_doinv(self) -> None:
        g = self.tc
        self.env.set_global("capjd", "OBJ_JD(R,CUR,K_EOH,JOT)*")
        self.env.set_global("capjd_GP", g.obj_jd[g.r, g.cur, g.KEoh, g.jot])
        self.tc.enqueue(self.exec8)
        self._label_dofix()

    def _label_update(self) -> None:
        self.tc.enqueue(self.exec9)
        self.tc.enqueue(self._label_done)

    def _label_done(self) -> None:
        self.exec10()


def coef_alt_lin_stp(
    *,
    obj: str,
    ctst: str,
    oblong: str,
) -> str:
    """Raw-GAMS twin of the ``STP`` path above.

    ``solve.stp`` splices this fragment into the middle of one still-untranslated
    raw block, so it cannot be expressed with GAMSPy statements until that module
    is translated; at that point it is replaced by ``CoefAltLin(arg1="STP")``,
    which emits exactly these statements.
    """
    linflo = ctst.upper() == "**EPS"
    linacc = obj.upper() == "LIN"
    obj_is_alt = obj.upper() == "ALT"

    if f"{oblong}{obj}".upper() == "YESALT":
        linacc = True

    iled = "$NCAP_ILED(R,V,P)"
    if f"{oblong}{int(linflo)}".upper() == "YES1":
        iled = ""

    # ---- blocks ----

    fpd_block = ""
    if linflo:
        fpd_block = """
  FPD(T) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH));
  OBJ_PVT(R,T,CUR)$RDCUR(R,CUR) = SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)); COEF_PVT(R,T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR));
"""

    altv_block = (
        """
  OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR));
"""
        if linflo
        else """
  OBJ_ALTV(R,T) = COEF_PVT(R,T) / SUM(TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));
"""
    )

    lint_expr = (
        "  SUM(TPULSEYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(T,Y_EOH)*TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
        if linacc
        else "  SUM(PERIODYR(T,Y_EOH)$TPULSEYR(TT,Y_EOH),TPULSE(TT,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR));"
    )

    trapezoid_block = ""
    if linflo:
        extra_block = ""
        if oblong.upper() != "YES":
            extra_block = """
* Calculate additional cost due to trapezoidal periods
  LOOP(G_RCUR(R,CUR),
    FIL2(T) = R_DF(R,T);
    PASTSUM(RTP(R,Y_EOH(T),P))$((NOT NCAP_ILED(R,T,P))$PRC_CAP(R,P)) =
      (FIL2(T)**(RB(R,T)-B(T))-1) /
      (1-FIL2(T)**MIN(MIYR_VL+1-B(T),COEF_RPTI(R,T,P)*NCAP_TLIFE(R,T,P))));
  RTP_CAPVL(R,T,P)$PASTSUM(R,T,P) =
      (1+RTP_CAPVL(R,T,P)) / (1+PASTSUM(R,T,P)) - 1;
"""

        trapezoid_block = rf"""
* Adjustments to Divisors when trapezoidal periods
  OPTION CLEAR=RTP_CAPVL;
  LOOP(T$(E(T) EQ MIYR_VL),
   PASTSUM(RTP(R,TT,P))$((COEF_CPT(R,TT,T,P) GT 0)$PRC_CAP(R,P)) =
       B(TT)+NCAP_ILED(R,TT,P)+COEF_RPTI(R,TT,P)*NCAP_TLIFE(R,TT,P);
   LOOP(G_RCUR(R,CUR), F = RB(R,T);
    MY_F = R_DF(R,T); Z = 1-MY_F**(MIYR_VL-F+1);
    RTP_CAPVL(R,TT(V),P)$PASTSUM(R,V,P) =
      COEF_PVT(R,T) *
      ((MIN(Z, 1-MY_F**(PASTSUM(R,V,P)-F))
        - (1-MY_F**MAX(0,B(V)+NCAP_ILED(R,V,P)-F)){iled}) / Z
        - COEF_CPT(R,V,T,P))));
  RTP_CAPVL(R,TT,P)$RTP_CAPVL(R,TT,P) =
      RTP_CAPVL(R,TT,P) /
      SUM(VNT(TT,Y_EOH(T)),COEF_PVT(R,T)*MAX(0,COEF_CPT(R,TT,T,P)));
  OPTION CLEAR=PASTSUM;
{extra_block}
  OBJ_DIVI(RTP(R,T,P))   = STP_DIV('1',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIV(RTP(R,T,P))  = STP_DIV('2',R,T,P)*(1+RTP_CAPVL(R,T,P));
  OBJ_DIVIII(RTP(R,T,P)) = STP_DIV('3',R,T,P)*(1+RTP_CAPVL(R,T,P));
"""

    # ---- final string ----

    return rf"""
  OPTION CLEAR=PERDINV,CLEAR=TPULSE,CLEAR=TPULSEYR;

  PERDINV(YK(T,K))$(YEARVAL(K) > M(T)-LEAD(T)) = YES;
  OPTION CLEAR=YK1; YK1(T,Y_EOH)$(YEARVAL(T)<=YEARVAL(Y_EOH)) = YES;

  TPULSEYR(PERDINV(T,Y_EOH)) = YES;
  TPULSE(TPULSEYR(T,Y_EOH)) = 1-((M(T)-YEARVAL(Y_EOH))/LEAD(T))$(NOT MIYR_1(T));
  TPULSEYR(YK1(T,Y_EOH))$(YEARVAL(Y_EOH) < M(T)+LAGT(T)) = YES;
  TPULSE(TPULSEYR(YK1(T,LL))) = 1-TPULSE(T+1,LL);

{fpd_block}

  IF(ABS(ALTOBJ) EQ 2, LOOP(G_RCUR(R,CUR),
{altv_block}
  ));

  OBJ_LINT(R,T,TT,CUR)$RDCUR(R,CUR) =
{"  OBJ_ALTV(R,T) *" if obj_is_alt else ""}
{lint_expr}

{trapezoid_block}

  OPTION CLEAR=PASTSUM,CLEAR=YK1;
"""
