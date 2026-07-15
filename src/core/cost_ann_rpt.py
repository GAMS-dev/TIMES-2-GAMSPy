# cost_ann_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COST_ANN: annual cost calculation
# *   - Investment Costs, Tax/Subsidies
# *   - Decommissioning
# *   - Fixed costs and taxes
# *   - Variable costs and Taxes/Subsidies
# *-----------------------------------------------------------------------------
# *  arg1 - Prefix for parameter names (optional)
# *  arg2 - SOW, (optional)
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.eqobjels_rpt import eqobjels_rpt
from core.eqobjvar_rpt import eqobjvar_rpt
from core.powerflo_vda import powerflo_vda_rptb
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CostAnnRpt(GamsClass):
    """Translation unit for cost_ann.rpt."""

    # Instance attributes
    module_name: str = "cost_ann_rpt"
    gams_source: str = "cost_ann.rpt"

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
        self.tc.enqueue(
            self.exec1,
            arg1=self.arg1,
            arg2=self.arg2,
            stages=self.env.stages,
            etl=self.env.etl,
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            sysprefix=self.env.sysprefix,
            pgprim=self.env.pgprim,
            tpulse=self.env.tpulse,
            is_vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv,
            sws=self.env.sws,
            varm=self.env.varm,
            is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            sow=self.env.sow,
            var=self.env.var,
            vart=self.env.vart,
            micro=self.env.micro,
            is_mi_agc_defined=self.tc.defined("MI_AGC"),
        )

    def exec1(
        self: CostAnnRpt,
        arg1: str,
        arg2: str,
        stages: str,
        etl: str,
        invlif: str,
        anncost: str,
        sysprefix: str,
        pgprim: str,
        tpulse: str,
        is_vnret_defined: bool,
        varv: str,
        sws: str,
        varm: str,
        is_obj_combal_defined: bool,
        sow: str,
        var: str,
        vart: str,
        micro: str,
        is_mi_agc_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=cost_ann_rpt(
                arg1=arg1,
                arg2=arg2,
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
            ),
        )


def cost_ann_rpt(
    arg1: str,
    arg2: str,
    stages: str,
    etl: str,
    invlif: str,
    anncost: str,
    sysprefix: str,
    pgprim: str,
    tpulse: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
    is_obj_combal_defined: bool,
    sow: str,
    var: str,
    vart: str,
    micro: str,
    is_mi_agc_defined: bool,
) -> str:
    return_str = rf"""
  OBJ_YES(NCAP_YES)=YES;
  OPTION CLEAR=COEF_CAP; CNT=1$ROUND(RPT_OPT('OBJ','2'));
  COEF_CAP(RTP_CPTYR(R,V,T,P))$(NCAP_YES(R,V,P)$PRC_RCAP(R,P)) = VAR_SCAP.L(R,V,T,P)/RTP_CAPVL(R,V,P);
* Levelized annual investment and fixed costs
  IF(CNT, OPTION CLEAR=PAR_OBJCAP;
    PAR_OBJCAP(OBJ_ICUR(NCAP_YES(R,V,P),CUR)) = SUM(RTP_CPTYR(R,V,T,P),COEF_CPT(R,V,T,P)*OBJ_PVT(R,T,CUR));
    RTP_OBJ(J,R,V,P,CUR)$RTP_OBJ(J,R,V,P,CUR) = (RTP_OBJ(J,R,V,P,CUR)/PAR_OBJCAP(R,V,P,CUR))$PAR_OBJCAP(R,V,P,CUR);
    {arg1}CST_INVC({arg2}RTP_CPTYR(R,V,T,P),SYSINV)$NCAP_YES(R,V,P) =
       SUM(RDCUR(R,CUR),RTP_OBJ('1',R,V,P,CUR)*COEF_CPT(R,V,T,P)*ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)));
    {arg1}CST_INVX({arg2}RTP_CPTYR(R,V,T,P),SYSINV)$NCAP_YES(R,V,P) =
       SUM(RDCUR(R,CUR),RTP_OBJ('2',R,V,P,CUR)*COEF_CPT(R,V,T,P)*ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)));
  IF(ACL,
    PAR_OBJCAP(OBJ_FCUR(NCAP_YES(R,V,P),CUR)) = SUM(RTP_CPTYR(R,V,T,P),COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P))*OBJ_PVT(R,T,CUR));
    RTP_NPV(J,R,V,P,CUR)$RTP_NPV(J,R,V,P,CUR) = (RTP_NPV(J,R,V,P,CUR)/PAR_OBJCAP(R,V,P,CUR))$PAR_OBJCAP(R,V,P,CUR);
    {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P))$NCAP_YES(R,V,P) = SUM(RDCUR(R,CUR),RTP_NPV('1',R,V,P,CUR)*COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P)));
    {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P))$NCAP_YES(R,V,P) = SUM(RDCUR(R,CUR),RTP_NPV('2',R,V,P,CUR)*COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P)));
    OPTION CLEAR=COEF_CAP);
    OPTION CLEAR=NCAP_YES;
  );
*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------
* Calculate Annual undiscounted investment costs CST_INVC
"""
    tmp = ""
    x1 = ""
    sic = "1"

    if stages.upper() == "YES":
        return_str += (
            "PASTSUM(NCAP_YES(R,T,P)) = SUM(SW_TSW(SOW,T,WW),OBJ_SIC(R,T,P,WW));"
        )
        sic = "1+PASTSUM(R,V,P)"

    return_str += rf"""
OPTION CLEAR=FIL,COEF_RVPT<=COEF_CPT; IF(NOT CNT,NCAP_YES(R,PYR_S,P)$PRC_RESID(R,'0',P)=NO);

LOOP(OBJ_ICUR(NCAP_YES(R,V,P),CUR), OPTION CLEAR=YKK; MY_F={sic};
  SYSPLIT(SYSINV)=ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR));
  F = RTP_CAPVL(R,V,P)*OBJ_CRF(R,V,P,CUR)/OBJ_DIVI(R,V,P);
  LOOP(OBJ_SUMII(R,V,P,LIFE,K_EOH,JOT), Z=ORD(LIFE); FIL(T)=VNT(V,T)$(M(T)<YEARVAL(K_EOH)+ORD(JOT)+Z);
    YKK(YK(FIL(YEAR),LL),K)$((ORD(YEAR) < ORD(LL)+Z)$INVSPRED(K_EOH,JOT,LL,K)) = YES);
  CSTVPJ(R,V,P,'1',SYSINV,T(FIL)) = SUM(YKK(T,LL,K), F * MY_F * {
        macro.obj_icost("R", "K", "P", "CUR")
    })*SYSPLIT(SYSINV);
  CSTVPJ(R,V,P,'2',SYSINV,T(FIL))$({macro.obj_itax("R", "V", "P", "CUR")}+{
        macro.obj_isub("R", "V", "P", "CUR")
    }) =
       SUM(YKK(T,LL,K), F * ({macro.obj_itax("R", "K", "P", "CUR")}-{
        macro.obj_isub("R", "K", "P", "CUR")
    }))*SYSPLIT(SYSINV);
);

 IF(NOT CNT, FIL(V)=PYR_S(V); OPTION CSTVNT < CSTVPJ, CLEAR=CSTVPJ);
 {arg1}CST_INVC({arg2}R,V,T,P,SYSINV) $= CSTVNT('1',R,V,T,P,SYSINV);
 {arg1}CST_INVX({arg2}R,V,T,P,SYSINV) $= CSTVNT('2',R,V,T,P,SYSINV);

* Report approximate costs for RESID according to available capacity
LOOP(OBJ_ICUR(R,FIL(V),P,CUR)$PRC_RESID(R,'0',P),
 FIL2(T)=(NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T)-RTFORC(R,V,T,P))*OBJ_CRF(R,V,P,CUR);
 {arg1}CST_INVC({
        arg2
    }RTP_CPTYR(R,V,T,P),SYSINV) = ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)) * FIL2(T) * {
        macro.obj_icost("R", "V", "P", "CUR")
    };
 {arg1}CST_INVX({
        arg2
    }RTP_CPTYR(R,V,T,P),SYSINV) = ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)) * FIL2(T) * ({
        macro.obj_itax("R", "V", "P", "CUR")
    }-{macro.obj_isub("R", "V", "P", "CUR")});
);

* Handle ETL
{
        ""
        if etl != "YES"
        else (
            f'''
LOOP(OBJ_ICUR(R,T,TEG(P),CUR)$VAR_IC.L(R,T,P), OPTION CLEAR=YKK;
  F = VAR_IC.L(R,T,P) * OBJ_CRF(R,T,P,CUR)/OBJ_DIVI(R,T,P);
  LOOP((OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT),INVSPRED(K_EOH,JOT,LL,K)),
    Z=ORD(LIFE); YKK(YK(TT,LL),K)$(YEARVAL(TT) < YEARVAL(LL)+Z) = YES);
  {arg1}CST_INVC({arg2}R,VNT(T,TT),P,SYSINV)$SYSONE(SYSINV) = {arg1}CST_INVC({arg2}R,T,TT,P,SYSINV)+SUM(YKK(TT,LL,K),F);
);
'''
        )
    }

*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------
OPTION OBJ_SUMSI <= OBJ_SUMIII;
* Calculate decommissioning costs, annualized to operating years:
LOOP(OBJ_ICUR(NCAP_YES(R,V,P),CUR)${
        macro.obj_dcost("R", "V", "P", "CUR")
    }, F = RTP_CAPVL(R,V,P);
  F = F*OBJ_CRF(R,V,P,CUR)/OBJ_DIVIII(R,V,P); Z = ROUND(NCAP_{invlif}(R,V,P));
  {arg1}CST_DECC({
        arg2
    }R,VNT(V,T),P) = SUM(OBJ_SUMSI(R,V,P,LL)$((YEARVAL(T) < YEARVAL(LL)+Z)$YK(T,LL)),
      (SUM(OBJ_SUMIII(R,V,P,LL,K,Y),OBJ_DISC(R,Y,CUR)*{
        macro.obj_dcost("R", "K", "P", "CUR")
    })*COR_SALVD(R,V,P,CUR) +
       SUM(OBJ_SUMIVS(R,V,P,K(LL),Y),OBJ_DISC(R,Y,CUR))*{
        macro.obj_dlagc("R", "LL", "P", "CUR")
    })*F/OBJ_DISC(R,LL,CUR));
);

*------------------------------------------------------------------------------
* Cases IV - Fixed costs
*------------------------------------------------------------------------------
 IF(NOT ACL,OPTION CLEAR=FIL2,CLEAR=MY_FIL2;
   IF(CNT,NCAP_YES(OBJ_YES)=YES; NCAP_YES(R,PYR_S,P)$PRC_RESID(R,'0',P)=NO; FIL(PYR_S)=1;
   ELSE COEF_RVPT(NCAP_YES(RTP),T)$COEF_RVPT(RTP,T) = (1+RTP_CPX(RTP,T)$NCAP_CPX(RTP))/MAX(1,OBJ_DIVIV(RTP))));
 LOOP(OBJ_FCUR(NCAP_YES(R,V,P),CUR), F = RTP_CAPVL(R,V,P);
   OPTION CLEAR=YKAGE; MY_FIL2(T)=COEF_RVPT(R,V,P,T); MY_F = B(V)+NCAP_ILED(R,V,P);
   LOOP(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE), Z=ORD(LIFE)-1;
     FIL2(T(YEAR))=ORD(YEAR)+(MAX(0,MY_F-M(T))-MAX(0,M(T)-MY_F-Z))$CNT;
     YKAGE(T,LL,AGE(LIFE+(FIL2(T)-ORD(LL)-Z)))$(INVSTEP(K_EOH,JOT,LL,JOT)$OPYEAR(LIFE,AGE)$MY_FIL2(T)) = YES);
   FIL2(T)=F*MY_FIL2(T)/MAX(1,SUM(YKAGE(T,LL,AGE),1)$CNT);
   CSTVPJ(R,V,P,'1','FIX',T) = FIL2(T) *
     SUM(YKAGE(T,K,AGE), {
        macro.obj_fom("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1)));
   CSTVPJ(R,V,P,'2','FIX',T)$({macro.obj_ftx("R", "V", "P", "CUR")}+{
        macro.obj_fsb("R", "V", "P", "CUR")
    }) = FIL2(T) *
     SUM(YKAGE(T,K,AGE), ({
        macro.obj_ftx("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1)) -
                          {
        macro.obj_fsb("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1))));
 );
 OPTION CSTVNT < CSTVPJ, CLEAR=CSTVPJ;
 {arg1}CST_FIXC({arg2}R,V,T,P) $= CSTVNT('1',R,V,T,P,'FIX');
 {arg1}CST_FIXX({arg2}R,V,T,P) $= CSTVNT('2',R,V,T,P,'FIX');

* Report approximate costs for RESID according to available capacity
LOOP(OBJ_FCUR(R,FIL(V),P,CUR)$PRC_RESID(R,'0',P),
 {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P)) = NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T) * {
        macro.obj_fom("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),MULTI(JJ,T)-1));
 {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P)) = NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T) *({
        macro.obj_ftx("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),MULTI(JJ,T)-1)) -
                                                                          {
        macro.obj_fsb("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),MULTI(JJ,T)-1)));
);

 IF(CARD(PRC_RCAP),
  COEF_CAP(RTP_CPTYR(R,V,T,P))$COEF_CAP(R,V,T,P) = 1-COEF_CAP(R,V,T,P)+EPS;
  {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P)) $= COEF_CAP(R,V,T,P)*{arg1}CST_FIXC({
        arg2
    }R,V,T,P);
  {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P)) $= COEF_CAP(R,V,T,P)*{arg1}CST_FIXX({
        arg2
    }R,V,T,P);
 );
 NCAP_YES(OBJ_YES)=YES;

*-----------------------------------------------------------------------------
* Marginal costs of endogenous trade
*-----------------------------------------------------------------------------
  OPTION CLEAR=OBJ_YES,CLEAR=CSTVNT,CLEAR=PAR_IPRIC;
  PAR_IPRIC(RTP(R,T,P),C,TS,'IMP') $= (-1) * EQ_IRE.M(R,T,P,C,'IMP',TS);
  CG_GRP(R,P,C,COM)$TOP_IRE(R,C,R,COM,P) = YES;
  LOOP(CG_GRP(REG,P,COM1,COM)$RPC_MARKET(REG,P,COM,'IMP'),
    PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'IMP')$TOP_IRE(REG,COM1,R,C,P) =
      -SUM((RS_TREE(R,ALL_TS,TS),S)$(IRE_TSCVT(R,ALL_TS,REG,S)$EQ_IRE.M(REG,T,P,COM,'IMP',S)),
               EQ_IRE.M(REG,T,P,COM,'IMP',S) *
               IRE_CCVT(REG,COM1,REG,COM) * IRE_CCVT(R,C,REG,COM1) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S)));

  PAR_XPRI(RTPCS_VARF(R,T,P,C,TS),REG,COM)$(TOP_IRE(R,C,REG,COM,P)$RPC_IREIO(R,P,C,'EXP','IN')) =
    SUM((RS_TREE(R,TS,ALL_TS),S)$(IRE_TSCVT(R,ALL_TS,REG,S)$EQ_IRE.M(REG,T,P,COM,'IMP',S)),
              EQ_IRE.M(REG,T,P,COM,'IMP',S) * IRE_FLO(R,T,P,C,REG,COM,S) *
              IRE_CCVT(R,C,REG,COM) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S));
  PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'EXP')$RPC_IREIO(R,P,C,'EXP','IN') $= SMAX(TOP_IRE(R,C,REG,COM,P),PAR_XPRI(R,T,P,C,TS,REG,COM));

  PAR_IPRIC(RTP(R,T,P),C,TS,'EXP') $= EQ_IRE.M(R,T,P,C,'EXP',TS);
  LOOP(RPC_EQIRE(REG,P,COM,'EXP'),
    PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'IMP')$TOP_IRE(REG,COM,R,C,P) =
      -SUM((RS_TREE(R,ALL_TS,TS),S)$IRE_TSCVT(R,ALL_TS,REG,S),
               EQ_IRE.M(REG,T,P,COM,'EXP',S) / IRE_FLO(REG,T,P,COM,R,C,TS) *
               IRE_CCVT(R,C,REG,COM) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S)));

  PRC_YMAX(RP_IRE(R,P)) $= SUM((RPC_IREIO(R,P,C,IE,'IN'),RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,S)),
                                PAR_IPRIC(R,T,P,C,S,IE)*PAR_IRE(R,V,T,P,C,S,IE));
  {arg1}REG_IREC({arg2}R) $= SUM(P,PRC_YMAX(R,P));
  PAR_IPRIC(R,T,P,C,TS,IE)$PAR_IPRIC(R,T,P,C,TS,IE) = PAR_IPRIC(R,T,P,C,TS,IE)*(1/COEF_PVT(R,T));
{
        f"{arg1}PAR_IPRIC({arg2}R,T,P,C,TS,IE) $= PAR_IPRIC(R,T,P,C,TS,IE);"
        if arg1 == "S"
        else ""
    }
  OPTION CLEAR=CG_GRP,CLEAR=PAR_OBJCAP,CLEAR=PAR_XPRI,CLEAR=RTP_OBJ,CLEAR=RTP_NPV,CLEAR=COEF_CRF,CLEAR=COEF_RVPT;

*------------------------------------------------------------------------------
* Marginal costs associated with endogenous imports/exports
* - note that price only applied when actually an internal region
*------------------------------------------------------------------------------
  {arg1}CST_IREC({arg2}RTP_VINTYR(R,V,T,P),C)$(RPC(R,P,C)$RP_IRE(R,P)) $=
     SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'IN')),PAR_IPRIC(R,T,P,C,S,IE)*PAR_IRE(R,V,T,P,C,S,IE));
*------------------------------------------------------------------------------
* EQOBJVAR the objective function variable cost reporting
*------------------------------------------------------------------------------
"""

    if anncost.upper() == "LEV":
        x1 = "LEV"
        tmp = "*(1/OBJ_PVT(R,T,CUR))"

    return_str += rf"""
{arg1}CST_TIME({arg2}R,T,ANNUAL,'{sysprefix}{x1}COST') = COEF_PVT(R,T);
"""

    if anncost.upper() != "LEV":
        return_str += eqobjvar_rpt(
            arg1="PAR",
            arg2="J('1'),",
            arg3="J('2'),",
            arg4="T",
            arg5="",
            pgprim=pgprim,
            tpulse=tpulse,
            tmp=tmp,
            stages=stages,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )

    return_str += rf"""
  {arg1}CST_ACTC({arg2}R,V,T,P,'-') $= SUM(CUR$PAR_ACTC('1',R,V,T,P,'{pgprim}',CUR),PAR_ACTC('1',R,V,T,P,'{pgprim}',CUR){tmp});
  {arg1}CST_ACTC({arg2}R,V,T,P,'+') $= SUM(CUR$PAR_ACTC('2',R,V,T,P,'{pgprim}',CUR),PAR_ACTC('2',R,V,T,P,'{pgprim}',CUR){tmp});
  {arg1}CST_FLOC({arg2}R,V,T,P,C) $= SUM(CUR$PAR_FLOC('1',R,V,T,P,C,CUR),PAR_FLOC('1',R,V,T,P,C,CUR){tmp});
  {arg1}CST_FLOX({arg2}R,V,T,P,C) $= SUM(CUR$PAR_FLOC('2',R,V,T,P,C,CUR),PAR_FLOC('2',R,V,T,P,C,CUR){tmp});
  {arg1}CST_COMC({arg2}R,T,C)     $= SUM(CUR$PAR_COMC('1',R,T,C,CUR),PAR_COMC('1',R,T,C,CUR){tmp});
  {arg1}CST_COMX({arg2}R,T,C)     $= SUM(CUR$PAR_COMC('2',R,T,C,CUR),PAR_COMC('2',R,T,C,CUR){tmp});
"""
    if is_obj_combal_defined:
        return_str += powerflo_vda_rptb(
            arg4=arg1,
            arg5=arg2,
            arg6=sow,
            var=var,
            vart=vart,
            sws=sws,
        )
    # *------------------------------------------------------------------------------
    # * EQOBJELS the objective function flexible demand cost reporting
    # *------------------------------------------------------------------------------
    return_str += eqobjels_rpt(
        arg1=f"{arg1}CST_COME({arg2}R,TT,C)",
        arg2="TT",
        arg3="",
        micro=micro,
        if_mi_agc_defined=is_mi_agc_defined,
    )

    return_str += rf"""
  IF(CARD({arg1}CST_PVP),
   {arg1}CST_PVC({arg2}'{sysprefix}ELS',R,C)$SUM(RCJ(R,C,'1',BDNEQ),1) = SUM(T,{
        arg1
    }CST_COME({arg2}R,T,C)*COEF_PVT(R,T));
   {arg1}CST_PVP({arg2}'{sysprefix}IRE',RP_IRE(RP)) $= PRC_YMAX(RP);
  );
*------------------------------------------------------------------------------
* Regional annual costs
  {arg1}REG_ACOST({arg2}R,T,'INV') =  SUM((VNT(V,T),P,SYSINV)${arg1}CST_INVC({
        arg2
    }R,V,T,P,SYSINV),{arg1}CST_INVC({arg2}R,V,T,P,SYSINV));
  {arg1}REG_ACOST({arg2}R,T,'INVX') = SUM((VNT(V,T),P,SYSINV)${arg1}CST_INVX({
        arg2
    }R,V,T,P,SYSINV),{arg1}CST_INVX({arg2}R,V,T,P,SYSINV));
  {arg1}REG_ACOST({arg2}R,T,'FIX') =  SUM((VNT(V,T),P)${arg1}CST_FIXC({arg2}R,V,T,P),{
        arg1
    }CST_FIXC({arg2}R,V,T,P));
  {arg1}REG_ACOST({arg2}R,T,'FIXX') = SUM((VNT(V,T),P)${arg1}CST_FIXX({arg2}R,V,T,P),{
        arg1
    }CST_FIXX({arg2}R,V,T,P));
  {arg1}REG_ACOST({arg2}R,T,'VAR') =  SUM((VNT(V,T),P,RPM)${arg1}CST_ACTC({
        arg2
    }R,V,T,P,RPM),{arg1}CST_ACTC({arg2}R,V,T,P,RPM)) +
                              SUM((VNT(V,T),P,C)${arg1}CST_FLOC({arg2}R,V,T,P,C),{
        arg1
    }CST_FLOC({arg2}R,V,T,P,C)) +
                              SUM(C${arg1}CST_COMC({arg2}R,T,C),{arg1}CST_COMC({
        arg2
    }R,T,C));
  {arg1}REG_ACOST({arg2}R,T,'VARX') = SUM((VNT(V,T),P,C)${arg1}CST_FLOX({
        arg2
    }R,V,T,P,C),{arg1}CST_FLOX({arg2}R,V,T,P,C)) +
                              SUM(C${arg1}CST_COMX({arg2}R,T,C),{arg1}CST_COMX({
        arg2
    }R,T,C));
  {arg1}REG_ACOST({arg2}R,T,'IRE') =  SUM((VNT(V,T),P,C)${arg1}CST_IREC({
        arg2
    }R,V,T,P,C),{arg1}CST_IREC({arg2}R,V,T,P,C));
  {arg1}REG_ACOST({arg2}R,T,'ELS') =  SUM(C${arg1}CST_COME({arg2}R,T,C),{arg1}CST_COME({
        arg2
    }R,T,C));
*------------------------------------------------------------------------------
  OPTION CLEAR=PAR_ACTC,CLEAR=PAR_COMC,CLEAR=PAR_FLOC,CLEAR=PRC_YMAX,CLEAR=PASTSUM;
{
        ""
        if arg1 == "S"
        else (
            f'''
*------------------------------------------------------------------------------
* Salvage costs (not for stochastic runs)
*------------------------------------------------------------------------------
* Calculate actual Salvage values
  PAR_OBJSAL(OBJ_ICUR(R,T,P,CUR)) = PAR_OBJSAL(R,T,P,CUR)*VAR_NCAP.L(R,T,P);
  {"PAR_OBJSAL(RTP(R,T,TEG(P)),CUR)$G_RCUR(R,CUR) = PAR_OBJSAL(RTP,CUR)+SUM(OBJ_SUMS(RTP),OBJSIC(RTP)*VAR_IC.L(RTP))*OBJ_DCEOH(R,CUR);" if etl == "YES" else ""}
  {arg1}CST_SALV({arg2}R,T,P) $= SUM(RDCUR(R,CUR),PAR_OBJSAL(R,T,P,CUR));
  REG_OBJ(R) = SUM((RDCUR(R,CUR),ITEM,OBV)$SUM_OBJ(ITEM,OBV),VAR_OBJ.L(R,OBV,CUR)*SUM_OBJ(ITEM,OBV));
'''
        )
    }
"""
    return return_str
