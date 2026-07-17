# clearsol_stp.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CLEARSOL.stp: Clear solution values for projection years
# *=============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ClearsolStp(GamsClass):
    """Translation unit for clearsol.stp."""

    module_name: str = "clearsol_stp"
    gams_source: str = "clearsol.stp"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_clearsol_stp,
            arg1=self.arg1,
            var=self.env.var,
            sow=self.env.sow,
            eq=self.env.eq,
            swt=self.env.swt,
            cli=self.env.cli,
            abs_=self.env.abs,
            macro=self.env.macro,
            stages=self.env.stages,
        )

    def exec_clearsol_stp(
        self: ClearsolStp,
        arg1: str,
        var: str,
        sow: str,
        eq: str,
        swt: str,
        cli: str,
        abs_: str,
        macro: str,
        stages: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=clearsol_stp(
                arg1=arg1,
                var=var,
                sow=sow,
                eq=eq,
                swt=swt,
                cli=cli,
                abs_=abs_,
                macro=macro,
                stages=stages,
            ),
        )


def clearsol_stp(
    *,
    arg1: str = "",
    var: str,
    sow: str,
    eq: str,
    swt: str,
    cli: str,
    abs_: str,
    macro: str,
    stages: str,
) -> str:
    return rf"""
  IF(1{arg1},
  RVT(R,VNT(V,T))$RT_PP(R,T) = YES;
  FIL(LL)=T(LL); LOOP(R, FIL(T)$NO_RT(R,T) = NO);
  {var}_ACT.L(RVT,P,S{sow}) = 0;
  {var}_FLO.L(RVT,P,C,S{sow}) = 0;
  {var}_IRE.L(RVT,P,C,S,IE{sow}) = 0;
  {var}_SIN.L(RVT,P,C,S{sow}) = 0;
  {var}_SOUT.L(RVT,P,C,S{sow}) = 0;
  {var}_NCAP.L(RT_PP,P{sow}) = 0;
  {var}_COMNET.L(RT_PP,C,S{sow}) = 0;
  {var}_COMPRD.L(RT_PP,C,S{sow}) = 0;
  {var}_NCAP.L(RT_PP,P{sow}) = 0;
  {var}_UCT.L(UC_N,T(FIL){sow}) = 0;
  {var}_UCTS.L(UC_N,T(FIL),S{sow}) = 0;
  {var}_UCRT.L(UC_N,RT_PP{sow}) = 0;
  {var}_UCRTS.L(UC_N,RT_PP,S{sow}) = 0;
  {var}_SCAP.L(RVT,P{sow}) = 0;
  {eq}G_COMBAL.L(RT_PP,C,S{swt}) = 0;
{f"{var}_CLIBOX.L(CM_VAR,CM_BOX,LL{sow})$CM_LED(LL)=0;" if cli.upper() == "YES" else ""}
{f"{var}_BSPRS.L(RVT,P,C,S,L{sow}) = 0;" if abs_.upper() == "YES" else ""}
{"EQ_OBJ.M = 0;" if macro.upper() != "YES" else ""}
  );
{
        r'''
  VAR_NCAP.L(RT_PP,P) = 0;
  VAR_UCT.L(UC_N,T(FIL)) = 0;
  VAR_UCTS.L(UC_N,T(FIL),S) = 0;
  VAR_UCRT.L(UC_N,RT_PP) = 0;
  VAR_UCRTS.L(UC_N,RT_PP,S) = 0;
'''
        if stages == "YES"
        else ""
    }
"""
