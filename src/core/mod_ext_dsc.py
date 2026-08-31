# mod_ext_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================*
# * MOD_EXT.EXT EXTENSION EQUATIONS                                  *
# * called from MAINDRV.MOD                                          *
# *==================================================================*

from __future__ import annotations

import logging

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_ext_dsc(tc: TimesModelClass, eq: str, dsc: str, solmip: str) -> list[Equation]:
    """Translation unit for mod_ext.dsc."""

    equations = []
    eq = eq.lower()
    if f"{dsc}{solmip}".upper() == "YESYES":
        equations.append(tc.get_equation(f"{eq}_dscncap"))
        equations.append(tc.get_equation(f"{eq}_dscone"))

    return equations
