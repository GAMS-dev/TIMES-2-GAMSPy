# clearsol_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CLEARSOL.stc: Clear solution values
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.eqdeclr_mod import EqdeclrMod
from core.mod_vars_mod import ModVarsMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ClearsolStc(GamsClass):
    """Translation unit for clearsol.stc."""

    module_name: str = "clearsol_stc"
    gams_source: str = "clearsol.stc"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.arg1 != "":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                # TODO
                code=rf"${self.env.sw_notags}",
            )
            self.include(ModVarsMod(tc=self.tc, env=self.env))
            self.include(EqdeclrMod(tc=self.tc, env=self.env, arg1=""))
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
$ CLEAR VAR_CUMFLO VAR_CUMCOM VAR_CUMCST VAR_ACT VAR_FLO VAR_IRE VAR_SIN VAR_SOUT VAR_COMNET VAR_COMPRD VAR_ELAST VAR_SCAP VAR_UPS VAR_UPT VAR_UDP VAR_UC
""",
            )
            if self.arg1.upper() == "DEF":
                return

        self.tc.enqueue(
            self.exec1,
            var_dam_defined=self.tc.defined(f"{self.env.var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
        )

    def exec1(self: ClearsolStc, var_dam_defined: bool, var_scap_defined: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(YES,DISPLAY 'Solution store cleared';
  OPTION CLEAR=VAR_ACT;
  OPTION CLEAR=VAR_BLND;
  OPTION CLEAR=VAR_COMNET;
  OPTION CLEAR=VAR_COMPRD;
  OPTION CLEAR=VAR_IRE;
  OPTION CLEAR=VAR_ELAST;
  OPTION CLEAR=VAR_FLO;
  OPTION CLEAR=VAR_SIN,CLEAR=VAR_SOUT;
  OPTION CLEAR=VAR_CAP,CLEAR=VAR_NCAP;
  OPTION CLEAR=VAR_UC,CLEAR=VAR_UCR;
  OPTION CLEAR=VAR_UCT,CLEAR=VAR_UCRT;
  OPTION CLEAR=VAR_UCTS,CLEAR=VAR_UCRTS;
  OPTION CLEAR=VAR_UPS,CLEAR=VAR_UPT,CLEAR=VAR_UDP;
  OPTION CLEAR=VAR_OBJ,CLEAR=VAR_OBJELS;
* Delicate bounds
  VAR_CUMCOM.L(R,C,COM_VAR,ALLYEAR,YEAR)=0;
  VAR_CUMFLO.L(R,P,C,ALLYEAR,YEAR)=0;
{"VAR_DAM.L(R,T,C,BD,J)=0;" if var_dam_defined else ""}
{"VAR_SCAP.L(R,YEAR,T,P)=0;" if var_scap_defined else ""}
* Equations
  OPTION CLEAR=EQE_COMBAL,CLEAR=EQG_COMBAL,CLEAR=EQE_COMPRD;
  OPTION CLEAR=EQ_PEAK,CLEAR=EQ_IRE,CLEAR=EQE_CPT;
  OPTION CLEAR=EQE_FLOMRK,CLEAR=EQG_FLOMRK,CLEAR=EQL_FLOMRK;
  OPTION CLEAR=EQE_ACTBND,CLEAR=EQG_ACTBND,CLEAR=EQL_ACTBND;
  );
""",
        )


def clearsol_stc(
    var: str, sow: str, cli: str, abs_: str, macro: str, stages: str
) -> str:
    return ""
