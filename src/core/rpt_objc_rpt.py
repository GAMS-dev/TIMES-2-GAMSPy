# rpt_objc_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOL_FLO - code associated with the substitution of flow variables
# *	%1 - target parameter name
# *	%2 - parameter name suffix
# *	%3 - VAR_FLO suffix (.L or .M)
# *=============================================================================*

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from utils.macros import macro_config as macro

logger = logging.getLogger(__name__)


def _timesrng_load_code(
    *,
    timesrng_script: str,
    timesrng_gdx: str,
) -> str:
    script_path = Path(timesrng_script)

    if not (script_path.exists() and script_path.stat().st_size > 0):
        return ""

    subprocess.run(["python", timesrng_script], check=True)

    return rf"""
  IF(CNT,
   EXECUTE_LOAD '{timesrng_gdx}',VAR_NCAPRNG;
  );
"""


def rpt_objc_rpt(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    capjd: str,
    capwd: str,
    tpulse: str,
    stages: str,
    bencost: str,
    timesrng_script: str = "timesrng_inc.py",
    timesrng_gdx: str = "timesrng_inc",
) -> str:
    effective_bencost = "NO" if stages == "YES" else bencost
    bencost_yes = effective_bencost.upper() == "YES"

    return rf"""
* Remove any invalid marginals of OFFed technologies
  VAR_NCAP.M(RTP_OFF(R,T,P)) = 0; CNT = RPT_OPT('NCAP','1');
*-------------------------------------------------------------------------------
* Calculate the effect of a one unit of investment costs to the objective.
  OPTION CLEAR=PAR_OBJCAP;
  PAR_OBJCAP(OBJ_ICUR(R,T,P,CUR)) = COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) *
    SUM(OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,Y,K), (1-SALV_INV(R,T,P,Y)$OBJ_SUMS(R,T,P)) * OBJ_DISC(R,K,CUR)));
* If does not carry investment costs, just undiscount with most common inv. spread
  LOOP(G_RCUR(R,CUR), MY_ARRAY(T)=SUM(PERDINV(T,Y),OBJ_DISC(R,Y,CUR))/LEAD(T); COEF_OBJINV(RTP(R,T,P))$PRC_CAP(R,P)=MY_ARRAY(T));
  COEF_OBJINV(RTP(R,T,P)) $= SUM(RDCUR(R,CUR)$PAR_OBJCAP(R,T,P,CUR),PAR_OBJCAP(R,T,P,CUR));
*-------------------------------------------------------------------------------
{"  CNT = 1;" if bencost_yes else ""}
*-------------------------------------------------------------------------------
* Investment cost coefficient
  OPTION CLEAR=PAR_OBJCAP;
  IF(CNT,
  PAR_OBJCAP(OBJ_ICUR(R,T,P,CUR)) = COR_SALVI(R,T,P,CUR) / OBJ_DIVI(R,T,P) *
    SUM(OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT), {capjd}
      SUM(INVSPRED(K_EOH,JOT,Y,K), OBJ_DISC(R,K,CUR) *
        ({macro.obj_icost("R", "K", "P", "CUR")} + {
        macro.obj_itax("R", "K", "P", "CUR")
    } - {macro.obj_isub("R", "K", "P", "CUR")}
{
        f"        +SUM(SW_TSW(SOW,T,WW)$OBJ_SIC(R,T,P,WW),OBJ_SIC(R,T,P,WW)*{macro.obj_icost('R', 'K', 'P', 'CUR')}*(1-SALV_INV(R,T,P,Y)))"
        if stages.upper() == "YES"
        else ""
    }
        )));

* Decommissioning costs
  OPTION CLEAR=PAR_OBJSAL;
  PAR_OBJSAL(RTP(R,T,P),CUR)$RDCUR(R,CUR) = COR_SALVD(R,T,P,CUR) / OBJ_DIVIII(R,T,P) *
    SUM(OBJ_SUMIII(R,T,P,LL,K,Y)${
        macro.obj_dcost("R", "T", "P", "CUR")
    }, OBJ_DISC(R,Y,CUR) * {macro.obj_dcost("R", "K", "P", "CUR")});

  PAR_OBJCAP(RTP(R,T,P),CUR)$PAR_OBJSAL(R,T,P,CUR) = PAR_OBJCAP(R,T,P,CUR) + PAR_OBJSAL(R,T,P,CUR));
*-------------------------------------------------------------------------------
* Fixed O&M cost coefficient
  OPTION CLEAR=PAR_OBJSAL;
  IF(CNT,
  PAR_OBJSAL(OBJ_FCUR(R,T,P,CUR)) =
    SUM(OBJ_SUMIV(K_EOH,R,T,P,JOT,LIFE)$(NOT RTP_ISHPR(R,T,P)),
       SUM(INVSPRED(K_EOH,JOT,LL,K), OBJ_LIFE(LL,R,JOT,LIFE,CUR) * {capwd}
        ({macro.obj_fom("R", "K", "P", "CUR")}+{macro.obj_ftx("R", "K", "P", "CUR")}-{
        macro.obj_fsb("R", "K", "P", "CUR")
    })) / OBJ_DIVIV(R,T,P)) +

    SUM(OBJ_SUMIV(K_EOH,RTP_ISHPR(R,T,P),JOT,LIFE),
       SUM((INVSPRED(K_EOH,JOT,LL,K),OPYEAR(LIFE,AGE),Y_EOH(LL+(ORD(AGE)-1))),
           OBJ_DISC(R,Y_EOH,CUR) * {capwd}
              (
                {
        macro.obj_fom("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,T,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                {
        macro.obj_ftx("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,T,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
                {
        macro.obj_fsb("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,T,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
              )
           ) / OBJ_DIVIV(R,T,P));

  PAR_OBJCAP(RTP(R,T,P),CUR)$PAR_OBJSAL(R,T,P,CUR) = PAR_OBJCAP(R,T,P,CUR) + PAR_OBJSAL(R,T,P,CUR));
*-------------------------------------------------------------------------------
* Decommissioning Surveillance coefficient
  PAR_OBJCAP(RTP(R,T,P),CUR)$({
        macro.obj_dlagc("R", "T", "P", "CUR")
    }$CNT) = PAR_OBJCAP(R,T,P,CUR) +
        SUM(OBJ_SUMIVS(R,T,P,K,Y), OBJ_DISC(R,Y,CUR) * {
        macro.obj_dlagc("R", "K", "P", "CUR")
    });
*-------------------------------------------------------------------------------
* Capacity-related flow cost coefficient
  OPTION CLEAR=PAR_OBJSAL;
  PASTSUM(RTP(R,V(TT),P))$CNT =
    SUM((RPC_CAPFLO(R,V,P,C),RDCUR(R,CUR)),
* Flows related to investment / decommissioning
      SUM(VNT(V,T)$(COEF_ICOM(R,V,T,P,C)+COEF_OCOM(R,V,T,P,C)),(COEF_ICOM(R,V,T,P,C)+COEF_OCOM(R,V,T,P,C)) *
        SUM(RPCS_VAR(R,P,C,TS), G_YRFR(R,TS) * SUM(TS_ANN(TS,SL),SUM({tpulse}({
        macro.obj_fcost("R", "Y_EOH", "P", "C", "SL", "CUR")
    }+{macro.obj_fdelv("R", "Y_EOH", "P", "C", "SL", "CUR")}+{
        macro.obj_ftax("R", "Y_EOH", "P", "C", "SL", "CUR")
    }))))) +
* Flows related to existing capacity over lifetime
      SUM((RTP_CPTYR(R,V,T,P),IO)$NCAP_COM(R,V,P,C,IO),
        COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,IO) * (1 + COEF_CIO(R,V,T,P,C,IO)) *
        SUM(RPCS_VAR(R,P,C,TS), G_YRFR(R,TS) * SUM(TS_ANN(TS,SL),SUM({tpulse}({
        macro.obj_fcost("R", "Y_EOH", "P", "C", "SL", "CUR")
    }+{macro.obj_fdelv("R", "Y_EOH", "P", "C", "SL", "CUR")}+{
        macro.obj_ftax("R", "Y_EOH", "P", "C", "SL", "CUR")
    })))))
    );
*-------------------------------------------------------------------------------
* Salvage coefficient
  OPTION CLEAR=PAR_OBJSAL,CLEAR=COEF_RTP;
  PAR_OBJSAL(RTP(R,T,P),CUR)$RDCUR(R,CUR) =
*   Cases I - Investment Cost and II - Taxes/Subsidies
    SUM(OBJ_SUMS(R,T,P), OBJSCC(R,T,P,CUR)) * OBJ_DCEOH(R,CUR) * (1+SUM(NCAP_YES(RTP),VAR_SCAP.L(R,T,'0',P)/RTP_CAPVL(RTP)-1)$RVPRL(RTP)) +
*   Cases III - Decommissioning
    SUM(OBJ_SUMS3(R,T,P), SALV_DEC(R,T,P,CUR)) * OBJ_DCEOH(R,CUR) +
*   Cases IV - Decommissioning Surveillance
      SUM(OBJ_SUMIVS(R,T,P,K,Y)$SALV_INV(R,T,P,K),
          OBJ_DISC(R,Y,CUR) * {
        macro.obj_dlagc("R", "K", "P", "CUR")
    } * SALV_INV(R,T,P,K));

  COEF_RTP(R,T,P) $= SUM(CUR$PAR_OBJCAP(R,T,P,CUR),ROUND(PAR_OBJCAP(R,T,P,CUR)-PAR_OBJSAL(R,T,P,CUR),7));
{
        ""
        if not bencost_yes
        else rf"""
*-------------------------------------------------------------------------------
* Add range information if available
  OPTION CLEAR=VAR_NCAPRNG;
{_timesrng_load_code(timesrng_script=timesrng_script, timesrng_gdx=timesrng_gdx)}
* Calculate CostBen indicators
  {arg1}PAR_NCAPR({arg2}RTP(R,T,P),'{arg3}COST') $= COEF_RTP(R,T,P)+PASTSUM(R,T,P);
  PASTSUM(R,T,P)${arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}COST') = VAR_NCAP.M(R,T,P)+EPS;
  PASTSUM(RTP(R,T,P))$((VAR_NCAPRNG(RTP,'LO') GT -9E9)$(ABS(VAR_NCAP.L(RTP)) LT MICRO)$PASTSUM(RTP)) = MAX(PASTSUM(RTP),-VAR_NCAPRNG(RTP,'LO'));
  OPTION RVP < PASTSUM;
  {arg1}PAR_NCAPR({arg2}RTP(R,T,P),'{arg3}CGAP')${arg1}PAR_NCAPR({arg2}RTP,'{arg3}COST') = PASTSUM(RTP)+EPS;
  {arg1}PAR_NCAPR({arg2}RVP(R,T,P),RNGLIM) = SUM(RNGMAP(RNGLIM,BD),VAR_NCAPRNG(R,T,P,BD));
*-------------------------------------------------------------------------------
* Calculate the net activity benefits
  BC_INVACT(RTP_VINTYR(R,V,T,P),S)$(PRC_TS(R,P,S)$RVP(R,V,P)) =
    -ROUND(VAR_ACT.M(R,V,T,P,S)+SMIN(RPC_PG(R,P,C),VAR_FLO.M(R,V,T,P,C,S)*PRC_ACTFLO(R,V,P,C)),7);
* Calculate the corresponding net NCAP benefits
  BC_INVTOT(RVP(R,V,P))$(NOT PRC_VINT(R,P)) = PRC_CAPACT(R,P) *
    SUM((RTP_CPTYR(R,V,T,P),PRC_TS(R,P,S),BDUPX(BD))$COEF_AF(R,V,T,P,S,BD), COEF_CPT(R,V,T,P) * COEF_AF(R,V,T,P,S,BD) *
       G_YRFR(R,S) * MAX(-INF$BDLOX(BD),BC_INVACT(R,T,T,P,S)));
  BC_INVTOT(RVP(R,V,P))$PRC_VINT(R,P) = PRC_CAPACT(R,P) *
    SUM((RTP_VINTYR(R,V,T,P),PRC_TS(R,P,S),BDUPX(BD))$COEF_AF(R,V,T,P,S,BD), COEF_CPT(R,V,T,P) * COEF_AF(R,V,T,P,S,BD) *
       G_YRFR(R,S) * MAX(-INF$BDLOX(BD),BC_INVACT(R,V,T,P,S)));
* Add the net activity benefits to the net capacity benefits
  BC_INVTOT(RVP(R,T,P)) = BC_INVTOT(R,T,P) - VAR_NCAP.M(R,T,P) - SUM(TT$COEF_CPT(R,T,TT,P), COEF_CPT(R,T,TT,P) * VAR_CAP.M(R,TT,P)) +EPS;
  {arg1}PAR_NCAPR({arg2}RVP(R,T,P),'{arg3}GGAP') = MAX(-BC_INVTOT(R,T,P),(PASTSUM(R,T,P)-INF$(PASTSUM(R,T,P) LE MICRO)));
* Normalize and calculate RATIOs
  {arg1}PAR_NCAPR({arg2}RTP(R,T,P),SYSUC)${arg1}PAR_NCAPR({arg2}R,T,P,SYSUC) = {arg1}PAR_NCAPR({arg2}R,T,P,SYSUC)/COEF_OBJINV(R,T,P);
  {arg1}PAR_NCAPR({arg2}RVP(R,T,P),'{arg3}GRATIO') = 1-ROUND({arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}GGAP')/{arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}COST'),7)+EPS;
  {arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}RATIO')$COEF_RTP(R,T,P) = 1-ROUND({arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}CGAP')/{arg1}PAR_NCAPR({arg2}R,T,P,'{arg3}COST'),6)+EPS;
"""
    }
  OPTION CLEAR=RVP,CLEAR=PASTSUM;
"""
