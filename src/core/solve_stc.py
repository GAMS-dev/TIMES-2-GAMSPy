# solve_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Solve.stc is the wrapper for solving stochastic problems
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.bnd_ucw_mod import bnd_ucw_mod
from core.par_uc_rpt import declare_par_uc_rpt_params
from core.rpt_dam_mod import rpt_dam_mod
from core.rpt_par_cli import rpt_par_cli
from core.rptlite_rpt import (
    SOL_FLO_RED_V_SCOPE,
    RptliteRpt,
    RptliteRptConfig,
    rptlite_rpt,
)
from core.sensis_stc import sensis_stc
from core.solve_mod import solve_mod, solve_mod_GP
from core.utils import apply_v_scope

if TYPE_CHECKING:
    from gamspy import Equation

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolveStc(GamsClass):
    """Translation unit for solve.stc."""

    module_name: str = "solve_stc"
    gams_source: str = "solve.stc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        model_name: str,
        equations: list[Equation],
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.model_name = model_name
        self.equations = equations
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
  SCALAR GDL /0/;
  PARAMETER WHANDLE(ALLSOW) //;
""",
        )

        self.env.set_scoped("solveda", "1")
        if self.env.mca.upper() == "YES":
            self.tc.enqueue(
                self.exec_model_number,
                model_name=self.env.model_name,
                mca1=self.env.mca1,
            )

        if self.env.stages != "YES":
            self.include(
                RptliteRpt(
                    self.tc,
                    self.env,
                    config=RptliteRptConfig(arg1="S", arg2=(self.tc.ww,)),
                )
            )

        # TODO!
        # $IF %OBMAC%==YES
        # $IF NOT %gams.gdir%==%gams.scrdir% GDL=%solvelink.AsyncGrid%;
        # self.container._process_directory?
        gdl_init = ""
        if (
            self.env.obmac == "YES"
            # and self.env.gams_gdir != self.tc.container._process_directory
            and self.env.is_set("gams_gdir")  # Solution for now
        ):
            gdl_init = "GDL=3;"

        if self.env.stages != "YES" and self.env.var_uc != "YES":
            # rptlite_rpt() below embeds par_uc_rpt()'s assignments into "run"-phase code
            declare_par_uc_rpt_params(self.tc)

        # Snapshot V (sol_flo.red:11's SET%4 V VAR) right before the call
        # below, matching sol_flo_red.py's own SolFloRed.compile().
        apply_v_scope(self.env, SOL_FLO_RED_V_SCOPE, self.env.var)

        rptlite_no_code = (
            rptlite_rpt(
                config=RptliteRptConfig(
                    arg1="S", arg2=(self.tc.ww,), arg3=(self.tc.allsow,), arg4="NO"
                ),
                sow=self.env.sow,
                sysprefix=self.env.sysprefix,
                sensis=self.env.sensis,
                var_uc=self.env.var_uc,
                stages=self.env.stages,
                obmac=self.env.obmac,
                abs_=self.env.abs,
                var=self.env.var,
                v=self.env.v,
                pgprim=self.env.pgprim,
                bencost=self.env.bencost,
                rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                etl=self.env.etl,
                mx=self.env.mx,
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
                discshift=self.env.discshift,
                model_name=self.env.model_name,
                eq=self.env.eq,
                rpt_flots=self.env.rpt_flots,
                solans=self.env.solans,
                eqe_ucrtp_defined=self.tc.defined("EQE_UCRTP"),
                eq_g_ucmax_not_defined=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
            )
            if self.env.stages != "YES"
            else ""
        )

        rpt_dam_code = (
            rpt_dam_mod(
                stages=self.env.stages,
                var=self.env.var,
                cli=self.env.cli,
                vart=self.env.vart,
                sws=self.env.sws,
                sow=self.env.sow,
                solveda=self.env.solveda,
                scum=self.env.scum,
            )
            if self.tc.defined("DAM_COST")
            else ""
        )
        rpt_par_cli_loop_code = (
            rpt_par_cli(arg1="LOOP(SOW,", arg2=");") if self.env.cli == "YES" else ""
        )

        async_rpt_par_cli_loop_code = (
            rpt_par_cli(arg1="LOOP(SOW,", arg2=");")
            if self.env.cli.upper() == "YES"
            else ""
        )
        # TODO: rpt_ext_mca.py does not exist
        async_ext_code = ""
        # if self.env.mca.upper() == "YES":
        #     from core.rpt_ext_mca import rpt_ext_mca

        #     async_ext_code = rpt_ext_mca(arg1="MCA", arg2="solve")

        self.tc.enqueue(
            self.exec_main,
            gdl_init=gdl_init,
            stepped_yes=(self.env.stepped == "YES"),
            spines_yes=(self.env.spines.upper() == "YES"),
            stages=self.env.stages,
            swd=self.env.swd,
            var=self.env.var,
            sow=self.env.sow,
            bnd_ucw_defined={
                f"{self.env.var}_UC": self.tc.defined(f"{self.env.var}_UC"),
                f"{self.env.var}_UCR": self.tc.defined(f"{self.env.var}_UCR"),
                f"{self.env.var}_UCT": self.tc.defined(f"{self.env.var}_UCT"),
                f"{self.env.var}_UCRT": self.tc.defined(f"{self.env.var}_UCRT"),
                f"{self.env.var}_UCTS": self.tc.defined(f"{self.env.var}_UCTS"),
                f"{self.env.var}_UCRTS": self.tc.defined(f"{self.env.var}_UCRTS"),
            },
            rptlite_no_code=rptlite_no_code,
            rpt_dam_code=rpt_dam_code,
            rpt_par_cli_loop_code=rpt_par_cli_loop_code,
            solve_now=self.env.solve_now,
            damage=self.env.damage,
            micro=self.env.micro,
            macro=self.env.macro,
            etl=self.env.etl,
            solmip=self.env.solmip,
            mixlp=self.env.mixlp if self.env.is_set("mixlp") else "",
            nonlp=self.env.nonlp if self.env.is_set("nonlp") else "",
            gams_cgi=self.env.gams_cgi if self.env.is_set("gams_cgi") else "",
            memclean=self.env.memclean,
            err_abort=self.env.err_abort,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
            cli=self.env.cli,
            eq=self.env.eq,
            swt=self.env.swt,
            abs_=self.env.abs,
            rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
            s_cap_bnd_declared=("S_CAP_BND" in self.tc.container.listSymbols()),
        )

        if self.env.obmac.upper() == "YES":
            # TODO: uses handlestatus() %Handlestatus.Ready%, %Handlestatus.Running%, etc
            self.tc.enqueue(
                self.exec_async_grid,
                model_name=self.env.model_name,
                stages=self.env.stages,
                sensis=self.env.sensis,
                rptlite_no_code=rptlite_no_code,
                rpt_dam_code=rpt_dam_code,
                rpt_par_cli_loop_code=async_rpt_par_cli_loop_code,
                async_ext_code=async_ext_code,
                var=self.env.var,
                cufscal=self.env.cufscal,
                cucscal=self.env.cucscal,
                cli=self.env.cli,
                swd=self.env.swd,
                sow=self.env.sow,
                eq=self.env.eq,
                swt=self.env.swt,
                abs_=self.env.abs,
                macro=self.env.macro,
                rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                s_cap_bnd_declared=("S_CAP_BND" in self.tc.container.listSymbols()),
                bnd_ucw_defined={
                    f"{self.env.var}_UC": self.tc.defined(f"{self.env.var}_UC"),
                    f"{self.env.var}_UCR": self.tc.defined(f"{self.env.var}_UCR"),
                    f"{self.env.var}_UCT": self.tc.defined(f"{self.env.var}_UCT"),
                    f"{self.env.var}_UCRT": self.tc.defined(f"{self.env.var}_UCRT"),
                    f"{self.env.var}_UCTS": self.tc.defined(f"{self.env.var}_UCTS"),
                    f"{self.env.var}_UCRTS": self.tc.defined(f"{self.env.var}_UCRTS"),
                },
            )

    def exec_model_number(self: SolveStc, model_name: str, mca1: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"{model_name}.number={mca1}-1;",
        )

    def exec_main(
        self: SolveStc,
        gdl_init: str,
        stepped_yes: bool,
        spines_yes: bool,
        stages: str,
        swd: str,
        var: str,
        sow: str,
        bnd_ucw_defined: dict[str, bool],
        rptlite_no_code: str,
        rpt_dam_code: str,
        rpt_par_cli_loop_code: str,
        cufscal: str,
        cucscal: str,
        cli: str,
        eq: str,
        swt: str,
        abs_: str,
        macro: str,
        rtp_ffcs_defined: bool,
        s_cap_bnd_declared: bool,
        solve_now: str,
        damage: str,
        micro: str,
        etl: str,
        solmip: str,
        mixlp: str,
        nonlp: str,
        gams_cgi: str,
        memclean: str,
        err_abort: str,
    ) -> None:
        g = self.tc

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
{gdl_init}
*------------------------------------------------------------------------------
  DOITER = (SUM(SW_T(MIYR_1,WW),1) GT 1) OR SW_PHASE OR (SUM((XPT{swd}(W)),1)=0);
{"  DOITER = 0;" if spines_yes else ""}
  IF(DOITER,
*------------------------------------------------------------------------------
* Set of deterministic runs if several scenarios at stage 1
*------------------------------------------------------------------------------
{
                '   Abort "Cannot use Stepped Mode with Sensitivity/Tradeoff Analysis";'
                if stepped_yes
                else ""
            }
   CNT = SUM(SW_T(MIYR_1,SOW),1);
   IF(SW_PHASE, GDL=0;
     IF(S_UCOBJ('OBJ1','1') GT 0,
       SW_PHASE=1; DISPLAY "Phase 1 deterministic scenarios.",CNT;
     ELSE SW_PHASE=-1; DISPLAY "Multiphase tradeoff scenarios.",CNT);
   ELSE DISPLAY "Decomposed deterministic scenarios!",CNT;
     IF(GDL,{self.model_name}.solvelink = GDL));
*  Use MERGE for stochastic, because otherwise bounds for other scenarios get cleared
   OPTION SOLVEOPT=MERGE;
  );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(ALLSOW$(SUM(SW_T(MIYR_1,ALLSOW),1)$DOITER),
     CNT = ORD(ALLSOW); DISPLAY CNT;
     IF(S_UCOBJ('OBJ1',ALLSOW) EQ 4,
{
                r'''*  If no user-defined objective, skip Phase 1 copying previous VAR_UC solution if necessary
       LOOP(SOW,SPAR_UCSL(ALLSOW,UC_N,U2,U3,U4) $= SPAR_UCSL(SOW,UC_N,U2,U3,U4));'''
                if stages != "YES"
                else ""
            }

     ELSE
       IF((SW_PHASE EQ -1) AND (ORD(ALLSOW) GT 1),
{
                bnd_ucw_mod(
                    arg1="",
                    arg2="M",
                    var=var,
                    stages=stages,
                    swd=swd,
                    sow=sow,
                    defined_symbols=bnd_ucw_defined,
                )
                if stages == "YES"
                else ""
            }
*  Set deviation bounds in multiphase
         LOOP(SOW, Z = S_UC_RHS('OBJ1','N','1',SOW);
           {var}_UC.LO(UC_N('OBJ1'){sow})$((Z GE 0)$Z) = {var}_UC.L(UC_N{sow})-ABS({
                var
            }_UC.L(UC_N{sow})*Z);
           {var}_UC.UP(UC_N('OBJ1'){sow})$((Z GE 0)$Z) = {var}_UC.L(UC_N{sow})+ABS({
                var
            }_UC.L(UC_N{sow})*Z));
         AUXSOW(ALLSOW) = YES;
       );
       LOOP(MIYR_1(T),SOW(WW) = SW_TSW(WW,T,ALLSOW);
            SW_NORM = SW_TPROB(T,ALLSOW));
{
                sensis_stc(
                    var=var,
                    cufscal=cufscal,
                    cucscal=cucscal,
                    cli=cli,
                    model_name=self.model_name,
                    mca="",
                    stages=stages,
                    swd=swd,
                    sow=sow,
                    eq=eq,
                    swt=swt,
                    abs_=abs_,
                    macro=macro,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                    s_cap_bnd_declared=s_cap_bnd_declared,
                    bnd_ucw_defined=bnd_ucw_defined,
                )
                if stages != "YES"
                else ""
            }
{
                solve_mod(
                    g=self.tc,
                    model_name=self.model_name,
                    solve_now=solve_now,
                    damage=damage,
                    micro=micro,
                    macro=macro,
                    etl=etl,
                    solmip=solmip,
                    mixlp=mixlp,
                    nonlp=nonlp,
                    gams_cgi=gams_cgi,
                    memclean=memclean,
                    err_abort=err_abort,
                )
            }
       WHANDLE(ALLSOW)={self.model_name}.handle;
{
                f'''       IF(NOT (SW_PARM OR GDL), Z=0;
{rptlite_no_code}{rpt_dam_code}{rpt_par_cli_loop_code}
       ELSEIF NOT GDL,
* Save VAR_UC solution
       SPAR_UCSL(SOW,UC_N,'','','') $= VAR_UC.L(UC_N);
       SPAR_UCSL(SOW,UC_N,R,'','')  $= VAR_UCR.L(UC_N,R);
       SPAR_UCSL(SOW,UC_N,T,'','')  $= VAR_UCT.L(UC_N,T);
       SPAR_UCSL(SOW,UC_N,R,T,'')   $= VAR_UCRT.L(UC_N,R,T);
       SPAR_UCSL(SOW,UC_N,T,S,'')   $= VAR_UCTS.L(UC_N,T,S);
       SPAR_UCSL(SOW,UC_N,R,T,S)    $= VAR_UCRTS.L(UC_N,R,T,S));'''
                if stages != "YES"
                else ""
            }
     );
  );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Reset SOW
  IF(DOITER,
   SOW(WW)$(ORD(WW) LE SW_DESC('1','1')) = YES;
   AUXSOW(WW)$(ORD(WW) GT 1) = NO;
  );
""",
        )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*------------------------------------------------------------------------------
  IF(SW_PARM$SW_PHASE, SW_PHASE = SW_PARM;
{
                bnd_ucw_mod(
                    arg1="",
                    arg2="I",
                    var=var,
                    stages=stages,
                    swd=swd,
                    sow=sow,
                    defined_symbols=bnd_ucw_defined,
                )
                if stages == "YES"
                else ""
            }
    IF(SW_PARM EQ 2,
     DISPLAY "Phase 2 determinstic scenarios.";
     LOOP(ALLSOW$(SUM(SW_T(MIYR_1,ALLSOW),1)$(S_UCOBJ('OBJ1',ALLSOW) GT 0)),
       CNT = ORD(ALLSOW); DISPLAY CNT;
       LOOP(MIYR_1,SOW(WW) = SW_TSW(WW,MIYR_1,ALLSOW));
{
                sensis_stc(
                    var=var,
                    cufscal=cufscal,
                    cucscal=cucscal,
                    cli=cli,
                    model_name=self.model_name,
                    mca="",
                    stages=stages,
                    swd=swd,
                    sow=sow,
                    eq=eq,
                    swt=swt,
                    abs_=abs_,
                    macro=macro,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                    s_cap_bnd_declared=s_cap_bnd_declared,
                    bnd_ucw_defined=bnd_ucw_defined,
                )
                if stages != "YES"
                else ""
            }
{
                solve_mod(
                    g=self.tc,
                    model_name=self.model_name,
                    solve_now=solve_now,
                    damage=damage,
                    micro=micro,
                    macro=macro,
                    etl=etl,
                    solmip=solmip,
                    mixlp=mixlp,
                    nonlp=nonlp,
                    gams_cgi=gams_cgi,
                    memclean=memclean,
                    err_abort=err_abort,
                )
            }
{rptlite_no_code + rpt_dam_code + rpt_par_cli_loop_code if stages != "YES" else ""}
     );
* Reset SOW for reporting
     SOW(WW)$(ORD(WW) LE SW_DESC('1','1')) = YES$(S_UCOBJ('OBJ1',WW) GE 0);
    ELSE
* Set deviation bounds for OBJ1 if Single run in Phase 2
       F = UC_RHS('OBJ1','N');
       LOOP(SOW, Z = F; Z $= S_UC_RHS('OBJ1','N','1',SOW);
         {var}_UC.LO(UC_N('OBJ1'){sow})$((Z GE 0)$Z) = {var}_UC.L(UC_N{sow})-ABS({
                var
            }_UC.L(UC_N{sow})*Z);
         {var}_UC.UP(UC_N('OBJ1'){sow})$((Z GE 0)$Z) = {var}_UC.L(UC_N{sow})+ABS({
                var
            }_UC.L(UC_N{sow})*Z));
       AUXSOW(WW) = SOW(WW); SOW(WW) = ORD(WW) EQ 1;
       OPTION SOLVEOPT=REPLACE;
{
                solve_mod(
                    g=self.tc,
                    model_name=self.model_name,
                    solve_now=solve_now,
                    damage=damage,
                    micro=micro,
                    macro=macro,
                    etl=etl,
                    solmip=solmip,
                    mixlp=mixlp,
                    nonlp=nonlp,
                    gams_cgi=gams_cgi,
                    memclean=memclean,
                    err_abort=err_abort,
                )
            }
  ));
""",
        )
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  IF(SW_PHASE,SW_PROB(SOW) = EPS);
  """,
        )

        if not g.doiter.toValue():
            g.sw_norm[...] = 1

            solve_mod_GP(
                module=self,
                model_name=self.model_name,
                solve_now=solve_now,
                damage=damage,
                micro=micro,
                macro=macro,
                etl=etl,
                solmip=solmip,
                mixlp=mixlp,
                nonlp=nonlp,
                memclean=memclean,
                equations=self.equations,
            )

    def exec_async_grid(
        self: SolveStc,
        model_name: str,
        stages: str,
        sensis: str,
        rptlite_no_code: str,
        rpt_dam_code: str,
        rpt_par_cli_loop_code: str,
        async_ext_code: str,
        var: str,
        cufscal: str,
        cucscal: str,
        cli: str,
        swd: str,
        sow: str,
        eq: str,
        swt: str,
        abs_: str,
        macro: str,
        rtp_ffcs_defined: bool,
        s_cap_bnd_declared: bool,
        bnd_ucw_defined: dict[str, bool],
    ) -> None:
        async_reporting = ""
        if stages != "YES":
            async_reporting = (
                rptlite_no_code + rpt_dam_code + rpt_par_cli_loop_code + async_ext_code
            )

        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Load grid solutions if asynchronous
  DOITER=2*({model_name}.solvelink=GDL)$GDL;
* Force clear solution if Grid SENSIS Runs
  REG_FIXT(R)$GDL=MAX(REG_FIXT(R),1);
  IF(NOT DOITER,OPTION CLEAR=WHANDLE); DUR_MAX=TIMEELAPSED;
  REPEAT DONE=DOITER;
    LOOP(ALLSOW$(SW_PROB(ALLSOW)$DOITER),
      OPTION CLEAR=SOW; SOW(ALLSOW) = YES;
      F = handlestatus(WHANDLE(ALLSOW));
      IF(F<>%Handlestatus.Running%,
        IF(F=%Handlestatus.Ready%,
          Z=WHANDLE(ALLSOW); {model_name}.handle=Z;

{
                sensis_stc(
                    var=var,
                    cufscal=cufscal,
                    cucscal=cucscal,
                    cli=cli,
                    model_name=model_name,
                    mca="",
                    stages=stages,
                    swd=swd,
                    sow=sow,
                    eq=eq,
                    swt=swt,
                    abs_=abs_,
                    macro=macro,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                    s_cap_bnd_declared=s_cap_bnd_declared,
                    bnd_ucw_defined=bnd_ucw_defined,
                )
                if sensis.upper() == "YES"
                else ""
            }
          execute_loadhandle {model_name};
{async_reporting}
          F=1; DUR_MAX=TIMEELAPSED; DONE=0);
        IF(F, F=handledelete(WHANDLE(ALLSOW)));
        WHANDLE(SOW)=0));
    F=sleep(DONE+card(WHANDLE)*0.3);
  UNTIL(CARD(WHANDLE)=0 OR TIMEELAPSED-DUR_MAX>10000);
""",
        )
