# eqashar_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQx_ASHAR is an ANNUAL level share constraint on flows
# *   %1 - equation declaration type
# *   %2 - BOUND type for %1
# *=============================================================================*
# * Comments:
# *-----------------------------------------------------------------------------
# *$ONLISTING


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core import pp_lvlfc_mod
from core import cal_nored_red
from core import cal_red_red

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqasharVda(GamsClass):
    """Translation unit for eqashar.vda."""

    # Instance attributes
    module_name: str = "eqashar_vda"
    gams_source: str = "eqashar.vda"

    def __init__(
        self: EqasharVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self: EqasharVda) -> None:
        if len(self.arg1):
            self.label_eqdef(
                no_red=self.env.cal_red == "cal_nored.red",
                eq=self.env.eq,
                r_v_t=self.env.r_v_t,
                swt=self.env.swt,
                sow=self.env.sow,
                var=self.env.var,
            )
        else:
            self.tc.enqueue(self.collect_all_flo_ashar_groups)
            self.include(
                pp_lvlfc_mod.PpLvlfcMod(
                    tc=self.tc,
                    env=self.env,
                    arg1="FLO_ASHAR",
                    arg2="P",
                    arg3="RPS_S2",
                    arg4=",BD",
                    arg5=",''",
                    arg6="ALL_TS",
                    arg7="V",
                    arg8="1",
                    arg9="0",
                    arg10=",C,CG",
                    arg11="N",
                )
            )

    def collect_all_flo_ashar_groups(self: EqasharVda):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Collect all FLO_ASHAR groups
  OPTION CG_GRP <= FLO_ASHAR;
  FLO_SHAR(R,'0',P,C,CG,ANNUAL,'LO')$CG_GRP(R,P,C,CG) = EPS;

* We have been left with any C not in CG or not in RPC
  IF(CARD(CG_GRP),
    LOOP((CG_GRP(RPC(R,P,C),C),COM_TMAP(R,COM_TYPE(CG),C)),RPCG_ASHAR(R,P,C,CG,S)$(PRC_SGL(R,P)=STOAL(R,S))=-1);
    FLO_ASHAR(RTP(R,V,P),C,COM_TYPE(CG),S,BD)$COM_TMAP(R,COM_TYPE,C) $= FLO_ASHAR(R,V,P,C,C,S,BD);
    FLO_ASHAR(R,LL,P,C,C,S,BD) = 0; CG_GRP(RPC(RP,C),C) = NO;
    RP_PGFLO(RP_FLO(RP)) $= SUM(CG_GRP(NO_ACT(RP),C,ACTCG),1);
    RPCG_ASHAR(CG_GRP(RPC,CG),S)$=RPCS_VAR(RPC,S);
    RPCG_ASHAR(CG_GRP(RPC_STG(RP,C),ACTCG),S)=RPS_STG(RP,S)+PRC_TSL(RP,'ANNUAL')$ANNUAL(S);
    CG_GRP(RPC,CG)=NO;
    LOOP(CG_GRP(R,P,CG,CG2), Z=1;
      LOOP(COM_TSL(R,C(CG),TSL), Z=0; RPCG_ASHAR(R,P,CG,CG2,S)$TS_GROUP(R,TSL,S) = 1);
      IF(Z, RPCG_ASHAR(R,P,CG,CG2,ANNUAL) = YES));
    OPTION CLEAR=CG_GRP);
""",
        )

    def label_eqdef(
        self: EqasharVda,
        no_red: bool,
        eq: str,
        r_v_t: str,
        swt: str,
        sow: str,
        var: str,
    ) -> None:
        if no_red:
            cal_red_code = cal_nored_red.cal_nored_red(
                arg1="COM",
                arg2="COM1",
                arg3="TS",
                arg4="P",
                arg5="T",
                def_rtp_ffcs="RTP_FFCS" in self.tc.container.listSymbols()
                and self.tc.container["RTP_FFCS"].number_records,
                shff=self.env.shff,
                sow=self.env.sow,
                var=self.env.var,
            )
        else:
            cal_red_code = cal_red_red.cal_red_red(
                arg1="COM",
                arg2="COM1",
                arg3="TS",
                arg4="P",
                arg5="T",
                pgprim=self.env.pgprim,
                def_rtp_ffcs="RTP_FFCS" in self.tc.container.listSymbols()
                and self.tc.container["RTP_FFCS"].number_records,
                shff=self.env.shff,
                sow=self.env.sow,
                var=self.env.var,
            )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{eq}{self.arg1}_ASHAR(RTP_VINTYR({r_v_t},P),CG,CG2,RTS(S){swt})$(SUM(RS_TREE(R,S,TS)$FLO_ASHAR(R,V,P,CG,CG2,TS,'{self.arg2}'),1)$RPCG_ASHAR(R,P,CG,CG2,S))..

* sum over RPS_S2 timeslices
     SUM(RPS_S2(RP_FLO(R,P),SL)$TS_MAP(R,S,SL),
         SUM(TS_ANN(SL,TS),FLO_ASHAR(R,V,P,CG,CG2,TS,'{self.arg2}')) *
* sum over all flows in the reference group CG2
         (SUM((RTPCS_VARF(R,T,P,COM,TS),RS_TREE(R,SL,TS))$COM_GMAP(R,CG2,COM),
{cal_red_code}
             * MAX(RPCG_ASHAR(R,P,CG,CG2,S),1$SUM(TOP(R,P,C(CG),IO),TOP(R,P,COM,IO))$COM_TYPE(CG2)) *
* timeslice S coarser than variable or finer than variable
             RS_FR(R,SL,TS)*(1+RTCS_FR(R,T,COM,SL,TS))) +
* Allow referring to activity as well
          SUM((PRC_TS(R,P,TS),RTP_VARA(R,T,P))$RS_FR(R,SL,TS),RS_FR(R,SL,TS)*
            ({var}_ACT(R,V,T,P,TS {sow})*EXP((-ABS(STG_LOSS(R,V,P,TS))/2)$RP_STG(R,P)))$(NOT RP_PGFLO(R,P)) +
            SUM(RPC_PG(RP_STD(R,P),COM),({var}_ACT(R,V,T,P,TS {sow})$RP_PGACT(R,P)+({var}_FLO(R,V,T,P,COM,TS {sow})/PRC_ACTFLO(R,V,P,COM))$(NOT RP_PGACT(R,P))) *
              RS_FR(R,SL,TS)*(1+RTCS_FR(R,T,COM,SL,TS)))$RP_PGFLO(R,P))$ACTCG(CG2)
         )
        ) +
* Allow ANNUAL share for IRE processes
     SUM(ANNUAL(S),
       SUM(RPC_IRE(R,P,COM,IE)$(COM_GMAP(R,CG,COM)*((NOT IMPEXP(CG2))+SAMEAS(IE,CG2))),
         FLO_ASHAR(R,V,P,CG,CG2,S,'{self.arg2}') *
         (SUM(RTPCS_VARF(REG,T,P,C,TS)$((COM_GMAP(REG,CG2,C)+IMPEXP(CG2))$RPC_IRE(REG,P,C,IE)),
           {var}_IRE(REG,V,T,P,C,TS,IE{sow})$(NOT RPC_AIRE(REG,P,C))+({var}_ACT(REG,V,T,P,TS{sow})*PRC_ACTFLO(REG,V,P,C))$RPC_AIRE(REG,P,C)) +
          SUM(PRC_TS(R,P,TS),{var}_ACT(R,V,T,P,TS {sow}))$ACTCG(CG2)) -
         SUM(RTPCS_VARF(R,T,P,COM,TS),
           {var}_IRE(R,V,T,P,COM,TS,IE{sow})$(NOT RPC_AIRE(R,P,COM))+({var}_ACT(R,V,T,P,TS{sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM)))
        )$RP_IRE(R,P)

    ={self.arg1}=

* derived commodities, summed for all flows in the group CG
   SUM((RTPCS_VARF(R,T,P,COM,TS),COM_GMAP(R,CG,COM))$TS_MAP(R,S,TS),
{cal_red_code}
      )$RP_FLO(R,P) +
   SUM(PRC_TS(R,P,TS)$TS_MAP(R,S,TS),{var}_ACT(R,V,T,P,TS {sow})$(NOT NO_ACT(R,P))+
     SUM(RPC_PG(NO_ACT(R,P),C),{var}_FLO(R,V,T,P,C,TS {sow})/PRC_ACTFLO(R,V,P,C)))$ACTCG(CG) +
   SUM((TOP(RPC_STG(R,P,C(CG)),'OUT'),RPCS_VAR(R,P,C,TS)),RS_FR(R,S,TS)*(1+RTCS_FR(R,T,C,S,TS))*
     {var}_SOUT(R,V,T,P,C,TS{sow}/PRC_ACTFLO(R,V,P,C))$ACTCG(CG2)

;
""",
        )
