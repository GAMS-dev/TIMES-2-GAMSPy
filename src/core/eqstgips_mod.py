# eqstgips_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTG Inter-Period Storage (IPS) and TIME-Slice Storage (TSS)               *
# *=============================================================================*
# *UR Questions/Comments:
# *
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgipsMod(GamsClass):
    """Translation unit for eqstgips.mod."""

    # Instance attributes
    module_name: str = "eqstgips_mod"
    gams_source: str = "eqstgips.mod"

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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*$ONLISTING

  {self.env.eq}_STGIPS(RTP_VINTYR({self.env.r_v_t},P),IPS {self.env.swt})$(((MIYR_1(V)*MIYR_1(T)+LIM(IPS))*SUM(PRC_STGIPS(R,P,C),1))$PRC_MAP(R,'STK',P)) ..

* storage level in the end of period T
     {self.env.var}_ACT(R,V,T,P,'ANNUAL' {self.env.sow})$LIM(IPS) +
     SUM((IO(IPS),MODLYEAR,MIYR_1(LL))$RTP_VINTYR(R,MODLYEAR,T,P),
       {self.env.var}_ACT(R,MODLYEAR,LL-LEAD(LL),P,'ANNUAL' {self.env.sow}))

    =E=

     (
* storage level in the end of period T-1
         (SUM(TT(T-1),
           ({self.env.vartt}_ACT(R,V,TT,P,'ANNUAL'{self.env.sws})$RTP_VINTYR(R,V,TT,P))$PRC_VINT(R,P) +
           ({self.env.vartt}_ACT(R,TT,TT,P,'ANNUAL'{self.env.sws})$RTP_VINTYR(R,TT,TT,P))$(NOT PRC_VINT(R,P))) +
* [AL] In the first period VAR_ACT is not available, but exogenous charge can be used
          SUM(MIYR_1(LL),{self.env.var}_ACT(R,V,LL-LEAD(LL),P,'ANNUAL' {self.env.sow}))$MIYR_1(T)) *
* storage losses
* [AL] Initial storage level/charge is reduced to (1-LOSS)**D(T) during the period
         POWER(1-STG_LOSS(R,V,P,'ANNUAL'),D(T)) +

* in- and output flows to/from storage
* [AL] Added summing over PERIODYR, as the storage operates during the whole period
         SUM(TOP(PRC_STGIPS(R,P,C),IO),
          ({self.env.var}_SIN(R,V,T,P,C,'ANNUAL' {self.env.sow})$IPS(IO) - {self.env.var}_SOUT(R,V,T,P,C,'ANNUAL' {self.env.sow})$(NOT IPS(IO))) *
* storage losses
* [AL] Inflows and outflows occur, on average, at the mid-point of each year
          SUM(PERIODYR(T,Y_EOH),((1-STG_LOSS(R,V,P,'ANNUAL'))**(E(T)-YEARVAL(Y_EOH)+0.5))) / PRC_ACTFLO(R,V,P,C)
         )
       )$LIM(IPS) +
* Exogenous charge at BOH
     SUM((IO(IPS),MIYR_1(LL)),STG_CHRG(R,LL-LEAD(LL),P,'ANNUAL'))
;
$OFFLISTING
""",
        )
