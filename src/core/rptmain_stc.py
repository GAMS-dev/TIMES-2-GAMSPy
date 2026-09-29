# rptmain_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTMAIN.stc is the main driver for the report writer for stochastics
# *   arg1, arg2 - SOW, self.env.sws
# *=============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Variable

from core.base_class import GamsClass
from core.clearsol_stc import ClearsolStc, clearsol_stc
from core.cost_ann_rpt import cost_ann_rpt
from core.pextlevs_stc import PextlevsStc, PextlevsStcConfig
from core.rpt_obj_rpt import rpt_obj_rpt
from core.rptlite_rpt import RptliteRpt, RptliteRptConfig
from core.rptmisc_rpt import rptmisc_rpt
from core.sol_flo_red import SolFloRed, SolFloRedConfig, sol_flo_red
from core.sol_ire_rpt import SolIreRpt, sol_ire_rpt
from core.utils import apply_sw_notags

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptmainStc(GamsClass):
    """Translation unit for rptmain.stc."""

    # Instance attributes
    module_name: str = "rptmain_stc"
    gams_source: str = "rptmain.stc"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str,
        arg2: str,
        model_name: str,
        arg1_GP: tuple[Set | Alias | str] | tuple[()] = (),
        arg3: str = "",
        arg4: str = "",
        arg3_GP: tuple[Set | Alias | str] | tuple[()] = (),
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg1_GP = arg1_GP
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg3_GP = arg3_GP
        self.model_name = model_name
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.env.set_scoped("eqs", self.env.eq)
        self.env.set_scoped("v", self.env.var)

        self.include(ClearsolStc(self.tc, self.env, arg1="DEF"))

        if self.env.etl == "YES":
            g.VAR_IC = Variable(
                g.container, name="VAR_IC", domain=[g.r, g.year, g.prc], type="positive"
            )

        g.sw_unpb = Parameter(g.container, name="SW_UNPB", domain=[g.ll, g.ww])
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
PARAMETERS SW_UNPC(LL,WW);
""",
        )

        if self.env.stepped == "+":
            self.env.set_scoped("solveda", "1")

        if self.env.spines.upper() == "YES":
            # $SHIFT SHIFT (rptmain.stc:19): %1/%2 drop, so what the caller
            # passed as arg3/arg4 become the new arg1/arg2.
            self.arg1 = self.arg3
            self.arg2 = self.arg4
            self.arg1_GP = self.arg3_GP

        if str(self.env.spines + self.env.solveda).upper() != "YES1":
            self.env.set_scoped("solveda", "1")
            self.include(
                RptliteRpt(
                    self.tc,
                    self.env,
                    config=RptliteRptConfig(arg1="S", arg2=(self.tc.ww,)),
                )
            )

            self.tc.enqueue(self.calculate_sw_unpb, spines=self.env.spines)

            self.tc.enqueue(
                self.sow_loop,
                vart=self.env.vart,
                sws=self.env.sws,
                var=self.env.var,
                etl=self.env.etl,
                arg1=self.arg1,
                arg2=self.arg2,
                var_dam_defined=self.tc.defined("VAR_DAM"),
                var_scap_defined=self.tc.defined("VAR_SCAP"),
                eq=self.env.eq,
                v=self.env.v,
                pgprim=self.env.pgprim,
                sow=self.env.sow,
                rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                stages=self.env.stages,
                sysprefix=self.env.sysprefix,
                capjd=self.env.capjd,
                capwd=self.env.capwd,
                timesed=self.env.timesed,
                obj=self.env.obj,
                varcost=self.env.varcost,
                vnret_defined=self.tc.defined("VNRET"),
                invlif=self.env.invlif,
                anncost=self.env.anncost,
                tpulse=self.env.tpulse,
                is_vnret_defined=self.tc.defined("IS_VNRET"),
                varv=self.env.varv,
                varm=self.env.varm,
                is_obj_combal_defined=self.tc.defined("IS_OBJ_COMBAL"),
                micro=self.env.micro,
                bencost=self.env.bencost,
                cufscal=self.env.cufscal,
                rpt_flots=self.env.rpt_flots,
                var_uc=self.env.var_uc,
                solans=self.env.solans,
                mx=self.env.mx,
                discshift=self.env.discshift,
                model_name=self.model_name,
                is_mi_agc_defined=self.tc.defined("IS_MI_AGC"),
                if_defined_vnret=self.tc.defined("VNRET"),
                if_defined_eqe_ucrtp=self.tc.defined("EQE_UCRTP"),
                if_not_defined_eq_g_ucmax=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
            )

            self.include(
                PextlevsStc(
                    self.tc,
                    self.env,
                    config=PextlevsStcConfig(arg1=self.arg1, arg1_GP=self.arg1_GP),
                )
            )
            self.tc.enqueue(self.set_auxsow)
            return

        # *-----------------------------------------------------------------------------
        # * Standard Reports based on expected values
        # *-----------------------------------------------------------------------------

        apply_sw_notags(env=self.env)
        self.tc.enqueue(self.report_param)
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(arg1="S", arg2=(self.tc.ww,)),
            )
        )

        self.env.set_scoped("sow", ",SOW")
        self.env.set_scoped("sow_GP", (g.Sow,))
        self.env.set_scoped("eq", self.env.eqs)
        self.env.set_scoped("var", self.env.v)

        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(
                    arg1=f"{self.env.v}_FLO",
                    arg2=".L",
                    arg3=".L",
                    arg4="GLOBAL",
                    arg5=(g.Sow,),
                    arg6=g.SwT[g.t, g.Sow],
                ),
            ),
        )

        self.include(
            SolIreRpt(
                self.tc,
                self.env,
                arg1="GLOBAL",
                arg2=",SOW",
                arg3="SUM(SW_T(T,SOW),SW_TPROB(T,SOW)*",
                arg4=")",
            )
        )

        self.include(
            PextlevsStc(
                self.tc,
                self.env,
                PextlevsStcConfig(arg1=self.arg1, arg1_GP=self.arg1_GP),
            )
        )

        self.env.set_scoped("sow", "")
        self.env.set_scoped("sow_GP", ())
        self.env.set_scoped("eq", "EQ")
        self.env.set_scoped("var", "VAR")

        if self.tc.defined("RTP_FFCS"):
            self.tc.add_gams_code(module=self, phase="init", code="$KILL RTP_FFCS")

        self.tc.enqueue(self.clear_symbols)
        self.include(
            RptliteRpt(
                self.tc,
                self.env,
                config=RptliteRptConfig(
                    arg1="S", arg2=(self.tc.ww,), arg3=("'1',",), arg4=("NO",)
                ),
            )
        )

        if "RTP_FFCS" in self.tc.container.listSymbols():
            self.tc.add_gams_code(module=self, phase="init", code="$CLEAR RTP_FFCS")

    def define_variable_bases_on_if(self: RptmainStc) -> None:
        g = self.tc
        m = g.container
        r, year, Rpc = g.r, g.year, g.Rpc
        g.VAR_IC = Variable(m, "VAR_IC", type="Positive", domain=[r, year, Rpc])

    def report_param(self: RptmainStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
SW_UNPB(SW_T) = 1;
""",
        )

    def clear_symbols(self: RptmainStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
OPTION CLEAR=RPC_EMIS,CLEAR=RPC_FFUNC,CLEAR=F_IOSET; SOW(W)=AUXSOW(W);
""",
        )

    def calculate_sw_unpb(self: RptmainStc, spines: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  SW_UNPB(SW_T(T,W))=POWER(SW_TPROB(T,W)/SW_NORM,1$SW_PHASE-1); SW_UNPC(T,W) $= SW_UNPB(T,W);
  SW_UNPB('0',W)=POWER(SW_PROB(W)/SW_NORM,1$SW_PHASE-1$SW_PROB(W));
{"SW_UNPC(SW_T) = 1;" if spines == "YES" else ""}
""",
        )

    def sow_loop(
        self: RptmainStc,
        vart: str,
        sws: str,
        var: str,
        etl: str,
        arg1: str,
        arg2: str,
        eq: str,
        v: str,
        pgprim: str,
        sow: str,
        rtp_ffcs_defined: bool,
        stages: str,
        sysprefix: str,
        capjd: str,
        capwd: str,
        timesed: str,
        obj: str,
        varcost: str,
        vnret_defined: bool,
        invlif: str,
        anncost: str,
        tpulse: str,
        is_vnret_defined: bool,
        varv: str,
        varm: str,
        is_obj_combal_defined: bool,
        micro: str,
        bencost: str,
        cufscal: str,
        rpt_flots: str,
        var_uc: str,
        solans: str,
        mx: str,
        discshift: float,
        model_name: str,
        is_mi_agc_defined: bool,
        if_not_defined_eq_g_ucmax: bool,
        if_defined_vnret: bool,
        if_defined_eqe_ucrtp: bool,
        var_dam_defined: bool,
        var_scap_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(SOW$SW_PROB(SOW),

  {
                clearsol_stc(
                    g=self.tc,
                    var_dam_defined=var_dam_defined,
                    var_scap_defined=var_scap_defined,
                    inline=True,
                )
            }

* Get the variable levels
    VAR_ACT.L(R,V,T,P,S)      $= {vart}_ACT.L(R,V,T,P,S {sws});
    VAR_BLND.L(R,T,COM,C)     $= {vart}_BLND.L(R,T,COM,C {sws});
    VAR_CAP.L(R,T,P)          $= {vart}_CAP.L(R,T,P {arg2});
    VAR_COMNET.L(R,T,COM,S)   $= {vart}_COMNET.L(R,T,COM,S {sws});
    VAR_COMPRD.L(R,T,COM,S)   $= {vart}_COMPRD.L(R,T,COM,S {sws});
    VAR_IRE.L(R,V,T,P,C,S,IE) $= {vart}_IRE.L(R,V,T,P,C,S,IE {sws});
    VAR_ELAST.L(R,T,C,S,J,BD) $= {vart}_ELAST.L(R,T,C,S,J,BD {sws});
    VAR_FLO.L(R,V,T,P,C,S)    $= {vart}_FLO.L(R,V,T,P,C,S {sws});
    VAR_NCAP.L(R,T,P)         $= {vart}_NCAP.L(R,T,P {arg2});
    VAR_SIN.L(R,V,T,P,C,S)    $= {vart}_SIN.L(R,V,T,P,C,S {sws});
    VAR_SOUT.L(R,V,T,P,C,S)   $= {vart}_SOUT.L(R,V,T,P,C,S {sws});
    VAR_UPS.L(R,V,T,P,S,L)    $= {vart}_UPS.L(R,V,T,P,S,L {sws});
    VAR_UPT.L(R,V,T,P,S,UPT)  $= {vart}_UPT.L(R,V,T,P,S,UPT {sws});
    VAR_UDP.L(R,V,T,P,S,L)    $= {vart}_UDP.L(R,V,T,P,S,L {sws});
    VAR_SCAP.L(R,V,T,P)       $= {vart}_SCAP.L(R,V,T,P{
                arg2
            }); VAR_SCAP.L(R,V,'0',P) $= {var}_SCAP.L(R,V,'0',P,{arg1});
{
                f"OPTION CLEAR=VAR_IC; VAR_IC.L(R,T,P) $= {vart}_IC.L(R,T,P{arg2});"
                if etl == "YES"
                else ""
            }
* Get variable marginals
    VAR_ACT.M(R,V,T,P,S)    $= {vart}_ACT.M(R,V,T,P,S,W)*SW_UNPB(T{sws});
    VAR_CAP.M(R,T,P)        $= SUM(SW_TSW({arg1},T,W),{
                var
            }_CAP.M(R,T,P,W)*SW_UNPC(T,W));
    VAR_NCAP.M(R,T,P)       $= SUM(SW_TSW({arg1},T,W),{
                var
            }_NCAP.M(R,T,P,W)*SW_UNPC(T,W));
    VAR_COMNET.M(R,T,COM,S) $= {vart}_COMNET.M(R,T,COM,S,W)*SW_UNPB(T{sws});
    VAR_COMPRD.M(R,T,COM,S) $= {vart}_COMPRD.M(R,T,COM,S,W)*SW_UNPB(T{sws});
    VAR_FLO.M(R,V,T,P,C,S)  $= {vart}_FLO.M(R,V,T,P,C,S,W)*SW_UNPB(T{sws});


* Get equation marginals
    EQG_COMBAL.M(R,T,C,S)  $= SUM(SW_TSW(SOW,T,W),{
                eq
            }G_COMBAL.M(R,T,C,S,T,W)*SW_UNPB(T,W));
    EQE_COMBAL.M(R,T,C,S)  $= SUM(SW_TSW(SOW,T,W),{
                eq
            }E_COMBAL.M(R,T,C,S,T,W)*SW_UNPB(T,W));
    EQE_COMPRD.M(R,T,C,S)  $= SUM(SW_TSW(SOW,T,W),{
                eq
            }E_COMPRD.M(R,T,C,S,T,W)*SW_UNPB(T,W));
    EQ_PEAK.M(R,T,CG,S)    $= SUM(SW_TSW(SOW,T,W),{
                eq
            }_PEAK.M(R,T,CG,S,T,W)*SW_UNPB(T,W));
    EQ_IRE.M(R,T,P,C,IE,S) $= SUM(SW_TSW(SOW,T,W),{
                eq
            }_IRE.M(R,T,P,C,IE,S,T,W)*SW_UNPB(T,W));
    EQE_CPT.M(R,T,P)       $= SUM(SW_TSW({arg1},T,W),{
                eq
            }E_CPT.M(R,T,P,T,W)*SW_UNPC(T,W));
    EQG_COMBAL.L(R,T,C,S)  $= {eq}G_COMBAL.L(R,T,C,S,T,SOW);
*-----------------------------------------------------------------------------
* Calculate the reporting parameters
*-----------------------------------------------------------------------------
* Calculation of solution values for (due to reduction) substituted flows
*-----------------------------------------------------------------------------
  OPTION CLEAR=PAR_FLO,CLEAR=PAR_FLOM;
{
                sol_flo_red(
                    arg1="PAR_FLO",
                    arg2="",
                    arg3=".L",
                    v=v,
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
                    v=v,
                    pgprim=pgprim,
                    sow=sow,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                )
            }
{sol_ire_rpt(v=v, sow=sow, mx=mx, rtp_ffcs_defined=rtp_ffcs_defined)}
  OPTION CLEAR=COEF_OBJINV;
{
                rpt_obj_rpt(
                    arg1="S",
                    arg2="SOW,",
                    arg3=",SOW",
                    arg4=sysprefix,
                    stages=stages,
                    sysprefix=sysprefix,
                    etl=etl,
                    capjd=capjd,
                    capwd=capwd,
                    var=var,
                    timesed=timesed,
                    obj=obj,
                    varcost=varcost,
                    varv=varv,
                    varm=varm,
                    sws=sws,
                    pgprim=pgprim,
                    bencost=bencost,
                    discshift=discshift,
                    vnret_defined=vnret_defined,
                )
            }
*-----------------------------------------------------------------------------
* Calculation of annual costs
*-----------------------------------------------------------------------------
{
                cost_ann_rpt(
                    arg1="S",
                    arg2="SOW,",
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
            }
*-----------------------------------------------------------------------------
* Miscellaneous reportings
  EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD('FX'))  $= SUM(SW_TSW(SOW,T,W),{
                eq
            }E_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W)*SW_UNPB(T,W));
  EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BDNEQ(BD)) $= SUM(SW_TSW(SOW,T,W),{
                eq
            }N_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W)*SW_UNPB(T,W));
{
                rptmisc_rpt(
                    arg1="S",
                    arg2="SOW,",
                    arg3=",SOW",
                    arg4=",W)*SW_UNPB(T,W)",
                    arg5=",SOW)*SW_UNPB('0',SOW",
                    var=var,
                    cufscal=cufscal,
                    sysprefix=sysprefix,
                    vart=vart,
                    sws=sws,
                    eq=eq,
                    rpt_flots=rpt_flots,
                    stages=stages,
                    var_uc=var_uc,
                    solans=solans,
                    model_name=model_name,
                    if_defined_eqe_ucrtp=if_defined_eqe_ucrtp,
                    if_defined_vnret=if_defined_vnret,
                    if_not_defined_eq_g_ucmax=if_not_defined_eq_g_ucmax,
                )
            }
* Non-common reporting
  SPAR_CAPBD(SOW,RTP(R,T,P),'LO')  $= S_CAP_BND(RTP,'LO','1',SOW);
  SPAR_CAPBD(SOW,RTP(R,T,P),'UP')$(S_CAP_BND(RTP,'UP','1',SOW)<INF) $= S_CAP_BND(RTP,'UP','1',SOW);
*-----------------------------------------------------------------------------
* ** End of SOW loop **
*-----------------------------------------------------------------------------
  );
  REG_WOBJ(R,ITEM,CUR) $= SUM(W$SREG_WOBJ(W,R,ITEM,CUR),SW_PROB(W)*SREG_WOBJ(W,R,ITEM,CUR));
""",
        )

    def set_auxsow(self: RptmainStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  AUXSOW(W) = YES;
""",
        )
