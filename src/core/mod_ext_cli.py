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

logger = logging.getLogger(__name__)


def mod_ext_cli(equations: list[str], eq: str) -> None:
    """Translation unit for mod_ext.cli."""

    equations.extend(
        [
            f"{eq}_CLITOT",
            f"{eq}_CLICONC",
            f"{eq}_CLITEMP",
            f"{eq}_CLIBEOH",
            f"{eq}_CLIMAX",
        ]
    )
