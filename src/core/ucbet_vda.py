# ucbet_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UCBET.vda Derivation of maximum activities and flows according to UCBET     *
# *   arg1 - mod or v# for the source code to be used                           *
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core import cal_nored_red, cal_red_red
from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class UcbetVda(GamsClass):
    """Translation unit for ucbet.vda."""

    # Instance attributes
    module_name: str = "ucbet_vda"
    gams_source: str = "ucbet.vda"

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
* Preprocessing of UC_FLOBET:
  SET UC_GMAX(UC_N,ALL_R,ITEM,C,ITEM);
  SET UC_GMAXR(ALL_R,UC_N);
  ALIAS(*,NAME);

""",
        )
        self.tc.enqueue(
            self.ucbet_exec,
            pgprim=self.env.pgprim,
        )

        if self.env.cal_red == "cal_nored.red":
            cal_red_code = cal_nored_red.cal_nored_red(
                arg1="COM",
                arg2="COM1",
                arg3="S",
                arg4="P",
                arg5="T",
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow,
                var=self.env.var,
                pgprim=self.env.pgprim,
            )
        else:
            cal_red_code = cal_red_red.cal_red_red(
                arg1="COM",
                arg2="COM1",
                arg3="S",
                arg4="P",
                arg5="T",
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=self.env.sow,
                var=self.env.var,
            )
        self.env.set_scoped("swtd2", self.env.swtd)
        self.env.set_scoped("sow2", self.env.sow)
        if self.env.stages == "YES":
            self.env.set_scoped("swtd2", ",SW_TSW(SOW,T,W)")
            self.env.set_scoped("sow2", ",W")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
   {self.env.eq}G_UCMAX(UC_GMAX(UC_N,ALL_R,ITEM,C,NAME){self.env.sow}) ..

* Select variable to be maximized (remove SUM if IMPEXP group allowed)

      {self.env.var}_UC(UC_N{self.env.sow})$(NOT UC_GMAXR(ALL_R,UC_N)) +
      SUM(R(ALL_R),{self.env.var}_UCR(UC_N,R{self.env.sow})$UC_GMAXR(ALL_R,UC_N))

   =G=

* Sum of flows by region
   SUM((UC_T_SUM(UC_GMAXR(R(ALL_R),UC_N),T){self.env.swtd2}),
*....Time Mutiplier
     (FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','ACT','PERDISC')) *
     SUM(RTPCS_VARF(R,T,P,COM,S)$(COM_GMAP(R,C,COM)$UC_FLOBET(UC_N,R,T,P,C)),
       UC_FLOBET(UC_N,R,T,P,C) *
       SUM(RTP_VINTYR(R,V,T,P),
         (
            {cal_red_code}
         )$RP_STD(R,P) +
*....For IRE processes, sum Import flows only
         SUM(RPC_IRE(R,P,COM,IE('IMP')),
          {self.env.var}_IRE(R,V,T,P,COM,S,IE{self.env.sow2})$(NOT RPC_AIRE(R,P,COM)) +
          ({self.env.var}_ACT(R,V,T,P,S{self.env.sow2})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM))$RP_IRE(R,P)
       )))$LIM(NAME) +

* Sum of flows globally
   SUM((UC_T_SUM(R,UC_N,T){self.env.swtd2})$(NOT UC_GMAXR(R,UC_N)),
*....Time Mutiplier
     (FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','ACT','PERDISC')) *
     SUM(RTPCS_VARF(R,T,P,COM,S)$(COM_GMAP(R,C,COM)$UC_FLOBET(UC_N,R,T,P,C)),
       UC_FLOBET(UC_N,R,T,P,C) *
       SUM(RTP_VINTYR(R,V,T,P),
         (
            {cal_red_code}
         )$RP_STD(R,P) +
*....For IRE processes, sum Import flows only
         SUM(RPC_IRE(R,P,COM,IE('IMP')),
          {self.env.var}_IRE(R,V,T,P,COM,S,IE{self.env.sow2})$(NOT RPC_AIRE(R,P,COM)) +
          ({self.env.var}_ACT(R,V,T,P,S{self.env.sow2})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM))$RP_IRE(R,P)
       )))$((NOT REG(ALL_R))$LIM(NAME)) +

* Sum of activities by region
   SUM((UC_T_SUM(R(ALL_R),UC_N,T){self.env.swtd2}),
*....Time Mutiplier
     (FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','ACT','PERDISC')) *
     SUM(RTP_VINTYR(R,V,T,P(ITEM))$UC_FLOBET(UC_N,R,T,P,{self.env.pgprim}),
       UC_FLOBET(UC_N,R,T,P,{self.env.pgprim}) *
       (
*........For Standard processes, sum activities
         SUM((RTP_VARA(R,T,P),PRC_TS(R,P,S)), {self.env.var}_ACT(R,V,T,P,S{self.env.sow2}))$RP_STD(R,P) +
*........For IRE processes, sum Import flows only
         SUM((RPC_IRE(R,P,COM,IE('IMP')),RTPCS_VARF(R,T,P,COM,S)),
           ({self.env.var}_IRE(R,V,T,P,COM,S,IE{self.env.sow2})$(NOT RPC_AIRE(R,P,COM))+
            ({self.env.var}_ACT(R,V,T,P,S{self.env.sow2})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)))$RP_IRE(R,P)
       ))
    )$UC_NUMBER(NAME) +

* Sum of activities globally
   SUM((UC_T_SUM(R,UC_N,T){self.env.swtd2})$(NOT REG(ALL_R)),
*....Time Mutiplier
     (FPD(T)+(COEF_PVT(R,T)-FPD(T))$UC_ATTR(R,UC_N,'LHS','ACT','PERDISC')) *
     SUM(RTP_VINTYR(R,V,T,P(ITEM))$UC_FLOBET(UC_N,R,T,P,{self.env.pgprim}),
       UC_FLOBET(UC_N,R,T,P,{self.env.pgprim}) *
       (
*........For Standard processes, sum activities
         SUM((RTP_VARA(R,T,P),PRC_TS(R,P,S)), {self.env.var}_ACT(R,V,T,P,S{self.env.sow2}))$RP_STD(R,P) +
*........For IRE processes, sum Import flows only
         SUM((RPC_IRE(R,P,COM,IE('IMP')),RTPCS_VARF(R,T,P,COM,S)),
           ({self.env.var}_IRE(R,V,T,P,COM,S,IE{self.env.sow2})$(NOT RPC_AIRE(R,P,COM))+
            ({self.env.var}_ACT(R,V,T,P,S{self.env.sow2})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)))$RP_IRE(R,P)
       ))
    )$((NOT REG(ALL_R))$UC_NUMBER(NAME))

;
*-----------------------------------------------------------------------------
* Sum regional maximums to global (change R to ALL_R if IMPEXP allowed)
   {self.env.eq}G_UCSUMAX(UC_N{self.env.sow})$SUM(UC_GMAXR(ALL_R,UC_N),1) ..

   {self.env.var}_UC(UC_N{self.env.sow})  =G=  SUM(UC_GMAXR(R,UC_N),{self.env.var}_UCR(UC_N,R{self.env.sow}));

*-----------------------------------------------------------------------------
""",
        )

    def ucbet_exec(self: UcbetVda, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Collect set of all regional cumulative UC_N
  OPTION CLEAR=UNCD1;
  LOOP((UC_N,R,T,P,C)$UC_FLOBET(UC_N,R,T,P,C),UNCD1(UC_N)=YES);
  UC_GMAXR(UC_R_EACH) = YES;
  UC_R_SUM(R,UC_N(UNCD1)) = YES;

* Set Equation controls
  LOOP((UC_N,R,T,P,C)$UC_FLOBET(UC_N,R,T,P,C),
   IF(SAMEAS('{pgprim}',C),
     IF(UC_ATTR(R,UC_N,'LHS','ACT','N'),
       UC_GMAX(UC_N,'IMPEXP',P,C,'EACH') = YES;
     ELSE UC_GMAX(UC_N,R,P,C,'EACH') = YES);
   ELSE
     IF(UC_GMAXR(R,UC_N), UC_GMAX(UC_N,R,'N',C,'N') = YES;
     ELSE UC_GMAX(UC_N,'IMPEXP','N',C,'N') = YES);
  ));

* If IMPEXP should be one group, add IMPEXP for regional UC_N
  LOOP(R,UC_GMAXR('IMPEXP',UC_N)$UC_GMAXR(R,UC_N) = YES);
* Remove all (ALL_R,UC_N) not used in betting parameters
  OPTION CLEAR=RXX;
  LOOP(UC_GMAX(UC_N,ALL_R,ITEM,C,NAME),RXX('IMPEXP',UC_N,ALL_R) = YES);
  UC_GMAXR(ALL_R,UC_N)$(NOT RXX('IMPEXP',UC_N,ALL_R)) = NO;
* Remove EQE_UC equations for maxed UC_N
  UC_TS_SUM(R,UC_N(UNCD1),S) = NO;
""",
        )
