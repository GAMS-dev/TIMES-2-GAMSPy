# mod_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================*
# * MOD_EQUA.ABS Ancillary Balancing Services equations
# * called from MOD_EQUA.MOD
# *==================================================================*

from __future__ import annotations

import logging

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_ext_abs(tc: TimesModelClass, obmac: str) -> list[Equation]:
    """Translation unit for mod_ext.abs."""

    equations = []
    if obmac.upper() == "YES":
        equations.extend(
            [
                tc.eq_bs00,
                tc.eq_bs01,
                tc.eq_bs02,
                tc.eq_bs03,
                tc.eq_bs04,
                tc.eq_bs05,
                tc.eq_bs07,
                tc.eq_bs09,
                tc.eq_bs10,
                tc.eq_bs11,
                tc.eq_bs18,
                tc.eq_bs19,
                tc.eq_bs22,
                tc.eq_bs23,
                tc.eq_bs24,
                tc.eq_bs25,
                tc.eq_bs26,
                tc.eq_bs27,
                tc.eq_bs28,
            ]
        )

    return equations
