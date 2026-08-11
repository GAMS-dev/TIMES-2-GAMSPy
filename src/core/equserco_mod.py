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
from typing import TYPE_CHECKING, Literal, TypedDict, TypeVar

from gamspy import Alias, Domain, Set, Sum
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitSet

from core.base_class import GamsClass
from core.uc_act_mod import UcActModConfig, uc_act_mod
from core.uc_cap_mod import uc_cap_mod
from core.uc_cli_mod import uc_cli_mod
from core.uc_com_mod import UcComModConfig, uc_com_mod
from core.uc_flo_mod import uc_flo_mod
from core.uc_ire_mod import uc_ire_mod
from core.uc_ncap_mod import uc_ncap_mod
from core.uc_pasti_mod import uc_pasti_mod
from core.utils import wrap_in_sum

# from core.utils import generate_equation

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitVariable

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

GAMSPyArg = TypeVar("GAMSPyArg")


class Arg3Config(TypedDict):
    cond: Condition | ImplicitSet | Set | Expression
    dom: Domain | ImplicitSet | Set
    eq: str


@dataclass
class DualArgs[GAMSPyArg]:
    """Groups a legacy GAMS string with its GAMSPy equivalent."""

    s: str
    gp: GAMSPyArg


@dataclass
class EqusercoModConfig:
    arg2: Literal["E", "G", "L"]
    arg3: DualArgs[Arg3Config]
    arg4: DualArgs[bool | None]
    arg5: DualArgs[
        Set
        | Alias
        | ImplicitSet
        | Condition
        | tuple[Condition, ImplicitParameter]
        | None
    ]
    arg6: DualArgs[ImplicitSet | Domain | None]
    arg7: DualArgs[ImplicitSet | Domain | None]
    arg8: DualArgs[Literal["S", 1, 2, 0]]
    arg9: ImplicitVariable
    arg10: ImplicitParameter


def make_arg2(
    g: TimesModelClass, set_element: str
) -> tuple[Condition, ImplicitParameter]:
    domain = g.UcTmap[g.t, g.ll, g.tt, g.side, g.UcDynt].where[
        (g.lim[g.UcDynt]) ^ (g.UcAttr[g.r, g.ucn, g.side, set_element, g.UcDynt])
    ]
    return domain, g.uc_sign[g.side]


class EqusercoMod(GamsClass):
    """Translation unit for eq_uc.mod."""

    module_name: str = "eq_uc_mod"
    gams_source: str = "eq_uc.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqusercoModConfig,
    ):
        self.env = env.fork()
        self.tc = tc

        self.arg2 = config.arg2
        self.arg9 = config.arg9
        self.arg10 = config.arg10

        # Legacy GAMS string arguments
        self.arg3 = config.arg3.s
        self.arg4 = config.arg4.s
        self.arg5 = config.arg5.s
        self.arg6 = config.arg6.s
        self.arg7 = config.arg7.s
        self.arg8 = config.arg8.s

        # GAMSPy objects
        self.arg3_GP = config.arg3.gp
        self.arg4_GP = config.arg4.gp
        self.arg5_GP = config.arg5.gp
        self.arg6_GP = config.arg6.gp
        self.arg7_GP = config.arg7.gp
        self.arg8_GP = config.arg8.gp

        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc

        lhs = ""
        if self.arg8_GP == 1:
            lhs = self._label_dynamic(
                is_stages=self.env.stages == "YES",
                is_cli=self.env.cli == "YES",
            )
        else:
            # self.env.set_local("hs", "'LHS'")
            # NOTE: hs is only used in this file, using python variable instead
            hs = "'LHS'"
            hs_GP: str | Set
            hs_GP = "LHS"
            if self.arg8_GP == 2:
                self.env.set_scoped("swt", self.env.sow)
                self.env.set_scoped("swt_GP", self.env.sow_GP)
                self.env.set_scoped("sow", self.env.swd)
                self.env.set_scoped("sow_GP", self.env.swd_GP)
            elif self.arg8_GP == "S":
                # self.env.set_local("hs", "SIDE")
                hs = "SIDE"
                hs_GP = g.side
            lhs = self._static_lhs(is_several=self.arg8_GP == 2, hs_arg=(hs, hs_GP))

        rhs = (
            self.arg9 if self.env.var_uc == "YES" else self.arg10.where[self.arg10 != 0]
        )

        arg7 = () if self.arg7_GP is None else (self.arg7_GP,)

        if self.arg8_GP != 1:
            domain_expr = Domain(*arg7, g.v[g.t]).where[g.uc_time[g.ucn, g.r, g.t]]
            base_expr = g.uc_time[g.ucn, g.r, g.t] * g.fpd[g.t]
            inner_term: Expression | Sum
            inner_term = wrap_in_sum(arg=self.arg5_GP, expression=base_expr)
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
        time_term_str = f"+{time_term.gamsRepr()}"  # type: ignore[no-untyped-call]
        # eq = self.arg3_GP["eq"]
        # domain = self.arg3_GP["dom"]
        # condition = self.arg3_GP["cond"]
        # eq_uc: Equation = g.get_equation(name=f"{self.env.eq}{self.arg2}_UC{eq}")
        # # NOTE: lhs is a string
        # eq_uc[*domain.sets].where[condition] = generate_equation(
        #     lhs=lhs, type=self.arg2, rhs=rhs + time_term
        # )
        old_code = rf"""
    {self.env.eq}{self.arg2}_UC{self.arg3}..
{lhs}

        ={self.arg2}=

        {rhs.gamsRepr()}
{time_term_str}

   ;
"""
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=old_code,
        )

    def _static_lhs(
        self: EqusercoMod, is_several: bool, hs_arg: tuple[str, str | Set]
    ) -> str:
        g = self.tc
        hs, hs_GP = hs_arg
        include_uc_flo = uc_flo_mod(
            cal_red=self.env.cal_red,
            var=self.env.var,
            swt=self.env.swt,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            sow=self.env.sow,
            cufscal=self.env.cufscal,
            pgprim=self.env.pgprim,
            sws=self.env.sws,
            varm=self.env.varm,
            varv=self.env.varv,
            is_vnret_defined=self.tc.defined("VNRET"),
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
            arg8=self.arg7,
        )
        include_uc_ncap = uc_ncap_mod(
            var=self.env.var,
            sow=self.env.sow,
            varv=self.env.varv,
            sws=self.env.sws,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3="T",
            arg4=hs,
            arg5=self.arg8,
            arg6="T",
        )
        include_uc_cap = uc_cap_mod(
            var=self.env.var,
            sow=self.env.sow,
            upscaps=self.env.upscaps,
            vda=self.env.vda,
            abs=self.env.abs,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3="T",
            arg4=hs,
            arg5=self.arg8,
            arg6="T",
        )
        include_uc_act = uc_act_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcActModConfig(
                arg1=(self.arg7_GP,),
                arg2=(self.arg5_GP,),
                arg3=(self.arg6_GP,),
                arg4=(g.t,),
                arg5=(hs_GP,),
                arg6=(self.arg8_GP,),
                arg7=(g.t,),
            ),
        )
        include_uc_com_prd = uc_com_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=(self.arg7_GP,),
                arg2=(self.arg5_GP,),
                arg3=(self.arg6_GP,),
                arg4=(g.t,),
                arg5=(hs_GP,),
                arg6=(self.arg8_GP,),
                arg7=(g.t,),
                arg8=("PRD",),
                arg9=("PRD",),
                arg10=("PD",),
            ),
        )
        include_uc_com_net = uc_com_mod(
            g=g,
            var=self.env.var,
            sow_GP=self.env.sow_GP,
            config=UcComModConfig(
                arg1=(self.arg7_GP,),
                arg2=(self.arg5_GP,),
                arg3=(self.arg6_GP,),
                arg4=(g.t,),
                arg5=(hs_GP,),
                arg6=(self.arg8_GP,),
                arg7=(g.t,),
                arg8=("BAL",),
                arg9=("NET",),
                arg10=("NT",),
            ),
        )
        include_uc_ire = uc_ire_mod(
            var=self.env.var,
            sow=self.env.sow,
            arg1=f"{self.arg4}{self.arg7}",
            arg2=self.arg5,
            arg3=self.arg6,
            arg4="T",
            arg5=hs,
            arg6=self.arg8,
            arg7="T",
        )

        cumcom_term = ""
        if is_several:
            cumcom_term = rf"""
+SUM(({self.arg7}COM_VAR,C,YEAR,LL)$UC_CUMCOM(UC_N,R,COM_VAR,C,YEAR,LL),UC_CUMCOM(UC_N,R,COM_VAR,C,YEAR,LL)*{self.env.var}_CUMCOM(R,C,COM_VAR,YEAR,LL{self.env.swt})*{self.env.cucscal})
"""

        return rf"""
{include_uc_flo}
+
{include_uc_ncap}
+
{include_uc_cap}
+
{include_uc_act}
+
{include_uc_com_prd}
+
{include_uc_com_net}
+
{include_uc_ire}
{cumcom_term}
"""

    def _label_dynamic(
        self: EqusercoMod,
        is_stages: bool,
        is_cli: bool,
    ) -> str:
        g = self.tc

        uc_flo_arg9 = self.env.var  # self.env.set_scoped("swflo", self.env.var)
        uc_flo_arg10 = ""
        uc_flo_arg11 = ""
        uc_flo_arg12 = ""
        self.env.set_scoped("var_GP", self.env.var)

        if is_stages:
            temp_var = self.env.var
            self.env.set_scoped("var", f"SUM({self.arg5}{temp_var}")
            self.env.set_scoped("var_GP", (temp_var, self.arg5_GP))
            self.env.set_scoped("sow", ",WW)")
            self.env.set_scoped("sow_GP", (g.ww,))
            # self.env.set_scoped("swflo", f"{temp_var} ,WW SUM {self.arg5}")
            uc_flo_arg9 = temp_var
            uc_flo_arg10 = " ,WW"
            uc_flo_arg11 = "SUM"
            uc_flo_arg12 = self.arg5

        self.env.set_local("tsum", "SUM(UC_TMAP(TT,T,T,SIDE,'N'),UC_SIGN(SIDE)*")
        # self.env.set_local(
        #     "tsum_GP", ((g.UcTmap[g.tt, g.t, g.t, g.side, "N"], g.uc_sign[g.side]),)
        # )  # NOTE: We multiply in the parent file
        # NOTE: tsum_GP gets passed on from equwrap_mod.py and only changes its value in this file.
        tsum_GP = ((g.UcTmap[g.tt, g.t, g.t, g.side, "N"], g.uc_sign[g.side]),)
        block_tplus = rf"""
(
{
            uc_flo_mod(
                cal_red=self.env.cal_red,
                var=self.env.var,  # TODO: Use self.env.var_GP
                swt=self.env.swt,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws,
                varm=self.env.varm,
                varv=self.env.varv,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="LAGT(T)",
                # arg9=self.env.swflo, !%SWFLO% contains emtpy strings! -> split into multiple arguments
                arg9=uc_flo_arg9,
                arg10=uc_flo_arg10,
                arg11=uc_flo_arg11,
                arg12=uc_flo_arg12,
            )
        }
+
{
            uc_ncap_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                varv=self.env.varv,
                sws=self.env.sws,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="TT",
                arg7="LAGT(T)",
            )
        }
+
{
            uc_cap_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                upscaps=self.env.upscaps,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="TT",
                arg7="LAGT(T)",
            )
        }
+
{
            uc_act_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcActModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(*tsum_GP,),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.tt,),
                    arg8=(g.lagt[g.t],),
                ),
            )
        }
+
{
            uc_com_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcComModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(*tsum_GP,),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.tt,),
                    arg8=("PRD",),
                    arg9=("PRD",),
                    arg10=("PD",),
                    arg11=(g.lagt[g.t],),
                ),
            )
        }
+
{
            uc_com_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcComModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(*tsum_GP,),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.tt,),
                    arg8=("BAL",),
                    arg9=("NET",),
                    arg10=("NT",),
                    arg11=(g.lagt[g.t],),
                ),
            )
        }
+
{
            uc_ire_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=self.env.tsum,
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="TT",
                arg8="LAGT(T)",
            )
        }
+SUM(({self.arg7}UC_GMAP_U(R,UC_N,UCN)),{self.env.tsum} UC_UCN(UC_N,SIDE,R,TT,UCN)*{
            self.env.var  # TODO: Use self.env.var_GP
        }_UCRT(UCN,R,TT{self.env.sow})$UC_RHSRT(R,UCN,TT,'N')))
)$(NOT SUM(UC_DYNDIR(R,UC_N,'RHS'),1))
"""

        self.env.set_local(
            "tsum",
            "SUM(UC_TMAP(T,LL,TT,SIDE,UC_DYNT)$(LIM(UC_DYNT) xor UC_ATTR(R,UC_N,SIDE,",
        )
        self.env.set_local("tucn", ",UC_DYNT)),UC_SIGN(SIDE)*")

        block_tminus = rf"""
(
{
            uc_flo_mod(
                cal_red=self.env.cal_red,
                var=self.env.var,  # TODO: Use self.env.var_GP
                swt=self.env.swt,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow,
                cufscal=self.env.cufscal,
                pgprim=self.env.pgprim,
                sws=self.env.sws,
                varm=self.env.varm,
                varv=self.env.varv,
                is_vnret_defined=self.tc.defined("VNRET"),
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'FLO'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
                arg9=uc_flo_arg9,
                arg10=uc_flo_arg10,
                arg11=uc_flo_arg11,
                arg12=uc_flo_arg12,
            )
        }
+
{
            uc_ncap_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                varv=self.env.varv,
                sws=self.env.sws,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'NCAP'{self.env.tucn}",
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="LL",
                arg7="-LEAD(T)",
            )
        }
+
{
            uc_cap_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                upscaps=self.env.upscaps,
                vda=self.env.vda,
                abs=self.env.abs,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'CAP'{self.env.tucn}",
                arg3="TT",
                arg4="SIDE",
                arg5=self.arg8,
                arg6="LL",
                arg7="-LEAD(T)",
            )
        }
+
{
            uc_act_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcActModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(make_arg2(g, set_element="ACT"),),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.ll,),
                    arg8=(-g.lead[g.t],),
                ),
            )
        }
+
{
            uc_com_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcComModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(make_arg2(g, set_element="COMPRD"),),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.ll,),
                    arg8=("PRD",),
                    arg9=("PRD",),
                    arg10=("PD",),
                    arg11=(-g.lead[g.t],),
                ),
            )
        }
+
{
            uc_com_mod(
                g=g,
                var=self.env.var_GP,
                sow_GP=self.env.sow_GP,
                config=UcComModConfig(
                    arg1=(self.arg7_GP,),
                    arg2=(make_arg2(g, set_element="COMNET"),),
                    arg3=(self.arg6_GP,),
                    arg4=(g.tt,),
                    arg5=(g.side,),
                    arg6=(self.arg8_GP,),
                    arg7=(g.ll,),
                    arg8=("BAL",),
                    arg9=("NET",),
                    arg10=("NT",),
                    arg11=(-g.lead[g.t],),
                ),
            )
        }
+
{
            uc_ire_mod(
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'IRE'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
            )
        }
+SUM(({self.arg7}UC_GMAP_U(R,UC_N,UCN)),{self.env.tsum}'UCN'{
            self.env.tucn
        } UC_UCN(UC_N,SIDE,R,LL,UCN)*{
            self.env.var
        }_UCRT(UCN,R,TT{  # TODO: Use self.env.var_GP
            self.env.sow
        })$UC_RHSRT(R,UCN,TT,'N')))
{
            uc_cli_mod(
                is_uc_cli_defined=self.tc.defined("UC_CLI"),
                var=self.env.var,  # TODO: Use self.env.var_GP
                sow=self.env.sow,
                arg1=f"{self.arg4}{self.arg7}",
                arg2=f"{self.env.tsum}'CLI'{self.env.tucn}",
                arg3=self.arg6,
                arg4="TT",
                arg5="SIDE",
                arg6=self.arg8,
                arg7="LL",
                arg8="-LEAD(T)",
            )
            if is_cli
            else ""
        }
-
{
            uc_pasti_mod(
                arg1=f"{self.arg4}{self.arg7}",
                arg2="MIYR_1",
                arg3="T",
                arg4="'RHS'",
            )
        }
)$SUM(UC_DYNDIR(R,UC_N,'RHS'),1)
"""
        return block_tplus + "\n+\n" + block_tminus
