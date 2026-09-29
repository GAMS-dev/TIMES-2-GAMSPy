# eqobsalv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJSALV the objective functions for salvaging
# *   - Investment Costs
# *   - Taxes and subsidies on investments
# *   - Decommissioning
# *=============================================================================*
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Domain, Expression, If, Loop, Number, Ord, Parameter, Set, Smax, Sum
from gamspy.math import Min, Round, exp, project

from core import prepret_dsc
from core.base_class import GamsClass
from core.utils import extract_var_domain, generate_equation, resolve_ctst, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqobsalvModConfig:
    arg1: Literal["mod", "tm", "STP"]
    arg2: Literal["EXIT", ""] = ""


class EqobsalvMod(GamsClass):
    """Translation unit for eqobsalv.mod."""

    # Instance attributes
    module_name: str = "eqobsalv_mod"
    gams_source: str = "eqobsalv.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqobsalvModConfig
    ):
        self.env = env.fork()
        self.config = config
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        if self.tc.defined("OBJSCC"):
            self._label_prepro()
            return

        g.salv_dec = Parameter(
            m, name="SALV_DEC", domain=[g.Reg, g.allyear, g.prc, g.cur]
        )
        g.objscc = Parameter(m, name="OBJSCC", domain=[g.Reg, g.allyear, g.prc, g.cur])
        g.objsic = Parameter(m, name="OBJSIC", domain=[g.Reg, g.allyear, g.prc])
        g.obj_dceoh = Parameter(m, name="OBJ_DCEOH", domain=[g.Reg, g.cur])
        g.ObjSali = Set(
            m,
            name="OBJ_SALI",
            domain=[g.r, g.allyear, g.p, g.age, g.year, g.age, g.allyear, g.year],
        )

        self._label_prepro()

    def _label_prepro(self) -> None:
        self.tc.enqueue(
            self.exec_eqobsalv_prepro,
            arg1=self.config.arg1,
            timestep_is_set=self.env.is_set("TIMESTEP"),
            stepped=self.env.stepped,
            ctst=self.env.ctst,
            capjd=self.env.capjd_GP,
            etl=self.env.etl,
            declif=self.env.declif,
            vnret_defined=self.tc.defined("VNRET"),
        )

        if self.config.arg2.upper() == "EXIT":
            return

        self._label_equa(
            eq=self.env.eq,
            sow=self.env.sow_GP,
            vart=self.env.vart_GP,
            validate=self.env.validate,
            etl=self.env.etl,
            sws=self.env.sws_GP,
            varv=self.env.varv_GP,
            var=self.env.var,
        )

    def exec_eqobsalv_prepro(
        self: EqobsalvMod,
        arg1: str,
        timestep_is_set: bool,
        stepped: str,
        ctst: Literal["", "**EPS", "**0", "1"],
        capjd: ImplicitParameter | Number,
        etl: str,
        declif: str,
        vnret_defined: bool,
    ) -> None:
        eqobsalv_prepro_GP(
            g=self.tc,
            arg1=arg1,
            timestep_is_set=timestep_is_set,
            stepped=stepped,
            ctst=ctst,
            capjd=capjd,
            etl=etl,
            declif=declif,
            vnret_defined=vnret_defined,
        )

    def _label_equa(
        self,
        eq: str,
        sow: SowGPType,
        vart: tuple[str, ImplicitSet | None],
        validate: str,
        etl: str,
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varv: tuple[str, ImplicitSet | None],
        var: str,
    ) -> None:
        g = self.tc
        eq_objsalv, sow = macro.EQ_OBJSALV_GP(eq, sow)

        def create_wrapped_vars(base_var: Any, suffix: str) -> Any:
            v_id, v_domain = extract_var_domain(base_var)
            return wrap_in_sum(
                target=g.get_variable(f"{v_id}_{suffix}"), domain=v_domain
            )

        var_obj = create_wrapped_vars(var, "OBJ")

        if validate != "YES":
            sub_expr1: Expression | int = (
                Sum(
                    g.ObjSums[g.r, g.pyr[g.v], g.p],
                    g.objscc[g.r, g.v, g.p, g.cur] * g.ncap_pasti[g.r, g.v, g.p],
                )
                * g.obj_dceoh[g.r, g.cur]
            )
        else:
            sub_expr1 = 0

        if etl == "YES":
            vart_ic = create_wrapped_vars(vart, "IC")
            sub_expr2: Expression | int = (
                Sum(
                    Domain(g.ObjSums[g.r, g.t, g.Teg[g.p]], g.GRcur[g.r, g.cur]),
                    g.objsic[g.r, g.t, g.p] * vart_ic[g.r, g.t, g.p, *sws],
                )
                * g.obj_dceoh[g.r, g.cur]
            )
        else:
            sub_expr2 = 0

        sub_expr3 = (
            prepret_dsc.objsalv_GP(g, self.env) if self.tc.defined("VNRET") else 0
        )

        lhs = (
            # *------------------------------------------------------------------------------
            # * Cases I - Investment Cost and II - Taxes/Subsidies
            # *------------------------------------------------------------------------------
            # * [AL] Note that discounting to EOH+1 is imbedded in OBJSCC and OBJSIC
            Sum(
                g.ObjSums[g.r, g.t, g.p],
                g.objscc[g.r, g.t, g.p, g.cur]
                * macro.VAR_NCAP_GP(vart, g.r, g.t, g.p, sws),
            )
            * g.obj_dceoh[g.r, g.cur]
            + sub_expr1
            + sub_expr2
            + sub_expr3
            # *------------------------------------------------------------------------------
            # * Cases III - Decommissioning
            # *------------------------------------------------------------------------------
            # * [AL] Note that discounting to EOH+1 is imbedded in SALV_DEC
            + Sum(
                g.ObjSums3[g.r, g.t, g.p],
                macro.VAR_NCAP_GP(vart, g.r, g.t, g.p, sws)
                * g.salv_dec[g.r, g.t, g.p, g.cur],
            )
            * g.obj_dceoh[g.r, g.cur]
            # * Past investments
            + Sum(
                g.ObjSums3[g.r, g.pyr, g.p],
                g.ncap_pasti[g.r, g.pyr, g.p] * g.salv_dec[g.r, g.pyr, g.p, g.cur],
            )
            * g.obj_dceoh[g.r, g.cur]
            # *------------------------------------------------------------------------------
            # * Cases IV - Decommissioning Surveillance
            # *------------------------------------------------------------------------------
            # * The same proportion SALV_INV is salvaged from investments and surveillance costs
            + Sum(
                g.ObjSumivs[g.r, g.v, g.p, g.k, g.Y].where[
                    g.salv_inv[g.r, g.v, g.p, g.k]
                ],
                g.obj_disc[g.r, g.Y, g.cur]
                * macro.obj_dlagc_GP(g.r, g.k, g.p, g.cur)
                * g.salv_inv[g.r, g.v, g.p, g.k]
                * (
                    macro.VAR_NCAP_GP(varv, g.r, g.v, g.p, sws).where[g.Milestonyr[g.v]]
                    + g.ncap_pasti[g.r, g.v, g.p].where[g.Pastyear[g.v]]
                ),
            )
            # *------------------------------------------------------------------------------
            # * LATE REVENUES
            # *------------------------------------------------------------------------------
            # * [AL] LATEREVENUES identical to decommissioning, with DCOST replaced by OCOM*VALU
            # * Revenues are obtained in the proportion 1-SALV_INV of the total revenues
            + Sum(
                Domain(g.ObjSumiii[g.r, g.v, g.p, g.ll, g.k, g.Y], g.Com).where[
                    ((~(g.YEoh[g.Y])).where[g.ncap_ocom[g.r, g.v, g.p, g.Com]])
                ],
                (1.0 - g.salv_inv[g.r, g.v, g.p, g.ll])
                * g.ncap_valu[g.r, g.k, g.p, g.Com, g.cur]
                * g.obj_disc[g.r, g.Y, g.cur]
                * (
                    macro.VAR_NCAP_GP(varv, g.r, g.v, g.p, sws).where[g.Milestonyr[g.v]]
                    + g.ncap_pasti[g.r, g.v, g.p].where[g.Pastyear[g.v]]
                )
                * g.ncap_ocom[g.r, g.v, g.p, g.Com]
                / g.obj_diviii[g.r, g.v, g.p],
            )
        )

        rhs = var_obj[g.r, "OBJSAL", g.cur, *sow]

        eq_objsalv[g.Rdcur[g.r, g.cur], *sow] = generate_equation(
            lhs=lhs, type="E", rhs=rhs
        )


def eqobsalv_prepro_GP(
    *,
    g: TimesModelClass,
    arg1: str,
    timestep_is_set: bool,
    stepped: str,
    ctst: Literal["", "**EPS", "**0", "1"],
    capjd: ImplicitParameter | Number,
    etl: str,
    declif: str,
    vnret_defined: bool,
) -> None:
    if stepped == "+" and arg1.upper() == "MOD":
        return

    pft: SET_OR_ALIAS = g.v
    if not vnret_defined and ctst != "":
        # string replacement was used to set the domain
        pft = g.v[g.t]

    if timestep_is_set:
        g.ObjSums.setRecords(None)
        g.ObjSums3.setRecords(None)
        g.salv_inv.setRecords(None)
        g.objscc.setRecords(None)

    # * Salvaging of Investments; LL is investment year, K is commissioning year
    # *[UR] 19.12.2003 added -1 in line below, since lifetime starts at the beginning of year K
    g.ObjSali[
        g.ObjSumii[g.r, pft, g.p, g.age, g.KEoh, g.jot],
        g.k,
        g.ll.lag(Ord(g.ll), "circular"),
    ].where[
        (
            (g.yearval[g.k] + g.ncap_tlife[g.r, g.v, g.p] - 1.0 > g.miyr_vl).where[
                g.Invspred[g.KEoh, g.jot, g.k, g.ll]
            ]
        )
    ] = True
    project(source=g.ObjSali, target=g.ObjSumsi, direction="left")
    g.ObjSali.setRecords(None)

    # * No retrofit salvage

    with Loop(Domain(g.Rp[g.r, g.prc], g.p).where[g.prc_refit[g.Rp, g.p]]):  # noqa: SIM117
        with If(g.prc_refit[g.Rp, g.p] < 0.0):
            g.ObjSumsi[g.r, g.t, g.p, g.k] = False

    project(source=g.ObjSumsi, target=g.ObjSums, direction="left")
    # * Salvaging of Decommissioning
    with Loop(g.ObjSumiii[g.ObjSums[g.r, g.v, g.p], g.ll, g.k, g.Y]):
        g.ObjSums3[g.r, g.v, g.p] = True
    # * Salvaging of Decommissioning surveillance
    with Loop(
        g.ObjSumivs[g.r, g.v, g.p, g.k, g.Y].where[
            (g.yearval[g.k] + g.ncap_tlife[g.r, g.v, g.p] - 1.0 > g.miyr_vl)
        ]
    ):
        g.ObjSums3[g.r, g.v, g.p] = True
        g.ObjSumsi[g.r, g.v, g.p, g.k] = True
    # *===============================================================================
    with Loop(g.Rdcur[g.r, g.cur]):
        # * Salvage proportion of investments at the commissioning year K:
        g.salv_inv[g.ObjSumsi[g.r, g.v, g.p, g.k]].where[
            g.ObjIcur[g.r, g.v, g.p, g.cur]
        ] = Min(
            1.0,
            (
                (
                    (
                        (1.0 + g.g_drate[g.r, g.v, g.cur])
                        * exp(g.ncap_fdr[g.r, g.v, g.p])
                    )
                    ** (g.ncap_tlife[g.r, g.v, g.p] + g.yearval[g.k] - g.miyr_vl - 1.0)
                )
                - 1.0
            )
            / (
                (
                    (
                        (1.0 + g.g_drate[g.r, g.v, g.cur])
                        * exp(g.ncap_fdr[g.r, g.v, g.p])
                    )
                    ** g.ncap_tlife[g.r, g.v, g.p]
                )
                - 1.0
            ),
        )
    # * Discount factors for the year EOH+1:
    with Loop(g.Miyr1[g.ll]):
        g.f[...] = g.miyr_vl + 1.0 - g.yearval[g.Miyr1]
        g.obj_dceoh[g.Rdcur[g.r, g.cur]] = g.obj_disc[g.r, g.ll + g.f, g.cur]
    # * Shape-reduced salvage at EOH+1:
    g.z[...] = Smax(g.t.where[(g.b[g.t] <= g.miyr_vl + 1.0)], Ord(g.t) - 1.0)
    with Loop(g.Miyr1[g.t - g.z]):
        g.salv_inv[g.ObjSumsi[g.Rtp, g.k]].where[g.ncap_cpx[g.Rtp]] = g.salv_inv[
            g.Rtp, g.k
        ] * (1.0 + g.rtp_cpx[g.Rtp, g.t])
    g.ObjSumsi.setRecords(None)
    macro_dom = (g.r, g.k, g.p, g.cur)
    # *===============================================================================
    # * Salvage value of investments at year EOH+1:
    # * Note that in Cases 2a and 2b investment costs are paid before K
    g.objscc[g.ObjIcur[g.ObjSums[g.r, g.v, g.p], g.cur]] = (
        g.cor_salvi[g.r, g.v, g.p, g.cur]
        / g.obj_dceoh[g.r, g.cur]
        / g.obj_divi[g.r, g.v, g.p]
        * Sum(
            Domain(
                g.ObjSumii[g.r, g.v, g.p, g.age, g.KEoh, g.jot],
                g.Invspred[g.KEoh, g.jot, g.ll, g.k],
            ).where[g.salv_inv[g.r, g.v, g.p, g.ll]],
            capjd
            * (
                macro.obj_icost_GP(*macro_dom)
                + macro.obj_itax_GP(*macro_dom)
                - macro.obj_isub_GP(*macro_dom)
            )
            * g.salv_inv[g.r, g.v, g.p, g.ll]
            * g.obj_disc[g.r, g.k, g.cur],
        )
    )
    if etl == "YES":
        with Loop(
            Domain(g.ObjSums[g.r, g.t[g.v], g.p], g.GRcur[g.r, g.cur]).where[
                g.seg[g.r, g.p]
            ]
        ):
            g.objsic[g.r, g.t, g.p] = (
                g.cor_salvi[g.r, g.t, g.p, g.cur]
                / g.obj_dceoh[g.r, g.cur]
                / g.obj_divi[g.r, g.t, g.p]
                * Sum(
                    Domain(
                        g.ObjSumii[g.r, g.v, g.p, g.age, g.KEoh, g.jot],
                        g.Invspred[g.KEoh, g.jot, g.ll, g.k],
                    ),
                    capjd
                    * g.salv_inv[g.r, g.t, g.p, g.ll]
                    * g.obj_disc[g.r, g.k, g.cur],
                )
            )
    # * Additional constant term

    g.obj_iad[g.Rdcur[g.r, g.cur]] = Sum(
        g.ObjIcur[g.ObjSums[g.r, g.Pastmile[g.v], g.p], g.cur].where[
            ((g.obj_pasti[g.r, g.v, g.p, g.cur] == 0.0) + resolve_ctst(Number(0), ctst))
        ],
        g.objscc[g.r, g.v, g.p, g.cur]
        * g.ncap_pasti[g.r, g.v, g.p]
        * g.obj_dceoh[g.r, g.cur],
    )
    # *===============================================================================
    # *GG* only if decommissioning lifetime provided by user
    condition = macro.obj_dcost_GP(g.r, g.v, g.p, g.cur)
    g.cor_salvd[g.Rtp[g.r, g.v, g.p], g.cur].where[condition] = (
        (
            (1.0 - 1.0 / (1.0 + g.ncap_drate[g.r, g.v, g.p]))
            * (
                1.0
                - 1.0
                / ((1.0 + g.obj_rfr[g.r, g.v, g.cur]) ** g.ncap_delif[g.r, g.v, g.p])
            )
        )
        / (
            (1.0 - 1.0 / (1.0 + g.obj_rfr[g.r, g.v, g.cur]))
            * (
                1.0
                - 1.0
                / ((1.0 + g.ncap_drate[g.r, g.v, g.p]) ** g.ncap_delif[g.r, g.v, g.p])
            )
        )
    ).where[(g.ncap_drate[g.r, g.v, g.p] > 0.0)] + Number(1.0).where[
        (g.ncap_drate[g.r, g.v, g.p] == 0.0)
    ]
    ncap_declif = g.get_parameter(f"NCAP_{declif}")
    g.obj_crfd[g.Rtp[g.r, g.v, g.p], g.cur].where[condition] = (
        g.cor_salvd[g.r, g.v, g.p, g.cur]
        * (1.0 - (1.0 / (1.0 + g.g_drate[g.r, g.v, g.cur])))
        / (
            1.0
            - (
                (1.0 + g.g_drate[g.r, g.v, g.cur])
                ** (-Round(ncap_declif[g.r, g.v, g.p]))
            )
        )
    )
    # *------------------------------------------------------------------------------
    # * Salvage value of Decommissioning at year EOH+1:
    # * Documentation defines the value for each decommissioning year Y; here aggregated by vintage
    g.salv_dec[g.ObjSums3[g.r, g.v, g.p], g.cur].where[
        g.cor_salvd[g.r, g.v, g.p, g.cur]
    ] = (
        g.cor_salvd[g.r, g.v, g.p, g.cur]
        / g.obj_diviii[g.r, g.v, g.p]
        / g.obj_dceoh[g.r, g.cur]
        * Sum(
            g.ObjSumiii[g.r, g.v, g.p, g.ll, g.k, g.Y].where[
                g.salv_inv[g.r, g.v, g.p, g.ll]
            ],
            g.salv_inv[g.r, g.v, g.p, g.ll]
            * macro.obj_dcost_GP(*macro_dom)
            * g.obj_disc[g.r, g.Y, g.cur],
        )
    )
