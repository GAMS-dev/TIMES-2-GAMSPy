# rpt_ext_ecb.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * RPT_EXT.ecb - Extension for the Market Sharing Mechanism (economic choices)
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Equation

from core.base_class import GamsClass
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.solve_mod import SolveMod
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtEcb(GamsClass):
    """Translation unit for rpt_ext.ecb."""

    # Instance attributes
    module_name: str = "rpt_ext_ecb"
    gams_source: str = "rpt_ext.ecb"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        model_name: str,
        equations: list[Equation],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.model_name = model_name
        self.equations = equations
        self.arg1 = arg1
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        if not self.tc.defined("RTC_MS"):
            return

        self.tc.enqueue(self.exec1, self.env.capjd)

        if "DOITER" in self.tc.container.listParameters():
            self.tc.enqueue(self.exec_doiter_na)

        if self.env.macro.upper() == "MLF":
            return

        # * Resolve model
        self.tc.enqueue(self.exec_set_solveopt_merge)
        self.include(
            SolveMod(
                self.tc,
                self.env,
                arg1=self.arg1,
                model_name=self.model_name,
                equations=self.equations,
            )
        )
        self.env.set_scoped("solveda", "1")
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(arg4=("NO",)),
            )
        )
        self.tc.enqueue(self.exec2)

    def exec1(self: RptExtEcb, capjd: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  OPTION RVP < COEF_LMS, CLEAR=OBJ_SUMSI;
  OBJ_SUMSI(RTP(R,T,P),V)$RVPT(R,V,P,T) = YES;
  OBJ_SUMSI(RTP(R,T,P),T)$(COEF_CPT(R,T,T,P)>0) = YES;
* Existence flags
  PAR_TOP(RVP(R,T,P),C,'OUT')$COEF_LMS(R,T,C,P) = SUM((OBJ_SUMSI(RVP,V),PRC_TS(R,P,S)),PAR_NCAPL(R,V,P)*PAR_FLO(R,V,T,P,C,S)>0);
  PAR_TOP(RVP(R,T,P),C,IO)$PAR_TOP(RVP,C,IO) = SUM(OBJ_SUMSI(RVP,V),PAR_NCAPL(R,V,P)*PRC_CAPACT(R,P)*POWER(COEF_CPT(R,V,T,P),0.5$(DIAG(V,T)-1)))/VAR_XCAP.L(R,T,C)+EPS;
* Implied utilization factors
  PASTSUM(RVP(R,T,P))$PAR_CAPL(RVP) = (PAR_CAPL(RVP)+SUM(PASTCV,PAR_PASTI(R,T,P,PASTCV)))*PRC_CAPACT(R,P)+1-1;
  PASTSUM(NCAP_YES(RVP(R,V,P))) =
    (SUM(RTP_CPTYR(R,V,T,P),COEF_PVT(R,T)*SUM(RPCS_VAR(RPC_PG(R,P,C),S),PAR_FLO(R,V,T,P,C,S))) / SUM(RTP_CPTYR(R,V,T,P),COEF_PVT(R,T)*VAR_NCAP.L(RVP)*COEF_CPT(R,V,T,P)*PRC_CAPACT(R,P)))$PRC_VINT(R,P) +
    (SUM(RTP_CPTYR(R,V,T,P)$PASTSUM(R,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)/PASTSUM(R,T,P)*SUM(RPCS_VAR(RPC_PG(R,P,C),S),PAR_FLO(R,T,T,P,C,S))) / SUM(RTP_CPTYR(R,V,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)))$(NOT PRC_VINT(R,P));
  PASTSUM(RVP)$((PASTSUM(RVP)=0)$PASTSUM(RVP)) = 0;
* Calculate INV unit cost annuity and intangibles
  COEF_RTP(RVP(R,T,P)) =
    SUM(OBJ_ICUR(RVP,CUR),SUM(OBJ_SUMII(RVP,LIFE,K_EOH,JOT),{capjd} OBJ_CRF(RVP,CUR) / OBJ_DIVI(RVP) * SUM(INVSPRED(K_EOH,JOT,Y,K),{macro.obj_icost("R", "K", "P", "CUR")})));
  NCAP_MSPRF(R,T,C,P,'FX')$COEF_LMS(R,T,C,P) = NCAP_MSPRF(R,T,C,P,'LO')*SUM(OBJ_SUMSI(R,T,P,V)$PASTSUM(R,V,P),COEF_RTP(R,V,P)/PRC_CAPACT(R,P)/PASTSUM(R,V,P));
* Map LEC(v) and IUF(v) to t
  ECB_NCAPR(RVP)$PASTSUM(RVP)$=PAR_NCAPR(RVP,'LEVCOST');
  PAR_NCAPR(RVP(R,T,P),'LEVCOST') = SUM(OBJ_SUMSI(RVP,V),PAR_NCAPR(R,V,P,'LEVCOST'));
  PASTSUM(RVP(R,T,P)) = SUM(OBJ_SUMSI(RVP,V),PASTSUM(R,V,P));
  OPTION CLEAR=RVP,CLEAR=COEF_RTP;
*-----------------------------------------------------------------------------
* Calculate logit market shares
  LOOP(RTC_MS(RTC(R,T,C)), Z = -ABS(COM_MSHGV(RTC)); OPTION CLEAR=PRC_YMIN;
* Get weights for shares and their sum
    PRC_YMIN(R,P)$PAR_TOP(R,T,P,C,'OUT') = (NCAP_MSPRF(RTC,P,'N')/PASTSUM(R,T,P))*((PAR_NCAPR(R,T,P,'LEVCOST')+NCAP_MSPRF(RTC,P,'FX'))**Z)$(PAR_NCAPR(R,T,P,'LEVCOST')>1E-3);
    F = SUM(P$PRC_YMIN(R,P),PRC_YMIN(R,P));
    IF(F>0,
* Get initial shares and their Max
      PRC_YMIN(R,P)$PRC_YMIN(R,P)=(PRC_YMIN(R,P)/F);
      F = SMAX(P$PRC_YMIN(R,P),PRC_YMIN(R,P));
      MY_F=SMAX(P$PRC_YMIN(R,P),PAR_TOP(R,T,P,C,'OUT'));
* Adjust shares, normalize, and get sum over cutoff
      PRC_YMIN(R,P)$((PRC_YMIN(R,P)>.05)$PRC_YMIN(R,P)) = MAX(PRC_YMIN(R,P),PAR_TOP(R,T,P,C,'OUT')/MY_F*F);
      F = SUM(P$PRC_YMIN(R,P),PRC_YMIN(R,P));
      PRC_YMIN(R,P)$PRC_YMIN(R,P)=(PRC_YMIN(R,P)/F)$(PRC_YMIN(R,P)/F>.005);
      F = SUM(P$PRC_YMIN(R,P),PRC_YMIN(R,P))*.9999;
* Get MY_F = Max share, and Z = sum of differences from max
      MY_F = SMAX(P$PRC_YMIN(R,P),PRC_YMIN(R,P)); Z = SUM(P$PRC_YMIN(R,P),MY_F-PRC_YMIN(R,P));
      IF(Z, CNT=1; ELSE CNT=F);
* Final normalized share values: V0i+(MAX0-V0i)*(1-SUM0)/DIFSUM
      COEF_LMS(RTC,P)$COEF_LMS(RTC,P) = PRC_YMIN(R,P)/CNT+((MY_F-PRC_YMIN(R,P))*(1-F)/Z)$PRC_YMIN(R,P)$Z;
    ELSE COEF_LMS(RTC,P)$COEF_LMS(RTC,P)=0));
  OPTION CLEAR=PRC_YMIN,CLEAR=OBJ_SUMSI,CLEAR=PASTSUM,CLEAR=PAR_TOP;
*-----------------------------------------------------------------------------
* Reports clear
  OPTION CLEAR=REG_WOBJ, CLEAR=REG_IREC, CLEAR=REG_ACOST, CLEAR=CAP_NEW, CLEAR=PAR_EOUT, CLEAR=F_IN, CLEAR=F_OUT, CLEAR=P_OUT, CLEAR=AGG_OUT;
  OPTION CLEAR=PAR_ACTL, CLEAR=PAR_ACTM, CLEAR=PAR_PASTI, CLEAR=PAR_CAPL, CLEAR=PAR_CAPM, CLEAR=PAR_CAPBD, CLEAR=PAR_CUMRET, CLEAR=PAR_NCAPL, CLEAR=PAR_NCAPM, CLEAR=PAR_NCAPR, CLEAR=PAR_OBJSAL;
  OPTION CLEAR=PAR_COMPRDL, CLEAR=PAR_COMPRDM, CLEAR=PAR_COMNETL, CLEAR=PAR_COMNETM, CLEAR=PAR_COMBALEM, CLEAR=PAR_COMBALGM, CLEAR=PAR_IPRIC, CLEAR=PAR_PEAKM;
  OPTION CLEAR=PAR_UCSL, CLEAR=PAR_UCSM, CLEAR=PAR_CUMFLOL, CLEAR=PAR_CUMFLOM, CLEAR=PAR_CUMCST, CLEAR=PAR_UCMRK, CLEAR=PAR_UCRTP, CLEAR=PAR_UCMAX;
  OPTION CLEAR=CST_INVC, CLEAR=CST_INVX, CLEAR=CST_DECC, CLEAR=CST_FIXC, CLEAR=CST_FIXX, CLEAR=CST_ACTC, CLEAR=CST_FLOC, CLEAR=CST_FLOX, CLEAR=CST_IREC, CLEAR=CST_COMC, CLEAR=CST_COMX, CLEAR=CST_COME, CLEAR=CST_SALV, CLEAR=CST_TIME;
*-----------------------------------------------------------------------------
  F = RPT_OPT('NCAP','101'); IF(F,RPT_OPT('NCAP','1') = ROUND(F));
""",
        )

    def exec_doiter_na(self: RptExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="  DOITER=NA;",
        )

    def exec_set_solveopt_merge(self: RptExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="  OPTION SOLVEOPT=MERGE;",
        )

    def exec2(self: RptExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  PAR_NCAPR(RTP,'COST')$=ECB_NCAPR(RTP);
""",
        )
