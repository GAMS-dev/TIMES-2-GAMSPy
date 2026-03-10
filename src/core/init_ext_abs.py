# init_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INIT_EXT.xtd oversees initial preprocessor activities
# *   arg11 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtAbs(GamsClass):
    """Translation unit for init_ext.abs."""

    # Instance attributes
    module_name: str = "init_ext_abs"
    gams_source: str = "init_ext.abs"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile(tc)

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="SET BS_RVT(R,YEAR,T);",
        )
        self.tc.enqueue(self.proc_allowed)

    def proc_allowed(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Get processes allowed to participate in the reserve markets per region
  OPTION BS_BSC<BS_RMAX, TRACKP<BS_BSC; Z=CARD(TRACKP);
  BS_RTYPE(R,C)$BS_RTYPE(R,C) = SIGN(BS_RTYPE(R,C))*ROUND(MIN(5,ABS(BS_RTYPE(R,C))));
* Remove reserve commodities from topology
  LOOP(TRACKP(R,P)$Z,RP_UPR(R,P,'FX')=Z; Z=0);
  TRACKP(R,P)$=SUM((C,BD)$BS_STIME(R,P,C,BD),1);
  TOP(TRACKP(R,P),C,IO)$BS_RTYPE(R,C) = NO;
  NRG_TMAP(R,NRG_TYPE,C)$BS_RTYPE(R,C) = DIAG(NRG_TYPE,'RATE');
  OPTION CLEAR=TRACKP;
*-----------------------------------------------------------------------------
* Make A-sets
  BS_ABD(R,C,'LO')$(BS_RTYPE(R,C)<0) $=BS_RTYPE(R,C);
  BS_ABD(R,C,'UP')$(BS_RTYPE(R,C)>0) $=BS_RTYPE(R,C);
  BS_ANEG(R,C) $= BS_ABD(R,C,'LO');
  BS_APOS(R,C) $= BS_ABD(R,C,'UP');
* Remove invalid values
  BS_DEMDET(R,YEAR,RSP,C,S)$(NOT BS_RTYPE(R,C))=0;
  BS_OMEGA(R,YEAR,C,S)$(NOT BS_RTYPE(R,C))=0;
  BS_DELTA(R,YEAR,C,S)$(NOT BS_RTYPE(R,C))=0;
  BS_LAMBDA(R,YEAR,C)$(NOT BS_RTYPE(R,C))=0;
  BS_DETWT(R,YEAR,C)$(NOT BS_RTYPE(R,C))=0;
  BS_SIGMA(R,YEAR,C,ITEM,S)$(NOT BS_RTYPE(R,C))=0;
  BS_RMAX(R,YEAR,P,C,S)$(NOT BS_RTYPE(R,C))=0;
  BS_STIME(R,P,C,BD)$(NOT BS_RTYPE(R,C))=0;
""",
        )

