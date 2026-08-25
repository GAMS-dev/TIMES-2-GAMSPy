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

from gamspy import Domain, Number, Sum
from gamspy.math import diag, power

from core.base_class import GamsClass
from core.cal_caps_mod import CalCapsModConfig, cal_caps_mod, cal_caps_mod_GP
from core.cal_nored_red import cal_nored_red, cal_nored_red_GP
from core.cal_red_red import CalRedRedConfig, cal_red_red, cal_red_red_GP
from core.utils import extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from core.utils import SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

    # %TPULSE% always expands to "<sum domain>,<multiplier of the summand>"
    PulseSum = tuple[
        Condition | Domain | ImplicitSet,
        Expression | ImplicitParameter | MathOp | Sum,
    ]

logger = logging.getLogger(__name__)


class EqobjvarMod(GamsClass):
    """Translation unit for eqobjvar.mod."""

    # Instance attributes
    module_name: str = "eqobjvar_mod"
    gams_source: str = "eqobjvar.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, included: bool = False
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.included = included
        self.compile_result: str | None = None
        self.compile()

    def compile(self) -> None:
        g = self.tc

        r, v, p, c, cur = g.r, g.v, g.p, g.c, g.cur

        self.env.set_scoped("tpulse", self.set_tpulse())

        # * Generate Variable cost equation summing over all active indexes by region and currency
        self.env.set_scoped("sowtmp", self.env.sow)
        sowtmp_GP = self.env.sow_GP
        # NB: unrelated to the domain-suffix meaning of env.swtd_GP used elsewhere
        # (e.g. equcwrap_mod.py); here it is only ever a local Sum-wrapper for the
        # body of this equation, so it is kept as a plain local instead of reusing
        # that (differently typed) schema field.
        swtd_wrapper_GP: ImplicitSet | None = None
        if self.env.stages == "YES":
            self.env.set_local("swtd", "SUM(SW_TSW(SOW,T,WW),")
            swtd_wrapper_GP = g.SwTsw[g.Sow, g.t, g.ww]
            self.env.set_scoped("sow", ",WW")
            self.env.set_scoped("sow_GP", (g.ww,))
        if self.tc.defined("RTP_FFCS"):
            self.env.set_scoped("mx", f"*(1+RTP_FFCS(R,V,P,C,C{self.env.sow}))")
            sow = self.env.sow_GP
            self.env.set_scoped("mx_GP", Number(1) + g.rtp_ffcs[r, v, p, c, c, *sow])
        if self.env.stages == "YES":
            self.env.set_scoped("sowtmpend", ",SOW")
            sowtmpend_GP: SowGPType = (g.Sow,)
        else:
            self.env.set_scoped("sowtmpend", self.env.sow)
            sowtmpend_GP = sowtmp_GP

        if self.included:
            eqobjvar_lhs = self.eqobjvar_mod()
        else:
            eqobjvar_lhs_GP = self.eqobjvar_mod_GP(swtd_wrapper_GP=swtd_wrapper_GP)

        if self.env.stages == "YES":
            self.env.set_scoped("sow", ",SOW")
            self.env.set_scoped("sow_GP", (g.Sow,))

        # mimics arg2=*
        if self.included:
            # only return the lhs
            self.compile_result = eqobjvar_lhs
        else:
            eq_objvar = g.get_equation(f"{self.env.eq}_OBJVAR")
            VAR_OBJ = g.get_variable(f"{self.env.var}_OBJ")
            eq_objvar[g.Rdcur[r, cur], *sowtmp_GP] = eqobjvar_lhs_GP == Sum(
                g.obv,
                g.sum_obj["OBJVAR", g.obv] * VAR_OBJ[r, g.obv, cur, *sowtmpend_GP],
            )

    def set_tpulse(self: EqobjvarMod) -> str:
        if self.env.varcost.upper() == "LIN":
            return "Y_EOH$OBJ_LINT(R,T,Y_EOH,CUR),OBJ_LINT(R,T,Y_EOH,CUR)"
        if self.env.obj.upper() == "LIN":
            return "TPULSEYR(T,Y_EOH),TPULSE(T,Y_EOH)*OBJ_DISC(R,Y_EOH,CUR)"
        if self.env.obj.upper() == "ALT":
            return "PERIODYR(T,Y_EOH),OBJ_ALTV(R,T)*OBJ_DISC(R,Y_EOH,CUR)"
        return "PERIODYR(T,Y_EOH),OBJ_DISC(R,Y_EOH,CUR)"

    def set_tpulse_GP(self: EqobjvarMod) -> PulseSum:
        """GAMSPy counterpart of set_tpulse(): a <sum domain, multiplier> pair."""
        g = self.tc
        r, t, cur = g.r, g.t, g.cur

        if self.env.varcost.upper() == "LIN":
            return (
                g.YEoh.where[g.obj_lint[r, t, g.YEoh, cur]],
                g.obj_lint[r, t, g.YEoh, cur],
            )
        if self.env.obj.upper() == "LIN":
            return (
                g.Tpulseyr[t, g.YEoh],
                g.tpulse[t, g.YEoh] * g.obj_disc[r, g.YEoh, cur],
            )
        if self.env.obj.upper() == "ALT":
            return (
                g.Periodyr[t, g.YEoh],
                g.obj_altv[r, t] * g.obj_disc[r, g.YEoh, cur],
            )
        return (g.Periodyr[t, g.YEoh], g.obj_disc[r, g.YEoh, cur])

    def eqobjvar_mod(self: EqobjvarMod) -> str:
        """We can pass the env and tc as only used during compile"""

        tpulse = self.env.tpulse
        var = self.env.var
        sow = self.env.sow
        pgprim = self.env.pgprim
        vart = self.env.vart
        sws = self.env.sws
        mx = self.env.mx
        condition1 = self.env.stages.upper() == "YES"
        condition2 = self.env.stages == "YES"
        is_vnret_defined = self.tc.defined("VNRET")
        is_def_rtp_ffcs = self.tc.defined("RTP_FFCS")
        varv = self.env.varv
        varm = self.env.varm
        cal_red = self.env.cal_red
        swtd = self.env.swtd

        include_cal_caps_ = cal_caps_mod(
            is_vnret_defined=is_vnret_defined,
            arg1="T",
            arg2=f"SUM(TS_ANN(TS,SL),SUM({tpulse}*({macro.obj_fcost('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')}+{macro.obj_fdelv('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')}+{macro.obj_ftax('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')})))",
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
        SUM(RTP_VARA(R,T,P)${macro.obj_acost("R", "T", "P", "CUR")},
            SUM({tpulse} * {macro.obj_acost("R", "Y_EOH", "P", "CUR")}) *
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
        SUM({tpulse} * ({macro.obj_fcost("R", "Y_EOH", "P", "C", "TS", "CUR")}+{macro.obj_fdelv("R", "Y_EOH", "P", "C", "TS", "CUR")}+{macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")}))) *
        SUM(RTP_VINTYR(R,V,T,P),
{include_cal_red}
        )) +

* same for IRE processes
    SUM(RTPCS_VARF(R,T,P,C,S)$SUM(OBJ_VFLO(RP_IRE(R,P),C,CUR,UC_COST),1),
        SUM(TS_ANN(S,TS),
        SUM({tpulse} * ({macro.obj_fcost("R", "Y_EOH", "P", "C", "TS", "CUR")}+{macro.obj_fdelv("R", "Y_EOH", "P", "C", "TS", "CUR")}+{macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")}))) *
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
        SUM(TS_ANN(S,TS),SUM({tpulse} * ({var}_SIN(R,V,T,P,C,S{sow})*{macro.obj_fcost("R", "Y_EOH", "P", "C", "TS", "CUR")}+{var}_SOUT(R,V,T,P,C,S{sow})*STG_EFF(R,V,P)*{macro.obj_fdelv("R", "Y_EOH", "P", "C", "TS", "CUR")})))))
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

    def eqobjvar_mod_GP(
        self: EqobjvarMod, swtd_wrapper_GP: ImplicitSet | None
    ) -> Expression:
        """GAMSPy counterpart of eqobjvar_mod().

        This function returns the LHS of an equation. Equation type is =E=
        """
        g = self.tc

        r, v, t, p, c, s, sl, ts, tsl, cur = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.sl,
            g.ts,
            g.tsl,
            g.cur,
        )
        io, ie, bd, upt, lA, y = g.io, g.ie, g.bd, g.upt, g.lA, g.Y

        tpulse = self.set_tpulse_GP()

        def pulse(
            x: Expression | ImplicitParameter | MathOp | Sum,
        ) -> Expression | Sum:
            """%TPULSE%(x): sum x over the pulse years."""
            return wrap_in_sum(x, tpulse)  # type: ignore[arg-type]

        var = self.env.var
        sow = self.env.sow_GP
        pgprim = self.env.pgprim
        sws = self.env.sws_GP
        condition1 = self.env.stages.upper() == "YES"
        is_vnret_defined = self.tc.defined("VNRET")
        is_def_rtp_ffcs = self.tc.defined("RTP_FFCS")
        varv = self.env.varv_GP
        varm = self.env.varm_GP
        vart_id, vart_set = extract_var_domain(self.env.vart_GP)
        mx_multiplier = self.env.mx_GP if is_def_rtp_ffcs else Number(1)
        cal_red = self.env.cal_red
        if cal_red == "cal_red.red":
            cal_red_func_GP = cal_red_red_GP
        elif cal_red == "cal_nored.red":
            cal_red_func_GP = cal_nored_red_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_UPT = g.get_variable(f"{var}_UPT")
        VAR_UDP = g.get_variable(f"{var}_UDP")
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        VART_BLND = g.get_variable(f"{vart_id}_BLND")

        # *------------------------------------------------------------------------------
        # * Costs on Overall activity of a process
        # *------------------------------------------------------------------------------
        # * multiply storage activity by average residence time
        block_activity = Sum(
            g.RtpVara[r, t, p].where[macro.obj_acost_GP(r, t, p, cur)],
            pulse(macro.obj_acost_GP(r, g.YEoh, p, cur))
            * Sum(
                Domain(g.RtpVintyr[r, v, t, p], g.PrcTs[r, p, s]),
                VAR_ACT[r, v, t, p, s, *sow]
                * power(g.rs_stgav[r, s], Number(1).where[g.RpStg[r, p]]),
            ),
        )

        # * modal costs if modeled
        block_modal = Sum(
            g.RtpVintyr[r, v, t, p].where[g.RpcCur[r, p, pgprim, cur]],
            Sum(
                g.RpUps[r, p, tsl, lA["UP"]],
                g.act_cstup[r, v, p, tsl, cur]
                * g.obj_pvt[r, t, cur]
                * Sum(
                    g.TsGroup[r, tsl, s],
                    g.rs_stgprd[r, s] * VAR_UPS[r, v, t, p, s, lA, *sow],
                ),
            )
            + Sum(
                g.RpUpt[r, p, upt, "UP"],
                g.act_cstsd[r, v, p, upt, "FX", cur]
                * g.obj_pvt[r, t, cur]
                * Sum(
                    g.TsGroup[r, tsl, s].where[g.RpDpl[r, p, tsl]],
                    g.rs_stgprd[r, s] * VAR_UPT[r, v, t, p, s, upt, *sow],
                ),
            )
            + Sum(
                g.RpUpr[r, p, g.Bdneq[bd]],
                g.act_cstrmp[r, v, p, bd, cur]
                * g.obj_pvt[r, t, cur]
                * Sum(
                    g.PrcTs[r, p, s],
                    g.rs_stgprd[r, s] * VAR_UDP[r, v, t, p, s, bd, *sow],
                ),
            ),
        )

        # *------------------------------------------------------------------------------
        # * Commodity added costs and sub/tax
        # *------------------------------------------------------------------------------
        block_com: Expression | Sum = Sum(
            g.RhsCombal[r, t, c, s],
            VAR_COMNET[r, t, c, s, *sow]
            * pulse(Sum(g.costype, g.obj_comnt[r, g.YEoh, c, s, g.costype, cur])),
        ) + Sum(
            g.RhsComprd[r, t, c, s],
            VAR_COMPRD[r, t, c, s, *sow]
            * pulse(Sum(g.costype, g.obj_compd[r, g.YEoh, c, s, g.costype, cur])),
        )
        if condition1:
            # eqobjvar.mod:22 gates the enclosing SW_TSW wrap on a
            # case-SENSITIVE "%STAGES%==YES" ($IF), while eqobjvar.mod:55
            # gates this whole term on a case-INSENSITIVE "%STAGES%==YES"
            # ($IFI). SENSIS=YES alone sets STAGES to "Yes" (mixed case,
            # see maindrv.mod:36 / maindrv_mod.py), which satisfies only the
            # second check -- so swtd_wrapper_GP can be None here even
            # though condition1 is True.
            #
            # When swtd_wrapper_GP is set, WW is already bound by that
            # enclosing SUM, and the GAMS source's "W(WW)" only re-asserts
            # WW's membership in the W/SOW alias rather than binding a
            # fresh index. When it's None, no enclosing WW binding exists,
            # so "W(WW)" here binds a fresh local WW index instead.
            tax_ww_condition: Condition | Expression | ImplicitParameter
            if swtd_wrapper_GP is not None:
                tax_ww_domain = Domain(g.RtcsVarc[r, t, c, s], g.comvar)
                tax_ww_condition = (
                    g.w[g.ww] & g.s_com_tax[r, t, c, s, g.comvar, cur, "1", g.ww]
                )
            else:
                tax_ww_domain = Domain(g.RtcsVarc[r, t, c, s], g.comvar, g.w[g.ww])
                tax_ww_condition = g.s_com_tax[r, t, c, s, g.comvar, cur, "1", g.ww]

            block_com = block_com + Sum(
                tax_ww_domain.where[tax_ww_condition],
                Sum(
                    g.YEoh[y].where[g.obj_lint[r, t, y, cur]],
                    g.obj_lint[r, t, y, cur]
                    * g.s_com_tax[r, y, c, s, g.comvar, cur, "1", g.ww],
                )
                * (
                    VAR_COMPRD[r, t, c, s, *sow].where[diag("PRD", g.comvar)]
                    + VAR_COMNET[r, t, c, s, *sow].where[diag("NET", g.comvar)]
                ),
            )

        # *------------------------------------------------------------------------------
        # * Commodity costs/tax/sub associated with imports/exports from outside study area
        # * - note that price only applied when actually an external region
        # *------------------------------------------------------------------------------
        block_ire_import = Sum(
            Domain(g.RtpcsVarf[r, t, p, c, s], g.RpcIreio[r, p, c, ie, "OUT"]),
            pulse(g.obj_ipric[r, g.YEoh, p, c, s, ie, cur])
            * Sum(
                g.RtpVintyr[r, v, t, p],
                VAR_IRE[r, v, t, p, c, s, ie, *sow].where[~g.RpcAire[r, p, c]]
                + (VAR_ACT[r, v, t, p, s, *sow] * g.prc_actflo[r, v, p, c]).where[
                    g.RpcAire[r, p, c]
                ],
            ),
        )

        # *------------------------------------------------------------------------------
        # * Flow level costs/tax/sub
        # *------------------------------------------------------------------------------
        # *GG* need to add VAR_NCAP if I/O/COM and FLO_COST/DELIV/SUB/TAX for commodity
        # *    based upon RPC_CAPFLOr,t,p,c
        flow_pulse = pulse(
            macro.obj_fcost_GP(r, g.YEoh, p, c, ts, cur)
            + macro.obj_fdelv_GP(r, g.YEoh, p, c, ts, cur)
            + macro.obj_ftax_GP(r, g.YEoh, p, c, ts, cur)
        )
        cal_red_config = CalRedRedConfig(
            var=var,
            sow=sow,
            pgprim=pgprim,
            def_rtp_ffcs=is_def_rtp_ffcs,
            arg1=c,
            arg2=g.Com,
            arg3=s,
            arg4=p,
            arg5=t,
            arg10=Number(1),
        )
        block_flow_rpflo = Sum(
            g.RtpcsVarf[r, t, p, c, s].where[
                Sum(g.ObjVflo[g.RpFlo[r, p], c, cur, g.UcCost], 1)
            ],
            Sum(g.TsAnn[s, ts], flow_pulse)
            * Sum(g.RtpVintyr[r, v, t, p], cal_red_func_GP(g, cal_red_config)),
        )

        # * same for IRE processes
        block_flow_rpire = Sum(
            g.RtpcsVarf[r, t, p, c, s].where[
                Sum(g.ObjVflo[g.RpIre[r, p], c, cur, g.UcCost], 1)
            ],
            Sum(g.TsAnn[s, ts], flow_pulse)
            * Sum(
                g.RtpVintyr[r, v, t, p],
                Sum(
                    g.RpcIre[r, p, c, ie],
                    VAR_IRE[r, v, t, p, c, s, ie, *sow].where[~g.RpcAire[r, p, c]]
                    + (VAR_ACT[r, v, t, p, s, *sow] * g.prc_actflo[r, v, p, c]).where[
                        g.RpcAire[r, p, c]
                    ],
                )
                # *V06a_3 handle aux delivery cost to exchange processes, BUT NOT
                # * HANDLING different TSlevel!!!
                # * Negative IRE_FLOSUM is resonable for import flows only, and
                # * for the commodity itself
                + Sum(
                    Domain(g.RpcIre[r, p, g.Com, ie], io).where[
                        g.ire_flosum[r, t, p, g.Com, s, ie, c, io]
                    ],
                    g.ire_flosum[r, t, p, g.Com, s, ie, c, io]
                    * mx_multiplier
                    * (
                        VAR_IRE[r, v, t, p, g.Com, s, ie, *sow].where[
                            ~g.RpcAire[r, p, g.Com]
                        ]
                        + (
                            VAR_ACT[r, v, t, p, s, *sow] * g.prc_actflo[r, v, p, g.Com]
                        ).where[g.RpcAire[r, p, g.Com]]
                    ),
                ),
            ),
        )

        # *V3.3.3 support costs also for storage flows (FCOST for IN, FDELV for OUT)
        block_storage_flow = Sum(
            g.ObjVflo[g.RpcStg[r, p, c], cur, "COST"],
            Sum(
                Domain(g.RtpVintyr[r, v, t, p], g.RpcsVar[r, p, c, s]),
                Sum(
                    g.TsAnn[s, ts],
                    pulse(
                        VAR_SIN[r, v, t, p, c, s, *sow]
                        * macro.obj_fcost_GP(r, g.YEoh, p, c, ts, cur)
                        + VAR_SOUT[r, v, t, p, c, s, *sow]
                        * g.stg_eff[r, v, p]
                        * macro.obj_fdelv_GP(r, g.YEoh, p, c, ts, cur)
                    ),
                ),
            ),
        )

        activity_block = (
            block_activity
            + block_modal
            + block_com
            + block_ire_import
            + block_flow_rpflo
            + block_flow_rpire
            + block_storage_flow
        )

        # *V05c 980924 handle the fact that commodity costs may be associated with capacity
        # * note that G_YRFR fraction in the cal_*.mod files
        # * [AL] Moved cost summation over TPULSEYR inside called routines; V must be
        # * in RTP, but T need not be
        cal_caps_result = cal_caps_mod_GP(
            g,
            CalCapsModConfig(
                is_vnret_defined=is_vnret_defined,
                varv=varv,
                sws=sws,
                varm=varm,
                arg1=t,
                arg2=Sum(
                    g.TsAnn[ts, sl],
                    pulse(
                        macro.obj_fcost_GP(r, g.YEoh, p, c, sl, cur)
                        + macro.obj_fdelv_GP(r, g.YEoh, p, c, sl, cur)
                        + macro.obj_ftax_GP(r, g.YEoh, p, c, sl, cur)
                    ),
                ),
                arg3=ts,
                is_output=False,
            ),
        )

        # *------------------------------------------------------------------------------
        # * Commodity blending costs
        # *------------------------------------------------------------------------------
        block_blend = Sum(
            Domain(g.BleOpr[r, g.Ble, g.Opr], g.tt[t]),
            pulse(g.obj_blndv[r, g.YEoh, g.Ble, g.Opr, cur])
            * wrap_in_sum(target=VART_BLND[r, t, g.Ble, g.Opr, *sws], domain=vart_set),
        )

        return (
            wrap_in_sum(activity_block, swtd_wrapper_GP)
            + Sum(g.Annual[s], cal_caps_result)
            + block_blend
        )
