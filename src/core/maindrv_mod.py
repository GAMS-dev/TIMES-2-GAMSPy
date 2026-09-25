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
from typing import TYPE_CHECKING, Literal

from gamspy import Set

from core.base_class import GamsClass
from core.bndmain_mod import BndmainMod
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
from core.equ_ext_mlf import EquExtMlf
from core.equ_ext_msa import EquExtMsa
from core.equ_ext_vda import EquExtVda
from core.err_stat_mod import ErrStatMod
from core.init_ext_abs import InitExtAbs
from core.init_ext_dsc import InitExtDsc
from core.init_ext_vda import InitExtVda
from core.main_ext_mod import include_extension
from core.mod_equa_mod import mod_equa_mod
from core.mod_equa_tm import mod_equa_tm
from core.mod_ext_abs import mod_ext_abs
from core.mod_ext_cli import mod_ext_cli
from core.mod_ext_dsc import mod_ext_dsc
from core.mod_ext_etl import mod_ext_etl
from core.mod_ext_ier import mod_ext_ier
from core.mod_ext_vda import mod_ext_vda
from core.mod_vars_abs import ModVarsAbs
from core.mod_vars_cli import ModVarsCli
from core.mod_vars_dsc import ModVarsDsc
from core.mod_vars_etl import ModVarsEtl
from core.mod_vars_mod import ModVarsMod
from core.mod_vars_msa import ModVarsMsa
from core.mod_vars_tm import ModVarsTm
from core.pp_qack_mod import PpQackMod
from core.ppm_ext_cli import PpmExtCli
from core.ppm_ext_dsc import PpmExtDsc
from core.ppm_ext_ecb import PpmExtEcb
from core.ppm_ext_mlf import PpmExtMlf
from core.ppm_ext_vda import PpmExtVda
from core.ppmain_mod import PpmainMod
from core.readbprice_mod import ReadbpriceMod
from core.rptmain_mod import RptmainMod
from core.rptmain_rpt import RptmainRpt
from core.rptmain_stc import RptmainStc
from core.rptmain_tm import RptmainTm
from core.setglobs_gms import SetglobsGms
from core.solve_mod import SolveMod
from core.solve_msa import SolveMsa
from core.solve_stc import SolveStc
from core.solve_stp import SolveStp
from core.spoint_mod import SpointMod
from core.stages_stc import StagesStc
from core.utils import apply_sw_notags, apply_sw_tags
from core.wrtbprice_mod import WrtbpriceMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class MainDrvMod(GamsClass):
    """Translation unit for maindrv.mod."""

    # Instance attributes
    module_name: str = "maindrv_mod"
    gams_source: str = "maindrv.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: Literal["mod"]
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        if tc.test_run:
            tc.save_test_state(env=self.env, checkpoint="maindrv_mod_start")
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        self.env.set_local("src", self.arg1)
        self.include(SetglobsGms(tc=self.tc, env=self.env, arg1="1"))

        self.env.set_scoped("model_name", "TIMES")

        if self.env.micro.upper() == "YES" and self.env.timesed == "0":
            self.env.set_scoped("timesed", "YES")

        if self.env.macro.upper() == "YES":
            self.env.set_scoped("macro", "YES")
            self.env.set_scoped("timesed", "0")

        if os.name != "nt":
            self.env.set_scoped("model_name", "times")

        if self.env.timesed.upper() != "NO" and self.env.timesed != "0":
            self.include(ReadbpriceMod(tc=self.tc, env=self.env))

        # $   %MX% SETGLOBAL MX
        # mx_GP carries the switch reassignment deferred by ReadbpriceMod (see
        # readbprice_mod.py) as flat (name, value) pairs; replay it here, then reset.
        mx_gp = self.env.mx_GP
        for name, value in zip(mx_gp[0::2], mx_gp[1::2], strict=False):
            self.env.set_scoped(name, value)

        self.env.set_global("mx", "")
        self.env.set_global("mx_GP", ())

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
        self.env.set_scoped("r_t_GP", (g.r, g.t))
        self.env.set_scoped("tx", "T")
        self.env.set_scoped("tx_GP", (g.t,))
        self.env.set_scoped("r_v_t", "R,V,T")
        self.env.set_scoped("r_v_t_GP", (g.r, g.v, g.t))
        self.env.set_scoped("rtpx", "")

        # moved symbol declarion from pp_main.py
        g.Subt = Set(m, name="SUBT", domain=[g.t])
        if self.env.is_set("stepped"):
            self.env.set_scoped("r_t", "R,SUBT(T)")
            self.env.set_scoped("r_t_GP", (g.r, g.Subt[g.t]))
            self.env.set_scoped("tx", "SUBT(T)")
            self.env.set_scoped("tx_GP", (g.Subt[g.t],))
            self.env.set_scoped("r_v_t", "R,V,SUBT(T)")
            self.env.set_scoped("r_v_t_GP", (g.r, g.v, g.Subt[g.t]))

        if self.tc.defined("REG_FIXT"):
            r_t = self.env.r_t
            r_v_t = self.env.r_v_t
            self.env.set_scoped("r_t", f"RT_PP({r_t})")
            self.env.set_scoped("r_t_GP", g.RtPp[*self.env.r_t_GP])
            self.env.set_scoped("r_v_t", f"RVT({r_v_t})")
            self.env.set_scoped("r_v_t_GP", (g.Rvt[*self.env.r_v_t_GP],))
            self.env.set_scoped("rtpx", "X")

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
            self.tc.enqueue(self.exec_datadump)

        # * Set the main controls for stochastic mode
        if self.env.stages.upper() == "YES":
            self.include(StagesStc(tc=self.tc, env=self.env))
        if self.env.stages == "YES":
            apply_sw_tags(env=self.env, g=g)
        else:
            apply_sw_notags(env=self.env)

        # *-----------------------------------------------------------------------------
        # * build the coefficients
        # *-----------------------------------------------------------------------------
        if self.env.mid_year.upper() == "YES":
            self.env.set_scoped("discshift", 0.5)
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
            raise KeyError(f"Unknown extension {src} for mod_vars<ext>.py.")

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
            # Order matches the canonical %EXTEND% assembly in initmty.mod
            equ_extensions = {
                "ECB": EquExtEcb,
                "MSA": EquExtMsa,
                "MLF": EquExtMlf,
                "ETL": EquExtEtl,
                "CLI": EquExtCli,
                "DSC": EquExtDsc,
                "VDA": EquExtVda,
                "ABS": EquExtAbs,
                "IER": EquExtIer,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=equ_extensions,
                requested_exts=requested_exts,
                source="maindrv",
            )

        src = self.env.src.upper()
        def_prc_simv = self.tc.defined("PRC_SIMV")
        def_dam_cost = self.tc.defined("DAM_COST")
        def_vnret = self.tc.defined("VNRET")

        if src == "MOD":
            model_name = "TIMES"
            equations = mod_equa_mod(
                tc=self.tc,
                arg1="",
                stages=self.env.stages,
                eq=self.env.eq,
                timesed=self.env.timesed,
                objann=self.env.objann,
                var_uc=self.env.var_uc,
                damage=self.env.damage,
                spines=self.env.spines,
                def_prc_simv=def_prc_simv,
                def_dam_cost=def_dam_cost,
                def_vnret=def_vnret,
            )
        elif src == "TM":
            model_name = "TIMES_MACRO"
            equations = mod_equa_tm(
                tc=self.tc,
                merge=self.env.merge,
                eq=self.env.eq,
                timesed=self.env.timesed,
                var_uc=self.env.var_uc,
                damage=self.env.damage,
                spines=self.env.spines,
                macro=self.env.macro,
                nonlp=self.env.nonlp,
                def_prc_simv=def_prc_simv,
                def_dam_cost=def_dam_cost,
                def_vnret=def_vnret,
            )
        else:
            raise KeyError(f"Unknown extension {src} for mod_equa_<ext>.py.")

        def_uc_flobet = self.tc.defined("UC_FLOBET")
        def_com_cstbal = self.tc.defined("COM_CSTBAL")
        def_gr_vargen = self.tc.defined("GR_VARGEN")
        def_rtc_ms = self.tc.defined("RTC_MS")
        def_gg_mm = self.tc.defined("GG_MM")

        if self.env.merge.upper() != "YES" and self.env.extend != "":
            requested_exts = set(self.env.extend.split())
            if "ABS" in requested_exts:
                equations.extend(mod_ext_abs(tc=self.tc, obmac=self.env.obmac))
            if "CLI" in requested_exts:
                equations.extend(mod_ext_cli(tc=self.tc, eq=self.env.eq))
            if "DSC" in requested_exts:
                equations.extend(
                    mod_ext_dsc(
                        tc=self.tc,
                        eq=self.env.eq,
                        dsc=self.env.dsc,
                        solmip=self.env.solmip,
                    )
                )
            if "ETL" in requested_exts:
                equations.extend(mod_ext_etl(tc=self.tc, eq=self.env.eq))
            if "IER" in requested_exts:
                equations.extend(mod_ext_ier(tc=self.tc, chp_mode=self.env.chp_mode))
            if "VDA" in requested_exts:
                equations.extend(
                    mod_ext_vda(
                        tc=self.tc,
                        eq=self.env.eq,
                        obmac=self.env.obmac,
                        duc=self.env.duc,
                        solmip=self.env.solmip,
                        ecb=self.env.ecb,
                        powerflo=self.env.powerflo,
                        def_uc_flobet=def_uc_flobet,
                        def_com_cstbal=def_com_cstbal,
                        def_gr_vargen=def_gr_vargen,
                        def_rtc_ms=def_rtc_ms,
                        def_gg_mm=def_gg_mm,
                    )
                )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
MODEL {model_name} / {", ".join([equation.name for equation in equations])} /;
""",
        )

        # establish bounds
        self.include(BndmainMod(tc=self.tc, env=self.env, arg1=self.arg1, arg2="0"))

        # do quality assurance checks
        self.include(PpQackMod(tc=self.tc, env=self.env, arg1=self.arg1))

        self.include(
            ErrStatMod(
                tc=self.tc,
                env=self.env,
                arg1="$IF NOT ERRORFREE",
                arg2="ABORT",
                arg3="*** ERRORS IN GAMS COMPILE ***",
            )
        )
        self.include(
            ErrStatMod(
                tc=self.tc,
                env=self.env,
                arg1="ABORT",
                arg2="EXECERROR",
                arg3="*** ERRORS IN GAMS EXECUTION ***",
            )
        )

        self.include(SpointMod(tc=self.tc, env=self.env, arg1="1"))

        if self.env.rpoint == "NO":
            # *-----------------------------------------------------------------------------
            # * solve the appropriate model & report solver status
            # *-----------------------------------------------------------------------------
            self.env.set_local("ext", self.arg1)
            if self.env.stages.upper() == "YES":
                self.env.set_local("ext", "stc")
            if self.env.is_set("stepped"):
                self.env.set_local("ext", "stp")
            if self.env.merge.upper() == "YES":
                self.env.set_local("ext", "mrg")

            ext = self.env.ext
            if ext == "mod":
                self.include(
                    SolveMod(
                        tc=self.tc,
                        env=self.env,
                        arg1=self.arg1,
                        model_name=model_name,
                        equations=equations,
                    )
                )
            elif ext == "stc":
                self.include(
                    SolveStc(
                        tc=self.tc,
                        env=self.env,
                        arg1=self.arg1,
                        model_name=model_name,
                        equations=equations,
                    )
                )
            elif ext == "stp":
                self.include(
                    SolveStp(
                        tc=self.tc,
                        env=self.env,
                        arg1=self.arg1,
                        model_name=model_name,
                        equations=equations,
                    )
                )
            elif ext == "msa":
                self.include(SolveMsa(tc=self.tc, env=self.env, arg1=self.arg1))

            if self.env.solve_now == "NO":
                return

        # *-----------------------------------------------------------------------------
        # * produce the reports
        # *-----------------------------------------------------------------------------
        ext = self.arg1.upper()
        if ext == "MOD":
            self.include(
                RptmainMod(
                    tc=self.tc,
                    env=self.env,
                    arg1=self.arg1,
                    arg2="NO_EMTY",
                    model_name=model_name,
                    equations=equations,
                )
            )
        elif ext == "RPT":
            self.include(
                RptmainRpt(
                    tc=self.tc,
                    env=self.env,
                    arg1=self.arg1,
                    arg2="NO_EMTY",
                )
            )
        elif ext == "STC":
            self.include(
                RptmainStc(
                    tc=self.tc,
                    env=self.env,
                    arg1=self.arg1,
                    arg2="NO_EMTY",
                    model_name=model_name,
                )
            )
        elif ext == "TM":
            self.include(
                RptmainTm(
                    tc=self.tc,
                    env=self.env,
                    arg1=self.arg1,
                    arg2="NO_EMTY",
                )
            )
        else:
            raise ValueError(f"Unexpected extension {self.arg1} for rptmain.<ext>.")

        if self.env.timesed != "0" and self.env.timesed != "YES":
            self.include(WrtbpriceMod(tc=self.tc, env=self.env))

        if self.env.is_set("spoint"):
            self.include(SpointMod(tc=self.tc, env=self.env, arg1="0"))

        # *-----------------------------------------------------------------------------
        # * do an check on compile/execute errors from reports
        # *-----------------------------------------------------------------------------
        self.include(
            ErrStatMod(
                tc=self.tc,
                env=self.env,
                arg1="$IF NOT ERRORFREE",
                arg2="ABORT",
                arg3="*** ERRORS IN GAMS COMPILE ***",
            )
        )
        self.include(
            ErrStatMod(
                tc=self.tc,
                env=self.env,
                arg1="ABORT",
                arg2="EXECERROR",
                arg3="*** ERRORS IN GAMS EXECUTION ***",
            )
        )

    def exec_datadump(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code='execute_unload "DATADUMP.gdx";',
        )
