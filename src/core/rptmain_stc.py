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

from core.clearsol_stc import ClearsolStc
from core.cost_ann_rpt import cost_ann_rpt
from core.pextlevs_stc import PextlevsStc
from core.rpt_obj_rpt import rpt_obj_rpt
from core.rptlite_rpt import RptliteRpt
from core.rptmisc_rpt import rptmisc_rpt
from core.sol_flo_red import SolFlowRed, sol_flo_red
from core.sol_ire_rpt import SolIreRpt, sol_ire_rpt

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

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
        self.env.set_scoped("eqs", self.env.eq)
        self.env.set_scoped("v", self.env.var)

        self.include(ClearsolStc(self.tc, self.env, arg1="DEF"))

        if self.env.etl == "YES":
            self.tc.enqueue(self.define_variable_bases_on_if)

        self.tc.enqueue(self.define_variable)

        if self.env.stepped == "+":
            self.env.set_scoped("solveda", "1")

        if self.env.spines.upper() == "YES":
            self.arg1 = ""
            self.arg2 = ""

        if str(self.env.spines + self.env.solveda).upper() != "YES1":
            self.env.set_scoped("solveda", "1")
            self.include(RptliteRpt(self.tc, self.env, arg1="S", arg2="WW,"))

            self.tc.enqueue(self.calculate_sw_unpb, spines=self.env.spines)
            # NOTE/TODO: L33, The LOOP does not effect the batinclude and the lines till L64
            # For now, we can place the loop down to L63 and hope the tests pass.
            self.include(ClearsolStc(self.tc, self.env))
            self.tc.enqueue(
                self.get_variable_levels,
                vart=self.env.vart,
                sws=self.env.sws,
                var=self.env.var,
                etl=self.env.etl,
                arg1=self.arg1,
                arg2=self.arg2,
            )
            self.tc.enqueue(
                # NOTE: check the defined method args
                self.sow_loop,
                eq=self.env.eq,
                arg1=self.env.arg1,
                v=self.env.v,
                shff=self.env.shff,
                pgprim=self.env.pgprim,
                sow=self.env.sow,
                rtp_ffcs_defined=self.tc.defined("RTP_FFCS"),
                stages=self.env.stages,
                sysprefix=self.env.sysprefix,
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
                tpulse=self.env.tpulse,
                is_vnret_defined=self.tc.defined("IS_VNRET"),
                varv=self.env.varv,
                sws=self.env.sws,
                varm=self.env.varm,
                is_obj_combal_defined=self.tc.defined("IS_OBJ_COMBAL"),
                vart=self.env.vart,
                micro=self.env.micro,
                is_mi_agc_defined=self.tc.defined("IS_MI_AGC"),
            )

            self.include(PextlevsStc(self.tc, self.env, arg1=self.arg1))
            self.tc.enqueue(self.set_auxsow)
            return

        # *-----------------------------------------------------------------------------
        # * Standard Reports based on expected values
        # *-----------------------------------------------------------------------------

        if (
            self.env.sw_notags
            != "SET EQ 'EQ' SET VAR 'VAR' SET SWS '' SET SOW '' SET SWT '' SET SWD '' SET SWTD '' SET SWSW '' SET VART 'VAR' SET VARV 'VAR' SET VARM 'VAR' SET VARTT VAR"
        ):
            raise ValueError(f"Unknown value in sw_notags: {self.env.sw_notags}")

        self.tc.enqueue(self.report_param)
        self.include(RptliteRpt(self.tc, self.env, arg1="S", arg2="WW,"))

        self.env.set_scoped("sow", ",SOW")
        self.env.set_scoped("EQ", self.env.eqs)
        self.env.set_scoped("var", self.env.v)

        self.include(
            SolFlowRed(
                self.tc,
                self.env,
                arg1=f"{self.env.v}_FLO",
                arg2=".L",
                arg3=".L",
                arg4="GLOBAL",
                arg5=",SOW",
                arg6="$SW_T(T,SOW)",
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

        self.include(PextlevsStc(self.tc, self.env, arg1=self.arg1))

        self.env.set_scoped("sow", "")
        self.env.set_scoped("EQ", "EQ")
        self.env.set_scoped("var", "VAR")

        if self.tc.defined("RTP_FFCS"):
            self.tc.add_gams_code(module=self, phase="init", code="$KILL RTP_FFCS")

        self.tc.enqueue(self.clear_symbols)
        self.include(
            RptliteRpt(self.tc, self.env, arg1="S", arg2="WW,", arg3="'1',", arg4="NO")
        )

        if "RTP_FFCS" in self.tc.container.listSymbols():
            self.tc.add_gams_code(module=self, phase="init", code="$CLEAR RTP_FFCS")

    def define_variable_bases_on_if(self: RptmainStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
POSITIVE VARIABLES VAR_IC(R,YEAR,PRC)
""",
        )

    def define_variable(self: RptmainStc) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
PARAMETERS SW_UNPB(LL,WW), SW_UNPC(LL,WW);
""",
        )

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

    def get_variable_levels(
        self: RptmainStc, vart: str, sws: str, var: str, etl: str, arg1: str, arg2: str
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
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
    VAR_SCAP.L(R,V,T,P)       $= {vart}_SCAP.L(R,V,T,P{arg2}); VAR_SCAP.L(R,V,'0',P) $= {var}_SCAP.L(R,V,'0',P,{arg1});
{f"OPTION CLEAR=VAR_IC; VAR_IC.L(R,T,P) $= {vart}_IC.L(R,T,P {arg2});" if etl == "YES" else ""}
* Get variable marginals
    VAR_ACT.M(R,V,T,P,S)    $= {vart}_ACT.M(R,V,T,P,S,W)*SW_UNPB(T{sws});
    VAR_CAP.M(R,T,P)        $= SUM(SW_TSW({arg1},T,W),{var}_CAP.M(R,T,P,W)*SW_UNPC(T,W));
    VAR_NCAP.M(R,T,P)       $= SUM(SW_TSW({arg1},T,W),{var}_NCAP.M(R,T,P,W)*SW_UNPC(T,W));
    VAR_COMNET.M(R,T,COM,S) $= {vart}_COMNET.M(R,T,COM,S,W)*SW_UNPB(T{sws});
    VAR_COMPRD.M(R,T,COM,S) $= {vart}_COMPRD.M(R,T,COM,S,W)*SW_UNPB(T{sws});
    VAR_FLO.M(R,V,T,P,C,S)  $= {vart}_FLO.M(R,V,T,P,C,S,W)*SW_UNPB(T{sws});
""",
        )

    def sow_loop(
        self: RptmainStc,
        eq: str,
        arg1: str,
        v: str,
        shff: str,
        pgprim: str,
        sow: str,
        rtp_ffcs_defined: bool,
        stages: str,
        sysprefix: str,
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
        varm: str,
        is_obj_combal_defined: bool,
        vart: str,
        micro: str,
        is_mi_agc_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(SOW$SW_PROB(SOW),
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
                    arg2="''",
                    arg3=".L",
                    v=v,
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
                    v=v,
                    shff=shff,
                    pgprim=pgprim,
                    sow=sow,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                )
            }
{
                sol_ire_rpt(
                    v=v,
                    shff=shff,
                    sow=sow,
                    rtp_ffcs_defined=rtp_ffcs_defined,
                )
            }
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
                    vnret_defined=vnret_defined,
                )
            }
*-----------------------------------------------------------------------------
* Calculation of annual costs
*-----------------------------------------------------------------------------
{
                cost_ann_rpt(
                    arg1="S",
                    arg2="SOW",
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
