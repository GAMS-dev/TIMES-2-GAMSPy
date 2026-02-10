# maindrv_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MAINDRV.EXT is the main driver hooking together the various core model code *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
# *  Questions/Comments:
# *   - BATINCLUDE calls should all be with lower case file names for UNIX
# *   - Move the NO_EMTY to the *.RUN (user controlled) for dumpdata control
# *     and make YES/NO the expected value in DUMPPUT
# *   - [AL]: support for TIMES extension modules added
# *-----------------------------------------------------------------------------

import logging
from typing import TYPE_CHECKING

from core import setglobs_gms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class MainDrvMod(GamsClass):
    """Translation unit for maindrv.mod."""

    # Instance attributes
    module_name: str = "maindrv_mod"
    gams_source: str = "maindrv.mod"

    def __init__(self, tc: "TimesModelClass", env: "CompileEnvironment", arg1: str):
        self.env = env.fork()
        self.arg1 = arg1
        self._sub_modules = {}
        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="maindrv_mod_start")
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        self.env.set_local("src", self.arg1)

        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="setglobs_gms_start")
        self.include(setglobs_gms.SetglobsGms(tc=tc, env=self.env, arg1=1))
        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="setglobs_gms_end")

        self.env.set_scoped("model_name", "TIMES")
