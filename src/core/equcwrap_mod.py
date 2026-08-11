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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, get_args

from gamspy import Alias, Domain, Sum
from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

from core.base_class import GamsClass
from core.equserco_mod import DualArgs, EqusercoMod, EqusercoModConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Set
    from gamspy._algebra.condition import Condition

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

EqucwrapArg6Type = Literal["", "NOT"]


@dataclass
class EqucwrapModConfig:
    arg1: Literal["E", "G", "L"]
    arg2: Literal["FX", "LO", "UP"] | Set | Alias  # BD
    arg3: tuple[Literal["FX", "LO", "UP"]] | tuple[()]
    arg4: Set | Alias | None = None
    arg5: Literal[1] | None = None
    arg6: Literal["NOT", ""] = ""
    legacy_support: tuple = ()  # type: ignore  # TODO: This should be removed


class EqucwrapMod(GamsClass):
    """Translation unit for equcwrap.mod."""

    module_name: str = "equcwrap_mod"
    gams_source: str = "equcwrap.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqucwrapModConfig,
    ):
        self.env = env.fork()
        self.tc = tc
        ls = config.legacy_support

        self.arg1: str = ls[0]
        self.arg2: str = ls[1]
        self.arg3: str = ls[2]
        self.arg4: str = ls[3]
        self.arg5: str = ls[4]
        self.arg6: str = ls[5]
        # TODO: Refactor this once legacy code is removed
        self.arg1_GP = config.arg1
        self.arg2_GP = config.arg2
        self.arg3_GP = config.arg3
        self.arg4_GP = config.arg4
        self.arg5_GP = config.arg5
        self.arg6_GP = config.arg6

        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc

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

        # NOTE: tsum is used only in this file and it gets passed on the equserco_mod.py
        # ATM, it is safe to use a python variable instead of setting tsum
        # It is difficult to set a complicated tsum via the set_local method
        self.env.set_local("tsum", "UC_T_SUM(R,UC_N,T),")
        tsum_GP: Condition | ImplicitSet | tuple[Condition, ImplicitParameter] = (
            g.UcTSum[g.r, g.ucn, g.t]
        )
        self.env.set_scoped("sw1", self.env.sow)
        self.env.set_scoped("sw1_GP", self.env.sow_GP)

        if self.env.stages == "YES":
            self.env.set_local("sws", "(SW_UCT(UC_N,T,SOW)*")
            self.env.set_local("sws_GP", (g.SwUct[g.ucn, g.t, g.Sow],))
            self.env.set_local("swd", ")")
            self.env.set_local("swd_GP", ())
            self.env.set_local("tst", self.env.tsum)
            self.env.set_local("tsum", f"({self.env.tsum}WW)${self.env.swsw}")

            implicit_set = next(iter(self.env.swsw_GP))
            base_tsum = cast(ImplicitSet, tsum_GP)

            tsum_GP = Domain(base_tsum, g.ww).where[implicit_set]
            self.env.set_local("swtd", "SW_TSW(SOW,TT,WW),")
            self.env.set_local("swtd_GP", (g.SwTsw[g.Sow, g.tt, g.ww],))

        if self.env.scum == "1":
            self.env.set_scoped("sw1", ",'1'")
            self.env.set_scoped("sw1_GP", (1,))
            self.env.set_local("sws", "(")
            self.env.set_local(
                "tsum", f"({self.env.tst}SOW(WW))$SW_T(T,WW),SW_TPROB(T,WW)*"
            )
            tsum_GP = (
                Domain(*self.env.tst_GP, g.Sow[g.ww]).where[g.SwT[g.t, g.ww]],
                g.sw_tprob[g.t, g.ww],
            )  # NOTE: We Multiple in the parent file

            self.env.set_local("swtd", "SW_TSW(SOW(WW),TT,WW),SW_TPROB(TT,WW)*")
            self.env.set_local(
                "swtd_GP", (g.SwTsw[g.Sow[g.ww], g.tt, g.ww], g.sw_tprob[g.tt, g.ww])
            )  # TODO: Move "*" to main code

        set_uc_ts_sum = g.UcTsSum[g.r, g.ucn, g.s]
        set_uc_r_sum = g.UcRSum[g.r, g.ucn]

        condition1: Condition | bool = True
        condition2: Condition | bool = True
        if self.arg4_GP is not None and self.arg5_GP is not None:
            condition1 = Sum(  # type: ignore[assignment]
                self.arg4_GP.where[g.uc_rhs[g.ucn, self.arg2_GP]], self.arg5_GP
            ).where[
                (
                    Sum(g.UcTsSum[set_uc_r_sum, g.s], 1.0).where[
                        Sum(g.UcTSum[g.r, g.ucn, g.t], 1.0)
                    ]
                )
            ]
            condition2 = Sum(  # type: ignore[assignment]
                self.arg4_GP.where[g.uc_rhsr[g.r, g.ucn, self.arg2_GP]],
                self.arg5_GP,
            ).where[
                (Sum(set_uc_ts_sum, 1.0).where[Sum(g.UcTSum[g.r, g.ucn, g.t], 1.0)])
            ]
        else:
            raise ValueError(
                f"arg4 and arg5 must both be not None. They are {self.arg4_GP=} and {self.arg5_GP=}"
            )
        arg9 = g.get_variable(name=f"{self.env.var}_UC")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"(UC_N{self.env.sow})$({self.arg4}UC_RHS(UC_N,{self.arg2}){self.arg5}$(SUM(UC_TS_SUM(UC_R_SUM(R,UC_N),S),1)$SUM(UC_T_SUM(R,UC_N,T),1)))",
                        gp={
                            "cond": condition1,
                            "eq": "",
                            "dom": Domain(g.ucn, *self.env.sow_GP),
                        },
                    ),
                    arg4=DualArgs(s="SUM(", gp=None),
                    arg5=DualArgs(s=f"SUM({self.env.tsum}", gp=tsum_GP),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="UC_R_SUM(R,UC_N),", gp=set_uc_r_sum),
                    arg8=DualArgs(s="2", gp=2),
                    arg9=arg9[g.ucn, *self.env.sw1_GP],
                    arg10=g.uc_rhs[g.ucn, self.arg2_GP],
                ),
            )
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCR")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"R(UC_R_EACH(R,UC_N){self.env.sow})$({self.arg4}UC_RHSR(R,UC_N,{self.arg2}){self.arg5}$(SUM(UC_TS_SUM(R,UC_N,S),1)$SUM(UC_T_SUM(R,UC_N,T),1)))",
                        gp={
                            "cond": condition2,
                            "dom": Domain(g.UcREach[g.r, g.ucn], *self.env.sow_GP),
                            "eq": "R",
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(s=f"SUM({self.env.tsum}", gp=tsum_GP),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="2", gp=2),
                    arg9=arg9[g.ucn, g.r, *self.env.sw1_GP],
                    arg10=g.uc_rhsr[g.r, g.ucn, self.arg2_GP],
                ),
            ),
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCT")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"T(UC_N,T{self.env.swt})$(SUM(UC_T_EACH(UC_R_SUM(R,UC_N),T)$SUM(UC_TS_SUM(R,UC_N,S),1),1)$UC_UT(UC_N,T{self.arg3}))",
                        gp={
                            "cond": Sum(
                                g.UcTEach[set_uc_r_sum, g.t].where[
                                    Sum(set_uc_ts_sum, 1.0)
                                ],
                                1.0,
                            ).where[g.UcUt[g.ucn, g.t, *self.arg3_GP]],
                            "dom": Domain(g.ucn, g.t, *self.env.swt_GP),
                            "eq": "T",
                        },
                    ),
                    arg4=DualArgs(s="SUM(", gp=True),
                    arg5=DualArgs(s="(", gp=None),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="UC_R_SUM(R,UC_N),", gp=set_uc_r_sum),
                    arg8=DualArgs(s="0", gp=0),
                    arg9=arg9[g.ucn, g.t, *self.env.sow_GP],
                    arg10=g.uc_rhst[g.ucn, g.t, self.arg2_GP],
                ),
            ),
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCRT")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"RT({self.env.r_t},UC_N{self.env.swt})$UC_RHSMAP(R,T,UC_N,'SEVERAL','ANNUAL'{self.arg3})",
                        gp={
                            "cond": g.UcRhsmap[
                                g.r, g.t, g.ucn, "SEVERAL", "ANNUAL", *self.arg3_GP
                            ],
                            "dom": Domain(*self.env.r_t_GP, g.ucn, *self.env.swt_GP),
                            "eq": "RT",
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(s="(", gp=None),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="0", gp=0),
                    arg9=arg9[g.ucn, g.r, g.t, *self.env.sow_GP],
                    arg10=g.uc_rhsrt[g.r, g.ucn, g.t, self.arg2_GP],
                ),
            ),
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCTS")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"TS(UC_N,T,S{self.env.swt})$(SUM(UC_T_EACH(UC_R_SUM(R,UC_N),T)$UC_TS_EACH(R,UC_N,S),1)$UC_UTS(UC_N,T,S{self.arg3}))",
                        gp={
                            "cond": Sum(
                                g.UcTEach[set_uc_r_sum, g.t].where[
                                    g.UcTsEach[g.r, g.ucn, g.s]
                                ],
                                1.0,
                            ).where[g.UcUts[g.ucn, g.t, g.s, *self.arg3_GP]],
                            "eq": "TS",
                            "dom": Domain(g.ucn, g.t, g.s, *self.env.swt_GP),
                        },
                    ),
                    arg4=DualArgs(s="SUM(", gp=True),
                    arg5=DualArgs(s="(", gp=None),
                    arg6=DualArgs(s="(", gp=None),
                    arg7=DualArgs(s="UC_R_SUM(R,UC_N),", gp=set_uc_r_sum),
                    arg8=DualArgs(s="0", gp=0),
                    arg9=arg9[g.ucn, g.t, g.s, *self.env.sow_GP],
                    arg10=g.uc_rhsts[g.ucn, g.t, g.s, self.arg2_GP],
                ),
            ),
        )

        rts = macro.rts(s="S", g=self.tc, env=self.env)
        rts_GP = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        arg9 = g.get_variable(name=f"{self.env.var}_UCRTS")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"RTS({self.env.r_t},UC_N,{rts}{self.env.swt})$UC_RHSMAP(R,T,UC_N,'EACH',S{self.arg3})",
                        gp={
                            "eq": "RTS",
                            "dom": Domain(
                                *self.env.r_t_GP, g.ucn, rts_GP, *self.env.swt_GP
                            ),
                            "cond": g.UcRhsmap[
                                g.r, g.t, g.ucn, "EACH", g.s, *self.arg3_GP
                            ],
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(s="(", gp=None),
                    arg6=DualArgs(s="(", gp=None),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="0", gp=0),
                    arg9=arg9[g.ucn, g.r, g.t, g.s, *self.env.sow_GP],
                    arg10=g.uc_rhsrts[g.r, g.ucn, g.t, g.s, self.arg2_GP],
                ),
            ),
        )
        sws_GP: int | ImplicitSet
        if self.env.sws_GP == ():
            sws_GP = 1
        elif len(self.env.sws_GP) > 0 and isinstance(self.env.sws_GP[0], ImplicitSet):
            sws_GP = next(iter(self.env.sws_GP))
        else:
            raise ValueError(f"Unexpected data in sws_GP {self.env.sws_GP}")

        swd_GP: int | Alias
        if self.env.swd_GP == ():
            swd_GP = 1
        elif len(self.env.swd_GP) > 0 and isinstance(self.env.swd_GP[0], Alias):
            swd_GP = next(iter(self.env.swd_GP))
        else:
            raise ValueError(f"Unexpected data in swd_GP {self.env.swd_GP}")

        arg9 = g.get_variable(name=f"{self.env.var}_UCT")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"SU(UC_N,T{self.env.sow})$({self.env.sws}SUM(UC_T_SUCC(UC_R_SUM(R,UC_N),T)$SUM(UC_TS_SUM(R,UC_N,S),1),1)$UC_UT(UC_N,T{self.arg3})){self.env.swd}",
                        gp={
                            "eq": "SU",
                            "dom": Domain(g.ucn, g.t, *self.env.sow_GP),
                            "cond": sws_GP
                            * Sum(
                                g.UcTSucc[set_uc_r_sum, g.t].where[
                                    Sum(set_uc_ts_sum, 1.0)
                                ],
                                1.0,
                            ).where[g.UcUt[g.ucn, g.t, *self.arg3_GP]]
                            * swd_GP,
                        },
                    ),
                    arg4=DualArgs(s="SUM(", gp=True),
                    arg5=DualArgs(s=self.env.swtd, gp=self.env.swtd_GP),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="UC_R_SUM(R,UC_N),", gp=set_uc_r_sum),
                    arg8=DualArgs(s="1", gp=1),
                    arg9=arg9[g.ucn, g.t, *self.env.sw1_GP],
                    arg10=g.uc_rhst[g.ucn, g.t, self.arg2_GP],
                ),
            ),
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCRT")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"RSU(UC_RTSUC(R,T,UC_N){self.env.sow})${self.env.sws}UC_RHSMAP(R,T,UC_N,'DYNAMIC','ANNUAL'{self.arg3}){self.env.swd}",
                        gp={
                            "eq": "RSU",
                            "dom": Domain(g.UcRtsuc[g.r, g.t, g.ucn], *self.env.sow_GP),
                            "cond": sws_GP
                            * g.UcRhsmap[
                                g.r, g.t, g.ucn, "DYNAMIC", "ANNUAL", *self.arg3_GP
                            ]
                            * swd_GP,
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(s=self.env.swtd, gp=self.env.swtd_GP),
                    arg6=DualArgs(s="SUM(UC_TS_SUM(R,UC_N,S),", gp=set_uc_ts_sum),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="1", gp=1),
                    arg9=arg9[g.ucn, g.r, g.t, *self.env.sw1_GP],
                    arg10=g.uc_rhsrt[g.r, g.ucn, g.t, self.arg2_GP],
                ),
            ),
        )
        rts = macro.rts(s="S", g=self.tc, env=self.env)
        rts_GP = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        arg9 = g.get_variable(name=f"{self.env.var}_UCRTS")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"RSUS(UC_RTSUC(R,T,UC_N),{rts}{self.env.sow})${self.env.sws}UC_RHSMAP(R,T,UC_N,'SUCC',S{self.arg3}){self.env.swd}",
                        gp={
                            "eq": "RSUS",
                            "dom": Domain(
                                g.UcRtsuc[g.r, g.t, g.ucn], rts_GP, *self.env.sow_GP
                            ),
                            "cond": sws_GP
                            * g.UcRhsmap[g.r, g.t, g.ucn, "SUCC", g.s, *self.arg3_GP]
                            * swd_GP,
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(s=self.env.swtd, gp=self.env.swtd_GP),
                    arg6=DualArgs(s="(", gp=None),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="1", gp=1),
                    arg9=arg9[g.ucn, g.r, g.t, g.s, *self.env.sw1_GP],
                    arg10=g.uc_rhsrts[g.r, g.ucn, g.t, g.s, self.arg2_GP],
                ),
            ),
        )

        arg9 = g.get_variable(name=f"{self.env.var}_UCTS")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"SUS(UC_N,T,S{self.env.sow})$({self.env.sws}SUM(UC_T_SUCC(UC_R_SUM(R,UC_N),T)$UC_TS_EACH(R,UC_N,S),1)$UC_UTS(UC_N,T,S{self.arg3})){self.env.swd}",
                        gp={
                            "cond": Sum(
                                g.UcTSucc[set_uc_r_sum, g.t].where[
                                    g.UcTsEach[g.r, g.ucn, g.s]
                                ],
                                1.0,
                            ).where[g.UcUts[g.ucn, g.t, g.s, *self.arg3_GP]],
                            "eq": "SUS",
                            "dom": Domain(g.ucn, g.t, g.s, *self.env.sow_GP),
                        },
                    ),
                    arg4=DualArgs(s="SUM(", gp=True),
                    arg5=DualArgs(s=self.env.swtd, gp=self.env.swtd_GP),
                    arg6=DualArgs(s="(", gp=None),
                    arg7=DualArgs(s="UC_R_SUM(R,UC_N),", gp=set_uc_r_sum),
                    arg8=DualArgs(s="1", gp=1),
                    arg9=arg9[g.ucn, g.t, g.s, *self.env.sw1_GP],
                    arg10=g.uc_rhsts[g.ucn, g.t, g.s, self.arg2_GP],
                ),
            ),
        )

        rts = macro.rts(s="SL", g=self.tc, env=self.env)
        rts_GP = macro.rts_GP(s=g.sl, g=self.tc, env=self.env)
        arg9 = g.get_variable(name=f"{self.env.var}_UCRTS")
        self.include(
            EqusercoMod(
                self.tc,
                self.env,
                EqusercoModConfig(
                    arg2=self.arg1_GP,
                    arg3=DualArgs(
                        s=f"RS({self.env.r_t},UC_N,TSL(UC_NUMBER),{rts}{self.env.swt})$(UC_RHSMAP(R,T,UC_N,UC_NUMBER,SL{self.arg3})$UC_DS(R,UC_N,TSL))",
                        gp={
                            "cond": g.UcRhsmap[
                                g.r, g.t, g.ucn, g.ucnumber, g.sl, *self.arg3_GP
                            ].where[g.UcDs[g.r, g.ucn, g.tsl]],
                            "eq": "RS",
                            "dom": Domain(
                                *self.env.r_t_GP,
                                g.ucn,
                                g.tsl[g.ucnumber],
                                rts_GP,
                                *self.env.swt_GP,
                            ),
                        },
                    ),
                    arg4=DualArgs(s="(", gp=None),
                    arg5=DualArgs(
                        s="SUM((UC_TSL(R,UC_N,SIDE,TSL),G_UDS(SL,SIDE,S))$(RHS(SIDE)->RS_PREV(R,SL,S)),UC_SIGN(SIDE)*",
                        gp=(
                            Domain(
                                g.UcTsl[g.r, g.ucn, g.side, g.tsl],
                                g.GUds[g.sl, g.side, g.s],
                            ).where[((~(g.Rhs[g.side])) | (g.RsPrev[g.r, g.sl, g.s]))],
                            g.uc_sign[g.side],
                        ),  # NOTE: Sum over the domain and UC_SIGN gets multiplied by something in the parent file
                    ),
                    arg6=DualArgs(s="(", gp=None),
                    arg7=DualArgs(s="", gp=None),
                    arg8=DualArgs(s="S", gp="S"),
                    arg9=arg9[g.ucn, g.r, g.t, g.sl, *self.env.sow_GP],
                    arg10=g.uc_rhsrts[g.r, g.ucn, g.t, g.sl, self.arg2_GP],
                ),
            ),
        )
