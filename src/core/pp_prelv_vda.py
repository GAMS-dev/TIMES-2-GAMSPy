# pp_prelv_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * pp_prelvl.vda - Auxiliary preprocessing before levelizing
# *=============================================================================*
# * Called AFTER establishing RTCS_VARC and RPCS_VAR.
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.dynslite_vda import DynsliteVda
from core.powerflo_vda import PowerfloVda
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpPrelvVda(GamsClass):
    """Translation unit for pp_prelv.vda."""

    # Instance attributes
    module_name: str = "pp_prelv_vda"
    gams_source: str = "pp_prelv.vda"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.compile()

    def compile(self: PpPrelvVda) -> None:
        g = self.tc
        self.tc.enqueue(self.restore_ncap_tlife, dflbl=self.env.dflbl)
        self.tc.enqueue(self.filter_vda_flop, pgprim=self.env.pgprim)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
{"PRC_ACTFLO(R,V,P,C)$((NOT KEEP_FLOF(R,P,C))$TRACKPC(R,P,C)) = 0;" if self.env.shell.upper() == "ANSWER" else ""}
""",
        )
        self.tc.enqueue(self.exec1)
        self.tc.enqueue(self.preprocess_vda_flop)
        self.tc.enqueue(self.partition_groups)

        self.tc.enqueue(self.process_trackp)
        self.tc.enqueue(self.update_trackp)
        self.tc.enqueue(self.vda_flop_direction)
        self.tc.enqueue(self.set_flo_sum)
        self.tc.enqueue(self.distribute_ire_flosum, pgprim=self.env.pgprim)
        self.tc.enqueue(self.preprocess_flo_emis)
        self.tc.enqueue(self.update_src_commodities)
        self.tc.enqueue(
            self.add_activity_src,
            pgprim=self.env.pgprim,
            rl=self.env.rl,
            pl=self.env.pl,
        )
        self.tc.enqueue(self.add_single_src_commodity, pgprim=self.env.pgprim)
        self.tc.enqueue(self.preprocessing_for_veda_interface_before_include)
        self.include(
            PpLvlfcMod(
                self.tc,
                self.env,
                config=PpLvlfcModConfig(
                    arg1=g.flo_fr,
                    arg2=(g.p, g.c),
                    arg3=g.RpcsVar,
                    arg4=(g.bd,),
                    arg5=("0", "0"),
                    arg6=g.allts,
                    arg7=(g.t,),
                    arg8=g.RpcConly[g.r, g.t, g.p, g.c],
                ),
            )
        )

        self.tc.enqueue(self.preprocessing_for_veda_interface_after_include)
        if self.env.powerflo.upper() == "YES":
            self.include(PowerfloVda(self.tc, self.env))
        self.tc.enqueue(self.set_com_var_def_bounds)
        if self.env.rts() != "S":
            self.include(DynsliteVda(self.tc, self.env, arg1="PRELEV"))

    def restore_ncap_tlife(self: PpPrelvVda, dflbl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Restore NCAP_TLIFE for RESID
LOOP(PYR_S(V),NCAP_TLIFE(R,V,P)$PRC_RESID(R,'{dflbl}',P) = PRC_RESID(R,'{dflbl}',P));
""",
        )

    def filter_vda_flop(self: PpPrelvVda, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* For filtering VDA_FLOP, check ACT_EFF groups
TRACKPC(RPC_SPG(R,P,C))$((NOT RPG_1ACE(R,P,C,C))$RPC_ACE(R,P,'{pgprim}')) = YES;
  Z = CARD(VDA_FLOP);
  VDA_FLOP(R,LL,P,C,S)$((NOT KEEP_FLOF(R,P,C))$TRACKPC(R,P,C)) = 0;
""",
        )

    def exec1(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
Z = Z-CARD(VDA_FLOP); IF(Z, DISPLAY 'Deleted FLOPS for SPG:',Z);
* Residual values
  ACT_FLO(R,LL,P,C,S)$RPS_PRCTS(R,P,S) = 0;
  OPTION RPC_AFLO < ACT_FLO, RP_GRP < VDA_FLOP, PRC_ACT < RP_GRP, CLEAR=ACT_FLO,CLEAR=KEEP_FLOF,CLEAR=TRACKPC;
  TRACKPC(RP_GRP(RPC)) = YES; RP_GRP(TRACKPC) = NO;
  RP_XRED(PRC_ACT(R,P)) = (NOT RP_PGFLO(R,P)+RP_PGACT(R,P)+RP_SGS(R,P))$(CHP(R,P)->RP_XRED(R,P));
  RPC_AFLO(TRACKPC(RP_STD(RP_XRED),C)) = YES;
  RPC_AFLO(R,P,C)$(TRACKPC(R,P,C)->RPC_PG(R,P,C)) = NO;
  ACT_FLO(R,V,P,C,S)$RPC_AFLO(R,P,C) $= VDA_FLOP(R,V,P,C,S);
  VDA_FLOP(RTP,C,S)$ACT_FLO(RTP,C,S) = 1;
""",
        )

    def preprocess_vda_flop(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Preprocessing of VDA_FLOP after establishing PRC_SPG
* RP_GRP contains only CGs not in topology, but including some C in RPC
  RP_GRP(R,P,CG)$(NOT SUM(RPC(R,P,C)$COM_GMAP(R,CG,C),1)) = NO;
* Set PRC_CG now automatically
  PRC_CG(RP_GRP) = YES;
* Identify processes with PG-based FLO_SUMs
  LOOP(TRACKPC(RPC_PG(R,P,C)),TRACKP(R,P)=YES);
* Add default value for PG commodities not in TRACKPC
  VDA_FLOP(RTP(R,V,P),C,ANNUAL)$((RPC_PG(R,P,C)*(NOT TRACKPC(R,P,C)))$TRACKP(R,P)) = 1;
* Remove all PG commodities from TRACKPC:
  TRACKPC(RPC_PG) = NO;
""",
        )

    def partition_groups(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Partition the groups into direct/PG based ones
  CG_GRP(RP_PG(R,P,CG2),CG)$RP_GRP(R,P,CG) = YES;
  RPCC_FFUNC(CG_GRP(TRACKP(R,P),CG2,CG))$SUM(RPC_SPG(R,P,C)$COM_GMAP(R,CG,C),1) = YES;
  CG_GRP(RPCC_FFUNC) = NO; OPTION CLEAR=RP_GRP,CLEAR=PRC_ACT;
""",
        )

    def process_trackp(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Remove from TRACKP those processes for which CG has been defined:
  LOOP(RPCC_FFUNC(R,P,CG2,CG),TRACKP(R,P) = NO);
""",
        )

    def update_trackp(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Add into FFUNC single SPG commodities for remaining TRACKP:
  TRACKP(RP)$(SUM(RPC_SPG(TRACKPC(RP,C)),1)<>1) = NO;
  RPCC_FFUNC(RP_PG(TRACKP(RP),CG),C) $= SUM(RPC_SPG(TRACKPC(RP,C)),1);
  TRACKPC(RPC_SPG(TRACKP,C)) = NO;
""",
        )

    def vda_flop_direction(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* VDA_FLOP is in the direction from the PG to the CG:
FLO_FUNC(RTP(R,V,P),CG2,CG,S)$RPCC_FFUNC(R,P,CG2,CG) = VDA_FLOP(RTP,CG,S);
""",
        )

    def set_flo_sum(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Set FLO_SUM for individual commodities in PG:
FLO_SUM(RTP(R,V,P),CG2,C,CG,S)$(RPC_PG(R,P,C)$RPCC_FFUNC(R,P,CG2,CG)) = VDA_FLOP(RTP,C,S)*(1/PRC_ACTFLO(RTP,C));
* Set FLO_SUM for groups of commodities:
  FLO_SUM(RTP(R,V,P),CG2,C,CG,S)$(RPC_PG(R,P,C)$CG_GRP(R,P,CG2,CG)) = VDA_FLOP(RTP,CG,S)*(1/PRC_ACTFLO(RTP,C));
* Finally, handle single commodities without a group (and not in PG either)
  FLO_SUM(RTP(R,V,P),CG,C,COM,S)$(RP_PG(R,P,CG)*RPC_PG(R,P,C)*TRACKPC(R,P,COM)) $= VDA_FLOP(RTP,COM,S)*(1/PRC_ACTFLO(RTP,C));
  FLO_FUNC(RTP(R,V,P),ACTCG,C,ANNUAL(S))$((FLO_FUNCX(RTP,ACTCG,C)<0)$TRACKPC(R,P,C)) $= VDA_FLOP(RTP,C,S);
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=VDA_FLOP,CLEAR=CG_GRP,CLEAR=RPCC_FFUNC;
""",
        )

    def distribute_ire_flosum(self: PpPrelvVda, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Distribute IRE_FLOSUM for ACT; Ignore possible overwriting for now
  PRC_ACTFLO(R,V,P,C) $= FLO_EMIS(R,V,P,'{pgprim}',C,'ANNUAL')$PRC_MAP(R,'STG',P);
  IRE_FLOSUM(R,V,P,C(ACTCG),S,IE,COM,'OUT') $= FLO_EMIS(R,V,P,C,COM,S)$RP_AIRE(R,P,IE);
""",
        )

    def preprocess_flo_emis(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Preprocessing of FLO_EMIS
  OPTION RP_CGC <= FLO_EMIS;
  FLO_EMIS(RTP(R,V,P),C,C,S)$(RP_CGC(R,P,C,C)$RPC_PG(R,P,C)) = 1+(FLO_EMIS(RTP,C,C,S)-1)/PRC_ACTFLO(RTP,C);
  RP_CGC(RP_IRE(R,P),CG,C)=NO; RP_CGC(RPC_STG,C)=NO;
  RPCC_FFUNC(RP_CGC(RPC,COM)) = YES;
  RP_CGC(RPCC_FFUNC(RPC,COM)) = NO;
  RPC_EMIS(R,P,C)$SUM(RPCC_FFUNC(R,P,COM,C),1) = NO;
""",
        )

    def update_src_commodities(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Add groups of source commodities
  FSCK(RP_CGC(R,P,CG,COM),C)$(COM_GMAP(R,CG,C)$RPC(R,P,C)) = YES;
  LOOP(FSCK(R,P,CG,COM,C), FLO_SUM(R,V,P,COM,C,COM,S) $= FLO_EMIS(R,V,P,CG,COM,S));
  RPC_EMIS(R,P,COM)$SUM(FSCK(R,P,CG,COM,C),1) = NO;
""",
        )

    def add_activity_src(self: PpPrelvVda, pgprim: str, rl: str, pl: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Add activity sources
  FLO_SUM(RTP(R,V,P),COM,C,COM,S)$(RPC_PG(R,P,C)$RP_CGC(R,P,'{pgprim}',COM)) = FLO_EMIS(RTP,'{pgprim}',COM,S)/PRC_ACTFLO(RTP,C);
  RP_CGC(R,P,'{pgprim}',C) = NO; PUTGRP=0;
  LOOP(RP_CGC(R,P,CG,COM)$RPC_EMIS(R,P,COM),
  {pp_qaput("PUTOUT", "PUTGRP", "01", "FLO_EMIS with no members of source group in process - ignored")}
    PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' CG=',CG.TL,' COM=',COM.TL;
  );
  FLO_SUM(RTP(R,V,P),COM,C,COM,ANNUAL)$RPC_PG(R,P,C) $= SUM(RP_CGC(R,P,CG,COM)$RPC_EMIS(R,P,COM),EPS);
""",
        )

    def add_single_src_commodity(self: PpPrelvVda, pgprim: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Add single source commodities
  OPTION CLEAR=RP_CGC, CLEAR=FSCK, CLEAR=RPC_EMIS, CG_GRP < RPCC_FFUNC;
  FLO_SUM(RTP(R,V,P),C,COM,C,S)$CG_GRP(R,P,C,COM) = FLO_EMIS(RTP,COM,C,S);
  FLO_EFF(RTP(R,V,P),C,COM,S)$((NOT CG_GRP(R,P,C,COM))$RPC_PG(R,P,COM)$CHP(R,P)) $= FLO_EMIS(RTP,'{pgprim}',C,S);
  OPTION NE<IRE_BND,CLEAR=CG_GRP,CLEAR=RPCC_FFUNC,CLEAR=FLO_EMIS;
""",
        )

    def preprocessing_for_veda_interface_before_include(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Remove non-standard shares from FLO_SHAR
  FLO_ASHAR(R,DM_YEAR,P,C,CG,S,BD) $= FLO_SHAR(R,DM_YEAR,P,C,CG,S,BD)$(NOT RP_STD(R,P));
  FLO_SHAR(R,LL,P,C,CG,S,BD)$FLO_ASHAR(R,LL,P,C,CG,S,BD) = 0;
  NCAP_CHPR(RTP(R,V,P),'N') $= NCAP_CHPR(R,'0',P,'N');
* Support for levelised FLO_FR
  RPC_CONLY(RTP,C) $=SUM(L$FLO_FR(RTP,C,'ANNUAL',L),1);
""",
        )

    def preprocessing_for_veda_interface_after_include(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  FLO_FR(RPC_CONLY(R,T,P,C),S,'N')=MIN(1,SUM(RS_BELOW1(R,S,TS)$RPCS_VAR(R,P,C,TS),G_YRFR(R,TS)))$TS_CYCLE(R,S);
  FLO_FR(RPC_CONLY(R,T,P,C),S,BD)$FLO_FR(R,T,P,C,S,BD)=FLO_FR(R,T,P,C,S,BD)*G_YRFR(R,S)$RPCS_VAR(R,P,C,S);
* Support using aggregated ANNUAL variable for FLO_FR fractions
  IF(CARD(FLO_FR),
    RVPCSL(RTPC(R,T,P,C),TS(S+STOA(S)),BD)$(FLO_FR(R,'0',P,C,TS,BD)$FLO_FR(RTPC,S,BD)) = YES;
    RVPCSL(RTPC(R,T,P,C),S+STOA(S),BD)$FLO_FR(RTPC,S,'N') = NO;
    RVPCSL(RTPC(R,T,P,C),S,'N')$TS_CYCLE(R,S) $= SUM(RVPCSL(RTPC,TS,BD),1));
  FLO_FR(RVPCSL(R,T,P,C,S,'N'))$(NOT RPCS_VAR(R,P,C,S)) = EPS+1$ANNUAL(S);
* Cleanup some dummies
  TOP_IRE('IMPEXP',C,R,C,P(DUMIMP))$(NOT NE(R,C)) = NO;
  OPTION CLEAR=NE,CLEAR=RVPCSL,CLEAR=RPC_CONLY;
""",
        )

    def set_com_var_def_bounds(self: PpPrelvVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Set COM_VAR default bounds
  COM_BNDNET(R,T,C,ANNUAL(S),'N')$(NOT COM_BNDNET(R,T,C,S,'N')) $=COM_BNDNET(R,'0',C,S,'N');
  COM_BNDNET(RTCS_VARC(RTC,S),BDLOX(BD))$((NOT COM_BNDNET(RTC,S,BD))$COM_BNDNET(RTC,'ANNUAL','N')) =
    (EPS-INF$BDNEQ(BD))$(-SIGN(COM_BNDNET(RTC,'ANNUAL','N'))=1$BDNEQ(BD));
  COM_BNDPRD(R,T,C,ANNUAL(S),'N')$(NOT COM_BNDPRD(R,T,C,S,'N')) $=COM_BNDPRD(R,'0',C,S,'N');
  COM_BNDPRD(RTCS_VARC(RTC,S),BDLOX(BD))$((NOT COM_BNDPRD(RTC,S,BD))$COM_BNDPRD(RTC,'ANNUAL','N')) =
    (EPS-INF$BDNEQ(BD))$(-SIGN(COM_BNDPRD(RTC,'ANNUAL','N'))=1$BDNEQ(BD));
""",
        )
