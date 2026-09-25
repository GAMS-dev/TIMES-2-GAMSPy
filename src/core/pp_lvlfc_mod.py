# pp_lvlfc_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLPC aggregate/inherit attributes if at different than target level
# * Parameter arguments must be of the form (R,V,{P/C/P,C},S[,xx]*)
# *   arg1 - attribute name (FLO_COST, FLO_TAX etc.)
# *   arg2 - 'P', 'C' 'COM' or 'P,C' depending on attribute
# *   arg3 - TS set shooting for
# *   arg4 - remaining indexes (e.g. ',CUR')
# *   arg5 - UNCD7 residual dimension
# *   arg6 - ALL_TS or TS depending on whether inheritance is allowed
# *   arg7 - YEAR set to look for data (DATAYEAR/XMILE/V/'')
# *   arg8 - Existence qualifier set or YES
# *   arg9 - Optional indicator for weighting: Use 1 if inheritance is weighted
# *  arg10 - Optional indexes between TS set items and the S index
# *=============================================================================*


from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Alias,
    Domain,
    Else,
    Expression,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Sum,
    UniverseAlias,
)
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class PpLvlfcModConfig:
    arg1: Parameter
    arg2: tuple[Set | Alias, ...]
    arg3: Set
    arg4: tuple[Set | Alias | UniverseAlias, ...]
    arg5: tuple[str, ...]
    arg6: Set | Alias
    arg7: tuple[Set | Alias, ...]
    arg8: ImplicitSet | Number | Condition
    arg9: bool = False
    arg10: tuple[Set | Alias, ...] = ()
    arg11: Literal["N"] | Number | None = None
    arg12: Expression | ImplicitParameter | ImplicitSet | Number = Number(1)  # noqa: RUF009


class PpLvlfcMod(GamsClass):
    """Translation unit for pp_lvlfc.mod."""

    # Instance attributes
    module_name: str = "pp_lvlfc_mod"
    gams_source: str = "pp_lvlfc.mod"

    def __init__(
        self: PpLvlfcMod,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: PpLvlfcModConfig,
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self: PpLvlfcMod) -> None:
        self.tc.enqueue(pp_lvlfc_mod, module=self, cc=self.config)


def clear_uncd7(module: GamsClass) -> None:
    g = module.tc
    g.Uncd7.setRecords(None)


def all_exec(
    module: GamsClass,
    take: Expression | Number | ImplicitSet | ImplicitParameter,
    regy: tuple[Set | Alias, ...],
    ts: Expression | Number,
    awgt: Expression | Number,
    iwgt: Expression | Number,
    cc: PpLvlfcModConfig,
) -> None:
    g = module.tc
    r, ll, stoa, s, stoal = g.r, g.ll, g.stoa, g.s, g.stoal
    Uncd7 = g.Uncd7
    ts_array, RsBelow, Annual, TsMap, sl, Finest = (
        g.ts_array,
        g.RsBelow,
        g.Annual,
        g.TsMap,
        g.sl,
        g.Finest,
    )

    if isinstance(cc.arg11, str) and cc.arg11 == "N":
        cc.arg1[
            r,
            ll.lag(Ord(ll), type="circular"),
            *cc.arg2,
            *cc.arg10,
            s + stoa[s],
            *cc.arg4,
        ].where[stoal[r, s].where[cc.arg1[r, ll, *cc.arg2, *cc.arg10, s, *cc.arg4]]] = 1

    # Mark to be levelized if inheritance is allowed or S is not ANNUAL:
    with Loop(
        Domain(*regy, *cc.arg2, *cc.arg10, s, *cc.arg4).where[  # type: ignore[arg-type]
            ts.where[cc.arg1[*regy, *cc.arg2, *cc.arg10, s, *cc.arg4]]
        ]
    ):
        Uncd7[*regy, *cc.arg2, *cc.arg10, *cc.arg4, *cc.arg5].where[cc.arg8 & take] = (
            True
        )

    # Aggregation/inheritance to target timeslices
    with Loop(Uncd7[*regy, *cc.arg2, *cc.arg10, *cc.arg4, *cc.arg5]):
        ts_array[s] = cc.arg1[*regy, *cc.arg2, *cc.arg10, s, *cc.arg4]
        with If(
            (~Sum(RsBelow[r, "ANNUAL", s].where[ts_array[s]], 1)).where[
                ts_array["ANNUAL"]
            ]
        ):
            cc.arg1[*regy, *cc.arg2, *cc.arg10, s, *cc.arg4].where[
                cc.arg3[r, *cc.arg2, s]
            ] = Sum(Annual[cc.arg6], ts_array[cc.arg6] * iwgt)

        with Else():  # type: ignore[no-untyped-call] # noqa: SIM117
            # Leveling by simultaneous aggregation/inheritance; but only if target level value is not present
            with Loop(cc.arg3[r, *cc.arg2, g.ts].where[~ts_array[g.ts]]):
                sparse_expr = Sum(
                    TsMap[r, g.ts, s].where[Finest[r, s]],
                    awgt
                    * (
                        ts_array[s]
                        + Sum(
                            RsBelow[r, cc.arg6, s].where[
                                ts_array[cc.arg6]
                                & (
                                    ~Sum(
                                        sl.where[RsBelow[r, cc.arg6, sl]],
                                        TsMap[r, sl, s] * ts_array[sl],
                                    )
                                )
                            ],
                            ts_array[cc.arg6] * iwgt,
                        )
                    ),
                )
                cc.arg1[*regy, *cc.arg2, *cc.arg10, g.ts, *cc.arg4].where[
                    sparse_expr
                ] = sparse_expr

    if isinstance(cc.arg11, Number) and cc.arg11._value == 0:
        expr = cc.arg1[*regy, *cc.arg2, *cc.arg10, "ANNUAL", *cc.arg4]
        cc.arg1[*regy, *cc.arg2, *cc.arg10, s, *cc.arg4].where[
            (~cc.arg1[*regy, *cc.arg2, *cc.arg10, s, *cc.arg4]).where[
                cc.arg3[r, *cc.arg2, s]
            ]
            & expr
        ] = expr

    if cc.arg11:
        cc.arg1[r, ll, *cc.arg2, *cc.arg10, s, *cc.arg4].where[
            (~cc.arg3[r, *cc.arg2, s]).where[take]
        ] = 0


def pp_lvlfc_mod(module: GamsClass, cc: PpLvlfcModConfig) -> None:
    g = module.tc
    clear_uncd7(module=module)

    take = cc.arg12
    regy = (g.r, *cc.arg7)
    ts = Number(1) if cc.arg6.name == "S2" else ~cc.arg3[g.r, *cc.arg2, g.s]
    awgt: Number | Expression = g.g_yrfr[g.r, g.s] / g.g_yrfr[g.r, g.ts]
    iwgt: Number | Expression = Number(1)

    if cc.arg9:
        awgt = Number(1)
        iwgt = g.g_yrfr[g.r, g.s] / g.g_yrfr[g.r, cc.arg6]

    if isinstance(cc.arg11, str) and cc.arg11 == "N":
        take = cc.arg1[g.r, "0", *cc.arg2, *cc.arg10, "ANNUAL", *cc.arg4]

    all_exec(module=module, take=take, regy=regy, ts=ts, awgt=awgt, iwgt=iwgt, cc=cc)
