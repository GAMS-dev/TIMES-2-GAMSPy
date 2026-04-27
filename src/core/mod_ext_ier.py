# mod_ext_ier.py
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


def mod_ext_ier(equations: list[str], chp_mode: str) -> None:
    """Translation unit for mod_ext.ier."""
    equations.extend(
        [
            "EQE_MRKPRD",
            "EQL_MRKPRD",
            "EQG_MRKPRD",
            "EQE_MRKCON",
            "EQL_MRKCON",
            "EQG_MRKCON",
        ]
    )

    if chp_mode == "YES":
        equations.extend(
            [
                "EQL_CHPCON",
                "EQL_CHPBPT",
                "EQE_CHPCON",
                "EQE_CHPBPT",
            ]
        )
