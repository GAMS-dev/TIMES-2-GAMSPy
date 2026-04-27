# init_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INIT_EXT.VDA has all the initial preprocessing for VEDA
# *=============================================================================*

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from core import equcrtp_vda

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitExtVda(GamsClass):
    """Translation unit for init_ext.vda."""

    # Instance attributes
    module_name: str = "init_ext_vda"
    gams_source: str = "init_ext.vda"

    def __init__(
        self: InitExtVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self: InitExtVda) -> None:
        m = self.tc.container
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Internal SETs
 SET RP_UX(R,P);
 SET RP_PL(R,P,L);
 SET RTP_PL(R,LL,P);
 SET RPS_UPS(R,P,S);
 SET RP_UPC(R,P,TSL,L);
 SET AFUPS(R,T,P,S);
 SET RP_DP(R,P) //;
 SET DP_LOSD(R,LL,P) //;
 SET FS_EMCB(R,P,C,C);
 SET RP_DCGG(R,P,C,CG,CG,L);
 SET RP_CGC(REG,PRC,CG,COM);
 SET RPC_IREIN(R,P,C,IE,IO) //;
* Sets for commodity specific availabilities
 SET RVPS(REG,ALLYEAR,PRC,TS);
 SET RPS_CAFLAC(R,P,S,BD);
 SET RVPCSL(R,YEAR,P,C,S,L);
* Sets for ACT_EFF processing
 SET RPG_ACE(R,P,CG,IO) //;
 SET RPG_PACE(R,P,CG) //;
 SET RPG_1ACE(R,P,CG,C) //;
 SET RPC_ACE(REG,PRC,CG) //;
 SET RVP_KMAP(R,YEAR,P,YEAR);
 SET DUMIMP / IMPNRGZ,IMPMATZ,IMPDEMZ /;
 SET NRGELC(ALL_R,C) 'Electricity';
*-----------------------------------------------------------------------------
* Internal PARAMATERs
  SCALAR MIYR_BOH / 0 /;
  PARAMETER REG_FIXT //;
  PARAMETER RTFORC(R,LL,LL,P) //;
* For dynamic process bounds
  PARAMETER PRC_DYNUC(UC_N,SIDE,R,ALLYEAR,P,UC_GRPTYPE,BD);
* For special handling of non-standard FLO_SHAR
  PARAMETER RPCG_ASHAR(R,P,CG,CG,S);
  PARAMETER FLO_ASHAR(REG,ALLYEAR,PRC,CG,CG,S,BD);
* For internal IRE prices processing
  PARAMETER PAR_IPRIC(R,ALLYEAR,P,C,TS,IE);
* For partial load efficiencies
  PARAMETER DP_PSUD(R,LL,P,UPT,BD) //;
* For storage level UP availability
  PARAMETER COEF_AFUPS(R,YEAR,P,S) //;
""",
        )

        self.tc.enqueue(
            self.basic_years_stuff,
            dflbl=self.env.dflbl,
            waver=self.env.waver,
        )

        self.tc.enqueue(
            self.peaking_and_storage_stuff,
        )

        if self.env.obmac != "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="PARAMETER VAR_SIFT(LL,S,L) //;",
            )

        self.add_records_to_universe_item(records=[""])

        self.tc.enqueue(self.clean_up_some_parameters)

        self.tc.enqueue(self.identify_and_initial_preprocessing)

        self.tc.enqueue(
            self.initial_preprocessing_of_com_agg,
            self.env.shell,
            self.env.dflbl,
        )

        # * Handle Updatable OFF-ranges & REG_BDNCAP process-based bounds
        self.tc.enqueue(self.handle_updatetable_off_ranges, self.env.eotime)

        if self.tc.test_run:
            self.tc.save_test_state(
                env=self.env, checkpoint="init_ext_vda_prior_equcrtp_vda"
            )

        self.include(
            equcrtp_vda.EqucrtpVda(
                self.tc,
                self.env,
                arg1="INIT_EXT",
            )
        )

        uc_actbet_defined = self.tc.defined("UC_ACTBET")
        self.tc.enqueue(
            self.prepare_uc_cli_uc_dynbnd_uc_actbet_cont,
            cli=self.env.cli,
            uc_actbet_defined=uc_actbet_defined,
            pgprim=self.env.pgprim,
        )

        if self.env.stages == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="$CLEAR GG_KGF",
            )

        if self.tc.defined("PRC_REACT"):
            self.env.set_global("powerflo", "YES")

        if m["GR_PTDF"].number_records + m["GG_KGF"].number_records:
            self.env.set_global("powerflo", "YES")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Load bounds/prices for exogenous trade from previous run if requested
SET PREMILE(ALLYEAR);
$KILL PAR_IRE PAR_IPRIC
""",
        )

        if not self.env.is_set("gdx_irebnd"):
            self.label_ifprice()
        else:
            if not os.path.exists(f"{self.env.gdxpath}{self.env.gdx_irebnd}.gdx"):
                self.label_ifprice()
            else:
                self.tc.add_gams_code(
                    module=self,
                    phase="init",
                    code=f"""
$GDXIN {self.env.gdxpath}{self.env.gdx_irebnd}
$LOAD RPC_IREIN=RPC_IREIO PREMILE=MILESTONYR PAR_IRE
""",
                )

                if self.env.gdx_irebnd.upper() == self.env.gdx_ipric:
                    self.label_load2()

                else:
                    self.tc.add_gams_code(
                        module=self,
                        phase="init",
                        code="$GDXIN",
                    )
                    self.label_ifprice()
        self.tc.enqueue(
            self.remove_originally_exogenous_trade_flows,
        )

        if self.tc.test_run:
            self.tc.save_test_state(env=self.env, checkpoint="init_ext_vda_end")

    def label_ifprice(self: InitExtVda) -> None:
        if not self.env.is_set("gdx_ipric"):
            return
        if not Path(f"{self.env.gdxpath}{self.env.gdx_ipric}.gdx").exists():
            return
        self.label_load2()

    def label_load2(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
$LOAD RPC_IREIN=RPC_IREIO PREMILE=MILESTONYR PAR_IPRIC
$GDXIN
""",
        )

    def prepare_uc_cli_uc_dynbnd_uc_actbet_cont(
        self: InitExtVda,
        cli: str,
        uc_actbet_defined: bool,
        pgprim: str,
    ) -> None:
        if cli == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="""
  LOOP((UC_N,SIDE,R,LL,CM_VAR)$UC_CLI(UC_N,SIDE,R,LL,CM_VAR),UC_ATTR(R,UC_N,'RHS','CLI','YES')=YES);
""",
            )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  LOOP(UC_ATTR(R,UC_N,SIDE,UC_GRPTYPE,UC_NAME(TSL)),UC_TSL(R,UC_N,SIDE,TSL)=YES);
""",
        )
        if uc_actbet_defined:
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=f"""
  UC_FLOBET(UC_N,ALL_R,YEAR,P,{pgprim}) $= UC_ACTBET(UC_N,ALL_R,YEAR,P); LOOP((UC_N,R,YEAR,P)$UC_ACTBET(UC_N,R,YEAR,P),UC_GMAP_P(R,UC_N,'ACT',P)=YES);
""",
            )

    def basic_years_stuff(
        self: InitExtVda,
        dflbl: str,
        waver: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Basic Years stuff:
  IF(CARD(DATAYEAR)=0, DATAYEAR(T)=YES;
    DATAYEAR(LL)$(MOD(MAX(1999,MIN(2051,YEARVAL(LL))),5)=0)=YES);
  DATAYEAR(PASTYEAR) = YES;
  DATAYEAR('{dflbl}') = NO;
  LOOP(T$(ORD(T)=1),IF(ABS(B(T)-YEARVAL(T)+5)>5,B(T)=YEARVAL(T));
    MIYR_1(T)=YES; MIYR_BOH=B(T)-1);
  PYR_S(LL) = YEARVAL(LL)=MIYR_BOH;
  """,
        )

        if waver.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="INT_DEFAULT('PASTI')=1;",
            )

    def peaking_and_storage_stuff(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Peaking and Storage stuff
  PRC_PKNO(R,P)$((NCAP_PKCNT(R,'0',P,'ANNUAL')>=10)$NCAP_PKCNT(R,'0',P,'ANNUAL')) = YES;
  PRC_PKAF(R,P)$((NCAP_PKCNT(R,'0',P,'ANNUAL')<= 0)$NCAP_PKCNT(R,'0',P,'ANNUAL')) = YES;
  PRC_STGIPS(R,P,C)$(NOT SUM(PRC_ACTUNT(R,P,CG,UNITS_ACT)$(COM_GMAP(R,CG,C)+SAMEAS(CG,C)),1)) = NO;
* Set penalty cost for partial loads and excess storage cycling
  OPTION TRACKP<STG_MAXCYC; RP_PL(TRACKP,'UP')=YES;
  LOOP(TSL(S(ANNUAL)),
   ACT_CSTUP(R,LL,P,TSL,CUR)=0;
   ACT_CSTUP(R,LL,P,TSL,CUR)$=ACT_CSTPL(R,LL,P,CUR);
   ACT_CSTUP(R,LL,P,TSL,CUR)$TRACKP(R,P) $= NCAP_COST(R,LL,P,CUR);
   ACT_UPS(R,LL,P,S,'FX') $= ACT_MINLD(R,LL,P));
  OPTION CLEAR=TRACKP, RP_UPR<ACT_TIME, RP_UPT<ACT_CSTSD;
""",
        )

    def clean_up_some_parameters(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Clean up some parameters
  LOOP(LASTLL(YEAR),
   OPTION CLEAR=UNCD7; UNCD7(R,LL--ORD(LL),C,COM,'','','') $= (VDA_EMCB(R,LL,C,COM) NE 0);
   VDA_EMCB(R,DATAYEAR,C,COM)$(NOT UNCD7(R,YEAR,C,COM,'','','')) = 0;
   OPTION CLEAR=UNCD7; LOOP(IE,UNCD7(R,LL--ORD(LL),P,C,S,ALL_R,CUR) $= (IRE_PRICE(R,LL,P,C,S,ALL_R,IE,CUR) NE 0));
   IRE_PRICE(R,DATAYEAR,P,C,S,ALL_R,IE,CUR)$(NOT UNCD7(R,YEAR,P,C,S,ALL_R,CUR)) = 0;
   OPTION CLEAR=UNCD7; UNCD7(R,LL--ORD(LL),P,CUR,'','','') $= (ACT_COST(R,LL,P,CUR) NE 0);
   ACT_COST(R,DATAYEAR,P,CUR)$(NOT UNCD7(R,YEAR,P,CUR,'','','')) = 0;
   OPTION CLEAR=UNCD7; UNCD7(R,LL--ORD(LL),P,C,S,CUR,'') $= (FLO_DELIV(R,LL,P,C,S,CUR) NE 0);
   FLO_DELIV(R,DATAYEAR,P,C,S,CUR)$(NOT UNCD7(R,YEAR,P,C,S,CUR,'')) = 0;
   OPTION CLEAR=UNCD7; UNCD7(R,LL--ORD(LL),P,C,S,CUR,'') $= (FLO_COST(R,LL,P,C,S,CUR) NE 0);
   FLO_COST(R,DATAYEAR,P,C,S,CUR)$(NOT UNCD7(R,YEAR,P,C,S,CUR,'')) = 0;
  );
  NCAP_CEH(R,LL,P) $= VDA_CEH(R,LL,P);
""",
        )

    def identify_and_initial_preprocessing(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
*-----------------------------------------------------------------------------
* Identify PRC_RESID processes and initialize NCAP_PASTI
  PRC_RESID(R,LL--ORD(LL),P)$((PRC_RESID(R,LL,P)>0)$PRC_RESID(R,LL,P)) = PRC_RESID(R,'0',P)+EPS;
  NCAP_PASTI(R,PYR_S,P)$PRC_RESID(R,'0',P) = 1;
*-----------------------------------------------------------------------------
* Initial Preprocessing of VDA_EMCB, FLO_EMIS and IRE_FLOSUM
  FLO_EMIS(R,LL,P,CG,C,S) $= FLO_EFF(R,LL,P,CG,C,S);
  OPTION CLEAR=RXX,CLEAR=FLO_EFF;
  VDA_EMCB(R,YEAR,C,COM)$COM_TMAP(R,'ENV',C) = 0;
  LOOP((R,DATAYEAR,C,COM)$VDA_EMCB(R,DATAYEAR,C,COM),RXX(R,C,COM) = YES);
  RXX(R,C,COM)$(NOT COM_TMAP(R,'ENV',COM)) = NO;
  LOOP((TOP(R,P,C,'IN'),RXX(R,C,COM)),FS_EMCB(R,P,COM,C)=YES);
  FS_EMCB(R,P,COM,C)$TOP(R,P,COM,'IN') = NO;
  OPTION TRACKPC <= FS_EMCB; TOP(TRACKPC,'OUT') = YES;
  OPTION CLEAR=RXX, CLEAR=TRACKPC;
  LOOP((R,DATAYEAR,P,CG,C,S)$FLO_EMIS(R,DATAYEAR,P,CG,C,S),RPC_EMIS(R,P,C) = YES);
  RPG_RED(RPC_EMIS(R,P,C),'OUT')$(NOT TOP(R,P,C,'IN')) = YES;
  LOOP((R,DATAYEAR,P,C,S,IE,COM,IO)$(PRC_MAP(R,'IRE',P)$IRE_FLOSUM(R,DATAYEAR,P,C,S,IE,COM,IO)),RPG_RED(R,P,COM,IO) = YES);
""",
        )

    def initial_preprocessing_of_com_agg(
        self: InitExtVda,
        shell: str,
        dflbl: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Initial Preprocessing of COM_AGG and VDA_FLOP
  COM_AGG(R,LL,C,C)$COM_AGG(R,LL,C,C) = 0;
  VDA_FLOP(R,LL,P,CG,S) $= ACT_FLO(R,LL,P,CG,S);
  KEEP_FLOF(R,P,C)$VDA_FLOP(R,'{dflbl}',P,C,'ANNUAL') = YES;
""",
        )

        if shell.upper() == "ANSWER":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=rf"KEEP_FLOF(R,P,C)$PRC_ACTFLO(R,'{dflbl}',P,C) = YES;",
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"OPTION RP_XRED<ACT_FLO, CLEAR=ACT_FLO;",
        )

    def handle_updatetable_off_ranges(
        self: InitExtVda,
        eotime: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Handle Updatable OFF-ranges & REG_BDNCAP process-based bounds
  NCAP_START(R,P)$(NCAP_START(R,P)<=MIYR_BOH)=0;
  RVP(R,LL,P) $= NCAP_BND(R,LL,P,'N');
  IF(CARD(RVP),
    NCAP_BND(RVP,'N')$(NCAP_BND(RVP,'N')>{eotime}) = {eotime};
    NCAP_START(R,P)$((ABS(NCAP_BND(R,'0',P,'N'))>999)$RVP(R,'0',P)) = ABS(NCAP_BND(R,'0',P,'N'))+1;
    PRC_NOFF(R,P,LL,EOHYEAR)$RVP(R,LL,P) = NO;
    PRC_NOFF(R,P,BOHYEAR(LL),LL+(NCAP_BND(R,LL,P,'N')-YEARVAL(LL)))$RVP(R,LL,P) = YES);
  NCAP_BND(RVP(R,LL,P),L('N')) = MOD(MIN(2,ROUND(MAX(NCAP_BND(RVP,L),-1))),2)$LASTLL(LL)+(YEARVAL(LL)-1)$(ROUND(MOD(NCAP_BND(RVP,L)-YEARVAL(LL),MAX(1,YEARVAL(LL))))=-1);
  OPTION CLEAR=RVP;
""",
        )

    def remove_originally_exogenous_trade_flows(self: InitExtVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
PAR_IRE(R,LL,T,P,C,S,IE)$RPC_IREIN(R,P,C,IE,'OUT') = 0;
PAR_IPRIC(R,T,P,C,TS,IE)$RPC_IREIN(R,P,C,IE,'OUT') = 0;
RPC_IREIN(R,P,C,IE,'OUT') = NO;
""",
        )
