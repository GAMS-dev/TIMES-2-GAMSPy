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
from typing import TYPE_CHECKING, Literal

from gamspy import Sum

from core.base_class import GamsClass
from core.utils import generate_equation

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqblndMod(GamsClass):
    """Translation unit for eqblnd.mod."""

    module_name: str = "eqblnd_mod"
    gams_source: str = "eqblnd.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        equation_type: Literal["L", "E", "N", "G"],
        blnd_code: int,
    ):
        self.env = env.fork()
        self.tc = tc
        self.equation_type: Literal["L", "E", "N", "G"] = equation_type
        self.blnd_code: int = blnd_code
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        """
        *============================================================================*
        *  BLENDing equation by type                                                 *
        *============================================================================*
        """
        g = self.tc

        r, t, spe = g.r, g.t, g.spe
        Ble, Opr = g.Ble, g.Opr

        r_t = self.env.r_t_GP
        swx = self.env.swx_GP
        sow = self.env.sow_GP
        swtx = self.env.swtx_GP

        VAR_BLND = g.get_variable(f"{self.env.var}_BLND")
        eq = g.get_equation(f"EQ{self.equation_type}_BLND")

        eq[g.BleTp[*r_t, Ble], spe, *swx].where[
            swtx & (g.bl_type[r, Ble, spe] == self.blnd_code)
        ] = generate_equation(
            Sum(
                Opr.where[g.BleOpr[r, Ble, Opr]],
                (g.bl_com[r, Ble, Opr, spe] - g.bl_spec[r, Ble, spe])
                * g.ru_cvt[r, Ble, spe, Opr]
                * VAR_BLND[r, t, Ble, Opr, *sow],
            ),
            self.equation_type,
            0,
        )
