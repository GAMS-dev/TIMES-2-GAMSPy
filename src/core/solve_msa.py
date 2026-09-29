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

from gamspy import Domain, Else, If, Loop, Model, Ord, Parameter, Set, Smax
from gamspy.math import Max, abs, aggregate

from core.base_class import GamsClass
from core.clearsol_stp import clearsol_stp
from core.ddfupd_msa import ddfupd_msa, ddfupd_msa_GP
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
        self.tc.enqueue(self.comp1_seed)

        if self.env.msa.upper() == "MSA":
            # POLICY
            self.tc.enqueue(self.exec_policy)
        else:
            self.tc.enqueue(self.exec2)
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
        g = self.tc
        m = g.container
        # ABORT$EXECERROR and SOLPRINT/SOLVELINK/DECIMALS are GAMS
        # constructs with no GAMSPy equivalent reachable outside a native
        # SOLVE (GAMSPy runs every SOLVE as its own GAMS job, so neither an
        # ABORT nor an OPTION statement here can reach it -- see
        # solve_stp.py's BRATIO/SOLVEOPT note; every other ABORT in this
        # codebase is likewise left raw). Emitted verbatim to keep the
        # generated source in step with solve.msa.
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* Abort execution if execute errors
  ABORT$EXECERROR '*** ERRORS IN EXECUTION ***'

  OPTION SOLPRINT = OFF;
  OPTION SOLVELINK = 1;
  OPTION DECIMALS = 5;
""",
        )

        equations = [
            g.eq_util,
            g.eq_conso,
            g.eq_prod_y,
            g.eq_mcap,
            g.eq_tmc,
            g.eq_dd,
            g.eq_ivecbnd,
            g.eq_escost,
            g.eq_trdbal,
        ]
        if is_tm_catt_defined:
            equations += [
                g.eq_ccdm,
                g.eq_clitot,
                g.eq_cliconc,
                g.eq_clitemp,
                g.eq_clibeoh,
            ]
        g.mce = Model(
            m,
            name="MCE",
            equations=equations,
            problem="NLP",
            sense="MAX",
            objective=g.VAR_UTIL,
        )
        # MCE.MODELSTAT/.SOLVESTAT/.OPTFILE are GAMS model suffixes with no
        # GAMSPy equivalent (status/solve_status are read-only post-solve
        # outputs, and optfile has no per-model setter) -- emitted verbatim
        # to keep the generated source in step with solve.msa.
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="MCE.MODELSTAT=0; MCE.SOLVESTAT=0; MCE.OPTFILE=1;",
        )

        g.loops = Set(m, name="LOOPS", records=["NWT", "DDF", "GDP"])
        g.gdploss = Parameter(
            m,
            name="GDPLOSS",
            domain=[g.miter, g.Reg, g.tp],
            description="GDP losses in percent",
        )
        g.msa_err = Parameter(
            m, name="MSA_ERR", domain=[g.miter, g.niter, g.loops, g.Reg]
        )
        g.tm_tol = Parameter(
            m,
            name="TM_TOL",
            domain=[g.item],
            records=[
                ("CAL", 7e-07),
                ("MST", 1e-05),
                ("BND", 0.5),
                ("TIG", 0.6),
                ("DEM", 0),
                ("EQUIL", 1),
            ],
        )
        g.errdem = Parameter(m, name="ERRDEM", records=0)
        g.errgdp = Parameter(m, name="ERRGDP", records=0)
        g.tm_cal = Parameter(m, name="TM_CAL", records=1)
        g.doiter = Parameter(m, name="DOITER", records=1)

    def comp1_seed(self: SolveMsa) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
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
        g = self.tc
        g.tm_growv[g.r, g.t] = g.tm_gr[g.r, g.t]
        g.par_grgdp[g.r, g.t] = g.tm_gr[g.r, g.t]
        g.par_mc[g.r, g.t, g.Dm].where[g.tm_dem[g.r, g.t, g.Dm]] = g.tm_dmc[
            g.r, g.t, g.Dm
        ]
        g.doiter[...] = 1.0
        # SOLVEOPT/LIMROW/BRATIO are GAMS solve options with no GAMSPy
        # equivalent reachable from a native SOLVE (GAMSPy runs every SOLVE
        # as its own GAMS job, so an OPTION statement here can't reach it --
        # see solve_stp.py's BRATIO/SOLVEOPT note). Emitted verbatim to keep
        # the generated source in step with solve.msa.
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="OPTION SOLVEOPT=MERGE,LIMROW=0,BRATIO=0.25;",
        )
        with Loop(g.niter.where[g.doiter]):
            ddfupd_msa_GP(g)
            with If(Ord(g.niter) < 5.0):
                with Loop(g.Mreg):
                    g.Mr[g.r] = False
                    g.Mr[g.r[g.Mreg]] = True
                    g.mce.solve()
                g.Mr[g.r[g.Mreg]] = True
            with Else():
                g.mce.solve()
            g.tm_gdp[g.r, g.t] = g.VAR_C.l[g.r, g.t] + g.VAR_INV.l[g.r, g.t]
            g.par_grgdp[g.Mr[g.r], g.tp[g.t - 1]] = 100.0 * (
                ((g.tm_gdp[g.r, g.t] / g.tm_gdp[g.r, g.tp]) ** (1.0 / g.nyper[g.tp]))
                - 1.0
            )
            g.par_y[g.r, g.t] = g.VAR_Y.l[g.r, g.t]
            g.par_mc[g.Mr[g.r], g.Pp[g.t], g.c].where[g.tm_dem[g.r, g.t, g.c]] = (
                Max(
                    abs(g.VAR_SP.m[g.r, g.t, g.c] * g.tm_scale_nrg),
                    abs(g.eq_dd.m[g.r, g.t, g.c]),
                )
                / Max(g.eq_escost.m[g.r, g.t], -g.VAR_EC.m[g.r, g.t])
                / g.tm_scale_cst
            )
            g.msa_err["1", g.niter, "DDF", g.Mr[g.r]] = Smax(
                Domain(g.t, g.c).where[g.tm_dem[g.r, g.t, g.c]],
                abs(g.tm_dem[g.r, g.t, g.c] - g.VAR_DEM.l[g.r, g.t, g.c])
                / g.tm_dem[g.r, g.t, g.c],
            )
            g.msa_err["1", g.niter, "GDP", g.Mr[g.r]] = Smax(
                g.t,
                abs(g.tm_gdpgoal[g.r, g.t] - g.tm_gdp[g.r, g.t])
                / g.tm_gdpgoal[g.r, g.t],
            )
            g.errdem[...] = Smax(g.Mr, g.msa_err["1", g.niter, "DDF", g.Mr])
            g.errgdp[...] = Smax(g.Mr, g.msa_err["1", g.niter, "GDP", g.Mr])
            with If(Max(g.errdem, g.errgdp) < g.tm_tol["CAL"] * Ord(g.niter)):
                g.doiter[...] = 0.0
        print(g.msa_err.records)
        g.tm_ddf_dm[g.Mr, g.tp, g.Dm].where[g.tm_dem[g.Mr, g.tp, g.Dm]] = (
            1.0 - g.VAR_DEM.l[g.Mr, g.tp, g.Dm] / g.tm_dem[g.Mr, g.tp, g.Dm]
        ) * 100.0
        aggregate(source=g.tm_ddf_dm, target=g.tm_dd)
        print(f"estimated to assumed demand difference in percent {g.tm_dd.records}")
        g.tm_tol["DEM"] = g.errdem
        g.tm_tol["GDP"] = g.errgdp

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
