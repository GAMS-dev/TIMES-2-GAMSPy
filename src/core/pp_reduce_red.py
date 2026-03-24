# pp_reduce_red.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpReduceRed(GamsClass):
    """Translation unit for pp_reduce.red."""

    # Instance attributes
    module_name: str = "pp_reduce_red"
    gams_source: str = "pp_reduce.red"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
        arg8: str = "",
        arg9: str = "",
        arg10: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.arg8 = arg8
        self.arg9 = arg9
        self.arg10 = arg10
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.reduction_of_model_size,
        )
        self.env.set_global("cal_red", "cal_nored.red")
        if self.env.reduce == "NO":  # GOTO reddone
            self.tc.enqueue(
                self.reddone,
            )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* determining processes that need capacity variables
  PRC_CAP(RP) = NO;
""",
        )

        if self.tc.defined("PRC_DSCNCAP"):
            self.tc.add_gams_code(
                module=self, phase="init", code=r"PRC_CAP(PRC_DSCNCAP) = YES;"
            )

    def reduction_of_model_size(self: PpReduceRed):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Reduction of model size
*-----------------------------------------------------------------------------
* when no reduction all processes have capacity variables and activity equations
  PRC_CAP(RP)     = YES;
  PRC_ACT(RP)     = RP_STD(RP)+RP_IRE(RP);
  OPTION RP_AFB < NCAP_AF;
""",
        )

    def reddone(self: PpReduceRed):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Mark emissions to be handled by substitution
  LOOP(FS_EMIS(R,P,CG,C,COM), RPCC_FFUNC(R,P,CG,COM) = YES);
  OPTION CLEAR=TRACKPC,CLEAR=FSCK;
  PRC_TS2(PRC_TS(RP_XRED(R,P),S)) = YES;
  RPC_PKC(RP,C)$(NOT PRC_CAP(RP)) = NO;
  RPC_PKF(RPC_PKC) = 0;
""",
        )

    def determine_capacity_variables(self: PpReduceRed):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* determining processes that need capacity variables
  PRC_CAP(RP) = NO;
{"PRC_CAP(PRC_DSCNCAP) = YES;" if self.tc.defined("PRC_DSCNCAP") else ""}
  LOOP((R,UC_N,P)$UC_GMAP_P(R,UC_N,'CAP',P),  PRC_CAP(R,P) = YES);
  LOOP((R,UC_N,P)$UC_GMAP_P(R,UC_N,'NCAP',P), PRC_CAP(R,P) = YES);
  LOOP((RTP(R,PYR,P))$NCAP_PASTI(R,PYR,P),    PRC_CAP(R,P) = YES);
  LOOP((RTP(R,T,P),BD)$CAP_BND(R,T,P,BD),     PRC_CAP(R,P) = YES);
  LOOP((RTP(R,T,P),BD)$NCAP_BND(R,T,P,BD),    PRC_CAP(R,P) = YES);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_COST(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_FOM(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_ISUB(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_ITAX(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_FSUB(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_FTAX(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_DCOST(R,LL,P,CUR) NE 0);
  OBJ_ICUR(R,LL--ORD(LL),P,CUR)$DM_YEAR(LL) $= (NCAP_DLAGC(R,LL,P,CUR) NE 0);
  LOOP(OBJ_ICUR(R,LL,P,CUR), PRC_CAP(R,P) = YES);
*[UR]: added checks for fixed availabilities
  PRC_CAP(RP(R,P))                      $= RP_AFB(RP,'FX');
  RTPS_BD(R,T--ORD(T),P,S--ORD(S),'FX') $= NCAP_AFS(R,T,P,S,'FX');
  RTPS_BD(R,T--ORD(T),P,ANNUAL,'FX')    $= NCAP_AFA(R,T,P,'FX');
  LOOP(RTPS_BD(R,T,P,S,BD), PRC_CAP(R,P) = YES);
  OPTION CLEAR=OBJ_ICUR,CLEAR=RTPS_BD;
{"PRC_CAP(R,P)$SEG(R,P) = YES;" if self.env.etl == "YES" else ""}
""",
        )
