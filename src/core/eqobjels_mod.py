# eqobjels_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJELS the objective function flexible demand utility
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.pp_micro_mod import PpMicroMod

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjelsMod(GamsClass):
    """Translation unit for eqobjels.mod."""

    # Instance attributes
    module_name: str = "eqobjels_mod"
    gams_source: str = "eqobjels.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if self.env.micro == "YES":
            self.include(PpMicroMod(self.tc, self.env, arg1="NLP"))
        self.comp1(
            eq=self.env.eq,
            sow=self.env.sow,
            vart=self.env.vart,
            sws=self.env.sws,
            var=self.env.var,
            r_t=self.env.r_t,
            swt=self.env.swt,
            mx=self.env.mx,
            condition=self.env.micro.upper() != "YES",
        )

    def comp1(
        self: EqobjelsMod,
        eq: str,
        sow: str,
        vart: str,
        sws: str,
        var: str,
        r_t: str,
        swt: str,
        mx: str,
        condition: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {eq}_OBJELS(R,BD,CUR {sow})$(RDCUR(R,CUR)$SUM_OBJ(R,'OBJELS'))..

*------------------------------------------------------------------------------
* Direction with bound sign BDSIG
*------------------------------------------------------------------------------
*V0.5b 980824 - correct ORD adjustment
      SUM(RTCS_VARC(R,T,C,S)$(COM_ELAST(R,T,C,S,BD)$COM_STEP(R,C,BD)),
        COEF_PVT(R,T) * COM_BPRICE(R,T,C,S,CUR) *
        (SUM(RCJ(R,C,J,BD), {vart}_ELAST(R,T,C,S,J,BD {sws}) *
          (1-BDSIG(BD)*(ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))**(1/COM_ELAST(R,T,C,S,BD)))$(NOT COM_ELASTX(R,T,C,BD)) +
* Shaped elasticities
         SUM(RTC_SHED(R,T,C,BD,JJ(AGE)),
           SUM((RCJ(R,C,J,BD),SPAN(AGE+CEIL((ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD)*100-ORD(AGE)))),
             (SHAPED(BD,JJ,SPAN) *
              ((1-BDSIG(BD)*(ORD(J)-.5)*COM_VOC(R,T,C,BD)/COM_STEP(R,C,BD))/SHAPED(BD,'1',SPAN))**(1/MAX(1E-3,SHAPE(JJ,SPAN)))
             )**(1/COM_ELAST(R,T,C,S,BD)) * {vart}_ELAST(R,T,C,S,J,BD {sws}))) +
         SUM(MI_DMAS(R,COM,C)$MI_DOPE(R,T,C),SUM(RCJ(R,C,J,BD),{
                vart
            }_ELAST(R,T,C,S,J,BD {sws}) * MI_AGC(R,T,COM,C,J,BD)))
        )
      )$BDNEQ(BD)


* Micro NLP formulation
{
                (
                    '''  +  SUM(T$(ORD(T)>1), COEF_PVT(R,T) *
        SUM(DEM(R,C)$(MI_ELASP(R,T,C)$RD_NLP(R,C)), MI_CCONS(R,T,C) *
          (({vart}_DEM(R,T,C{sws})**MI_ELASP(R,T,C))$(RD_NLP(R,C)=1) +
           ((SUM(MI_DMAS(R,C,COM),RD_SHAR(R,T,C,COM)**(1/MI_ESUB(R,T,C))*(COM_AGG(R,T,COM,C)*{vart}_DEM(R,T,COM{sws}))**MI_RHO(R,T,C))**(1/MI_RHO(R,T,C)))**MI_ELASP(R,T,C))$(RD_NLP(R,C)>2) -
           DDF_QREF(R,T,C)**MI_ELASP(R,T,C))$(RD_NLP(R,C)>0)
          ))$LNX(BD)
 '''
                )
                if not condition
                else ""
            }
    =E=
    {var}_OBJELS(R,BD,CUR {sow});

*------------------------------------------------------------------------------

* Step bounds for linear CES demand functions
  {eq}L_COMCES(RTC({r_t},COM),C,S{
                swt
            })$(RTCS_VARC(R,T,C,S)$MI_DOPE(R,T,C)$MI_DMAS(R,COM,C))..
   SUM(RCJ(R,C,J,BDNEQ(BD))$COM_ELAST(R,T,C,S,BD),{var}_ELAST(R,T,C,S,J,BD{
                sow
            })*COM_STEP(R,C,BD)/ORD(J)/(DDF_QREF(R,T,C)*COM_FR{
                mx
            }(R,T,C,S)*COM_VOC(R,T,C,BD)))
   =L= {var}_COMPRD(R,T,COM,'ANNUAL'{sow})/DDF_QREF(R,T,COM);
""",
        )
