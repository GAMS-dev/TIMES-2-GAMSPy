# solve_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Solve.MSA is the wrapper for solving the soft-linked standalone MACRO
# *   arg1 - mod or v# for the source code to be used

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.clearsol_stp import clearsol_stp
from core.ddfupd_msa import ddfupd_msa
from core.preppm_msa import preppm_msa_label_tolp
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.solprep_msa import solprep_msa
from core.writeddf_msa import writeddf_msa

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolveMsa(GamsClass):
    """Translation unit for solve.msa."""

    # Instance attributes
    module_name: str = "solve_msa"
    gams_source: str = "solve.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        if self.env.msa == "CSA":
            self.tc.enqueue(self.exec_tm_ycheck)

        self.comp1(is_tm_catt_defined=self.tc.defined("TM_CATT"))

        if self.env.msa.upper() == "MSA":
            # POLICY
            self.tc.enqueue(
                self.exec_policy,
            )
        else:
            self.tc.enqueue(
                self.exec2,
            )
            if self.env.objann.upper() != "YES":
                pass
            else:
                self.tc.enqueue(
                    self.exec3,
                    model_name=self.env.model_name,
                    msa=self.env.msa,
                    v=self.env.v,
                    pgprim=self.env.pgprim,
                    sow=self.env.sow,
                    rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                    stages=self.env.stages,
                    etl=self.env.etl,
                    invlif=self.env.invlif,
                    anncost=self.env.anncost,
                    mx=self.env.mx,
                    sysprefix=self.env.sysprefix,
                    tpulse=self.env.tpulse,
                    is_vnret_defined=self.tc.defined("VNRET"),
                    varv=self.env.varv,
                    sws=self.env.sws,
                    varm=self.env.varm,
                    is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
                    var=self.env.var,
                    vart=self.env.vart,
                    micro=self.env.micro,
                    is_mi_agc_defined=self.tc.defined("MI_AGC"),
                    capjd=self.env.capjd,
                    capwd=self.env.capwd,
                    timesed=self.env.timesed,
                    obj=self.env.obj,
                    varcost=self.env.varcost,
                    vnret_defined=self.tc.defined("VNRET"),
                    is_tm_catt_defined=self.tc.defined("TM-CATT"),
                    is_dam_cost_defined=self.tc.defined("DAM_COST"),
                    cli=self.env.cli,
                    solveda=self.env.solveda,
                    scum=self.env.scum,
                    sw_notags=self.env.sw_notags,
                    objann=self.env.objann,
                    dflbl=self.env.dflbl,
                    bencost=self.env.bencost,
                    discshift=self.env.discshift,
                )

        # NEGISHI
        self.tc.enqueue(
            self.exec_negishi_iteration,
            msa=self.env.msa,
            model_name=self.env.model_name,
            is_tm_catt_defined=self.tc.defined("TM_CATT"),
            var=self.env.var,
            sow=self.env.sow,
            eq=self.env.eq,
            swt=self.env.swt,
            cli=self.env.cli,
            abs_=self.env.abs,
            macro=self.env.macro,
            stages=self.env.stages,
            v=self.env.v,
            mx=self.env.mx,
            pgprim=self.env.pgprim,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            etl=self.env.etl,
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            sysprefix=self.env.sysprefix,
            tpulse=self.env.tpulse,
            is_vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv,
            sws=self.env.sws,
            varm=self.env.varm,
            is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            vart=self.env.vart,
            micro=self.env.micro,
            is_mi_agc_defined=self.tc.defined("MI_AGC"),
            capjd=self.env.capjd,
            capwd=self.env.capwd,
            timesed=self.env.timesed,
            obj=self.env.obj,
            varcost=self.env.varcost,
            vnret_defined=self.tc.defined("VNRET"),
            is_dam_cost_defined=self.tc.defined("DAM_COST"),
            solveda=self.env.solveda,
            scum=self.env.scum,
            sw_notags=self.env.sw_notags,
            objann=self.env.objann,
            dflbl=self.env.dflbl,
            bencost=self.env.bencost,
            discshift=self.env.discshift,
        )

        self.env.set_scoped("solveda", "1")
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(arg4=("NO",)),
            )
        )

        if self.env.qsf.upper() == "YES":
            self.tc.enqueue(
                self.exex_solprep_msa,
                msa=self.env.msa,
                v=self.env.v,
                pgprim=self.env.pgprim,
                sow=self.env.sow,
                rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                stages=self.env.stages,
                etl=self.env.etl,
                invlif=self.env.invlif,
                anncost=self.env.anncost,
                sysprefix=self.env.sysprefix,
                mx=self.env.mx,
                tpulse=self.env.tpulse,
                is_vnret_defined=self.tc.defined("VNRET"),
                varv=self.env.varv,
                sws=self.env.sws,
                varm=self.env.varm,
                var=self.env.var,
                vart=self.env.vart,
                micro=self.env.micro,
                capjd=self.env.capjd,
                capwd=self.env.capjd,
                timesed=self.env.timesed,
                obj=self.env.obj,
                varcost=self.env.varcost,
                cli=self.env.cli,
                solveda=self.env.solveda,
                scum=self.env.scum,
                sw_notags=self.env.sw_notags,
                objann=self.env.objann,
                dflbl=self.env.dflbl,
                bencost=self.env.bencost,
                discshift=self.env.discshift,
            )

        if self.env.msa.upper() != "CSA":
            return

        self.tc.enqueue(self.exec_calc_ivetol)

        self.tc.enqueue(self.exex_writeddf_msa)

    def exex_writeddf_msa(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=writeddf_msa(arg1="MSADDF", arg2="PAR_GRGDP"),
        )

    def exex_solprep_msa(
        self: SolveMsa,
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
        var: str,
        vart: str,
        micro: str,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        cli: str,
        solveda: str,
        scum: str,
        sw_notags: str,
        mx: str,
        objann: str,
        dflbl: str,
        bencost: str,
        discshift: float,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=solprep_msa(
                arg1="OUT",
                arg2="",
                msa=msa,
                v=v,
                pgprim=pgprim,
                sow=sow,
                rtp_ffcs_defined=rtp_ffcs_defined,
                stages=stages,
                etl=etl,
                mx=mx,
                invlif=invlif,
                anncost=anncost,
                sysprefix=sysprefix,
                tpulse=tpulse,
                is_vnret_defined=is_vnret_defined,
                varv=varv,
                sws=sws,
                varm=varm,
                is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
                var=var,
                vart=vart,
                micro=micro,
                is_mi_agc_defined=self.tc.defined("MI_AGC"),
                capjd=capjd,
                capwd=capwd,
                timesed=timesed,
                obj=obj,
                varcost=varcost,
                vnret_defined=self.tc.defined("VNRET"),
                is_tm_catt_defined=self.tc.defined("TM-CATT"),
                is_dam_cost_defined=self.tc.defined("DAM_COST"),
                cli=cli,
                solveda=solveda,
                scum=scum,
                sw_notags=sw_notags,
                objann=objann,
                dflbl=dflbl,
                bencost=bencost,
                discshift=discshift,
            ),
        )

    def exec_tm_ycheck(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="TM_YCHECK(R) = TM_IVETOL(R); TM_IVETOL(R)=MAX(1,TM_IVETOL(R));",
        )

    def comp1(self: SolveMsa, is_tm_catt_defined: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
* Abort execution if execute errors
  ABORT$EXECERROR '*** ERRORS IN EXECUTION ***'

  OPTION SOLPRINT = OFF;
  OPTION SOLVELINK = 1;
  OPTION DECIMALS = 5;

  MODEL MCE  /  EQ_UTIL, EQ_CONSO, EQ_PROD_Y, EQ_MCAP, EQ_TMC, EQ_DD, EQ_IVECBND, EQ_ESCOST, EQ_TRDBAL
{"EQ_CCDM, EQ_CLITOT, EQ_CLICONC, EQ_CLITEMP, EQ_CLIBEOH" if is_tm_catt_defined else ""}
  /;
  MCE.MODELSTAT=0; MCE.SOLVESTAT=0; MCE.OPTFILE=1;

  SET LOOPS / NWT, DDF, GDP /;
  PARAMETER GDPLOSS(MITER,REG,tp) 'GDP losses in percent';
  PARAMETER MSA_ERR(MITER,NITER,LOOPS,REG);
  PARAMETER TM_TOL(ITEM) / CAL 7E-7, MST 1E-5, BND 0.5, TIG 0.6, DEM 0, EQUIL 1 /;
  SCALAR ERRDEM / 0 /, ERRGDP / 0 /, TM_CAL / 1 /, DOITER/ 1 /;
  TM_GDP(MR(R),T) = TM_GDPGOAL(R,T);
  PAR_Y(R,T)      = TM_GDPGOAL(R,T);
  TM_NWT(MR) = 1;
""",
        )

    def exec_policy(self: SolveMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Get initial solution
  TM_CAL=0;
  OPTION SOLVEOPT=MERGE;
  LOOP(MREG, MR(R)= NO; MR(R(MREG))=YES; SOLVE MCE MAXIMIZING VAR_UTIL USING NLP);
  MR(R(MREG))=YES;
""",
        )

    def exec2(self: SolveMsa) -> None:
        include_ddfupd = ddfupd_msa()
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  TM_GROWV(R,T)  = TM_GR(R,T);
  PAR_GRGDP(R,T) = TM_GR(R,T);
  PAR_MC(R,T,DM)$TM_DEM(R,T,DM) = TM_DMC(R,T,DM);

  DOITER=1;
  OPTION SOLVEOPT=MERGE,LIMROW=0,BRATIO=0.25;

  LOOP(NITER$DOITER,

{include_ddfupd}

   IF(ORD(NITER)<5,
     LOOP(MREG, MR(R)= NO; MR(R(MREG))=YES;
        SOLVE MCE MAXIMIZING VAR_UTIL USING NLP); MR(R(MREG))=YES;
   ELSE SOLVE MCE MAXIMIZING VAR_UTIL USING NLP);

   TM_GDP(R,T) = VAR_C.L(R,T) + VAR_INV.L(R,T);
   PAR_GRGDP(MR(R),TP(T-1)) = 100 * ((TM_GDP(R,T)/TM_GDP(R,TP))**(1/NYPER(TP))-1);
   PAR_Y(R,T) = VAR_Y.L(R,T);
   PAR_MC(MR(R),PP(T),C)$TM_DEM(R,T,C) = MAX(ABS(VAR_SP.M(R,T,C)*TM_SCALE_NRG),ABS(EQ_DD.M(R,T,C))) / MAX(EQ_ESCOST.M(R,T),-VAR_EC.M(R,T)) / TM_SCALE_CST;

   MSA_ERR('1',NITER,'DDF',MR(R)) = SMAX((T,C)$TM_DEM(R,T,C),ABS(TM_DEM(R,T,C)-VAR_DEM.L(R,T,C))/TM_DEM(R,T,C));
   MSA_ERR('1',NITER,'GDP',MR(R)) = SMAX(T,ABS(TM_GDPGOAL(R,T)-TM_GDP(R,T))/TM_GDPGOAL(R,T));
   ERRDEM = SMAX(MR, MSA_ERR('1',NITER,'DDF',MR));
   ERRGDP = SMAX(MR, MSA_ERR('1',NITER,'GDP',MR));
   IF(MAX(ERRDEM,ERRGDP) < TM_TOL('CAL')*ORD(NITER), DOITER=0);
  );

  DISPLAY MSA_ERR;
  TM_DDF_DM(MR,TP,DM)$TM_DEM(MR,TP,DM)=(1-VAR_DEM.L(MR,TP,DM)/TM_DEM(MR,TP,DM))*100;
  OPTION TM_DD < TM_DDF_DM;
  DISPLAY 'estimated to assumed demand difference in percent', TM_dd;
  TM_TOL('DEM') = ERRDEM;
  TM_TOL('GDP') = ERRGDP;
""",
        )

    def exec3(
        self: SolveMsa,
        model_name: str,
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
        dflbl: str,
        bencost: str,
        mx: str,
        discshift: float,
    ) -> None:
        include_solprep = solprep_msa(
            arg1="",
            arg2="",
            msa=msa,
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
            stages=stages,
            etl=etl,
            mx=mx,
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
            vart=vart,
            micro=micro,
            is_mi_agc_defined=is_mi_agc_defined,
            capjd=capjd,
            capwd=capwd,
            timesed=timesed,
            obj=obj,
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
            bencost=bencost,
            discshift=discshift,
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Update discounting factors
  TM_CAL = 2;
  LOOP(PP(T-1),OBJ_PVT(MR(R),T,CUR) = OBJ_PVT(R,PP,CUR)*EQ_ESCOST.M(R,T)/EQ_ESCOST.M(R,PP));
  COEF_PVT(MR(R),T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR));
  OPTION SOLVEOPT=REPLACE,LIMROW=0,BRATIO=1;
  SOLVE {model_name} MINIMIZING objZ USING LP;
{include_solprep}
""",
        )

    def exec_negishi_iteration(
        self: SolveMsa,
        msa: str,
        model_name: str,
        is_tm_catt_defined: bool,
        var: str,
        sow: str,
        eq: str,
        swt: str,
        cli: str,
        abs_: str,
        macro: str,
        stages: str,
        v: str,
        pgprim: str,
        rtp_ffcs_defined: bool,
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
        vart: str,
        micro: str,
        is_mi_agc_defined: bool,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        is_dam_cost_defined: bool,
        solveda: str,
        scum: str,
        mx: str,
        sw_notags: str,
        objann: str,
        dflbl: str,
        bencost: str,
        discshift: float,
    ) -> None:
        include_clearsol_stp = clearsol_stp(
            var=var,
            sow=sow,
            eq=eq,
            swt=swt,
            cli=cli,
            abs_=abs_,
            macro=macro,
            stages=stages,
        )
        include_solprep = solprep_msa(
            arg1="",
            arg2="",
            msa=msa,
            v=v,
            pgprim=pgprim,
            sow=sow,
            rtp_ffcs_defined=rtp_ffcs_defined,
            stages=stages,
            etl=etl,
            invlif=invlif,
            mx=mx,
            anncost=anncost,
            sysprefix=sysprefix,
            tpulse=tpulse,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            is_obj_combal_defined=is_obj_combal_defined,
            var=var,
            vart=vart,
            micro=micro,
            is_mi_agc_defined=is_mi_agc_defined,
            capjd=capjd,
            capwd=capwd,
            timesed=timesed,
            obj=obj,
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
            bencost=bencost,
            discshift=discshift,
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Prepare Negishi iterations

* Calculate initial Negishi weights as in MERGE, e.g. based on the regional GDP
  TM_NWT(MR(R)) = SUM(TP, TM_GDPGOAL(R,TP)*TM_DFACT(R,TP));
  Z = SUM(MR(R),TM_NWT(R));
  TM_NWT(MR(R)) = TM_NWT(R) / Z;
  OPTION CLEAR=MSA_ERR;

* Relax trades
  VAR_NTX.UP(MR,PP,TRD) = INF;
  VAR_NTX.LO(MR,PP,TRD) = -INF;
  RT_PP(R,T)$(NOT NO_RT(R,T)) = YES;
  DOITER=1; ERRDEM=0.8;

  LOOP(MITER$DOITER,
*   Heuristic tightening of demand bounds
    TM_TOL('BND')=MIN(TM_TOL('BND'),ERRDEM);
    IF(NOT TM_CAL,
      VAR_DEM.LO(RT_PP(MR(R),T),C)$((TM_DDATPREF(R,C)>0)$TM_DEM(R,T,C)) = TM_DEM(R,T,C)*(1-TM_TOL('BND')*TM_TOL('TIG'));
      VAR_DEM.UP(RT_PP(MR(R),T),C)$((TM_DDATPREF(R,C)>0)$TM_DEM(R,T,C)) = TM_DEM(R,T,C)*(1+TM_TOL('BND')*TM_TOL('TIG'));
    );
   LOOP(NITER$DOITER,

    OPTION BRATIO=0.25,SOLVEOPT=REPLACE;
    SOLVE MCE MAXIMIZING VAR_UTIL USING NLP;

*-- Calculate Macro parameters
    EQ_TRDBAL.M(PP,TRD) = EQ_TRDBAL.M(PP,"NMR");
    VAR_NTX.L(MR,PP,TRD('IRE')) = -REG_ACOST(MR,PP,TRD)*TM_SCALE_CST;
    TM_GDP(MR(R),PP) = VAR_C.L(R,PP)+VAR_INV.L(R,PP) + SUM(TRD, ABS(EQ_TRDBAL.M(PP,TRD)/EQ_TRDBAL.M(PP,"NMR"))*VAR_NTX.L(R,PP,TRD));
    PAR_GRGDP(MR(R),tp(T-1)) = 100 * ((TM_GDP(R,T)/TM_GDP(R,TP))**(1/NYPER(TP))-1);
    PAR_Y(R,T) = VAR_Y.L(R,T);
    PAR_MC(MR(R),PP(T),C)$TM_DEM(R,T,C) = MAX(ABS(VAR_SP.M(R,T,C)*TM_SCALE_NRG),ABS(EQ_DD.M(R,T,C))) / MAX(EQ_ESCOST.M(R,T),-VAR_EC.M(R,T)) / TM_SCALE_CST;
    MSA_ERR(MITER,NITER,'DDF',MR(R)) = SMAX((T,C)$TM_DEM(R,T,C),ABS(TM_DEM(R,T,C)-VAR_DEM.L(R,T,C))/TM_DEM(R,T,C));
    MSA_ERR(MITER,NITER,'GDP',MR(R)) = SMAX(T,ABS(TM_GDPGOAL(R,T)-TM_GDP(R,T))/TM_GDPGOAL(R,T));
    ERRDEM = SMAX(MR, MSA_ERR(MITER,NITER,'DDF',MR)); DISPLAY ERRDEM;
    ERRGDP = SMAX(MR, MSA_ERR(MITER,NITER,'GDP',MR));
    DFUNC = ((ERRGDP>1.5*TM_TOL('GDP'))+(ERRDEM>1.5*TM_TOL('DEM')))*(MAX(ERRDEM,ERRGDP)>TM_TOL('MST'))$TM_CAL;

*-- Calculate deflators and new Negishi weights
    LOOP(TB(T-1), TM_PVPI(TRD,PP) = ABS(EQ_TRDBAL.M(PP,TRD)/EQ_TRDBAL.M(T,"NMR")));
    TM_NWT(MR(R)) = SUM(PP,TM_PVPI("NMR",PP)*VAR_C.L(R,PP) + SUM(TRD, TM_PVPI(TRD,PP)*VAR_NTX.L(R,PP,TRD)));
    TM_NWT(MR) = TM_NWT(MR) / SUM(REG, TM_NWT(REG));
    TM_NWTIT(NITER,MR) = TM_NWT(MR);
    IF(CARD(MR)=1, TM_TOL('EQUIL')=0;
    ELSE TM_TOL('EQUIL') = SUM(MR, ABS(TM_NWTIT(NITER-1,MR) - TM_NWT(MR))));
    MSA_ERR(MITER,NITER,'NWT',MR) = TM_TOL('EQUIL');
    IF((TM_CAL=1)$DFUNC, TM_TOL('EQUIL')=1; DFUNC=0);
    IF(TM_TOL('EQUIL') LE TM_TOL('MST') OR ORD(NITER)=CARD(NITER), DOITER=0);

    IF(DOITER+DFUNC,
*-- Recalibrate DDF factors
{ddfupd_msa() if msa.upper() == "CSA" else ""}
    ));

   GDPLOSS(MITER,MR,TP)= 100*(TM_GDPGOAL(MR,TP)-TM_GDP(MR,TP))/TM_GDPGOAL(MR,TP);
   TM_DDF_DM(MR,TP,DM)$TM_DEM(MR,TP,DM)=(VAR_DEM.L(MR,TP,DM)/TM_DEM(MR,TP,DM));
   OPTION TM_DD < TM_DDF_DM;
*  DISPLAY 'Demand ratio VAR_DEM/TM_DEM', TM_dd;
   IF(TM_CAL=2, DOITER=DFUNC; ELSEIF NOT TM_CAL, DOITER=ROUND(ERRDEM/CARD(MR),5)>3*TM_TOL('MST'));
{preppm_msa_label_tolp() if is_tm_catt_defined else ""}
   IF(DOITER$(ORD(MITER) < CARD(MITER)),
*     Update either demands or PVT factors
      IF(NOT TM_CAL,OPTION CLEAR=RCJ; COM_PROJ(MR(R),PP(T),C)$TM_DEM(R,T,C) = COM_PROJ(R,T,C)+VAR_DEM.L(R,T,C)-TM_DEM(R,T,C);
      ELSEIF TM_CAL=2,LOOP(PP(T-1),OBJ_PVT(MR(R),T,CUR) = OBJ_PVT(R,PP,CUR)*EQ_ESCOST.M(R,T)/EQ_ESCOST.M(R,PP));
         COEF_PVT(MR(R),T) = SUM(G_RCUR(R,CUR),OBJ_PVT(R,T,CUR)) DISPLAY "UDF updated";);
      OPTION BRATIO=1;
{include_clearsol_stp}
      OPTION SOLVEOPT=MERGE;
      SOLVE {model_name} MINIMIZING objZ USING LP;
{include_solprep}
    );
  );
  OPTION MSA_ERR:6:3:1;
  DISPLAY MSA_ERR,GDPLOSS,ERRDEM,ERRGDP;
""",
        )

    def exec_calc_ivetol(self: SolveMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Calculate IVETOL for policy run
  TM_IVETOL(MR(R)) = MAX(TM_YCHECK(R),SMAX(PP$(TM_L(R,PP)>1),LOG((VAR_INV.L(R,PP)+VAR_EC.L(R,PP))/TM_Y0(R))/LOG(TM_L(R,PP)))+.005);
  PAR_IV(MR(R),T) = VAR_INV.L(R,T);

* Write out final calibrated DDF factors and realized GDP
  OPTION CLEAR=TM_UDF; IF(TM_CAL=2,TM_UDF(MR(R),T)=COEF_PVT(R,T); DISPLAY TM_UDF);
""",
        )
