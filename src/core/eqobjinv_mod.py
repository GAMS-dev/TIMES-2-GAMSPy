# eqobjinv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJINV the objective functions on investments
# *   - Investment Costs
# *   - Investmnet Tax/Subsidies
# *   - Decommissioning
# *=============================================================================*
# *GaG Questions/Comments:
# *  - Note that V=T in OBJ.DOC, but in the code V is assocated with the vintage year,
# *    that is the year of investment as distinguished from T = the current MILESTONYR
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *  - combining all the INVs into a single equation at the moment
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Alias,
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
)
from gamspy.math import Max, Min, Round, ceil, floor, project, rpower, same_as

from core.base_class import GamsClass
from core.coef_alt_lin import CoefAltLin
from core.utils import resolve_ctst, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression, Number
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from core.utils import SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjinvMod(GamsClass):
    """Translation unit for eqobjinv.mod."""

    module_name: str = "eqobjinv_mod"
    gams_source: str = "eqobjinv.mod"

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
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        # Discounting shift is zero unless the user says otherwise:
        if not self.env.is_set("discshift"):
            self.env.set_global("discshift", 0.0)

        # If annual cost should be reported for TLIFE years and not just ELIFE,
        # change INVLIF and DECLIF to TLIFE and DLIFE instead of ELIFE and DELIF
        self.env.set_global("invlif", "ELIFE")
        self.env.set_global("declif", "DELIF")
        g = self.tc
        m = g.container

        r, reg, allyear, p, age, year, life, prc, cur = (
            g.r,
            g.Reg,
            g.allyear,
            g.p,
            g.age,
            g.year,
            g.life,
            g.prc,
            g.cur,
        )

        # * For loop controls
        g.jot = Alias(m, name="JOT", alias_with=g.age)
        g.obj_c = Parameter(m, name="OBJ_C", records=0)
        g.obj_d = Parameter(m, name="OBJ_D", records=0)
        # * OBJ coefficient SUM control set with the ALLYEAR indexes in sequence =
        # *   V - investment vintage year, K - commissioning index, Y - decommissioning index
        g.ObjSumii = Set(m, name="OBJ_SUMII", domain=[r, allyear, p, age, allyear, age])
        g.ObjSumiii = Set(
            m, name="OBJ_SUMIII", domain=[r, allyear, p, allyear, year, allyear]
        )
        g.ObjYes = Set(m, name="OBJ_YES", domain=[reg, allyear, p])
        g.ObjI2 = Set(m, name="OBJ_I2", domain=[reg, allyear, p])
        g.Ykage = Set(m, name="YKAGE", domain=[allyear, allyear, age])
        g.Kage = Set(m, name="KAGE", domain=[allyear, age])
        g.ObjSpred = Set(m, name="OBJ_SPRED", domain=[r, allyear, p, age])
        g.Invstep = Set(m, name="INVSTEP", domain=[allyear, age, allyear, age])
        g.Invspred = Set(m, name="INVSPRED", domain=[allyear, age, allyear, allyear])
        g.obj_pasti = Parameter(m, name="OBJ_PASTI", domain=[reg, allyear, p, cur])
        g.salv_inv = Parameter(m, name="SALV_INV", domain=[reg, allyear, prc, allyear])
        g.cor_salvi = Parameter(m, name="COR_SALVI", domain=[reg, allyear, prc, cur])
        g.cor_salvd = Parameter(m, name="COR_SALVD", domain=[reg, allyear, prc, cur])
        g.obj_divi = Parameter(m, name="OBJ_DIVI", domain=[reg, allyear, prc])
        g.obj_diviii = Parameter(m, name="OBJ_DIVIII", domain=[reg, allyear, prc])
        g.ObjIdc = Set(m, name="OBJ_IDC", domain=[r, allyear, p, life, allyear, age])
        g.obj_iad = Parameter(m, name="OBJ_IAD", domain=[r, cur])

        self.tc.enqueue(
            self.exec1,
            etl_yes=(self.env.etl.upper() == "YES"),
            invlif=self.env.invlif,
            discshift=self.env.discshift,
        )

        self.env.set_scoped("zhalf", "CEIL(Z/2-.5)")
        self.env.set_scoped("zhalf_GP", ceil(g.z / 2 - 0.5))
        self.env.set_scoped("istep", "IPD(T)")
        self.env.set_scoped("istep_GP", g.ipd[g.t])
        if self.env.ctst != "":
            self.env.set_scoped("zhalf", "FLOOR(ROUND(Z)/2)")
            self.env.set_scoped("zhalf_GP", floor(Round(g.z) / 2))
            self.env.set_scoped("istep", "MIN(IPD(T),ROUND(Z))")
            self.env.set_scoped("istep_GP", Min(g.ipd[g.t], Round(g.z)))

        self.tc.enqueue(self.exec2)

        if self.env.validate == "YES":
            self.tc.enqueue(self._label_m2t)
        else:
            self.tc.enqueue(self.exec3)

        self.tc.enqueue(self._label_cont)
        # *===============================================================================
        # * Case I/II.1.b: Investment/Tax&Sub ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *   Note - no PASTINV as TLIFE always >= D(t) which = 1
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * build repeated investment blocks until end of lifetime
        # *------------------------------------------------------------------------------
        if self.env.validate == "YES":
            self.tc.enqueue(self._label_m2t_2)
        else:
            self.tc.enqueue(
                self.exec4,
                ctst=self.env.ctst,
                zhalf=self.env.zhalf_GP,
                istep=self.env.istep_GP,
            )
        self.tc.enqueue(self._label_cont_2)
        if self.env.ctst != "":
            self.include(CoefAltLin(self.tc, self.env, arg1="INV"))
        self.tc.enqueue(self.exec6)
        self.tc.enqueue(self._label_cont_2b)
        if self.env.ctst == "":
            self.tc.enqueue(
                self.exec5,
                validate_yes=(self.env.validate == "YES"),
                ctst=self.env.ctst,
            )
        self.tc.enqueue(self._label_clrs)

        assert self.arg2.upper() in {
            "",
            "EXIT",
        }, f"Expected empty string or 'exit', but got '{self.arg2}'"

        if self.arg2.upper() == "EXIT":
            return

        self.define_equation(
            eq=self.env.eq,
            capjd=self.env.capjd_GP,
            sow=self.env.sow_GP,
            sws=self.env.sws_GP,
            swd=self.env.swd_GP,
            vart=self.env.vart_GP,
            varv=self.env.varv_GP,
            var=self.env.var,
            etl_yes=(self.env.etl == "YES"),
            stages_yes=(self.env.stages.upper() == "YES"),
        )

    def exec1(self: EqobjinvMod, etl_yes: bool, invlif: str, discshift: float) -> None:
        g = self.tc
        r, v, t, p, ll, cur = g.r, g.v, g.t, g.p, g.ll, g.cur
        age, life = g.age, g.life
        Rtp, ObjIcur, ObjYes, ObjSums3, ObjI2, ObjSpred = (
            g.Rtp,
            g.ObjIcur,
            g.ObjYes,
            g.ObjSums3,
            g.ObjI2,
            g.ObjSpred,
        )
        ncap_invlif = g.get_parameter(f"NCAP_{invlif}")
        ncap_drate, obj_rfr, g_drate, ncap_elife = (
            g.ncap_drate,
            g.obj_rfr,
            g.g_drate,
            g.ncap_elife,
        )

        # *===============================================================================
        # * Hold on to those RTPs for which some investment related cost is provided
        # *===============================================================================
        # * Investment
        Rtp[r, g.Pastmile, p].where[g.ncap_pasti[r, g.Pastmile, p] == 0] = False
        ObjIcur[Rtp[r, v, p], cur].where[
            macro.obj_icost_GP(r, v, p, cur)
            + macro.obj_isub_GP(r, v, p, cur)
            + macro.obj_itax_GP(r, v, p, cur)
        ] = True
        # * if ETL technology then going to do it as well
        if etl_yes:
            ObjIcur[Rtp[r, v, g.Teg], cur].where[g.GRcur[r, cur]] = True
        # * Decommissioning
        ObjIcur[Rtp[r, v, p], cur].where[macro.obj_dcost_GP(r, v, p, cur)] = True
        with Loop(cur):
            ObjSums3[Rtp[r, v, p]].where[macro.obj_dcost_GP(r, v, p, cur)] = True
        with Loop(Domain(Rtp, g.Com).where[g.ncap_ocom[Rtp, g.Com]]):
            ObjSums3[Rtp] = True
        # * Currency independent OBJ_YES
        ObjIcur[g.RtpOff, cur].where[~g.ncap_pasti[g.RtpOff]] = False
        ObjIcur[r, ll, p, cur].where[~g.Rdcur[r, cur]] = False
        project(source=ObjIcur, target=ObjYes)
        ObjYes[ObjSums3] = True

        # * Correct small TLIFE and DLIFE values, because rounded values are used as divisors
        g.ncap_tlife[ObjYes[r, v, p]].where[Round(g.ncap_tlife[r, v, p]) <= 0] = 1
        ncap_elife[ObjYes[r, v, p]].where[Round(ncap_elife[r, v, p]) <= 0] = 1
        g.ncap_dlife[ObjSums3[r, v, p]].where[Round(g.ncap_dlife[r, v, p]) <= 0] = 1
        g.ncap_delif[ObjSums3[r, v, p]] = Max(1, g.ncap_delif[r, v, p])
        # * Classify processes into I1 / I2 Cases
        ObjI2[Rtp].where[g.ncap_iled[Rtp]] = True
        with Loop(same_as(life, "1")):
            ObjSpred[
                ObjYes[r, v, p],
                life + Max(0, Min(Card(age), ncap_invlif[r, v, p]) - 1),
            ] = True
        # *------------------------------------------------------------------------------
        # * COR_SALVI can be used to take into account technology-specific discount rate
        # * Take also into account a user-defined discounting shift (0/0.5/1 years):
        g.cor_salvi[ObjIcur[r, v, p, cur]] = (
            (
                rpower((1 + ncap_drate[r, v, p]) / (1 + obj_rfr[r, v, cur]), discshift)
                * (
                    (1 - 1 / (1 + ncap_drate[r, v, p]))
                    * (1 - rpower(1 + obj_rfr[r, v, cur], -ncap_elife[r, v, p]))
                )
                / (
                    (1 - 1 / (1 + obj_rfr[r, v, cur]))
                    * (1 - rpower(1 + ncap_drate[r, v, p], -ncap_elife[r, v, p]))
                )
                - 1
            ).where[ncap_drate[r, v, p] > 0]
            + 1
        ) * rpower(1 + g_drate[r, v, cur], discshift)
        g.cor_salvi[ObjIcur[ObjI2[r, v, p], cur]] = g.cor_salvi[r, v, p, cur] / rpower(
            1 + g_drate[r, v, cur], discshift
        )
        # * OBJ_CRF/OBJ_CRFD must now be based on G_DRATE because we use COR_SALVI and COR_SALVD for the correction
        g.obj_crf[ObjIcur[r, v, p, cur]] = (
            g.cor_salvi[r, v, p, cur]
            * (1 - (1 / (1 + g_drate[r, v, cur])))
            / (1 - rpower(1 + g_drate[r, v, cur], -Round(ncap_invlif[r, v, p])))
        )
        # *------------------------------------------------------------------------------
        # * OBJ_PASTI is the correction for past investments (similar to SALV_INV fraction)
        g.obj_pasti[ObjIcur[Rtp[r, g.Pastyear[v], p], cur]] = g.ncap_pasti[
            r, v, p
        ] * Max(
            0,
            Min(
                1,
                (
                    rpower(
                        1 + g_drate[r, v, cur],
                        g.yearval[v]
                        + Round(g.ncap_iled[r, v, p])
                        - g.minyr
                        + ncap_invlif[r, v, p],
                    )
                    - 1
                )
                / (rpower(1 + g_drate[r, v, cur], ncap_invlif[r, v, p]) - 1),
            ),
        )
        # *------------------------------------------------------------------------------
        # * Operating years for all technical lifetimes
        g.z[...] = (
            Smax(Domain(Rtp[r, g.PyrS[v], p], t).where[g.prc_resid[r, t, p]], g.e[t])
            - g.miyr_v1
            + 2
        )
        g.maxlife[...] = Max(Smax(t, 2 * g.d[t]), g.z, ceil(g.maxlife))
        g.Opyear[life, age].where[
            (Ord(age) <= Ord(life)) & (Ord(life) <= g.maxlife)
        ] = True
        # *--------------------------------------------------------------------------------------

    def exec2(self: EqobjinvMod) -> None:
        g = self.tc
        r, v, p = g.r, g.v, g.p

        # *===============================================================================
        # * Case 1.a: ILEDt <= ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *===============================================================================
        g.Obj1a[g.Rtp[r, v, p]].where[
            (~g.ObjI2[r, v, p]) & (g.coef_rpti[r, v, p] < 1.01)
        ] = True
        # *------------------------------------------------------------------------------
        # * build trapazoid covering year and number of payment blocks for a process
        # *------------------------------------------------------------------------------
        # * - K is EACHYEAR
        # *     beginning from the
        # *       MAX(period length before the middle year of the current (investment)
        # *           period, or the current year - the economic lifetime + 1)
        # *     until the
        # *       MIN(middle year of the current (investment) period - 1, or the year
        # *           calculating)

    def _label_m2t(self: EqobjinvMod) -> None:
        g = self.tc
        r, v, p, life, Y = g.r, g.v, g.p, g.life, g.Y

        # * Y is investment year, V is cost basis year
        g.ObjSumii[g.ObjSpred[g.Obj1a[r, v, p], life], Y, "1"].where[
            g.yearval[Y] == g.b[v]
        ] = True

    def exec3(self: EqobjinvMod) -> None:
        g = self.tc
        r, v, t, p, ll, k, age, life = g.r, g.v, g.t, g.p, g.ll, g.k, g.age, g.life

        # * Set period parameters for Case 1a:
        g.fil2[v] = (g.ipd[v] - 1).where[t[v]]
        g.my_array[v] = (
            g.b[v] - g.yearval[v] + (g.m[v] - g.b[v] - g.fil2[v]).where[t[v]]
        )
        with Loop(same_as(age, "1")):
            # * K is both investment year and cost/commissioning year
            g.ObjSumii[
                g.ObjSpred[g.Obj1a[r, v[ll], p], life],
                k[ll + g.my_array[ll]],  # type: ignore[index]
                age + g.fil2[v],
            ] = True

    def _label_cont(self: EqobjinvMod) -> None:
        g = self.tc
        r, t, p = g.r, g.t, g.p

        # *===============================================================================
        # * Case 1.b: ILEDt <= ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *   Note - no PASTINV as TLIFE always >= D(t) which = 1
        # *===============================================================================
        g.Obj1b[g.Rtp[r, t, p]].where[(~g.ObjI2[r, t, p]) & (~g.Obj1a[r, t, p])] = True

    def _label_m2t_2(self: EqobjinvMod) -> None:
        g = self.tc
        r, t, p, ll, life, Y = g.r, g.t, g.p, g.ll, g.life, g.Y

        with Loop(g.ObjSpred[g.Obj1b[r, t[ll], p], life]):
            g.z[...] = g.ncap_tlife[r, t, p]
            with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                g.f[...] = g.b[t] + Round((g.obj_c - 1) * g.z) - g.yearval[t]
                # * Y is investment year, T is cost basis year
                g.ObjSumii[r, t, p, life, Y[ll + g.f], "1"] = True  # type: ignore[index]

    def exec4(
        self: EqobjinvMod,
        ctst: Literal["", "**EPS", "**0", "1"],
        zhalf: MathOp,
        istep: MathOp | ImplicitParameter,
    ) -> None:
        g = self.tc
        r, t, p, ll, k, age, life = g.r, g.t, g.p, g.ll, g.k, g.age, g.life

        with Loop(same_as(age, "1")):  # noqa: SIM117
            with Loop(g.ObjSpred[g.Obj1b[r, t[ll], p], life]):
                g.z[...] = g.ncap_tlife[r, t, p]
                # * Slightly different handling according to objective formulation
                with If((Round(g.z) - resolve_ctst(g.ipd[t], ctst)) <= 0):
                    g.f[...] = g.b[t] - zhalf - g.yearval[t]
                    g.z[...] = Round(g.coef_rpti[r, t, p] * g.z) - 1
                    # * LL+F is both first investment year and first cost/commissioning year
                    g.ObjSumii[r, t, p, life, k[ll + g.f], age + g.z] = True  # type: ignore[index]
                with Else():  # type: ignore[no-untyped-call]
                    g.cnt[...] = istep
                    g.f[...] = g.b[t] - g.yearval[t] - floor(g.cnt / 2)
                    g.cnt[...] = g.cnt - 1
                    with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                        g.ObjSumii[r, t, p, life, k[ll + g.f], age + g.cnt] = True  # type: ignore[index]
                        g.f[...] = g.f + g.z

    def _label_cont_2(self: EqobjinvMod) -> None:
        g = self.tc
        r, v, t, p, ll, cur = g.r, g.v, g.t, g.p, g.ll, g.cur
        age, jot, life, year = g.age, g.jot, g.life, g.year
        ObjSumii, ObjIdc, ObjSpred, ObjI2 = (
            g.ObjSumii,
            g.ObjIdc,
            g.ObjSpred,
            g.ObjI2,
        )

        # *===============================================================================
        # * Case 2.a: ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *===============================================================================
        g.Obj2a[ObjI2[r, v, p]].where[g.coef_rpti[r, v, p] <= 1] = True
        # *===============================================================================
        # * Case I/II.2.a: Investment/Tax&Sub ILEDt > ILEDmin,t and TLIFEt + ILEDt >= D(t)
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * build trapazoid covering year and number of payment blocks for a process
        # * - K is EACHYEAR
        # *    for MILESTONYR or PASTYEAR
        # *      beginning from the
        # *        MAX(beginning of the period, or the current year - the economic lifetime + 1)
        # *      until the
        # *        MIN(beginning of the period + leadtime - 1, or the year calculating)
        # *------------------------------------------------------------------------------
        # * there is a relevant cost
        with Loop(same_as(age, "1")):  # noqa: SIM117
            with Loop(ObjSpred[g.Obj2a[r, v[ll], p], life]):
                g.z[...] = g.ncap_iled[r, v, p]
                g.my_f[...] = g.b[v] - g.yearval[v] + g.z
                # * LL+F is investment year; LL+MY_F is commissioning year (cost basis)
                ObjIdc[r, v, p, life, ll + g.my_f, age + Max(0, g.z - 1)] = True
        # *===============================================================================
        # * Case 2.b: ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *   Note - no PASTINV as TLIFE always >= D(t) which = 1
        # *===============================================================================
        g.Obj2b[ObjI2[r, t, p]].where[~g.Obj2a[r, t, p]] = True
        # *===============================================================================
        # * Case I/II.2.b: Investment/Tax&Sub ILEDt > ILEDmin,t and TLIFEt + ILEDt < D(t)
        # *   Note - no PASTINV as TLIFE always >= D(t) which = 1
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * build repeated investment blocks until end of lifetime
        # *------------------------------------------------------------------------------
        # * calculate the contribution in each year, if there is a cost
        with Loop(same_as(age, "1")):  # noqa: SIM117
            with Loop(ObjSpred[g.Obj2b[r, t[ll], p], life]):
                with For(g.obj_c, start=1, end=g.coef_rpti[r, t, p]):
                    g.z[...] = g.ncap_iled[r, t, p]
                    g.my_f[...] = (
                        Round(g.b[t] + (g.obj_c - 1) * g.ncap_tlife[r, t, p])
                        - g.yearval[t]
                        + g.z
                    )
                    # * LL+F is investment year; LL+MY_F is commissioning year (cost basis)
                    ObjIdc[r, t, p, life, ll + g.my_f, age + Max(0, g.z - 1)] = True

        # *===============================================================================
        # * Calculate Interest During Construction (IDC) for any fractional ILED
        # * Note: Zero ILED represents half year's interest, consistently
        with Loop(g.ObjIcur[ObjI2[r, v, p], cur]):
            g.z[...] = g.coef_iled[r, v, p]
            with If(g.z):
                g.obj_c[...] = 1 + g.g_drate[r, v, cur]
                g.my_f[...] = 0
                g.f[...] = 0
                # *..Interest according to rounded spreads using actual discount rates
                with Loop(ObjIdc[r, v, p, life, ll, jot]):
                    g.cnt[...] = Ord(jot)
                    g.my_f[...] = g.my_f + Sum(
                        Domain(g.Opyear[jot, age], year[ll.lag(Ord(age))]),  # type: ignore[index]
                        g.obj_disc[r, year, cur],
                    )
                    g.f[...] = g.f + g.obj_disc[r, ll, cur]
                g.my_f[...] = g.my_f / g.f / g.cnt - 1
                # *..Interest according to rounded and accurate spreads using constant discount rate
                g.f[...] = (rpower(g.obj_c, g.cnt) - 1) / (1 - 1 / g.obj_c) / g.cnt - 1
                g.cnt[...] = Max(0.001, g.z)
                g.z[...] = (rpower(g.obj_c, g.cnt) - 1) / (1 - 1 / g.obj_c) / g.cnt - 1
            with Else():  # type: ignore[no-untyped-call]
                g.f[...] = 1
            g.obj_divi[r, v, p] = 1 / (1 + g.z * g.my_f / g.f)
        # * Add spread header tuples
        ObjSumii[r, v, p, life, ll, jot + (1 - Ord(jot))].where[
            ObjIdc[r, v, p, life, ll, jot]
        ] = True
        ObjIdc.setRecords(None)

        # *===============================================================================
        # * Generate the Investment spreads
        # *===============================================================================
        project(source=ObjSumii, target=g.Kage)
        g.Invstep[
            g.Kage[ll, jot], ll + (Ord(age) - 1), age + (Ord(jot) - Ord(age))
        ].where[g.Opyear[jot, age]] = True

    def exec6(self: EqobjinvMod) -> None:
        g = self.tc
        ll, jot, k = g.ll, g.jot, g.k

        g.Invspred[ll, jot, k, k].where[g.Invstep[ll, jot, k, jot]] = True

    def _label_cont_2b(self: EqobjinvMod) -> None:
        g = self.tc
        r, v, p, ll, k = g.r, g.v, g.p, g.ll, g.k
        age, jot, life, year = g.age, g.jot, g.life, g.year
        Uncd7, Ykage, Invspred, ObjSumii, ObjSumiii, ObjI2, KEoh, Lastll = (
            g.Uncd7,
            g.Ykage,
            g.Invspred,
            g.ObjSumii,
            g.ObjSumiii,
            g.ObjI2,
            g.KEoh,
            g.Lastll,
        )

        # *===============================================================================
        # * Case III.1.a-b, III.2.a-b: Decommissioning
        # *===============================================================================
        Uncd7.setRecords(None)
        # * Collect header tuples for decommissioning spreads
        Uncd7[
            g.ObjSums3[r, v, p],
            life + (g.ncap_dlife[r, v, p] - Ord(life)),
            ll.lag(Ord(ll).where[ObjI2[r, v, p]], "circular"),
            ll,
            jot,
        ].where[ObjSumii[r, v, p, life, ll, jot]] = True

        # * Generate the Decommissioning spreads
        Ykage.setRecords(None)
        with Loop(Uncd7[r, v, p, life, Lastll[ll], k, jot]):
            Ykage[ll, k, life] = True
        with Loop(Ykage[year, k[ll], jot]):
            Invspred[year, age + (Ord(jot) - Ord(age)), ll + (Ord(age) - 1), k].where[
                g.Opyear[jot, age]
            ] = True
        with Loop(Uncd7[r, v, p, life, year, KEoh, jot]):
            g.f[...] = ceil(g.ncap_tlife[r, v, p] + g.ncap_dlag[r, v, p])
            # * K is commissioning year (cost basis), LL+F is decommissioning year
            with If(Lastll[year]):
                ObjSumiii[r, v, p, k[KEoh], k, ll + g.f].where[
                    Invspred[year, life, ll, KEoh]
                ] = True
            with Else():  # type: ignore[no-untyped-call]
                ObjSumiii[r, v, p, ll, k, ll + g.f].where[
                    Invspred[KEoh, jot, ll, k]
                ] = True
        Invspred["0", jot, year, k] = False

    def exec5(
        self: EqobjinvMod,
        validate_yes: bool,
        ctst: Literal["", "**EPS", "**0", "1"],
    ) -> None:
        g = self.tc
        r, v, t, p = g.r, g.v, g.t, g.p
        ObjYes, ObjSums3, ObjI2, Obj1a, Obj1b = (
            g.ObjYes,
            g.ObjSums3,
            g.ObjI2,
            g.Obj1a,
            g.Obj1b,
        )

        # *------------------------------------------------------------------------------
        # * The equation divisors for investments:
        g.obj_divi[ObjYes[Obj1a[r, v, p]]] = 1 + (g.ipd[v] - 1).where[g.Milestonyr[v]]
        g.obj_divi[ObjYes[Obj1b[r, t, p]]] = g.ncap_tlife[r, t, p]
        if g.altobj.toValue():
            g.obj_divi[ObjYes[Obj1b[r, t, p]]].where[
                (Round(g.ncap_tlife[r, t, p]) - resolve_ctst(g.ipd[t], ctst)) > 0
            ] = g.ipd[t] * Min(1, g.ncap_tlife[r, t, p])
        if validate_yes:
            g.obj_divi[ObjYes[r, t, p]].where[~ObjI2[r, t, p]] = 1
        # * The equation divisors for decommissioning :
        g.obj_diviii[ObjSums3[r, v, p]] = g.obj_divi[r, v, p]
        g.obj_diviii[ObjSums3[ObjI2[r, v, p]]] = Round(g.ncap_dlife[r, v, p])
        if validate_yes:
            g.obj_pasti.setRecords(None)

    def _label_clrs(self: EqobjinvMod) -> None:
        g = self.tc

        g.ObjYes.setRecords(None)
        g.ObjSums3.setRecords(None)
        g.Ykage.setRecords(None)
        g.Invstep.setRecords(None)
        g.ObjSpred.setRecords(None)
        g.ObjI2.setRecords(None)

    def define_equation(
        self: EqobjinvMod,
        eq: str,
        capjd: ImplicitParameter | Number,
        sow: SowGPType,
        sws: tuple[Set | Alias, ...] | tuple[()],
        swd: tuple[Set | Alias, ...] | tuple[()],
        vart: tuple[str, ImplicitSet | None],
        varv: tuple[str, ImplicitSet | None],
        var: str,
        etl_yes: bool,
        stages_yes: bool,
    ) -> None:
        g = self.tc
        r, v, t, p, cur, k, ll = g.r, g.v, g.t, g.p, g.cur, g.k, g.ll
        jot, life = g.jot, g.life
        KEoh, Y, obv = g.KEoh, g.Y, g.obv
        ObjSumii, ObjSumiii, Invspred = g.ObjSumii, g.ObjSumiii, g.Invspred

        eq_objinv, sow = macro.EQ_OBJINV_GP(eq, sow)
        vart_id, vart_set = vart
        VAR_OBJ = g.get_variable(f"{var}_OBJ")

        def icost_net(year: Set | Alias) -> Expression:
            """OBJ_ICOST + OBJ_ITAX - OBJ_ISUB for a given cost basis year."""
            return (
                macro.obj_icost_GP(r, year, p, cur)
                + macro.obj_itax_GP(r, year, p, cur)
                - macro.obj_isub_GP(r, year, p, cur)
            )

        # *===============================================================================
        # * Generate Investment equation summing over all active indexes by region and currency
        # *===============================================================================
        # *------------------------------------------------------------------------------
        # * Cases I - Investment Cost and II - Taxes/Subsidies
        # *------------------------------------------------------------------------------
        investment: Expression | Sum = (
            capjd
            * Sum(Invspred[KEoh, jot, Y, k], g.obj_disc[r, k, cur] * icost_net(k))
            * g.cor_salvi[r, t, p, cur]
            / g.obj_divi[r, t, p]
            * macro.VAR_NCAP_GP(vart, r, t, p, sws)
        )
        if etl_yes:
            # * handle ETL
            # * %VART%_IC is only declared by mod_vars.etl
            VART_IC = g.get_variable(f"{vart_id}_IC")
            investment = (
                investment
                + Sum(
                    g.GRcur[r, cur],
                    wrap_in_sum(VART_IC[r, t, p, *sws], vart_set)
                    * Sum(Invspred[KEoh, jot, Y, k], g.obj_disc[r, k, cur])
                    * g.cor_salvi[r, t, p, cur]
                    / g.obj_divi[r, t, p],
                ).where[g.seg[r, p]]
            )

        lhs: Expression | Sum = Sum(
            ObjSumii[r, t, p, life, KEoh, jot].where[g.ObjIcur[r, t, p, cur]],
            investment,
        )

        if stages_yes:
            lhs = lhs + Sum(
                Domain(
                    ObjSumii[r, t, p, life, KEoh, jot], g.SwTsw[g.Sow, t, g.ww]
                ).where[g.obj_sic[r, t, p, g.ww]],
                capjd
                * Sum(
                    Invspred[KEoh, jot, Y, k],
                    g.obj_disc[r, k, cur]
                    * macro.obj_icost_GP(r, k, p, cur)
                    * (1 - g.salv_inv[r, t, p, Y]),
                )
                * g.obj_sic[r, t, p, g.ww]
                * g.cor_salvi[r, t, p, cur]
                / g.obj_divi[r, t, p]
                * macro.VAR_NCAP_GP(var, r, t, p, swd),
            )

        # * PASTI charge
        lhs = lhs + Sum(
            ObjSumii[r, g.Pastyear[v], p, life, KEoh, jot].where[
                g.obj_pasti[r, v, p, cur]
            ],
            capjd
            * Sum(Invspred[KEoh, jot, ll, k], g.obj_disc[r, k, cur] * icost_net(k))
            * g.obj_pasti[r, v, p, cur]
            * g.cor_salvi[r, v, p, cur]
            / g.obj_divi[r, v, p],
        )

        lhs = lhs + g.obj_iad[r, cur]

        # *------------------------------------------------------------------------------
        # * Cases III - Decommissioning
        # *------------------------------------------------------------------------------
        lhs = lhs + Sum(
            ObjSumiii[r, v, p, ll, k, Y].where[macro.obj_dcost_GP(r, v, p, cur)],
            g.obj_disc[r, Y, cur]
            * g.cor_salvd[r, v, p, cur]
            * macro.obj_dcost_GP(r, k, p, cur)
            * (
                macro.VAR_NCAP_GP(varv, r, v, p, sws).where[g.Milestonyr[v]]
                + g.obj_pasti[r, v, p, cur].where[g.Pastyear[v]]
            )
            / g.obj_diviii[r, v, p],
        )

        eq_objinv[g.Rdcur[r, cur], *sow] = lhs == Sum(
            obv, g.sum_obj["OBJINV", obv] * VAR_OBJ[r, obv, cur, *sow]
        )
