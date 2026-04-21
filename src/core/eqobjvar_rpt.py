# eqobjvar_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJVAR - the variable O&M, flow and commodity direct costs
# *  arg1 - mod or prefix
# *  arg2 - '1', or J(UNCD1),
# *  arg3 - '2', or J(UNCD1),
# *  arg4 - T OR Y_EOH
# *  arg5 - SUM or ''

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cal_caps_mod import cal_caps_mod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjvarRpt(GamsClass):
    """Translation unit for eqobjvar.rpt."""

    # Instance attributes
    module_name: str = "eqobjvar_rpt"
    gams_source: str = "eqobjvar.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.compile()

    def compile(self) -> None:
        if not self.arg1.upper() == "MOD":
            if self.arg5.upper() == "":
                self.env.set_scoped("tpulse", "")
                self.env.set_scoped("tmp", "")

            self.tc.enqueue(
                self.exec1,
                arg1=self.arg1,
                arg2=self.arg2,
                arg3=self.arg3,
                arg4=self.arg4,
                arg5=self.arg5,
                pgprim=self.env.pgprim,
                tpulse=self.env.tpulse,
                tmp=self.env.tmp,
                condition=self.env.stages.upper() == "YES",
                is_vnret_defined=self.tc.defined("VNRET"),
                varv=self.env.varv,
                sws=self.env.sws,
                varm=self.env.varm,
            )
        else:  # LEGACY
            self.tc.enqueue(
                self.execute_legacy_behavior,
                is_vnret_defined=self.tc.defined("VNRET"),
                varv=self.env.varv,
                sws=self.env.sws,
                varm=self.env.varm,
            )

    def exec1(
        self: EqobjvarRpt,
        arg1: str,
        arg2: str,
        arg3: str,
        arg4: str,
        arg5: str,
        pgprim: str,
        tpulse: str,
        tmp: str,
        condition: bool,
        is_vnret_defined: bool,
        varv: str,
        sws: str,
        varm: str,
    ):
        include_cal_caps_1 = cal_caps_mod(
            is_vnret_defined=is_vnret_defined,
            arg1="T",
            arg2=f"SUM(TS_ANN(TS,SL),{arg5}({tpulse}(OBJ_FCOST(R,{arg4},P,C,SL,CUR)+OBJ_FDELV(R,{arg4},P,C,SL,CUR))))",
            arg3="TS",
            arg4=".L",
            varv=varv,
            sws=sws,
            varm=varm,
        )
        include_cal_caps_2 = cal_caps_mod(
            is_vnret_defined=is_vnret_defined,
            arg1="T",
            arg2=f"SUM(TS_ANN(TS,SL),{arg5}({tpulse} OBJ_FTAX(R,{arg4},P,C,SL,CUR)))",
            arg3="TS",
            arg4=".L",
            varv=varv,
            sws=sws,
            varm=varm,
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{"Z=SUM(W(SOW),SW_PROB(W));" if condition else ""}
*------------------------------------------------------------------------------
  OPTION CLEAR={arg1}_ACTC,CLEAR={arg1}_COMC,CLEAR={arg1}_FLOC;
*------------------------------------------------------------------------------
* Costs based on overall activity of process
*------------------------------------------------------------------------------

  {arg1}_ACTC({arg2}RTP_VINTYR(R,V,T,P),{pgprim},CUR)$(RDCUR(R,CUR)$OBJ_ACOST(R,T,P,CUR)) =
      {arg5}({tpulse} OBJ_ACOST(R,{arg4},P,CUR)) *
      SUM(PRC_TS(R,P,S), VAR_ACT.L(R,V,T,P,S) * POWER(RS_STGAV(R,S),1$RP_STG(R,P)));
  {arg1}_ACTC({arg3}RTP_VINTYR(R,V,T,P),C({pgprim}),CUR)$RPC_CUR(R,P,C,CUR) =
      SUM(RP_UPS(R,P,TSL,L('UP')),{arg5}({tpulse} ACT_CSTUP(R,V,P,TSL,CUR))*SUM(TS_GROUP(R,TSL,S),RS_STGPRD(R,S)*VAR_UPS.L(R,V,T,P,S,L))) +
      SUM(RP_UPT(R,P,UPT,'UP'),{arg5}({tpulse} ACT_CSTSD(R,V,P,UPT,'FX',CUR)*SUM(TS_GROUP(R,TSL,S)$RP_DPL(R,P,TSL),RS_STGPRD(R,S)*VAR_UPT.L(R,V,T,P,S,UPT)))) +
      SUM(RP_UPR(R,P,BDNEQ(BD)),{arg5}({tpulse} ACT_CSTRMP(R,V,P,BD,CUR))*SUM(PRC_TS(R,P,S),RS_STGPRD(R,S)*VAR_UDP.L(R,V,T,P,S,BD)));

*------------------------------------------------------------------------------
* Commodity added costs and sub/tax
*------------------------------------------------------------------------------
  {arg1}_COMC({arg2}R,T,C,CUR)$RDCUR(R,CUR) $=
        SUM(RHS_COMBAL(R,T,C,S), VAR_COMNET.L(R,T,C,S) * {arg5}({tpulse} OBJ_COMNT(R,{arg4},C,S,'COST',CUR))) +
        SUM(RHS_COMPRD(R,T,C,S), VAR_COMPRD.L(R,T,C,S) * {arg5}({tpulse} OBJ_COMPD(R,{arg4},C,S,'COST',CUR)));
  {arg1}_COMC({arg3}R,T,C,CUR)$RDCUR(R,CUR) $=
        SUM(RHS_COMBAL(R,T,C,S), VAR_COMNET.L(R,T,C,S) * {arg5}({tpulse} (OBJ_COMNT(R,{arg4},C,S,'TAX',CUR)+OBJ_COMNT(R,{arg4},C,S,'SUB',CUR)))) +
        SUM(RHS_COMPRD(R,T,C,S), VAR_COMPRD.L(R,T,C,S) * {arg5}({tpulse} (OBJ_COMPD(R,{arg4},C,S,'TAX',CUR)+OBJ_COMPD(R,{arg4},C,S,'SUB',CUR))));
{f"{arg1}_COMC({arg3}RTC(R,T,C),CUR)$RDCUR(R,CUR) $= SUM((RTCS_VARC(RTC,S),COM_VAR,SW_TSW(SOW,T,W))$S_COM_TAX(RTC,S,COM_VAR,CUR,'1',W),({arg5}({tmp}S_COM_TAX(R,{arg4},C,S,COM_VAR,CUR,'1',W))*(VAR_COMPRD.L(RTC,S)$DIAG('PRD',COM_VAR)+VAR_COMNET.L(RTC,S)$DIAG('NET',COM_VAR))+{arg1}_COMC(J,RTC,CUR)*G_YRFR(R,S))*SW_PROB(W)/Z);" if condition else ""}

*------------------------------------------------------------------------------
* Commodity costs associated with imports/exports from outside study area
*------------------------------------------------------------------------------
  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(RDCUR(R,CUR)$RPC(R,P,C)$RP_IRE(R,P)) $=
        SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'OUT')), {arg5}({tpulse} OBJ_IPRIC(R,{arg4},P,C,S,IE,CUR)) * PAR_IRE(R,V,T,P,C,S,IE));

*------------------------------------------------------------------------------
* Flow level costs
*------------------------------------------------------------------------------
  OPTION TRACKPC < PAR_FLO;
  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$TRACKPC(R,P,C)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} (OBJ_FCOST(R,{arg4},P,C,TS,CUR)+OBJ_FDELV(R,{arg4},P,C,TS,CUR)))) * PAR_FLO(R,V,T,P,C,S));

  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$RPC_STG(R,P,C)) =
     SUM(RPCS_VAR(R,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} (VAR_SIN.L(R,V,T,P,C,S)*OBJ_FCOST(R,{arg4},P,C,TS,CUR)+VAR_SOUT.L(R,V,T,P,C,S)*STG_EFF(R,V,P)*OBJ_FDELV(R,{arg4},P,C,TS,CUR)))));

  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$RP_IRE(R,P)) =
     {arg1}_FLOC(J,R,V,T,P,C,CUR) +
     SUM(RTPCS_VARF(R,T,P,C,S),
      SUM(TS_ANN(S,TS),{arg5}({tpulse} (OBJ_FCOST(R,{arg4},P,C,TS,CUR) + OBJ_FDELV(R,{arg4},P,C,TS,CUR)))) *
      (
         SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
         SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
      ));

* handle the fact that commodity costs may be associated with capacity
  {arg1}_FLOC({arg2}R,V,T,P,C,CUR)$(VNT(V,T)$OBJ_VFLO(R,P,C,CUR,'COST')$RPC_CAPFLO(R,V,P,C)) =
      {arg1}_FLOC(J,R,V,T,P,C,CUR) +
      SUM(ANNUAL(S),
{include_cal_caps_1}
        );

*------------------------------------------------------------------------------
* Flow level tax/sub
*------------------------------------------------------------------------------

  {arg1}_FLOC({arg3}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'TAX')$TRACKPC(R,P,C)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} OBJ_FTAX(R,{arg4},P,C,TS,CUR))) * PAR_FLO(R,V,T,P,C,S));

  {arg1}_FLOC({arg3}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'TAX')$RP_IRE(R,P)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
      SUM(TS_ANN(S,TS),{arg5}({tpulse} OBJ_FTAX(R,{arg4},P,C,TS,CUR))) *
      (
         SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
         SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
      ));

* handle the fact that commodity costs may be associated with capacity
  {arg1}_FLOC({arg3}R,V,T,P,C,CUR)$(VNT(V,T)$OBJ_VFLO(R,P,C,CUR,'TAX')$RPC_CAPFLO(R,V,P,C)) =
      {arg1}_FLOC(J,R,V,T,P,C,CUR) +
      SUM(ANNUAL(S),
{include_cal_caps_2}
        );
  OPTION CLEAR=TRACKPC;

*------------------------------------------------------------------------------
* Commodity blending costs
*------------------------------------------------------------------------------
  {arg1}_COMC({arg2}R,T,BLE,CUR)$RDCUR(R,CUR) = {arg1}_COMC(J,R,T,BLE,CUR) +
     SUM(BLE_OPR(R,BLE,OPR), {arg5}({tpulse} OBJ_BLNDV(R,{arg4},BLE,OPR,CUR)) * VAR_BLND.L(R,T,BLE,OPR));

*------------------------------------------------------------------------------
""",
        )

    def execute_legacy_behavior(
        self: EqobjvarRpt,
        is_vnret_defined: bool,
        varv: str,
        sws: str,
        varm: str,
    ):
        include_cal_caps = cal_caps_mod(
            is_vnret_defined=is_vnret_defined,
            arg1="T",
            arg2="SUM(TS_ANN(TS,SL),OBJ_FCOST(R,Y_EOH,P,C,SL,CUR)+OBJ_FDELV(R,Y_EOH,P,C,SL,CUR)+OBJ_FTAX(R,Y_EOH,P,C,SL,CUR))",
            arg3="TS",
            arg4=".L",
            varv=varv,
            sws=sws,
            varm=varm,
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*==============================================================================
* Legacy reporting (by every year and timeslice, discounted):
* Generate Variable cost formulas summing over all active indexes by region and currency
*===============================================================================

*------------------------------------------------------------------------------
* Overall activity of a process based costs
*------------------------------------------------------------------------------
 LOOP(T,
        PAR_OBJACT(R,V,Y_EOH,P,S,CUR)$(PERIODYR(T,Y_EOH)*RTP_VINTYR(R,V,T,P)*PRC_TS(R,P,S)) =
          OBJ_DISC(R,Y_EOH,CUR) * OBJ_ACOST(R,Y_EOH,P,CUR) * VAR_ACT.L(R,V,T,P,S) * POWER(RS_STGAV(R,S),1$RP_STG(R,P))
     );

*------------------------------------------------------------------------------
* Commodity added costs and sub/tax
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJCOM(R,Y_EOH,C,S,CUR)$PERIODYR(T,Y_EOH) $=
         SUM(RHS_COMBAL(R,T,C,S), OBJ_DISC(R,Y_EOH,CUR) * VAR_COMNET.L(R,T,C,S) * SUM(COSTYPE,OBJ_COMNT(R,Y_EOH,C,S,COSTYPE,CUR))) +
         SUM(RHS_COMPRD(R,T,C,S), OBJ_DISC(R,Y_EOH,CUR) * VAR_COMPRD.L(R,T,C,S) * SUM(COSTYPE,OBJ_COMPD(R,Y_EOH,C,S,COSTYPE,CUR)));
     );

*------------------------------------------------------------------------------
* Commodity costs/tax/sub associated with imports/exports from outside study area (external regions)
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$((PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P))$RP_IRE(R,P)) $=
         SUM(RPC_IREIO(R,P,C,IE,'OUT'), OBJ_DISC(R,Y_EOH,CUR) * OBJ_IPRIC(R,Y_EOH,P,C,S,IE,CUR) * PAR_IRE(R,V,T,P,C,S,IE));
     );

*------------------------------------------------------------------------------
* Flow level costs/tax/sub
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P)*RP_FLO(R,P)) =

         OBJ_DISC(R,Y_EOH,CUR) * PAR_FLO(R,V,T,P,C,S) *
         SUM(TS_ANN(S,TS),OBJ_FCOST(R,Y_EOH,P,C,TS,CUR) + OBJ_FDELV(R,Y_EOH,P,C,TS,CUR) + OBJ_FTAX(R,Y_EOH,P,C,TS,CUR))
     );

 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(SUM(OBJ_VFLO(R,P,C,CUR,UC_COST),1)$(PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P)$RP_IRE(R,P))) =

         PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR) +
         OBJ_DISC(R,Y_EOH,CUR) *
         SUM(TS_ANN(S,TS),OBJ_FCOST(R,Y_EOH,P,C,TS,CUR) + OBJ_FDELV(R,Y_EOH,P,C,TS,CUR) + OBJ_FTAX(R,Y_EOH,P,C,TS,CUR)) *
         (
           SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
           SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
         )
     );

* handle the fact that commodity costs may be associated with capacity
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(PERIODYR(T,Y_EOH)*RPCS_VAR(R,P,C,S)*VNT(V,T)*RPC_CAPFLO(R,V,P,C)) =
         PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR) +
         OBJ_DISC(R,Y_EOH,CUR) *
         (
{include_cal_caps}
         )
     );

*------------------------------------------------------------------------------
* Commodity blending costs
*------------------------------------------------------------------------------
   PAR_OBJBLE(R,Y_EOH,BLE,CUR)$RDCUR(R,CUR) = OBJ_DISC(R,Y_EOH,CUR) *
        SUM((BLE_OPR(R,BLE,OPR),PERIODYR(T,Y_EOH)), OBJ_BLNDV(R,Y_EOH,BLE,OPR,CUR) * VAR_BLND.L(R,T,BLE,OPR));

* Check that the Calculated objective components are equal to those Derived by the solver:
OBJ_C = SUM((R,V,Y_EOH,P,S,CUR)$PAR_OBJACT(R,V,Y_EOH,P,S,CUR),PAR_OBJACT(R,V,Y_EOH,P,S,CUR))+
   SUM((R,V,Y_EOH,P,C,S,CUR)$PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR),PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR))+
   SUM((R,Y_EOH,C,S,CUR)$PAR_OBJCOM(R,Y_EOH,C,S,CUR),PAR_OBJCOM(R,Y_EOH,C,S,CUR));
OBJ_D = SUM(RDCUR(R,CUR),SUM(OBV,SUM_OBJ('OBJVAR',OBV)*VAR_OBJ.L(R,OBV,CUR)));
DISPLAY OBJ_C,OBJ_D;
""",
        )
