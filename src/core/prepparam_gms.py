# prepparam_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * PREPPAR : Prepare parameters for preprocessing
# * Description: Non-default interpolation/extrapolation according to user option
# *              DFUNC = -1-> no interpolation, 0-> default action, 10->intra-period
# *              DFUNC = +1-> interp., 2->interp.+EPS, 3->interp.+extrap.
# *              DFUNC >999 -> exponential interpolation beyond year DFUNC
# * Parameters:
# *      %1 - table name
# *      %2 - control set 1
# *      %3 - control set 2
# *      %4 - UNCD7 residual dimension
# *      %5 - MODLYEAR or MILESTONYR depending on parameter
# *      %6 - RTP controlling the assignment to the MODLYEARs
# *      %7 - Option to prohibit extrapolation (1 for other than cost parameters)
# *******************************************************************************


import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepparamGms(GamsClass):
    """Translation unit for prepparam.gms."""

    # Instance attributes
    module_name: str = "prepparam_gms"
    gams_source: str = "prepparam.gms"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)
