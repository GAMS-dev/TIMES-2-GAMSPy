# pp_actef_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * PP_ACTEF.MOD : Make the necessary preparations for EQE_ACTEFF equations
# *  - Aggregate / inherit ACT_EFF parameters
# *==============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpActefVda(GamsClass):
    """Translation unit for pp_actef.vda."""

    # Instance attributes
    module_name: str = "pp_actef_vda"
    gams_source: str = "pp_actef.vda"

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
        g = self.tc
        m = g.container
        if self.arg1 == "LVL":
            g.micro = Parameter(m, "MICRO", records=1e-6)
            self.tc.enqueue(self.exec1)
        else:  # EQUA
            self.env.set_scoped("shg", f",P,CG,'{self.env.pgprim}'")
            base_shp1 = f"(1+RTP_FFCX(R,V,T{self.env.shg})$PRC_VINT(R,P))"
            if self.tc.defined("RTP_FFCS"):
                self.env.set_scoped(
                    "shp1", f"{base_shp1}*(1+RTP_FFCS(R,V{self.env.shg}{self.env.sow}))"
                )
            else:
                self.env.set_scoped("shp1", base_shp1)

            self.define_equation(
                eq=self.env.eq,
                r_v_t=self.env.r_v_t,
                swt=self.env.swt,
                var=self.env.var,
                sow=self.env.sow,
                shp1=self.env.shp1,
            )

    def define_equation(
        self: PpActefVda, eq: str, r_v_t: str, swt: str, var: str, sow: str, shp1: str
    ) -> None:
        rts = macro.rts(s="S", g=self.tc, env=self.env)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 {eq}E_ACTEFF(RTP_VINTYR({r_v_t},P),CG,IO,{rts} {swt})$(RPS_S1(R,P,S)$RPG_ACE(R,P,CG,IO))..

* Sum over input flows
  SUM((RPC_ACE(R,P,C),COM_GMAP(R,CG,C),TS_MAP(R,S,TS))$RTPCS_VARF(R,T,P,C,TS),
    (1+(ACT_EFF(R,V,P,C,TS)-1)$ACT_EFF(R,V,P,C,TS)) * {var}_FLO(R,V,T,P,C,TS {sow})) *
* Multiply with group efficiency
  SUM(TS_ANN(S,TS),ACT_EFF(R,V,P,CG,TS))*{shp1}

   =E=

  SUM(PRC_TS(R,P,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS) *
* COM_FR needs to be taken into account if process operates above S
    ({var}_ACT(R,V,T,P,TS {sow})$(NOT RP_PGFLO(R,P)) +
     SUM(RPC_PG(R,P,C),({var}_ACT(R,V,T,P,TS {sow})$RP_PGACT(R,P)+({var}_FLO(R,V,T,P,C,TS {sow})/PRC_ACTFLO(R,V,P,C))$(NOT RP_PGACT(R,P))) *
       (1+RTCS_FR(R,T,C,S,TS)))$RP_PGFLO(R,P)))$(NOT RPG_PACE(R,P,CG)) +

* Handle the special cases where ACT_EFF has been specified for PG commodities
  SUM(PRC_TS(R,P,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS) *
    SUM(RPC_PG(R,P,C), ({var}_ACT(R,V,T,P,TS {sow})$RP_PGACT(R,P) +
         ({var}_FLO(R,V,T,P,C,TS {sow})/PRC_ACTFLO(R,V,P,C))$(NOT RP_PGACT(R,P))) /
        (1+(ACT_EFF(R,V,P,C,TS)-1)$ACT_EFF(R,V,P,C,TS)) * (1+RTCS_FR(R,T,C,S,TS))))$RPG_PACE(R,P,CG) +

* Partial loads
  SUM(RP_PL(R,P,L('FX')),ACT_LOSPL(R,V,P,L) *
    SUM(PRC_TS(R,P,TS)$RS_FR(R,S,TS),{var}_UPS(R,V,T,P,TS,L{sow})*RS_FR(R,S,TS)));
""",
        )

    def exec1(self: PpActefVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=UNCD7;
*-----------------------------------------------------------------------------
* Save commodity ACT_EFF partitions
  CG_GRP(RPC_ACE(RPC(R,P,C)),C) = YES;
  OPTION KEEP_FLOF<RPG_1ACE, CLEAR=RPG_1ACE;
* Catch singleton groups
  LOOP(RPG_ACE(RP_PGACT(R,P),CG,IO)$(SUM(TOP(R,P,C,IO)$COM_GMAP(R,CG,C),1) LE 1),
    IF(NOT RPG_PACE(R,P,CG)+RP_PL(R,P,'FX'),RP_GRP(R,P,CG)=YES; RPG_1ACE(RP_GRP(R,P,CG),C)$(TOP(R,P,C,IO)$COM_GMAP(R,CG,C)) = YES));
* Accept EPS for shadow group flows only
  ACT_EFF(R,LL,P,C,S)$((RPC_PG(R,P,C)+KEEP_FLOF(R,P,C))$(ACT_EFF(R,LL,P,C,S)=0)$ACT_EFF(R,LL,P,C,S))=0;
  LOOP(RPG_ACE(RPC_SPG(R,P,C),IO),ACT_EFF(RTP(R,V,P),C,S)$ACT_EFF(RTP,C,S)=SQRT(ABS(ACT_EFF(RTP,C,S))));
* Store all flow level commodities in CG_GRP
  CG_GRP(RPG_1ACE) = YES;
  RPG_ACE(RP_GRP,IO) = NO;
*-----------------------------------------------------------------------------
* Inherit values to target timeslices when possible
  VDA_FLOP(R,LL--ORD(LL),P,CG,S--ORD(S))$STOAL(R,S)$=ACT_EFF(R,LL,P,CG,S); OPTION RPC_ACE<VDA_FLOP, CLEAR=VDA_FLOP;
  UNCD7('1',CG_GRP(RPC_ACE(R,P,CG),C),TSL,S+STOA(S))$TS_GROUP(R,TSL,S)$=RPCS_VAR(R,P,C,S);
  UNCD7('2',RPG_ACE(RPC_ACE(R,P,CG),IO),TSL,S+STOA(S))$TS_GROUP(R,TSL,S)$=RPS_S1(R,P,S); CG_GRP(RPC_ACE,C)=NO;
  IF(CARD(NORTS),LOOP((MIYR_1(T),UNCD7(J,R,P,CG,ITEM,TS,TS)),ACT_EFF(RTP(R,V,P),CG,S)$(NORTS(R,V,S)+NORTS(R,T,S)$PASTMILE(V))=0));
  OPTION CLEAR=RPC_ACE;
  LOOP(RPG_ACE(R,P,CG,IO),RPC_ACE(R,P,C)$(TOP(R,P,C,IO)$COM_GMAP(R,CG,C)) = YES);
  RPC_ACE(KEEP_FLOF) = NO;
*-----------------------------------------------------------------------------
* Aggregate values to target timeslices when inheritance could not be done
  LOOP(UNCD7(J,R,P,CG,ITEM,TSL,STL), MY_TS(S) = TS_GROUP(R,TSL,S);
   LOOP(RTP(R,V,P), TS_ARRAY(S) = ACT_EFF(R,V,P,CG,S);
    ACT_EFF(R,V,P,CG,MY_TS)$(NOT TS_ARRAY(MY_TS)) =
      SUM(RS_TREE(FINEST(R,S),MY_TS), G_YRFR(R,S) * (TS_ARRAY(S) +
           SUM(RS_BELOW(R,ALL_TS,S)$((NOT SUM(TS_MAP(R,SL,S)$RS_BELOW(R,ALL_TS,SL),TS_ARRAY(SL)))$TS_ARRAY(ALL_TS)),
               TS_ARRAY(ALL_TS))))/G_YRFR(R,MY_TS)));
*-----------------------------------------------------------------------------
  FSCKS(CG_GRP(R,P,CG,C),CG,S)$RPCS_VAR(R,P,C,S) = YES; OPTION FFCKS <= FSCKS;
  ACT_EFF(RTP(R,V,P),CG,S+STOA(S))$(RPS_S1(R,P,S)$STOA(S)$ACT_EFF(RTP,CG,S)) = 0;
  ACT_EFF(RTP(R,V,P),CG,S)$(NOT ACT_EFF(RTP,CG,S)) $= SUM(FFCKS(R,P,CG,CG,S),ACT_EFF(R,V,P,CG,'ANNUAL'));
  OPTION CLEAR=FFCKS,CLEAR=FSCKS,CLEAR=CG_GRP;
""",
        )
