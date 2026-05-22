# coef_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_EXT.vda oversees extended preprocessor activities after COEF_MAIN
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.eqashar_vda import EqasharVda
from core.eqlducs_vda import EqlducsVda
from core.fillwave_gms import FillwaveGms
from core.powerflo_vda import PowerfloVda

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefExtVda(GamsClass):
    """Translation unit for coef_ext.vda."""

    # Instance attributes
    module_name: str = "coef_ext_vda"
    gams_source: str = "coef_ext.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        self.comp1()
        if self.env.waver.upper() == "YES":
            # fmt: off
            batincludes = [
                ("PRC_RESID", "PRC", "0" ),
                ("COM_PROJ", "COM", "1" ),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    FillwaveGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                    )
                )
            self.tc.enqueue(self.exec1)

        # RESID
        self.tc.enqueue(self.make_sensible_resid_pasti)

        # * Offline capacity terms & STS amendments
        self.env.set_global(
            "upscaps",
            f"-SUM(TS_MAP(R,ALL_TS,S)$RPS_UPS(R,P,ALL_TS),{self.env.var}_UPS(R,V,T,P,ALL_TS,'N'{self.env.sow}))",
        )
        self.comp2(
            var=self.env.var,
            sow=self.env.sow,
        )

        self.tc.enqueue(
            self.exec2,
            pgprim=self.env.pgprim,
            condition1=self.env.stsflx.upper() != "YES",
            condition2=self.env.sensis.upper() != "YES",
        )

        self.include(EqlducsVda(self.tc, self.env))
        self.include(EqasharVda(self.tc, self.env))

        if self.tc.defined("COM_CSTBAL"):
            self.include(PowerfloVda(self.tc, self.env, arg1="CSTBAL"))

        self.tc.enqueue(self.exec3)

    def comp1(self: CoefExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER VDA_DISC(R,ALLYEAR);
$ CLEAR VDA_DISC
""",
        )

    def exec1(self: CoefExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=VDA_DISC;
""",
        )

    def make_sensible_resid_pasti(self: CoefExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Try making sensible RESID PASTI (although it does not affect solution)
* Finalize PRC_RESID capacity coefficients:
  LOOP(T, TRACKP(R,P)$((PRC_RESID(R,T,P)>0)$PRC_RESID(R,T,P)) = YES);
  LOOP(PYR_S(V),
  LOOP(PRC_RCAP(TRACKP(R,P)),Z=SMAX(T,PRC_RESID(R,T,P));RTFORC(RTP_CPTYR(R,V,T,P))=Z-PRC_RESID(R,T,P)+EPS;PRC_RESID(R,T,P)$RTFORC(R,V,T,P)=Z);
    NCAP_PASTI(R,V,P)$PRC_RESID(R,'0',P) = (SUM(T,PRC_RESID(R,T,P)*D(T))/SUM(T$(PRC_RESID(R,T,P)>0),D(T)))$TRACKP(R,P);
  );
  PRC_RESID(R,'0',P)$(NOT TRACKP(R,P)) = 0;
  COEF_CPT(RTP_CPTYR(R,PYR_S(V),T,P))$TRACKP(R,P) = PRC_RESID(R,T,P)/NCAP_PASTI(R,V,P);
""",
        )

    def comp2(self: CoefExtVda, var: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
$ macro var_sts(r,v,t,p,ts,bd) sum(rp_stl(r,p,tsl,bd)$ts_group(r,tsl,ts),{var}_udp(r,v,t,p,ts,bd{sow}))
""",
        )

    def exec2(
        self: CoefExtVda, pgprim: str, condition1: bool, condition2: bool
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{"RP_STL(RP_STS,TSL,BD)=0;" if condition1 else ""}
*-----------------------------------------------------------------------------
* Get AF-UPs for processes having storage level constrained
  COEF_AFUPS(RTP(R,V,P),S)$(NOT RPS_CAFLAC(R,P,S,'UP')) $= NCAP_AF(RTP,S,'UP')$RPS_STG(R,P,S);
  COEF_AFUPS(RTP(R,V,P),S(STL))$RPS_STG(R,P,S) $= NCAP_AFC(RTP,'{pgprim}',STL);
  COEF_AFUPS(R,V,P,S)$(NOT PRC_CAP(R,P)) = NO;
* Cycling cost annuity
  ACT_CSTUP(RTP(R,V,P),TSL(S),CUR)$(RDCUR(R,CUR)$STG_MAXCYC(RTP))=ACT_CSTUP(RTP,TSL,CUR)*G_DRATE(R,V,CUR)/(1-(1+G_DRATE(R,V,CUR))**(-NCAP_TLIFE(RTP)));
*-----------------------------------------------------------------------------
* Remove commodity balance equations from non-demand sinks
  OPTION TRACKP < RTP, TRACKC < RHS_COMBAL, RCS < IRE_FLOSUM;
  LOOP(TRACKP(R,P),TRACKC(R,C)$TOP(R,P,C,'IN') = YES);
  TRACKC(R,C) $= SUM(RPC_IRE(TRACKP(R,P),C,'EXP'),1);
  TRACKC(RC)  $= SUM(RCS(RC,S),1); TRACKC(DEM)=YES;
  TRACKC(R,C) $= SUM(RPC_NOFLO(TRACKP(R,P),C),1);
  RCS_COMBAL(RTCS_VARC(R,T,C,S),L)$(NOT TRACKC(R,C)) = NO;
* Reduce overhead from UCU trades
  TRACKC(RC) = COM_UNIT(RC,'UCU')$(NOT TRACKC(RC));
  RTCS_VARC(R,T,C,S)$((NOT RHS_COMPRD(R,T,C,S))$TRACKC(R,C)) = NO;
  TOP_IRE('IMPEXP',C,TRACKC,P) = NO;
  OPTION CLEAR=TRACKC,CLEAR=TRACKP,CLEAR=RCS;
* Filter out UC constraints
  IF(CARD(UC_TIME),OPTION R_UC<UC_TIME;
    LOOP(R_UC(R,UCN)$(ROUND(UC_TIME(UCN,R,'0'))=-13),UC_ON(R_UC)=NO; IF(UC_R_SUM(R_UC),UC_ON(UC_R_SUM(REG,UCN))=NO));
    UC_TIME(UCN,R,T)$((NOT UC_ON(R,UCN))$R_UC(R,UCN))=0; OPTION CLEAR=R_UC);
*-----------------------------------------------------------------------------
* Add singleton ACT_EFFs to COEF_PTRANS or ACT_FLO
  RP_CGC(RPG_1ACE) = YES; OPTION TRACKPC < RPG_1ACE, RP_GRP < RP_CGC;
* Convert ACT_EFF factors for reduced flows
  TRACKPC(TRACKPC) = RPC_FFUNC(TRACKPC);
  ACT_FLO(RTP(R,V,P),C,S)$(RPCS_VAR(R,P,C,S)$TRACKPC(R,P,C)) = 1/SUM(RP_CGC(R,P,CG,C),MAX(MICRO,ACT_EFF(RTP,CG,S)*(1+(ACT_EFF(RTP,C,S)-1)$ACT_EFF(RTP,C,S))));
* Convert FLO_FUNCX factors for all reduced flows
  OPTION CG_GRP <= RTP_FFCX;
  LOOP(RPCG_PTRAN(RP,C,COM,CG,CG2)$CG_GRP(RP,CG,CG2),IF(RPC_FFUNC(RP,C),RP_DCGG(RP,C,CG,CG2,'UP')=YES; ELSE RP_DCGG(RP,COM,CG,CG2,'LO')=YES));
  RP_DCGG(TRACKPC(RP,COM),CG,C,'UP')$(RP_CGC(RP,CG,COM)$RPC_ACT(RP,C)) $= CG_GRP(RP,CG,C);
  RTP_FFCX(RTP_CAPYR(R,V,T,P),ACTCG,C)$RPC_FFUNC(R,P,C) $= SUM(RP_DCGG(R,P,C,CG,CG2,L),(POWER(RTP_FFCX(R,V,T,P,CG,CG2)+1,BDSIG(L))-1)$(RTP_FFCX(R,V,T,P,CG,CG2)-MIN(0,BDSIG(L))));
  LOOP(RP_DCGG(R,P,C,CG,CG2,L),RTP_FFCX(R,V,T,P,CG,CG2)=0);
* Default to COEF_PTRAN
  RP_CGC(R,P,CG,C)$TRACKPC(R,P,C) = NO;
  COEF_PTRAN(RTP(R,V,P),CG,C,COM,S)$(RPCS_VAR(R,P,C,S)$RPC_PG(R,P,COM)$RP_CGC(R,P,CG,C)) = ACT_EFF(RTP,CG,S)*PRC_ACTFLO(RTP,COM)*(1+(ACT_EFF(RTP,C,S)-1)$ACT_EFF(RTP,C,S));
  ACT_EFF(R,LL,P,CG,S)$RP_GRP(R,P,CG) = 0;
  OPTION RP_GRP < RP_CGC; RPCC_FFUNC(RP_GRP(R,P,CG),COM)$RPC_PG(R,P,COM) = YES;
{"OPTION CLEAR=RPCG_PTRAN;" if condition2 else ""}
  OPTION CLEAR=TRACKPC,CLEAR=RP_GRP,CLEAR=CG_GRP,CLEAR=RP_DCGG,CLEAR=RTP_CAPYR,CLEAR=RP_CGC;
  """,
        )

    def exec3(self: CoefExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  COEF_PVT(R,T)$(NOT COEF_PVT(R,T)) = FPD(T);
  VDA_DISC(R,T) $= COEF_PVT(R,T);
  COEF_ILED(RTP(R,T,P))$NCAP_BND(RTP,'N') = MOD(COEF_ILED(RTP),1000)+EPS$NCAP_ILED(RTP);
""",
        )
