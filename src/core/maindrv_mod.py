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
import re
from typing import TYPE_CHECKING

from core.coef_ext_abs import CoefExtAbs
from core.coef_ext_cli import CoefExtCli
from core.coef_ext_etl import CoefExtEtl
from core.coef_ext_vda import CoefExtVda
from core.coefmain_mod import CoefmainMod
from core.eqmain_mod import EqmainMod
from core.equ_ext_abs import EquExtAbs
from core.equ_ext_cli import EquExtCli
from core.equ_ext_dsc import EquExtDsc
from core.equ_ext_ecb import EquExtEcb
from core.equ_ext_etl import EquExtEtl
from core.equ_ext_ier import EquExtIer
from core.equ_ext_msa import EquExtMsa
from core.equ_ext_vda import EquExtVda
from core.err_stat_mod import ErrStatMod
from core.init_ext_abs import InitExtAbs
from core.init_ext_dsc import InitExtDsc
from core.init_ext_vda import InitExtVda
from core.main_ext_mod import include_extension
from core.mod_vars_abs import ModVarsAbs
from core.mod_vars_cli import ModVarsCli
from core.mod_vars_dsc import ModVarsDsc
from core.mod_vars_etl import ModVarsEtl
from core.mod_vars_mod import ModVarsMod
from core.mod_vars_msa import ModVarsMsa
from core.mod_vars_tm import ModVarsTm
from core.ppm_ext_cli import PpmExtCli
from core.ppm_ext_dsc import PpmExtDsc
from core.ppm_ext_ecb import PpmExtEcb
from core.ppm_ext_mlf import PpmExtMlf
from core.ppm_ext_vda import PpmExtVda
from core.ppmain_mod import PpmainMod
from core.readbprice_mod import ReadbpriceMod
from core.setglobs_gms import SetglobsGms
from core.stages_stc import StagesStc

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

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
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
        self.include(SetglobsGms(tc=self.tc, env=self.env, arg1="1"))
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
                self.include(ReadbpriceMod(tc=self.tc, env=self.env))

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

        if self.tc.defined("REG_FIXT"):
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
            ErrStatMod(tc=self.tc, env=self.env, arg1=arg1, arg2=arg2, arg3=arg3)
        )

        # perform preprocessor tasks
        if self.env.extend != "":
            init_extensions = {
                "ABS": InitExtAbs,
                "DSC": InitExtDsc,
                "VDA": InitExtVda,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=init_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )

        self.include(PpmainMod(tc=self.tc, env=self.env, arg1=self.arg1))

        if self.env.intext_only.upper() == "YES":  # SKIP TO END
            return

        if self.env.extend != "":
            ppm_extensions = {
                "CLI": PpmExtCli,
                "DSC": PpmExtDsc,
                "ECB": PpmExtEcb,
                "MLF": PpmExtMlf,
                "VDA": PpmExtVda,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=ppm_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )

        # *-----------------------------------------------------------------------------
        # * dump out the user/system data structures
        # *-----------------------------------------------------------------------------
        if self.env.debug == "YES":
            self.tc.container.write("DATADUMP.gdx")

        # * Set the main controls for stochastic mode
        if self.env.stages.upper() == "YES":
            self.include(StagesStc(tc=self.tc, env=self.env))
        if self.env.stages == "YES":
            self.apply_inline_sets(set_string=self.env.sw_tags)
        else:
            self.apply_inline_sets(set_string=self.env.sw_notags)

        # *-----------------------------------------------------------------------------
        # * build the coefficients
        # *-----------------------------------------------------------------------------
        if self.env.mid_year.upper() == "YES":
            self.env.set_scoped("discshift", "0.5")
        self.include(CoefmainMod(tc=self.tc, env=self.env, arg1=self.arg1))

        if self.env.extend != "":
            coef_extensions = {
                "ABS": CoefExtAbs,
                "CLI": CoefExtCli,
                "ETL": CoefExtEtl,
                "VDA": CoefExtVda,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=coef_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )

        # *-----------------------------------------------------------------------------
        # * establish model (use different .ext?)
        # *-----------------------------------------------------------------------------
        src = self.env.src.upper()
        if src == "ABS":
            self.include(ModVarsAbs(tc=self.tc, env=self.env))
        elif src == "CLI":
            self.include(ModVarsCli(tc=self.tc, env=self.env))
        elif src == "DSC":
            self.include(ModVarsDsc(tc=self.tc, env=self.env))
        elif src == "ETL":
            self.include(ModVarsEtl(tc=self.tc, env=self.env))
        elif src == "MOD":
            self.include(ModVarsMod(tc=self.tc, env=self.env))
        elif src == "MSA":
            self.include(ModVarsMsa(tc=self.tc, env=self.env))
        elif src == "TM":
            self.include(ModVarsTm(tc=self.tc, env=self.env))
        else:
            raise Exception(f"Unknown extension {src} for mod_vars<ext>.py.")

        if self.env.extend != "":
            mod_var_extensions = {
                "ABS": ModVarsAbs,
                "CLI": ModVarsCli,
                "DSC": ModVarsDsc,
                "ETL": ModVarsEtl,
                "MOD": ModVarsMod,
                "MSA": ModVarsMsa,
                "TM": ModVarsTm,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=mod_var_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )

        self.include(EqmainMod(tc=self.tc, env=self.env, arg1=self.arg1))

        if self.env.extend != "":
            equ_extensions = {
                "ABS": EquExtAbs,
                "CLI": EquExtCli,
                "DSC": EquExtDsc,
                "ECB": EquExtEcb,
                "ETL": EquExtEtl,
                "IER": EquExtIer,
                "MLF": "",
                "MSA": EquExtMsa,
                "VDA": EquExtVda,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=equ_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )
        # TODO: Keep translating

    def apply_inline_sets(self: MainDrvMod, set_string: str) -> None:
        """
        Parses a string of consecutive GAMS SET, SETGLOBAL, or SETLOCAL commands
        and applies them to the compile environment.
        """
        # Regex breakdown:
        # 1. `(?i)`                      -> Makes the entire match case-insensitive
        # 2. `(SETGLOBAL|SETLOCAL|SET)`  -> Capture Group 1: The exact command used
        # 3. `\s+`                       -> Matches whitespace
        # 4. `(\w+)`                     -> Capture Group 2: The key (e.g., EQ, VAR)
        # 5. `\s+`                       -> Matches whitespace before the value
        # 6. `('[^']*'|"[^"]*"|\S+)`     -> Capture Group 3: The value (single quotes, double quotes, or unquoted)
        pattern = r"(?i)(SETGLOBAL|SETLOCAL|SET)\s+(\w+)\s+('[^']*'|\"[^\"]*\"|\S+)"

        # re.findall returns a list of tuples: [('SET', 'EQ', "'EQ'"), ('SETGLOBAL', 'VAR', '"VAR"'), ...]
        matches = re.findall(pattern, set_string)

        for command, key, value in matches:
            # Standardize the key to lowercase for your env dictionary
            clean_key = key.lower()

            # Strip both single and double surrounding quotes (if they exist)
            clean_value = value.strip("'\"")

            # Route to the correct env method based on the command
            command_upper = command.upper()
            if command_upper == "SETGLOBAL":
                self.env.set_global(clean_key, clean_value)
            elif command_upper == "SET":
                self.env.set_scoped(clean_key, clean_value)
            elif command_upper == "SETLOCAL":
                self.env.set_local(clean_key, clean_value)
            else:
                raise Exception(command_upper, "not in [SETGLOBAL, SET, SETSCOPED]")
