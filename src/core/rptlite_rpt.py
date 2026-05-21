# rptlite_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTLITE.rpt is the main driver for the light-weight report writer for TIMES
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cost_ann_rpt import cost_ann_rpt
from core.par_uc_rpt import par_uc_rpt
from core.rpt_obj_rpt import rpt_obj_rpt
from core.rptmisc_rpt import rptmisc_rpt
from core.sol_flo_red import sol_flo_red
from core.sol_ire_rpt import sol_ire_rpt
from core.solsetv_v3 import SolsetvV3
from core.solsysd_v3 import SolsysdV3

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptliteRpt(GamsClass):
    """Translation unit for rptlite.rpt."""

    module_name: str = "rptlite_rpt"
    gams_source: str = "rptlite.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        # $IF NOT %SOLVEDA%==1 $SHIFT SHIFT SHIFT
        if self.env.solveda != "1":
            self.arg1 = self.arg4
            self.arg2 = ""
            self.arg3 = ""
            self.arg4 = ""

        if self.arg4 == "NO":
            self._label_report()
            return

        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYSUC",
                set_name="SYSUC",
                map=True,
                set_prefix=self.env.sysprefix,
                labels=[
                    "VAR",
                    "VARX",
                    "INV",
                    "INVX",
                    "INV+",
                    "INVX+",
                    "FIX",
                    "FIXX",
                    "IRE",
                    "COM",
                    "ACT",
                    "FLO",
                    "ELS",
                    "DAM",
                    "DAS",
                    "DAM-EXT+",
                ],
            )
        )
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYSUC",
                map=False,
                set_name="SYSUC",
                set_prefix=self.env.sysprefix,
                labels=[
                    "INSTCAP",
                    "LUMPINV",
                    "LUMPIX",
                    "COST",
                    "CGAP",
                    "GGAP",
                    "RNGLO",
                    "RNGUP",
                    "RATIO",
                    "GRATIO",
                    "LEVCOST",
                ],
            )
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
ALIAS(ALLSOW,WW);
""",
        )

        if self.env.is_set("rpt_opt"):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"PARAMETER RPT_OPT / {self.env.rpt_opt} /;",
            )

        if self.env.rpt_flots == "COM":
            self.tc.enqueue(self.exec1)

        self.tc.enqueue(self.exec2)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*------------------------------------------------------------------------------
* Other general parameters and sets
 PARAMETERS
   RTP_OBJ(J,R,ALLYEAR,P,CUR)      //
   RTP_NPV(J,R,ALLYEAR,P,CUR)      //
   PAR_ACTC(J,R,LL,T,P,C,CUR)
   PAR_FLOC(J,R,LL,T,P,C,CUR)
   PAR_COMC(J,R,T,C,CUR)
   PAR_RPMX(R,P,J,LL,T,C,CUR)
   PAR_RCMX(R,C,J,T,CUR)
   PAR_OBJCAP(R,ALLYEAR,P,CUR)
   PAR_XPRI(R,T,P,C,TS,REG,COM)
   COEF_OBJINV(R,ALLYEAR,PRC)      //
   COEF_OBINV(R,ALLYEAR,P,CUR)     //
   COEF_OBFIX(R,ALLYEAR,P,CUR)     //
   COEF_CRF(R,ALLYEAR,P,CUR)       //
   VAR_NCAPRNG(R,ALLYEAR,P,BD)     //
   CSTVNT(J,R,LL,YEAR,P,SYSUC)     //
   CSTVPJ(R,LL,P,J,SYSUC,YEAR)
   F_VIO(R,ALLYEAR,T,P,IO)
   F_IOS(R,ALLYEAR,T,P,C,S)        //
   F_INOUT(R,ALLYEAR,T,P,C,IO)     //
   F_INOUTS(R,ALLYEAR,T,P,C,S,IO)  //
   REG_OBJ(REG)                    //
   BC_INVACT(R,ALLYEAR,LL,PRC,S)   //
   BC_INVTOT(R,ALLYEAR,PRC)        //
   VAL_FLO(R,ALLYEAR,LL,PRC,C)     //
   PAR_RTCS(R,T,C,S)
   PAR_TOP(R,T,P,C,IO);

 SET NCAP_YES(R,ALLYEAR,P)         //;
 SET F_IOSET(R,ALLYEAR,T,P,C,S,IO) //;
 SET RVTPC(R,ALLYEAR,T,P,C)        //;
 SET RTTC(R,ALLYEAR,C);
 SET PASTCV / '0','€' /, RPM / '-','+' /;
 SET RNGLIM(SYSUC), SYSINV(SYSUC);
 SET SUCMAP(J,SYSUC) /2.{self.env.sysprefix}LUMPINV,2.{self.env.sysprefix}INV+,1.{self.env.sysprefix}LUMPIX,1.{self.env.sysprefix}INVX+/;
 SET RNGMAP(SYSUC,BD) / {self.env.sysprefix}RNGLO.LO, {self.env.sysprefix}RNGUP.UP /;
""",
        )

        self.tc.enqueue(self.exec3)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
 SCALAR OBJVAL_1 / 0 /, OBJVAL_2 / 0 /;
 PARAMETER SYSONE(SYSUC) / {self.env.sysprefix}INV 1 /, SYSPLIT(SYSUC);

*------------------------------------------------------------------------------
* Stochastic result parameters
 PARAMETER {self.arg1}CST_PVC({self.arg2}SYSUC,R,C)       //;
 PARAMETER {self.arg1}CST_PVP({self.arg2}SYSUC,R,P)       //;
 PARAMETER {self.arg1}F_IN({self.arg2}R,ALLYEAR,T,P,C,S)  //;
 PARAMETER {self.arg1}F_OUT({self.arg2}R,ALLYEAR,T,P,C,S) //;
 PARAMETER {self.arg1}P_OUT({self.arg2}R,T,P,C,S)         //;
 PARAMETER {self.arg1}AGG_OUT({self.arg2}R,T,C,TS)        //;
 PARAMETER {self.arg1}PAR_ACTL({self.arg2}R,LL,LL,P,S)    //;
 PARAMETER {self.arg1}PAR_ACTM({self.arg2}R,LL,LL,P,S)    //;
 PARAMETER {self.arg1}PAR_PASTI({self.arg2}R,T,P,ITEM)    //;
 PARAMETER {self.arg1}PAR_CAPL({self.arg2}R,YEAR,P)       //;
 PARAMETER {self.arg1}PAR_CAPM({self.arg2}R,YEAR,P)       //;
 PARAMETER {self.arg1}PAR_CAPBD({self.arg2}R,YEAR,P,BD)   //;
 PARAMETER {self.arg1}PAR_CUMRET({self.arg2}R,YEAR,YEAR,P)//;
 PARAMETER {self.arg1}PAR_NCAPL({self.arg2}R,ALLYEAR,P)   //;
 PARAMETER {self.arg1}PAR_NCAPM({self.arg2}R,ALLYEAR,P)   //;
 PARAMETER {self.arg1}PAR_NCAPR({self.arg2}R,ALLYEAR,P,ITEM) //;
 PARAMETER {self.arg1}PAR_OBJSAL({self.arg2}R,ALLYEAR,P,CUR) //;

 PARAMETER {self.arg1}PAR_COMPRDL({self.arg2}R,ALLYEAR,C,S)   //;
 PARAMETER {self.arg1}PAR_COMPRDM({self.arg2}R,ALLYEAR,C,S)   //;
 PARAMETER {self.arg1}PAR_COMNETL({self.arg2}R,ALLYEAR,C,S)   //;
 PARAMETER {self.arg1}PAR_COMNETM({self.arg2}R,ALLYEAR,C,S)   //;
 PARAMETER {self.arg1}PAR_COMBALEM({self.arg2}R,ALLYEAR,C,S)  //;
 PARAMETER {self.arg1}PAR_COMBALGM({self.arg2}R,ALLYEAR,C,S)  //;
 PARAMETER {self.arg1}PAR_IPRIC({self.arg2}R,YEAR,P,C,TS,IE)  //;
 PARAMETER {self.arg1}PAR_PEAKM({self.arg2}R,ALLYEAR,CG,S)    //;
 PARAMETER {self.arg1}PAR_UCSL({self.arg2}UC_N,*,*,*)         //;
 PARAMETER {self.arg1}PAR_UCSM({self.arg2}UC_N,*,*,*)         //;
 PARAMETER {self.arg1}PAR_UCMRK({self.arg2}R,T,ITEM,C,S)      //;
 PARAMETER {self.arg1}PAR_UCMAX({self.arg2}UC_N,ALL_R,ITEM,C) //;
 PARAMETER {self.arg1}PAR_CUMFLOL({self.arg2}R,P,C,LL,LL)     //;
 PARAMETER {self.arg1}PAR_CUMFLOM({self.arg2}R,P,C,LL,LL)     //;
 PARAMETER {self.arg1}PAR_CUMCST({self.arg2}R,LL,LL,COSTAGG,CUR) //;
 PARAMETER {self.arg1}PAR_UCRTP({self.arg2}UC_N,R,T,P,UC_GRPTYPE)//;

* Stochastic cost parameters
 PARAMETER REG_WOBJ(REG,ITEM,CUR)              //;
 PARAMETER {self.arg1}REG_WOBJ({self.arg2}REG,ITEM,CUR)          //;
 PARAMETER {self.arg1}REG_IREC({self.arg2}REG)                   //;
 PARAMETER {self.arg1}REG_ACOST({self.arg2}R,ALLYEAR,ITEM)       //;
 PARAMETER {self.arg1}CST_INVC({self.arg2}R,ALLYEAR,T,P,SYSUC)   //;
 PARAMETER {self.arg1}CST_INVX({self.arg2}R,ALLYEAR,T,P,SYSUC)   //;
 PARAMETER {self.arg1}CST_DECC({self.arg2}R,ALLYEAR,T,P)         //;
 PARAMETER {self.arg1}CST_FIXC({self.arg2}R,ALLYEAR,T,P)         //;
 PARAMETER {self.arg1}CST_FIXX({self.arg2}R,ALLYEAR,T,P)         //;
 PARAMETER {self.arg1}CST_ACTC({self.arg2}R,ALLYEAR,T,P,RPM)     //;
 PARAMETER {self.arg1}CST_FLOC({self.arg2}R,ALLYEAR,T,P,C)       //;
 PARAMETER {self.arg1}CST_FLOX({self.arg2}R,ALLYEAR,T,P,C)       //;
 PARAMETER {self.arg1}CST_IREC({self.arg2}R,ALLYEAR,T,P,C)       //;
 PARAMETER {self.arg1}CST_COMC({self.arg2}R,ALLYEAR,C)           //;
 PARAMETER {self.arg1}CST_COMX({self.arg2}R,ALLYEAR,C)           //;
 PARAMETER {self.arg1}CST_COME({self.arg2}R,ALLYEAR,C)           //;
 PARAMETER {self.arg1}CST_SALV({self.arg2}R,ALLYEAR,P)           //;
 PARAMETER {self.arg1}CST_TIME({self.arg2}R,ALLYEAR,S,SYSUC)     //;
 PARAMETER {self.arg1}CAP_NEW({self.arg2}R,ALLYEAR,P,T,SYSUC)    //;
* Damage cost and custom parameters
 PARAMETER {self.arg1}DAM_OBJ({self.arg2}R,T,C,CUR);
 PARAMETER {self.arg1}CST_DAM({self.arg2}R,T,C) 'Damage costs'   //;
 PARAMETER {self.arg1}PAR_EOUT({self.arg2}R,ALLYEAR,T,P,C)       //;
""",
        )

        self.tc.enqueue(self.exec4, ctst=self.env.ctst)

        if self.env.sensis.upper() == "YES":
            self.include(SolsetvV3(self.tc, self.env))

        self.tc.enqueue(self.exec5)

        if self.env.solveda == "1":
            return

        self._label_report()

    def _label_report(self) -> None:
        self.tc.enqueue(
            self.exec_label_report,
            arg1=self.arg1,
            arg3=self.arg3,
            sow=self.env.sow,
            sysprefix=self.env.sysprefix,
            sensis=self.env.sensis,
            var_uc=self.env.var_uc,
            stages=self.env.stages,
            obmac=self.env.obmac,
            abs_=self.env.abs,
            var=self.env.var,
            shff=self.env.shff,
            pgprim=self.env.pgprim,
            bencost=self.env.bencost,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            etl=self.env.etl,
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            timesed=self.env.timesed,
            obj=self.env.obj,
            varcost=self.env.varcost,
            vnret_defined=self.tc.defined("VNRET"),
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            varv=self.env.varv,
            sws=self.env.sws,
            varm=self.env.varm,
            obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            vart=self.env.vart,
            micro=self.env.micro,
            mi_agc_defined=self.tc.defined("MI_AGC"),
            cufscal=self.env.cufscal,
            model_name=self.env.model_name,
            eq=self.env.eq,
            rpt_flots=self.env.rpt_flots,
            solans=self.env.solans,
            discshift=self.env.discshift,
            eqe_ucrtp_defined=self.tc.defined("EQE_UCRTP"),
            eq_g_ucmax_not_defined=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
        )

    def exec_label_report(
        self: RptliteRpt,
        arg1: str,
        arg3: str,
        sow: str,
        sysprefix: str,
        sensis: str,
        var_uc: str,
        stages: str,
        obmac: str,
        abs_: str,
        var: str,
        shff: str,
        pgprim: str,
        rtp_ffcs_defined: bool,
        etl: str,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        invlif: str,
        anncost: str,
        varv: str,
        sws: str,
        bencost: str,
        varm: str,
        obj_combal_defined: bool,
        vart: str,
        micro: str,
        mi_agc_defined: bool,
        cufscal: str,
        model_name: str,
        eq: str,
        rpt_flots: str,
        solans: str,
        discshift: str,
        eqe_ucrtp_defined: bool,
        eq_g_ucmax_not_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rptlite_rpt(
                arg1=arg1,
                arg3=arg3,
                sow=sow,
                sysprefix=sysprefix,
                sensis=sensis,
                var_uc=var_uc,
                stages=stages,
                obmac=obmac,
                abs_=abs_,
                var=var,
                shff=shff,
                pgprim=pgprim,
                rtp_ffcs_defined=rtp_ffcs_defined,
                bencost=bencost,
                etl=etl,
                capjd=capjd,
                capwd=capwd,
                timesed=timesed,
                obj=obj,
                varcost=varcost,
                vnret_defined=vnret_defined,
                invlif=invlif,
                anncost=anncost,
                varv=varv,
                sws=sws,
                varm=varm,
                obj_combal_defined=obj_combal_defined,
                vart=vart,
                micro=micro,
                mi_agc_defined=mi_agc_defined,
                cufscal=cufscal,
                model_name=model_name,
                eq=eq,
                rpt_flots=rpt_flots,
                solans=solans,
                discshift=discshift,
                eqe_ucrtp_defined=eqe_ucrtp_defined,
                eq_g_ucmax_not_defined=eq_g_ucmax_not_defined,
            ),
        )

    def exec1(self: RptliteRpt) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="RPT_OPT('FLO','1')=1;",
        )

    def exec2(self: RptliteRpt) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  RPT_OPT(ITEM,J)$(RPT_OPT(ITEM,J)=0)=0;
  RPT_OPT('FLO','1')$RPT_OPT('FLO','3')=1;
""",
        )

    def exec3(self: RptliteRpt) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=" OPTION RNGLIM < RNGMAP;",
        )

    def exec4(self: RptliteRpt, ctst: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*------------------------------------------------------------------------------
* Prepare some sets and parameters that can be used for all SOW
*------------------------------------------------------------------------------
  SALV_INV(OBJ_SUMS(R,PASTMILE(V),P),V)=SUM(OBJ_ICUR(R,V,P,CUR)$OBJ_PASTI(R,V,P,CUR),SALV_INV(R,V,P,V)*(NCAP_PASTI(R,V,P)/OBJ_PASTI(R,V,P,CUR)))*(1-0{ctst});
* Hold on to costs
  OBJ_VFLO(R,P,C,CUR,UC_COST)$(NOT RDCUR(R,CUR)) = NO;
  OBJ_VFLO(R,P,C,CUR,'TAX')$=OBJ_VFLO(R,P,C,CUR,'SUB');
  SYSINV(SYSUC)$=SYSONE(SYSUC);
* Hold on to auxliary flows and past investments
  LOOP(RPC_IRE(R,P,COM,IE),F_IOSET(RTP_VINTYR(R,V,T,P),C,TS,IO)$(RPCS_VAR(R,P,COM,TS)$IRE_FLOSUM(R,T,P,COM,TS,IE,C,IO)) = RC(R,C));
""",
        )

    def exec5(self: RptliteRpt) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION CLEAR=COEF_RTP;",
        )


def rptlite_rpt(
    *,
    arg1: str,
    arg3: str,
    sow: str,
    sysprefix: str,
    sensis: str,
    var_uc: str,
    stages: str,
    obmac: str,
    abs_: str,
    var: str,
    shff: str,
    pgprim: str,
    rtp_ffcs_defined: bool,
    etl: str,
    capjd: str,
    capwd: str,
    timesed: str,
    obj: str,
    varcost: str,
    vnret_defined: bool,
    invlif: str,
    anncost: str,
    varv: str,
    sws: str,
    varm: str,
    obj_combal_defined: bool,
    vart: str,
    micro: str,
    mi_agc_defined: bool,
    cufscal: str,
    model_name: str,
    eq: str,
    rpt_flots: str,
    solans: str,
    bencost: str,
    discshift: str,
    eqe_ucrtp_defined: bool,
    eq_g_ucmax_not_defined: bool,
) -> str:
    sensis_yes = sensis.upper() == "YES"
    var_uc_yes = var_uc == "YES"
    stages_yes = stages == "YES"
    obmac_yes = obmac.upper() == "YES"
    abs_yes = abs_.upper() == "YES"

    return rf"""
*------------------------------------------------------------------------------
* Reports based on SOW-specific values
*------------------------------------------------------------------------------
* Calculation of solution values for (due to reduction) substituted flows
*------------------------------------------------------------------------------
  OPTION CLEAR=PAR_FLO,CLEAR=PAR_FLOM;

{
        sol_flo_red(
            arg1="PAR_FLO",
            arg2="",
            arg3=".L",
            v=var,
            shff=shff,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
    }
{
        sol_flo_red(
            arg1="PAR_FLO",
            arg2="M",
            arg3=".M",
            v=var,
            shff=shff,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
    }
{
        sol_ire_rpt(
            v=var,
            shff=shff,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
    }

*------------------------------------------------------------------------------
* Objective function
*------------------------------------------------------------------------------
  OPTION CLEAR=COEF_OBJINV;

{
        rpt_obj_rpt(
            arg1=arg1,
            arg2=arg3,
            arg3=sow,
            arg4=sysprefix,
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
    }

* Calculation of annual costs
{
        cost_ann_rpt(
            arg1=arg1,
            arg2=arg3,
            stages=stages,
            etl=etl,
            invlif=invlif,
            anncost=anncost,
            sysprefix=sysprefix,
            pgprim=pgprim,
            tpulse=(
                "Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)*"
                if varcost.upper() == "LIN"
                else "TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)*"
                if obj.upper() == "LIN"
                else "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)* OBJ_ALTV(R,T)*"
                if obj.upper() == "ALT"
                else "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)*"
            ),
            is_vnret_defined=vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            is_obj_combal_defined=obj_combal_defined,
            sow=sow,
            var=var,
            vart=vart,
            micro=micro,
            is_mi_agc_defined=mi_agc_defined,
        )
    }

* Miscellaneous reportings
{
        rptmisc_rpt(
            arg1=arg1,
            arg2=arg3,
            arg3=sow,
            arg4=sws,
            arg5=sow,
            var=var,
            cufscal=cufscal,
            sysprefix=sysprefix,
            model_name=model_name,
            vart=vart,
            sws=sws,
            eq=eq,
            if_defined_vnret=vnret_defined,
            rpt_flots=rpt_flots,
            stages=stages,
            if_defined_eqe_ucrtp=eqe_ucrtp_defined,
            var_uc=var_uc,
            if_not_defined_eq_g_ucmax=eq_g_ucmax_not_defined,
            solans=solans,
        )
    }

* Add aggregation levels
{
        rf'''LOOP(NRG_TYPE,Z=RPT_OPT(NRG_TYPE,'1'); IF(Z,PAR_RTCS(RTCS_VARC(R,T,C,S))$NRG_TMAP(R,NRG_TYPE,C)={arg1}AGG_OUT({arg3}R,T,C,S)/G_YRFR(R,S)/Z));'''
        if not sensis_yes
        else ""
    }

{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQE", arg3=arg1, arg4=arg3)}
{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQG", arg3=arg1, arg4=arg3)}
{"" if var_uc_yes else par_uc_rpt(arg1="SM", arg2="EQL", arg3=arg1, arg4=arg3)}

{
        r'''REG_WOBJ(R,ITEM,CUR) $= SUM(W$SREG_WOBJ(W,R,ITEM,CUR),SW_PROB(W)*SREG_WOBJ(W,R,ITEM,CUR));'''
        if stages_yes
        else rf'''REG_WOBJ(R,ITEM,CUR) $= {arg1}REG_WOBJ({arg3}R,ITEM,CUR);'''
    }

{"$ONDOTL" if obmac_yes else ""}

{
        rf'''Z=RPT_OPT('RATE','1'); IF(Z,TRACKPC(BS_BSC)=YES; TRACKPC(BS_STGP(R,P),C)$=BS_RTYPE(R,C));
{arg1}P_OUT({arg3}RTP(R,T,P),C,S)$(PRC_TS(R,P,S)$BS_COMTS(R,C,S)$TRACKPC(R,P,C)$Z)=SUM(RTP_VINTYR(R,V,T,P),VAR_BSFSP(R,V,T,P,C,S)+VAR_BSFNSP(R,V,T,P,C,S))*PRC_CAPACT(R,P)/Z;'''
        if abs_yes
        else ""
    }

OPTION CLEAR=TRACKPC;
"""
