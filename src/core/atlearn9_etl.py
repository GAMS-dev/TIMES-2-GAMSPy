# atlearn9_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * File      : ATLEARN9.ETL
# * Language  : GAMS
# * Programmer: Ad Seebregts, adaped by Gary Goldstein for TIMES
# * Origin    : 04-02-00
# * Last edit : 07-27-01
# *=============================================================================*
# * arg1 = k or c
# * arg2 = VAR_NCAP or VAR_CAP
# * arg3 = TEG or PRC
# * arg4 = 0 1 2 3 4
# *      0 is for variable INV or CAP
# *      1 CAM; 2 GRP; 3 GRA; 4 GRF;
# * arg5 = INV or CAP or CAM or GRP or GRA or GRF;

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def atlearn9_etl(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
) -> str:
    return rf"""
     PUT "{arg1}",".{arg5}.",{arg3}.TL:0, '/r.', REG.TL:0, @30;
     PUT PRC.TE({arg3}):30 @74;
     LOOP(T,
          IF ({arg4} EQ 0,
              PUT {arg2}.L(REG,T,{arg3}):10:2;
             );

* maximum capacity based on growth factors
*          IF ({arg4} EQ 1,
*
*                  IF ((PRC_TGR({arg3},T) + PRC_GRTI({arg3})) GT 0,
*                      PUT ((PRC_TGR({arg3},T)**NYRSPER)*CAP.L(T-1,{arg3}) +
*                           PRC_GRTI({arg3})
*                          ):10:2;
*                  ELSE PUT "         -";
*                     );
*
*             );

* period growth factor CAP(T)/CAP(T-1)
          IF ({arg4} EQ 2,

              IF (VAR_CAP.L(REG,T-1,{arg3}) GT 0,
                  PUT (VAR_CAP.L(REG,T,{arg3})/(VAR_CAP.L(REG,T-1,{arg3}))):10:2;
              ELSE PUT "         -";
                 );
             );

* average annual growth factor in period T compared to T-1
          IF ({arg4} EQ 3,
             IF (VAR_CAP.L(REG,T-1,{arg3}) GT 0,
                 PUT ((VAR_CAP.L(REG,T,{arg3})/VAR_CAP.L(REG,T-1,{arg3}))**(1/D(T))):10:2;
             ELSE PUT "         -";
                 );

             );
* user-provided maximum growth factors: for the first T, the TID
* growth factor is given, if provided
*          IF ({arg4} EQ 4,
*
*             IF (ORD(T) EQ 1,
*                 IF (PRC_GRTI({arg3}) GT 0,
*                     PUT  TCH_GRTI({arg3}):10:2;
*                 ELSE PUT "         -";
*                    );
*             ELSE
*                 IF (PRC_TGR({arg3},T) GT 0,
*                      PUT (TCH_TGR({arg3},T)):10:2;
*                 ELSE PUT "         -";
*                    );
*                );
*             );
*
*
         );

     PUT /;
"""
