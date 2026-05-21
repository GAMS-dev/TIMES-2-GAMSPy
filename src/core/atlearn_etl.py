# atlearn_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * File      : ATLEARN.ETL
# * Language  : GAMS
# * Programmer: Ad Seebregts, adaped by Gary Goldstein for TIMES
# * Origin    : 02-06-98
# * Last edit : 07-27-01
# * Warning   :
# * Purpose   : Write specific LEARNing output to output file, resembling standard
# *             MARKAL analysis table output
# * Location  : TIMES directory
# * Called    : at the end of RPTMAIN.MOD
# * Output    : <case>.ETL
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.atlearn1_etl import atlearn1_etl
from core.atlearn8_etl import atlearn8_etl
from core.atsc_etl import atsc_etl
from core.mod_vars_etl import ModVarsEtl

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class AtlearnEtl(GamsClass):
    """Translation unit for atlearn.etl."""

    # Instance attributes
    module_name: str = "atlearn_etl"
    gams_source: str = "atlearn.etl"

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
        self.tc.enqueue(self.exec1, self.env.run_name)

        if self.env.stages != "YES":
            pass
        else:
            if (
                self.env.sw_notags
                == "SET EQ 'EQ' SET VAR 'VAR' SET SWS '' SET SOW '' SET SWT '' SET SWD '' SET SWTD '' SET SWSW '' SET VART 'VAR' SET VARV 'VAR' SET VARM 'VAR' SET VARTT VAR"
            ):
                self.env.set_scoped("eq", "EQ")
                self.env.set_scoped("var", "VAR")
                self.env.set_scoped("sws", "")
                self.env.set_scoped("sow", "")
                self.env.set_scoped("swt", "")
                self.env.set_scoped("swd", "")
                self.env.set_scoped("swtd", "")
                self.env.set_scoped("swsw", "")
                self.env.set_scoped("vart", "VAR")
                self.env.set_scoped("varv", "VAR")
                self.env.set_scoped("varm", "VAR")
                self.env.set_scoped("vartt", "VAR")
            else:
                raise ValueError(f"Unknown value in sw_notags: {self.env.sw_notags}")
            self.include(ModVarsEtl(self.tc, self.env))
            # $ BATINCLUDE eqdeclr.etl <- file is missing
            if (
                self.env.sw_tags
                == "SET EQ 'ES' SET VAR 'VAS' SET SWD ',WW' SET SWTD ',T,WW' SET SWS ',W)' SET SOW ',SOW' SET SWT ',SW_T(T,SOW)' SET VART 'SUM(SW_TSW(SOW,T,W),VAS' SET VARV 'SUM(SW_TSW(SOW,V,W),VAS' SET VARM 'SUM(SW_TSW(SOW,MODLYEAR,W),VAS'"
            ):
                self.env.set_scoped("eq", "ES")
                self.env.set_scoped("var", "VAS")
                self.env.set_scoped("swd", ",WW")
                self.env.set_scoped("swtd", ",T,WW")
                self.env.set_scoped("sws", ",W)")
                self.env.set_scoped("sow", ",SOW")
                self.env.set_scoped("swt", ",SW_T(T,SOW)")
                self.env.set_scoped("vart", "SUM(SW_TSW(SOW,T,W),VAS")
                self.env.set_scoped("varv", "SUM(SW_TSW(SOW,V,W),VAS")
                self.env.set_scoped("varm", "SUM(SW_TSW(SOW,MODLYEAR,W),VAS")
            else:
                raise ValueError(
                    f"Unknown value in sw_notags: {self.env.sw_nosw_tagstags}"
                )

        self.tc.enqueue(
            self.exec_loop,
            self.env.stages,
            self.env.model_name,
            self.env.var,
            self.env.run_name,
        )

        if self.env.stages == "YES":
            return

        self.tc.enqueue(self.exec_export_capital_cost)

    def exec1(self: AtlearnEtl, run_name: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
FILE ETL / {run_name}.ETL /;
PUT ETL;
""",
        )

    def exec_loop(
        self: AtlearnEtl,
        stages: str,
        model_name: str,
        var: str,
        run_name: str,
    ) -> None:
        include_atlearn1_etl = atlearn1_etl(
            arg1="VAR_CCAP",
            arg2="Cumulative capacity",
            arg3="CCA",
            arg4="1",
            arg5="4",
        )
        code_str = rf"""
ETL.PW=1000;
ETL.ND=4;

PUT /"Generated by ATLEARN.ETL"/;
PUT  "-----------------------";
PUT /"Date: ", SYSTEM.DATE, " (M/D/Y)";
PUT /"Time: ", SYSTEM.TIME;
PUT /"-------------------------------------";
PUT /"MODELSTAT AND SOLVESTAT INFO";
PUT /"Modelstat            : ", {model_name}.MODELSTAT:2:0;
PUT /"Solvestat            : ", {model_name}.SOLVESTAT:2:0;
PUT /"Number of iterations : ", {model_name}.ITERUSD:7:0;
PUT /"Number of variables  : ", {model_name}.NUMVAR:7:0;
PUT /"Number of equations  : ", {model_name}.NUMEQU:7:0;

PUT /"Maximum number of segments: ", (CARD(KP)-1):3:0," (SET KP defined in MMINIT.INC)";
PUT /"Number of periods T      : ", CARD(T):3:0

PUT //"---------------------------------------------------------------------------------------"/;
PUT "* Input learning PARAMETERS:";
PUT "  - Progress ratio, Start cost, Initial Cum. Cap., max. Cum. Cap"/;
PUT "  - Indicators derived from these: Floor cost (absolute and as percentage)"/;
PUT "  - Max. number of doublings, number of segments linearization"/;
PUT "* Cluster input info:"/;
PUT "  - number of PRC's in cluster of key TEG (if any)"/;
PUT "  - PRC's per cluster and coupling factor"/;
PUT "---------------------------------------------------------------------------------------"/;
PUT  //"* PRC/REG", @30 "Description" @60
PUT  "     Pr       SC0";
PUT  "     CCAP0     CCAPM     FLOOR     perc.         n      #seg"
PUT  "      #tch"/;
LOOP((TEG,REG)$SEG(REG,TEG),
     PUT "KEY.",TEG.TL:0, '/REG.',REG.TL:0, @30, PRC.TE(TEG):30, @60
         PRAT(REG,TEG):10:3,
         SC0(REG,TEG):10:2,
         CCAP0(REG,TEG):10:4,
         CCAPM(REG,TEG):10:4,
* floor cost implied
         (PAT(REG,TEG)*(CCAPM(REG,TEG)**(-PBT(REG,TEG)))):10:2,
         ((PAT(REG,TEG)*(CCAPM(REG,TEG)**(-PBT(REG,TEG))))/SC0(REG,TEG)*100):10:2,
         (LOG(CCAPM(REG,TEG)/CCAP0(REG,TEG))/LOG(2)):10:2,
         SEG(REG,TEG):10:0,
         NTCHTEG(REG,TEG):10:0
         ;
     PUT /;
* cluster PRC's and coupling factors plus INVCOS
     LOOP(PRC$(CLUSTER(REG,TEG,PRC) GT 0),
          PUT "    ",PRC.TL:0;
          PUT PRC.TE(PRC):30;
          PUT CLUSTER(REG,TEG,PRC):10:3;
          PUT /;
          );

    );

PUT //"Levels of learning variables: Cum. Cap. (CCAP) and Specific Cost"/;
PUT   "k is for learning key technologies (in set TEG)"/;
PUT   "c is for technology in corresponding cluster defined by CLUSTER(REG,TEG,PRC)"/;
PUT   "------------------------------------------------------------------------"/;
{include_atlearn1_etl}

{atsc_etl()}


PUT //"Levels of TEG and PRC INV, CAP variables"/;
PUT   "Results in order of Key technologies (TEG) and technologies in corresponding cluster"/;
PUT   "Technologies in clusters may appear more than once if they belong to more than one cluster"/;
PUT   "*-----------------------------------------------------------------------------------------"/;

PUT "*      INV CAP plus CAP growth factors"/;
PUT "*      CAM : maximum capacity based on (user-provided) growth factors"/;
PUT "*      GRP : growth in capacity in one period (CAP(T)/CAP(T-1))"/;
PUT "*      GRA : average annual growth in NYEARS of period T"/;
PUT "*      GRF : growth factor (input): TID and time-dependent"/;
PUT "*-----------------------------------------------------------------------------------------"/;

{atlearn8_etl()}
"""
        if stages == "YES":
            code_str = (
                rf"""
LOOP(SOW,
* Get levels
    OPTION CLEAR=VAR_CCAP;
    OPTION CLEAR=VAR_CCOST;
    OPTION CLEAR=VAR_IC;
    OPTION CLEAR=VAR_CAP;
    OPTION CLEAR=VAR_NCAP;
    VAR_CCAP.L(R,T,P)  $= SUM(SW_TSW(SOW,T,W), {var}_CCAP.L(R,T,P,W));
    VAR_CCOST.L(R,T,P) $= SUM(SW_TSW(SOW,T,W), {var}_CCOST.L(R,T,P,W));
    VAR_IC.L(R,T,P)    $= SUM(SW_TSW(SOW,T,W), {var}_IC.L(R,T,P,W));
    VAR_CAP.L(R,T,P)   $= SUM(SW_TSW(SOW,T,W), {var}_CAP.L(R,T,P,W));
    VAR_NCAP.L(R,T,P)  $= SUM(SW_TSW(SOW,T,W), {var}_NCAP.L(R,T,P,W));
    PUT_UTILITY 'REN' / '{run_name}-',SOW.TL:0,'.ETL' ;
"""
                + code_str
            )
            code_str += ");"
        code_str += "PUTCLOSE ETL;"
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=code_str,
        )

    def exec_export_capital_cost(self: AtlearnEtl) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Exporting capital cost data for clustered technologies

* Create a set of all key components
* Create a set of all clustered technologies
  LOOP((RP(R,P),PRC)$((CLUSTER(R,P,PRC) > 0.0)$CLUSTER(R,P,PRC)),
     TL_RP_KC(R,P) = YES; TL_RP_CT(R,PRC) = YES);

  TL_CT_COST(REG,MILESTONYR,PRC,CUR)$TL_RP_CT(REG,PRC) = OBJ_ICOST(REG,MILESTONYR,PRC,CUR) +
     INVC_UNIT(REG,MILESTONYR,PRC) +
* Costs of key components in same region
     SUM(P$CLUSTER(REG,P,PRC), (OBJ_ICOST(REG,MILESTONYR,P,CUR) + INVC_UNIT(REG,MILESTONYR,P)) * CLUSTER(REG,P,PRC)) +
* Costs of multi-regional key components
     SUM(RP(R,P)$TL_MRCLUST(R,P,REG,PRC), (OBJ_ICOST(R,MILESTONYR,P,CUR) + INVC_UNIT(R,MILESTONYR,P)) * TL_MRCLUST(R,P,REG,PRC));
*-----------------------------------------------------------------------------

""",
        )
