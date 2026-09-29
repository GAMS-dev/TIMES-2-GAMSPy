# rptmain_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTMAIN.MOD is the main driver for the report writer                        *
# *   arg1 - mod or v# for the source code to be used                             *
# *=============================================================================*
# *GaG Questions/Comments:
# *  -  COM, PRC descriptions need to be taken from the COM_GMAP/PRC_MAP Sets
# *-----------------------------------------------------------------------------
# *-----------------------------------------------------------------------------
# * dump solution if requested

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Equation

from core.atlearn_etl import AtlearnEtl
from core.base_class import GamsClass
from core.dumpsol_mod import DumpsolMod
from core.main_ext_mod import include_extension
from core.rpt_dam_mod import rpt_dam_mod_GP
from core.rpt_ext_cli import RptExtCli
from core.rpt_ext_ecb import RptExtEcb
from core.rpt_ext_ier import RptExtIer
from core.rpt_ext_mlf import RptExtMlf
from core.rpt_ext_msa import RptExtMsa
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.rptmain_rpt import RptmainRpt
from core.rptmain_stc import RptmainStc
from core.rptmain_tm import RptmainTm
from core.solputta_ans import SolputtaAns
from core.solsetv_v3 import SolsetvV3

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptmainMod(GamsClass):
    """Translation unit for rptmain.mod."""

    # Instance attributes
    module_name: str = "rptmain_mod"
    gams_source: str = "rptmain.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
        model_name: str,
        equations: list[Equation],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.model_name = model_name
        self.equations = equations
        self.compile()

    def compile(self) -> None:
        g = self.tc

        # rpt_dam_mod is reached via rptmain.mod:38 and SETLOCAL SOLVEDA 1
        # below is local to this file only. Snapshot it before the override so
        # exec_rpt_dam_mod gets scoped value.
        rpt_dam_solveda = self.env.solveda

        if self.env.stages != "YES" and self.env.dumpsol == "YES":
            self.include(DumpsolMod(self.tc, self.env, arg1=self.arg1))

        if self.env.vda.upper() == "YES":
            self.env.set_local("solveda", "1")

        if self.env.sensis.upper() != "YES":
            if self.env.solveda != "NO":
                self.include(SolsetvV3(self.tc, self.env))

            skip_to_finish = False
            if self.env.macro.upper() == "YES":
                pass  # GOTO to OTHER_REP (bypasses VAR_NTX check)
            elif self.tc.defined("VAR_NTX"):
                skip_to_finish = True  # GOTO to FINISH
            elif self.env.stages.upper() == "YES":
                pass  # GOTO to OTHER_REP

            if not skip_to_finish:
                # moved up from rptlite.rpt
                g.ww = Alias(g.container, name="WW", alias_with=g.allsow)

                if self.env.macro.upper() != "YES" and self.env.stages.upper() != "YES":
                    if self.env.solveda.upper() == "YES":
                        self.include(RptmainRpt(self.tc, self.env, arg1="", arg2=""))
                    elif self.env.solveda.upper() == "1":
                        self.include(
                            RptliteRpt(
                                self.tc,
                                self.env,
                                config=RptliteRptConfig(
                                    arg1="S", arg2=(self.tc.ww,), arg3=("'1',",)
                                ),
                            )
                        )

                if self.env.macro == "YES":
                    self.include(RptmainTm(self.tc, self.env))

                #  If running stochastics, streamline reports
                if self.env.stages.upper() == "YES":
                    # rptmain.mod:32: $BATINCLUDE rptmain.stc SOW %SWS% "'1'" ",'1')"
                    self.include(
                        RptmainStc(
                            self.tc,
                            self.env,
                            arg1="SOW",
                            arg2=self.env.sws,
                            model_name=self.model_name,
                            arg1_GP=(self.tc.Sow,),
                            arg3="'1'",
                            arg4=",'1')",
                            arg3_GP=("1",),
                        )
                    )

                if self.env.etl.upper() == "YES":
                    self.include(AtlearnEtl(self.tc, self.env))

                if self.tc.defined("DAM_COST"):
                    self.tc.enqueue(
                        self.exec_rpt_dam_mod,
                        solveda=rpt_dam_solveda,
                    )

        # LABEL FINISH
        if self.env.extend != "":
            rpt_extensions = {
                "CLI": RptExtCli,
                "ECB": RptExtEcb,
                "IER": RptExtIer,
                "MLF": RptExtMlf,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=rpt_extensions,
                requested_exts=requested_exts,
                source="rptmain",
            )
            # RptExtMsa (unlike its siblings) needs the model's equation list
            # to re-solve via SolveStp under FIXBOH, so it can't go through
            # include_extension's generic (tc, env, arg1, arg2) call shape.
            if "MSA" in requested_exts:
                self.include(
                    RptExtMsa(
                        tc=self.tc,
                        env=self.env,
                        model_name=self.model_name,
                        equations=self.equations,
                        arg1="MSA",
                        arg2="rptmain",
                    )
                )

        if self.env.solans.upper() == "YES":
            self.include(
                SolputtaAns(self.tc, self.env, arg1="S", arg2="WW,", arg3="SOW,")
            )

        if self.env.vda.upper() == "YES":
            self.include(SolsetvV3(self.tc, self.env, "FINISHUP"))

    def exec_rpt_dam_mod(self: RptmainMod, solveda: str) -> None:
        rpt_dam_mod_GP(self.tc, self.env, solveda=solveda)
