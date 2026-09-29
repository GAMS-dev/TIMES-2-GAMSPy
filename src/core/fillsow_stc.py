# fillsow_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLSOW : Fill stochastic parameters
# * Description: Preprocessing of stochastic uncertain data
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1 (before year index)
# *      arg3 - control set 2 (after year index)
# *      arg4 - Source data years T/LL
# *      arg5 - YES/NO for absolute/relative parameters
# *      arg6 - PERIOD control (SW_T OR PERIODYR OR SUPERYR)
# *      arg7 - YES/NO to copy baseline parameters
# *******************************************************************************
# *$ONLISTING

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NamedTuple

from gamspy import Alias, Card, Loop, Number, Ord, Set, Sum, sparse
from gamspy.math import same_as

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillsowStcConfig(NamedTuple):
    arg1: str
    arg2: tuple[Alias | Set, ...] | tuple[()]
    arg3: tuple[Alias | Set | str, ...] | tuple[()]
    arg4: tuple[Alias] | tuple[()]
    arg5: bool
    arg6: ImplicitSet | Number = Number(1)
    arg7: bool = False


class FillsowStc(GamsClass):
    """Translation unit for fillsow.stc."""

    # Instance attributes
    module_name: str = "fillsow_stc"
    gams_source: str = "fillsow.stc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: FillsowStcConfig,
    ) -> None:
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        tail: tuple[Alias | Set | str, ...] | tuple[()] = self.config.arg3
        ix: tuple[str] | tuple[()] = ("0",)
        stg = False

        if not self.config.arg3:
            tail = ()

        if not self.config.arg4:
            ix = ()

        if self.config.arg4 == (g.t,):
            stg = True

        self.tc.enqueue(
            clean_up_sow, module=self, config=self.config, tail=tail, ix=ix, stg=stg
        )

        if not self.config.arg5:
            return

        self.tc.enqueue(
            update_data_indicators,
            module=self,
            config=self.config,
            tail=tail,
            ix=ix,
            stg=stg,
        )


def clean_up_sow(
    module: GamsClass,
    config: FillsowStcConfig,
    tail: tuple[Alias | Set | str, ...] | tuple[()],
    ix: tuple[str] | tuple[()],
    stg: bool,
) -> None:
    g = module.tc
    t, j, ww, Sow, ll = g.t, g.j, g.ww, g.Sow, g.ll
    s_arg1 = g.get_parameter(f"S_{config.arg1}")
    arg2, arg4 = config.arg2, config.arg4

    # * Clean up stage 1 from invalid SOW:
    s_arg1[*arg2, *arg4, *tail, "1", Sow].where[~same_as(Sow, "1")] = 0.0

    # * Set up data indicators
    if arg4:
        s_arg1[*arg2, ll.lag(Ord(ll), "circular"), *tail, j, ww] = sparse(
            s_arg1[*arg2, ll, *tail, j, ww]
        )
    g.f[...] = Card(s_arg1)

    # * Copy parameters from first to other branches when appropriate
    not_set = ~s_arg1[*arg2, *ix, *tail, j, ww]
    s_arg1[*arg2, *arg4, *tail, j, ww].where[
        g.SwTstg[t, j].where[not_set] if stg else not_set
    ] = sparse(Sum(g.SwCpmap[j, ww, Sow], s_arg1[*arg2, *arg4, *tail, j, Sow]))


def update_data_indicators(
    module: GamsClass,
    config: FillsowStcConfig,
    tail: tuple[Alias | Set | str, ...] | tuple[()],
    ix: tuple[str] | tuple[()],
    stg: bool,
) -> None:
    g = module.tc
    t, j, ww, Sow, ll = g.t, g.j, g.ww, g.Sow, g.ll
    s_arg1 = g.get_parameter(f"S_{config.arg1}")
    arg2, arg4 = config.arg2, config.arg4
    arg6 = config.arg6

    # * Update data indicators if eventual copy occurred
    if arg4 and (Card(s_arg1) > g.f).toValue():
        s_arg1[*arg2, ll.lag(Ord(ll), "circular"), *tail, j, ww] = sparse(
            s_arg1[*arg2, ll, *tail, j, ww]
        )

    # * Copy baseline parameters to stage 1, SOW 1:
    if config.arg7:
        arg1 = g.get_parameter(config.arg1)
        s_arg1[*arg2, *arg4, *tail, "1", "1"].where[
            ~s_arg1[*arg2, *ix, *tail, "1", "1"]
        ] = sparse(arg1[*arg2, *arg4, *tail])

    # * Merge to single stage 1:
    if arg4 != (ll,):
        with Loop(j.where[g.sw_start[j]]):
            s_arg1[*arg2, *arg4, *tail, "1", ww].where[
                g.SwTstg[t, j].where[arg6] if stg else arg6
            ] = sparse(Sum(g.SwRev[ww, j, Sow], s_arg1[*arg2, *arg4, *tail, j, Sow]))
    else:
        with Loop(g.SwTstg[t, j]):
            s_arg1[*arg2, *arg4, *tail, "1", ww].where[arg6.where[g.SwT[t, ww]]] = (
                sparse(Sum(g.SwRev[ww, j, Sow], s_arg1[*arg2, *arg4, *tail, j, Sow]))
            )

    # * Remove flags if LL
    if arg4 == (ll,):
        s_arg1[*arg2, *ix, *tail, j, ww] = 0.0


def exec_fillsow_stc(module: GamsClass, config: FillsowStcConfig) -> None:
    """Run fillsow.stc at execution time, from inside an already-enqueued block."""
    # TODO this could be removed since its only called inside an if, which is evaluated in python
    # BUT then need to differentiate in the class between included or not
    # so that no second enqueue is happening!!
    g = module.tc
    tail: tuple[Alias | Set | str, ...] | tuple[()] = config.arg3
    ix: tuple[str] | tuple[()] = ("0",)
    stg = False

    if not config.arg3:
        tail = ()

    if not config.arg4:
        ix = ()

    if config.arg4 == (g.t,):
        stg = True

    clean_up_sow(module=module, config=config, tail=tail, ix=ix, stg=stg)

    if not config.arg5:
        return

    update_data_indicators(module=module, config=config, tail=tail, ix=ix, stg=stg)
