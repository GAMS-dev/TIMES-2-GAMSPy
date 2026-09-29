# mod_ext_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================*
# * MOD_EQUA.ETL Endogenous Technological learning equations         *
# * called from MOD_EQUA.MOD                                         *
# *==================================================================*

from __future__ import annotations

import logging

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_ext_etl(tc: TimesModelClass, eq: str) -> list[Equation]:
    """Translation unit for mod_ext.etl."""
    equations = [
        tc.get_equation(f"{eq}_cuinv"),
        tc.get_equation(f"{eq}_cc"),
        tc.get_equation(f"{eq}_del"),
        tc.get_equation(f"{eq}_cos"),
        tc.get_equation(f"{eq}_la1"),
        tc.get_equation(f"{eq}_la2"),
        tc.get_equation(f"{eq}_expe1"),
        tc.get_equation(f"{eq}_expe2"),
        tc.get_equation(f"{eq}_ic1"),
        tc.get_equation(f"{eq}_ic2"),
        # cluster
        tc.get_equation(f"{eq}_clu"),
        tc.get_equation(f"{eq}_mrclu"),
    ]

    return equations
