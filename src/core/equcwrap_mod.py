# equcwrap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQUCWRAP.MOD Wrapper for defining the actual UC equations
# *   %1 - equation type
# *   %2 - bound type (BD/FX/UP/LO)
# *   %3 - bound type2 (none/FX/UP/LO)
# *   %4 - SUM(BD$ or none
# *   %5 - ,1) or none
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, get_args

from core.equserco_mod import EqusercoMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

EqucwrapArg6Type = Literal["", "NOT"]


class EqucwrapMod(GamsClass):
    """Translation unit for equcwrap.mod."""

    module_name: str = "equcwrap_mod"
    gams_source: str = "equcwrap.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: EqucwrapArg6Type = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        # $IF %6 %VAR_UC%==YES $EXIT
        var_uc_is_yes = self.env.var_uc.strip().upper() == "YES"

        # Ensure arg6 is exactly what is implemented
        if self.arg6.strip().upper() not in get_args(EqucwrapArg6Type):
            raise ValueError(f"'{self.arg6}' not in {get_args(EqucwrapArg6Type)}.")

        is_inverted = self.arg6.strip().upper() == "NOT"

        # If it's "NOT" and var_uc is "NO" -> EXIT
        # If it's "" and var_uc is "YES" -> EXIT
        if is_inverted != var_uc_is_yes:
            return

        self.env.set_local("tsum", "UC_T_SUM(R,UC_N,T),")
        self.env.set_scoped("sw1", self.env.sow)

        if self.env.stages == "YES":
            self.env.set_local("sws", "(SW_UCT(UC_N,T,SOW)*")
            self.env.set_local("swd", ")")
            self.env.set_local("tst", self.env.tsum)
            self.env.set_local("tsum", f"({self.env.tsum}WW)${self.env.swsw}")
            self.env.set_local("swtd", "SW_TSW(SOW,TT,WW),")

        if self.env.scum == "1":
            self.env.set_scoped("sw1", ",'1'")
            self.env.set_local("sws", "(")
            self.env.set_local(
                "tsum", f"({self.env.tst}SOW(WW))$SW_T(T,WW),SW_TPROB(T,WW)*"
            )
            self.env.set_local("swtd", "SW_TSW(SOW(WW),TT,WW),SW_TPROB(TT,WW)*")

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"(UC_N{self.env.sow})$({self.arg4}UC_RHS(UC_N,{self.arg2}){self.arg5}$(SUM(UC_TS_SUM(UC_R_SUM(R,UC_N),S),1)$SUM(UC_T_SUM(R,UC_N,T),1)))",
                arg4="SUM(",
                arg5=f"SUM({self.env.tsum}",
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="UC_R_SUM(R,UC_N),",
                arg8="2",
                arg9=f"{self.env.var}_UC(UC_N{self.env.sw1})",
                arg10=f"UC_RHS(UC_N,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"R(UC_R_EACH(R,UC_N){self.env.sow})$({self.arg4}UC_RHSR(R,UC_N,{self.arg2}){self.arg5}$(SUM(UC_TS_SUM(R,UC_N,S),1)$SUM(UC_T_SUM(R,UC_N,T),1)))",
                arg4="(",
                arg5=f"SUM({self.env.tsum}",
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="",
                arg8="2",
                arg9=f"{self.env.var}_UCR(UC_N,R{self.env.sw1})",
                arg10=f"UC_RHSR(R,UC_N,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"T(UC_N,T{self.env.swt})$(SUM(UC_T_EACH(UC_R_SUM(R,UC_N),T)$SUM(UC_TS_SUM(R,UC_N,S),1),1)$UC_UT(UC_N,T{self.arg3}))",
                arg4="SUM(",
                arg5="(",
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="UC_R_SUM(R,UC_N),",
                arg8="0",
                arg9=f"{self.env.var}_UCT(UC_N,T{self.env.sow})",
                arg10=f"UC_RHST(UC_N,T,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"RT({self.env.r_t},UC_N{self.env.swt})$UC_RHSMAP(R,T,UC_N,'SEVERAL','ANNUAL'{self.arg3})",
                arg4="(",
                arg5="(",
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="",
                arg8="0",
                arg9=f"{self.env.var}_UCRT(UC_N,R,T{self.env.sow})",
                arg10=f"UC_RHSRT(R,UC_N,T,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"TS(UC_N,T,S{self.env.swt})$(SUM(UC_T_EACH(UC_R_SUM(R,UC_N),T)$UC_TS_EACH(R,UC_N,S),1)$UC_UTS(UC_N,T,S{self.arg3}))",
                arg4="SUM(",
                arg5="(",
                arg6="(",
                arg7="UC_R_SUM(R,UC_N),",
                arg8="0",
                arg9=f"{self.env.var}_UCTS(UC_N,T,S{self.env.sow})",
                arg10=f"UC_RHSTS(UC_N,T,S,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"RTS({self.env.r_t},UC_N,RTS(S){self.env.swt})$UC_RHSMAP(R,T,UC_N,'EACH',S{self.arg3})",
                arg4="(",
                arg5="(",
                arg6="(",
                arg7="",
                arg8="0",
                arg9=f"{self.env.var}_UCRTS(UC_N,R,T,S{self.env.sow})",
                arg10=f"UC_RHSRTS(R,UC_N,T,S,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"SU(UC_N,T{self.env.sow})$({self.env.sws}SUM(UC_T_SUCC(UC_R_SUM(R,UC_N),T)$SUM(UC_TS_SUM(R,UC_N,S),1),1)$UC_UT(UC_N,T{self.arg3})){self.env.swd}",
                arg4="SUM(",
                arg5=self.env.swtd,
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="UC_R_SUM(R,UC_N),",
                arg8="1",
                arg9=f"{self.env.var}_UCT(UC_N,T{self.env.sw1})",
                arg10=f"UC_RHST(UC_N,T,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"RSU(UC_RTSUC(R,T,UC_N){self.env.sow})${self.env.sws}UC_RHSMAP(R,T,UC_N,'DYNAMIC','ANNUAL'{self.arg3}){self.env.swd}",
                arg4="(",
                arg5=self.env.swtd,
                arg6="SUM(UC_TS_SUM(R,UC_N,S),",
                arg7="",
                arg8="1",
                arg9=f"{self.env.var}_UCRT(UC_N,R,T{self.env.sw1})",
                arg10=f"UC_RHSRT(R,UC_N,T,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"RSUS(UC_RTSUC(R,T,UC_N),RTS(S){self.env.sow})${self.env.sws}UC_RHSMAP(R,T,UC_N,'SUCC',S{self.arg3}){self.env.swd}",
                arg4="(",
                arg5=self.env.swtd,
                arg6="(",
                arg7="",
                arg8="1",
                arg9=f"{self.env.var}_UCRTS(UC_N,R,T,S{self.env.sw1})",
                arg10=f"UC_RHSRTS(R,UC_N,T,S,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"SUS(UC_N,T,S{self.env.sow})$({self.env.sws}SUM(UC_T_SUCC(UC_R_SUM(R,UC_N),T)$UC_TS_EACH(R,UC_N,S),1)$UC_UTS(UC_N,T,S{self.arg3})){self.env.swd}",
                arg4="SUM(",
                arg5=self.env.swtd,
                arg6="(",
                arg7="UC_R_SUM(R,UC_N),",
                arg8="1",
                arg9=f"{self.env.var}_UCTS(UC_N,T,S{self.env.sw1})",
                arg10=f"UC_RHSTS(UC_N,T,S,{self.arg2})",
            )
        )

        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                arg1="mod",
                arg2=self.arg1,
                arg3=f"RS({self.env.r_t},UC_N,TSL(UC_NUMBER),RTS(SL){self.env.swt})$(UC_RHSMAP(R,T,UC_N,UC_NUMBER,SL{self.arg3})$UC_DS(R,UC_N,TSL))",
                arg4="(",
                arg5="SUM((UC_TSL(R,UC_N,SIDE,TSL),G_UDS(SL,SIDE,S))$(RHS(SIDE)->RS_PREV(R,SL,S)),UC_SIGN(SIDE)*",
                arg6="(",
                arg7="",
                arg8="S",
                arg9=f"{self.env.var}_UCRTS(UC_N,R,T,SL{self.env.sow})",
                arg10=f"UC_RHSRTS(R,UC_N,T,SL,{self.arg2})",
            )
        )
