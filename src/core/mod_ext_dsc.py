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

logger = logging.getLogger(__name__)


def mod_ext_dsc(equations: list[str], eq: str, dsc: str, solmip: str) -> None:
    """Translation unit for mod_ext.dsc."""

    if f"{dsc}{solmip}".upper() == "YESYES":
        equations.append(f"{eq}_DSCNCAP")
        equations.append(f"{eq}_DSCONE")
