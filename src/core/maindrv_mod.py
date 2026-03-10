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

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from core import (
    err_stat_mod,
    init_ext_abs,
    init_ext_dsc,
    init_ext_vda,
    readbprice_mod,
    setglobs_gms,
)

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

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.tc = tc
        self._sub_modules = {}
        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="maindrv_mod_start")
        self.compile()

    def compile(self) -> None:
        self.env.set_local("src", self.arg1)

        if self.tc.test_run:
            self.tc.save_test_state(env=self.env, checkpoint="setglobs_gms_start")
        self.include(setglobs_gms.SetglobsGms(tc=tc, env=self.env, arg1=1))
        if self.tc.test_run:
            self.tc.save_test_state(env=self.env, checkpoint="setglobs_gms_end")

        self.env.set_scoped("model_name", "TIMES")

        if self.env.micro.upper() == "YES":
            if self.env.timesed == "0":
                self.env.set_scoped("timesed", "YES")

        if self.env.macro.upper() == "YES":
            self.env.set_scoped("macro", "YES")
            self.env.set_scoped("timesed", "0")

        if os.name != "nt":
            self.env.set_scoped("model_name", "times")

        if self.env.timesed.upper() != "NO":
            if self.env.timesed != "0":
                self.include(readbprice_mod.ReadpriceMod(tc=self.tc, env=self.env))

        # TODO: $   %MX% SETGLOBAL MX --> How to handle %MX% here?
        self.env.set_global("mx", "")

        if self.env.macro.upper() == "YES":
            self.env.set_scoped("model_name", "TIMES_MACRO")
            self.env.set_local("src", "tm")

        # Stochastic & sensitivity analysis controls
        if self.env.stages.upper() == "YES":
            self.env.set_scoped("stages", "YES")
        if self.env.sensis.upper() == "YES":
            self.env.set_scoped("stages", "Yes")
        if self.env.spines.upper() == "YES":
            self.env.set_scoped("stages", "YES")
        if self.env.stages == "YES":
            self.env.set_scoped("sensis", "NO")
            self.env.set_scoped("objann", "NO")

        # Stepped TIMES solution controls
        if self.env.is_set("timestep"):
            self.env.set_global("stepped", "+")
        self.env.set_scoped("r_t", "R,T")
        self.env.set_scoped("tx", "T")
        self.env.set_scoped("r_v_t", "R,V,T")
        self.env.set_scoped("rtpx", "")

        if self.env.is_set("stepped"):
            self.env.set_scoped("r_t", "R,SUBT(T)")
            self.env.set_scoped("tx", "SUBT(T)")
            self.env.set_scoped("r_v_t", "R,V,SUBT(T)")

        if "REG_FIXT" in self.tc.container.listSymbols() and self.tc.container["REG_FIXT"].number_records:
            r_t = self.env.r_t
            r_v_t = self.env.r_v_t
            self.env.set_scoped("r_t", f"RT_PP({r_t})")
            self.env.set_scoped("r_v_t", f"RVT({r_v_t})")
            self.env.set_scoped("rtpx", "X")

        if self.tc.test_run:
            self.tc.save_test_state(
                env=self.env, checkpoint="maindrv_mod_prior_err_stat_mod"
            )

        arg1 = "$IF NOT ERRORFREE"
        arg2 = "ABORT"
        arg3 = "*** ERRORS IN INPUT DATA/COMPILE ***"
        self.include(
            err_stat_mod.ErrStatMod(
                tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3
            )
        )

        # perform preprocessor tasks
        if self.env.extend != "":
            extensions = {
                "ABS": init_ext_abs.InitExtAbs,
                "DSC": init_ext_dsc.InitExtDsc,
                "VDA": init_ext_vda.InitExtVda,
            }
            for ext in self.env.extend.split(" "):
                self.include(
                    extensions[ext](
                        tc=self.tc, env=self.env, source="maindrv", arg1=ext, arg2="maindrv"
                    )
                )
