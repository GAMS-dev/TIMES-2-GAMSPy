# eqblnd_mod.py
# # *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *----------------------------------------------------------------------------*
# *GG* V07_2 BLENDing equation
# *  - %1 L/G/E/N
# *  - %2 1/2/3/4
# *----------------------------------------------------------------------------*
# *GG* Move these to the appropriate modules
# *----------------------------------------------------------------------------*
# * DISCOUNT ANNUAL COSTS
# *----------------------------------------------------------------------------*
# *  add blending costs
# *  SUM(BLE_TP(TP,BLE),
# *    SUM(OPR$BLE_OPR(BLE,OPR), (PRICE_BLE(TP,BLE,OPR) *  BLND(TP,BLE,OPR)))
# *  )
# *
# *----------------------------------------------------------------------------*
# * ANNUALIZED ANNUAL COSTS
# *----------------------------------------------------------------------------*
# *  add blending costs
# *  SUM(BLE_OPR(BLE,OPR)$BLE_TP(TP,BLE),
# *    ANNC_BLE(TP,BLE,OPR) * BLND(TP,BLE,OPR)
# *  )
# *
# *----------------------------------------------------------------------------*
# * BALANCE (plus ELC)
# *----------------------------------------------------------------------------*
# *  add blending requirements
# *  SUM(OPR$BLE_OPR(ENC_G,OPR),
# *    BAL_BLE(TP,ENC_G,OPR) * BLND(TP,ENC_G,OPR)
# *  ) +
# *  SUM(BLE_TP(TP,BLE)$BLE_OPR(BLE,ENC_G),
# *    -1 * BLND(TP,BLE,ENC_G)
# *  ) +
# *  SUM(BLE_OPR(BLE,OPR)$(BLE_INP(BLE,ENC_G) * BLE_TP(TP,BLE)),
# *    -(BL_INP(BLE,ENC_G) + SUM(BLE_SPEOPR(BLE,SPE,OPR)$BLE_SPEINP(BLE,SPE,ENC_G),
# *      TBL_INP(BLE,SPE,ENC_G,TP))) * BLND(TP,BLE,OPR)
# *  )
# *
# *
# *GG* V1.5r add blending requirements for electricity
# *  SUM(BLE_OPR(BLE,OPR)$BLE_INP(BLE,ELC),
# *    - BALE_BLE(TP,BLE,ELC,Z,'D') * BLND(TP,BLE,OPR)
# *  )
# *
# *----------------------------------------------------------------------------*
# * EMISSIONS
# *----------------------------------------------------------------------------*
# *  Emissions due to BLENDing
# *  + SUM(BLE_OPR(BLE,OPR),
# *        ENV_BL(ENV,BLE,OPR,TP) * BLND(TP,BLE,OPR))
# *
# *----------------------------------------------------------------------------*
# * PEAKING
# *----------------------------------------------------------------------------*
# *  add blending requirements
# *  SUM(BLE_OPR(BLE,OPR),
# *    - EPK_BLE(TP,BLE,ELC,Z) * BLND(TP,BLE,OPR)
# *  )


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqblndMod(GamsClass):
    """Translation unit for eqblnd.mod."""

    module_name: str = "eqblnd_mod"
    gams_source: str = "eqblnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*============================================================================*
*  BLENDing equation by type                                                 *
*============================================================================*
  EQ{self.arg1}_BLND(BLE_TP({self.env.r_t},BLE),SPE{self.env.swx})$({self.env.swtx}(BL_TYPE(R,BLE,SPE)={self.arg2}))..
  SUM(OPR$BLE_OPR(R,BLE,OPR), (BL_COM(R,BLE,OPR,SPE) - BL_SPEC(R,BLE,SPE)) *
                              RU_CVT(R,BLE,SPE,OPR) * {self.env.var}_BLND(R,T,BLE,OPR {self.env.sow}))
  ={self.arg1}=
  0;
""",
        )
