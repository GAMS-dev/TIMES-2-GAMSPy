# pp_lvlus_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLUS aggregate/inherit UC_N attributes if at different than target level
# *   arg1 - attribute name (UC_ACT, UC_FLO etc.)
# *   arg2 - other qualifying indexes before S index (e.g. ',C')
# *   arg3 - TS set shooting for (PRC_TS, RPCS etc.)
# *   arg4 - UNCD7 residual dimension
# *   arg5 - optional remaining indexes (e.g. 'IE')
# *   arg6 - optional UC_N qualifying indexes (e.g. COM_VAR)
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

from gamspy import (
    Alias,
    Domain,
    If,
    Loop,
    Ord,
    Parameter,
    Set,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlusConfig(NamedTuple):
    uc_parameter: Parameter
    arg2: tuple[Alias | Set, ...]
    arg3: Set | Alias
    arg4: tuple[str, ...] | tuple[()]
    arg5: tuple[Set | Alias] | tuple[()]
    arg6: tuple[Set | Alias] | tuple[()]
    arg7: Set | Alias
    arg8: Set | Alias
    arg9: Parameter | ImplicitParameter | int = 0
    arg10: tuple[Set | Alias] | tuple[()] = ()


class PpLvlusMod(GamsClass):
    """Translation unit for pp_lvlus.mod."""

    # Instance attributes
    module_name: str = "pp_lvlus_mod"
    gams_source: str = "pp_lvlus.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: PpLvlusConfig
    ):
        super().__init__(tc, env)
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.exec1, self.config)
        self.tc.enqueue(self.simultaneous_aggregation, self.config)

    def exec1(self: PpLvlusMod, cc: PpLvlusConfig) -> None:
        g = self.tc
        r, t, s, io, side, ucn, tsl = g.r, g.t, g.s, g.io, g.side, g.ucn, g.tsl

        g.Uncd7.setRecords(None)

        loop_domain = [ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5]

        with Loop(Domain(*loop_domain).where[cc.uc_parameter[*loop_domain]]):  # noqa: SIM117
            with If((~cc.arg3[r, cc.arg7, *cc.arg10, s]).where[g.stoa[s]]):
                g.z[...] = g.stoal[r, s]

                out_marker = g.Uncd7[
                    ucn, *cc.arg6, side, r, *cc.arg2, *cc.arg5, "OUT", *cc.arg4
                ]
                with If(out_marker):  # type: ignore[arg-type] # noqa: SIM117
                    with If(g.z[...] > g.f[...]):
                        g.f[...] = 9
                        g.Uncd7[
                            ucn, *cc.arg6, side, r, *cc.arg2, *cc.arg5, "IN", *cc.arg4
                        ] = True
                # ELSE
                with If(~out_marker):
                    g.f[...] = Smax(
                        cc.arg8[r, cc.arg7, tsl],
                        Max(cc.arg9 + SpecialValues.EPS, Ord(tsl) - 1),
                    )
                    with If(g.z[...] > g.f[...]):
                        g.f[...] = 9
                        g.Uncd7[
                            ucn, *cc.arg6, side, r, *cc.arg2, *cc.arg5, io, *cc.arg4
                        ] = True
                    # ELSE
                    with If(g.z[...] <= g.f[...]):
                        g.Uncd7[
                            ucn,
                            *cc.arg6,
                            side,
                            r,
                            *cc.arg2,
                            *cc.arg5,
                            "OUT",
                            *cc.arg4,
                        ] = True

    def simultaneous_aggregation(self: PpLvlusMod, cc: PpLvlusConfig) -> None:
        """Simultaneous aggregation/inheritance to target timeslices"""
        g = self.tc
        r, t, s, j, tsl = g.r, g.t, g.s, g.j, g.tsl
        io, side, ucn, ts, all_ts, sl = g.io, g.side, g.ucn, g.ts, g.allts, g.sl

        with Loop(g.Uncd7[ucn, *cc.arg6, side, r, *cc.arg2, *cc.arg5, io, *cc.arg4]):
            with If(g.ips[io]):  # type: ignore[arg-type]
                g.f[...] = 0
                # Leveling by simultaneous aggregation/inheritance; but only if target level value is not present
                with Loop(t):
                    g.ts_array[s] = cc.uc_parameter[
                        ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5
                    ]
                    cc.uc_parameter[
                        ucn, *cc.arg6, side, r, t, *cc.arg2, ts, *cc.arg5
                    ].where[
                        (~g.ts_array[ts]).where[cc.arg3[r, cc.arg7, *cc.arg10, ts]]
                    ] = sparse(
                        Sum(
                            g.RsTree[g.Finest[r, s], ts],
                            g.g_yrfr[r, s]
                            * (
                                g.ts_array[s]
                                + Sum(
                                    all_ts.where[
                                        g.RsBelow[r, all_ts, s]
                                        & (
                                            ~Sum(
                                                sl.where[g.RsBelow[r, all_ts, sl]],
                                                g.TsMap[r, sl, s] * g.ts_array[sl],
                                            )
                                        )
                                        & g.ts_array[all_ts]
                                    ],
                                    g.ts_array[all_ts],
                                )
                            ),
                        )
                        / g.g_yrfr[r, ts]
                    )
            # ELSEIF
            with If((~g.ips[io]) & (g.f[...] != 0)):  # noqa: SIM117
                # Inherit all from above
                with Loop(t):
                    g.ts_array[s] = cc.uc_parameter[
                        ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5
                    ]
                    with Loop(g.Rjlvl[j, r, tsl].where[Ord(tsl) < 4]):
                        with Loop(g.TsGroup[r, tsl, ts]):
                            g.ts_array[s].where[~g.ts_array[s]] = sparse(
                                g.ts_array[ts].where[g.RsBelow[r, ts, s]]
                            )
                        cc.uc_parameter[
                            ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5
                        ].where[cc.arg3[r, cc.arg7, *cc.arg10, s]] = sparse(
                            g.ts_array[s]
                        )
            # ELSE
            with If((~g.ips[io]) & (g.f[...] == 0)):
                g.f[...] = 1

        # *-----------------------------------------------------------------------------

        cc.uc_parameter[ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5].where[
            cc.arg3[r, cc.arg7, *cc.arg10, s].where[
                ~cc.uc_parameter[ucn, *cc.arg6, side, r, t, *cc.arg2, s, *cc.arg5]
            ]
        ] = sparse(
            cc.uc_parameter[ucn, *cc.arg6, side, r, t, *cc.arg2, "ANNUAL", *cc.arg5]
        )

        g.Uncd7.setRecords(None)
