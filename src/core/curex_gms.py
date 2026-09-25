# curex_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CUREX.GMS oversees the currency conversions
# *   arg1 - name of cost attribute
# *   arg2 - name of temp attribute (set to arg1 if no temp used)
# *   arg3 - indexes before CUR
# *   arg4 - constant indexes before CUR (optional, for temp attribute)
# *   arg5 - indexes after CUR
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from gamspy import Alias, Domain, Else, If, Loop, Number, Parameter, Set, Sum, sparse
from gamspy.math import power, same_as

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CurexGmsConfig:
    arg1: str = ""
    arg2: str = ""
    arg3: tuple[Set | Alias, ...] | tuple[()] = ()
    arg4: tuple[str] | tuple[()] = ()
    arg5: tuple[str | Set | Alias, ...] | tuple[()] = ()
    arg6: Number | None = None


class CurexGms(GamsClass):
    """Translation unit for curex.gms."""

    # Instance attributes
    module_name: str = "curex_gms"
    gams_source: str = "curex.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: CurexGmsConfig
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        cc = self.config

        r, ll, p, c, s, allr = g.r, g.ll, g.p, g.c, g.s, g.allr
        costagg, year, bd, ie, Com = g.costagg, g.year, g.bd, g.ie, g.Com
        tsl, upt = g.tsl, g.upt

        if self.env.intext_only == "YES":
            return  # $EXIT
        else:
            if cc.arg1 != "":  # SUBR
                if cc.arg6 is None:
                    self.env.set_scoped("mx", "1$YEARVAL(LL)")
                    self.env.set_scoped("mx_GP", Number(1).where[g.yearval[ll]])

                if not self.tc.declared(cc.arg2):
                    g.set_parameter(
                        name=cc.arg2,
                        parameter=Parameter(m, name=cc.arg2, domain=[*cc.arg3, g.cur]),
                    )

                self.tc.enqueue(
                    self.exec1,
                    condition=(cc.arg1.upper() == cc.arg2.upper()),
                    mx=self.env.mx_GP,
                )

            else:
                self.comp1()
                self.tc.register_assignment(g.r_curex)
                self.tc.enqueue(self.initialization)
                batincludes: list[CurexGmsConfig] = [
                    CurexGmsConfig("NCAP_COST", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_ITAX", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_ISUB", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_DCOST", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_DLAGC", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_FOM", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_FSUB", "RYPM", (r, ll, p)),
                    CurexGmsConfig("NCAP_FTAX", "RYPM", (r, ll, p)),
                    CurexGmsConfig("ACT_COST", "RYPM", (r, ll, p)),
                    CurexGmsConfig("FLO_COST", "RYPCSM", (r, ll, p, c, s)),
                    CurexGmsConfig("FLO_DELIV", "RYPCSM", (r, ll, p, c, s)),
                    CurexGmsConfig("FLO_TAX", "RYPCSM", (r, ll, p, c, s)),
                    CurexGmsConfig("FLO_SUB", "RYPCSM", (r, ll, p, c, s)),
                    CurexGmsConfig("NCAP_VALU", "RYPCSM", (r, ll, p, c), ("ANNUAL",)),
                    CurexGmsConfig("IRE_PRICE", "RYPCSRXM", (r, ll, p, c, s, allr, ie)),
                    CurexGmsConfig("COM_BPRICE", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_CSTNET", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_TAXNET", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_SUBNET", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_CSTPRD", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_TAXPRD", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig("COM_SUBPRD", "RYCSM", (r, ll, c, s)),
                    CurexGmsConfig(
                        "REG_BNDCST", "REG_BNDCST", (r, ll, costagg), (), (bd,)
                    ),
                    CurexGmsConfig(
                        "REG_CUMCST", "REG_CUMCST", (r, ll, year, costagg), (), (bd,)
                    ),
                    CurexGmsConfig(
                        "BL_VAROMC", "BL_VAROMC", (r, Com), (), (), Number(1)
                    ),
                    CurexGmsConfig(
                        "BL_DELIVC", "BL_DELIVC", (r, c, Com), (), (), Number(1)
                    ),
                    CurexGmsConfig("ACT_CSTUP", "ACT_CSTUP", (r, ll, p, tsl)),
                    CurexGmsConfig("ACT_CSTSD", "ACT_CSTSD", (r, ll, p, upt, bd)),
                    CurexGmsConfig("ACT_CSTRMP", "ACT_CSTRMP", (r, ll, p, bd)),
                    CurexGmsConfig("ACT_CSTPL", "RYPM", (r, ll, p)),
                ]
                for config in batincludes:
                    self.include(CurexGms(self.tc, self.env, config))

                if self.tc.defined("TL_CT_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            CurexGmsConfig(
                                arg1="TL_CT_COST",
                                arg2="RYPM",
                                arg3=(r, ll, p),
                            ),
                        )
                    )

                if self.tc.defined("DAM_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            CurexGmsConfig(
                                arg1="DAM_COST",
                                arg2="RYCSM",
                                arg3=(r, ll, c),
                                arg4=("ANNUAL",),
                            ),
                        )
                    )

                if self.tc.defined("S_DAM_COST"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            CurexGmsConfig(
                                arg1="S_DAM_COST",
                                arg2="S_DAM_COST",
                                arg3=(r, ll, c),
                                arg5=(g.j, g.allsow),
                            ),
                        )
                    )

                if self.tc.defined("S_COM_TAX"):
                    self.include(
                        CurexGms(
                            self.tc,
                            self.env,
                            CurexGmsConfig(
                                arg1="S_COM_TAX",
                                arg2="S_COM_TAX",
                                arg3=(r, ll, c, s, g.comvar),
                                arg5=(g.j, g.allsow),
                            ),
                        )
                    )

                self.tc.enqueue(self.exec2, prf=self.env.prf)

    def initialization(self: CurexGms) -> None:
        g = self.tc
        r_curex, r, cur, curr, Rdcur, Rxx, CurMap, cru = (
            g.r_curex,
            g.r,
            g.cur,
            g.curr,
            g.Rdcur,
            g.Rxx,
            g.CurMap,
            g.cru,
        )
        CurMap.setRecords(None)
        self.tc.container._options.profile = 0
        r_curex[r, cur, cur] = 0
        # --------------------------------------------------------------------------
        # Convert only if unambiguous single target RDCUR
        with Loop((r, curr)):
            with If(Sum(Rdcur[r, cur].where[r_curex[r, curr, cur]], 1) == 1):
                CurMap[Rdcur[r, cur], curr].where[r_curex[r, curr, cur]] = True
            with Else():  # type: ignore[no-untyped-call]
                CurMap[Rdcur[r, curr], curr] = True
        with Loop(CurMap[r, cur, curr].where[~same_as(cur, curr)]):
            Rdcur[r, curr] = False
        r_curex[Rdcur[r, cur], cur] = 1
        # Resolve two-step chained conversion
        Rxx.setRecords(None)
        with Loop(
            Domain(CurMap[Rdcur[r, cur], curr], cru).where[
                ~Rdcur[r, curr] & CurMap[r, curr, cru]
            ]
        ):
            Rxx[r, curr, cru].where[~r_curex[r, cru, cur]] = True
        with Loop(Rxx[r, curr, cru]):
            r_curex[r, cru, cur].where[CurMap[r, cur, curr]] = (
                r_curex[r, cru, curr] * r_curex[r, curr, cur]
            )
        with Loop(Rxx[r, curr, cru]):
            CurMap[r, curr, cru] = False
            CurMap[r, cur, cru].where[CurMap[r, cur, curr]] = True

    def exec1(self: CurexGms, condition: bool, mx: Any) -> None:
        g = self.tc
        cc = self.config

        r, cur, curr = g.r, g.cur, g.curr
        param_1 = g.get_parameter(name=cc.arg1)
        param_2 = g.get_parameter(name=cc.arg2)

        if cc.arg6 and mx == ():
            exponent = cc.arg6
        elif cc.arg6 is None and not isinstance(mx, tuple):
            exponent = mx  # type: ignore
        else:
            raise NotImplementedError(
                f"arg6 = {cc.arg6} and mx = {mx}. Cannot generate exponent."
            )

        if not condition:
            param_2.setRecords(None)
            param_2[*cc.arg3, *cc.arg4, cur] = sparse(param_1[*cc.arg3, cur])
            param_1.setRecords(None)

        param_1[*cc.arg3, cur, *cc.arg5] = sparse(
            Sum(
                g.CurMap[r, cur, curr].where[
                    param_2[*cc.arg3, *cc.arg4, curr, *cc.arg5]
                ],
                param_2[*cc.arg3, *cc.arg4, curr, *cc.arg5]
                * power(g.r_curex[r, curr, cur], exponent),
            )
        )

        if condition:
            param_1[*cc.arg3, cur, *cc.arg5].where[~g.Rdcur[r, cur]] = 0

    def exec2(self: CurexGms, prf: str) -> None:
        g = self.tc
        g.container._options.profile = 1  # TODO: handle this prf stuff at some point

        g.rypm.setRecords(None)
        g.rypcsm.setRecords(None)
        g.rypcsrxm.setRecords(None)
        g.rycsm.setRecords(None)

    def comp1(self: CurexGms) -> None:
        g = self.tc
        m = g.container

        g.CurMap = Set(m, name="CURMAP", domain=[g.Reg, g.cur, g.cur])
        g.cru = Alias(m, "CRU", alias_with=g.cur)
