# eqobjfix_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJFIX the objective functions capacity fixed costs
# *   arg1 - mod or v# for the source code to be used
# *   - fixed O&M, including surveillance during decommissioning
# *   - tax
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Note that V=T in OBJ.DOC, but in the code V is assocated with the vintage year,
# *    that is the of investment as distinguished from T = the current MILESTONYR.
# *  - Combining all the Fix into a single equation at the moment
# *  - the test for relevant costs is done on the year of installation, perhaps should be Y-running year
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Card,
    Domain,
    Else,
    For,
    If,
    Loop,
    Ord,
    Parameter,
    Set,
    Smax,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, Round, ceil, floor, project, same_as

from core import prepret_dsc
from core.base_class import GamsClass
from core.coef_alt_lin import CoefAltLin
from core.utils import resolve_ctst
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Number
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjfixMod(GamsClass):
    """Translation unit for eqobjfix.mod."""

    # Instance attributes
    module_name: str = "eqobjfix_mod"
    gams_source: str = "eqobjfix.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal["exit", ""] = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.declarations()

        self.tc.enqueue(self.exec1, condition=self.env.validate == "YES")
        self.env.set_scoped("zhalf", "CEIL(Z/2-.5)")
        self.env.set_scoped("zhalf_GP", ceil(g.z / 2 - 0.5))
        self.env.set_scoped("istep", "IPD(T)")
        self.env.set_scoped("istep_GP", g.ipd[g.t])
        if self.env.ctst != "":
            self.env.set_scoped("istep", "MIN(IPD(T),ROUND(Z))")
            self.env.set_scoped("istep_GP", Min(g.ipd[g.t], Round(g.z)))
            self.env.set_scoped("zhalf", "FLOOR(ROUND(Z)/2)")
            self.env.set_scoped("zhalf_GP", floor(Round(g.z) / 2))

        self.tc.enqueue(
            self.exec_loop,
            ctst=self.env.ctst,
            zhalf=self.env.zhalf_GP,
            istep=self.env.istep_GP,
            condition=self.env.validate == "YES",
        )

        # * Commissioning years
        if self.env.ctst.upper() != "":
            self.include(
                CoefAltLin(
                    self.tc,
                    self.env,
                    arg1="FIX",
                    arg2="*",
                )
            )

        self.tc.enqueue(self.exec2)

        # * Reset OBJ_DIVIV to be the year divisor in the equation
        # * Only single commissioning year B(V)+ILED is taken for PASTMILE
        if self.env.ctst.upper() != "":
            pass
        else:
            self.tc.enqueue(
                self.exec3,
                ctst=self.env.ctst,
                condition=self.env.validate == "YES",
            )

        assert self.arg1.upper() in {
            "",
            "EXIT",
        }, f"Expected empty string or 'exit', but got '{self.arg1}'"

        if self.arg1.upper() == "EXIT":
            return

        self.define_equation(
            eq=self.env.eq,
            sow=self.env.sow_GP,
            capwd=self.env.capwd_GP,
            varv=self.env.varv_GP,
            sws=self.env.sws_GP,
            vart=self.env.vart_GP,
            var=self.env.var,
            condition1=self.env.validate == "YES",
            condition2=self.tc.defined("VNRET"),
        )

    def declarations(self: EqobjfixMod) -> None:
        g = self.tc
        m = g.container

        r, Reg, allyear, p, prc, age, j, cur = (
            g.r,
            g.Reg,
            g.allyear,
            g.p,
            g.prc,
            g.age,
            g.j,
            g.cur,
        )

        # * For loop controls
        g.ObjFcur = Set(m, name="OBJ_FCUR", domain=[Reg, allyear, p, cur])
        # * OBJ coefficient SUM control set with the 3 ALLYEAR indexes in sequence =
        # *   Y-running OBJ year, V-variables' investment period, K-cost value counter & index
        g.ObjSumiv = Set(m, name="OBJ_SUMIV", domain=[allyear, r, allyear, p, age, age])
        g.ObjSumivs = Set(
            m, name="OBJ_SUMIVS", domain=[r, allyear, p, allyear, allyear]
        )
        # * Shaping controls
        g.RtpShape = Set(m, name="RTP_SHAPE", domain=[Reg, allyear, prc, j, j, j])
        # * Fixed cost year span divisor
        g.obj_diviv = Parameter(m, name="OBJ_DIVIV", domain=[Reg, allyear, prc])
        # * Present value factor of technical life
        g.obj_life = Parameter(m, name="OBJ_LIFE", domain=[allyear, Reg, age, age, cur])

    def exec1(self: EqobjfixMod, condition: bool) -> None:
        # *UR: 09/30/01
        g = self.tc
        r, v, t, p, j, age, cur = g.r, g.v, g.t, g.p, g.j, g.age, g.cur
        Rtp, ObjYes, ObjFcur, RtpShape = g.Rtp, g.ObjYes, g.ObjFcur, g.RtpShape

        # * if some relevant cost
        ObjFcur[Rtp[r, v, p], cur].where[
            macro.obj_fom_GP(r, v, p, cur)
            + macro.obj_ftx_GP(r, v, p, cur)
            + macro.obj_fsb_GP(r, v, p, cur)
        ] = True
        # * Decommissioning
        ObjFcur[Rtp[r, v, p], cur].where[macro.obj_dlagc_GP(r, v, p, cur)] = True
        project(source=ObjFcur, target=ObjYes)
        ObjYes[g.RtpOff[r, t, p]].where[~g.ncap_pasti[r, t, p]] = False

        # * Set up the rounded lifetimes; round half years down:
        g.obj_diviv[ObjYes[r, v, p]] = Max(
            1, Min(Card(age), ceil(g.ncap_tlife[r, v, p] - 0.5))
        )
        g.obj_diviv[ObjYes[r, g.PyrS[v], p]].where[g.prc_resid[r, "0", p]] = Max(
            2, Smax(t.where[(g.prc_resid[r, t, p] > 0)], g.e[t]) - g.miyr_v1 + 2
        )
        # *======================================================================================
        # * Apply SHAPE to OBJ_YES:
        # *--------------------------------------------------------------------------------------
        RtpShape.setRecords(None)
        with Loop(same_as(j, "1")):
            RtpShape[
                ObjYes[Rtp],
                "1",
                j + Max(0, g.ncap_fomx[Rtp] - 1),
                j + Max(0, g.ncap_fomm[Rtp] - 1),
            ].where[g.ncap_fomx[Rtp] + g.ncap_fomm[Rtp] + g.ncap_cpx[Rtp]] = True
            RtpShape[
                ObjYes[Rtp],
                "2",
                j + Max(0, g.ncap_ftaxx[Rtp] - 1),
                j + Max(0, g.ncap_ftaxm[Rtp] - 1),
            ].where[g.ncap_ftaxx[Rtp] + g.ncap_ftaxm[Rtp]] = True
            RtpShape[
                ObjYes[Rtp],
                "3",
                j + Max(0, g.ncap_fsubx[Rtp] - 1),
                j + Max(0, g.ncap_fsubm[Rtp] - 1),
            ].where[g.ncap_fsubx[Rtp] + g.ncap_fsubm[Rtp]] = True

        project(source=RtpShape, target=g.RtpIshpr)
        RtpShape[RtpShape[Rtp, j, "1", "1"]].where[~g.ncap_cpx[Rtp]] = False
        if condition:
            g.RtpIshpr[Rtp] = True

    def exec_loop(
        self: EqobjfixMod,
        ctst: Literal["", "**EPS", "**0", "1"],
        zhalf: MathOp,
        istep: MathOp | ImplicitParameter,
        condition: bool,
    ) -> None:
        g = self.tc
        r, p, v, t, ll, k = g.r, g.p, g.v, g.t, g.ll, g.k
        age, jot, life, cur = g.age, g.jot, g.life, g.cur
        Obj1a, Obj1b, Obj2a, Obj2b, ObjYes = (
            g.Obj1a,
            g.Obj1b,
            g.Obj2a,
            g.Obj2b,
            g.ObjYes,
        )
        ObjSumiv, ObjSumivs, Y = g.ObjSumiv, g.ObjSumivs, g.Y

        # *===============================================================================
        # * Case IV/V.1.a: Fixed O&M/Tax ILEDt <= ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *===============================================================================
        with Loop(same_as(age, "1")):
            # * [AL] 05/08/2003: small further speed-up
            if not condition:
                # * Set period parameters for Case 1a:
                g.fil2[v] = (g.ipd[v] - 1).where[t[v]]
                g.my_array[v] = (
                    g.b[v] - g.yearval[v] + (g.m[v] - g.b[v] - g.fil2[v]).where[t[v]]
                )
                # * The first commissioning year is LL+MY_ARRAY(LL) and the spread is AGE+FIL2(V)
                ObjSumiv[
                    ll + g.my_array[ll],
                    Obj1a[ObjYes[r, v[ll], p]],
                    age + g.fil2[v],
                    age + (g.obj_diviv[r, v, p] - 1),
                ] = True
            else:
                # * create square for investment costing if validating MARKAL
                g.my_array[v] = Max(g.miyr_v1, g.b[v]) - g.yearval[v]
                ObjSumiv[
                    ll + g.my_array[ll],
                    Obj1a[ObjYes[r, v[ll], p]],
                    age + (g.ncap_elife[r, v, p] - 1),
                    "1",
                ] = True

        # *===============================================================================
        # * Case IV/V.1.b: Fixed O&M/Tax ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *===============================================================================
        # * if some relevant cost
        with Loop(same_as(age, "1")):
            if not condition:
                with Loop(Obj1b[ObjYes[r, t[ll], p]]):
                    g.z[...] = g.ncap_tlife[r, t, p]
                    # * Slightly different handling according to objective formulation
                    with If((Round(g.z) - resolve_ctst(g.ipd[t], ctst)) <= 0):
                        g.my_f[...] = g.obj_diviv[r, t, p] - 1
                        g.f[...] = g.b[t] - zhalf - g.yearval[t]
                        g.z[...] = Round(g.coef_rpti[r, t, p] * g.z) - 1
                        # * The first commissioning year is LL+F and the spread is AGE+Z
                        ObjSumiv[ll + g.f, r, t, p, age + g.z, age + g.my_f] = True
                    with Else():  # type: ignore[no-untyped-call]
                        g.cnt[...] = istep
                        g.obj_d[...] = g.cnt - 1
                        g.my_f[...] = g.b[t] - g.yearval[t] - floor(g.cnt / 2)
                        with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                            g.f[...] = g.my_f
                            g.my_f[...] = g.f + g.z
                            g.cnt[...] = Round(g.my_f) - Round(g.f) - 1
                            ObjSumiv[ll + g.f, r, t, p, age + g.obj_d, age + g.cnt] = (
                                True
                            )
            else:
                # * create square for investment costing if validating MARKAL
                ObjSumiv[
                    ll + g.my_array[ll],
                    Obj1b[ObjYes[r, t[ll], p]],
                    age + (g.coef_rpti[r, t, p] * g.ncap_elife[r, t, p] - 1),
                    "1",
                ] = True

        # *===============================================================================
        # * Case IV/V.2.a: Fixed O&M/Tax ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *===============================================================================
        # * if some relevant cost
        # *V05c 981007 - treat PAST == MILE except take cost from decision/capacity installed
        with Loop(same_as(age, "1")):
            # * The commissioning year is B(V)+ILED for both MILESTONYR and PASTMILE, spread is '1'
            ObjSumiv[
                ll + (g.b[ll] + g.ncap_iled[r, ll, p] - g.yearval[ll]),
                ObjYes[Obj2a[r, v[ll], p]],
                "1",
                age + (g.obj_diviv[r, ll, p] - 1),
            ] = True

        # *-----------------------------------------------------------------------------
        # * Case IV.2.a: Surveillance ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *-----------------------------------------------------------------------------
        # * if some relevant cost
        with Loop(
            Domain(Obj2a[r, v[ll], p], cur).where[macro.obj_dlagc_GP(r, v, p, cur)]
        ):
            g.my_f[...] = g.b[v] + g.ncap_iled[r, v, p]
            g.f[...] = Round(g.my_f + g.ncap_tlife[r, v, p])
            g.z[...] = g.f + g.ncap_dlag[r, v, p]
            g.my_f[...] = g.my_f - g.yearval[v]
            ObjSumivs[r, v, p, ll + g.my_f, Y].where[
                (g.yearval[Y] >= g.f) & (g.yearval[Y] < g.z)
            ] = True

        # *===============================================================================
        # * Case IV/V.2.b: Fixed O&M/Tax ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *===============================================================================
        # * determine the number of repeated investments, if some relevant cost
        with Loop(same_as(age, "1")):  # noqa: SIM117
            with Loop(Obj2b[ObjYes[r, t[ll], p]]):
                g.z[...] = g.ncap_tlife[r, t, p]
                g.my_f[...] = Round(g.b[t] + g.ncap_iled[r, t, p]) - g.yearval[t]
                with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                    # * The commissioning year is LL+F and the spread is 1
                    g.f[...] = g.my_f
                    g.my_f[...] = g.f + g.z
                    g.cnt[...] = Round(g.my_f) - Round(g.f) - 1
                    ObjSumiv[ll + g.f, r, t, p, "1", age + g.cnt] = True

        # *-----------------------------------------------------------------------------
        # * Case IV.2.b: Surveillance ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *-----------------------------------------------------------------------------
        # * determine the number of repeated investments, if some relevant cost
        with Loop(  # noqa: SIM117
            Domain(Obj2b[r, t[ll], p], cur).where[macro.obj_dlagc_GP(r, t, p, cur)]
        ):
            with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                g.my_f[...] = (
                    g.b[t]
                    + g.ncap_iled[r, t, p]
                    + (g.obj_c - 1) * g.ncap_tlife[r, t, p]
                )
                g.f[...] = Round(g.my_f + g.ncap_tlife[r, t, p])
                g.z[...] = g.f + g.ncap_dlag[r, t, p]
                g.my_f[...] = g.my_f - g.yearval[t]
                ObjSumivs[r, t, p, ll + g.my_f, Y].where[
                    (g.yearval[Y] >= g.f) & (g.yearval[Y] < g.z)
                ] = True

        # *------------------------------------------------------------------------------
        # * forget about PASTINV charges if not PASTInvestment
        # *------------------------------------------------------------------------------
        ObjSumiv[ObjSumiv[g.KEoh, r, g.Pastmile, p, jot, age]].where[
            ~g.ncap_pasti[r, g.Pastmile, p]
        ] = False
        ObjSumivs[ObjSumivs[r, g.Pastmile, p, k, Y]].where[
            ~g.ncap_pasti[r, g.Pastmile, p]
        ] = False
        # *-----------------------------------------------------------------------------*
        # * precalculation of the PVF sum for the simple case is usually efficient
        with Loop(Domain(ObjSumiv[k, r, v, p, jot, life], g.Rdcur[r, cur])):
            g.obj_life[k, r, jot, life, cur] = 1
        project(source=g.obj_life, target=g.Kage, direction="left")
        g.Invstep[
            g.Kage[ll, jot], ll + (Ord(age) - 1), age + (Ord(jot) - Ord(age))
        ].where[g.Opyear[jot, age]] = True
        with Loop(g.Kage[k, jot]):
            g.obj_life[ll, r, jot, life, cur].where[g.Invstep[k, jot, ll, jot]] = (
                sparse(g.obj_life[k, r, jot, life, cur])
            )
        g.obj_life[k[ll], r, jot, life, cur].where[g.obj_life[k, r, jot, life, cur]] = (
            Sum(
                Domain(g.Opyear[life, age], g.YEoh[ll + (Ord(age) - 1)]),  # type: ignore[index]
                g.obj_disc[r, g.YEoh, cur],
            )
        )

    def exec2(self: EqobjfixMod) -> None:
        g = self.tc
        ll, jot, k = g.ll, g.jot, g.k

        g.Invspred[g.Kage[ll, jot], k, k].where[g.Invstep[ll, jot, k, jot]] = True

    def exec3(
        self: EqobjfixMod, ctst: Literal["", "**EPS", "**0", "1"], condition: bool
    ) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p
        Obj1a, Obj1b, ObjYes = g.Obj1a, g.Obj1b, g.ObjYes

        g.obj_diviv[ObjYes[r, g.Pastmile, p]] = 1
        g.obj_diviv[ObjYes[r, t, p]].where[~Obj1b[r, t, p]] = (
            1 + (g.ipd[t] - 1).where[Obj1a[r, t, p]]
        )
        if g.altobj.toValue():
            g.obj_diviv[Obj1b[ObjYes[r, t, p]]].where[
                (Round(g.ncap_tlife[r, t, p]) - resolve_ctst(g.ipd[t], ctst)) > 0
            ] = g.ipd[t]
        if condition:
            g.obj_diviv[ObjYes[r, t, p]] = 1
        # *-----------------------------------------------------------------------------*
        ObjYes.setRecords(None)
        g.Ykage.setRecords(None)

    def define_equation(
        self: EqobjfixMod,
        eq: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        capwd: ImplicitParameter | Number,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias, ...] | tuple[()],
        vart: tuple[str, ImplicitSet | None],
        var: str,
        condition1: bool,
        condition2: bool,
    ) -> None:
        g = self.tc
        r, v, t, p, cur, k, ll = g.r, g.v, g.t, g.p, g.cur, g.k, g.ll
        age, jot, life, j, jj = g.age, g.jot, g.life, g.j, g.jj
        KEoh, YEoh, Y, obv = g.KEoh, g.YEoh, g.Y, g.obv
        ObjSumiv, ObjSumivs, RtpIshpr = g.ObjSumiv, g.ObjSumivs, g.RtpIshpr

        eq_objfix, sow = macro.EQ_OBJFIX_GP(eq, sow)
        VAR_OBJ = g.get_variable(f"{var}_OBJ")

        capacity = (
            macro.VAR_NCAP_GP(varv, r, v, p, sws).where[g.Milestonyr[v]]
            + g.ncap_pasti[r, v, p].where[g.Pastyear[v]]
        )

        def shaped(cost: ImplicitParameter, index: str) -> Expression:
            """cost * (1+SUM(RTP_SHAPE(R,V,P,index,J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))"""
            return cost * (
                1
                + Sum(
                    g.RtpShape[r, v, p, index, j, jj],
                    g.shape[j, age] * g.multi[jj, YEoh] - 1,
                )
            )

        # *===============================================================================
        # * Generate Fixed Cost equation summing over all active indexes by region and currency
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * Cases IV - Fixed O&M including surveillance during decommissioning, V - Taxes
        # *------------------------------------------------------------------------------
        # * Fixed O&M Cost and Taxes
        lhs: Expression | Sum = Sum(
            ObjSumiv[KEoh, r, v, p, jot, life].where[~RtpIshpr[r, v, p]],
            Sum(
                g.Invspred[KEoh, jot, ll, k],
                g.obj_life[ll, r, jot, life, cur]
                * capwd
                * (
                    macro.obj_fom_GP(r, k, p, cur)
                    + macro.obj_ftx_GP(r, k, p, cur)
                    - macro.obj_fsb_GP(r, k, p, cur)
                ),
            )
            * capacity
            / g.obj_diviv[r, v, p],
        )

        shaped_costs = (
            g.obj_disc[r, YEoh, cur]
            * (
                1
                + Sum(g.Periodyr[t, YEoh], g.rtp_cpx[r, v, p, t]).where[
                    g.ncap_cpx[r, v, p]
                ]
            )
            * capwd
            * (
                shaped(macro.obj_fom_GP(r, k, p, cur), "1")
                + shaped(macro.obj_ftx_GP(r, k, p, cur), "2")
                - shaped(macro.obj_fsb_GP(r, k, p, cur), "3")
            )
        )
        if condition1:
            # * [UR] 07.10.2003: for validating MARKAL using VAR_CAP instead of VAR_NCAP+NCAP_PASTI,
            # *                  since it is possible in MARKAL to decommission capacity of demand
            # *                  devices (DMD)

            shaped_costs = shaped_costs * (
                Sum(g.Periodyr[t[v], YEoh], macro.VAR_CAP_GP(vart, r, t, p, sws)).where[
                    g.Obj1a[r, v, p] + g.Obj1b[r, v, p]
                ]
                + capacity.where[g.Obj2a[r, v, p] + g.Obj2b[r, v, p]]
            )

        shaped_sum: Expression | Sum = Sum(
            Domain(
                g.Invspred[KEoh, jot, ll, k],
                g.Opyear[life, age],
                YEoh[ll + (Ord(age) - 1)],  # type: ignore[index]
            ),
            shaped_costs,
        )
        if not condition1:
            shaped_sum = shaped_sum * capacity / g.obj_diviv[r, v, p]

        lhs = lhs + Sum(ObjSumiv[KEoh, RtpIshpr[r, v, p], jot, life], shaped_sum)

        if condition2:
            lhs = lhs + prepret_dsc.objfix_GP(g=g, capwd=capwd, vart=vart, sws=sws)

        # * Decommissioning Surveillance
        lhs = lhs + Sum(
            ObjSumivs[r, v, p, k, Y],
            g.obj_disc[r, Y, cur]
            * macro.obj_dlagc_GP(r, k, p, cur)
            # * Case 2.a-b
            * (
                macro.VAR_NCAP_GP(varv, r, v, p, sws).where[g.Milestonyr[v]]
                + g.ncap_pasti[r, v, p].where[g.Pastyear[v] & g.Obj2a[r, v, p]]
            ),
        )

        eq_objfix[g.Rdcur[r, cur], *sow] = lhs == Sum(
            obv, g.sum_obj["OBJFIX", obv] * VAR_OBJ[r, obv, cur, *sow]
        )
        # * Clears in INITCLR.MOD
