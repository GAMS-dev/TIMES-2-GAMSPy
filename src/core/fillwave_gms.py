# fillwave_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************
# * FILLWAVE : Fill parameters via weighted centered averaging
# * arg1 - table name
# * arg2 - index set (after year index)
# *******************************************************************

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, For, If, Loop, Number, Set, Smax, Sum
from gamspy.math import project

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Expression, Parameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class FillwaveGmsConfig:
    table: Parameter  # %1 - table name
    index_set: Set  # %2 - index set (after year index)
    extrapolate: Literal[0, 1]  # %3 - 1 fills the tail years after the last data year


class FillwaveGms(GamsClass):
    """Translation unit for fillwave.gms."""

    # Instance attributes
    module_name: str = "fillwave_gms"
    gams_source: str = "fillwave.gms"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: FillwaveGmsConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        cc = self.config

        self.env.set_scoped("tmp", "OBJ_DISC(R,LL,CUR)/COEF_PVT(R,T)")
        self.env.set_scoped(
            "tmp_GP", g.obj_disc[g.r, g.ll, g.cur] / g.coef_pvt[g.r, g.t]
        )
        if self.env.ctst == "":
            self.env.set_scoped("tmp", "1/D(T)")
            self.env.set_scoped("tmp_GP", 1 / g.d[g.t])

        name = f"REG_{cc.index_set.name}"
        reg_set = Set(m, name=name, domain=[g.Reg, cc.index_set])
        g.set_set(name=name, set=reg_set, domain=True)

        self.tc.enqueue(self.exec1, cc, reg_set=reg_set, tmp=self.env.tmp_GP)

    def exec1(
        self: FillwaveGms, cc: FillwaveGmsConfig, reg_set: Set, tmp: Expression
    ) -> None:
        g = self.tc
        r, t, tt, ll, cur = g.r, g.t, g.tt, g.ll, g.cur

        if g.vda_disc.number_records == 0:
            g.vda_disc[r, g.Miyr1] = 1
            with Loop(Domain(g.GRcur[r, cur], t[tt + 1])):
                g.vda_disc[r, g.YEoh[ll]].where[g.Periodyr[t, ll]] = tmp
        project(source=cc.table, target=reg_set, direction="left")
        g.done[...] = Smax(t, g.m[t])
        with Loop(reg_set[r, cc.index_set]):
            g.fil2.setRecords(None)
            g.my_array[g.DmYear] = cc.table[r, g.DmYear, cc.index_set]
            g.my_f[...] = 0
            g.z[...] = 0
            # * interpolate densely
            with Loop(g.DmYear[ll].where[g.my_array[ll]]):
                g.last_val[...] = g.my_f
                g.f[...] = g.z
                g.my_f[...] = g.my_array[ll]
                g.z[...] = g.yearval[ll]
                with If(g.last_val):  # noqa: SIM117
                    with For(g.cnt, g.f - g.z + 1, -1):
                        g.fil2[ll + g.cnt] = (
                            g.my_f + (g.my_f - g.last_val) / (g.z - g.f) * g.cnt
                        )
            with If(g.done == g.z.where[Number(cc.extrapolate)]):
                g.fil2[g.YEoh].where[g.yearval[g.YEoh] > g.z] = g.my_f
            # * weighted centered average
            cc.table[r, t, cc.index_set] = Sum(
                g.Periodyr[t, g.YEoh[ll]],
                (g.my_array[ll] + g.fil2[ll]) * g.vda_disc[r, ll],
            )
