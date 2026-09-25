# filshape_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILSHAPE : Fill shape parameters
# * Description: Dense interpolation/extrapolation of shape values
# * Parameters:
# * arg1 - Limit for forward extrapolation (MAXLIFE)
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import ElseIf, If, Loop, Number, Ord, Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FilshapeGms(GamsClass):
    """Translation unit for filshape.gms."""

    # Instance attributes
    module_name: str = "filshape_gms"
    gams_source: str = "filshape.gms"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: Parameter):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        g.Agefil = Set(self.tc.container, name="AGEFIL", domain=[g.age])

        self.tc.enqueue(self.filshape_exec, maxlife=self.arg1)

    def filshape_exec(self: FilshapeGms, maxlife: Parameter) -> None:
        g = self.tc
        j, age, life = g.j, g.age, g.life

        with Loop(j):
            g.z[...] = 0
            g.my_fyear[...] = 9999
            # do interpolate
            g.Agefil[age] = Number(1).where[g.shape[j, age]]

            with Loop(age.where[g.Agefil[age]]):  # check for nonzero (including EPS)
                g.my_f[...] = g.shape[j, age]
                g.z[...] = Ord(age)  # type: ignore[assignment]
                with If(g.z > (g.my_fyear + 1)):
                    g.shape[j, life].where[
                        ((Ord(life) > g.my_fyear).where[(g.z > Ord(life))])
                    ] = g.last_val + (g.my_f - g.last_val) / (g.z - g.my_fyear) * (
                        Ord(life) - g.my_fyear
                    )
                with ElseIf(g.z < g.my_fyear):
                    g.f[...] = g.z
                g.last_val[...] = g.my_f
                g.my_fyear[...] = g.z  # remember the value and year
            # Do back/forward extrapolate
            with If(g.z):
                g.shape[j, life].where[Ord(life) < g.f] = 1
                g.shape[j, life].where[
                    ((Ord(life) > g.z).where[(Ord(life) <= maxlife)])
                ] = g.last_val
