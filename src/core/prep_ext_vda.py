# prep_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.VDA oversees all the added inperpolation activities needed by VEDA
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Comments: RVP can be used to control flow-related attribs instead of RTP
# *------------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.equcrtp_vda import EqucrtpVda
from core.fillparm_gms import FillparmGms
from core.fillvint_gms import FillvintGms
from core.powerflo_vda import PowerfloVda
from core.resloadc_vda import ResloadcVda
from core.utils import EscapeStack

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtVda(GamsClass):
    """Translation unit for prep_ext.vda."""

    # Instance attributes
    module_name: str = "prep_ext_vda"
    gams_source: str = "prep_ext.vda"

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
        self.tc.enqueue(self.prepare_availabilities)

        # fmt: off
        batincludes = [
            ("VDA_EMCB",   "R",      "C,COM",        ",'0','0','0','0'",     "V", "1",          "GE 0",           ""),
            ("NCAP_AFC",   "R",      "P,CG,STL",     ",'0','0','0'",         "V", "RTP(R,V,P)", "GE -1$ACTCG(CG)",""),
            ("ACT_EFF",    "R",      "P,CG,TS",      ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           "X_RPGS"),
            ("VDA_FLOP",   "R",      "P,CG,TS",      ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           "X_RPGS"),
            ("FLO_EMIS",   "R",      "P,CG,COM,S",   ",'0','0'",             "V", "RVP(R,V,P)", "GE 0",           "X_RPGCS"),
            ("ACT_UPS",    "R",      "P,S,BD",       ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_LOSPL",  "R",      "P,L",          ",'0','0','0','0'",     "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_LOSSD",  "R",      "P,UPT,BD",     ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_SDTIME", "R",      "P,UPT,BD",     ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_MAXNON", "R",      "P,UPT",        ",'0','0','0','0'",     "V", "RVP(R,V,P)", "GE 0",           ""),
            ("STG_MAXCYC", "R",      "P",            ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0",           ""),
        ]
        # fmt: on

        if self.tc.defined("UC_FLOBET"):
            batincludes.append("UC_FLOBET", "UC_N,R", "P,C", ",'0','0','0'", "T", "1", "GE 0", "")  # fmt: skip

        if self.tc.defined("COM_CSTBAL"):
            batincludes.append("COM_CSTBAL", "R", "C,S,ITEM,CUR", ",'0','0'", "T", "1", "GE 0", "")  # fmt: skip

        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                )
            )

        if self.env.powerflow.upper() == "YES":
            self.include(
                PowerfloVda(
                    self.tc,
                    self.env,
                    arg1="PREP",
                )
            )
        if self.tc.defined("GR_VARGEN"):
            self.include(ResloadcVda(self.tc, self.env))

        if self.tc.test_run:
            self.tc.save_test_state(
                env=self.env, checkpoint="prep_ext_vda_prio_equcrtp"
            )

        raise EscapeStack(self.module_name)
        self.include(EqucrtpVda(self.tc, self.env, arg1="PREP_EXT"))

        if self.env.vintopt == "1":
            self.include(
                FillvintGms(
                    self.tc,
                    self.env,
                    arg1="VDA_FLOP",
                    arg2="R",
                    arg3="P,CG,TS",
                    arg4="X_RPGS",
                )
            )
            self.include(
                FillvintGms(
                    self.tc,
                    self.env,
                    arg1="ACT_EFF",
                    arg2="R",
                    arg3="P,CG,TS",
                    arg4="X_RPGS",
                )
            )
        self.tc.enqueue(
            self.tailored_interpolation, waver=self.env.waver.upper() == "YES"
        )

    def prepare_availabilities(self: PrepExtVda):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Prepare commodity-specific availabilities; NCAP_AFAC overrides NCAP_AFC
  OPTION RP_GRP < NCAP_AFAC;
  NCAP_AFC(R,DATAYEAR,P,CG,'ANNUAL')$RP_GRP(R,P,CG) = NCAP_AFAC(R,DATAYEAR,P,CG);
  NCAP_AFC(R,LL,P,CG,STL(S)) $= NCAP_AFCS(R,LL,P,CG,S); OPTION CLEAR=NCAP_AFCS;
* Collect ACT_EFF groups
  OPTION RP_GRP < ACT_EFF, CLEAR=UNCD7;
  UNCD7(R,LL--ORD(LL),P,CG,S--ORD(S),'','')$BOHYEAR(LL) $= (ACT_EFF(R,LL,P,CG,S) GT 0)$ACT_EFF(R,LL,P,CG,S);
  LOOP(UNCD7(R,LL,P,CG,S,'',''),RPC_ACE(R,P,CG) = YES);
  RPG_1ACE(RP_GRP(RPC(R,P,C)),C)$(NOT RPC_ACE(RPC)) = YES;
  OPTION CLEAR=RP_GRP;
  ACT_FLO(R,LL--ORD(LL),P,C,S)$STOA(S) $= VDA_FLOP(R,LL,P,C,S);
""",
        )

    def tailored_interpolation(self: PrepExtVda, waver: bool):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  FLO_FUNCX(R,LL,P,C,CG)$(NOT PRC_VINT(R,P)) = 0;
*------------------------------------------------------------------------------

* Tailored interpolation of PRC_RESID
  OPTION CLEAR=PRC_YMAX,CLEAR=MY_ARRAY;
  TRACKP(R,P)$=PRC_RESID(R,'0',P); PRC_YMAX(TRACKP(R,P))=ROUND(PRC_RESID(R,'0',P));
  LOOP(PYR_S(PYR(LL)),
    PRC_RESID(R,'0',P)$TRACKP(R,P) = MAX(1,NCAP_TLIFE(R,LL,P)+G_TLIFE$(NOT NCAP_TLIFE(R,LL,P)));
    LOOP(TRACKP(R,P), DFUNC=PRC_YMAX(R,P);
      MY_ARRAY(DM_YEAR)=PRC_RESID(R,DM_YEAR,P); MY_F=0; F=0; Z=0;
* do interpolate
      LOOP(DM_YEAR$MY_ARRAY(DM_YEAR),
        LAST_VAL=MY_F; MY_F=MY_ARRAY(DM_YEAR); Z=YEARVAL(DM_YEAR);
        IF(LAST_VAL, PRC_RESID(R,T,P)$((Z>M(T))$(M(T)>MY_FYEAR)) = MY_F-(MY_F-LAST_VAL)/(Z-MY_FYEAR)*(Z-M(T));
        ELSE F=Z); MY_FYEAR=Z; CNT$(LAST_VAL+MY_F>0)=Z);
* If only one RESID Interpolate towards EPS at Z+TLIFE
      IF(ABS(DFUNC-10)=5, DFUNC=F; F=Z; ELSE F$DFUNC=0);
      IF(Z=F,CNT=PRC_RESID(R,'0',P); Z=F+CNT; DFUNC=DFUNC+CNT;
         PRC_RESID(R,T,P)$(M(T)>F)=MY_F*MAX(0,1-(M(T)-F)$(M(T)>=DFUNC)/CNT); MY_F=0; ELSE Z=CNT);
{"PRC_YMAX(R,P)=Z+1$(MY_F>0); IF(MY_F=0, PRC_RESID(R,LL+(Z-MIYR_BOH),P)=EPS);" if waver else ""}
    );
* Initialize PRC_RESID capacity availability:
    NCAP_TLIFE(R,LL,P)$TRACKP(R,P) = 1;
    NCAP_ILED(R,LL,P)$TRACKP(R,P) = 0;
    RTP_CPTYR(R,LL,T,P)$(((PRC_RESID(R,T,P)>0)+(B(T)<PRC_YMAX(R,P)))$TRACKP(R,P))=YES);
  OPTION CLEAR=TRACKP;
* INF-QA override
  IFQ$SUM(COM_TYPE(CG(R)),1)=0;
  COM_LIM(RC,BDNEQ)$COM_LIM(RC,'FX')=NO;
*-----------------------------------------------------------------------------
  ACT_MINLD(RTP) $= ACT_UPS(RTP,'ANNUAL','FX');
* Move non-standard share parameters to dedicated parameter
  FLO_ASHAR(R,DM_YEAR,P,C,CG,S,BD) $= FLO_SHAR(R,DM_YEAR,P,C,CG,S,BD)$(NOT COM_GMAP(R,CG,C)*RPC(R,P,C));
* Process cost-neutral ILEDs
  RVPRL(RTP(R,T,P)) $= SUM(PERIODYR(T,YEAR)$NCAP_BND(R,YEAR,P,'N'),NCAP_BND(R,YEAR,P,'N'));
  IF(CARD(RVPRL),LOOP(RTP(R,T,P)$RVPRL(RTP),Z=RVPRL(RTP); Z=Z/ROUND(Z/M(T)); NCAP_BND(RTP,'N')=Z;
    COEF_ILED(RTP) = ABS(NCAP_ILED(RTP))+1000; NCAP_ILED(RTP) = MAX(EPS,Z+1-B(T)));
    NCAP_BND(RTP,BDUPX)$(MAPVAL(NCAP_BND(RTP,BDUPX))$RVPRL(RTP))=0; OPTION CLEAR=RVPRL);
""",
        )
