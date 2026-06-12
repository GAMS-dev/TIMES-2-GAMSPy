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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.equcwrap_mod import EqucwrapArg6Type

from core.coef_csv_mod import CoefCsvMod
from core.eqactbnd_mod import EqactbndMod
from core.eqactflo_mod import EqactfloMod
from core.eqblnd_mod import EqblndMod
from core.eqbndcom_mod import EqbndcomMod
from core.eqbndcst_mod import EqbndcstMod
from core.eqcapact_mod import EqcapactMod
from core.eqcombal_mod import EqcombalMod
from core.eqcpt_mod import EqcptMod
from core.eqcumcom_mod import EqcumcomMod
from core.eqcumflo_mod import EqcumfloMod
from core.eqdamage_mod import EqdamageMod
from core.eqdeclr_mod import EqdeclrMod
from core.eqdeclr_tm import EqdeclrTm
from core.eqflobnd_mod import EqflobndMod
from core.eqflofr_mod import EqflofrMod
from core.eqflomrk_mod import EqflomrkMod
from core.eqfloshr_mod import EqfloshrMod
from core.eqire_mod import EqireMod
from core.eqirebnd_mod import EqirebndMod
from core.eqmacro_tm import EqmacroTm
from core.eqobj_mod import EqobjMod
from core.eqobj_tm import EqobjTm
from core.eqpeak_mod import EqpeakMod
from core.eqptrans_mod import EqptransMod
from core.eqstgaux_lin import EqstgauxLin
from core.eqstgaux_mod import EqstgauxMod
from core.eqstgflo_mod import EqstgfloMod
from core.eqstgips_lin import EqstgipsLin
from core.eqstgips_mod import EqstgipsMod
from core.eqstgtss_mod import EqstgtssMod
from core.equ_ext_vda import EquExtVda
from core.equcwrap_mod import EqucwrapMod
from core.eqxbnd_mod import EqxbndMod
from core.recurrin_stc import RecurrinStc

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqmainMod(GamsClass):
    """Translation unit for eqmain.mod."""

    # Instance attributes
    module_name: str = "eqmain_mod"
    gams_source: str = "eqmain.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self.arg1 = arg1
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if not self.env.is_set("cufscal"):
            self.env.set_global("cufscal", "10")
        if not self.env.is_set("cucscal"):
            self.env.set_global("cucscal", "1000")

        # Equations
        if self.arg1.upper() == "MOD":
            self.include(EqdeclrMod(tc=self.tc, env=self.env, arg1=self.arg1))
        elif self.arg1.upper() == "TM":
            self.include(EqdeclrTm(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            raise Exception(f"Extension {self.arg1} not available.")

        if self.env.vda.upper() == "YES":
            self.include(EquExtVda(tc=self.tc, env=self.env, arg1="DECLR"))

        # Objective Function
        ## Main OBJ
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="PARAMETER SUM_OBJ(ITEM,ITEM) 'Objective component summation';",
        )

        if self.env.spines.upper() == "YES":
            self.include(RecurrinStc(tc=self.tc, env=self.env, arg1="SPINES"))
        if self.env.stages == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                # TODO: need to check possible values for variables
                code=rf"${self.env.witspine} {self.env.sw_stvars}",
            )

        if self.env.obj.upper() != "LIN":
            self.env.set_local("obj", self.arg1.upper())
        if self.env.macro.upper() != "YES":
            self.include(EqobjMod(tc=self.tc, env=self.env, arg1=self.arg1))
        else:
            self.include(EqobjTm(tc=self.tc, env=self.env))

        if self.env.spines.upper() == "YES":
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.ewispine}"
            )

        # Relationship between process activity & individual primary commodity flows
        self.include(EqactfloMod(tc=self.tc, env=self.env))

        # Bound of vintage process activity or TS-level above PRC_TS
        # *V0.5b avoid equations if LO=0/UP=INF
        eqactbnd_batincludes: list[tuple[str, str, str]] = [
            ("G", "LO", "(ACT_BND(R,T,P,S,'LO') NE 0)"),
            ("E", "FX", "YES"),
            ("L", "UP", "(ACT_BND(R,T,P,S,'UP') NE INF)"),
        ]
        for arg1, arg2, arg3 in eqactbnd_batincludes:
            self.include(
                EqactbndMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

        # Bound on commodity Net/Production activity above COM_TS
        # fmt: off
        eqbndcom_batincludes: list[tuple[str, str, str, str]] = [
            ("G", "LO", "(COM_BNDNET(R,T,C,S,'LO') NE 0)", "NET"),
            ("E", "FX", "YES", "NET"),
            ("L", "UP", "(COM_BNDNET(R,T,C,S,'UP') NE INF)", "NET"),
            ("G", "LO", "(COM_BNDPRD(R,T,C,S,'LO') NE 0)", "PRD"),
            ("E", "FX", "YES", "PRD"),
            ("L", "UP", "(COM_BNDPRD(R,T,C,S,'UP') NE INF)", "PRD"),
        ]
        # fmt: on
        for arg1, arg2, arg3, arg4 in eqbndcom_batincludes:
            self.include(
                EqbndcomMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                )
            )

        # Utilization equation ensure activity <= or = capacity
        eqcapact_batincludes: list[tuple[str, str, str]] = [
            ("E", "FX", self.env.mx),
            ("L", "UP", self.env.mx),
            ("G", "LO", ""),
        ]
        for arg1, arg2, arg3 in eqcapact_batincludes:
            self.include(
                EqcapactMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

        if self.tc.defined("PRC_SIMV"):
            self.include(CoefCsvMod(tc=self.tc, env=self.env))

        # Capacity transfer constraint
        if self.env.spines.upper() == "YES":
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.witspine}"
            )
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
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.ewispine}"
            )

        # Basic commodity balance equations (by type) ensuring that production >=/= consumption
        self.include(
            EqcombalMod(
                tc=self.tc,
                env=self.env,
                arg1=self.arg1,
                arg2="G",
                arg3="LO",
                arg4="BAL",
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
                arg5="* RHS_COMPRD(R,T,C,S)",
            )
        )

        # Bound on the flow variable
        eqflobnd_batincludes: list[tuple[str, str, str]] = [
            ("G", "LO", "YES"),
            ("E", "FX", "YES"),
            ("L", "UP", "(FLO_BND(R,T,P,CG,S,'UP') NE INF)"),
        ]

        for arg1, arg2, arg3 in eqflobnd_batincludes:
            self.include(
                EqflobndMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

        # Fraction of a flow within a specific time slice
        eqflofr_batincludes: list[tuple[str, str]] = [
            ("L", "'LO'"),
            ("E", "LNX"),
            ("G", "'UP'"),
        ]
        for arg1, arg2 in eqflofr_batincludes:
            self.include(EqflofrMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2))

        # Market share equation allocating commodity percentages of a group
        eqfloshr_batincludes: list[tuple[str, str, str]] = [
            ("L", "LO", "IN"),
            ("E", "FX", "IN"),
            ("G", "UP", "IN"),
        ]
        for arg1, arg2, arg3 in eqfloshr_batincludes:
            self.include(
                EqfloshrMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

        # Product share equation allocating commodity percentages of a group
        eqfloshr_batincludes = [
            ("L", "LO", "OUT"),
            ("E", "FX", "OUT"),
            ("G", "UP", "OUT"),
        ]
        for arg1, arg2, arg3 in eqfloshr_batincludes:
            self.include(
                EqfloshrMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

        # Process market share constraint in total commodity production
        eqflomrk_batincludes: list[tuple[str, str]] = [
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
        eqirebnd_batincludes: list[tuple[str, str, str]] = [
            ("G", "LO", "(IRE_BND(R,T,C,S,ALL_REG,IE,'LO') NE 0)"),
            ("E", "FX", "YES"),
            ("L", "UP", "(IRE_BND(R,T,C,S,ALL_REG,IE,'UP') NE INF)"),
        ]
        for arg1, arg2, arg3 in eqirebnd_batincludes:
            self.include(
                EqirebndMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
            )

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
            raise Exception(
                f"Invalid extension {self.env.obj} for eqstgips_<ext>.py and eqstgaux_<ext>.py."
            )

        # Time-slice storage
        self.include(EqstgtssMod(tc=self.tc, env=self.env))

        # Bound on input/output flows of storage process
        eqstgflo_batincludes: list[tuple[str, str, str, str]] = [
            ("IN", "G", "LO", "0"),
            ("IN", "E", "FX", "NA"),
            ("IN", "L", "UP", "INF"),
            ("OUT", "G", "LO", "0"),
            ("OUT", "E", "FX", "NA"),
            ("OUT", "L", "UP", "INF"),
        ]
        for arg1, arg2, arg3, arg4 in eqstgflo_batincludes:
            self.include(
                EqstgfloMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                )
            )

        if self.env.spines.upper() == "YES":
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.witspine}"
            )

        # Bounds on undiscounted costs by region, category and currency
        self.include(EqbndcstMod(tc=self.tc, env=self.env))

        # User-constraints
        uc_time = self.tc.container["UC_TIME"]
        uc_ucn = self.tc.container["UC_UCN"]
        if (uc_time.number_records + uc_ucn.number_records) > 0:
            self.env.set_global("var_uc", "YES")

        # Commissioning periods for UCs
        self.tc.add_gams_code(
            module=self, phase="init", code="SET RVPT(R,ALLYEAR,P,T);"
        )
        self.tc.enqueue(self.exec1)

        # Define a map for region and milestone year specific user constraints to be generated
        self.env.set_local("ucbd", "")
        self.env.set_local("uclim", ",LIM")
        self.env.set_local("tmp", "")
        self.env.set_local("take", "")
        if self.env.var_uc != "YES":
            self.env.set_local("ucbd", ",BD")
            self.env.set_local("uclim", ",BD")
            self.env.set_local("tmp", ",LIM")
            self.env.set_local("take", "UC_RHSRT(R,UC_N,T,BD)$")

        self.add_sets(ucbd=self.env.ucbd, tmp=self.env.tmp)
        self.tc.enqueue(self.exec2, ucbd=self.env.ucbd, take=self.env.take)

        equcwrap_batincludes: list[tuple[str, str, str, str, str, EqucwrapArg6Type]] = [
            ("E", "BD", "", "SUM(BD$", ",1)", "NOT"),
            ("E", "'FX'", ",'FX'", "", "", ""),
            ("G", "'LO'", ",'LO'", "", "", ""),
            ("L", "'UP'", ",'UP'", "", "", ""),
        ]
        for arg1, arg2, arg3, arg4, arg5, arg6 in equcwrap_batincludes:
            self.include(
                EqucwrapMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                    arg5=arg5,
                    arg6=arg6,
                )
            )

        if self.env.spines.upper() == "YES":
            # TODO: Resolve
            self.tc.add_gams_code(
                module=self, phase="init", code=f"${self.env.ewispine}"
            )

        # Bound on total inter-regional exchange, including external+internal regions
        # *V0.5b avoid equations if LO=0/UP=INF
        batincludes = [
            ("G", "LO", "(IRE_XBND(ALL_REG,T,C,S,IE,'LO') NE 0)"),
            ("E", "FX", "YES"),
            ("L", "UP", "(IRE_XBND(ALL_REG,T,C,S,IE,'UP') NE INF)"),
        ]

        for arg in batincludes:
            self.include(
                EqxbndMod(
                    tc=self.tc, env=self.env, arg1=arg[0], arg2=arg[1], arg3=arg[2]
                )
            )

        # *GG* V07_2 Refinery blending
        # Blending constraint to a specification characteristic
        eqblnd_batincludes: list[tuple[str, str]] = [
            ("L", "1"),
            ("G", "2"),
            ("E", "3"),
            ("N", "4"),
        ]
        for arg1, arg2 in eqblnd_batincludes:
            self.include(EqblndMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2))

        # MACRO equations
        if self.env.macro == "YES":
            self.include(EqmacroTm(tc=self.tc, env=self.env))

        if self.tc.defined("DAM_COST"):
            self.include(EqdamageMod(tc=self.tc, env=self.env))

    def _m2t(self: EqmainMod) -> None:
        # fmt: off
        batincludes: list[tuple[str, str, str, str]] = [
            ("E", "E", "NOT PRC_MAP(R,'DMD',P)", f"{self.env.var}_CAP(R,T,P {self.env.sow})"),
            ("L", "L", "PRC_MAP(R,'DMD',P)", f"{self.env.var}_CAP(R,T,P {self.env.sow})"),
            ("G", "G", "NO", "0"),
        ]
        # fmt: on
        for arg1, arg2, arg3, arg4 in batincludes:
            self.include(
                EqcptMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                )
            )

    def _no_m2t(self: EqmainMod) -> None:
        self.tc.enqueue(self.assign_rtp_varp, etl=self.env.etl, macro=self.env.macro)
        # fmt: off
        batincludes: list[tuple[str, str, str, str]] = [
            ("E", "E", "RTP_VARP(R,T,P) OR YES$CAP_BND(R,T,P,'FX')", f"{self.env.var}_CAP(R,T,P {self.env.sow})"),
            ("L", "L", "((NOT RTP_VARP(R,T,P))$CAP_BND(R,T,P,'LO'))", "CAP_BND(R,T,P,'LO')"),
            ("G", "G", "((NOT RTP_VARP(R,T,P))$CAP_BND(R,T,P,'UP'))", "CAP_BND(R,T,P,'UP')"),
        ]
        # fmt: on
        for arg1, arg2, arg3, arg4 in batincludes:
            self.include(
                EqcptMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=arg1,
                    arg2=arg2,
                    arg3=arg3,
                    arg4=arg4,
                )
            )

    def assign_rtp_varp(self: EqmainMod, etl: str, macro: str) -> None:
        if etl.upper() == "YES":
            self.tc.add_gams_code(
                module=self, phase="run", code="RTP_VARP(RTP(R,T,P))$TEG(P) = YES;"
            )
        if macro.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="RTP_VARP(RTP(R,T,P))$((TM_QFAC(R) NE 0)$TM_CAPTB(R,P)) = YES;",
            )

    def exec1(self: EqmainMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  LOOP(OBJ_2A(R,T,P)$(NOT RTP_OFF(R,T,P)),F=B(T)+NCAP_ILED(R,T,P); Z=SUM(VNT(T,TT)$(F>E(TT)+0.5),1);
    RVPT(R,T,P,T+Z) = YES);
  RTP_OFF(OBJ_2A(R,T,P))$(NOT SUM(RVPT(R,T,P,TT),1)) = YES;
""",
        )

    def add_sets(self: EqmainMod, ucbd: str, tmp: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 SET UC_RHSTMP(REG,UC_N,T,S{ucbd},UC_NUMBER);
 SET UC_RHSMAP(REG,T,UC_N,UC_NUMBER,S{ucbd});
 SET RUCTS(ALL_REG,UC_N,ALLYEAR,TS{tmp});
 SET UC_UT(UC_N,ALLYEAR{tmp}), UC_UTS(UC_N,ALLYEAR,TS{tmp});
 SET UC_TMAP(YEAR,YEAR,T,SIDE,UC_DYNT);
""",
        )

    def exec2(self: EqmainMod, ucbd: str, take: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
UC_TMAP(T,TT(T-DIAG(SIDE,'RHS')),TT,SIDE,'N') = YES;
 UC_TMAP(T,TT(T-DIAG(SIDE,'RHS')),MILESTONYR,SIDE,'CUMSUM')$(ORD(T) > ORD(MILESTONYR)+DIAG(SIDE,'RHS')) = YES;
 UC_TMAP(T,T,T,'RHS','SYNC') = YES;
 UC_TMAP(T,T,TT,'RHS','CUM+')$UC_TMAP(T,T,TT,'LHS','CUMSUM') = YES;
 IF(CARD(UC_RHSRT), OPTION R_UCT < UC_RHSRT, R_UC < UC_TS_SUM;
   UC_RHSTMP(R_UCT(R_UC(R,UC_N),T),ANNUAL{ucbd},'SEVERAL')$({take}UC_T_EACH(R,UC_N,T)) = YES;
   UC_RHSTMP(R_UCT(R_UC(R,UC_N),T),ANNUAL{ucbd},'DYNAMIC')$({take}UC_T_SUCC(R,UC_N,T)) = YES;
   OPTION CLEAR=R_UC,CLEAR=R_UCT;
 );
 IF(CARD(UC_RHSRTS), OPTION RUCTS < UC_RHSRTS;
   UC_RHSTMP(RUCTS(UC_T_EACH(UC_R_EACH(R,UC_N),T),S{ucbd}),'EACH')$UC_TS_EACH(R,UC_N,S) = YES;
   UC_RHSTMP(RUCTS(UC_T_SUCC(UC_R_EACH(R,UC_N),T),S{ucbd}),'SUCC')$UC_TS_EACH(R,UC_N,S) = YES;
   UC_RHSTMP(RUCTS(UC_T_EACH(UC_R_EACH(R,UC_N),T),S{ucbd}),UC_NUMBER(TSL))$(TS_GROUP(R,TSL,S)$UC_DS(R,UC_N,TSL)) = YES;
 );
 OPTION UC_RTSUC < UC_T_SUCC, UC_RHSMAP < UC_RHSTMP, UC_UT < UC_RHST, UC_UTS < UC_RHSTS, CLEAR=UC_RHSTMP, CLEAR=RUCTS;

""",
        )
