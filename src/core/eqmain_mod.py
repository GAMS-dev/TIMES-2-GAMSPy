# eqmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQMAIN.MOD declarations & call for actual equations                         *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
# *GaG Questions/Comments:
# *   - any non-binding (=N=) accounting equations, or do it all with reports?
# *   - what about scaling (by region)???
# *   - declare all equations so that re-start changing models will work
# *   - if UP then EQl_ is =L=, LO then EQl_ is =G=, FX then EQl_ is =E=
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Loop, Number, Parameter, Set, SpecialValues, Sum
from gamspy._symbols.implicits import ImplicitParameter, ImplicitVariable
from gamspy.math import project

from core.base_class import GamsClass
from core.coef_csv_mod import CoefCsvMod
from core.eqactbnd_mod import EqactbndMod, EqactbndModConfig
from core.eqactflo_mod import EqactfloMod
from core.eqblnd_mod import EqblndMod
from core.eqbndcom_mod import EqbndcomMod, EqbndcomModConfig
from core.eqbndcst_mod import EqbndcstMod
from core.eqcapact_mod import EqcapactMod, EqcapactModConfig
from core.eqcombal_mod import EqcombalMod
from core.eqcpt_mod import EqcptMod, EqcptModConfig
from core.eqcumcom_mod import EqcumcomMod
from core.eqcumflo_mod import EqcumfloMod
from core.eqdamage_mod import EqdamageMod
from core.eqdeclr_mod import EqdeclrMod
from core.eqdeclr_tm import EqdeclrTm
from core.eqflobnd_mod import EqflobndMod, EqflobndModConfig
from core.eqflofr_mod import EqflofrMod, EqflofrModConfig
from core.eqflomrk_mod import EqflomrkMod
from core.eqfloshr_mod import EqfloshrMod, EqfloshrModConfig
from core.eqire_mod import EqireMod
from core.eqirebnd_mod import EqirebndMod, EqirebndModConfig
from core.eqmacro_tm import EqmacroTm
from core.eqobj_mod import EqobjMod
from core.eqobj_tm import EqobjTm
from core.eqpeak_mod import EqpeakMod
from core.eqptrans_mod import EqptransMod
from core.eqstgaux_lin import EqstgauxLin
from core.eqstgaux_mod import EqstgauxMod
from core.eqstgflo_mod import EqstgfloMod, EqstgfloModConfig
from core.eqstgips_lin import EqstgipsLin
from core.eqstgips_mod import EqstgipsMod
from core.eqstgtss_mod import EqstgtssMod
from core.equ_ext_vda import EquExtVda
from core.equcwrap_mod import EqucwrapMod, EqucwrapModConfig
from core.eqxbnd_mod import EqxbndMod, EqxbndModConfig
from core.recurrin_stc import RecurrinStc
from core.utils import apply_ewispine, apply_sw_stvars, apply_witspine
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqmainMod(GamsClass):
    """Translation unit for eqmain.mod."""

    # Instance attributes
    module_name: str = "eqmain_mod"
    gams_source: str = "eqmain.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: Literal["mod"]
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        if not self.env.is_set("cufscal"):
            self.env.set_global("cufscal", 10)
        if not self.env.is_set("cucscal"):
            self.env.set_global("cucscal", 1000)

        # Equations
        if self.arg1.upper() == "MOD":
            self.include(EqdeclrMod(tc=self.tc, env=self.env, arg1=self.arg1))
        elif self.arg1.upper() == "TM":
            self.include(EqdeclrTm(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            raise ValueError(f"Extension {self.arg1} not available.")

        if self.env.vda.upper() == "YES":
            self.include(EquExtVda(tc=self.tc, env=self.env, arg1="DECLR"))

        # Objective Function
        ## Main OBJ
        g.sum_obj = Parameter(
            m,
            name="SUM_OBJ",
            domain=[g.item, g.item],
            description="Objective component summation",
        )

        if self.env.spines.upper() == "YES":
            self.include(RecurrinStc(tc=self.tc, env=self.env, arg1="SPINES"))
        if self.env.stages == "YES":
            apply_sw_stvars(env=self.env, g=self.tc, witspine=self.env.witspine)

        if self.env.obj.upper() != "LIN":
            self.env.set_local("obj", self.arg1.upper())
        if self.env.macro.upper() != "YES":
            self.include(EqobjMod(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            self.include(EqobjTm(tc=self.tc, env=self.env))

        if self.env.spines.upper() == "YES":
            apply_ewispine(env=self.env)

        # Relationship between process activity & individual primary commodity flows
        self.include(EqactfloMod(tc=self.tc, env=self.env))

        # Bound of vintage process activity or TS-level above PRC_TS
        # *V0.5b avoid equations if LO=0/UP=INF
        act_bnd, r, t, p, s = g.act_bnd, g.r, g.t, g.p, g.s
        eqactbnd_batincludes: list[EqactbndModConfig] = [
            EqactbndModConfig("G", "LO", act_bnd[r, t, p, s, "LO"] != 0),
            EqactbndModConfig("E", "FX", Number(1)),
            EqactbndModConfig(
                "L", "UP", act_bnd[r, t, p, s, "UP"] != SpecialValues.POSINF
            ),
        ]
        for eqactbnd_config in eqactbnd_batincludes:
            self.include(EqactbndMod(tc=self.tc, env=self.env, config=eqactbnd_config))

        # Bound on commodity Net/Production activity above COM_TS
        # fmt: off
        eqbndcom_batincludes: list[EqbndcomModConfig]= [
            EqbndcomModConfig("G", "LO", (g.com_bndnet[g.r,g.t,g.c,g.s, 'LO'] != 0), "NET"),
            EqbndcomModConfig("E", "FX", Number(1), "NET"),
            EqbndcomModConfig("L", "UP", (g.com_bndnet[g.r,g.t,g.c,g.s,'UP'] != SpecialValues.POSINF), "NET"),
            EqbndcomModConfig("G", "LO", (g.com_bndprd[g.r,g.t,g.c,g.s, 'LO'] != 0), "PRD"),
            EqbndcomModConfig("E", "FX", Number(1), "PRD"),
            EqbndcomModConfig("L", "UP", (g.com_bndprd[g.r,g.t,g.c,g.s,'UP'] != SpecialValues.POSINF), "PRD"),
        ]
        # fmt: on
        for eqbndcom_config in eqbndcom_batincludes:
            self.include(EqbndcomMod(tc=self.tc, env=self.env, config=eqbndcom_config))

        # Utilization equation ensure activity <= or = capacity
        eqcapact_batincludes: list[EqcapactModConfig] = [
            EqcapactModConfig(sense="E", bound_type="FX", arg3=self.env.mx_GP),
            EqcapactModConfig(sense="L", bound_type="UP", arg3=self.env.mx_GP),
            EqcapactModConfig(sense="G", bound_type="LO", arg3=()),
        ]
        for eqcapact_config in eqcapact_batincludes:
            self.include(EqcapactMod(tc=self.tc, env=self.env, config=eqcapact_config))

        if self.tc.defined("PRC_SIMV"):
            self.include(CoefCsvMod(tc=self.tc, env=self.env))

        # Capacity transfer constraint
        if self.env.spines.upper() == "YES":
            apply_witspine(env=self.env)
        if self.env.validate == "YES":
            self._m2t()
        else:
            self._no_m2t()

        # Cumulative Net/Production Commodity Limit
        self.include(EqcumcomMod(tc=self.tc, env=self.env, arg1="E", arg2="NET"))
        self.include(EqcumcomMod(tc=self.tc, env=self.env, arg1="E", arg2="PRD"))
        # Cumulative process flow / activity
        self.include(EqcumfloMod(tc=self.tc, env=self.env))
        if self.env.spines.upper() == "YES":
            apply_ewispine(env=self.env)

        # Basic commodity balance equations (by type) ensuring that production >=/= consumption
        self.include(
            EqcombalMod(
                tc=self.tc,
                env=self.env,
                arg1=self.arg1,
                arg2="G",
                arg3="LO",
                arg4="BAL",
                arg5=Number(1),
            )
        )
        self.include(
            EqcombalMod(
                tc=self.tc,
                env=self.env,
                arg1=self.arg1,
                arg2="E",
                arg3="FX",
                arg4="BAL",
                arg5=Number(1),
            )
        )
        # non-binding equation for FRERENEW/CONSRV commodities
        # self.include(EqcombalMod(tc=self.tc, env=self.env, arg1=self.arg1, arg2='L', arg3='UP', arg4='BAL'))

        # Limiting equation when total production is to be constrained
        self.include(
            EqcombalMod(
                tc=self.tc,
                env=self.env,
                arg1=self.arg1,
                arg2="E",
                arg3="FX",
                arg4="PRD",
                arg5=g.RhsComprd[g.r, g.t, g.c, g.s],
            )
        )

        # Bound on the flow variable
        eqflobnd_batincludes: list[EqflobndModConfig] = [
            EqflobndModConfig(sense="G", arg2="LO", arg3=Number(1)),
            EqflobndModConfig(sense="E", arg2="FX", arg3=Number(1)),
            EqflobndModConfig(
                sense="L",
                arg2="UP",
                arg3=g.flo_bnd[g.r, g.t, g.p, g.cg, g.s, "UP"] != SpecialValues.POSINF,
            ),
        ]

        for eqflobnd_config in eqflobnd_batincludes:
            self.include(EqflobndMod(tc=self.tc, env=self.env, config=eqflobnd_config))

        # Fraction of a flow within a specific time slice
        eqflofr_batincludes: list[EqflofrModConfig] = [
            EqflofrModConfig(arg1="L", arg2="LO"),
            EqflofrModConfig(arg1="E", arg2=g.Lnx),
            EqflofrModConfig(arg1="G", arg2="UP"),
        ]
        for eqflofr_config in eqflofr_batincludes:
            self.include(EqflofrMod(tc=self.tc, env=self.env, config=eqflofr_config))

        # Market share equation allocating commodity percentages of a group
        eqfloshr_batincludes: list[EqfloshrModConfig] = [
            EqfloshrModConfig(sense="L", arg2="LO", arg3="IN"),
            EqfloshrModConfig(sense="E", arg2="FX", arg3="IN"),
            EqfloshrModConfig(sense="G", arg2="UP", arg3="IN"),
        ]
        for eqfloshr_config in eqfloshr_batincludes:
            self.include(EqfloshrMod(tc=self.tc, env=self.env, config=eqfloshr_config))

        # Product share equation allocating commodity percentages of a group
        eqfloshr_batincludes = [
            EqfloshrModConfig(sense="L", arg2="LO", arg3="OUT"),
            EqfloshrModConfig(sense="E", arg2="FX", arg3="OUT"),
            EqfloshrModConfig(sense="G", arg2="UP", arg3="OUT"),
        ]
        for eqfloshr_config in eqfloshr_batincludes:
            self.include(EqfloshrMod(tc=self.tc, env=self.env, config=eqfloshr_config))

        # Process market share constraint in total commodity production
        eqflomrk_batincludes: list[tuple[Literal["E", "N", "L", "G"], str]] = [
            ("G", "LO"),
            ("E", "FX"),
            ("L", "UP"),
        ]
        for arg1, arg2 in eqflomrk_batincludes:
            self.include(EqflomrkMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2))

        # Inter-regional exchange
        self.include(EqireMod(tc=self.tc, env=self.env))

        # Bound on exchange between internal regions
        # *V0.5b avoid equations if LO=0/UP=INF
        eqirebndMod_batincludes: list[EqirebndModConfig] = [
            EqirebndModConfig(
                "G", "LO", (g.ire_bnd[g.r, g.t, g.c, g.s, g.allreg, g.ie, "LO"] != 0)
            ),
            EqirebndModConfig("E", "FX", Number(1)),
            EqirebndModConfig(
                "L",
                "UP",
                (
                    g.ire_bnd[g.r, g.t, g.c, g.s, g.allreg, g.ie, "UP"]
                    != SpecialValues.POSINF
                ),
            ),
        ]
        for eqirebnd_config in eqirebndMod_batincludes:
            self.include(EqirebndMod(tc=self.tc, env=self.env, config=eqirebnd_config))

        # Commodity peaking
        self.include(EqpeakMod(tc=self.tc, env=self.env, arg1=self.arg1))

        # Commodity-to-commodity transformation
        self.include(EqptransMod(tc=self.tc, env=self.env))

        # Inter-period storage
        if self.env.obj.upper() == "LIN":
            self.include(EqstgipsLin(tc=self.tc, env=self.env))
            self.include(EqstgauxLin(tc=self.tc, env=self.env))
        elif self.env.obj.upper() == "MOD":
            self.include(EqstgipsMod(tc=self.tc, env=self.env))
            self.include(EqstgauxMod(tc=self.tc, env=self.env))
        else:
            raise ValueError(
                f"Invalid extension {self.env.obj} for eqstgips_<ext>.py and eqstgaux_<ext>.py."
            )

        # Time-slice storage
        self.include(EqstgtssMod(tc=self.tc, env=self.env))

        # Bound on input/output flows of storage process
        eqstgflo_batincludes: list[EqstgfloModConfig] = [
            EqstgfloModConfig(arg1="IN", arg2="G", arg3="LO", arg4=0),
            EqstgfloModConfig(arg1="IN", arg2="E", arg3="FX", arg4=SpecialValues.NA),
            EqstgfloModConfig(
                arg1="IN", arg2="L", arg3="UP", arg4=SpecialValues.POSINF
            ),
            EqstgfloModConfig(arg1="OUT", arg2="G", arg3="LO", arg4=0),
            EqstgfloModConfig(arg1="OUT", arg2="E", arg3="FX", arg4=SpecialValues.NA),
            EqstgfloModConfig(
                arg1="OUT", arg2="L", arg3="UP", arg4=SpecialValues.POSINF
            ),
        ]
        for eqstgflo_config in eqstgflo_batincludes:
            self.include(EqstgfloMod(tc=self.tc, env=self.env, config=eqstgflo_config))

        if self.env.spines.upper() == "YES":
            apply_witspine(env=self.env)

        # Bounds on undiscounted costs by region, category and currency
        self.include(EqbndcstMod(tc=self.tc, env=self.env))

        # User-constraints
        if (g.uc_time.number_records + g.uc_ucn.number_records) > 0:
            self.env.set_global("var_uc", "YES")

        # Commissioning periods for UCs
        g.Rvpt = Set(m, name="RVPT", domain=[g.r, g.allyear, g.p, g.t])
        self.tc.enqueue(self.exec1)

        # Define a map for region and milestone year specific user constraints to be generated
        ucbd: tuple[()] | tuple[Set | Alias] = ()
        tmp: tuple[()] | tuple[Set | Alias] = ()
        take: Number | ImplicitParameter = Number(1)
        self.env.set_local("uclim", ",LIM")
        if self.env.var_uc != "YES":
            ucbd = (g.bd,)
            tmp = (g.lim,)
            take = g.uc_rhsrt[g.r, g.ucn, g.t, g.bd]
            self.env.set_local("uclim", ",BD")

        self.add_sets(ucbd=ucbd, tmp=tmp)
        self.tc.enqueue(self.exec2, ucbd=ucbd, take=take)

        equcwrap_batincludes: list[EqucwrapModConfig] = [
            EqucwrapModConfig(
                arg1="E",
                arg2=g.bd,
                arg3=(),
                arg4=g.bd,
                arg5=1,
                arg6="NOT",
            ),
            EqucwrapModConfig(
                arg1="E",
                arg2="FX",
                arg3=("FX",),
            ),
            EqucwrapModConfig(
                arg1="G",
                arg2="LO",
                arg3=("LO",),
            ),
            EqucwrapModConfig(
                arg1="L",
                arg2="UP",
                arg3=("UP",),
            ),
        ]

        for equcwrap_config in equcwrap_batincludes:
            self.include(EqucwrapMod(tc=self.tc, env=self.env, config=equcwrap_config))

        if self.env.spines.upper() == "YES":
            apply_ewispine(env=self.env)

        # Bound on total inter-regional exchange, including external+internal regions
        # *V0.5b avoid equations if LO=0/UP=INF
        all_reg, t, c, s, ie, ire_xbnd = g.allreg, g.t, g.c, g.s, g.ie, g.ire_xbnd
        batincludes: list[EqxbndModConfig] = [
            EqxbndModConfig(
                arg1="G", arg2="LO", arg3=ire_xbnd[all_reg, t, c, s, ie, "LO"] != 0
            ),
            EqxbndModConfig(arg1="E", arg2="FX", arg3=Number(1)),
            EqxbndModConfig(
                arg1="L",
                arg2="UP",
                arg3=ire_xbnd[all_reg, t, c, s, ie, "UP"] != float("inf"),
            ),
        ]

        for eqxbnd_config in batincludes:
            self.include(EqxbndMod(tc=self.tc, env=self.env, config=eqxbnd_config))

        # *GG* V07_2 Refinery blending
        # Blending constraint to a specification characteristic
        eqblnd_batincludes: list[tuple[Literal["L", "G", "E", "N"], int]] = [
            ("L", 1),
            ("G", 2),
            ("E", 3),
            ("N", 4),
        ]
        for type, code in eqblnd_batincludes:
            self.include(
                EqblndMod(tc=self.tc, env=self.env, equation_type=type, blnd_code=code)
            )

        # MACRO equations
        if self.env.macro == "YES":
            self.include(EqmacroTm(tc=self.tc, env=self.env))

        if self.tc.defined("DAM_COST"):
            self.include(EqdamageMod(tc=self.tc, env=self.env))

    def _m2t(self: EqmainMod) -> None:
        g = self.tc
        var_cap = macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, self.env.sow_GP)
        assert isinstance(var_cap, ImplicitVariable), (
            "self.env.var carries no var_set here, so VAR_CAP_GP should never return a Sum"
        )

        batincludes: list[EqcptModConfig] = [
            EqcptModConfig(
                sense="E",
                arg2="E",
                arg3=~g.PrcMap[g.r, "DMD", g.p],
                arg4=var_cap,
            ),
            EqcptModConfig(
                sense="L",
                arg2="L",
                arg3=g.PrcMap[g.r, "DMD", g.p],
                arg4=var_cap,
            ),
            EqcptModConfig(
                sense="G",
                arg2="G",
                arg3=Number(0),
                arg4=Number(0),
            ),
        ]

        for eqcpt_config in batincludes:
            self.include(EqcptMod(tc=self.tc, env=self.env, config=eqcpt_config))

    def _no_m2t(self: EqmainMod) -> None:
        g = self.tc
        var_cap = macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, self.env.sow_GP)
        assert isinstance(var_cap, ImplicitVariable), (
            "self.env.var carries no var_set here, so VAR_CAP_GP should never return a Sum"
        )

        self.tc.enqueue(self.assign_rtp_varp, etl=self.env.etl, macro=self.env.macro)

        batincludes: list[EqcptModConfig] = [
            EqcptModConfig(
                sense="E",
                arg2="E",
                arg3=(g.RtpVarp[g.r, g.t, g.p] | g.cap_bnd[g.r, g.t, g.p, "FX"]),
                arg4=var_cap,
            ),
            EqcptModConfig(
                sense="L",
                arg2="L",
                arg3=(~g.RtpVarp[g.r, g.t, g.p]).where[g.cap_bnd[g.r, g.t, g.p, "LO"]],
                arg4=g.cap_bnd[g.r, g.t, g.p, "LO"],
            ),
            EqcptModConfig(
                sense="G",
                arg2="G",
                arg3=(~g.RtpVarp[g.r, g.t, g.p]).where[g.cap_bnd[g.r, g.t, g.p, "UP"]],
                arg4=g.cap_bnd[g.r, g.t, g.p, "UP"],
            ),
        ]

        for eqcpt_config in batincludes:
            self.include(EqcptMod(tc=self.tc, env=self.env, config=eqcpt_config))

    def assign_rtp_varp(self: EqmainMod, etl: str, macro: str) -> None:
        g = self.tc

        if etl.upper() == "YES":
            g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[g.Teg[g.p]] = True
        if macro.upper() == "YES":
            g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[
                (g.tm_qfac[g.r] != 0) & g.tm_captb[g.r, g.p]
            ] = True

    def exec1(self: EqmainMod) -> None:
        g = self.tc

        with Loop(g.Obj2a[g.r, g.t, g.p].where[~g.RtpOff[g.r, g.t, g.p]]):
            g.f[...] = g.b[g.t] + g.ncap_iled[g.r, g.t, g.p]
            g.z[...] = Sum(g.Vnt[g.t, g.tt].where[g.f > g.e[g.tt] + 0.5], 1)
            g.Rvpt[g.r, g.t, g.p, g.t + g.z] = True
        g.RtpOff[g.Obj2a[g.r, g.t, g.p]].where[~Sum(g.Rvpt[g.r, g.t, g.p, g.tt], 1)] = (
            True
        )

    def add_sets(
        self: EqmainMod,
        ucbd: tuple[()] | tuple[Set | Alias],
        tmp: tuple[()] | tuple[Set | Alias],
    ) -> None:
        g = self.tc
        m = g.container

        g.UcRhstmp = Set(
            m, name="UC_RHSTMP", domain=[g.Reg, g.ucn, g.t, g.s, *ucbd, g.ucnumber]
        )
        g.UcRhsmap = Set(
            m, name="UC_RHSMAP", domain=[g.Reg, g.t, g.ucn, g.ucnumber, g.s, *ucbd]
        )
        g.Ructs = Set(m, name="RUCTS", domain=[g.allreg, g.ucn, g.allyear, g.ts, *tmp])
        g.UcUt = Set(m, name="UC_UT", domain=[g.ucn, g.allyear, *tmp])
        g.UcUts = Set(m, name="UC_UTS", domain=[g.ucn, g.allyear, g.ts, *tmp])
        g.UcTmap = Set(
            m, name="UC_TMAP", domain=[g.year, g.year, g.t, g.side, g.UcDynt]
        )

    def exec2(
        self: EqmainMod,
        ucbd: tuple[()] | tuple[Set | Alias],
        take: Number | ImplicitParameter,
    ) -> None:
        g = self.tc

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
 UC_TMAP(T,TT(T-DIAG(SIDE,'RHS')),TT,SIDE,'N') = YES;
 UC_TMAP(T,TT(T-DIAG(SIDE,'RHS')),MILESTONYR,SIDE,'CUMSUM')$(ORD(T) > ORD(MILESTONYR)+DIAG(SIDE,'RHS')) = YES;

""",
        )

        # TODO: diag not supported yet, see devel/gamspy#858
        # g.UcTmap[g.t, g.tt[g.t - g.side.diag("RHS")], g.tt, g.side, "N"] = True
        # g.UcTmap[g.t, g.tt[g.t - g.side.diag("RHS")], g.Milestonyr, g.side, "CUMSUM"].where[Ord(T) > Ord(g.Milestonyr) + g.side.diag("RHS")] = True

        g.UcTmap[g.t, g.t, g.t, "RHS", "SYNC"] = True
        g.UcTmap[g.t, g.t, g.tt, "RHS", "CUM+"].where[
            g.UcTmap[g.t, g.t, g.tt, "LHS", "CUMSUM"]
        ] = True

        if g.uc_rhsrt.number_records:
            project(g.uc_rhsrt, g.RUct)
            project(g.UcTsSum, g.RUc)

            g.UcRhstmp[
                g.RUct[g.RUc[g.r, g.ucn], g.t], g.Annual, *ucbd, "SEVERAL"
            ].where[take & g.UcTEach[g.r, g.ucn, g.t]] = True
            g.UcRhstmp[
                g.RUct[g.RUc[g.r, g.ucn], g.t], g.Annual, *ucbd, "DYNAMIC"
            ].where[take & g.UcTSucc[g.r, g.ucn, g.t]] = True

            g.RUc.setRecords(None)
            g.RUct.setRecords(None)

        if g.uc_rhsrts.number_records:
            project(g.uc_rhsrts, g.Ructs)
            g.UcRhstmp[
                g.Ructs[g.UcTEach[g.UcREach[g.r, g.ucn], g.t], g.s, *ucbd], "EACH"
            ].where[g.UcTsEach[g.r, g.ucn, g.s]] = True
            g.UcRhstmp[
                g.Ructs[g.UcTSucc[g.UcREach[g.r, g.ucn], g.t], g.s, *ucbd], "SUCC"
            ].where[g.UcTsEach[g.r, g.ucn, g.s]] = True
            g.UcRhstmp[
                g.Ructs[g.UcTEach[g.UcREach[g.r, g.ucn], g.t], g.s, *ucbd],
                g.ucnumber[g.tsl],
            ].where[g.TsGroup[g.r, g.tsl, g.s] & g.UcDs[g.r, g.ucn, g.tsl]] = True

        project(g.UcTSucc, g.UcRtsuc)
        project(g.UcRhstmp, g.UcRhsmap)
        project(g.uc_rhst, g.UcUt)
        project(g.uc_rhsts, g.UcUts)
        g.UcRhstmp.setRecords(None)
        g.Ructs.setRecords(None)
