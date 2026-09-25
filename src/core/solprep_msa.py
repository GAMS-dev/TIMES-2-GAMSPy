# solprep_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * SOLPREP.MSA Preprocessing routine for MACRO Stand-Alone
# *============================================================================*
from __future__ import annotations

import logging

from core.cost_ann_rpt import cost_ann_rpt
from core.filparam_gms import filparam_gms
from core.preppm_msa import preppm_msa_label_tonlp
from core.rpt_obj_rpt import rpt_obj_rpt
from core.sol_flo_red import sol_flo_red
from core.sol_ire_rpt import sol_ire_rpt

logger = logging.getLogger(__name__)


def solprep_msa(
    arg1: str,
    arg2: str,
    msa: str,
    v: str,
    pgprim: str,
    sow: str,
    rtp_ffcs_defined: bool,
    stages: str,
    etl: str,
    invlif: str,
    anncost: str,
    sysprefix: str,
    tpulse: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
    is_obj_combal_defined: bool,
    var: str,
    vart: str,
    micro: str,
    is_mi_agc_defined: bool,
    capjd: str,
    capwd: str,
    timesed: str,
    obj: str,
    varcost: str,
    vnret_defined: bool,
    is_tm_catt_defined: bool,
    is_dam_cost_defined: bool,
    cli: str,
    solveda: str,
    scum: str,
    sw_notags: str,
    objann: str,
    mx: str,
    dflbl: str,
    bencost: str,
    discshift: float,
) -> str:
    execution_str: str = ""

    if arg1 in ["", "INIT"]:
        execution_str += _solprep_msa_init(
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
            stages=stages,
            etl=etl,
            invlif=invlif,
            anncost=anncost,
            sysprefix=sysprefix,
            tpulse=tpulse,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            is_obj_combal_defined=is_obj_combal_defined,
            var=var,
            mx=mx,
            vart=vart,
            micro=micro,
            is_mi_agc_defined=is_mi_agc_defined,
            capjd=capjd,
            capwd=capwd,
            timesed=timesed,
            obj=obj,
            bencost=bencost,
            varcost=varcost,
            vnret_defined=vnret_defined,
            is_tm_catt_defined=is_tm_catt_defined,
            is_dam_cost_defined=is_dam_cost_defined,
            cli=cli,
            solveda=solveda,
            scum=scum,
            sw_notags=sw_notags,
            objann=objann,
            dflbl=dflbl,
            discshift=discshift,
        )
        execution_str += _solprep_msa_qsf(arg2=arg2, msa=msa)
    elif arg1 == "QSF":
        execution_str += _solprep_msa_qsf(arg2=arg2, msa=msa)
    elif arg1 == "OUT":
        execution_str += _solprep_msa_out()

    return execution_str


# to clear up the goto logic make individual functions


def _solprep_msa_init(
    v: str,
    pgprim: str,
    sow: str,
    rtp_ffcs_defined: bool,
    stages: str,
    etl: str,
    invlif: str,
    anncost: str,
    sysprefix: str,
    tpulse: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
    is_obj_combal_defined: bool,
    var: str,
    vart: str,
    micro: str,
    is_mi_agc_defined: bool,
    capjd: str,
    capwd: str,
    timesed: str,
    obj: str,
    varcost: str,
    vnret_defined: bool,
    is_tm_catt_defined: bool,
    is_dam_cost_defined: bool,
    cli: str,
    solveda: str,
    scum: str,
    sw_notags: str,
    mx: str,
    objann: str,
    dflbl: str,
    bencost: str,
    discshift: float,
) -> str:
    execution_str = "OPTION CLEAR=PAR_FLO,CLEAR=PAR_IRE;"

    execution_str += sol_flo_red(
        arg1="PAR_FLO",
        arg2="",
        arg3=".L",
        v=v,
        pgprim=pgprim,
        sow=sow,
        rtp_ffcs_defined=rtp_ffcs_defined,
    )

    execution_str += sol_ire_rpt(v=v, sow=sow, mx=mx, rtp_ffcs_defined=rtp_ffcs_defined)

    execution_str += """
*-----------------------------------------------------------------------------
* Calculation of annual costs and commodity marginals
*-----------------------------------------------------------------------------
  OPTION CLEAR=CST_PVP,CLEAR=CST_ACTC,CLEAR=CST_INVC,CLEAR=CST_INVX,CLEAR=CST_FIXC,CLEAR=CST_FIXX;
  OPTION CLEAR=CAP_NEW,CLEAR=CST_FLOC,CLEAR=CST_FLOX,CLEAR=CST_COMC,CLEAR=CST_COMX,CLEAR=CST_IREC;
"""

    execution_str += rpt_obj_rpt(
        arg1="",
        arg2="",
        arg3="",
        arg4=sysprefix,
        arg5="0",
        stages=stages,
        sysprefix=sysprefix,
        etl=etl,
        capjd=capjd,
        capwd=capwd,
        var=var,
        varv=varv,
        varm=varm,
        sws=sws,
        pgprim=pgprim,
        bencost=bencost,
        timesed=timesed,
        obj=obj,
        varcost=varcost,
        discshift=discshift,
        vnret_defined=vnret_defined,
    )

    execution_str += cost_ann_rpt(
        arg1="",
        arg2="",
        stages=stages,
        etl=etl,
        invlif=invlif,
        anncost=anncost,
        sysprefix=sysprefix,
        pgprim=pgprim,
        tpulse=tpulse,
        is_vnret_defined=is_vnret_defined,
        varv=varv,
        sws=sws,
        varm=varm,
        is_obj_combal_defined=is_obj_combal_defined,
        sow=sow,
        var=var,
        vart=vart,
        micro=micro,
        is_mi_agc_defined=is_mi_agc_defined,
    )

    execution_str += """
* Commodity levels and marginals
  OPTION CLEAR=PAR_COMBALEM;
  PAR_COMPRDL(R,T,C,S) $= VAR_COMPRD.L(R,T,C,S);
  PAR_COMNETL(R,T,C,S) $= VAR_COMNET.L(R,T,C,S);
  PAR_COMBALEM(R,T,C,S) $= EQG_COMBAL.M(R,T,C,S)*(1/COEF_PVT(R,T));
  PAR_COMBALEM(R,T,C,S) $= EQE_COMBAL.M(R,T,C,S)*(1/COEF_PVT(R,T));
"""

    execution_str += preppm_msa_label_tonlp(
        is_tm_catt_defined=is_tm_catt_defined,
        is_dam_cost_defined=is_dam_cost_defined,
        cli=cli,
        solveda=solveda,
        stages=stages,
        var=var,
        vart=vart,
        sws=sws,
        sow=sow,
        scum=scum,
        sw_notags=sw_notags,
    )

    execution_str += rf"""
*=============================================================================
* Annual costs for MACRO
  OPTION CLEAR=NCAP_YES,CLEAR=PAR_OBJINV,CLEAR=PAR_OBJFIX;
  NCAP_YES(R,V,P)$(VAR_NCAP.L(R,V,P)+NCAP_PASTI(R,V,P))=YES;
  PAR_OBJINV(RTP_CPTYR(R,V,T,P),CUR)$(NCAP_YES(R,V,P)$COEF_OBINVN(R,V,P,CUR)) = COEF_CPT(R,V,T,P) *
         COEF_OBINVN(R,V,P,CUR) * (VAR_NCAP.L(R,V,P)$T(V)+NCAP_PASTI(R,V,P));
  PAR_OBJFIX(RTP_CPTYR(R,V,T,P),CUR)$(NCAP_YES(R,V,P)$COEF_OBFIXN(R,V,P,CUR)) = COEF_CPT(R,V,T,P) *
         COEF_OBFIXN(R,V,P,CUR) * (VAR_NCAP.L(R,V,P)$T(V)+NCAP_PASTI(R,V,P));
{"MACST('VAR')=NO; VAR_ANNCST.UP('OBJVAR',R,T,CUR)=INF;" if objann.upper() == "YES" else ""}
  TM_ANNC(MR(R),T) = SUM(MACST$REG_ACOST(R,T,MACST),REG_ACOST(R,T,MACST)) +
     SUM((VNT(V,T),P,RDCUR(R,CUR))$PAR_OBJINV(R,V,T,P,CUR),PAR_OBJINV(R,V,T,P,CUR)) +
     SUM((VNT(V,T),P,RDCUR(R,CUR))$PAR_OBJFIX(R,V,T,P,CUR),PAR_OBJFIX(R,V,T,P,CUR));
{"TM_ANNC(R,T) = TM_ANNC(R,T)+SUM(RDCUR(R,CUR),VAR_ANNCST.L('OBJVAR',R,T,CUR));" if objann.upper() == "YES" else ""}
*-----------------------------------------------------------------------------
* Marginal costs of demands
  OPTION CLEAR=TM_DMC;
  TM_DMC(RTC(MR(R),T,C))$DEM(R,C) = SUM(RTCS_VARC(R,T,C,S),PAR_COMBALEM(R,T,C,S) * G_YRFR(R,S));
  TM_DMC(R,T,C)$(TM_DMC(R,T,C) EQ 0) = 0;
  LOOP(MIYR_1(TT(T-1)),TM_DMC(R,TT,C)$((TM_DMC(R,TT,C) GT TM_DMC(R,T,C))$DEM(R,C)) = TM_DMC(R,T,C));
"""
    execution_str += filparam_gms(
        arg1="TM_DMC",
        arg2="R,",
        arg3="C",
        arg4=",'0','0','0','0','0'",
        arg5="DATAYEAR",
        arg6="T",
        arg7="",
        arg8="",
        arg9="",
        arg10="",
        dflbl=dflbl,
    )

    execution_str += """
  LOOP(MIYR_1(TT(T-1)),TM_DMC(R,TT,C)$((TM_DMC(R,TT,C) LT TM_DMC(R,T,C)*0.7)$DEM(R,C)) = TM_DMC(R,T,C)*0.7);
* Demand levels
  TM_DEM(MR(R),T,C)$((COM_PROJ(R,T,C) GT 0)$DEM(R,C)) = COM_PROJ(R,T,C)
     - SUM((RTCS_VARC(R,T,C,S),RCJ(R,C,J,'LO')), VAR_ELAST.L(R,T,C,S,J,'LO'))
     + SUM((RTCS_VARC(R,T,C,S),RCJ(R,C,J,'UP')), VAR_ELAST.L(R,T,C,S,J,'UP'));
"""
    return execution_str


def _solprep_msa_qsf(arg2: str, msa: str) -> str:
    return rf"""
* Quadratic supply function
  OPTION DM < TM_DEM;
  TM_DMC(MR,TB,DM)$(TM_DMC(MR,TB,DM)*TM_DEM(MR,TB,DM) < 1E-5*TM_ANNC(MR,TB)) = 0;
  TM_ANNC(REG,TP)=TM_ANNC(REG,TP) * TM_SCALE_CST;
  LOOP(TB(T-1), TM_ANNC(REG,TB) = MIN(TM_ANNC(REG,T),TM_ANNC(REG,TB));
{"TM_EC0(REG) = TM_ANNC(REG,TB); TM_DDATPREF(REG,DM) = TM_DMC(REG,TB,DM); " if f"{msa}{arg2}".upper() == "CSA0" else ""}
   TM_ANNC(REG,TB) = TM_EC0(REG); TM_DMC(REG,TB,DM) = TM_DDATPREF(REG,DM));
  TM_QSFB(REG,TP,DM)$TM_DEM(REG,TP,DM) = 0.5*TM_DMC(REG,TP,DM)*TM_SCALE_CST/TM_DEM(REG,TP,DM);
  TM_QSFA(REG,TP)=TM_ANNC(REG,TP)- SUM(DM, TM_QSFB(REG,TP,DM)*TM_DEM(REG,TP,DM)**2);
"""


def _solprep_msa_out() -> str:
    return """
* Write data transfer attributes to file
  FILE TIM2MSA / MSAQSF.DD /;
*
  PUT TIM2MSA;
  PUT "$ONMULTI" /;
* Milestones
  PUT "SET T /" /;
  LOOP(T, PUT T.TL /;);
  PUT "/;" /;
* Lagtimes
  PUT "PARAMETER LAGT /" /;
  LOOP(T, PUT T.TL, LAGT(T) /;);
  PUT "/;" /;
* Durations
  PUT "PARAMETER D /" /;
  LOOP(T, PUT T.TL, D(T) /;);
  PUT "/;" /;
* Regions
  PUT "SET REG /" /;
  LOOP(MR(R), PUT R.TL /;);
  PUT "/;" /;
* Commodities
  PUT "SET COM /" /;
  LOOP(DM(C), PUT C.TL /;);
  PUT "/;" /;
*
  TIM2MSA.nr = 2;
  TIM2MSA.nd = 9;
  TIM2MSA.nw = 17;
  TIM2MSA.nz = 1e-9;
* Annual regional costs
  PUT "PARAMETER TM_ANNC /" /;
  LOOP((MR(R),T), PUT R.TL:0,".":0,T.TL:0 (TM_ANNC(R,T)/TM_SCALE_CST) /;);
  PUT "/;" /;
* GDP target
  PUT "PARAMETER TM_GR /" /;
  LOOP((MR(R),T), PUT R.TL:0,".":0,T.TL:0 TM_GR(R,T) /;);
  PUT "/;" /;
* Demand levels
  PUT "PARAMETER TM_DEM /" /;
  LOOP(MRTC(MR(R),T,C),PUT MRTC.TE(MRTC), TM_DEM(MRTC) /;);
  PUT "/;" /;
* Demand marginals
  PUT "PARAMETER TM_DMC /" /;
  LOOP(MRTC(MR(R),T,C)$TM_DMC(MRTC), PUT MRTC.TE(MRTC), TM_DMC(MRTC) /;);
  PUT "/;" /;
  PUT 'SCALAR TM_ARBM'       @25 '/' TM_ARBM ' /;' /;
  PUT 'SCALAR TM_SCALE_UTIL' @25 '/' TM_SCALE_UTIL ' /;' /;
  PUT 'SCALAR TM_SCALE_CST'  @25 '/' TM_SCALE_CST ' /;' /;
  PUT 'SCALAR TM_SCALE_NRG'  @25 '/' TM_SCALE_NRG ' /;' /;
  PUT / 'PARAMETER  TM_KGDP(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_KGDP(R) / @1 '/;');
  PUT / 'PARAMETER TM_KPVS(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_KPVS(R) / @1 '/;');
  PUT / 'PARAMETER TM_DEPR(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_DEPR(R) / @1 '/;');
  PUT / 'PARAMETER TM_ESUB(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_ESUB(R) / @1 '/;');
  PUT / 'PARAMETER TM_GDP0(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_GDP0(R) / @1 '/;');
  PUT / 'PARAMETER TM_DMTOL(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_DMTOL(R) / @1 '/;');
  PUT / 'PARAMETER TM_IVETOL(R)' @25 '/' /;
  LOOP(MR(R), PUT @1 R.TL:0, TM_IVETOL(R) / @1 '/;');
  PUTCLOSE TIM2MSA;
"""
