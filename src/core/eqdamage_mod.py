# eqdamage_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * EQDAMAGE.mod - Extension for Linearized/Non-linear Damages
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Alias,
    Domain,
    Else,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, project, same_as

from core.base_class import GamsClass
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.utils import wrap_in_sum

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqdamageMod(GamsClass):
    """Translation unit for eqdamage.mod."""

    # Instance attributes
    module_name: str = "eqdamage_mod"
    gams_source: str = "eqdamage.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.compile()

    def compile(self) -> None:
        g = self.tc

        if self.arg1 == "E":
            self._label_lpdam()
            return

        if not self.tc.defined(g.dam_elast):
            self.tc.register_assignment(g.dam_elast)

        # * Internal sets and parameters
        g.Jsubj = Set(
            g.container,
            name="JSUBJ",
            domain=[g.j, g.j],
            description="All steps up to J",
        )
        g.DamNum = Set(g.container, name="DAM_NUM", domain=[g.r, g.c, g.j, g.bd])
        g.damobj = Set(g.container, name="DAMOBJ", records=["DAM", "DAS", "DAM-EXT"])
        g.wwdam = Set(g.container, name="WWDAM", records=["DELTA-ATM"])
        g.rtdam = Set(g.container, name="RTDAM", domain=[g.r, g.t, g.c, g.allsow])
        g.sww = Set(g.container, name="SWW", domain=[g.allsow, g.allsow])
        g.dam_size = Parameter(
            g.container,
            name="DAM_SIZE",
            description="Size of emission steps",
            domain=[g.Reg, g.t, g.Com, g.lim],
        )

        self.tc.enqueue(self.exec1)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.dam_tqty,
                    arg2=(g.r,),
                    tail1=(g.c,),
                    arg4=("0", "0", "0", "0"),
                    arg5=g.Datayear,
                    arg6=g.t,
                    arg10=(g.year,),
                ),
            )
        )

        self.tc.enqueue(
            self.exec2,
            cli=self.env.cli,
            stages=self.env.stages,
            swx=self.env.swx_GP,
            swtx=self.env.swtx_GP,
        )

        # *-----------------------------------------------------------------------------
        # Kept as raw GAMS: this compile-time data line is where OBJDAM first enters
        # the universe, and GAMS remembers the quote character of a label's first
        # entry (CONVERT names the VAR_OBJ(R,'OBJDAM',CUR) columns with it). GAMSPy
        # always emits labels double-quoted, so a native expand_set/assignment would
        # rename those columns.
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
$onMulti
SET OBV / 'OBJDAM' /;
""",
        )
        if self.env.damage == "NO":
            self.tc.enqueue(self.exec3)

        if self.env.varmac in ["0==0", "1==1"]:
            self.env.set_scoped("var", self.env.vas)

        if self.env.damage == "NO":
            self._label_finish()
            return

        self.emission_balance_equation()

        if self.env.damage == "NLP":
            self._label_nlpdam()
            return

        self._label_lpdam()

    def exec1(self) -> None:
        self.tc.Rxx.setRecords(None)

    def exec2(
        self: EqdamageMod,
        cli: str,
        stages: str,
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
        swtx: Number | ImplicitSet,
    ) -> None:
        g = self.tc
        r, t, c, cur, s, bd, j, jj = g.r, g.t, g.c, g.cur, g.s, g.bd, g.j, g.jj
        Rxx, Trackc = g.Rxx, g.Trackc
        f, z, first_val, last_val = g.f, g.z, g.first_val, g.last_val
        dam_tqty, dam_cost, dam_tvoc, dam_elast, dam_step, dam_size, dam_voc = (
            g.dam_tqty,
            g.dam_cost,
            g.dam_tvoc,
            g.dam_elast,
            g.dam_step,
            g.dam_size,
            g.dam_voc,
        )
        dam_tqty[r, t, c].where[~dam_tqty[r, t, c]] = sparse(g.dam_bqty[r, c])

        # * Enable damage costs for atmospheric CO2 concentration:
        if cli == "YES":
            g.Rtc[r, t, c[g.cg[g.CmVar]]].where[
                (~g.Rc[r, c]).where[dam_tqty[r, t, c]]
            ] = True

        # * Remove EPS costs unless uncertain
        dam_cost[r, t, c, cur].where[
            (dam_cost[r, t, c, cur] == 0.0).where[dam_cost[r, t, c, cur]]
        ] = 0.0
        if stages.upper() == "YES":
            project(source=g.SwTsw, target=g.sww, direction="left")
            with Loop(g.Sow):
                dam_cost[r, t, c, cur].where[g.s_dam_cost[r, t, c, cur, "1", g.Sow]] = (
                    dam_cost[r, t, c, cur] + SpecialValues.EPS
                )
        with Loop(g.Rdcur[r, cur]):
            Rxx[g.Rtc].where[dam_cost[g.Rtc, cur]] = True
        with Loop(t):
            Trackc[r, c].where[Rxx[r, t, c]] = True
        dam_tvoc[Rxx[r, t, c], bd] = sparse(dam_voc[r, c, bd])

        g.RhsCombal[g.RtcsVarc[Rxx[r, t, c], s]].where[~dam_elast[r, c, "N"]] = True
        g.RcsCombal[g.RhsCombal[Rxx[r, t, c], s], "FX"] = True

        # * If BQTY is zero set VOC to zero to, leading to constant cost
        dam_tqty[Rxx[r, t, c]].where[dam_tqty[r, t, c] <= 0.0] = Max(
            0.0, dam_tvoc[r, t, c, "LO"]
        )
        dam_tvoc[Rxx[r, t, c], bd].where[~dam_tqty[r, t, c]] = 0.0
        with Loop(t):
            dam_elast[r, c, bd].where[(~dam_tqty[r, t, c]).where[Rxx[r, t, c]]] = 0.0
        dam_step[Trackc[r, c], "FX"] = 0.0
        z[...] = 100.0
        dam_step[Trackc[r, c], bd].where[
            (~dam_step[r, c, bd]).where[dam_elast[r, c, bd]]
        ] = 1.0
        dam_step[Trackc[r, c], bd].where[dam_step[r, c, bd]] = Min(
            z, abs(Round(dam_step[r, c, bd]))
        )

        # * Ensure that elasticities are greater than or equal to 1:
        dam_elast[Trackc[r, c], "LO"] = abs(
            dam_elast[r, c, "UP"].where[~dam_elast[r, c, "LO"]] + dam_elast[r, c, "LO"]
        )
        dam_elast[Trackc[r, c], "UP"] = abs(
            dam_elast[r, c, "LO"].where[~dam_elast[r, c, "UP"]] + dam_elast[r, c, "UP"]
        )

        # * Adjust VOCs
        dam_tvoc[Rxx[r, t, c], bd].where[~dam_tvoc[r, t, c, bd]] = sparse(
            (dam_step[r, c, bd] + 0.5) * dam_voc[r, c, "N"] * dam_tqty[r, t, c]
        )
        dam_tvoc[Rxx[r, t, c], "LO"] = Min(
            dam_tqty[r, t, c],
            dam_tvoc[r, t, c, "LO"]
            + Number(SpecialValues.POSINF).where[~dam_tvoc[r, t, c, "LO"]],
        )
        dam_tvoc[Rxx[r, t, c], "UP"].where[~dam_tvoc[r, t, c, "UP"]] = dam_tvoc[
            r, t, c, "LO"
        ] * (
            1.0
            + ((dam_step[r, c, "UP"] + 0.5) / (dam_step[r, c, "LO"] + 0.5) - 1.0).where[
                dam_step[r, c, "LO"]
            ]
        )

        with Loop(Rxx[r, t, c]):
            f[...] = dam_step[r, c, "LO"]
            z[...] = dam_step[r, c, "UP"]
            first_val[...] = dam_tvoc[r, t, c, "LO"]
            last_val[...] = dam_tvoc[r, t, c, "UP"]
            with If(f):
                dam_size[r, t, c, "FX"] = 2.0 * (
                    first_val
                    - (first_val * (4.0 * z + 1.0) - last_val)
                    / (1.0 + z * (4.0 + 1.0 / f))
                )
            with Else():
                dam_size[r, t, c, "FX"] = first_val + 0.5 * last_val / (z + 0.5)
        dam_size[Rxx[r, t, c], g.Bdneq[bd]].where[dam_step[r, c, bd]] = (
            Max(0.0, dam_tvoc[r, t, c, bd] - 0.5 * dam_size[r, t, c, "FX"])
            / dam_step[r, c, bd]
        )
        dam_size[Rxx[r, t, c], "UP"].where[~dam_step[r, c, "LO"]] = Max(
            0.0, dam_tvoc[r, t, c, "UP"] / (dam_step[r, c, "UP"] + 0.5)
        )
        dam_size[Rxx[r, t, c], "N"] = (
            dam_tqty[r, t, c]
            - dam_tvoc[r, t, c, "LO"]
            + 0.5 * dam_size[r, t, c, "LO"].where[dam_elast[r, c, "N"]]
        )

        g.dam_coef[g.RtcsVarc[r, t, c, s]].where[
            (~g.dam_coef[r, t, c, s]).where[Trackc[r, c]]
        ] = 1.0
        g.Jsubj[jj, j].where[(Ord(j) <= Ord(jj)).where[Ord(jj) <= 100.0]] = True
        # * Set number of FX steps (any non-zero DAM_STEP(R,C,'N') disables endogenous damage)
        dam_step[Trackc[r, c], "FX"].where[dam_step[r, c, "N"] == 0.0] = (
            1.0 + Number(1.0).where[Sum(t.where[dam_size[r, t, c, "N"] > 0.0], 1.0)]
        )
        if not dam_cost.number_records:
            g.sum_obj["OBJDAM", g.item] = 0.0
        g.rtdam[Rxx[r, t, c], *swx].where[swtx | g.wwdam[c]] = True

    def exec3(self) -> None:
        self.tc.sum_obj["OBJDAM", self.tc.item] = 0.0

    def emission_balance_equation(self: EqdamageMod) -> None:
        g = self.tc
        r, t, c, cur, s, bd, j, jj = g.r, g.t, g.c, g.cur, g.s, g.bd, g.j, g.jj
        var, sow, swx = self.env.var, self.env.sow_GP, self.env.swx_GP
        dam_elast, dam_coef = g.dam_elast, g.dam_coef
        eq_damage = g.get_equation(f"{self.env.eq}_DAMAGE")
        VAR_DAM = g.get_variable(f"{var}_DAM")
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")

        # * Emission balance equation
        lhs = Sum(
            g.DamNum[r, c, jj, bd], Sum(g.Jsubj[jj, j], VAR_DAM[r, t, c, bd, j, *sow])
        )

        if self.env.cli == "YES":
            vart_id, vart_set = self.env.vart_GP
            VART_CLITOT = g.get_variable(f"{vart_id}_CLITOT")
            VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
            CmVar, CmKind = g.CmVar, g.CmKind
            climate = Sum(
                CmVar[c],
                wrap_in_sum(VART_CLITOT[CmVar, t, *self.env.sws_GP], vart_set).where[  # type: ignore[union-attr]
                    CmKind[CmVar]
                ]
                + VAR_CLIBOX[CmVar, "ATM", t, *sow].where[~CmKind[CmVar]],
            ).where[~g.Rc[r, c]]
        com_ts = Sum(
            g.ComTs[g.Rc[r, c], s],
            dam_coef[r, t, c, s]
            * VAR_COMNET[r, t, c, s, *sow].where[~dam_elast[r, c, "N"]]
            + dam_coef[r, t, c, s]
            * VAR_COMPRD[r, t, c, s, *sow].where[dam_elast[r, c, "N"]],
        )
        rhs = climate + com_ts if self.env.cli == "YES" else com_ts

        eq_damage[g.Rtc[*self.env.r_t_GP, c], *sow].where[
            Sum(g.Rdcur[r, cur].where[g.dam_cost[r, t, c, cur]], 1.0).where[
                g.rtdam[g.Rtc, *swx]
            ]
        ] = lhs == rhs.where[g.dam_step[r, c, "FX"]]

    def _label_lpdam(self) -> None:
        self.damage_cost_equation()

        self._label_bound()

    def _label_nlpdam(self) -> None:
        self.damage_cost_equation_nlp()
        self._label_bound()

    def _label_bound(self) -> None:
        if self.env.damage == "NLP":
            self._label_bdnlp()
            return

        self.tc.enqueue(
            self.damage_var_bounds,
            var=self.env.var,
            swd=self.env.swd_GP,
            sow=self.env.sow_GP,
            swx=self.env.swx_GP,
        )
        self._label_finish()

    def _label_bdnlp(self) -> None:
        self.tc.enqueue(
            self.damage_var_bounds_bdnlp,
            var=self.env.var,
            swd=self.env.swd_GP,
            sow=self.env.sow_GP,
            swx=self.env.swx_GP,
        )
        self._label_finish()

    def _label_finish(self) -> None:
        self.tc.enqueue(self.finish)

    def finish(self) -> None:
        g = self.tc
        r, t, c = g.r, g.t, g.c
        g.Trackc.setRecords(None)
        g.Rxx.setRecords(None)
        g.dam_tvoc.setRecords(None)
        g.dam_tvoc[r, t, c, "N"].where[g.dam_size[r, t, c, "N"]] = (
            (g.dam_size[r, t, c, "N"] / g.dam_tqty[r, t, c]) ** g.dam_elast[r, c, "LO"]
        ).where[g.dam_elast[r, c, "N"]]

    def damage_var_bounds(
        self,
        var: str,
        swd: tuple[Set | Alias] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
    ) -> None:
        g = self.tc
        r, t, c, j, bd, Rtc = g.r, g.t, g.c, g.j, g.bd, g.Rtc
        dam_size, dam_step, rtdam = g.dam_size, g.dam_step, g.rtdam
        VAR_DAM = g.get_variable(f"{var}_DAM")

        # * Set bounds for damage variables:
        with Loop(j.where[same_as(j, "1")]):
            g.DamNum[g.Trackc[r, c], j + (dam_step[r, c, bd] - 1.0), bd] = True
        VAR_DAM.up[r, t, c, bd, j, *swd] = SpecialValues.POSINF
        VAR_DAM.up[Rtc[r, t, c], "LO", j, *sow].where[
            (Ord(j) <= dam_step[r, c, "LO"]).where[rtdam[Rtc, *swx]]
        ] = dam_size[Rtc, "LO"]
        VAR_DAM.up[Rtc[r, t, c], "LO", "1", *sow].where[
            g.dam_elast[r, c, "N"].where[rtdam[Rtc, *swx]]
        ] = dam_size[Rtc, "LO"] + g.dam_tqty[Rtc] - g.dam_tvoc[Rtc, "LO"]
        VAR_DAM.up[Rtc[r, t, c], "UP", j, *sow].where[
            (Ord(j) < dam_step[r, c, "UP"]).where[rtdam[Rtc, *swx]]
        ] = dam_size[Rtc, "UP"]
        VAR_DAM.up[Rtc[r, t, c], "FX", "1", *sow].where[
            g.dam_tvoc[Rtc, "UP"].where[rtdam[Rtc, *swx]]
        ] = dam_size[Rtc, "FX"]
        VAR_DAM.up[Rtc[r, t, c], "FX", "2", *sow].where[rtdam[Rtc, *swx]] = dam_size[
            Rtc, "N"
        ].where[~g.dam_elast[r, c, "N"]]

    def damage_var_bounds_bdnlp(
        self,
        var: str,
        swd: tuple[Set | Alias] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
    ) -> None:
        g = self.tc
        r, t, c, j, bd, Rtc = g.r, g.t, g.c, g.j, g.bd, g.Rtc
        dam_size, dam_step, rtdam = g.dam_size, g.dam_step, g.rtdam
        VAR_DAM = g.get_variable(f"{var}_DAM")

        # * Set bounds for damage variables:
        dam_step[g.Trackc, g.Bdneq] = 1.0
        with Loop(j.where[same_as(j, "1")]):
            g.DamNum[g.Trackc[r, c], j + (dam_step[r, c, bd] - 1.0), bd] = True
        VAR_DAM.up[r, t, c, bd, j, *swd] = SpecialValues.POSINF
        VAR_DAM.up[Rtc[r, t, c], "LO", "1", *sow].where[rtdam[Rtc, *swx]] = (
            g.dam_tqty[Rtc] - dam_size[Rtc, "N"]
        ).where[dam_step[r, c, "LO"]]
        VAR_DAM.up[Rtc[r, t, c], "FX", "1", *sow].where[rtdam[Rtc, *swx]] = (
            SpecialValues.EPS
        )
        VAR_DAM.up[Rtc[r, t, c], "FX", "2", *sow].where[rtdam[Rtc, *swx]] = dam_size[
            Rtc, "N"
        ]

    def damage_cost_equation(self: EqdamageMod) -> None:
        # %2/%3 = '*'/'$EXIT' turn this block into the bare expression that
        # eqobjcst.tm harvests; that form is eq_damage_mod_GP, not an equation.
        if self.arg2 or self.arg3:
            raise NotImplementedError(
                f"eqdamage.mod E {self.arg2} {self.arg3} is an expression "
                f"(arg2={self.arg2!r}, arg3={self.arg3!r}): use eq_damage_mod_GP"
            )
        g = self.tc
        r, cur, obv = g.r, g.cur, g.obv
        sow = self.env.sow_GP
        eq_objdam = g.get_equation(f"{self.env.eq}_OBJDAM")
        VAR_OBJ = g.get_variable(f"{self.env.var}_OBJ")

        # * Damage cost equation
        eq_objdam[g.Rdcur[r, cur], *sow] = eq_damage_mod_GP(
            g, self.env.var, self.env.swd_GP, self.env.stages
        ) == Sum(obv, g.sum_obj["OBJDAM", obv] * VAR_OBJ[r, obv, cur, *sow])

    def damage_cost_equation_nlp(self: EqdamageMod) -> None:
        g = self.tc
        r, t, c, cur, bd, Sow, ww, obv = (
            g.r,
            g.t,
            g.c,
            g.cur,
            g.bd,
            g.Sow,
            g.ww,
            g.obv,
        )
        dam_elast, dam_size, dam_tqty, dam_cost = (
            g.dam_elast,
            g.dam_size,
            g.dam_tqty,
            g.dam_cost,
        )
        sow, swd = self.env.sow_GP, self.env.swd_GP
        eq_objdam = g.get_equation(f"{self.env.eq}_OBJDAM")
        VAR_DAM = g.get_variable(f"{self.env.var}_DAM")
        VAR_OBJ = g.get_variable(f"{self.env.var}_OBJ")

        # * Damage cost equation
        cost = (
            g.dam_tvoc[r, t, c, "N"]
            * (
                VAR_DAM[r, t, c, "FX", "2", *swd]
                + dam_size[r, t, c, "N"] * dam_elast[r, c, "N"]
            )
            + (
                (
                    (VAR_DAM[r, t, c, "LO", "1", *swd] + dam_size[r, t, c, "N"])
                    ** (dam_elast[r, c, "LO"] + 1.0)
                    # * Subtract full LO costs if DAM_ELAST(N) = -1 (constant term)
                    + dam_elast[r, c, "N"]
                    * dam_tqty[r, t, c] ** (dam_elast[r, c, "LO"] + 1.0)
                    - dam_size[r, t, c, "N"] ** (dam_elast[r, c, "LO"] + 1.0)
                )
                / (
                    dam_tqty[r, t, c] ** dam_elast[r, c, "LO"]
                    * (dam_elast[r, c, "LO"] + 1.0)
                )
            ).where[g.dam_step[r, c, "LO"]]
            + (
                (VAR_DAM[r, t, c, "UP", "1", *swd] + dam_tqty[r, t, c])
                ** (dam_elast[r, c, "UP"] + 1.0)
                - dam_tqty[r, t, c] ** (dam_elast[r, c, "UP"] + 1.0)
            )
            / (
                dam_tqty[r, t, c] ** dam_elast[r, c, "UP"]
                * (dam_elast[r, c, "UP"] + 1.0)
            )
            # * Shift cost curve by DAM_ELAST(N) if applicable
            + dam_elast[r, c, "N"]
            * (
                Sum(g.Bdneq[bd], VAR_DAM[r, t, c, bd, "1", *swd])
                + dam_elast[r, c, "N"] * dam_tqty[r, t, c]
            )
        ) * g.obj_pvt[r, t, cur]

        weighted = (
            Sum(
                g.sww[Sow, ww].where[
                    g.SwTsw[Sow, t, ww].where[~g.wwdam[c]]
                    + g.sww[ww, Sow].where[g.wwdam[c]]
                ],
                cost * g.s_dam_cost[r, t, c, cur, "1", ww],
            )
            if self.env.stages.upper() == "YES"
            else cost * dam_cost[r, t, c, cur]
        )

        eq_objdam[g.Rdcur[r, cur], *sow] = Sum(
            g.Rtc[r, t, c].where[g.dam_step[r, c, "FX"].where[dam_cost[r, t, c, cur]]],
            weighted,
        ) == Sum(obv, g.sum_obj["OBJDAM", obv] * VAR_OBJ[r, obv, cur, *sow])


def eq_damage_mod(var: str, swd: str, stages: str) -> str:
    equation = """
    SUM(RTC(R,T,C)$(DAM_STEP(R,C,'FX')$DAM_COST(R,T,C,CUR)),
"""
    if stages.upper() == "YES":
        equation += """
SUM(SWW(SOW,WW)$(SW_TSW(SOW,T,WW)$(NOT WWDAM(C))+SWW(WW,SOW)$WWDAM(C)),
"""
    equation += rf"""
  (SUM((DAM_NUM(R,C,JJ,'LO'),JSUBJ(JJ,J)),
     ({var}_DAM(R,T,C,'LO',J{swd}) + DAM_ELAST(R,C,'N')*{var}_DAM.UP(R,T,C,'LO',J{swd}))*
     ((DAM_TQTY(R,T,C)-DAM_SIZE(R,T,C,'FX')/2-DAM_SIZE(R,T,C,'LO')*(ORD(JJ)-ORD(J)+.5))**DAM_ELAST(R,C,'LO') /
      DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'LO') + DAM_ELAST(R,C,'N')))$DAM_TQTY(R,T,C) +
   {var}_DAM(R,T,C,'FX','1'{swd}) * (1 + DAM_ELAST(R,C,'N')) +
   SUM((DAM_NUM(R,C,JJ,'UP'),JSUBJ(JJ,J)),
     {var}_DAM(R,T,C,'UP',J{swd}) *
     ((DAM_TQTY(R,T,C)+DAM_SIZE(R,T,C,'FX')/2+DAM_SIZE(R,T,C,'UP')*(ORD(J)-.5))**DAM_ELAST(R,C,'UP') /
      DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'UP') + DAM_ELAST(R,C,'N')))$DAM_TQTY(R,T,C)
  ) * OBJ_PVT(R,T,CUR) *
"""

    if stages.upper() != "YES":
        equation += "DAM_COST(R,T,C,CUR)"
    else:
        equation += "  S_DAM_COST(R,T,C,CUR,'1',WW))"

    equation += """
)
"""
    return equation


def eq_damage_mod_GP(
    g: TimesModelClass,
    var: str,
    swd: tuple[Set | Alias] | tuple[()],
    stages: str,
) -> Sum:
    r, t, c, cur, j, jj, Sow, ww = g.r, g.t, g.c, g.cur, g.j, g.jj, g.Sow, g.ww
    dam_elast, dam_size, dam_tqty, dam_cost = (
        g.dam_elast,
        g.dam_size,
        g.dam_tqty,
        g.dam_cost,
    )
    VAR_DAM = g.get_variable(f"{var}_DAM")

    cost = (
        Sum(
            Domain(g.DamNum[r, c, jj, "LO"], g.Jsubj[jj, j]),
            (
                VAR_DAM[r, t, c, "LO", j, *swd]
                + dam_elast[r, c, "N"] * VAR_DAM.up[r, t, c, "LO", j, *swd]
            )
            * (
                (
                    dam_tqty[r, t, c]
                    - dam_size[r, t, c, "FX"] / 2.0
                    - dam_size[r, t, c, "LO"] * (Ord(jj) - Ord(j) + 0.5)
                )
                ** dam_elast[r, c, "LO"]
                / dam_tqty[r, t, c] ** dam_elast[r, c, "LO"]
                + dam_elast[r, c, "N"]
            ),
        ).where[dam_tqty[r, t, c]]
        + VAR_DAM[r, t, c, "FX", "1", *swd] * (1.0 + dam_elast[r, c, "N"])
        + Sum(
            Domain(g.DamNum[r, c, jj, "UP"], g.Jsubj[jj, j]),
            VAR_DAM[r, t, c, "UP", j, *swd]
            * (
                (
                    dam_tqty[r, t, c]
                    + dam_size[r, t, c, "FX"] / 2.0
                    + dam_size[r, t, c, "UP"] * (Ord(j) - 0.5)
                )
                ** dam_elast[r, c, "UP"]
                / dam_tqty[r, t, c] ** dam_elast[r, c, "UP"]
                + dam_elast[r, c, "N"]
            ),
        ).where[dam_tqty[r, t, c]]
    ) * g.obj_pvt[r, t, cur]

    weighted = (
        Sum(
            g.sww[Sow, ww].where[
                g.SwTsw[Sow, t, ww].where[~g.wwdam[c]]
                + g.sww[ww, Sow].where[g.wwdam[c]]
            ],
            cost * g.s_dam_cost[r, t, c, cur, "1", ww],
        )
        if stages.upper() == "YES"
        else cost * dam_cost[r, t, c, cur]
    )

    return Sum(
        g.Rtc[r, t, c].where[g.dam_step[r, c, "FX"].where[dam_cost[r, t, c, cur]]],
        weighted,
    )
