# pp_lvlbd_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLBD aggregate the bound attributes if finer than level
# *  arg1 - bound attribute name (ACT_BND,FLO_FR,COM_BND,IRE_BND)
# *  arg2 - 'C'ommodity/'P'rocess index
# *  arg3 - 'C,' or none
# *  arg4 - other indexes between S and BD
# *  arg5 - temp residual indexes
# *  arg6 - COM/PRC_TS-level shooting for
# *  arg7 - valid bound levels
# *  arg8 - temp set name
# *  arg9 - treat negative bouds as 0/EPS?
# *=============================================================================*
# * Questions/Comments:
# *  - New implementation (Jul-2011)
# *  - As originally, based on summing of UP/FX and LO/FX bounds from finer levels
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set

from core.base_class import GamsClass
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlbdMod(GamsClass):
    """Translation unit for pp_lvlbd.mod."""

    # Instance attributes
    module_name: str = "pp_lvlbd_mod"
    gams_source: str = "pp_lvlbd.mod"

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
        self.compile()

    def compile(self) -> None:
        self.comp1()

        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg9,
            rl=self.env.rl,
            condition=self.arg9 != "",
        )

    def comp1(self: PpLvlbdMod) -> None:
        g = self.tc
        m = g.container

        g.Bdval = Set(m, name="BDVAL", domain=[g.bd])
        g.ts_bd = Parameter(m, name="TS_BD", domain=[g.s, g.bd])

    def exec1(
        self: PpLvlbdMod,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        arg6: str,
        arg7: str,
        arg8: str,
        arg9: str,
        rl: str,
        condition: bool,
    ) -> None:
        include_pp_qaput = pp_qaput(
            "PUTOUT",
            "PUTGRP",
            "01",
            f"{arg1} Bounds conflict: Value at {arg6} level and below, latter ignored",
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  {arg8}(RT{arg2}(R,T,{arg2}),{arg3}S--ORD(S),{arg4}'FX'{arg5}) $= SUM(BD${arg1}(RT{arg2},{arg3}S,{arg4}BD),1)$(NOT {arg7}(R,{arg2},{arg3}S));

* Aggregation only if target level value is not present
  LOOP(({arg8}(R,T,{arg2},{arg3}ALL_TS,{arg4}'FX'{arg5}),{arg6}(R,{arg2},{arg3}TS)),
    TS_BD(S,BD) = {arg1}(R,T,{arg2},{arg3}S,{arg4}BD)$TS_MAP(R,TS,S);
    TS_BD(S,BDNEQ) $= TS_BD(S,'FX'); Z=SUM(BD$TS_BD(TS,BD),1); F=CARD(TS_BD)-Z;
    IF(Z>1,Z=F; ELSE Z=SUM((RS_BELOW(R,TS,S),BDNEQ(BD))$(TS_BD(S,BD)$TS_BD(TS,BD)),1)$F);
    IF(Z, F=(F>Z);
{include_pp_qaput}
      PUT QLOG ' WARNING       -     {arg1}:  R=',{rl},' Y=',T.TL,' {arg2}=',{arg2}.TL,' S=',TS.TL);
    IF(F, BDVAL(BD)=(NOT TS_BD(TS,BD))$BDNEQ(BD);
*   Clear neg bounds and those below the topmost ones
{f"TS_BD(S,BDNEQ)$(TS_BD(S,BDNEQ)<0) = {arg9};" if condition else ""}
      TS_BD(S,BDVAL(BD))$SUM(RS_BELOW(R,SL,S)$TS_BD(SL,BD),1)=0;
*   Check the INF default for UP bounds before summing
      BDVAL(BDVAL('UP')) = (G_YRFR(R,TS)-SUM(RS_BELOW(R,TS,S)$TS_BD(S,'UP'),G_YRFR(R,S))) < 1E-5;
      TS_BD(TS,BDVAL)=SUM(RS_BELOW(R,TS,S),TS_BD(S,BDVAL));
      IF((TS_BD(TS,'UP')-TS_BD(TS,'LO') < 1E-7)$(SUM(BD$TS_BD(TS,BD),1)=2),
         {arg1}(R,T,{arg2},{arg3}TS,{arg4}'FX') = TS_BD(TS,'LO');
      ELSE {arg1}(R,T,{arg2},{arg3}TS,{arg4}BDVAL) $= TS_BD(TS,BDVAL))));

  {arg1}(R,T,{arg2},{arg3}S,{arg4}BDNEQ)${arg1}(R,T,{arg2},{arg3}S,{arg4}'FX') = 0;
  OPTION CLEAR={arg8};
""",
        )
