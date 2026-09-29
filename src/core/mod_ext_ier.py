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

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_ext_ier(tc: TimesModelClass, chp_mode: str) -> list[Equation]:
    """Translation unit for mod_ext.ier."""
    equations = [
        tc.eqe_mrkprd,
        tc.eql_mrkprd,
        tc.eqg_mrkprd,
        tc.eqe_mrkcon,
        tc.eql_mrkcon,
        tc.eqg_mrkcon,
    ]

    if chp_mode == "YES":
        equations.extend(
            [
                tc.eql_chpcon,
                tc.eql_chpbpt,
                tc.eqe_chpcon,
                tc.eqe_chpbpt,
            ]
        )

    return equations
