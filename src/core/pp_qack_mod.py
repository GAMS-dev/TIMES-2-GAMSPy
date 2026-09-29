# pp_qack_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_QACK.MOD perform the individual quality control checks
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# * - Provide control mechansim to turn-off (ALL, NOFATAL, NONE) tests
# *------------------------------------------------------------------------------
# * Pending Tests:
# *   - check that each process consumes/produces a commodity
# *   - check that each commodity is both produced/consumed
# *   - TOP not violated by reference to COM not in TOP/T/X
# *   - every process has PRC_ACTUNT/CAPUNT specified?
# *   - not both COM_NETBND and COM_PRDBND (or does not matter?) + COM_PROJ
# *   - check that any commodity/ts-index attribute OK according to COM_TS
# *   - c=OCOM+NCAP_VALU+input to another process, otherwise warning
# *   - check that FLO_FUNC/SHAR/SUM cg has all elements on the same side
# *   - if PRC_ANN and non-ANNUAL attribute provided give warning
# *   - check that all attributes s-index match up with RPS and the individual commodities
# *   - warning that "NRG" used if no group matching the PG and PRC_SPG not provided
# *   - No PRC_CAPUNIT/ACTUNIT assigned and > 1 input; fatal?
# *   - Check that anticipated mapping list members that may affect matrix generation are provided (e.g., FRE/LIMRENEW)
# *   - check the TS associated with any attribute (as well as COM/PRC_TS) is OK
# *   - check that if list of peak timeslices provided by the user then actual peak is in said list
# *   - check that all FLO_* c/cg somehow relate to the PG/SPG (ouch)
# *   - if TOP_IRE to/from an external check for IRE_BND/PRICE/XBND
# *   - check that PRC_TSL=COM_TSL=COM_FR for DEM commodities
# *   - check that TS-attributes are found in TS_GROUP/MAP for the region (during Aggr/Inher)
# *     - or see what is around for TS_GROUP (TS_MAP if > 2 levels) and G_YRFR at the min!!!
# *   - check that no 0/EPS for attributes that could turn-off a flow, or cause a 0 divide
# *-----------------------------------------------------------------------------

# pp_qack_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_QACK.MOD perform the individual quality control checks
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Set, Sum, UniverseAlias

from core.base_class import GamsClass
from core.pp_qaput_mod import pp_qaput

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def rpc_in_top_violations(g: TimesModelClass) -> Set:
    """RPC in TOP not found in any ACTFLO/FLO_SHAR/FLO_FUNC/FLO_SUM."""

    r, p, c, io = g.r, g.p, g.c, g.io
    Top, Rpc, Trackp, Trackpc = g.Top, g.Rpc, g.Trackp, g.Trackpc

    violations = Set(g.container, name="violations_r_p_c_io", domain=[r, p, c, io])

    with Loop(Top[Rpc[Trackp[r, p], c], io].where[~(Trackpc[r, p, c])]):
        violations[r, p, c, io] = True

    return violations


def empty_group_violations(g: TimesModelClass) -> Set:
    """Empty Group in FLO_SUM/FLO_FUNC/FLO_SHAR."""

    r, p, c, cg = g.r, g.p, g.c, g.cg
    RpGrp, Rp, Rpc, ComGmap = g.RpGrp, g.Rp, g.Rpc, g.ComGmap

    violations = Set(
        g.container, name="violations_r_p_cg_empty_group", domain=[r, p, cg]
    )
    with Loop(
        RpGrp[Rp[r, p], cg].where[~Sum(Rpc[r, p, c].where[ComGmap[r, cg, c]], 1.0)]
    ):
        violations[r, p, cg] = True
    return violations


class PpQackMod(GamsClass):
    """Translation unit for pp_qack.mod."""

    module_name: str = "pp_qack_mod"
    gams_source: str = "pp_qack.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules: dict[str, GamsClass] = {}
        self.compile()

    def compile(self) -> None:
        m = self.tc.container
        self.tc.u2 = UniverseAlias(m, name="U2")
        self.tc.u3 = UniverseAlias(m, name="U3")
        self.tc.u4 = UniverseAlias(m, name="U4")

        self.tc.enqueue(
            self.exec1,
            var_uc_yes=(self.env.var_uc.upper() == "YES"),
            rl=self.env.rl,
            pl=self.env.pl,
            cl=self.env.cl,
            pgprim=self.env.pgprim,
        )

        if self.env.timesed != "YES":
            self.env.set_local("timesed", "NO")

        self.tc.enqueue(
            self.exec2,
            timesed_yes=self.env.timesed == "YES",
            rl=self.env.rl,
            pl=self.env.pl,
            cl=self.env.cl,
            sol_bprice_defined=self.tc.defined("SOL_BPRICE"),
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="SET QASTAT(J) / 1 'Unreliable (see QA_Check.log)' /;",
        )

        self.tc.enqueue(self.exec2_1, rl=self.env.rl, pl=self.env.pl, cl=self.env.cl)

        if self.env.debug.upper() == "YES":
            self.env.set_scoped("xtqa", "YES")
        if f"{self.env.vda}{self.env.xtqa}".upper() == "YESYES":
            self.tc.enqueue(
                self.exec3,
                rl=self.env.rl,
                pl=self.env.pl,
                cl=self.env.cl,
                pgprim=self.env.pgprim,
                pgprim_is_set=self.env.is_set("pgprim"),
                rpg_ace_defined=self.tc.defined("RPG_ACE"),
            )

        self.tc.enqueue(self.exec4)

    def exec1(
        self: PpQackMod, var_uc_yes: bool, rl: str, pl: str, cl: str, pgprim: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  IF(YES, PUT QLOG; QLOG.AP$PUTOUT = 1;
*...make 2 decimals points and allow for wider page
    QLOG.NW=10; QLOG.ND=2; QLOG.PW=150);
  PUTGRP = 0;
*-----------------------------------------------------------------------------
* Some important control sets are completed here
* Complete merely CAP dependent flow indicators
  RPC_CONLY(RTPC(R,T,P,C))$RPC_NOFLO(R,P,C) = YES;
* Complete flow variable indicators
  RTPCS_VARF(RPC_CONLY,S) = NO;
* Remove superfluous entries from RCS_COMBAL
  RCS_COMBAL(RHS_COMBAL,BDNEQ) = NO;
* Establish the RPG_RED control set
  TRACKPC(R,P,C)$(RPC_ACT(R,P,C)+RPC_FFUNC(R,P,C)+RPC_EMIS(R,P,C)) = YES;
  RPG_RED(R,P,CG,IO)$(NOT SUM(TOP(TRACKPC(R,P,C),IO)$COM_GMAP(R,CG,C),1)) = NO;
{"OPTION UC_GMAP_U<=UC_UCN;" if var_uc_yes else ""}
  RTP(NO_RVP) = NO;
* Vintage controls for generation performance
  OPTION RTP_VNTBYR < RTP_VINTYR, COEF_VNT < COEF_CPT, TRACKP < RP_UPL;
  TRACKP(R,P)$=SUM(RP_PL(R,P,L),1); TRACKP(RP_XRED)=YES; TRACKP(CHP)=YES;
  RVP_KMAP(RTP(R,V,P),V)$(PRC_VINT(R,P)$TRACKP(R,P)) = YES; TRACKP(PRC_VINT)=NO;
  RVP_KMAP(RTP(R,T,P),V)$(COEF_VNT(RTP,V)$TRACKP(R,P)) = YES;
  OPTION CLEAR=TRACKPC,CLEAR=TRACKP,CLEAR=RP_XRED;

*-----------------------------------------------------------------------------
* Year fractions
*-----------------------------------------------------------------------------
  LOOP(R, TS_ARRAY(S) = 0;
    LOOP(TS_MAP(R,TS,S)$(G_YRFR(R,S) EQ 0), TS_ARRAY(S) = 1);
    LOOP(S$TS_ARRAY(S),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Year Fraction G_YRFR is ZERO!")}
         PUT QLOG ' FATAL ERROR   -     R=',{rl},' S=',S.TL;
  ));
  PUTGRP = 0;
*-----------------------------------------------------------------------------
* Topology
*-----------------------------------------------------------------------------
* Check PGPRIM
  LOOP(RPC(R,P,C('{pgprim}')),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Illegal system commodity in topology.")}
     PUT QLOG ' FATAL ERROR   -     R=',{rl},' P=',{pl},' C=',C.TL;
  );
  PUTGRP = 0;
* see that components of any CG for a process in topology
  LOOP(PRC_CG(R,P,CG)$(NOT COM_TYPE(CG)),
    IF(NOT SUM(COM_GMAP(R,CG,C)$RPC(R,P,C),1), Z = 1;
      LOOP(COM_GMAP(R,CG,C)$(NOT RPC(R,P,C)), Z = 0;
{pp_qaput("PUTOUT", "PUTGRP", "10", "Commodity in CG of process P but not in topology")}
         PUT QLOG ' SEVERE WARNING  -   R=',{rl},' P=',{pl},' C=',{cl},' CG=',CG.TL );
      IF(Z,
{pp_qaput("PUTOUT", "PUTGRP", "10", "No commodities in CG of process P")}
         PUT QLOG ' SEVERE WARNING  -   R=',{rl},' P=',{pl},' CG=',CG.TL );
      )
    );
  PUTGRP = 0;
""",
        )

    def exec2(
        self: PpQackMod,
        timesed_yes: bool,
        rl: str,
        cl: str,
        pl: str,
        sol_bprice_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Commodity description
*-----------------------------------------------------------------------------
  {"IF(YES, FORWARD(T)=YES;" if timesed_yes else "IF(NO, FORWARD(T)=YES;"}
{"OPTION FORWARD < SOL_BPRICE;" if sol_bprice_defined else ""}
    LOOP(T$(NOT FORWARD(T)),
{pp_qaput("PUTOUT", "PUTGRP", "09", "Elastic Demand but missing BPRICE for some MILESTONYR - using tail extrapolation")}
         PUT QLOG ' WARNING       -  Missing BPRICE, MILESTONYR=',T.TL);
    PUTGRP = 0;
    LOOP(DEM(R,C)$SUM(BD$COM_STEP(R,C,BD),1),
      IF((NOT SUM((T,S,CUR)$COM_BPRICE(R,T,C,S,CUR),1)) +
         (NOT SUM((T,BD)$COM_VOC(R,T,C,BD),1)) +
         (NOT SUM((T,S,BD)$COM_ELAST(R,T,C,S,BD),1)),
{pp_qaput("PUTOUT", "PUTGRP", "10", "Elastic Demand but either COM_BPRICE/ELAST/VOC missing")}
         PUT QLOG ' WARNING       -     R=',{rl},' C=',{cl} ;
      )
    );
  );
  PUTGRP = 0;
  LOOP(RC(R,C(COM_TYPE)),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Commodity type is also a commodity")}
           PUT QLOG ' FATAL ERROR   -     R=',{rl},' C=',C.TL ;
  );
  PUTGRP = 0;
  LOOP(RC(R,C)$(SUM(COM_TMAP(R,COM_TYPE,C),1) NE 1),
{pp_qaput("PUTOUT", "PUTGRP", "09", "Commodity has ambiguous base type")}
    IF(SUM(COM_TMAP(R,COM_TYPE,C),1) GT 1,
           PUT QLOG ' FATAL ERROR   -  Several types: R=',{rl},' C=',C.TL ;
    ELSE   PUT QLOG ' FATAL ERROR   -  Missing type : R=',{rl},' C=',C.TL ;);
  );
  PUTGRP = 0;
*-----------------------------------------------------------------------------
* Demand description
*-----------------------------------------------------------------------------
  OPTION TRACKC < RD_SHAR;
  LOOP((R,T,C)$COM_PROJ(R,T,C),TRACKC(R,C) = YES);
  LOOP(COM_GMAP(DEM(R,C),C)$(NOT TRACKC(R,C)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Demand: DEM commodity with missing COM_PROJ Projection")}
           PUT QLOG ' WARNING       -     R=',{rl},' C=',C.TL ;
  );
  PUTGRP = 0;
  LOOP(TRACKC(R,C)$(NOT DEM(R,C)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Demand: COM_PROJ specified for non-DEM commodity")}
           PUT QLOG ' WARNING       -     R=',{rl},' C=',C.TL ;
  );
  OPTION CLEAR=TRACKC;
  PUTGRP = 0;
""",
        )

    def exec2_1(
        self: PpQackMod,
        rl: str,
        cl: str,
        pl: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Process description
*-----------------------------------------------------------------------------

  OPTION TRACKPC<RPC; TRACKPC(RP(R,PRC(P)),C)$RC(R,C)=NO;
  LOOP(TRACKPC(RPC),
{pp_qaput("PUTOUT", "PUTGRP", "33", "Phantom entries found in topology (process/commodity not in SET PRC/COM)")}
    PUT QLOG ' FATAL ERROR   -     Phantom topology entry:   R.P.C= ',TRACKPC.TE(RPC));
  OPTION CLEAR=TRACKPC,CLEAR=PRC_CG;
  IF(ERRLEV=33,SOLVESTAT(J)$=QASTAT(J));
  PUTGRP = 0;
  PRC_YMAX(RP)=SUM(RP_PG(RP,CG),1)-1;
  LOOP(RP(R,P)$PRC_YMAX(R,P),
{pp_qaput("PUTOUT", "PUTGRP", "10", "Process with missing or mismatched CG/PRC_ACTUNIT")}
      IF(PRC_YMAX(RP)<0,
         PUT QLOG ' FATAL ERROR   -  No way to identify PCG:   R=',{rl},' P=',P.TL ;
      ELSE
         PUT QLOG ' FATAL ERROR   -  Several PCG groups:       R=',{rl},' P=',P.TL ;
      );
  );
  PRC_CG(RP_PG(R,P,CG))$=SUM(RPC_AFLO(R,P,C)$(NOT RPC_FFUNC(R,P,C)),1);
  PUTGRP = 0;
  LOOP(FS_EMIT(R,P,COM,CG,C)$RPC_EMIS(R,P,C),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Illegal dependency of substituted auxiliary commodities C1 and C2 in FLO_SUM")}
    PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' C1=',{cl},' C2=',COM.TL;
  );
  PUTGRP = 0;
  OPTION  PRC_YMAX < PRC_REFIT; PRC_YMAX(RP)$(PRC_YMAX(RP)=1)=0;
  LOOP(RP(R,P)$PRC_YMAX(RP),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Multiple host processes for REFIT option - Not supported")}
    PUT QLOG ' WARNING       -     REG=',R.TL,' PRC='P.TL);
  PUTGRP = 0;
  IF(CARD(RP_UPL),OPTION TRACKP<NCAP_AFX; TRACKP(PRC_VINT)=NO;
  LOOP(RP_UPL(TRACKP(R,P),'FX'),
{pp_qaput("PUTOUT", "PUTGRP", "00", "NCAP_AFX defined for NON-vintaged dispatchable process with ACT_MINLD")}
    PUT QLOG ' NOTICE        -     AFX ignored on PRC_TSL:  R=',{rl},' P=',{pl};
  );
  OPTION CLEAR=TRACKP,CLEAR=PRC_YMAX; PUTGRP = 0);
*-----------------------------------------------------------------------------
* Possible reasons for execerror in retrospect
  IF(EXECERROR,
    OPTION CLEAR=RXX; LOOP(RDCUR(R,CUR),RXX(R,CUR,R)=YES); RXX(R,CUR,R)=NO;
    LOOP(RXX(R,ITEM,R),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Active currency but not member of set CUR")}
    PUT QLOG ' FATAL ERROR   -     R=',{rl},' CUR=',ITEM.TL); PUTGRP=0;
    LOOP(R$PROD(G_RCUR(R,CUR),0),IF(SUM(RP(R,P),1),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Internal Region without Discount Rate")}
    PUT QLOG ' FATAL ERROR   -     R=',{rl})); PUTGRP=0;
    OPTION CLEAR=RXX; LOOP(OBJ_ICUR(R,V,P,CUR)$(NOT RDCUR(R,CUR)),RXX(R,R,CUR)=YES);
    LOOP(RXX(R,R,CUR),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Active Currency without Discount Rate")}
    PUT QLOG ' FATAL ERROR   -     R=',{rl},' CUR =',CUR.TL);
    LOOP(RTPC(R,T,P,C)$((PRC_ACTFLO(R,T,P,C) EQ 0)$RPC_PG(R,P,C)),TRACKPC(R,P,C)=YES);
    LOOP(TRACKPC(R,P,C),
{pp_qaput("PUTOUT", "PUTGRP", "99", "Process with zero PRC_ACTFLO for C in PG")}
    PUT QLOG ' FATAL ERROR   -     R=',{rl},' P=',{pl},' C=',{cl});
    OPTION CLEAR=TRACKPC; PUTGRP = 0);
""",
        )

    def exec3(
        self: PpQackMod,
        rl: str,
        pl: str,
        cl: str,
        pgprim: str,
        pgprim_is_set: bool,
        rpg_ace_defined: bool,
    ) -> None:
        g = self.tc
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Extended QA chacks - Activated when either DEBUG=YES or XTQA is set
*-----------------------------------------------------------------------------
* Not same commodity TOP IN/OUT
   LOOP(RPC(R,P,C)$(TOP(R,P,C,'IN')*TOP(R,P,C,'OUT')),
     IF(NOT PRC_MAP(R,'STG',P),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Same Commodity IN and OUT of non-STG process")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' C=',C.TL;
     ));
   PUTGRP = 0;
*-----------------------------------------------------------------------------
* IRE process parameter check
  OPTION CLEAR=UNCD7;
  UNCD7(R,LL+(1-ORD(LL)),P,CG1,CG2,S--ORD(S),'0') $= FLO_FUNC(R,LL,P,CG1,CG2,S)$RP_IRE(R,P);
  UNCD7(R,LL+(2-ORD(LL)),P,CG1,C,CG2,S--ORD(S))   $= FLO_SUM(R,LL,P,CG1,C,CG2,S)$RP_IRE(R,P);
  UNCD7(R,LL+(3-ORD(LL)),P,C,CG,S--ORD(S),BD)     $= FLO_SHAR(R,LL,P,C,CG,S,BD)$RP_IRE(R,P);
  UNCD7(R,LL+(4-ORD(LL)),P,CG,S--ORD(S),'0','0')  $= ACT_EFF(R,LL,P,CG,S)$RP_IRE(R,P);
  LOOP(UNCD7(R,LL,P,CG,U2,U3,U4), Z = ORD(LL);
{pp_qaput("PUTOUT", "PUTGRP", "01", "IRE Process with invalid Parameters")}
       IF(Z = 1, PUT QLOG ' WARNING       - IRE with FLO_FUNC: R=',{rl},' P=',{pl},' CG=',CG.TL);
       IF(Z = 2, PUT QLOG ' WARNING       - IRE with FLO_SUM:  R=',{rl},' P=',{pl},' CG=',CG.TL);
       IF(Z = 3, PUT QLOG ' WARNING       - IRE with FLO_SHAR: R=',{rl},' P=',{pl},' C=',CG.TL);
       IF(Z = 4, PUT QLOG ' WARNING       - IRE with ACT_EFF:  R=',{rl},' P=',{pl},' CG=',CG.TL);
  );
  OPTION CLEAR=RXX;
  LOOP(UC_QAFLO('1',UCN,SIDE,R,P,C)$(NOT UC_CAPFLO(UCN,SIDE,R,P,C)),RXX(R,P,UCN)=YES);
  LOOP(RXX(R,P,UC_N),
{pp_qaput("PUTOUT", "PUTGRP", "01", "IRE Process with invalid Parameters")}
       PUT QLOG ' WARNING       - IRE with UC_FLO:   R=',{rl},' P=',{pl},' UC_N=',UC_N.TL;
  );
  OPTION CLEAR=RXX; PUTGRP=0;
  LOOP(PRC_MAP(R,'IRE',P)$(RP(R,P)$(NOT RP_IRE(R,P))),
{pp_qaput("PUTOUT", "PUTGRP", "09", "Standard Flow Process with invalid Attributes")}
       PUT QLOG ' SEVERE ERROR  - Process Group is IRE:  R=',{rl},' P=',{pl};
  );
  LOOP(UC_QAFLO('2',UC_N,SIDE,RPC(R,P,C)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Standard Flow Process with invalid Parameters")}
       PUT QLOG ' WARNING       - FLO flow with UC_IRE:  R=',{rl},' P=',{pl},' C=',{cl},' UC_N=',UC_N.TL;
  );
*-----------------------------------------------------------------------------
  PUTGRP = 0;
* ACT_EFF quality tests
  IF(CARD(ACT_EFF),
  OPTION RP_GRP < ACT_EFF;
  RP_GRP(RPC_ACE)=NO; RP_GRP(RPC_PG)=NO;
  RP_GRP(R,P,CG)$SUM(RPG_ACE(R,P,CG,IO),1)=NO;
  RP_GRP(R,P,CG)$SUM(RPG_1ACE(R,P,CG,C),1)=NO;
  RP_GRP(R,P,C)$SUM(RPG_1ACE(R,P,CG,C),1)=NO;
  LOOP(RP_GRP(R,P,CG),
   IF(NOT SUM((TOP(R,P,C(CG),IO),COM_GMAP(R,CG2,C))$RPG_ACE(R,P,CG2,IO),1),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Invalid Commodity / Group used in ACT_EFF - parameter ignored")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' CG=',CG.TL;
   )));
  PUTGRP = 0;
* FLO_SUM quality tests
  OPTION CLEAR=FSCK, CLEAR=UNCD7;
  OPTION FSCK <= FLO_SUM;
  FSCK(RPC_EMIS(R,P,CG),C,CG)$RPC(R,P,C) = NO;
  LOOP(FSCK(R,P,CG,C,CG2)$(NOT RPC(R,P,C)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "FLO_SUM Commodity Not in RPC - parameter ignored")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' CG=',CG.TL,' C=',C.TL;
   );
  PUTGRP = 0;
* FLO_SUM commodity-in-group test
  FSCK(RPC(R,P,COM),C,COM)$RPCC_FFUNC(R,P,COM,COM) = NO;
  LOOP(FSCK(R,P,CG,C,CG2)$(NOT COM_GMAP(R,CG,C)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "FLO_SUM Commodity Not in CG1 - parameter ignored")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' CG1=',CG.TL,' C=',C.TL;
   );
  PUTGRP = 0;
* Two-way PTRANS equations chack
   OPTION CLEAR=CG_GRP; FSCK(RP,C,COM,C)=NO;
   LOOP(FSCK(R,P,CG1,C,CG2),CG_GRP(R,P,CG1,CG2) = YES);
   LOOP((R,V,P,CG1,CG2,S)$(FLO_FUNC(R,V,P,CG2,CG1,S)$FLO_FUNC(R,V,P,CG1,CG2,S)),CG_GRP(R,P,CG1,CG2) = YES);
   LOOP(CG_GRP(R,P,CG1,CG2)$CG_GRP(R,P,CG2,CG1),
{pp_qaput("PUTOUT", "PUTGRP", "10", "PTRANS between CG1 and CG2 in both directions")}
         PUT QLOG ' FATAL ERROR   -     R=',{rl},' P=',{pl},' CG1=',CG1.TL,' CG2=',CG2.TL;
   );
  OPTION CLEAR=FSCK;
  PUTGRP = 0;
* All TOPc are in some ACTFLO/FLO_SHAR/FLO_FUNC
  OPTION CLEAR=CG_GRP;
  OPTION RP_CCG < COEF_PTRAN;
  CG_GRP(RP_CCG) = YES;
  OPTION RP_CCG < FLO_SHAR;
  CG_GRP(RP_CCG) = YES;
  OPTION RP_GRP < CG_GRP;
  CG_GRP(R,P,C,COM)$((NOT ENV(R,C))$ENV(R,COM)) = NO;
  TRACKPC(R,P,C) $= SUM(CG_GRP(R,P,C,CG2),1);
  RP_GRP(TRACKPC(R,P,C))$(NOT RPC(R,P,C)) = YES;
  TRACKPC(RP_GRP(RPC(R,P,C))) = YES; RP_GRP(RPC) = NO;
  LOOP(RP_GRP(R,P,CG),TRACKPC(RPC(R,P,C))$COM_GMAP(R,CG,C) = YES);
{"  LOOP(RPG_ACE(R,P,CG,IO),TRACKPC(RPC_ACE(R,P,C)) = YES);" if rpg_ace_defined else ""}
  TRACKPC(RPC_PG) = YES;
  TRACKPC(RPC(R,P,C))$RP_IRE(R,P) = YES;
  TRACKPC(RPC_SPG(RPC_STG)) = YES;
  TRACKPC(RPC_NOFLO) = YES;
  TRACKPC(RPC_FFUNC) = YES;
  TRACKPC(RMKC(R,P,C))$=SUM(OBJ_VFLO(R,P,C,CUR,UC_COST),1);
  LOOP(T, TRACKP(RP_STD(R,P))$RTP_VARA(R,T,P) = YES);
  """,
        )

        violations = rpc_in_top_violations(g=g)
        g.pp_qaput_logger.log_violations(
            violations_df=violations.records,
            err_level=1,
            group_desc="RPC in TOP not found in any ACTFLO/FLO_SHAR/FLO_FUNC/FLO_SUM",
            message_template="WARNING       -     R={R} P={P} C={C} IO={IO}",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=CG_GRP,CLEAR=RP_CCG; PUTGRP = 0;",
        )

        # Empty groups check
        g.RpGrp[g.RpPg[g.r, g.p, g.cg]].where[(~(Sum(g.RpcPg[g.r, g.p, g.c], 1.0)))] = (
            True
        )
        if pgprim_is_set:
            g.RpGrp[g.r, g.p, pgprim] = False

        empty_group_violations_set = empty_group_violations(g=g)
        g.pp_qaput_logger.log_violations(
            violations_df=empty_group_violations_set.records,
            err_level=1,
            group_desc="Empty Group in FLO_SUM/FLO_FUNC/FLO_SHAR",
            message_template="WARNING       -     R={R} P={P} CG={CG}",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  PUTGRP = 0;
* Simultaneous NCAP_AF/NCAP_AFA availability check
  RVP(RTP(R,V,P))$(SUM(BD$NCAP_AFA(RTP,BD),1)$PRC_TSL(R,P,'ANNUAL')) = YES;
  LOOP((RVP(R,V,P),BD)$((NCAP_AF(R,V,P,'ANNUAL',BD) NE 1)$NCAP_AF(R,V,P,'ANNUAL',BD)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Both NCAP_AF and NCAP_AFA specified for same process")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' V=',V.TL;
  );
  OPTION CLEAR=RVP,CLEAR=RP_GRP;
  PUTGRP = 0;
* Commodity fraction check
  LOOP(RTC(R,T,C)$(ABS(SUM(COM_TS(R,C,S),COM_FR(R,T,C,S))-1) GT 3E-3),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Commodity fractions do not sum up to 1")}
         PUT QLOG ' WARNING       -     R=',{rl},' C=',{cl},' T=',T.TL;
  );
  PUTGRP = 0;
* NCAP_CLED duration check
   LOOP((R,V,P,C)$NCAP_CLED(R,V,P,C),
     IF(NCAP_CLED(R,V,P,C) > COEF_ILED(R,V,P),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Too Long Commodity Lead Time")}
         PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl},' C=',C.TL;
     ));
  PUTGRP = 0;
* CHP parameter check
  OPTION CLEAR=UNCD7;
  UNCD7('1',R,V,P,'','','')$(NOT CHP(R,P)) $=NCAP_BPME(R,V,P);
  UNCD7('2',R,V,P,BDUPX,'','')$(NOT CHP(R,P)) $=NCAP_CHPR(R,V,P,BDUPX);
  UNCD7('3',R,V,P,'','','')$(NOT CHP(R,P)) $=NCAP_CEH(R,V,P);
  LOOP(UNCD7(J,R,V,P,U2,U3,U4), Z=ORD(J);
{pp_qaput("PUTOUT", "PUTGRP", "01", "CHP parameter specified for Non-CHP process")}
    PUT QLOG ' WARNING       -     NCAP_';
    IF(Z=1,PUT QLOG,'BPME';ELSEIF Z=2,PUT QLOG,'CHPR';ELSE PUT QLOG,'CEH ');
    PUT QLOG ': R=',{rl},' P=',{pl},' V=',V.TL;
  );
  PUTGRP = 0;
* CHP primary group check
  LOOP(CHP(RP_PGACT(R,P)),
   IF(SUM((T,BD)$NCAP_CHPR(R,T,P,BD),1),
{pp_qaput("PUTOUT", "PUTGRP", "01", "PG of CHP process consists of single commodity yet has a CHP-ratio")}
         PUT QLOG ' SEVERE ERROR  -     R=',{rl},' P=',{pl};);
  );
  PUTGRP = 0;
* CHP ratio check, if some ratios defined
  TRACKP(CHP(R,P))=SUM(RTP(R,T,P)$(NOT SUM(BD$NCAP_CHPR(R,T,P,BD),1)),1);
  LOOP(R, Z=SUM(TRACKP(R,P)$(NOT RP_PGACT(R,P)),1);
   IF(Z,
{pp_qaput("PUTOUT", "PUTGRP", "01", "Found CHP processes without CHP-ratio defined")}
       PUT QLOG ' WARNING       -     R=',{rl},' Number of PRCs without ratio: ',Z:0:0;);
  ); OPTION CLEAR=TRACKP;
  PUTGRP = 0;
* CHP efficiency check
  LOOP((CHP_ELC(R,P,C),RPG_PACE(R,P,CG)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Found CHP processes with PG commodity efficiencies - unsupported")}
       PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl};);
  PUTGRP = 0;
* CHP electricity check
  LOOP(CHP(R,P)$(NOT SUM(RPC_PG(R,P,C)$NRG_TMAP(R,'ELC',C),1)),
{pp_qaput("PUTOUT", "PUTGRP", "01", "Found CHP processes without electricity in the PG")}
       PUT QLOG ' WARNING       -     R=',{rl},' P=',{pl};);
""",
        )

    def exec4(self: PpQackMod) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Abort if truly MAJOR ERROR
  IF(ERRLEV >= 33,
    IF(ERRLEV=33, PUTGRP=0;
{pp_qaput("PUTOUT", "PUTGRP", "33", "Found severe modeling errors (see error code 33 above) ***")}
       PUT QLOG ' ERROR ALERT   -     Model Solution is Unreliable         ';
    ELSE ABORT '*** FATAL QA ERROR - Check the QA_CHECK.LOG file for details ***'
  ));

{pp_qaput("PUTOUT$PUTOUT", "PUTOUT", "*", "ALL QUALITY CHECKS PASSED ***")}
  OPTION CLEAR = PUTOUT, CLEAR = PUTGRP, CLEAR = ERRLEV;
  PUTCLOSE QLOG;
""",
        )
