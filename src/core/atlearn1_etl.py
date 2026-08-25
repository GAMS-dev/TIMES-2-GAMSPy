# atlearn1_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * File      : ATLEARN1.ML
# * Language  : GAMS
# * Programmer: Ad Seebregts, adaped by Gary Goldstein for TIMES
# * Origin    : 02-06-98
# * Last edit : 07-27-01
# * Warning   :
# * Purpose   : generic content of AT output
# * Location  : TIMES directory
# * Called    : at the end of ATLEARN.ETL
# * Output    : <case>.ETL
# *=============================================================================*
# * arg1 IS VARIABLE TO BE OUTPUTTED
# * arg2 is name of table
# * arg3 is prefix of row
# * arg4 is 1 if CCAPM is to be output
# * arg5 is number of decimals

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def atlearn1_etl(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
) -> str:
    return rf"""
PUT /"{arg2} {arg1}"/;
PUT @63, LOOP(T,PUT T.TL:10);
IF ({arg4} GT 0, PUT "CCAPM     % reached";
   );
PUT /;

LOOP((TEG,REG)$SEG(REG,TEG),
     PUT "k",".{arg3}.",TEG.TL:0 '/r.'REG.TL:0, ' ';
     PUT @30, PRC.TE(TEG):30 @60;
     LOOP(T,
          IF ({arg1}.L(REG,T,TEG) GT 0,
              PUT {arg1}.L(REG,T,TEG):10:{arg5};
          ELSE PUT "         0";
             );
          IF ((ORD(T) EQ CARD(T)) AND ({arg4} GT 0),
              PUT " ",CCAPM(REG,TEG):10:2; PUT (100 - 100*(CCAPM(REG,TEG)-VAR_CCAP.L(REG,T,TEG))/
                                            (CCAPM(REG,TEG)-CCAP0(REG,TEG))):10:2;
             );
         );
     PUT /;
* print PRC in TEG cluster
     IF({arg4} EQ 0,
      LOOP(PRC$(CLUSTER(REG,TEG,PRC) GT 0),
          PUT "c",".{arg3}.",PRC.TL:0;
          PUT @30, PRC.TE(PRC):30 @60;
          LOOP(T,
               IF ({arg1}.L(REG,T,PRC) GT 0,
                   PUT {arg1}.L(REG,T,PRC):10:{arg5};
               ELSE PUT "         0";
                  );
              );
          PUT /;
          );
     );
    );
"""
