# initmty_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * INIT DECLARATIONS FOR THE DSC EXTENSION
# *=============================================================================
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyDsc(GamsClass):
    """Translation unit for initmty.dsc."""

    # Instance attributes
    module_name: str = "initmty_dsc"
    gams_source: str = "initmty.dsc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase = "init"
        self.env.set_global("dsc", "YES")
        if not self.env.dsc == "YES":
            raise Exception("Activation of DSC extension failed")

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=r"""
* Sets and parameters for discrete capacity extension
SET       UNIT                                   'Number of different units'           / 0*100 /;
SET       PRC_DSCNCAP(R,P)                       'Processes with discrete capacity additions';
PARAMETER NCAP_DISC(R,ALLYEAR,P,UNIT)            'Unit size of discrete capacity addition';
PARAMETER NCAP_SEMI(R,ALLYEAR,P)                 'Semi-continuous capacity, lower bound'      //;
*PARAMETER NCAP_CSTD(REG,ALLYEAR,PRC,CUR,UNIT)   'Investment cost of unit'                    //;
*PARAMETER NCAP_FOMD(REG,ALLYEAR,PRC,CUR,UNIT)   'Fixed operating and maintenace cost of unit'//;
""",
        )
