# filshape_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILSHAPE : Fill shape parameters
# * Description: Dense interpolation/extrapolation of shape values
# * Parameters:
# * arg1 - Limit for forward extrapolation (MAXLIFE)
# *******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FilshapeGms(GamsClass):
    """Translation unit for filshape.gms."""

    # Instance attributes
    module_name: str = "filshape_gms"
    gams_source: str = "filshape.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(module=self, phase="init", code=r"SET AGEFIL(AGE);")
        self.tc.enqueue(
            self.filshape_exec,
            maxlife=self.arg1,
        )

    def filshape_exec(self: FilshapeGms, maxlife: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
$ EOLCOM !
 LOOP(J, Z = 0; MY_FYEAR = 9999;
* do interpolate
     AGEFIL(AGE) = YES$SHAPE(J,AGE);
     LOOP(AGE$AGEFIL(AGE),                ! check for nonzero (including EPS)
	  MY_F = SHAPE(J,AGE); Z = ORD(AGE);
          IF(Z > MY_FYEAR+1,                      ! linear interpolation
               SHAPE(J,LIFE)$((ORD(LIFE) GT MY_FYEAR)$(Z GT ORD(LIFE)))
			= LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(ORD(LIFE)-MY_FYEAR);
	  ELSEIF Z LT MY_FYEAR, F = Z;);
	  LAST_VAL = MY_F; MY_FYEAR=Z;);   ! remember the value and year
* Do back/forward extrapolate
     IF(Z, SHAPE(J,LIFE)$(ORD(LIFE) LT F) = 1;
           SHAPE(J,LIFE)$((ORD(LIFE) GT Z)$(ORD(LIFE) LE {maxlife})) = LAST_VAL;);
 );
""",
        )
