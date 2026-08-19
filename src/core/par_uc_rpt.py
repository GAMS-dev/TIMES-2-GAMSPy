# par_uc_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *====================================================================
# * Par_uc.rpt : reporting parameters for UCs (no STAGES/SENSIS)
# * arg1 - parameter suffix
# * arg2 - equation prefix
# *--------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def declare_par_uc_rpt_params(module: GamsClass) -> None:
    """Declare PAR_RTUS/PAR_URTS immediately (init phase).

    PAR_RTUS/PAR_URTS are declarative statements -- in real GAMS they are part
    of the single compile pass and exist regardless of when %BATINCLUDE
    par_uc.rpt happens to be lexically reached. Callers that embed
    par_uc_rpt()'s output in "run"-phase code must call this once themselves
    beforehand (rather than letting the declaration ride along with the rest
    of the block).
    """
    module.tc.add_gams_code(
        module=module,
        phase="init",
        code="""
  PARAMETER PAR_RTUS(R,YEAR,UC_N,S) //;
  PARAMETER PAR_URTS(UC_N,R,YEAR,S) //;
""",
    )


class ParUcRpt(GamsClass):
    """Translation unit for par_uc.rpt."""

    # Instance attributes
    module_name: str = "par_uc_rpt"
    gams_source: str = "par_uc.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.compile()

    def compile(self) -> None:
        declare_par_uc_rpt_params(self)
        self.tc.enqueue(
            self.exec_par_uc_rpt,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
        )

    def exec_par_uc_rpt(
        self: ParUcRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=par_uc_rpt(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
            ),
        )


def par_uc_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
) -> str:
    return rf"""
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE','NONE','NONE') $= {arg2}_UC.M(UC_N);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,'NONE')      $= {arg2}_UCT.M(UC_N,T);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,S)           $= {arg2}_UCTS.M(UC_N,T,S);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,'NONE')      $= {arg2}_UCSU.M(UC_N,T);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,S)           $= {arg2}_UCSUS.M(UC_N,T,S);
* Handle shuffled indexes
  PAR_RTUS(R,'0',UC_N,ANNUAL)             $= {arg2}_UCR.M(R,UC_N);
  PAR_RTUS(R,T,UC_N,ANNUAL)               $= {arg2}_UCRT.M(R,T,UC_N);
  PAR_RTUS(R,T,UC_N,ANNUAL)               $= {arg2}_UCRSU.M(R,T,UC_N);
  OPTION PAR_URTS<PAR_RTUS,CLEAR=PAR_RTUS;
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,'NONE','NONE')      $= PAR_URTS(UC_N,R,'0','ANNUAL');
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,T,'NONE')           $= PAR_URTS(UC_N,R, T, 'ANNUAL')*(1/COEF_PVT(R,T));
  PAR_RTUS(R,T,UC_N,S)                    $= {arg2}_UCRTS.M(R,T,UC_N,S);
  PAR_RTUS(R,T,UC_N,S)                    $= {arg2}_UCRSUS.M(R,T,UC_N,S);
  LOOP(TSL,PAR_RTUS(R,T,UC_N,S)           $= {arg2}_UCRS.M(R,T,UC_N,TSL,S));
  OPTION PAR_URTS<PAR_RTUS,CLEAR=PAR_RTUS;
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,T,S)                $= PAR_URTS(UC_N,R,T,S)*(1/COEF_PVT(R,T));
  OPTION CLEAR=PAR_URTS;

"""
