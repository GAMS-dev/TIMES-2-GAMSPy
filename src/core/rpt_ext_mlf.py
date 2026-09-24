# rpt_ext_mlf.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.cost_ann_rpt import cost_ann_rpt
from core.par_uc_rpt import ParUcRpt, ParUcRptConfig
from core.rpt_obj_rpt import rpt_obj_rpt
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.rptmisc_rpt import RptmiscRpt, RptmiscRptConfig
from core.sol_flo_red import SolFloRed, SolFloRedConfig, sol_flo_red
from core.sol_ire_rpt import sol_ire_rpt

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtMlf(GamsClass):
    """Translation unit for rpt_ext.mlf."""

    # Instance attributes
    module_name: str = "rpt_ext_mlf"
    gams_source: str = "rpt_ext.mlf"

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
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("solveda", "1")

        self.include(RptliteRpt(self.tc, self.env, config=RptliteRptConfig()))

        # * Scenario index not supported in current version, use SOW 1
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET SOW / 1 /;
""",
        )
        self.env.set_scoped("method", "LP")

        if self.env.nonlp.upper() == "NL":
            self.env.set_scoped("method", "NLP")

        self.env.set_scoped("timesed", "NO")
        self.tc.enqueue(
            self.exec_loop,
            model_name=self.env.model_name,
            method=self.env.method,
            v=self.env.v,
            pgprim=self.env.pgprim,
            sow=self.env.sow,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            stages=self.env.stages,
            etl=self.env.etl,
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            var=self.env.var,
            timesed=self.env.timesed,
            obj=self.env.obj,
            varcost=self.env.varcost,
            vnret_defined=self.tc.defined("VNRET"),
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            sysprefix=self.env.sysprefix,
            tpulse=self.env.tpulse,
            is_vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv,
            sws=self.env.sws,
            mx=self.env.mx,
            varm=self.env.varm,
            is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            vart=self.env.vart,
            micro=self.env.micro,
            is_mi_agc_defined=self.tc.defined("MI_AGC"),
            bencost=self.env.bencost,
            discshift=self.env.discshift,
        )

        # * Calculation of undiscounted shadow prices in MACRO
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER VDA_DISC(R,ALLYEAR) //;
""",
        )
        self.tc.enqueue(self.exec1)

        # * Miscellaneous reportings
        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(arg1="PAR_FLO", arg2="M", arg3=".M"),
            )
        )
        self.tc.enqueue(self.exec2)
        # $ BATINCLUDE rptmisc.rpt '' ''
        self.include(
            RptmiscRpt(self.tc, self.env, config=RptmiscRptConfig(arg1="", arg2=()))
        )

        self.tc.enqueue(self.exec3, dam_cost_defined=self.tc.defined("DAM_COST"))

        # *---------------------------------------------------------------------
        # * Shadow prices of user constraints
        # *---------------------------------------------------------------------
        # * Note: undiscounting only done for user constraints having region and period as index

        if self.env.var_uc != "YES":
            for config in (
                ParUcRptConfig(arg1="SM", arg2="EQE"),
                ParUcRptConfig(arg1="SM", arg2="EQG"),
                ParUcRptConfig(arg1="SM", arg2="EQL"),
            ):
                self.include(ParUcRpt(self.tc, self.env, config=config))

        # GAMS's single-pass compiler registers every literal string in the
        # whole program as a UEL during compilation, before anything executes
        # -- including these TM_RESULT row labels from exec4 below, even
        # though that assignment doesn't run until much later (post-solve).
        # GAMSPy's incremental addGamsCode model only registers a literal once
        # its owning snippet actually executes, so without this, ITEM/U2/U3/U4
        # (all ALIAS(*,X)) are missing these 8 labels at compile-dump time.
        # The $0 guard means the assignment body never runs, so this creates
        # the UEL without creating a TM_RESULT record.
        # TODO: shrink to a smaller assignment
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  TM_RESULT('TM_GDP-REF',R,T)$0 = 1;
  TM_RESULT('TM_GDP-ACT',R,T)$0 = 1;
  TM_RESULT('TM_PRD-Y',R,T)$0   = 1;
  TM_RESULT('TM_CON-C',R,T)$0   = 1;
  TM_RESULT('TM_CAP-K',R,T)$0   = 1;
  TM_RESULT('TM_INV-I',R,T)$0   = 1;
  TM_RESULT('TM_ESCOST',R,T)$0  = 1;
  TM_RESULT('TM_GDPLOS',R,T)$0  = 1;
""",
        )

        self.tc.enqueue(self.exec4)

    def exec_loop(
        self: RptExtMlf,
        sysprefix: str,
        model_name: str,
        method: str,
        v: str,
        pgprim: str,
        sow: str,
        rtp_ffcs_defined: bool,
        stages: str,
        etl: str,
        capjd: str,
        capwd: str,
        var: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        invlif: str,
        anncost: str,
        tpulse: str,
        is_vnret_defined: bool,
        varv: str,
        sws: str,
        mx: str,
        varm: str,
        is_obj_combal_defined: bool,
        vart: str,
        micro: str,
        is_mi_agc_defined: bool,
        bencost: str,
        discshift: float,
    ) -> None:
        include_sol_flo_red = sol_flo_red(
            arg1="PAR_FLO",
            arg2="",
            arg3=".L",
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
        )
        include_rpt_obj = rpt_obj_rpt(
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
            timesed=timesed,
            obj=obj,
            varcost=varcost,
            vnret_defined=vnret_defined,
            varv=varv,
            varm=varm,
            sws=sws,
            pgprim=pgprim,
            bencost=bencost,
            discshift=discshift,
        )
        include_cost_ann = cost_ann_rpt(
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
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  DOITER=1-INF$(DOITER=NA);
  LOOP(NITER$DOITER,
*   Perform Negishi iterations with tax rebate
*-----------------------------------------------------------------------
*   Calculation of annual costs and commodity marginals
    OPTION CLEAR=PAR_FLO,CLEAR=PAR_IRE;
{include_sol_flo_red}
{sol_ire_rpt(v=v, sow=sow, mx=mx, rtp_ffcs_defined=rtp_ffcs_defined)}
    OPTION CLEAR=CST_PVP,CLEAR=CST_ACTC,CLEAR=CST_INVC,CLEAR=CST_INVX,CLEAR=CST_FIXC,CLEAR=CST_FIXX;
    OPTION CLEAR=CAP_NEW,CLEAR=CST_FLOC,CLEAR=CST_FLOX,CLEAR=CST_COMC,CLEAR=CST_COMX,CLEAR=CST_IREC;
{include_rpt_obj}
{include_cost_ann}
*-----------------------------------------------------------------------
*   Calculate new Negishi weights
    IF(CARD(MR)-MIN(0,DOITER),
      TM_NWTIT(NITER,MR) = TM_NWT(MR);
      MY_ARRAY(PP) = ABS(EQ_TRDBAL.M(PP));
      TM_NWT(MR(R)) = SUM(PP, MY_ARRAY(PP)*(VAR_C.L(R,PP)+VAR_NTX.L(R,PP)));
      Z = SUM(MR(R), TM_NWT(R));
      IF(Z>0, TM_NWT(MR) = TM_NWT(MR) / Z);
      IF(CARD(MR)=1, Z=0; ELSE Z = SUM(MR, ABS(TM_NWTIT(NITER,MR)-TM_NWT(MR))));
      F=TM_DEFVAL('NEGTOL'); IF(ORD(NITER)=1, F=F*(1+LOG(10**.1)) ELSE F=ABS(F));
*     Calculate rebate of tax revenues
      RB(MR(R),T)=TM_TAXREV(R,T);
      TM_TAXREV(MR(R),PP(T)) = REG_ACOST(R,T,'INVX')+REG_ACOST(R,T,'FIXX')+REG_ACOST(R,T,'VARX');
      DFUNC = SMAX(MR(R),TM_SCALE_CST*SUM(PP(T),COEF_PVT(R,T)*ABS(TM_TAXREV(R,T)-RB(R,T)))/SUM(PP(T),COEF_PVT(R,T)*VAR_EC.L(R,T)*TM_HDF(R,T)));
      DISPLAY "Negishi Tolerance, Negishi Gap, Tax Gap:",F,Z,DFUNC;
      DOITER=(MAX(Z,DFUNC)>=F+MIN(0,DOITER));
      IF(DOITER, SOLVE {model_name} MAXIMIZING VAR_UTIL USING {method};
        {self.tc.model_status_GP.name} = {model_name}.MODELSTAT)
    ELSE DOITER=0));
""",
        )

    def exec1(self: RptExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  VDA_DISC(MR,T) = ABS(-EQ_ENSCST.M(MR,T) * TM_SCALE_CST);
  VDA_DISC(MR,T)$(NOT RT_PP(MR,T)) = COEF_PVT(MR,T);
  LOOP(MIYR_1(TT(T-1)),VDA_DISC(R,TT)$(VDA_DISC(R,TT) LE 0) = COEF_PVT(R,TT)/COEF_PVT(R,T)*VDA_DISC(R,T));
  VAR_OBJ.L(R,OBV(OBVANN),CUR)=0;
* Trade prices and implied costs/revenues
  PAR_IPRIC(MR(R),PP(T),P,C,TS,IE)$PAR_IPRIC(R,T,P,C,TS,IE) = -PAR_IPRIC(R,T,P,C,TS,IE)*COEF_PVT(R,T)/VDA_DISC(R,T);
  CST_IREC(RTP_VINTYR(MR(R),V,PP(T),P),C)$(RPC(R,P,C)$RP_IRE(R,P)) $=
     SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'IN')),PAR_IPRIC(R,T,P,C,S,IE)*PAR_IRE(R,V,T,P,C,S,IE));
  REG_ACOST(MR(R),PP(T),'IRE') =  SUM((VNT(V,T),P,C)$CST_IREC(R,V,T,P,C),CST_IREC(R,V,T,P,C));
""",
        )

    def exec2(self: RptExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  TM_UDF(R,T)=COEF_PVT(R,T);
  COEF_PVT(RT_PP(MR,T)) = -VDA_DISC(MR,T);
""",
        )

    def exec3(self: RptExtMlf, dam_cost_defined: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  VAR_UTIL.UP = INF;
  PAR_NCAPM(RTP(R,T,P))$(VAR_NCAP.M(RTP)*COEF_OBJINV(RTP)) = VAR_NCAP.M(RTP)*TM_UDF(R,T)/COEF_PVT(R,T)/COEF_OBJINV(RTP);
*-----------------------------------------------------------------------
* Discounted objective values by cost type(INV, FIX, VAR etc.)
*-----------------------------------------------------------------------
* Discounted objective value by region
  REG_WOBJ(R,'INV',CUR)  = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'INV'));
  REG_WOBJ(R,'INVX',CUR) = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'INVX'));
  REG_WOBJ(R,'FIX',CUR)  = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'FIX'));
  REG_WOBJ(R,'FIXX',CUR) = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'FIXX'));
  REG_WOBJ(R,'VAR',CUR)  = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'VAR'));
  REG_WOBJ(R,'VARX',CUR) = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'VARX'));
  REG_WOBJ(R,'ELS',CUR)  = SUM(T, OBJ_PVT(R,T,CUR)*REG_ACOST(R,T,'ELS'));
{"REG_WOBJ(R,'DAM',CUR)  = VAR_OBJ.L(R,'OBJDAM',CUR);" if dam_cost_defined else ""}
  REG_IREC(R) = SUM(T,TM_UDF(R,T)*REG_ACOST(R,T,'IRE'));
  REG_OBJ(R) = SUM((ITEM,RDCUR(R,CUR))$REG_WOBJ(R,ITEM,CUR), REG_WOBJ(R,ITEM,CUR));
  OBJz.L = SUM(R,REG_OBJ(R));
""",
        )

    def exec4(self: RptExtMlf) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  OPTION CLEAR=F_INOUT, CLEAR=F_INOUTS, CLEAR=F_IOSET;

*---------------------------------------------------------------------
* Report parameters for TIMES-MACRO
*---------------------------------------------------------------------

  PAR_Y(MR(R),T(TB))  = TM_Y0(R);   PAR_Y(MR(R),PP(T)) = VAR_C.L(R,T) + VAR_INV.L(R,T) + VAR_EC.L(R,T) + VAR_NTX.L(R,T);
  TM_GDP(MR(R),T(TB)) = TM_GDP0(R); TM_GDP(MR(R),PP(T)) = VAR_C.L(R,T) + VAR_INV.L(R,T) + VAR_NTX.L(R,T);

* Reporting parameters
  TM_RESULT('TM_GDP-REF',MR,T) = TM_GDPGOAL(MR,T);
  TM_RESULT('TM_GDP-ACT',MR,T) = TM_GDP(MR,T);
  TM_RESULT('TM_PRD-Y',MR,T)   = PAR_Y(MR,T);
  TM_RESULT('TM_CON-C',MR,T)   = VAR_C.L(MR,T);
  TM_RESULT('TM_CAP-K',MR,T)   = VAR_K.L(MR,T);
  TM_RESULT('TM_INV-I',MR,T)   = VAR_INV.L(MR,T);
  TM_RESULT('TM_ESCOST',MR,T)  = VAR_EC.L(MR,T);
  TM_RESULT('TM_GDPLOS',MR,T) = 100*(TM_GDPGOAL(MR,T)-TM_GDP(MR,T))/TM_GDPGOAL(MR,T);
  DISPLAY TM_RESULT;
""",
        )
