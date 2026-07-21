# eqstgtss_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGTSS TIME-Slice Storage (TSS) and general storage (STS)
# *=============================================================================*
# * Questions/Comments:
# *   - the storage level does NOT need to be fixed to an initial storage level in some TS

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgtssMod(GamsClass):
    """Translation unit for eqstgtss.mod."""

    # Instance attributes
    module_name: str = "eqstgtss_mod"
    gams_source: str = "eqstgtss.mod"

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
        rts = macro.rts(s="S", g=self.tc, env=self.env)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
    {self.env.eq}_STGTSS(RTP_VINTYR({self.env.r_v_t},P),{rts}{self.env.swt})$(RPS_STG(R,P,S)$RP_STG(R,P))..

* storage level in time-slice s
          {self.env.var}_ACT(R,V,T,P,S {self.env.sow})

    =E=

          SUM(RPS_STG(R,P,ALL_TS(S--RS_STG(R,S))),
* storage level in time-slice s
               {self.env.var}_ACT(R,V,T,P,ALL_TS{self.env.sow})
               +
* for day-night storage; allow flow variable at or above ALL_TS
               (
                 SUM((RPCS_VAR(RPC_STG(R,P,C),TS),TS_MAP(R,TS,ALL_TS)),
                   ({self.env.var}_SIN(R,V,T,P,C,TS{self.env.sow})$(TOP(R,P,C,'IN')$PRC_NSTTS(R,P,TS)) -
                    {self.env.var}_SOUT(R,V,T,P,C,TS{self.env.sow})$(TOP(R,P,C,'OUT')$(PRC_NSTTS(R,P,TS) EQV RPC_STGN(R,P,C,'OUT')))) *
                   RS_FR(R,ALL_TS,TS) * (1+RTCS_FR(R,T,C,ALL_TS,TS)) / PRC_ACTFLO(R,V,P,C))
               )$PRC_MAP(R,'NST',P)
               +
* for storage processes without charging restriction
               SUM(TOP(PRC_STGTSS(R,P,C),'IN'),{self.env.var}_SIN(R,V,T,P,C,ALL_TS{self.env.sow})/PRC_ACTFLO(R,V,P,C)) -
               SUM(TOP(PRC_STGTSS(R,P,C),'OUT'),{self.env.var}_SOUT(R,V,T,P,C,ALL_TS{self.env.sow})/PRC_ACTFLO(R,V,P,C))
               -
* optional balancer flow
               SUM(PRC_TS(R,P,TS)$RS_BELOW1(R,TS,S),{self.env.var}_SOUT(R,V,T,P,'{self.env.pgprim}',TS{self.env.sow})*RS_FR(R,ALL_TS,TS))$RP_STS(R,P) -

* storage losses: average storage level per cycle * loss fraction by cycle * cycles
               {self.env.var}_ACT(R,V,T,P,ALL_TS{self.env.sow}) * MAX(STG_LOSS(R,V,P,ALL_TS)/2,
* equilibrium loss (STG_LOSS<0): Act0 * (1-Loss/(1/EXP(-Loss)-1))
                 (1+(STG_LOSS(R,V,P,ALL_TS))/(1/EXP(STG_LOSS(R,V,P,ALL_TS))-1)))$STG_LOSS(R,V,P,ALL_TS) -
               {self.env.var}_ACT(R,V,T,P,S{self.env.sow}) * MAX(STG_LOSS(R,V,P,ALL_TS)/2,
* equilibrium loss (STG_LOSS<0): Act1 * (-Loss/(EXP(-Loss)-1)-1)
                 ((STG_LOSS(R,V,P,ALL_TS))/(EXP(STG_LOSS(R,V,P,ALL_TS))-1)-1))$STG_LOSS(R,V,P,ALL_TS)
             )
* storage charge
    + STG_CHRG(R,T,P,S--RS_STG(R,S));


*--- Balancer Equation ---

    {self.env.eq}_STSBAL(RTP_VINTYR({self.env.r_v_t},P),TSL,{rts},L{self.env.swt})$(TS_GROUP(R,TSL,S)$PRC_TS(R,P,S)$RP_STL(R,P,TSL,L))..

* storage level in time-slice s
         SUM(RS_BELOW(R,ANNUAL,S),{self.env.var}_ACT(R,V,T,P,S{self.env.sow})+({self.env.var}_SIN(R,V,T,P,'{self.env.pgprim}',S{self.env.sow})+{macro.var_sts.render("R", "V", "T", "P", "S", "'N'")})$RP_STL(R,P,TSL,'UP'))

    =E=

         SUM(RS_BELOW(R,ANNUAL,SL(S--RS_STG(R,S))),
* storage level in time-slice s
             {self.env.var}_ACT(R,V,T,P,SL{self.env.sow})$IPS(L) + {self.env.var}_UDP(R,V,T,P,SL,'LO'{self.env.sow})$BD(L) +
             ({self.env.var}_SIN(R,V,T,P,'{self.env.pgprim}',SL{self.env.sow})+{macro.var_sts.render("R", "V", "T", "P", "SL", "L")})$RP_STL(R,P,TSL,'UP')
             +
* balancer flows
             ({self.env.var}_SOUT(R,V,T,P,'{self.env.pgprim}',SL{self.env.sow}) -
              SUM(PRC_TS(R,P,TS)$RS_BELOW1(R,TS,S),{self.env.var}_SOUT(R,V,T,P,'{self.env.pgprim}',TS{self.env.sow})*RS_FR(R,SL,TS))
              -
* storage losses: average storage level * year fraction * loss fraction
              ({self.env.var}_ACT(R,V,T,P,SL{self.env.sow})$RS_STG(R,S)) * MAX(STG_LOSS(R,V,P,SL)/2,
* equilibrium loss (STG_LOSS<0): Act0 * (1-Loss/(1/EXP(-Loss)-1))
                (1+STG_LOSS(R,V,P,SL)/(1/EXP(STG_LOSS(R,V,P,SL))-1)))$STG_LOSS(R,V,P,SL) -
              ({self.env.var}_ACT(R,V,T,P,S{self.env.sow})$RS_STG(R,S)+({self.env.var}_SIN(R,V,T,P,'{self.env.pgprim}',S{self.env.sow})-{self.env.var}_SIN(R,V,T,P,'{self.env.pgprim}',SL{self.env.sow}))$RP_STL(R,P,TSL,'UP')) *
* equilibrium loss (STG_LOSS<0): Act1 * (-Loss/(EXP(-Loss)-1)-1)
              MAX(STG_LOSS(R,V,P,SL)/2, (STG_LOSS(R,V,P,SL)/(EXP(STG_LOSS(R,V,P,SL))-1)-1))$STG_LOSS(R,V,P,SL)
            )$IPS(L))
         +
         SUM(ANNUAL(S),
* net charging into IPS
             SUM(TOP(PRC_STGIPS(R,P,C),IO), 1 / PRC_ACTFLO(R,V,P,C) *
                {self.env.var}_SIN(R,V,T,P,C,S {self.env.sow})$IPS(IO) - {self.env.var}_SOUT(R,V,T,P,C,S {self.env.sow})$(NOT IPS(IO))) -
* balancer flow
             {self.env.var}_SOUT(R,V,T,P,'{self.env.pgprim}',S{self.env.sow}));


*--- Levelizer Equation ---

    EQ_STSLEV(RTP_VINTYR({self.env.r_v_t},P),TSL,{rts}{self.env.swx})$({self.env.swtx}(STOAL(R,S)=PRC_SGL(R,P))$TS_GROUP(R,TSL,S)$RP_STL(R,P,TSL,'UP'))..

* Sum of levelizers must be less than average variation over S
        SUM(TS_MAP(R,TS,S)$STOA(TS),({self.env.var}_SIN(R,V,T,P,'{self.env.pgprim}',TS{self.env.sow})+{self.env.var}_UDP(R,V,T,P,TS,'LO'{self.env.sow})+{macro.var_sts.render("R", "V", "T", "P", "TS", "'N'")})/RS_STGPRD(R,TS))
        =L=
        SUM(RS_BELOW1(R,S,TS)$RS_FR(R,TS,S),{self.env.var}_ACT(R,V,T,P,TS{self.env.sow})/RS_STGPRD(R,TS)*RS_FR(R,TS,S));
""",
        )
