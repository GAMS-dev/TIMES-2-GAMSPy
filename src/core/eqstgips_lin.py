# eqstgips_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGIPS Inter-Period Storage (IPS) and TIME-Slice Storage (TSS)            *
# *=============================================================================*
# *AL Questions/Comments:
# * v2.6.0: VART redefined locally for stochastic mode
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgipsLin(GamsClass):
    """Translation unit for eqstgips.lin."""

    # Instance attributes
    module_name: str = "eqstgips_lin"
    gams_source: str = "eqstgips.lin"

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
            code=r"""
*$ONLISTING
   SET RTP_EQSTK(R,ALLYEAR,T,P,ITEM);
""",
        )

        self.tc.enqueue(self.exec1)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
  {self.env.eq}_STGIPS(RTP_EQSTK({self.env.r_v_t},P,ITEM) {self.env.swt})$(SUM(PRC_STGIPS(R,P,C),1)$PRC_MAP(R,'STK',P)) ..

* storage level at the milestone year T
     {self.env.var}_ACT(R,V,T,P,'ANNUAL' {self.env.sow})$LIM(ITEM) +
     SUM((IO(ITEM),MODLYEAR,MIYR_1(LL))$RTP_VINTYR(R,MODLYEAR,T,P),
       {self.env.var}_ACT(R,MODLYEAR,LL-LEAD(LL),P,'ANNUAL' {self.env.sow}))

    =E=

     SUM(TOP(PRC_STGIPS(R,P,C),IO),

         SUM(TT(T-1),
* storage level at the milestone year TT, corrected with storage losses
           ({self.env.vartt}_ACT(R,V,TT,P,'ANNUAL'{self.env.sws})*POWER(1-STG_LOSS(R,V,P,'ANNUAL'),LEAD(T))$IPS(IO) +
* Add in- and output flows to/from storage related to period TT
            SUM(PERDINV(T,Y_EOH),TPULSE(TT,Y_EOH)*((1-STG_LOSS(R,V,P,'ANNUAL'))**(M(T)-YEARVAL(Y_EOH)+0.5)))/PRC_ACTFLO(R,V,P,C) *
            ({self.env.vartt}_SIN(R,V,TT,P,C,'ANNUAL'{self.env.sws})$IPS(IO) - {self.env.vartt}_SOUT(R,V,TT,P,C,'ANNUAL'{self.env.sws})$(NOT IPS(IO))))$(RTP_VINTYR(R,V,TT,P)$PRC_VINT(R,P)) +
* storage level at the milestone year TT, corrected with storage losses
           ({self.env.vartt}_ACT(R,TT,TT,P,'ANNUAL'{self.env.sws})*POWER(1-STG_LOSS(R,V,P,'ANNUAL'),LEAD(T))$IPS(IO) +
* Add in- and output flows to/from storage related to period TT
            SUM(PERDINV(T,Y_EOH),TPULSE(TT,Y_EOH)*((1-STG_LOSS(R,V,P,'ANNUAL'))**(M(T)-YEARVAL(Y_EOH)+0.5)))/PRC_ACTFLO(R,TT,P,C) *
            ({self.env.vartt}_SIN(R,TT,TT,P,C,'ANNUAL'{self.env.sws})$IPS(IO) - {self.env.vartt}_SOUT(R,TT,TT,P,C,'ANNUAL'{self.env.sws})$(NOT IPS(IO))))$(RTP_VINTYR(R,TT,TT,P)$(NOT PRC_VINT(R,P)))) +

* in- and output flows to/from storage related to period T
* [AL] Summing over PERDINV years, as the activity is measured at M(T)
* [AL] Inflows and outflows occur, on average, at the mid-point of each year
         SUM(PERDINV(T,Y_EOH),TPULSE(T,Y_EOH)*((1-STG_LOSS(R,V,P,'ANNUAL'))**(M(T)-YEARVAL(Y_EOH)+0.5)))$RTP_VINTYR(R,V,T,P) *
         ({self.env.var}_SIN(R,V,T,P,C,'ANNUAL' {self.env.sow})$IPS(IO) - {self.env.var}_SOUT(R,V,T,P,C,'ANNUAL' {self.env.sow})$(NOT IPS(IO))) / PRC_ACTFLO(R,V,P,C)
     )$LIM(ITEM) +

* [AL] In the first period VAR_ACT is not available, but exogenous charge can be used
     SUM(VNT(T,MIYR_1(LL)),{self.env.var}_ACT(R,V,LL-LEAD(LL),P,'ANNUAL' {self.env.sow}) *
         POWER(1-STG_LOSS(R,V,P,'ANNUAL'),LEAD(T)))$LIM(ITEM) +

* Exogenous charge at BOH
     SUM((IO(ITEM),MIYR_1(LL)),STG_CHRG(R,LL-LEAD(LL),P,'ANNUAL')) +
* Minimum storage balance at end-of-period
     ({self.env.var}_ACT(R,V,T,P,'ANNUAL'{self.env.sow}) * POWER(1-STG_LOSS(R,V,P,'ANNUAL'),E(T)-M(T)) -
      SUM((MIYR_1(LL),Y_EOH(LL+(E(T)-YEARVAL(LL)))),{self.env.var}_ACT(R,V,Y_EOH,P,'ANNUAL'{self.env.sow})) +
* in- and output flows to/from storage
      SUM(TOP(PRC_STGIPS(R,P,C),IO),
       SUM(PERIODYR(T,Y_EOH)$(YEARVAL(Y_EOH) GT M(T)),((1-STG_LOSS(R,V,P,'ANNUAL'))**(E(T)-YEARVAL(Y_EOH)+0.5))) *
* half year's correction if LAGT is even
       (1+((LAGT(T)-1)/2/(E(T)-M(T))-1)$(E(T) < MIYR_VL)) / PRC_ACTFLO(R,V,P,C) *
       ({self.env.var}_SIN(R,V,T,P,C,'ANNUAL' {self.env.sow})$IPS(IO) - {self.env.var}_SOUT(R,V,T,P,C,'ANNUAL' {self.env.sow})$(NOT IPS(IO)))))$J(ITEM)
;
$OFFLISTING
""",
        )

    def exec1(self: EqstgipsLin):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Charge at beginning of horizon (BOH)
   RTP_EQSTK(R,MIYR_1(T),T,P,'IN')$(RTP(R,T,P)$PRC_MAP(R,'STK',P)) = YES;
* Normal storage balance in each period (N)
   RTP_EQSTK(RTP_VINTYR(R,V,T,P),'N')$PRC_MAP(R,'STK',P) = YES;
* We must ensure that the storage level is non-negative at end of each period (1)
   RTP_EQSTK(RTP_VINTYR(R,V,T,P),'1')$((E(T) GT M(T))$PRC_MAP(R,'STK',P)) = YES;
*------------------------------------------------------------------------------
""",
        )
