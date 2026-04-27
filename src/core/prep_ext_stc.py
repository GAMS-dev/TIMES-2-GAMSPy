# prep_ext_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.stc oversees all the added inperpolation activities needed by STC  *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillparm_gms import FillparmGms
from core.prepparm_gms import PrepparmGms
from core.recurrin_stc import RecurrinStc

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtStc(GamsClass):
    """Translation unit for prep_ext.stc."""

    # Instance attributes
    module_name: str = "prep_ext_stc"
    gams_source: str = "prep_ext.stc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        # fmt: off
        batincludes = [
            ("fp", "S_COM_PROJ",  "R",          "C,J,WW",               ",'0','0','0'", "MILESTONYR", "1",                   "GE 0", ""),
            ("fp", "S_COM_TAX",   "R",          "C,S,COM_VAR,CUR,J,WW", "",             "MILESTONYR", "1",                   "GE 0", ""),
            ("fp", "S_NCAP_COST", "R",          "P,J,WW",               ",'0','0','0'", "MILESTONYR", "1",                   "GE 0", ""),
            ("pp", "S_CAP_BND",   "R",          "P,BD,J,WW",            ",'0'",         "MILESTONYR", "RTP(R,MILESTONYR,P)", "1",    ""),
            ("pp", "S_UC_RHSRT",  "ALL_R,UC_N", "L,J,WW",               ",'0'",         "MILESTONYR", "1",                   "1",    ""),
            ("pp", "S_UC_RHSRTS", "ALL_R,UC_N", "TS,L,J,WW",            "",             "MILESTONYR", "1",                   "1",    ""),
            ("pp", "S_UC_RHST",   "UC_N",       "L,J,WW",               ",'0','0'",     "MILESTONYR", "1",                   "1",    ""),
            ("pp", "S_UC_RHSTS",  "UC_N",       "TS,L,J,WW",            ",'0'",         "MILESTONYR", "1",                   "1",    ""),
            ("pp", "S_DAM_COST",  "R",          "C,CUR,J,WW",           ",'0'",         "MILESTONYR", "1",                   "EPS",  "3"),
            ("fp", "S_FLO_FUNC",  "R",          "P,CG,CG2,J,WW",        ",'0'",         "MILESTONYR", "1",                   "GE 0", ""),
            ("fp", "S_NCAP_AFS",  "R",          "P,TS,J,WW",            ",'0','0'",     "MILESTONYR", "1",                   "GE 0", ""),
            ("fp", "S_COM_FR",    "R",          "C,TS,J,WW",            ",'0','0'",     "MILESTONYR", "1",                   "GE 0", ""),
        ]
        # fmt: on
        for arg in batincludes:
            if arg[1] in ["S_DAM_COST", "S_FLO_FUNC", "S_NCAP_AFS", "S_COM_FR"]:
                if not self.tc.defined(arg[1]):
                    continue
            if arg[0] == "fp":
                self.include(
                    FillparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[1],
                        arg2=arg[2],
                        arg3=arg[3],
                        arg4=arg[4],
                        arg5=arg[5],
                        arg6=arg[6],
                        arg7=arg[7],
                        arg8=arg[8],
                    )
                )
            elif arg[0] == "pp":
                self.include(
                    PrepparmGms(
                        self.tc,
                        self.env,
                        arg1=arg[1],
                        arg2=arg[2],
                        arg3=arg[3],
                        arg4=arg[4],
                        arg5=arg[5],
                        arg6=arg[6],
                        arg7=arg[7],
                        arg8=arg[8],
                    )
                )
        self.include(
            RecurrinStc(
                self.tc,
                self.env,
                arg1="MXPAR",
            )
        )
        code = ""
        if self.tc.defined("S_DAM_COST"):
            code += "PARAMETER DAM_COST //;\n"
        if self.tc.defined("DAM_COST"):
            code += "PARAMETER S_DAM_COST //;\n"
        if len(code):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=code,
            )

        self.tc.enqueue(
            self.prep_ext_stc_exec,
            have_s_flo_func=self.tc.defined("S_FLO_FUNC"),
        )

    def prep_ext_stc_exec(self: PrepExtStc, have_s_flo_func: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* commodities involved in CUM constraints
  S_COM_CUM(R,'NET',ALLYEAR(BOHYEAR+BEOH(BOHYEAR)),LL(EOHYEAR+BEOH(EOHYEAR)),C,BD,J,WW) $= S_COM_CUMNET(R,BOHYEAR,EOHYEAR,C,BD,J,WW);
  S_COM_CUM(R,'PRD',ALLYEAR(BOHYEAR+BEOH(BOHYEAR)),LL(EOHYEAR+BEOH(EOHYEAR)),C,BD,J,WW) $= S_COM_CUMPRD(R,BOHYEAR,EOHYEAR,C,BD,J,WW);
  OPTION CLEAR=S_COM_CUMPRD,CLEAR=S_COM_CUMNET;
  S_COM_CUM(R,COM_VAR,ALLYEAR,LL,C,'LO',J,WW)$((S_COM_CUM(R,COM_VAR,ALLYEAR,LL,C,'LO',J,WW) EQ 0)$S_COM_CUM(R,COM_VAR,ALLYEAR,LL,C,'LO',J,WW)) = 0;
  RC_CUMCOM(R,COM_VAR,ALLYEAR,LL,C) $= SUM((BD,J,WW)$S_COM_CUM(R,COM_VAR,ALLYEAR,LL,C,BD,J,WW),YES);
  LOOP((R,T,C,S,COM_VAR,CUR,J,WW)$S_COM_TAX(R,T,C,S,COM_VAR,CUR,J,WW),UC_COM('OBJ1',COM_VAR,'LHS',R,'0',C,ANNUAL,'UCN')=1);

* collect transformation tuples
{"OPTION RP_FFSGG <= S_FLO_FUNC;" if have_s_flo_func else ""}

* Activate capacity variables if S_CAP_BND is specified
  LOOP((R,T,P,BD,J,WW)$S_CAP_BND(R,T,P,BD,J,WW),RTP_VARP(R,T,P) = YES);

* Set flags for Phased UC_N
  UC_R_SUM(R,'OBJZ') = YES; UC_R_EACH(R,'OBJZ') = YES; UC_R_SUM(R,'OBJ1') = YES;
  UC_T_SUM(R,'OBJZ',T) = YES; UC_T_SUM(R,'OBJ1',MIYR_1) = YES;
  LOOP((UC_N,WW)$S_UCOBJ(UC_N,WW),UC_RHS(UC_N,'N')$(NOT UC_RHS(UC_N,'N')) = -1);
* Initialize SW_PARM
  SW_PARM = CARD(S_COM_PROJ) + CARD(S_CAP_BND) + CARD(S_COM_CUMPRD) + CARD(S_COM_CUMNET);
  SW_PARM = SW_PARM + CARD(S_CM_CONST) + CARD(S_CM_MAXC);
* Set flag for detemininstic RHS if none set but is set for some SOW
  UC_RHS(UC_N,'UP')$((NOT UC_RHS(UC_N,'UP'))$SUM((LIM,J,WW)$S_UC_RHS(UC_N,LIM,J,WW),1)) = INF;
  UC_RHSR(R,UC_N,'UP')$((NOT UC_RHSR(R,UC_N,'UP'))$SUM((LIM,J,WW)$S_UC_RHSR(R,UC_N,LIM,J,WW),1)) = INF;
  UC_RHST(UC_N,T,'UP')$((NOT UC_RHST(UC_N,T,'UP'))$SUM((LIM,J,WW)$S_UC_RHST(UC_N,T,LIM,J,WW),1)) = INF;
  UC_RHSRT(R,UC_N,T,'UP')$((NOT UC_RHSRT(R,UC_N,T,'UP'))$SUM((LIM,J,WW)$S_UC_RHSRT(R,UC_N,T,LIM,J,WW),1)) = INF;
  UC_RHSTS(UC_N,T,S,'UP')$((NOT UC_RHSTS(UC_N,T,S,'UP'))$SUM((LIM,J,WW)$S_UC_RHSTS(UC_N,T,S,LIM,J,WW),1)) = INF;
  UC_RHSRTS(R,UC_N,T,S,'UP')$((NOT UC_RHSRTS(R,UC_N,T,S,'UP'))$SUM((LIM,J,WW)$S_UC_RHSRTS(R,UC_N,T,S,LIM,J,WW),1)) = INF;
  UC_DYNBND('OBJ1','N')=YES;
""",
        )
