# main_ext_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MAIN_EXT.mod is the extension driver
# *=============================================================================*
# * %1 is the name of the extension module to be called, e.g. 'rpt_ext' for reporting extensions
# * Different extensions are identified by file extensions given in %2, %3, %4....%9
# * Example: $BATINCLUDE rpt_ext ETL RP1 RP2
# *          This would include the reporting extensions for ETL and two custom
# *          reporting routines rpt_ext.RP1 and rpt_ext.RP2
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.base_class import GamsClass

logger = logging.getLogger(__name__)


def include_extension(
    module: GamsClass, extensions: dict[str, Any], requested_exts: set[str], source: str
) -> None:
    for ext_name, ext_class in extensions.items():
        if ext_name in requested_exts:
            module.include(
                ext_class(
                    tc=module.tc,
                    env=module.env,
                    arg1=ext_name,
                    arg2=source,
                )
            )
