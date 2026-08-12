# eqbndcst_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQBNDCOST: bounds on undiscounted cost components
# *   arg1 -
# *=============================================================================*
# *[AL] Questions/Comments:
# *

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.cal_nored_red import cal_nored_red
from core.cal_red_red import cal_red_red
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqbndcstMod(GamsClass):
    """Translation unit for eqbndcst.mod."""

    # Instance attributes
    module_name: str = "eqbndcst_mod"
    gams_source: str = "eqbndcst.mod"

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
        g = self.tc

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Need a few more aliases and sets
 SET SUPERYR(T,ALLYEAR) 'SUpremum PERiod YeaR'   //;
 SET YKK(ALLYEAR,ALLYEAR,ALLYEAR)                //;
 SET RTP_IAN(REG,T,P,CUR)                        //;
 SET RT_IAN(REG,ALLYEAR,ALLYEAR,CUR,COSTAGG)     //;
 PARAMETER CST_ANNC(R,ALLYEAR,P,ALLYEAR,UC_NAME,CUR) //;
""",
        )

        if "OBJ_SUMII" not in self.tc.container.listSymbols():
            return

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
 SET COST_GMAP(COSTAGG,COSTAGG,COSTYPE) /
  INVTAXSUB.(INVTAX.TAX,INVSUB.SUB)
  INVALL   .(INV.COST,INVTAX.TAX,INVSUB.SUB)
  FOMTAXSUB.(FOMTAX.TAX,FOMSUB.SUB)
  FOMALL   .(FOM.COST,FOMTAX.TAX,FOMSUB.SUB)
  FIX      .(INV.COST,FOM.COST)
  FIXTAX   .(INVTAX.TAX,FOMTAX.TAX)
  FIXSUB   .(INVSUB.TAX,FOMSUB.TAX)
  FIXTAXSUB.(INVTAX.TAX,INVSUB.SUB,FOMTAX.TAX,FOMSUB.SUB)
  FIXALL   .(INV.COST,INVTAX.TAX,INVSUB.SUB,FOM.COST,FOMTAX.TAX,FOMSUB.SUB)
  COMTAXSUB.(COMTAX.TAX,COMSUB.SUB)
  FLOTAXSUB.(FLOTAX.TAX,FLOSUB.SUB)
  ALLTAX   .(INVTAX.TAX,FOMTAX.TAX,COMTAX.TAX,FLOTAX.TAX)
  ALLSUB   .(INVSUB.TAX,FOMSUB.TAX,COMSUB.TAX,FLOSUB.TAX)
  ALLTAXSUB.(INVTAX.TAX,INVSUB.SUB,FOMTAX.TAX,FOMSUB.SUB,COMTAX.TAX,COMSUB.SUB,FLOTAX.TAX,FLOSUB.SUB)
/;
""",
        )

        self.tc.enqueue(self.exec1, declif=self.env.declif)
        if self.env.stages == "YES":
            self.env.set_scoped("swt", f"SW_T(TT{self.env.sow})$")
            self.env.set_scoped(
                "swt_GP", (g.SwT[g.tt, *self.env.sow_GP],)
            )  # ToDo: Move $ to main code

        if self.env.scum == "1":
            self.env.set_scoped("swt", "")
            self.env.set_scoped("swt_GP", ())

        self.env.set_scoped("sowstart", self.env.sow)

        if self.env.stages == "YES":
            self.env.set_scoped("swd", self.env.sow)
            self.env.set_scoped("swd_GP", self.env.sow_GP)
            self.env.set_scoped("sow", self.env.swd)
            self.env.set_scoped("sow_GP", self.env.swd_GP)
            self.env.set_scoped("swtd", "SUM")
            self.env.set_scoped("swtd_GP", "SUM")  # ToDo: How to handle SUM here?

        if self.env.obj.upper() != "LIN":
            self.env.set_scoped(
                "tpulse", "(PERIODYR(T,Y_EOH),YK(ALLYEAR,Y_EOH))$YK(Y_EOH,YEAR),"
            )
        else:
            self.env.set_scoped(
                "tpulse",
                "(TPULSEYR(T,Y_EOH),YK(ALLYEAR,Y_EOH))$YK(Y_EOH,YEAR),TPULSE(T,Y_EOH)*",
            )
        if self.env.varcost.upper() == "LIN":
            self.env.set_scoped(
                "tpulse",
                "(PERIODYR(T,Y),MILESTONYR(Y_EOH),YK(ALLYEAR,Y))$(YK(Y,YEAR)$TPULSE(Y_EOH,Y)),TPULSE(Y_EOH,Y)*",
            )
        if f"{self.env.obj.upper()}{self.env.varcost.upper()}" == "LINLIN":
            self.env.set_scoped(
                "tpulse",
                "(TPULSEYR(T,Y),MILESTONYR(Y_EOH),YK(ALLYEAR,Y))$(YK(Y,YEAR)$TPULSE(Y_EOH,Y)),TPULSE(Y_EOH,Y)*TPULSE(T,Y)*",
            )

        # vart  & vart1 are only used in this file, not used in its children
        # degradation to local
        vart1 = self.env.vart
        if self.env.scum == "1":
            vart = "SUM(SW_TSW(W,T,W),SW_TPROB(T,W)*Z"
        else:
            vart = self.env.vart

        self.env.set_scoped("sowend", self.env.sow)
        if self.env.stages == "YES":
            self.env.set_scoped("sowend", self.env.swd)

        self.equation(
            eq=self.env.eq,
            sowstart=self.env.sowstart,
            swt=self.env.swt,
            vart1=vart1,
            sws=self.env.sws,
            declif=self.env.declif,
            tpulse=self.env.tpulse,
            vart=vart,
            swtd=self.env.swtd,
            swsw=self.env.swsw,
            cal_red=self.env.cal_red,
            var=self.env.var,
            sowend=self.env.sowend,
            pgprim=self.env.pgprim,
            sow=self.env.sow,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )

        if self.env.stages == "YES":
            self.env.set_scoped("sow", self.env.swd)
            self.env.set_scoped("sow_GP", self.env.swd_GP)

    def equation(
        self: EqbndcstMod,
        eq: str,
        sowstart: str,
        swt: str,
        vart1: str,
        sws: str,
        declif: str,
        tpulse: str,
        vart: str,
        swtd: str,
        swsw: str,
        cal_red: str,
        var: str,
        sowend: str,
        pgprim: str,
        sow: str,
        def_rtp_ffcs: bool,
    ) -> None:
        include_cal_red = ""

        # only set in pp_reduce.red
        if cal_red == "cal_red.red":
            include_cal_red = cal_red_red(
                arg1="C",
                arg2="COM",
                arg3="S",
                arg4="P",
                arg5="T",
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                sow=sow,
                var=var,
            )
        elif cal_red == "cal_nored.red":
            include_cal_red = cal_nored_red(
                arg1="C",
                arg2="COM",
                arg3="S",
                arg4="P",
                arg5="T",
                def_rtp_ffcs=def_rtp_ffcs,
                sow=sow,
                var=var,
                pgprim=pgprim,
            )
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*-----------------------------------------------------------------------------
  {eq}_BNDCST(R,YEAR,SUPERYR(TT,ALLYEAR),COSTCAT,CUR {sowstart})$({swt}REG_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR,'UP')) ..
*------------------------------------------------------------------------------
* Investment Costs
  (SUM((OBJ_SUMII(R,T,P,AGE,K_EOH(LL),JOT),SPAN(AGE+MIN(ORD(LL)+ORD(JOT)-ORD(YEAR)-1,0)))$YK(TT,T),
    SUM(INVSPRED(K_EOH,JOT,Y,K)$YK(ALLYEAR,Y),
      {macro.obj_icost("R", "K", "P", "CUR")} *
      MAX(0,MIN(YEARVAL(ALLYEAR)+1,YEARVAL(Y)+ORD(AGE))-MAX(YEARVAL(YEAR),YEARVAL(Y)))) *
    {vart1}_NCAP(R,T,P {sws}) * OBJ_CRF(R,T,P,CUR) / OBJ_DIVI(R,T,P))$(NOT RT_IAN(R,YEAR,ALLYEAR,CUR,'INV')) +
   SUM((T,P)$CST_ANNC(R,T,P,TT,'INVCOST',CUR),CST_ANNC(R,T,P,TT,'INVCOST',CUR)*{vart1}_NCAP(R,T,P {sws}))$RT_IAN(R,YEAR,ALLYEAR,CUR,'INV')
  )$SAMEAS(COSTCAT,'INV') +

* Decommissioning Costs
  SUM(RTP(R,T,P)$(YK(TT,T)${macro.obj_dcost("R", "T", "P", "CUR")}),
    SUM(OBJ_SUMIII(R,T,P,K_EOH,K,LL)$YK(ALLYEAR,LL), {macro.obj_dcost("R", "K", "P", "CUR")} *
      MAX(0,MIN(ORD(ALLYEAR)+1,ORD(LL)+ROUND(NCAP_{declif}(R,T,P)))-MAX(ORD(YEAR),ORD(LL)))) *
    {vart1}_NCAP(R,T,P {sws}) * OBJ_CRFD(R,T,P,CUR) / OBJ_DIVIII(R,T,P)
    )$SAMEAS(COSTCAT,'INV') +

* Investment Taxes and Subsidies
  (SUM(OBJ_SUMII(R,T,P,AGE,K_EOH,JOT)$(YK(TT,T)${macro.obj_itax("R", "T", "P", "CUR")}),
    SUM((INVSPRED(K_EOH,JOT,LL,K),SPAN(AGE+MIN(ORD(LL)-ORD(YEAR),0)))$YK(ALLYEAR,LL),
      {macro.obj_itax("R", "K", "P", "CUR")} * (MIN(ORD(ALLYEAR)+1,ORD(LL)+ORD(AGE))-MAX(ORD(YEAR),ORD(LL)))) *
    {vart1}_NCAP(R,T,P {sws}) * OBJ_CRF(R,T,P,CUR) / OBJ_DIVI(R,T,P))$(NOT RT_IAN(R,YEAR,ALLYEAR,CUR,'INVTAXSUB')) +
   SUM((T,P)$CST_ANNC(R,T,P,TT,'INVTAX',CUR),CST_ANNC(R,T,P,TT,'INVTAX',CUR)*{vart1}_NCAP(R,T,P {sws}))$RT_IAN(R,YEAR,ALLYEAR,CUR,'INVTAXSUB')
  )$SAMEAS(COSTCAT,'INVTAX') +

  (SUM(OBJ_SUMII(R,T,P,AGE,K_EOH,JOT)$(YK(TT,T)${macro.obj_isub("R", "T", "P", "CUR")}),
    SUM((INVSPRED(K_EOH,JOT,LL,K),SPAN(AGE+MIN(ORD(LL)-ORD(YEAR),0)))$YK(ALLYEAR,LL),
      {macro.obj_isub("R", "K", "P", "CUR")} * (MIN(ORD(ALLYEAR)+1,ORD(LL)+ORD(AGE))-MAX(ORD(YEAR),ORD(LL)))) *
    {vart1}_NCAP(R,T,P {sws}) * OBJ_CRF(R,T,P,CUR) / OBJ_DIVI(R,T,P))$(NOT RT_IAN(R,YEAR,ALLYEAR,CUR,'INVTAXSUB')) -
   SUM((T,P)$CST_ANNC(R,T,P,TT,'INVSUB',CUR),CST_ANNC(R,T,P,TT,'INVSUB',CUR)*{vart1}_NCAP(R,T,P {sws}))$RT_IAN(R,YEAR,ALLYEAR,CUR,'INVTAXSUB')
  )$SAMEAS(COSTCAT,'INVSUB') +
*------------------------------------------------------------------------------
* Fixed O&M Cost - shaped or not
  SUM((OBJ_SUMIV(LL,R,T,P,JOT,LIFE),SPAN(LIFE+MIN(ORD(LL)+ORD(JOT)-ORD(YEAR)-1,0)))$YK(TT,T),
      SUM(INVSTEP(LL,JOT,K,JOT)$YK(ALLYEAR,K), {macro.obj_fom("R", "K", "P", "CUR")} *
        MAX(0,MIN(YEARVAL(ALLYEAR)+1,YEARVAL(K)+ORD(LIFE))-MAX(YEARVAL(YEAR),YEARVAL(K)))) *
      {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
     )$SAMEAS(COSTCAT,'FOM') +
* Fixed O&M Cost - YES shaped
  SUM(RTP_SHAPE(R,T,P,'1',J,JJ)$YK(TT,T),
    SUM((OBJ_SUMIV(K,R,T,P,JOT,LIFE),INVSTEP(K,JOT,LL,JOT),SPAN(LIFE+MIN(ORD(LL)-ORD(YEAR),0)))$YK(ALLYEAR,LL),
      SUM(OPYEAR(LIFE,AGE)$((ORD(LL)+ORD(AGE) > ORD(YEAR))$(ORD(LL)+ORD(AGE) < ORD(ALLYEAR)+2)),
          SHAPE(J,AGE)*MULTI(JJ,LL+(ORD(AGE)-1))-1) * {macro.obj_fom("R", "LL", "P", "CUR")}) *
    {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
  )$SAMEAS(COSTCAT,'FOM') +

* Fixed O&M Taxes - shaped or not
  SUM((OBJ_SUMIV(LL,R,T,P,JOT,LIFE),SPAN(LIFE+MIN(ORD(LL)+ORD(JOT)-ORD(YEAR)-1,0)))$(YK(TT,T)${macro.obj_ftx("R", "T", "P", "CUR")}),
      SUM(INVSTEP(LL,JOT,K,JOT)$YK(ALLYEAR,K), {macro.obj_ftx("R", "K", "P", "CUR")} *
        MAX(0,MIN(YEARVAL(ALLYEAR)+1,YEARVAL(K)+ORD(LIFE))-MAX(YEARVAL(YEAR),YEARVAL(K)))) *
      {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
     )$SAMEAS(COSTCAT,'FOMTAX') +
* Fixed O&M Taxes - Shaped
  SUM(RTP_SHAPE(R,T,P,'2',J,JJ)$(YK(TT,T)${macro.obj_ftx("R", "T", "P", "CUR")}),
    SUM((OBJ_SUMIV(K,R,T,P,JOT,LIFE),INVSTEP(K,JOT,LL,JOT),SPAN(LIFE+MIN(ORD(LL)-ORD(YEAR),0)))$YK(ALLYEAR,LL),
      SUM(OPYEAR(LIFE,AGE)$((ORD(LL)+ORD(AGE) > ORD(YEAR))$(ORD(LL)+ORD(AGE) < ORD(ALLYEAR)+2)),
          SHAPE(J,AGE)*MULTI(JJ,LL+(ORD(AGE)-1))-1) * {macro.obj_ftx("R", "LL", "P", "CUR")}) *
    {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
  )$SAMEAS(COSTCAT,'FOMTAX') +

* Fixed O&M Subsidies - shaped or not
  SUM((OBJ_SUMIV(LL,R,T,P,JOT,LIFE),SPAN(LIFE+MIN(ORD(LL)+ORD(JOT)-ORD(YEAR)-1,0)))$(YK(TT,T)${macro.obj_fsb("R", "T", "P", "CUR")}),
      SUM(INVSTEP(LL,JOT,K,JOT)$YK(ALLYEAR,K), {macro.obj_fsb("R", "K", "P", "CUR")} *
        MAX(0,MIN(YEARVAL(ALLYEAR)+1,YEARVAL(K)+ORD(LIFE))-MAX(YEARVAL(YEAR),YEARVAL(K)))) *
      {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
     )$SAMEAS(COSTCAT,'FOMSUB') +
* Fixed O&M Subsidies - Shaped
  SUM(RTP_SHAPE(R,T,P,'3',J,JJ)$(YK(TT,T)${macro.obj_fsb("R", "T", "P", "CUR")}),
    SUM((OBJ_SUMIV(K,R,T,P,JOT,LIFE),INVSTEP(K,JOT,LL,JOT),SPAN(LIFE+MIN(ORD(LL)-ORD(YEAR),0)))$YK(ALLYEAR,LL),
      SUM(OPYEAR(LIFE,AGE)$((ORD(LL)+ORD(AGE) > ORD(YEAR))$(ORD(LL)+ORD(AGE) < ORD(ALLYEAR)+2)),
          SHAPE(J,AGE)*MULTI(JJ,LL+(ORD(AGE)-1))-1) * {macro.obj_fsb("R", "LL", "P", "CUR")}) *
    {vart1}_NCAP(R,T,P {sws}) / OBJ_DIVIV(R,T,P)
  )$SAMEAS(COSTCAT,'FOMSUB') +
*------------------------------------------------------------------------------
* Variable commodity taxes and subsidies
  SUM({tpulse}
     (SUM(RHS_COMBAL(R,T,C,S), {vart}_COMNET(R,T,C,S {sws}) * OBJ_COMNT(R,Y_EOH,C,S,'TAX',CUR)) +
      SUM(RHS_COMPRD(R,T,C,S), {vart}_COMPRD(R,T,C,S {sws}) * OBJ_COMPD(R,Y_EOH,C,S,'TAX',CUR)))
    )$SAMEAS(COSTCAT,'COMTAX') -

  SUM({tpulse}
     (SUM(RHS_COMBAL(R,T,C,S), {vart}_COMNET(R,T,C,S {sws}) * OBJ_COMNT(R,Y_EOH,C,S,'SUB',CUR)) +
      SUM(RHS_COMPRD(R,T,C,S), {vart}_COMPRD(R,T,C,S {sws}) * OBJ_COMPD(R,Y_EOH,C,S,'SUB',CUR)))
    )$SAMEAS(COSTCAT,'COMSUB') +
*------------------------------------------------------------------------------
* Variable flow taxes and subsidies
  SUM(T$(YK(TT,T)*(M(T)+LAGT(T) GT YEARVAL(YEAR))),
     SUM(RTPCS_VARF(R,T,P,C,S)$OBJ_VFLO(R,P,C,CUR,'TAX'),
        SUM(TS_ANN(S,TS), SUM({tpulse} MAX(0,{macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")}))) *
        SUM(RTP_VINTYR(R,V,T,P),
         {swtd}({swsw}
{include_cal_red}
            )$(NOT RP_IRE(R,P)) +
            (SUM(RPC_IRE(R,P,C,IE),
               {vart}_IRE(R,V,T,P,C,S,IE {sws})$(NOT RPC_AIRE(R,P,C))+({vart}_ACT(R,V,T,P,S {sws})*PRC_ACTFLO(R,V,P,C))$(RPC_AIRE(R,P,C))
                ) +
             SUM((RPC_IRE(R,P,COM,IE),IO)$(RTPCS_VARF(R,T,P,COM,S)$IRE_FLOSUM(R,T,P,COM,S,IE,C,IO)),
                  IRE_FLOSUM(R,T,P,COM,S,IE,C,IO) *
                  ({vart}_IRE(R,V,T,P,COM,S,IE {sws})$(NOT RPC_AIRE(R,P,COM))+({vart}_ACT(R,V,T,P,S {sws})*PRC_ACTFLO(R,V,P,COM))$(RPC_AIRE(R,P,COM)))
             ))$RP_IRE(R,P)
           )
       ))$SAMEAS(COSTCAT,'FLOTAX') +

  SUM(T$(YK(TT,T)*(M(T)+LAGT(T) GT YEARVAL(YEAR))),
     SUM(RTPCS_VARF(R,T,P,C,S)$OBJ_VFLO(R,P,C,CUR,'SUB'),
        SUM(TS_ANN(S,TS), SUM({tpulse} MAX(0,-{macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")}))) *
        SUM(RTP_VINTYR(R,V,T,P),
         {swtd}({swsw}
{include_cal_red}
            )$(NOT RP_IRE(R,P)) +
            (SUM(RPC_IRE(R,P,C,IE),
               {vart}_IRE(R,V,T,P,C,S,IE {sws})$(NOT RPC_AIRE(R,P,C))+({vart}_ACT(R,V,T,P,S {sws})*PRC_ACTFLO(R,V,P,C))$(RPC_AIRE(R,P,C))
                ) +
             SUM((RPC_IRE(R,P,COM,IE),IO)$(RTPCS_VARF(R,T,P,COM,S)$IRE_FLOSUM(R,T,P,COM,S,IE,C,IO)),
                  IRE_FLOSUM(R,T,P,COM,S,IE,C,IO) *
                  ({vart}_IRE(R,V,T,P,COM,S,IE {sws})$(NOT RPC_AIRE(R,P,COM))+({vart}_ACT(R,V,T,P,S {sws})*PRC_ACTFLO(R,V,P,COM))$(RPC_AIRE(R,P,COM)))
             ))$RP_IRE(R,P)
           )
       ))$SAMEAS(COSTCAT,'FLOSUB') +
*------------------------------------------------------------------------------
  SUM(COST_GMAP(COSTCAT,COSTAGG,COSTYPE), {var}_CUMCST(R,YEAR,ALLYEAR,COSTAGG,CUR {sowend})*(1-2*DIAG(COSTYPE,'SUB')))
*------------------------------------------------------------------------------

   =E=   {var}_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR {sowend});
""",
        )

    def exec1(self: EqbndcstMod, declif: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*-----------------------------------------------------------------------------
* Construct SUPERYR (needed for filtering)
  SUPERYR(PERIODYR(T,LL))$(YEARVAL(LL) LE YEARVAL(T)) = YES;
  SUPERYR(T+1,LL)$((YEARVAL(LL) GT YEARVAL(T))$PERIODYR(T,LL)) = YES;
  LOOP(MIYR_1(T++1),SUPERYR(T,LL)$(YEARVAL(LL) GT M(T)) = YES);
* Add single MILESTONYR bounds to REG_CUMCST
  REG_CUMCST(R,T,T,COSTAGG,CUR,BD) $= REG_BNDCST(R,T,COSTAGG,CUR,BD);
* Add infinite bound for components if aggregate bound
  LOOP((COST_GMAP(COSTCAT,COSTAGG,COSTYPE),BD),
    REG_CUMCST(R,YEAR,LL,COSTAGG,CUR,'UP')$((NOT REG_CUMCST(R,YEAR,LL,COSTAGG,CUR,'UP'))$REG_CUMCST(R,YEAR,LL,COSTCAT,CUR,BD)) = INF);
  LOOP(BDLOX(BD),
    REG_CUMCST(R,YEAR,LL,COSTCAT,CUR,'UP')$((NOT REG_CUMCST(R,YEAR,LL,COSTCAT,CUR,'UP'))$REG_CUMCST(R,YEAR,LL,COSTCAT,CUR,BD)) = INF);
*-----------------------------------------------------------------------------
* Prepare INVCOST and ITAXSUB coefficients
LOOP(UC_ATTR(R,UC_N,SIDE,'NCAP','INVCOST'),LOOP(T,TRACKP(R,P)$UC_NCAP(UC_N,SIDE,R,T,P)=YES));
RT_IAN(R,T,T,CUR,'INV')$REG_CUMCST(R,T,T,'INV',CUR,'UP') = YES;
RTP_IAN(OBJ_ICUR(R,T,P,CUR))$(RT_IAN(R,T,T,CUR,'INV')+TRACKP(R,P)) = YES;
* Calculate annual undiscounted INVCOST coefficients
OPTION CLEAR=YK1; YK1(TT,T)$YK(T,TT) = YES;
CST_ANNC(R,TT,P,T(YEAR),'INVCOST',CUR)$(YK1(TT,T)$RTP_IAN(R,TT,P,CUR)) =
  SUM(OBJ_SUMII(R,TT,P,AGE,K_EOH(LL),JOT)$((ORD(LL)+ORD(AGE)+ORD(JOT)-1 > ORD(YEAR))$YK(T,LL)),
    SUM(INVSPRED(K_EOH,JOT,ALLYEAR,K)$((ORD(ALLYEAR)+ORD(AGE) > ORD(YEAR))$YK(T,ALLYEAR)),
      {macro.obj_icost("R", "K", "P", "CUR")}) * OBJ_CRF(R,TT,P,CUR) / OBJ_DIVI(R,TT,P));
* Add decommissioning costs when defined
LOOP(RTP_IAN(R,TT,P,CUR)${macro.obj_dcost("R", "TT", "P", "CUR")},
 CST_ANNC(R,TT,P,T(YEAR),'INVCOST',CUR)$YK1(TT,T) =
   CST_ANNC(R,TT,P,T,'INVCOST',CUR) + OBJ_CRFD(R,TT,P,CUR) / OBJ_DIVIII(R,TT,P) *
   SUM(OBJ_SUMIII(R,TT,P,K_EOH,K,LL)$((ORD(LL)+ROUND(NCAP_{declif}(R,TT,P)) > ORD(YEAR))$YK(T,LL)),
     {macro.obj_dcost("R", "K", "P", "CUR")}));
* Calculate annual undiscounted INVTAXSUB coefficients
OPTION CLEAR=TRACKP, CLEAR=RTP_IAN;
LOOP(UC_ATTR(R,UC_N,SIDE,'NCAP',UC_ANNUL(UC_NAME(COSTCAT))),LOOP(T,TRACKP(R,P)$UC_NCAP(UC_N,SIDE,R,T,P)=YES));
RT_IAN(R,T,T,CUR,'INVTAXSUB')$(REG_CUMCST(R,T,T,'INVTAX',CUR,'UP')+REG_CUMCST(R,T,T,'INVSUB',CUR,'UP')) = YES;
RTP_IAN(OBJ_ICUR(R,T,P,CUR))$(RT_IAN(R,T,T,CUR,'INVTAXSUB')+TRACKP(R,P)) = YES;
LOOP(RTP_IAN(R,TT,P,CUR)$({macro.obj_itax("R", "TT", "P", "CUR")}+{macro.obj_isub("R", "TT", "P", "CUR")}),
  OPTION CLEAR=YKK; F = OBJ_CRF(R,TT,P,CUR)/OBJ_DIVI(R,TT,P);
  LOOP(OBJ_SUMII(R,TT,P,LIFE,K_EOH,JOT), Z=ORD(LIFE);
    YKK(YK(T(YEAR),LL),K)$((ORD(YEAR) < ORD(LL)+Z)$INVSPRED(K_EOH,JOT,LL,K)) = YES);
  CST_ANNC(R,TT,P,T,'INVTAX',CUR)$YK1(TT,T) = SUM(YKK(T,LL,K), F * {macro.obj_itax("R", "K", "P", "CUR")});
  CST_ANNC(R,TT,P,T,'INVSUB',CUR)$YK1(TT,T) = SUM(YKK(T,LL,K),-F * {macro.obj_isub("R", "K", "P", "CUR")});
);
OPTION CLEAR=TRACKP, CLEAR=RTP_IAN;
""",
        )
