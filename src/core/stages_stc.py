# stages_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * STAGES.stc - Preprocessing for multi-stage stochastics
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Ord, Set

from core.base_class import GamsClass
from core.fillsow_stc import FillsowStc
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class StagesStc(GamsClass):
    """Translation unit for stages.stc."""

    # Instance attributes
    module_name: str = "stages_stc"
    gams_source: str = "stages.stc"

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

        if self.env.macro == "YES":
            raise NotImplementedError("Stochastic MACRO Not Implemented - aborted.")
        if self.arg1 == "MCA":  # L10: GOTO POST
            pass
        else:
            self.env.set_global(
                "sw_tags",
                r"""SET EQ 'ES' SET VAR 'VAS' SET SWD ',WW' SET SWTD ',T,WW' SET SWS ',W)' SET SOW ',SOW' SET SWT ',SW_T(T,SOW)' SET VART 'SUM(SW_TSW(SOW,T,W),VAS' SET VARV 'SUM(SW_TSW(SOW,V,W),VAS' SET VARM 'SUM(SW_TSW(SOW,MODLYEAR,W),VAS'""",
            )
            if self.env.stages == "YES":
                self.env.set_global(
                    "sw_stvars",
                    r"""SET VARTT 'SUM(SW_TSW(SOW,TT,W),VAS' SET SWSW SW_TSW(SOW,T,WW),""",
                )
            self.env.set_global("swd", ",WW")
            self.env.set_global("swd_GP", (g.ww,))
            self.env.set_global("witspine", False)
            if self.env.stages == "YES":
                self.env.set_global("swx", ",SOW")
                self.env.set_global("swx_GP", (g.Sow,))
                self.env.set_global("swtx", "SW_T(T,SOW)$")
                self.env.set_global("swtx_GP", g.SwT[g.t, g.Sow])
            if self.env.sensis == "YES":
                self.env.set_global("swd", "")
                self.env.set_global("swd_GP", ())

            g.Auxsow = Set(m, name="AUXSOW", domain=[g.allsow], records=["1"])

            self.env.set_global("var_uc", "YES")
            if not self.env.var_uc == "YES":
                raise ValueError("Invalid VAR_UC setting in stochastic mode - abort")
            self.tc.enqueue(self.preprocess_inputs)
            self.tc.enqueue(self.check_parameters)
            self.tc.enqueue(self.construct_spanning_tree)
            if self.env.is_set_local("DEBUG"):
                self.tc.add_gams_code(
                    module=self,
                    phase="run",
                    code=r"""
DISPLAY SW_PROB,SW_SPROB;
""",
                )
            self.tc.enqueue(self.normalize_probability_distribution)
            if self.env.is_set_local("DEBUG"):
                self.tc.add_gams_code(
                    module=self,
                    phase="run",
                    code=r"""
DISPLAY SW_START,SW_SUBS,SW_CHILD,SW_TREE,SW_MAP,SW_STAGE,SW_T,SW_TSW,SW_TPROB,SW_TSTG;
""",
                )
            self.tc.enqueue(self.construct_sw_uct)
            self.tc.enqueue(self.preprocess_cumulative_bounds)
            # fmt: off
            fillsow_batincludes1 = [
                ("COM_PROJ", "R,", "C", "T", "NO", "", ""),
                ("COM_TAX", "R,", "C,S,COM_VAR,CUR", "T", "YES", "SW_T(T,WW)", "NO"),
                ("NCAP_COST", "R,", "P", "T", "NO", "", ""),
            ]
            # fmt: on

            for arg in fillsow_batincludes1:
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                    )
                )

            if self.tc.defined("S_FLO_FUNC"):
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1="FLO_FUNC",
                        arg2="R,",
                        arg3="P,CG,CG2",
                        arg4="T",
                        arg5="NO",
                        arg6="",
                        arg7="",
                    )
                )

            if self.tc.defined("S_NCAP_AFS"):
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1="NCAP_AFS",
                        arg2="R,",
                        arg3="P,S",
                        arg4="T",
                        arg5="NO",
                        arg6="",
                        arg7="",
                    )
                )

            if self.tc.defined("S_COM_FR"):
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1="COM_FR",
                        arg2="R,",
                        arg3="C,S",
                        arg4="T",
                        arg5="NO",
                        arg6="",
                        arg7="",
                    )
                )

            # fmt: off
            fillsow_batincludes2 = [
                ("CAP_BND", "R,", "P,BD", "T", "YES", "SW_T(T,WW)", "NO"),
                ("COM_CUM", "R,COM_VAR,ALLYEAR,", "C,BD", "LL", "YES", "SUPERYR(T,LL)", "YES"),
                ("FLO_CUM", "R,P,C,ALLYEAR,", "BD", "LL", "YES", "SUPERYR(T,LL)", "YES"),
                ("UC_RHST", "UC_N,", "LIM", "T", "YES", "SW_T(T,WW)", "NO"),
                ("UC_RHSRT", "R,UC_N,", "LIM", "T", "YES", "SW_T(T,WW)", "NO"),
                ("UC_RHSTS", "UC_N,", "TS,LIM", "T", "YES", "SW_T(T,WW)", "NO"),
                ("UC_RHSRTS", "R,UC_N,", "TS,LIM", "T", "YES", "SW_T(T,WW)", "NO"),
            ]
            # fmt: on

            for arg in fillsow_batincludes2:
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                    )
                )

            if self.tc.defined("S_DAM_COST"):
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1="DAM_COST",
                        arg2="R,",
                        arg3="COM,CUR",
                        arg4="T",
                        arg5="YES",
                        arg6="SW_T(T,WW)",
                        arg7="YES",
                    )
                )

            # fmt: off
            fillsow_batincludes3 = [
                ("UC_RHS", "UC_N,LIM", "", "", "YES", "YES", "YES"),
                ("UC_RHSR", "R,UC_N,LIM", "", "", "YES", "YES", "YES"),
            ]
            # fmt: on

            for arg in fillsow_batincludes3:
                self.include(
                    FillsowStc(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                    )
                )

            self.tc.enqueue(self.clear_superyr)
            if self.env.mca == "YES":
                return
        self.post()
        self.tc.enqueue(self.s_com_tax)

        if self.tc.defined("S_FLO_FUNC"):
            self.tc.enqueue(self.preprocess_flo_func, swd=self.env.swd)
            if self.env.sensis != "YES":
                self.tc.enqueue(self.remap_reduced_func_flows)

        self.tc.enqueue(self.didfunc)

        if self.tc.defined("S_NCAP_AFS"):
            self.tc.enqueue(self.process_ncap_afs)

        if self.tc.defined("S_COM_FR"):
            self.tc.enqueue(self.process_com_fr)

    def clear_superyr(self) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="OPTION CLEAR=SUPERYR;")

    def post(self: StagesStc) -> None:
        g = self.tc

        # LABLE POST
        # * Levelize & merge
        self.include(
            PpLvlfcMod(
                self.tc,
                self.env,
                config=PpLvlfcModConfig(
                    arg1=g.s_com_tax,
                    arg2=(g.c,),
                    arg3=g.ComTs,
                    arg4=(g.comvar, g.cur, g.j, g.ww),
                    arg5=(),
                    arg6=g.allts,
                    arg7=(g.t,),
                    arg8=g.Rc[g.r, g.c].where[Ord(g.j) == 1],
                ),
            )
        )

    def didfunc(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Pre-process uncertain NCAP_COST
  OPTION RVP < S_NCAP_COST;
  OBJ_SIC(RVP(R,T,P),SOW)$SW_T(T,SOW) = PROD(SW_MAP(T,SOW,J,WW)$S_NCAP_COST(R,T,P,J,WW),S_NCAP_COST(R,T,P,J,WW))-1;
  OPTION CLEAR=RVP,CLEAR=TRACKP,CLEAR=S_NCAP_COST;
""",
        )

    def preprocess_inputs(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
 OPTION SUC_L<UC_T_SUCC; SUC_L(UC_ON)$SUC_L(UC_ON)=(NOT UC_DYNDIR(UC_ON,'RHS'));
*$SETLOCAL DEBUG YES
*-----------------------------------------------------------------------------
* Pre-preprocessing of inputs to internal mappings
 SW_SUBS('1',WW)$(ORD(WW) > 1) = 0;
 IF(SW_SUBS('1','1') EQ 0,
   IF(CARD(SW_SUBS)+CARD(SW_SPROB) EQ 0, SW_SUBS('1','1') = MAX(1,SMAX(WW$SW_PROB(WW),ORD(WW)));
   ELSE SW_SUBS('1','1') = MAX(1,SMAX(WW$(SW_SPROB('2',WW)+SW_SUBS('2',WW)),ORD(WW)))));

* Copy number of childs from first parent to others when missing
 LAST_VAL = SMAX((J,WW)$SW_SUBS(J,WW),ORD(J));
 LOOP(JJ(J-1)$(ORD(J) LE LAST_VAL),
   F = MAX(1,SW_SUBS(J,'1')); Z = SUM(WW$SW_SUBS(JJ,WW),SW_SUBS(JJ,WW));
   LOOP(WW$(ORD(WW) LE Z),
     IF(NOT SW_SUBS(J,WW), SW_COPY(J,WW)$(ORD(WW) > 1) = YES; SW_SUBS(J,WW) = F;)));

* Construch SW_CHILD
 LOOP((J,ALLSOW)$SW_SUBS(J,ALLSOW),
  IF(ORD(ALLSOW) EQ 1, F = 0);
  Z = SW_SUBS(J,ALLSOW)+F;
  SW_CHILD(J,ALLSOW,WW)$((ORD(WW) LE Z)*(ORD(WW) > F)) = YES;
  F = Z;);

* Construct sow:
 LOOP(SW_CHILD(J,ALLSOW,WW), SOW(WW) = YES);
""",
        )

    def check_parameters(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
  SW_PHASE = 0;
* Make sure OBJZ will not be generated
    UC_TS_SUM(R,'OBJZ',S) = NO;
    UC_TS_EACH(R,'OBJZ',S) = NO;
  IF(SUM((UC_N,SOW)$S_UCOBJ(UC_N,SOW),1),
    SW_START('1') = 9999;
    SW_LAMBDA = 0;
    SW_PHASE = -9;
* Make sure OBJ1 will not be generated
    UC_TS_SUM(R,'OBJ1',S) = NO;
    UC_TS_EACH(R,'OBJ1',S) = NO;
    UC_T_SUM(R,'OBJ1',T) = NO;
* Complete checking for uncertain parameters
    CNT = SW_PARM;
    CNT$(NOT CNT) = SUM((UC_N,BD,J,W)$S_UC_RHS(UC_N,BD,J,W),1);
    CNT$(NOT CNT) = SUM((R,UC_N,BD,J,W)$S_UC_RHSR(R,UC_N,BD,J,W),1);
    CNT$(NOT CNT) = SUM((UC_N,T,BD,J,W)$S_UC_RHST(UC_N,T,BD,J,W),1);
    CNT$(NOT CNT) = SUM((R,UC_N,T,BD,J,W)$S_UC_RHSRT(R,UC_N,T,BD,J,W),1);
    CNT$(NOT CNT) = SUM((UC_N,T,S,BD,J,W)$S_UC_RHSTS(UC_N,T,S,BD,J,W),1);
    CNT$(NOT CNT) = SUM((R,UC_N,T,S,BD,J,W)$S_UC_RHSRTS(R,UC_N,T,S,BD,J,W),1);
* Reset UCOBJ(OBJ1) flags to either 1 or 2:
  FIRST_VAL = S_UCOBJ('OBJ1','1');
  S_UCOBJ('OBJ1',SOW) = 1+1$(S_UCOBJ('OBJ1',SOW) GE 0);
* Copy UCOBJ from previous if missing and uncertain parameters defined
    LOOP((SOW(WW),W(WW-1)),
      IF(SUM(UC_N$S_UCOBJ(UC_N,SOW),1) EQ 1,
        S_UCOBJ(UC_N,SOW) $= S_UCOBJ(UC_N,W);
        S_UCOBJ('OBJ1',SOW) = 4+2$CNT;));
* Check setups with single terminal SOW:
    IF(FIRST_VAL,
  {"IF((FIRST_VAL EQ 0)$(NOT SW_PARM), SW_PARM = 1;" if self.env.stages == "YES" else ""}
  {"ELSE S_UCOBJ('OBJ1',SOW)=S_UCOBJ('OBJ1',SOW)-ABS(S_UCOBJ('OBJ1',SOW)-4); SW_PARM = -1);" if self.env.stages == "YES" else ""}
    ELSE SW_PARM = 0); S_UCOBJ('OBJ1',SOW(WW))$(ORD(WW) EQ CARD(SOW)) = MAX(0,S_UCOBJ('OBJ1',WW));
* Check MinMax Regret option
  ELSEIF SUM((J,SOW)$S_UC_RHS('OBJ1','FX',J,SOW),1), UC_T_SUM(R,'OBJ1',T) = NO; SW_LAMBDA = -1
  );
  {"SW_START('1') = 9999; SW_LAMBDA = 0; SW_PARM = 0;" if self.env.stages != "YES" else ""}
""",
        )

    def construct_spanning_tree(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Contruct spanning tree
 FOR(Z = LAST_VAL-1 DOWNTO 0,
  LOOP((SAMEAS(J-Z,'1'),JJ(J+1)),
   IF(Z=LAST_VAL-1,SW_TREE(J,ALLSOW,SOW)$SW_CHILD(J,ALLSOW,SOW) = YES;
   ELSE LOOP(SW_CHILD(J,ALLSOW,WW),SW_TREE(J,ALLSOW,SOW)$SW_TREE(JJ,WW,SOW) = YES;));
 ));

* Adjust SW_START to period years
 MY_FYEAR = SW_START('1'); Z = 0; SW_START('1') = 0;
 SW_START(J)$(ORD(J) > LAST_VAL+1) = 0;
 LOOP(MIYR_1(TT), F = -1;
  LOOP(J$(ORD(J) LE LAST_VAL+1),
    MY_F = SW_START(J);
    IF(NOT MY_F, F = F+1; Z = MAX(Z+1,YEARVAL(TT+F)); SW_START(J) = Z;
    ELSEIF MY_F > Z, Z = MY_F; F = MAX(1,F,SUM(T$(YEARVAL(T) < MY_F),1));
      SW_START(J) = MAX(YEARVAL(TT+(F-1))+1,Z);
    ELSE SW_START(J) = SW_START(J-1));
 ));

* Construct mapping of valid data stages for each T
 LOOP(J$SW_START(J), SW_TSTG(T,J)$(SW_START(J) LE YEARVAL(T)) = YES);
* Reset SW_START if first year is large
 IF(MY_FYEAR GE SW_START('2'), SW_START(J)$((SW_START(J) LE MY_FYEAR)$SW_START(J)) = MIYR_V1);

* Construct SW_STAGE for internal SOWs
 SW_DESC(J,WW) = SUM(SW_TREE(J,WW,SOW),1);
 LOOP(SAMEAS(WW,'1'), F = 0;
   LOOP((J,SOW)$SW_SUBS(J,SOW),
     IF(ORD(J) NE F, Z = 0; F = ORD(J));
     SW_STAGE(J,WW+Z) = YES;
     Z = Z + SW_DESC(J,SOW);
 ));

* Copy probabilities when missing
 LOOP((JJ(J-1),ALLSOW)$SW_SUBS(JJ,ALLSOW), Z=0; MY_F=0;
   IF(ORD(ALLSOW) EQ 1, F=0; ELSE F=F+CNT); CNT=SW_SUBS(JJ,ALLSOW);
   LOOP(SW_CHILD(JJ,ALLSOW,WW)$SW_SPROB(J,WW), Z=Z+SW_SPROB(J,WW); MY_F=MY_F+1);
   IF(SW_COPY(JJ,ALLSOW)$(NOT MY_F), SW_SPROB(J,WW)$SW_CHILD(JJ,ALLSOW,WW) = SW_SPROB(J,WW-F);
   ELSE SW_SPROB(J,WW)$((NOT SW_SPROB(J,WW))*SW_CHILD(JJ,ALLSOW,WW)) = MAX(0,1-Z)/(CNT-MY_F));
 );
* Set map for copying attributes
 LOOP(SW_COPY(JJ(J-1),W), F=0; LOOP(SW_CHILD(JJ,W,WW), IF(F=0,F=ORD(WW)-1); SW_CPMAP(J,WW,WW-F)=YES));

* Normalize probabilities under each parent
 SW_SPROB('1','1') = 1;
 LOOP((J,WW)$SW_SUBS(J,WW),
   Z = SUM(SOW$SW_CHILD(J,WW,SOW),SW_SPROB(J+1,SOW));
   IF(Z NE 1,SW_SPROB(J+1,SOW)$SW_CHILD(J,WW,SOW) = SW_SPROB(J+1,SOW)/Z;);
 );

* Add final stage to SW_TREE
  LOOP(SAMEAS(J-LAST_VAL,'1'), SW_TREE(J,SOW,SOW) = YES);
  OPTION SW_REV < SW_TREE;
* Calculate final stage probabilities
  SW_PROB(SOW)$(NOT SW_PROB(SOW)) = PROD(SW_TREE(JJ,ALLSOW,SOW),SW_SPROB(JJ,ALLSOW));
""",
        )

    def normalize_probability_distribution(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Normalize probability distribution
  SW_PROB(ALLSOW)$(SW_PROB(ALLSOW) LE 0) = 0;
  Z = SUM(ALLSOW,SW_PROB(ALLSOW));
  IF(Z EQ 0, Z = 1; SW_PROB('1') = Z);
  SW_PROB(SOW) = SW_PROB(SOW)/Z;

* Set all SOWs into the last stage and Cumulate SOW from each stage to next:
  LOOP(SAMEAS(J,'1'), SW_STAGE(J+LAST_VAL,SOW) = YES;);
  LOOP(J$(ORD(J) LE LAST_VAL), SW_STAGE(J+1,SOW)$SW_STAGE(J,SOW) = YES;);

* Convert stages to periods
  LOOP(SW_STAGE(J,SOW), SW_T(T,SOW)$(SW_START(J) LE YEARVAL(T)) = YES);

* Map SOWs to unique SOW at each period:
  LOOP(T, F = 0;
    LOOP(SW_T(T,WW), Z = ORD(WW);
      SW_TSW(SOW(ALLSOW),T,WW+(F-Z))$((ORD(ALLSOW) GE F)*(ORD(ALLSOW) < Z)) = YES;
      F = Z;);
    SW_TSW(SOW(ALLSOW),T,WW)$((ORD(WW) EQ F)*(ORD(ALLSOW) GE F)) = YES;
  );

* Calculate aggregate probablilities; remove from maps all SOWs with zero PROB
  SW_TPROB(T,W) = SUM(SW_TSW(SOW,T,W),SW_PROB(SOW));
  SW_T(T,ALLSOW)$(SW_TPROB(T,ALLSOW) EQ 0) = NO;
  SW_TSW(SOW,T,WW)$(NOT SW_T(T,WW)) = NO;

* Construct mapping between internal (T,SOW) and original (J,SOW)
  SW_MAP(SW_T(T,WW),J,SOW)$(SW_TSTG(T,J)*SW_TREE(J,SOW,WW)) = YES;
""",
        )

    def construct_sw_uct(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Construct SW_UCT (needed to control dynamic stochastic UC-constraints)
  LOOP(R, SW_UCT(UC_N,SW_T(T,SOW))$(UC_T_SUCC(R,UC_N,T)$UC_DYNDIR(R,UC_N,'RHS'))  = YES;
    LOOP(SW_T(T+1,SOW),SW_UCT(UC_N,T,SOW)$(UC_T_SUCC(R,UC_N,T)*(NOT UC_DYNDIR(R,UC_N,'RHS'))) = YES;));
""",
        )

    def preprocess_cumulative_bounds(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Pre-Process cumulative bounds
  S_FLO_CUM(R,P,C,BOHYEAR+BEOH(BOHYEAR),EOHYEAR+BEOH(EOHYEAR),BD,J,SOW) $= S_FLO_CUM(R,P,C,BOHYEAR,EOHYEAR,BD,J,SOW);
  S_FLO_CUM(R,P,C,BOHYEAR,EOHYEAR,BD,J,SOW)$(NOT LL(BOHYEAR)*LL(EOHYEAR)) = 0;
  RPC_CUMFLO(RP(R,P),C,ALLYEAR,LL) $= SUM((BD,J,SOW)$S_FLO_CUM(R,P,C,ALLYEAR,LL,BD,J,SOW),YES);
*-----------------------------------------------------------------------------
* Construct SUPERYR (needed in cumulative constraints)
  SUPERYR(PERIODYR(T,LL)) = YES;
  LOOP(MIYR_1(T),SUPERYR(T--1,LL)$(YEARVAL(LL) > MIYR_VL) = YES);
""",
        )

    def s_com_tax(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
S_COM_TAX(RTC(R,T,C),S,COM_VAR,CUR,'1',W)$(NOT SW_T(T,W)) $= SUM(SW_TSW(W,T,WW),S_COM_TAX(RTC,S,COM_VAR,CUR,'1',WW));
""",
        )

    def preprocess_flo_func(self: StagesStc, swd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
PARAMETER RTP_FFCS(R,ALLYEAR,P,CG,CG{swd}); OPTION CLEAR=RTP_FFCS;
  RP_FFSGG(R,P,ACTCG(CG),CG) = NO;
  RP_FFSGGM(RP_PG(RP,CG1),CG,ACTCG,CG)$RP_FFSGG(RP,ACTCG,CG) = YES;
  RP_FFSGGM(RP_FFSGG(RP,CG,CG2),CG,CG2)$(NOT ACTCG(CG)) = YES;
  OPTION RP_FFSGG <= RP_FFSGGM, TRACKP < RP_FFSGG;
""",
        )

    def remap_reduced_func_flows(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=UNCD7; UNCD7(R,TT,T--ORD(T),P,SOW,'','')$TRACKP(R,P) $= RTP_VINTYR(R,TT,T,P)$SW_T(T,SOW);
  LOOP(UNCD7(R,T,TT,P,SOW,'',''),RTPW(R,T,P,SOW)=YES);
  RTP_FFCS(R,T,P,CG,COM_GRP,SOW)$(RTPW(R,T,P,SOW)*RP_FFSGG(R,P,CG,COM_GRP)) =
    SUM((RP_FFSGGM(R,P,CG,COM_GRP,CG1,CG2),SW_TSW(SOW,T,W)),
      PROD(SW_MAP(T,W,J,WW)$S_FLO_FUNC(R,T,P,CG1,CG2,J,WW),S_FLO_FUNC(R,T,P,CG1,CG2,J,WW))-1);
* Remap reduced FUNC flows
  LOOP(RPCG_PTRAN(RP,C,COM,CG,CG2)$RP_FFSGG(RP,CG,CG2),IF(RPC_FFUNC(RP,C),RP_DCGG(RP,C,CG,CG2,'UP')=YES; ELSE RP_DCGG(RP,COM,CG,CG2,'LO')=YES));
  RP_DCGG(RPC_FFUNC(RP,COM),CG,C,'UP')$(RPG_1ACE(RP,CG,COM)$RPC_ACT(RP,C)) $= RP_FFSGG(RP,CG,C);
  RTP_FFCS(RTP(R,T,P),ACTCG,C,W)$RPC_FFUNC(R,P,C) $= SUM(RP_DCGG(R,P,C,CG,CG2,L),(POWER(RTP_FFCS(RTP,CG,CG2,W)+1,BDSIG(L))-1)$(RTP_FFCS(RTP,CG,CG2,W)+1));
  LOOP(RP_DCGG(R,P,C,CG,CG2,L),RTP_FFCS(R,T,P,CG,CG2,W) = 0);
  OPTION CLEAR=S_FLO_FUNC,CLEAR=RTPW,CLEAR=RP_DCGG,CLEAR=RP_FFSGG,CLEAR=RP_FFSGGM;
""",
        )

    def process_ncap_afs(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
LOOP(J, RTP_SAFS(R,T,P,S,W) $= SUM(SW_MAP(T,W,J,WW),S_NCAP_AFS(R,T,P,S,J,WW)));
  OPTION CLEAR=S_NCAP_AFS;
  LOOP(BDUPX(BD),
  S_NCAP_AFS(R,T,P,S,'1',W)$((NCAP_AF(R,T,P,S,BD) > 0)$RTP_SAFS(R,T,P,S,W)) = RTP_SAFS(R,T,P,S,W)/NCAP_AF(R,T,P,S,BD);
  S_NCAP_AFS(R,T,P,S,'1',W)$((NCAP_AFS(R,T,P,S,BD) > 0)$RTP_SAFS(R,T,P,S,W)) = RTP_SAFS(R,T,P,S,W)/NCAP_AFS(R,T,P,S,BD);
  S_NCAP_AFS(R,T,P,ANNUAL(S),'1',W)$((NCAP_AFA(R,T,P,BD) > 0)$RTP_SAFS(R,T,P,S,W)) = RTP_SAFS(R,T,P,S,W)/NCAP_AFA(R,T,P,BD));
  OPTION CLEAR=RTP_SAFS;
  RTP_SAFS(R,T,P,S,W)$S_NCAP_AFS(R,T,P,S,'1',W) = ROUND(S_NCAP_AFS(R,T,P,S,'1',W)-1,8);
  OPTION CLEAR=S_NCAP_AFS;
""",
        )

    def process_com_fr(self: StagesStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  T0(T)=YES; T0('0')=YES; SW_T2W(SW_TSW(SOW,T,WW),T)=YES; SW_T2W(SW_TSW(SOW,T,WW),'0')$SW_TSTG(T,'2')=YES;
  LOOP(J, RTCS_SFR(R,T,C,S,W,S) $= SUM(SW_MAP(T,W,J,WW),S_COM_FR(R,T,C,S,J,WW)));
  RTCS_SFR(R,T,C,S,W,S)$RTCS_SFR(R,T,C,S,W,S) = RTCS_SFR(R,T,C,S,W,S)-1;
  OPTION CLEAR=S_COM_FR;
* Fill down the multipliers
  RTCSW(R,T,C,S+STOA(S),W)$RTCS_SFR(R,T,C,S,W,S) = YES;
  RTCSW(R,T,C,S,W)$((COM_FR(R,T,C,S) > 0)$RTCSW(R,T,C,'ANNUAL',W)) = YES;
  RTCS_SFR(RTCSW(R,T,C,S,W),S)$((NOT RTCS_SFR(RTCSW,S))$TS_GROUP(R,'WEEKLY',S)) = SUM(RS_BELOW1(R,TS,S),RTCS_SFR(R,T,C,TS,W,TS));
  RTCS_SFR(RTCSW(R,T,C,S,W),S)$((NOT RTCS_SFR(RTCSW,S))$TS_GROUP(R,'DAYNITE',S)) = SUM(RS_BELOW1(R,TS,S),RTCS_SFR(R,T,C,TS,W,TS));
* Sum up COM_FR for all commodities that have it defined
  FOR(Z=3 DOWNTO 1,LOOP(TSLVL$(ORD(TSLVL)=Z),
  RTCS_SFR(RTCSW(R,T,C,S,W),S)$TS_GROUP(R,TSLVL,S) =
    SUM(RS_BELOW1(R,S,TS),(1+RTCS_SFR(R,T,C,TS,W,TS))*COM_FR(R,T,C,TS))/COM_FR(R,T,C,S)-1;
  ));
  S_COM_FR(R,T,C,S,'1',W)$RTCSW(R,T,C,S,W) = (1+RTCS_SFR(R,T,C,S,W,S))/(1+RTCS_SFR(R,T,C,'ANNUAL',W,'ANNUAL'))-1;
  OPTION CLEAR=RTCS_SFR;
  RTCS_SFR(RTCSW(R,T,C,S,W),TS)$RS_BELOW(R,TS,S) = (1+{macro.rtcs_fr.rtcs_frmx("R", "T", "C", "S", "TS")})*(((1+S_COM_FR(R,T,C,S,'1',W))/MAX(1E-9,1+S_COM_FR(R,T,C,TS,'1',W)))-1);
  RTCS_SFR(RTCSW(R,T,C,S,W),TS)$(ABS(RTCS_SFR(R,T,C,S,W,TS)) < 1E-9) = 0;
  RTCS_SFR(R,LL--ORD(LL),C,S,W,TS)$SW_TSTG(LL,'2') $= RTCS_SFR(R,LL,C,S,W,TS);
  RTCS_SFR(R,T,C,S,W,TS)$(SW_TSTG(T,'2')$RTCS_SFR(R,'0',C,S,W,TS)) = RTCS_SFR(R,T,C,S,W,TS)-RTCS_SFR(R,'0',C,S,W,TS);
  OPTION RCS_SSFR <= RTCS_SFR; OPTION CLEAR=RTCSW,CLEAR=RTCS_SFR;
""",
        )
