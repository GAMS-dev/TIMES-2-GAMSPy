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
from typing import TYPE_CHECKING, Literal, get_args

from gamspy import Alias, Domain, Sum, Variable
from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

from core.base_class import GamsClass
from core.equserco_mod import EqusercoMod, EqusercoModConfig
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
        self.config = config

        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        # $IF %6 %VAR_UC%==YES $EXIT
        var_uc_is_yes = self.env.var_uc.strip().upper() == "YES"

        # Ensure arg6 is exactly what is implemented
        if cc.arg6.strip().upper() not in get_args(EqucwrapArg6Type):
            raise ValueError(f"'{cc.arg6}' not in {get_args(EqucwrapArg6Type)}.")

        is_inverted = cc.arg6.strip().upper() == "NOT"

        # If it's "NOT" and var_uc is "NO" -> EXIT
        # If it's "" and var_uc is "YES" -> EXIT
        if is_inverted != var_uc_is_yes:
            return

        # NOTE: We keep this local variable for now, since it trickls down to another file and is required by legacy code.
        # Could be removed at a later stage.
        self.env.set_local("tsum", "UC_T_SUM(R,UC_N,T),")
        uc_t_sum = g.UcTSum[g.r, g.ucn, g.t]
        tsum: Condition | ImplicitSet | tuple[Condition, ImplicitParameter] = uc_t_sum
        self.env.set_scoped("sw1", self.env.sow)
        self.env.set_scoped("sw1_GP", self.env.sow_GP)

        if self.env.stages == "YES":
            self.env.set_local("sws", "(SW_UCT(UC_N,T,SOW)*")
            self.env.set_local("sws_GP", (g.SwUct[g.ucn, g.t, g.Sow],))
            self.env.set_local("swd", ")")
            self.env.set_local("swd_GP", ())
            self.env.set_scoped(
                "tst", self.env.tsum
            )  # %TST% of the SCUM==1 branch below refers to whatever %TSUM% meant
            self.env.set_scoped("tst_GP", (tsum,))

            self.env.set_local("tsum", f"({self.env.tsum}WW)${self.env.swsw}")
            match self.env.swsw_GP:
                case (condition, imp_param):
                    tsum = (Domain(uc_t_sum, g.ww).where[condition], imp_param)
                case (condition,):
                    tsum = Domain(uc_t_sum, g.ww).where[condition]
                case _:
                    raise ValueError(f"Unexpected data in swsw_GP {self.env.swsw_GP}")

            self.env.set_local("swtd", "SW_TSW(SOW,TT,WW),")
            self.env.set_local("swtd_GP", (g.SwTsw[g.Sow, g.tt, g.ww],))

        if self.env.scum == "1":
            self.env.set_scoped("sw1", ",'1'")
            self.env.set_scoped("sw1_GP", (1,))
            self.env.set_local("sws", "(")
            self.env.set_local("sws_GP", ())
            self.env.set_local(
                "tsum", f"({self.env.tst}SOW(WW))$SW_T(T,WW),SW_TPROB(T,WW)*"
            )
            tsum = (
                Domain(*self.env.tst_GP, g.Sow[g.ww]).where[g.SwT[g.t, g.ww]],
                g.sw_tprob[g.t, g.ww],
            )  # NOTE: We Multiple in the parent file

            self.env.set_local("swtd", "SW_TSW(SOW(WW),TT,WW),SW_TPROB(TT,WW)*")
            self.env.set_local(
                "swtd_GP", (g.SwTsw[g.Sow[g.ww], g.tt, g.ww], g.sw_tprob[g.tt, g.ww])
            )  # TODO: Move "*" to main code

        set_uc_ts_sum = g.UcTsSum[g.r, g.ucn, g.s]
        set_uc_r_sum = g.UcRSum[g.r, g.ucn]

        def get_var(suffix: str) -> Variable:
            return g.get_variable(name=f"{self.env.var}_{suffix}")

        var_uc = get_var("UC")
        var_ucr = get_var("UCR")
        var_uct = get_var("UCT")
        var_ucrt = get_var("UCRT")
        var_ucts = get_var("UCTS")
        var_ucrts = get_var("UCRTS")

        condition1: Condition | bool = True
        condition2: Condition | bool = True
        innermost_sum = Sum(g.UcTSum[g.r, g.ucn, g.t], 1.0)
        expr1 = Sum(g.UcTsSum[set_uc_r_sum, g.s], 1.0).where[innermost_sum]
        expr2 = Sum(set_uc_ts_sum, 1.0).where[innermost_sum]
        if cc.arg4 is not None and cc.arg5 is not None:
            condition1 = Sum(cc.arg4.where[g.uc_rhs[g.ucn, cc.arg2]], cc.arg5).where[
                expr1
            ]
            condition2 = Sum(
                cc.arg4.where[g.uc_rhsr[g.r, g.ucn, cc.arg2]], cc.arg5
            ).where[expr2]
        elif cc.arg4 is None and cc.arg5 is None:
            condition1 = g.uc_rhs[g.ucn, cc.arg2].where[expr1]
            condition2 = g.uc_rhsr[g.r, g.ucn, cc.arg2].where[expr2]
        else:
            raise ValueError(
                f"arg4 and arg5 must either both be None or both be not None. "
                f"They are {cc.arg4=} and {cc.arg5=}"
            )

        rts_GP = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        rts_GP_sl = macro.rts_GP(s=g.sl, g=self.tc, env=self.env)
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

        equsercomod_config: list[EqusercoModConfig] = [
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": condition1,
                    "eq": "",
                    "dom": Domain(g.ucn, *self.env.sow_GP),
                },
                arg3={"legacy": f"SUM({self.env.tsum}", "gp": tsum},
                arg4=set_uc_ts_sum,
                arg5=set_uc_r_sum,
                arg6=2,
                arg7=var_uc[g.ucn, *self.env.sw1_GP],
                arg8=g.uc_rhs[g.ucn, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": condition2,
                    "dom": Domain(g.UcREach[g.r, g.ucn], *self.env.sow_GP),
                    "eq": "R",
                },
                arg3={"legacy": f"SUM({self.env.tsum}", "gp": tsum},
                arg4=set_uc_ts_sum,
                arg5=None,
                arg6=2,
                arg7=var_ucr[g.ucn, g.r, *self.env.sw1_GP],
                arg8=g.uc_rhsr[g.r, g.ucn, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": Sum(
                        g.UcTEach[set_uc_r_sum, g.t].where[Sum(set_uc_ts_sum, 1.0)],
                        1.0,
                    ).where[g.UcUt[g.ucn, g.t, *cc.arg3]],
                    "dom": Domain(g.ucn, g.t, *self.env.swt_GP),
                    "eq": "T",
                },
                arg3={"legacy": "(", "gp": None},
                arg4=set_uc_ts_sum,
                arg5=set_uc_r_sum,
                arg6=0,
                arg7=var_uct[g.ucn, g.t, *self.env.sow_GP],
                arg8=g.uc_rhst[g.ucn, g.t, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": g.UcRhsmap[g.r, g.t, g.ucn, "SEVERAL", "ANNUAL", *cc.arg3],
                    "dom": Domain(*self.env.r_t_GP, g.ucn, *self.env.swt_GP),
                    "eq": "RT",
                },
                arg3={"legacy": "(", "gp": None},
                arg4=set_uc_ts_sum,
                arg5=None,
                arg6=0,
                arg7=var_ucrt[g.ucn, g.r, g.t, *self.env.sow_GP],
                arg8=g.uc_rhsrt[g.r, g.ucn, g.t, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": Sum(
                        g.UcTEach[set_uc_r_sum, g.t].where[g.UcTsEach[g.r, g.ucn, g.s]],
                        1.0,
                    ).where[g.UcUts[g.ucn, g.t, g.s, *cc.arg3]],
                    "eq": "TS",
                    "dom": Domain(g.ucn, g.t, g.s, *self.env.swt_GP),
                },
                arg3={"legacy": "(", "gp": None},
                arg4=None,
                arg5=set_uc_r_sum,
                arg6=0,
                arg7=var_ucts[g.ucn, g.t, g.s, *self.env.sow_GP],
                arg8=g.uc_rhsts[g.ucn, g.t, g.s, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "eq": "RTS",
                    "dom": Domain(*self.env.r_t_GP, g.ucn, rts_GP, *self.env.swt_GP),
                    "cond": g.UcRhsmap[g.r, g.t, g.ucn, "EACH", g.s, *cc.arg3],
                },
                arg3={"legacy": "(", "gp": None},
                arg4=None,
                arg5=None,
                arg6=0,
                arg7=var_ucrts[g.ucn, g.r, g.t, g.s, *self.env.sow_GP],
                arg8=g.uc_rhsrts[g.r, g.ucn, g.t, g.s, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "eq": "SU",
                    "dom": Domain(g.ucn, g.t, *self.env.sow_GP),
                    "cond": sws_GP
                    * Sum(
                        g.UcTSucc[set_uc_r_sum, g.t].where[Sum(set_uc_ts_sum, 1.0)],
                        1.0,
                    ).where[g.UcUt[g.ucn, g.t, *cc.arg3]]
                    * swd_GP,
                },
                arg3={"legacy": self.env.swtd, "gp": self.env.swtd_GP},
                arg4=set_uc_ts_sum,
                arg5=set_uc_r_sum,
                arg6=1,
                arg7=var_uct[g.ucn, g.t, *self.env.sw1_GP],
                arg8=g.uc_rhst[g.ucn, g.t, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "eq": "RSU",
                    "dom": Domain(g.UcRtsuc[g.r, g.t, g.ucn], *self.env.sow_GP),
                    "cond": sws_GP
                    * g.UcRhsmap[g.r, g.t, g.ucn, "DYNAMIC", "ANNUAL", *cc.arg3]
                    * swd_GP,
                },
                arg3={"legacy": self.env.swtd, "gp": self.env.swtd_GP},
                arg4=set_uc_ts_sum,
                arg5=None,
                arg6=1,
                arg7=var_ucrt[g.ucn, g.r, g.t, *self.env.sw1_GP],
                arg8=g.uc_rhsrt[g.r, g.ucn, g.t, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "eq": "RSUS",
                    "dom": Domain(g.UcRtsuc[g.r, g.t, g.ucn], rts_GP, *self.env.sow_GP),
                    "cond": sws_GP
                    * g.UcRhsmap[g.r, g.t, g.ucn, "SUCC", g.s, *cc.arg3]
                    * swd_GP,
                },
                arg3={"legacy": self.env.swtd, "gp": self.env.swtd_GP},
                arg4=None,
                arg5=None,
                arg6=1,
                arg7=var_ucrts[g.ucn, g.r, g.t, g.s, *self.env.sw1_GP],
                arg8=g.uc_rhsrts[g.r, g.ucn, g.t, g.s, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": Sum(
                        g.UcTSucc[set_uc_r_sum, g.t].where[g.UcTsEach[g.r, g.ucn, g.s]],
                        1.0,
                    ).where[g.UcUts[g.ucn, g.t, g.s, *cc.arg3]],
                    "eq": "SUS",
                    "dom": Domain(g.ucn, g.t, g.s, *self.env.sow_GP),
                },
                arg3={"legacy": self.env.swtd, "gp": self.env.swtd_GP},
                arg4=None,
                arg5=set_uc_r_sum,
                arg6=1,
                arg7=var_ucts[g.ucn, g.t, g.s, *self.env.sw1_GP],
                arg8=g.uc_rhsts[g.ucn, g.t, g.s, cc.arg2],
            ),
            EqusercoModConfig(
                arg1=cc.arg1,
                arg2={
                    "cond": g.UcRhsmap[
                        g.r, g.t, g.ucn, g.ucnumber, g.sl, *cc.arg3
                    ].where[g.UcDs[g.r, g.ucn, g.tsl]],
                    "eq": "RS",
                    "dom": Domain(
                        *self.env.r_t_GP,
                        g.ucn,
                        g.tsl[g.ucnumber],
                        rts_GP_sl,
                        *self.env.swt_GP,
                    ),
                },
                arg3={
                    "legacy": "SUM((UC_TSL(R,UC_N,SIDE,TSL),G_UDS(SL,SIDE,S))$(RHS(SIDE)->RS_PREV(R,SL,S)),UC_SIGN(SIDE)*",
                    "gp": (
                        Domain(
                            g.UcTsl[g.r, g.ucn, g.side, g.tsl],
                            g.GUds[g.sl, g.side, g.s],
                        ).where[((~(g.Rhs[g.side])) | (g.RsPrev[g.r, g.sl, g.s]))],
                        g.uc_sign[g.side],
                    ),  # NOTE: Sum over the domain and UC_SIGN gets multiplied by something in the parent file
                },
                arg4=None,
                arg5=None,
                arg6="S",
                arg7=var_ucrts[g.ucn, g.r, g.t, g.sl, *self.env.sow_GP],
                arg8=g.uc_rhsrts[g.r, g.ucn, g.t, g.sl, cc.arg2],
            ),
        ]

        for equser_config in equsercomod_config:
            self.include(EqusercoMod(self.tc, self.env, config=equser_config))
