# atlearn8_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * File      : ATLEARN8.ETL
# * Language  : GAMS
# * Programmer: Ad Seebregts, adaped by Gary Goldstein for TIMES
# * Origin    : 04-02-00
# * Last edit : 07-27-01
# *=============================================================================*
# * loop over TEG, PRC for key and clusters
# *      INV CAP
# *      CAM : maximum capacity based on growth factors
# *      GRP : growth in capacity in one period (CAP(TP)/CAP(TP-1))
# *      GRA : average annual growth in NYEARS of period TP
# *      GRF : growth factor (input): TID and time-dependent

from __future__ import annotations

import logging

from core.atlearn9_etl import atlearn9_etl

logger = logging.getLogger(__name__)


def atlearn8_etl() -> str:
    return rf"""
LOOP((TEG,REG)$SEG(REG,TEG),
*    Investment levels
     PUT /;
*    first output for key, next its cluster PRC's
{atlearn9_etl(arg1="k", arg2="VAR_NCAP", arg3="TEG", arg4="0", arg5="INV")}
     LOOP(PRC$CLUSTER(REG,TEG,PRC),
{atlearn9_etl(arg1="c", arg2="VAR_NCAP", arg3="PRC", arg4="0", arg5="INV")}
         );

*    Capacity levels and growth factors (input and resulting)
     PUT /;
{atlearn9_etl(arg1="k", arg2="VAR_CAP", arg3="TEG", arg4="0", arg5="CAP")}
{atlearn9_etl(arg1="k", arg2="VAR_CAP", arg3="TEG", arg4="1", arg5="CAM")}
{atlearn9_etl(arg1="k", arg2="VAR_CAP", arg3="TEG", arg4="2", arg5="GRP")}
{atlearn9_etl(arg1="k", arg2="VAR_CAP", arg3="TEG", arg4="3", arg5="GRA")}
{atlearn9_etl(arg1="k", arg2="VAR_CAP", arg3="TEG", arg4="4", arg5="GRF")}

     LOOP(PRC$CLUSTER(REG,TEG,PRC),
{atlearn9_etl(arg1="c", arg2="VAR_CAP", arg3="PRC", arg4="0", arg5="CAP")}
{atlearn9_etl(arg1="c", arg2="VAR_CAP", arg3="PRC", arg4="1", arg5="CAM")}
{atlearn9_etl(arg1="c", arg2="VAR_CAP", arg3="PRC", arg4="2", arg5="GRP")}
{atlearn9_etl(arg1="c", arg2="VAR_CAP", arg3="PRC", arg4="3", arg5="GRA")}
{atlearn9_etl(arg1="c", arg2="VAR_CAP", arg3="PRC", arg4="4", arg5="GRF")}
         );

     );
"""
