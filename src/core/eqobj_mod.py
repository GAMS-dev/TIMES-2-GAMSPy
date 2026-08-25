# eqobj_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJ the objective functions
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *  - V-index used in place to T for MODLYEAR
# * Note: PASTYEAR always have D(V) = 1
# *  - V-vintage MODLYEAR year, the point in time where the investment took place
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Loop, Number, Ord, Set, Sum
from gamspy.math import Min, abs, diag, same_as

from core.base_class import GamsClass
from core.eqobjann_tm import EqobjannTm
from core.eqobjels_mod import EqobjelsMod
from core.eqobjfix_mod import EqobjfixMod
from core.eqobjfix_rpt import EqobjfixRpt
from core.eqobjinv_mod import EqobjinvMod
from core.eqobjinv_rpt import EqobjinvRpt
from core.eqobjvar_mod import EqobjvarMod
from core.eqobjvar_rpt import EqobjvarRpt, EqobjvarRptConfig
from core.eqobsalv_mod import EqobsalvMod, EqobsalvModConfig
from core.eqobsalv_rpt import EqobsalvRpt
from core.prepret_dsc import PrepretDsc, PrepretDscConfig
from core.utils import extract_var_domain, generate_equation, wrap_in_sum

if TYPE_CHECKING:
    from typing import Any

    from gamspy import Alias, Expression
    from gamspy._algebra.condition import Condition

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjMod(GamsClass):
    """Translation unit for eqobj.mod."""

    # Instance attributes
    module_name: str = "eqobj_mod"
    gams_source: str = "eqobj.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: Literal["mod"]
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        g.KEoh = Set(m, name="K_EOH", domain=[g.allyear])
        self.tc.enqueue(self.exec1)
        # Sets for periodic costs
        g.Ktyage = Set(m, name="KTYAGE", domain=[g.ll, g.year, g.ll, g.age])
        self.add_records_to_universe_item(["OBJELS"])
        self.tc.enqueue(self.exec2)

        r, allyear, p = g.r, g.allyear, g.p

        # * Cases for ILED and TLIFE/D(t); values assigned in EQOBJINV
        g.Obj1a = Set(m, name="OBJ_1A", domain=[r, allyear, p])
        g.Obj1b = Set(m, name="OBJ_1B", domain=[r, allyear, p])
        g.Obj2a = Set(m, name="OBJ_2A", domain=[r, allyear, p])
        g.Obj2b = Set(m, name="OBJ_2B", domain=[r, allyear, p])
        # * Salvage controls
        g.ObjSums = Set(m, name="OBJ_SUMS", domain=[r, allyear, p])
        g.ObjSums3 = Set(m, name="OBJ_SUMS3", domain=[r, allyear, p])
        g.ObjSumsi = Set(m, name="OBJ_SUMSI", domain=[r, allyear, p, allyear])

        if self.tc.declared("VNRET"):
            self.include(
                PrepretDsc(self.tc, self.env, config=PrepretDscConfig(arg1="EQOBJ"))
            )

        arg_mode = self.arg1.upper()
        if arg_mode == "MOD":
            # Elastic Demand costs
            self.include(EqobjinvMod(self.tc, self.env, arg1="EQOBJ", arg2=""))

            # Fixed O&M Cost and Tax components (Conditional)
            if self.env.timesed == "YES":
                self.include(EqobjelsMod(self.tc, self.env))

            # Fixed O&M Cost and Tax components
            self.include(EqobjfixMod(self.tc, self.env))

        elif arg_mode == "RPT":
            # Elastic Demand costs
            self.include(EqobjinvRpt(self.tc, self.env))

            # Fixed O&M Cost and Tax components (Conditional)
            if self.env.timesed == "YES":
                # eqobj.mod's `$BATINCLUDE eqobjels.%1` (no trailing args) only
                # ever expands to eqobjels.mod: every real entry point hardcodes
                # arg1="mod" (main.py, initmty_mod.py -> MainDrvMod ->
                # EqmainMod -> EqobjMod), so arg_mode == "RPT" cannot occur
                # today. Were it to occur, eqobjels.rpt needs %1..%3 (target
                # parameter, year index, multiplier) that eqobj.mod never
                # supplies in GAMS either, so there is no source text to
                # translate faithfully -- picking values would mean inventing
                # semantics rather than porting them.
                raise NotImplementedError(
                    "EqobjMod arg_mode='RPT' is unreachable from any current "
                    "entry point, and eqobjels.rpt needs %1..%3 that "
                    "eqobj.mod's batinclude never supplies"
                )

            # Fixed O&M Cost and Tax components
            self.include(EqobjfixRpt(self.tc, self.env, arg1=self.arg1))

        # Variable O&M and direct commodity related cost components
        if (self.env.oblong + self.env.obj).upper() == "YESALT":
            self.env.set_scoped("obj", "LIN")
            self.env.set_scoped("varcost", "LIN")

        if arg_mode == "MOD":
            self.include(EqobjvarMod(self.tc, self.env))

            # Salvage value of investment and decommissioning costs
            self.include(
                EqobsalvMod(self.tc, self.env, config=EqobsalvModConfig(arg1=self.arg1))
            )

        elif arg_mode == "RPT":
            self.include(
                EqobjvarRpt(self.tc, self.env, config=EqobjvarRptConfig(arg1=self.arg1))
            )

            # Salvage value of investment and decommissioning costs
            self.include(EqobsalvRpt(self.tc, self.env, arg1=self.arg1))

        # Annualized objective formulation
        if self.env.objann.upper() == "YES":
            self.include(EqobjannTm(self.tc, self.env))

        # Actual OBJ
        is_stages = self.env.stages.upper() == "YES"
        is_timesed = self.env.timesed == "YES"
        is_micro = self.env.micro.upper() == "YES"

        sow = self.env.sow_GP
        eq = self.env.eq
        var_id, var_set = extract_var_domain(self.env.var)
        _ucr = g.get_variable(name=f"{var_id}_UCR")
        VAR_UCR = wrap_in_sum(target=_ucr["OBJZ", g.r, *sow], domain=var_set)
        if is_stages:
            main_eq = g.get_equation(name=f"{eq}_ROBJ")
            main_eq_domain: tuple[Any, ...] = (g.Reg[g.r], *sow)
            lhs1 = -VAR_UCR
        else:
            main_eq = g.get_equation(name=f"{eq}_OBJ")
            main_eq_domain = (...,)
            lhs1 = -g.OBJZ

        # include_main_ext = ""
        # TODO: no obj_ext files present -> remove code
        # if self.env.extend != "":
        #     extensions = {}
        #     requested_exts = set(self.env.extend.split())
        #     include_main_ext = include_extension(
        #         module=self,
        #         extensions=extensions,
        #         requested_exts=requested_exts,
        #         source="obj_ext",
        #     )

        if is_timesed or is_micro:
            self.add_records_to_universe_item(["OBJELS"])

        VAR_OBJ = wrap_in_sum(
            target=g.get_variable(name=f"{var_id}_OBJ"), domain=var_set
        )

        if is_timesed:
            VAR_OBJELS1 = wrap_in_sum(
                target=g.get_variable(name=f"{var_id}_OBJELS"), domain=var_set
            )
            sum_expr1: Condition | int = Sum(
                g.bd, VAR_OBJELS1[g.r, g.bd, g.cur, *sow] * g.bdsig[g.bd]
            ).where[g.sum_obj[g.r, "OBJELS"]]
        else:
            sum_expr1 = 0

        if is_micro:
            VAR_OBJELS2 = wrap_in_sum(
                target=g.get_variable(name=f"{var_id}_OBJELS"), domain=var_set
            )
            sum_expr2: Expression | int = -VAR_OBJELS2[g.r, "FX", g.cur, *sow].where[
                g.sum_obj[g.r, "OBJELS"]
            ]
        else:
            sum_expr2 = 0

        lhs2 = Sum(
            g.Rdcur[g.r, g.cur],
            # * Investment Costs, Tax/Subsidies and Decommissioning
            # * Salvage value of investment and decommissioning costs
            # * Fixed O&M and Tax/Subsidies
            # * Variable O&M and direct commodity costs
            # * Damages
            Sum(
                Domain(g.item, g.obv).where[g.sum_obj[g.item, g.obv]],  # type: ignore[arg-type]
                VAR_OBJ[g.r, g.obv, g.cur, *sow] * g.sum_obj[g.item, g.obv],
            )
            # * Elastic Demand costs
            + sum_expr1
            + sum_expr2,
        )
        # * Extensions to objective function # NOTE: include_main_ext here if any

        main_eq[main_eq_domain] = generate_equation(lhs=lhs1 + lhs2, type="E", rhs=0)

        # Stochastic objective function
        if not is_stages:
            return

        VAR_UC = wrap_in_sum(target=g.get_variable(name=f"{var_id}_UC"), domain=var_set)

        def fetch_inner_sum(arg_set: Set | Alias) -> Sum:
            return Sum(
                g.ucn.where[
                    (
                        Sum(g.UcTSum[g.UcRSum[g.r, g.ucn], g.t], 1.0).where[
                            g.s_ucobj[g.ucn, arg_set]
                        ]
                    )
                ],
                g.s_ucobj[g.ucn, arg_set] * VAR_UC[g.ucn, *sow],
            )

        # ------- EQ 1 -------
        g.eq_expobj[g.Auxsow[g.ww]] = (
            Sum(g.Sow, g.sw_prob[g.Sow] * VAR_UC["OBJZ", *sow]) / g.sw_norm
            - g.VAS_EXPOBJ
        ).where[(~(g.sw_phase))] + Sum(
            g.Sow,
            fetch_inner_sum(g.Sow) - VAR_UC["OBJ1", *sow],
        ).where[(g.sw_phase > 0.0)] + Sum(
            g.Sow,
            fetch_inner_sum(g.ww) - VAR_UC["OBJ1", *self.env.swd_GP],
        ).where[(g.sw_phase < 0.0)] == 0

        # ------- EQ 2 -------
        g.eq_updev[g.Sow].where[g.sw_lambda] = (
            VAR_UC["OBJZ", *sow]
            - g.VAS_EXPOBJ.where[(g.sw_lambda > 0.0)]
            - VAR_UC["OBJ1", *sow].where[(g.sw_lambda < 0.0)]
        ) <= (
            g.VAS_UPDEV[g.Sow].where[(g.sw_lambda > 0.0)]
            + g.VAS_UPDEV["1"].where[(g.sw_lambda < 0.0)]
        )

        # ------- EQ 3 -------
        eq_sobj = g.get_equation(name=f"{eq}_SOBJ")
        eq_sobj["N", *sow] = -VAR_UC["OBJZ", *sow] + Sum(g.r, VAR_UCR) == 0.0

        # ------- EQ 4 -------
        g.eq_obj[...] = (
            (
                g.VAS_EXPOBJ
                + g.sw_lambda
                * Sum(g.Sow, g.sw_prob[g.Sow] * g.VAS_UPDEV[g.Sow])
                / g.sw_norm
            ).where[(g.sw_lambda >= 0.0)]
            - Min(0.0, g.sw_lambda) * g.VAS_UPDEV["1"]
        ).where[(~(g.sw_phase))] + Sum(
            g.Sow,
            VAR_UC["OBJ1", *sow].where[(abs(g.sw_phase) == 1.0)]
            + VAR_UC["OBJZ", *sow].where[(abs(g.sw_phase) == 2.0)],
        ) == g.OBJZ

    def exec1(self: EqobjMod) -> None:
        g = self.tc

        # * [UR] 21.06.2003: K_EOH must include pastyears, since it links to past vintages
        g.KEoh[g.Eachyear].where[
            ((g.yearval[g.Eachyear] >= g.pyr_v1) * (g.yearval[g.Eachyear] <= g.miyr_vl))
        ] = True

    def exec2(self: EqobjMod) -> None:
        g = self.tc

        with Loop(same_as("1", g.age)):
            g.Ktyage[
                g.k[g.ll],
                g.Periodyr[g.t, g.YEoh[g.year]],
                g.age + (Ord(g.year) - Ord(g.ll)),
            ].where[g.Yk[g.year, g.ll]] = True
            g.Ktyage[
                g.k[g.ll],
                g.Yk[g.PyrS, g.YEoh[g.year]],
                g.age + (Ord(g.year) - Ord(g.ll)),
            ].where[g.Yk[g.year, g.ll]] = True

        # * Set up summing of OBJ component variables
        g.sum_obj[g.obv, g.item] = diag(g.obv, g.item)  # type: ignore[arg-type]
        g.sum_obj[g.obv["OBJSAL"], g.obv] = -1.0
        g.sum_obj[g.r, "OBJELS"] = Number(1.0).where[
            Sum(g.Rcj[g.r, g.c, g.j, g.bd], 1.0)
        ]
