# eqobjvar_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJVAR the objective functions variable costs, variable O&M and commodity
# *          direct costs
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# * - Top-level SUM over Y_EOH moved to individual components
# * - This version works for the alternative objective formulations ALT/LIN

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.cal_caps_mod import cal_caps_mod
from core.cal_nored_red import cal_nored_red
from core.cal_red_red import cal_red_red

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjvarMod(GamsClass):
    """Translation unit for eqobjvar.mod."""

    # Instance attributes
    module_name: str = "eqobjvar_mod"
    gams_source: str = "eqobjvar.mod"

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
        g = self.tc

        self.env.set_scoped("tpulse", "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)")
        if self.env.obj.upper() == "ALT":
            self.env.set_scoped(
                "tpulse", "PERIODYR(T,Y_EOH),OBJ_ALTV(R,T)*OBJ_DISC(R,Y_EOH,CUR)"
            )
        if self.env.obj.upper() == "LIN":
            self.env.set_scoped(
                "tpulse", "TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)"
            )
        if self.env.varcost.upper() == "LIN":
            self.env.set_scoped(
                "tpulse", "Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)"
            )
        # * Generate Variable cost equation summing over all active indexes by region and currency
        self.env.set_scoped("sowtmp", self.env.sow)
        if self.env.stages == "YES":
            self.env.set_local("swtd", "SUM(SW_TSW(SOW,T,WW),")
            self.env.set_scoped("sow", ",WW")
            self.env.set_scoped("sow_GP", (g.ww,))
        if self.tc.defined("RTP_FFCS"):
            self.env.set_scoped("mx", f"*(1+RTP_FFCS(R,V,P,C,C{self.env.sow}))")
        if self.env.stages == "YES":
            self.env.set_scoped("sowtmpend", ",SOW")
        else:
            self.env.set_scoped("sowtmpend", self.env.sow)

        # TODO need to figure out what todo if arg2 = *
        if self.arg2 == "*":
            raise NotImplementedError("No implementation for arg2 = *")

        eqobjvar = eqobjvar_mod(
            tpulse=self.env.tpulse,
            var=self.env.var,
            sow=self.env.sow,
            pgprim=self.env.pgprim,
            vart=self.env.vart,
            sws=self.env.sws,
            mx=self.env.mx,
            condition1=self.env.stages.upper() == "YES",
            condition2=self.env.stages == "YES",
            is_vnret_defined=self.tc.defined("VNRET"),
            is_def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
            varv=self.env.varv,
            varm=self.env.varm,
            cal_red=self.env.cal_red,
            swtd=self.env.swtd,
        )

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
   {self.env.eq}_OBJVAR(RDCUR(R,CUR) {self.env.sowtmp}) ..

{eqobjvar}

    SUM(OBV,SUM_OBJ('OBJVAR',OBV)*{self.env.var}_OBJ(R,OBV,CUR {self.env.sowtmpend}));

""",
        )

        if self.env.stages == "YES":
            self.env.set_scoped("sow", ",SOW")
            self.env.set_scoped("sow_GP", (g.Sow,))


def eqobjvar_mod(
    swtd: str,
    tpulse: str,
    var: str,
    sow: str,
    pgprim: str,
    vart: str,
    sws: str,
    mx: str,
    condition1: bool,
    condition2: bool,
    is_vnret_defined: bool,
    is_def_rtp_ffcs: bool,
    varv: str,
    varm: str,
    cal_red: str,
) -> str:
    include_cal_caps_ = cal_caps_mod(
        is_vnret_defined=is_vnret_defined,
        arg1="T",
        arg2=f"SUM(TS_ANN(TS,SL),SUM({tpulse}*(OBJ_FCOST(R,Y_EOH,P,C,SL,CUR)+OBJ_FDELV(R,Y_EOH,P,C,SL,CUR)+OBJ_FTAX(R,Y_EOH,P,C,SL,CUR))))",
        arg3="TS",
        arg4="",
        varv=varv,
        sws=sws,
        varm=varm,
    )

    if cal_red == "cal_red.red":
        include_cal_red = cal_red_red(
            arg1="C",
            arg2="COM",
            arg3="S",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_def_rtp_ffcs,
        )
    elif cal_red == "cal_nored.red":
        include_cal_red = cal_nored_red(
            arg1="C",
            arg2="COM",
            arg3="S",
            arg4="P",
            arg5="T",
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_def_rtp_ffcs,
        )
    else:
        raise ValueError(f"Unexpected value for cal_red: {cal_red}")

    return rf"""
      ({swtd}
*------------------------------------------------------------------------------
* Costs on Overall activity of a process
*------------------------------------------------------------------------------
* multiply storage activity by average residence time
          SUM(RTP_VARA(R,T,P)$OBJ_ACOST(R,T,P,CUR),
            SUM({tpulse} * OBJ_ACOST(R,Y_EOH,P,CUR)) *
            SUM((RTP_VINTYR(R,V,T,P),PRC_TS(R,P,S)),{var}_ACT(R,V,T,P,S {sow}) *
                POWER(RS_STGAV(R,S),1$RP_STG(R,P)))
             ) +
* modal costs if modeled
          SUM(RTP_VINTYR(R,V,T,P)$RPC_CUR(R,P,'{pgprim}',CUR),
            SUM(RP_UPS(R,P,TSL,L('UP')),ACT_CSTUP(R,V,P,TSL,CUR)*OBJ_PVT(R,T,CUR)*SUM(TS_GROUP(R,TSL,S),RS_STGPRD(R,S)*{var}_UPS(R,V,T,P,S,L{sow}))) +
            SUM(RP_UPT(R,P,UPT,'UP'),ACT_CSTSD(R,V,P,UPT,'FX',CUR)*OBJ_PVT(R,T,CUR)*SUM(TS_GROUP(R,TSL,S)$RP_DPL(R,P,TSL),RS_STGPRD(R,S)*{var}_UPT(R,V,T,P,S,UPT{sow}))) +
            SUM(RP_UPR(R,P,BDNEQ(BD)),ACT_CSTRMP(R,V,P,BD,CUR)*OBJ_PVT(R,T,CUR)*SUM(PRC_TS(R,P,S),RS_STGPRD(R,S)*{var}_UDP(R,V,T,P,S,BD{sow})))) +

*------------------------------------------------------------------------------
* Commodity added costs and sub/tax
*------------------------------------------------------------------------------
     SUM(RHS_COMBAL(R,T,C,S), {var}_COMNET(R,T,C,S {sow}) *
       SUM({tpulse} * SUM(COSTYPE,OBJ_COMNT(R,Y_EOH,C,S,COSTYPE,CUR)))) +
     SUM(RHS_COMPRD(R,T,C,S), {var}_COMPRD(R,T,C,S {sow}) *
       SUM({tpulse} * SUM(COSTYPE,OBJ_COMPD(R,Y_EOH,C,S,COSTYPE,CUR)))) +
{f"SUM((RTCS_VARC(R,T,C,S),COM_VAR,W(WW))$S_COM_TAX(R,T,C,S,COM_VAR,CUR,'1',W),SUM(Y_EOH(Y)$OBJ_LINT(R,T,Y,CUR),OBJ_LINT(R,T,Y,CUR)*S_COM_TAX(R,Y,C,S,COM_VAR,CUR,'1',W))*({var}_COMPRD(R,T,C,S{sow})$DIAG('PRD',COM_VAR)+{var}_COMNET(R,T,C,S{sow})$DIAG('NET',COM_VAR))) +" if condition1 else ""}

*------------------------------------------------------------------------------
* Commodity costs/tax/sub associated with imports/exports from outside study area
* - note that price only applied when actually an external region
*------------------------------------------------------------------------------
     SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'OUT')),
       SUM({tpulse} * OBJ_IPRIC(R,Y_EOH,P,C,S,IE,CUR)) *
       SUM(RTP_VINTYR(R,V,T,P),
         ({var}_IRE(R,V,T,P,C,S,IE {sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,T,P,S {sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C))
          )
        ) +

*------------------------------------------------------------------------------
* Flow level costs/tax/sub
*------------------------------------------------------------------------------
*GG* need to add VAR_NCAP if I/O/COM and FLO_COST/DELIV/SUB/TAX for commodity
*    based upon RPC_CAPFLOr,t,p,c
     SUM(RTPCS_VARF(R,T,P,C,S)$SUM(OBJ_VFLO(RP_FLO(R,P),C,CUR,UC_COST),1),
        SUM(TS_ANN(S,TS),
          SUM({tpulse} * (OBJ_FCOST(R,Y_EOH,P,C,TS,CUR)+OBJ_FDELV(R,Y_EOH,P,C,TS,CUR)+OBJ_FTAX(R,Y_EOH,P,C,TS,CUR)))) *
        SUM(RTP_VINTYR(R,V,T,P),
{include_cal_red}
          )) +

* same for IRE processes
     SUM(RTPCS_VARF(R,T,P,C,S)$SUM(OBJ_VFLO(RP_IRE(R,P),C,CUR,UC_COST),1),
        SUM(TS_ANN(S,TS),
          SUM({tpulse} * (OBJ_FCOST(R,Y_EOH,P,C,TS,CUR)+OBJ_FDELV(R,Y_EOH,P,C,TS,CUR)+OBJ_FTAX(R,Y_EOH,P,C,TS,CUR)))) *
        SUM(RTP_VINTYR(R,V,T,P),
            SUM(RPC_IRE(R,P,C,IE),
              {var}_IRE(R,V,T,P,C,S,IE {sow})$(NOT RPC_AIRE(R,P,C))+({var}_ACT(R,V,T,P,S {sow})*PRC_ACTFLO(R,V,P,C))$RPC_AIRE(R,P,C)
               ) +
*V06a_3 handle aux delivery cost to exchange processes, BUT NOT HANDLING different TSlevel!!!
* Negative IRE_FLOSUM is resonable for import flows only, and for the commodity itself
            SUM((RPC_IRE(R,P,COM,IE),IO)$IRE_FLOSUM(R,T,P,COM,S,IE,C,IO),
                IRE_FLOSUM(R,T,P,COM,S,IE,C,IO) {mx} *
                ({var}_IRE(R,V,T,P,COM,S,IE {sow})$(NOT RPC_AIRE(R,P,COM))+({var}_ACT(R,V,T,P,S {sow})*PRC_ACTFLO(R,V,P,COM))$RPC_AIRE(R,P,COM))
             ))) +
*V3.3.3 support costs also for storage flows (FCOST for IN, FDELV for OUT)
     SUM(OBJ_VFLO(RPC_STG(R,P,C),CUR,'COST'),
       SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,S)),
         SUM(TS_ANN(S,TS),SUM({tpulse} * ({var}_SIN(R,V,T,P,C,S{sow})*OBJ_FCOST(R,Y_EOH,P,C,TS,CUR)+{var}_SOUT(R,V,T,P,C,S{sow})*STG_EFF(R,V,P)*OBJ_FDELV(R,Y_EOH,P,C,TS,CUR))))))
{")" if condition2 else ""}
       ) +

*V05c 980924 handle the fact that commodity costs may be associated with capacity
* note that G_YRFR fraction in the cal_*.mod files
* [AL] Moved cost summation over TPULSEYR inside called routines; V must be in RTP, but T need not be
     SUM(ANNUAL(S),
{include_cal_caps_}
        ) +

*------------------------------------------------------------------------------
* Commodity blending costs
*------------------------------------------------------------------------------
     SUM((BLE_OPR(R,BLE,OPR),TT(T)),
        SUM({tpulse} * OBJ_BLNDV(R,Y_EOH,BLE,OPR,CUR)) * {vart}_BLND(R,T,BLE,OPR {sws})
        )

    =E=
"""
