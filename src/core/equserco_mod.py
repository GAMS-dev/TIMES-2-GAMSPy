# equserco_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQ_UC - user constraints
# *   %1  - mod or v# for the source code to be used
# *   %2  - equation declaration type
# *   %3  - equation name suffix and condition of existence of equation
# *   %4  - region summation index or bracket
# *   %5  - period summation index or bracket
# *   %6  - time-slice summation index or bracket
# *   %7  - summand for region
# *   %8  - 0 if UC_DYN=EACH, 1 if UC_DYN=SUCC, 2 if SEVERAL
# *   %9  - UC variable name
# *   %10 - UC RHS parameter
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from gamspy import Alias, Domain, Set, Sum
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitSet

from core.base_class import GamsClass
from core.uc_act_mod import UcActModConfig, uc_act_mod
from core.uc_cap_mod import UcCapModConfig, uc_cap_mod
from core.uc_cli_mod import UcCliModConfig, uc_cli_mod
from core.uc_com_mod import UcComModConfig, uc_com_mod
from core.uc_flo_mod import UcFloModConfig, uc_flo_mod
from core.uc_ire_mod import UcIreModConfig, uc_ire_mod
from core.uc_ncap_mod import UcNcapModConfig, uc_ncap_mod
from core.uc_pasti_mod import UcPastiModConfig, uc_pasti_mod
from core.utils import extract_var_domain, generate_equation, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitVariable

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Arg2Config(TypedDict):
    cond: Condition | ImplicitSet | Expression
    dom: Domain
    eq: str


class Arg3Config(TypedDict):
    legacy: str
    gp: (
        Set
        | Alias
        | ImplicitSet
        | Condition
        | tuple[Condition, ImplicitParameter]
        | None
    )


@dataclass
class EqusercoModConfig:
    arg1: Literal["E", "G", "L"]
    arg2: Arg2Config
    arg3: Arg3Config
    arg4: ImplicitSet | None
    arg5: ImplicitSet | None
    arg6: Literal["S", 1, 2, 0]
    arg7: ImplicitVariable
    arg8: ImplicitParameter


class EqusercoMod(GamsClass):
    """Translation unit for eq_uc.mod."""

    module_name: str = "equserco_mod"
    gams_source: str = "equserco.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqusercoModConfig
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.config = config
        self.compile()

    def make_arg2(self, set_element: str) -> tuple[Condition, ImplicitParameter]:
        g = self.tc

        domain = g.UcTmap[g.t, g.ll, g.tt, g.side, g.UcDynt].where[
            (g.lim[g.UcDynt]) ^ (g.UcAttr[g.r, g.ucn, g.side, set_element, g.UcDynt])
        ]
        return domain, g.uc_sign[g.side]

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        eq = cc.arg2["eq"]
        domain = cc.arg2["dom"]
        condition = cc.arg2["cond"]
        if macro.eq_uc.redirects(cc.arg1, eq):
            eq_uc, uc_sow = macro.eq_uc.EQ_UC_GP(
                self.env.eq, cc.arg1, eq, self.env.sow_GP
            )
            fixed_sets = domain.sets[: len(domain.sets) - len(self.env.sow_GP)]
            eq_index: tuple[Any, ...] = (*fixed_sets, *uc_sow)
        else:
            eq_uc = g.get_equation(name=f"{self.env.eq}{cc.arg1}_UC{eq}")
            eq_index = domain.sets

        if cc.arg6 == 1:
            lhs = self._label_dynamic(
                is_stages=self.env.stages == "YES",
                is_cli=self.env.cli == "YES",
            )
        else:
            hs: str | Set = "LHS"
            if cc.arg6 == 2:
                self.env.set_scoped("swt", self.env.sow)
                self.env.set_scoped("swt_GP", self.env.sow_GP)
                self.env.set_scoped("sow", self.env.swd)
                self.env.set_scoped("sow_GP", self.env.swd_GP)
            elif cc.arg6 == "S":
                hs = g.side
            lhs = self._static_lhs(is_several=cc.arg6 == 2, hs=hs)

        rhs = cc.arg7 if self.env.var_uc == "YES" else cc.arg8.where[cc.arg8 != 0]

        arg7 = () if cc.arg5 is None else (cc.arg5,)

        if cc.arg6 != 1:
            domain_expr = Domain(*arg7, g.v[g.t]).where[g.uc_time[g.ucn, g.r, g.t]]
            base_expr = g.uc_time[g.ucn, g.r, g.t] * g.fpd[g.t]
            inner_term = wrap_in_sum(target=base_expr, domain=cc.arg3["gp"])
            time_term = Sum(domain_expr, inner_term)
        else:
            time_term = Sum(
                Domain(*arg7, g.v[g.t]).where[g.uc_time[g.ucn, g.r, g.t]],
                g.uc_time[g.ucn, g.r, g.t]
                * (
                    g.lead[g.t].where[g.UcDyndir[g.r, g.ucn, "RHS"]]
                    + g.lagt[g.t].where[(~(g.UcDyndir[g.r, g.ucn, "RHS"]))]
                ),
            )

        eq_uc[eq_index].where[condition] = generate_equation(
            lhs=lhs, type=cc.arg1, rhs=rhs + time_term
        )

    def _static_lhs(self: EqusercoMod, is_several: bool, hs: str | Set) -> Expression:
        g = self.tc
        cc = self.config

        include_uc_flo = uc_flo_mod(
            g=g,
            config=UcFloModConfig(
                cal_red=self.env.cal_red,
                var=self.env.var,
                swt=self.env.swt_GP,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow_GP,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws_GP,
                varm=self.env.varm_GP,
                varv=self.env.varv_GP,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=cc.arg4,
                arg4=g.t,
                arg5=hs,
                arg6=cc.arg6,
                arg7=g.t,
                arg8=cc.arg5,
                arg9=(self.env.var, ()),
            ),
        )
        include_uc_ncap = uc_ncap_mod(
            g=g,
            config=UcNcapModConfig(
                var=self.env.var,
                sow=self.env.sow_GP,
                varv=self.env.varv_GP,
                sws=self.env.sws_GP,
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=g.t,
                arg4=hs,
                arg5=cc.arg6,
                arg6=g.t,
            ),
        )
        include_uc_cap = uc_cap_mod(
            g=g,
            config=UcCapModConfig(
                var=self.env.var,
                sow=self.env.sow_GP,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=g.t,
                arg4=hs,
                arg5=cc.arg6,
                arg6=g.t,
            ),
        )
        include_uc_act = uc_act_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcActModConfig(
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=cc.arg4,
                arg4=g.t,
                arg5=hs,
                arg6=cc.arg6,
                arg7=g.t,
            ),
        )
        include_uc_com_prd = uc_com_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=cc.arg4,
                arg4=g.t,
                arg5=hs,
                arg6=cc.arg6,
                arg7=g.t,
                arg8="PRD",
                arg9="PRD",
                arg10="PD",
            ),
        )
        include_uc_com_net = uc_com_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=cc.arg4,
                arg4=g.t,
                arg5=hs,
                arg6=cc.arg6,
                arg7=g.t,
                arg8="BAL",
                arg9="NET",
                arg10="NT",
            ),
        )
        include_uc_ire = uc_ire_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcIreModConfig(
                arg1=cc.arg5,
                arg2=cc.arg3["gp"],
                arg3=cc.arg4,
                arg4=g.t,
                arg5=hs,
                arg6=cc.arg6,
                arg7=g.t,
            ),
        )

        sum_all_include = (
            include_uc_flo
            + include_uc_ncap
            + include_uc_cap
            + include_uc_act
            + include_uc_com_prd
            + include_uc_com_net
            + include_uc_ire
        )
        if not is_several:
            return sum_all_include

        arg7_rep = (cc.arg5,) if cc.arg5 is not None else ()
        cumcom_term = Sum(
            Domain(*arg7_rep, g.comvar, g.c, g.year, g.ll).where[
                g.uc_cumcom[g.ucn, g.r, g.comvar, g.c, g.year, g.ll]
            ],
            g.uc_cumcom[g.ucn, g.r, g.comvar, g.c, g.year, g.ll]
            * macro.VAR_CUMCOM_GP(
                self.env.var, g.r, g.c, g.comvar, g.year, g.ll, self.env.swt_GP
            )
            * self.env.cucscal,
        )
        return sum_all_include + cumcom_term

    def _label_dynamic(
        self: EqusercoMod, is_stages: bool, is_cli: bool
    ) -> Expression | Condition:
        g = self.tc
        cc = self.config

        uc_flo_arg9: tuple[Any, Any] = (
            self.env.var,
            (),
        )  # self.env.set_scoped("swflo", self.env.var)
        uc_flo_arg10 = None
        self.env.set_scoped("var_GP", self.env.var)

        if is_stages:
            temp_var = self.env.var
            self.env.set_scoped("var", f"SUM({cc.arg3['legacy']}{temp_var}")
            self.env.set_scoped("var_GP", (temp_var, cc.arg3["gp"]))
            self.env.set_scoped("sow", ",WW)")
            self.env.set_scoped("sow_GP", (g.ww,))
            # self.env.set_scoped("swflo", f"{temp_var} ,WW SUM {cc.arg3["gp"]}")
            # NOTE: uc_flo_arg9 and uc_flo_arg10 are used to pass the swflo value
            uc_flo_arg9 = (temp_var, (g.ww,))
            uc_flo_arg10 = cc.arg3["gp"]

        tsum = (g.UcTmap[g.tt, g.t, g.t, g.side, "N"], g.uc_sign[g.side])
        uc_flo_mod_tplus = uc_flo_mod(
            g=g,
            config=UcFloModConfig(
                cal_red=self.env.cal_red,
                var=self.env.var_GP,
                swt=self.env.swt_GP,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow_GP,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws_GP,
                varm=self.env.varm_GP,
                varv=self.env.varv_GP,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=cc.arg5,
                arg2=tsum,
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.tt,
                arg8=g.lagt[g.t],
                # arg9=self.env.swflo, !%SWFLO% contains emtpy strings! -> split into multiple arguments
                arg9=uc_flo_arg9,
                arg10=uc_flo_arg10,
            ),
        )
        uc_ncap_mod_tplus = uc_ncap_mod(
            g=g,
            config=UcNcapModConfig(
                var=self.env.var_GP,
                sow=self.env.sow_GP,
                varv=self.env.varv_GP,
                sws=self.env.sws_GP,
                arg1=cc.arg5,
                arg2=tsum,
                arg3=g.tt,
                arg4=g.side,
                arg5=cc.arg6,
                arg6=g.tt,
                arg7=g.lagt[g.t],
            ),
        )
        uc_cap_mod_tplus = uc_cap_mod(
            g=g,
            config=UcCapModConfig(
                var=self.env.var_GP,
                sow=self.env.sow_GP,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=cc.arg5,
                arg2=tsum,
                arg3=g.tt,
                arg4=g.side,
                arg5=cc.arg6,
                arg6=g.tt,
                arg7=g.lagt[g.t],
            ),
        )
        uc_act_mod_tplus = uc_act_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcActModConfig(
                arg1=cc.arg5,
                arg2=tsum,
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.tt,
                arg8=g.lagt[g.t],
            ),
        )
        uc_com_mod_tplus_prd = uc_com_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=tsum,
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.tt,
                arg8="PRD",
                arg9="PRD",
                arg10="PD",
                arg11=g.lagt[g.t],
            ),
        )
        uc_com_mod_tplus_bal = uc_com_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=tsum,
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.tt,
                arg8="BAL",
                arg9="NET",
                arg10="NT",
                arg11=g.lagt[g.t],
            ),
        )
        uc_ire_mod_tplus = uc_ire_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcIreModConfig(
                arg1=cc.arg5,
                arg2=tsum,
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.tt,
                arg8=g.lagt[g.t],
            ),
        )

        arg7_rep = (cc.arg5,) if cc.arg5 is not None else ()
        var_id, domain = extract_var_domain(self.env.var_GP)
        # Indexed first, then wrap_in_sum applied: wrapping the bare variable
        # here and indexing it later mis-counts dimensions once domain
        # becomes a weighted (condition, weight) 2-tuple.
        var_ucrt = g.get_variable(name=f"{var_id}_UCRT")
        var_ucrt_reduced = wrap_in_sum(
            var_ucrt[g.ucn, g.r, g.tt, *self.env.sow_GP], domain
        ).where[g.uc_rhsrt[g.r, g.ucn, g.tt, "N"]]
        inner_sum = wrap_in_sum(
            target=g.uc_ucn[g.ucn, g.side, g.r, g.tt, g.ucn] * var_ucrt_reduced,
            domain=tsum,
        )
        sum_all_tplus_mods = (
            uc_flo_mod_tplus
            + uc_ncap_mod_tplus
            + uc_cap_mod_tplus
            + uc_act_mod_tplus
            + uc_com_mod_tplus_prd
            + uc_com_mod_tplus_bal
            + uc_ire_mod_tplus
            + Sum(
                Domain(*arg7_rep, g.UcGmapU[g.r, g.ucn, g.ucn]),
                inner_sum,
            )
        )

        uc_flo_mod_tminus = uc_flo_mod(
            g=g,
            config=UcFloModConfig(
                cal_red=self.env.cal_red,
                var=self.env.var_GP,
                swt=self.env.swt_GP,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow_GP,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws_GP,
                varm=self.env.varm_GP,
                varv=self.env.varv_GP,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="FLO"),
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.ll,
                arg8=-g.lead[g.t],
                arg9=uc_flo_arg9,
                arg10=uc_flo_arg10,
            ),
        )
        uc_ncap_mod_tminus = uc_ncap_mod(
            g=g,
            config=UcNcapModConfig(
                var=self.env.var_GP,
                sow=self.env.sow_GP,
                varv=self.env.varv_GP,
                sws=self.env.sws_GP,
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="NCAP"),
                arg3=g.tt,
                arg4=g.side,
                arg5=cc.arg6,
                arg6=g.ll,
                arg7=(-g.lead[g.t]),
            ),
        )
        uc_cap_mod_tminus = uc_cap_mod(
            g=g,
            config=UcCapModConfig(
                var=self.env.var_GP,
                sow=self.env.sow_GP,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="CAP"),
                arg3=g.tt,
                arg4=g.side,
                arg5=cc.arg6,
                arg6=g.ll,
                arg7=-g.lead[g.t],
            ),
        )
        uc_act_mod_tminus = uc_act_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcActModConfig(
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="ACT"),
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.ll,
                arg8=-g.lead[g.t],
            ),
        )
        uc_com_mod_tminus_prd = uc_com_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="COMPRD"),
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.ll,
                arg8="PRD",
                arg9="PRD",
                arg10="PD",
                arg11=-g.lead[g.t],
            ),
        )
        uc_com_mod_tminus_bal = uc_com_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="COMNET"),
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.ll,
                arg8="BAL",
                arg9="NET",
                arg10="NT",
                arg11=-g.lead[g.t],
            ),
        )
        uc_ire_mod_tminus = uc_ire_mod(
            g=g,
            var=self.env.var_GP,
            sow_GP=self.env.sow_GP,
            config=UcIreModConfig(
                arg1=cc.arg5,
                arg2=self.make_arg2(set_element="IRE"),
                arg3=cc.arg4,
                arg4=g.tt,
                arg5=g.side,
                arg6=cc.arg6,
                arg7=g.ll,
                arg8=-g.lead[g.t],
            ),
        )

        inner_sum = wrap_in_sum(
            target=g.uc_ucn[g.ucn, g.side, g.r, g.ll, g.ucn] * var_ucrt_reduced,
            domain=self.make_arg2(set_element="UCN"),
        )
        sum_all_tminus_mods = (
            uc_flo_mod_tminus
            + uc_ncap_mod_tminus
            + uc_cap_mod_tminus
            + uc_act_mod_tminus
            + uc_com_mod_tminus_prd
            + uc_com_mod_tminus_bal
            + uc_ire_mod_tminus
            + Sum(Domain(*arg7_rep, g.UcGmapU[g.r, g.ucn, g.ucn]), inner_sum)
        )
        uc_cli_mod_tminus: Expression | Sum | int = 0
        if is_cli:
            uc_cli_mod_tminus = uc_cli_mod(
                g=g,
                is_uc_cli_defined=self.tc.defined("UC_CLI"),
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcCliModConfig(
                    arg1=cc.arg5,
                    arg2=self.make_arg2(set_element="CLI"),
                    arg3=cc.arg4,
                    arg4=g.tt,
                    arg5=g.side,
                    arg6=cc.arg6,
                    arg7=g.ll,
                    arg8=-g.lead[g.t],
                ),
            )
        uc_pasti_mod_tminus = uc_pasti_mod(
            g=g,
            config=UcPastiModConfig(
                arg1=cc.arg5,
                arg2=g.Miyr1,
                arg3=g.t,
                arg4="RHS",
            ),
        )
        return (
            sum_all_tplus_mods.where[(~(Sum(g.UcDyndir[g.r, g.ucn, "RHS"], 1.0)))]
            + (sum_all_tminus_mods + uc_cli_mod_tminus - uc_pasti_mod_tminus).where[
                Sum(g.UcDyndir[g.r, g.ucn, "RHS"], 1.0)
            ]
        )
