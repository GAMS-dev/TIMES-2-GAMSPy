# coefmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEFMAIN.MOD oversees the bulk of the coefficient calculations
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy.math import diag

from core.base_class import GamsClass
from core.coef_alt_lin import CoefAltLin
from core.coef_cpt_mod import CoefCptMod
from core.coef_nio_mod import CoefNioMod
from core.coef_obj_mod import CoefObjMod
from core.coef_ptr_mod import CoefPtrMod
from core.coef_shp_mod import CoefShpMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefmainMod(GamsClass):
    """Translation unit for coefmain.mod."""

    # Instance attributes
    module_name: str = "coefmain_mod"
    gams_source: str = "coefmain.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.env.stages.upper() != "YES":
            self.tc.enqueue(self.exec)

        self.include(CoefCptMod(tc=self.tc, env=self.env, arg1=self.arg1))
        self.include(CoefNioMod(tc=self.tc, env=self.env))
        self.include(CoefPtrMod(tc=self.tc, env=self.env))
        self.include(CoefObjMod(tc=self.tc, env=self.env, arg1=self.arg1))
        self.include(CoefAltLin(tc=self.tc, env=self.env, arg1=f"VAR{self.env.ctst}"))
        self.include(CoefShpMod(tc=self.tc, env=self.env))

    def exec(self) -> None:
        g = self.tc
        Sow, allsow, SwT, t = g.Sow, g.allsow, g.SwT, g.t
        Sow[allsow] = diag(allsow, "1")  # type: ignore[assignment]
        SwT[t, allsow] = Sow[allsow]
