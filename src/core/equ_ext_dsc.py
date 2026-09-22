# equ_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQ_EXT.dsc declarations & call for actual DSC equations
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Equation, Sum

from core.base_class import GamsClass
from core.utils import apply_sw_stvars
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtDsc(GamsClass):
    """Translation unit for equ_ext.dsc."""

    # Instance attributes
    module_name: str = "equ_ext_dsc"
    gams_source: str = "equ_ext.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal["DSC", "VDA"],
        arg2: Literal["maindrv"],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        if self.env.dsc.upper() != "YES":
            return

        g = self.tc

        domain = [g.r, g.allyear, g.p, *self.env.swtd_GP]
        eq_dscncap = Equation(
            self.tc.container,
            f"{self.env.eq}_DSCNCAP",
            domain=domain,
            description="Discrete capacity extension (=E=)",
        )
        eq_dscone = Equation(
            self.tc.container,
            f"{self.env.eq}_DSCONE",
            domain=domain,
            description="Discrete capacity extension unity condition (=E=)",
        )
        g.set_equation(f"{self.env.eq}_DSCNCAP", eq_dscncap)
        g.set_equation(f"{self.env.eq}_DSCONE", eq_dscone)

        if self.env.stages == "YES":
            apply_sw_stvars(env=self.env, g=self.tc, witspine=self.env.witspine)

        r, t, p, Rtp = g.r, g.t, g.p, g.Rtp
        PrcDscncap, ncap_disc, unit, ncap_semi = (
            g.PrcDscncap,
            g.ncap_disc,
            g.unit,
            g.ncap_semi,
        )

        VAR_NCAP, VAR_SNCAP, VAR_DNCAP = (
            g.get_variable(f"{self.env.var}_NCAP"),
            g.get_variable(f"{self.env.var}_SNCAP"),
            g.get_variable(f"{self.env.var}_DNCAP"),
        )

        r_t = self.env.r_t_GP
        sow = self.env.sow_GP

        eq_dscncap_final, dscncap_swt = macro.EQ_DSCNCAP_GP(
            self.env.eq, self.env.swt_GP
        )
        eq_dscncap_final[Rtp[*r_t, p, *dscncap_swt]].where[PrcDscncap[r, p]] = VAR_NCAP[
            r, t, p, *sow
        ] == (
            Sum(
                unit.where[ncap_disc[r, t, p, unit]],
                VAR_DNCAP[r, t, p, *sow, unit] * ncap_disc[r, t, p, unit],
            )
            + VAR_SNCAP[r, t, p, *sow].where[ncap_semi[r, t, p]]
        )
        eq_dscone_final, dscone_swt = macro.EQ_DSCONE_GP(self.env.eq, self.env.swt_GP)
        eq_dscone_final[Rtp[*r_t, p, *dscone_swt]].where[
            ncap_disc[r, t, p, "0"].where[PrcDscncap[r, p]]
        ] = (
            Sum(
                unit.where[ncap_disc[r, t, p, unit]],
                VAR_DNCAP[r, t, p, *sow, unit],
            )
            == 1
        )
