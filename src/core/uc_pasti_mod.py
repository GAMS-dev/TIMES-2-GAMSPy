# uc_pasti_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_PASTI code associated with first period capacity in GROWTH constraint
# *     - %1 region summation index
# *     - %2 period summation index (MIYR_1)
# *     - %3 T index
# *     - %4 'LHS' or 'RHS'
# *=============================================================================*
# *AL Questions/Comments:
# *  - Possible bound attributes are for now ignored for PASTI
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def uc_pasti_mod(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    """Translation unit for uc_pasti.mod."""

    return rf"""
*"SUM(UC_R_SUM(R,UC_N)," or bracket "("
 {arg1}

*[AL] Sum over RTP that have UC_CAP specified on current side
        SUM(RTP(R,{arg3},P)$UC_GMAP_P(R,UC_N,'CAP',P),

* Sum of PASTI inherited to first period is used as a capacity value for T-1 of MIYR_1(T)
* UC_CAP coefficient is taken from MIYR_1, because UC_CAP is interpolated on T only
            SUM(RTP_CPTYR(R,PASTYEAR,{arg3},P),COEF_CPT(R,PASTYEAR,{arg3},P)*NCAP_PASTI(R,PASTYEAR,P)) *
                UC_CAP(UC_N,{arg4},R,{arg3},P) *
* [AL] PROD operator is useful here, but needs to be 'initialized' due to a GAMS bug:
                PROD(SIDE({arg4}),PROD(UC_ATTR(R,UC_N,SIDE,'CAP','GROWTH'),
                     POWER(ABS(UC_CAP(UC_N,{arg4},R,{arg3},P)),M({arg3})-B({arg3}))))

         )

*   closing bracket of {arg1} :
    )$SUM({arg2}({arg3}),1)
"""
