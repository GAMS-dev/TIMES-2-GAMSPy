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

logger = logging.getLogger(__name__)


def mod_ext_etl(equations: list[str], eq: str) -> None:
    """Translation unit for mod_ext.etl."""
    equations.extend(
        [
            f"{eq}_CUINV",
            f"{eq}_CC",
            f"{eq}_DEL",
            f"{eq}_COS",
            f"{eq}_LA1",
            f"{eq}_LA2",
            f"{eq}_EXPE1",
            f"{eq}_EXPE2",
            f"{eq}_IC1",
            f"{eq}_IC2",
            # cluster
            f"{eq}_CLU",
            f"{eq}_MRCLU",
        ]
    )
