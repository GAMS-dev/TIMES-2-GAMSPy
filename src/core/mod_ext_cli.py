# mod_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
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


def mod_ext_cli(tc: TimesModelClass, eq: str) -> list[Equation]:
    """Translation unit for mod_ext.cli."""

    equations = [
        tc.get_equation(f"{eq}_clitot"),
        tc.get_equation(f"{eq}_cliconc"),
        tc.get_equation(f"{eq}_clitemp"),
        tc.get_equation(f"{eq}_clibeoh"),
        tc.get_equation(f"{eq}_climax"),
    ]

    return equations
