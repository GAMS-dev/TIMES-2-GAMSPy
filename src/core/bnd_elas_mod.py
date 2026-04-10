# bnd_elas_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_ELAS.MOD establishes bounds on demand elasticity variables
#   %1 - LO/UP step limit
# =============================================================================*
# Questions/Comments:
# - RCJ includes testing for COM_STEP
# - May want elasticity without COM_PROJ - may use COM_BQTY
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndElasMod(GamsClass):
    """Translation unit for bnd_elas.mod."""

    # Instance attributes
    module_name: str = "bnd_elas_mod"
    gams_source: str = "bnd_elas.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.bnd_elas,
            stages=self.env.stages,
            var=self.env.var,
            mx=self.env.mx,
            sow=self.env.sow,
        )

    def bnd_elas(self: BndElasMod, stages: str, var: str, mx: str, sow: str):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=MI_DOPE;
  LOOP((ANNUAL(S),MI_DMAS(RD_AGG(R,C),COM)),
    RD_SHAR(R,T,COM,C)=COM_AGG(R,T,COM,C)*DDF_PREF(R,T,C);
    COM_AGG(R,T,COM,C)$(COM_ELAST(R,T,C,S,'N')>0)=0;
    COM_ELAST(R,T(MIYR_1),COM,TS,BD)=0;
    COM_VOC(RTC(R,T,COM),'LO')$MI_ESUB(R,T,C)=MIN(COM_VOC(RTC,'LO'),1-9E9**(-COM_ELAST(RTC,S,'FX')));
    MI_DOPE(R,T,COM)$MI_ESUB(R,T,C)=MAX(ABS(COM_ELAST(R,T,COM,S,'FX')),MI_ESUB(R,T,C))$SUM(BDNEQ$COM_ELAST(R,T,C,S,BDNEQ),1));
""",
        )

        base_statement = rf"""
    {var}_ELAST.UP(RTCS_VARC(R,T,C,S),J,BDNEQ(BD){sow})$RCJ(R,C,J,BD) = INF$MI_DOPE(R,T,C) +
      (MAX(DDF_QREF(R,T,C) * COM_FR{mx}(R,T,C,S), COM_BQTY(R,C,S)) * COM_VOC(R,T,C,BD)) / COM_STEP(R,C,BD);
"""
        if stages == "YES":
            code_block = f"LOOP(SW_T(T{sow}), \n{base_statement});"
        else:
            code_block = base_statement

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=code_block,
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Price levels for CES (marginal / average)
  MI_RHO(RTC(R,T,C))$MI_DOPE(RTC) = ROUND(1-1/MI_DOPE(RTC),6);
  MI_AGC(R,T(TT+1),COM,C,J,BDNEQ(BD))$(RCJ(R,C,J,BD)$MI_DMAS(R,COM,C)$MI_ESUB(R,T,COM)) = (1-BDSIG(BD)*(ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))**(-1/COM_ELAST(R,T,C,'ANNUAL','FX'));
  MI_AGC(R,T,COM,C,J,BD)$((COM_VOC(R,T,C,BD)>0)$MI_AGC(R,T,COM,C,J,BD)$MI_DOPE(R,T,C)) =
    BDSIG(BD)/(ORD(J)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD)) *
    (((1-(1-BDSIG(BD)*ORD(J)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))**MI_RHO(R,T,C))/MI_RHO(R,T,C))$MI_RHO(R,T,C) -
      LOG(1-BDSIG(BD)*ORD(J)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))$(MI_RHO(R,T,C)=0));

* Fix redundancies
  LOOP(RD_AGG(R,COM),FIL(T)=NOT PROD(BDNEQ,SUM(COM_TS(R,C,S)$MI_DMAS(R,COM,C),COM_ELAST(R,T,C,S,BDNEQ)));
    COM_ELAST(RTCS_VARC(R,T(FIL),C,S),BD)$MI_DMAS(R,COM,C)=0; RCS_COMPRD(R,T(FIL),COM,S,BD)=NO);
  COM_ELASTX(R,T,C,BDNEQ)$MI_DOPE(R,T,C)=1;
  RTC_SHED(R,T,C,BD,JJ)$MI_DOPE(R,T,C)=NO;
""",
        )
