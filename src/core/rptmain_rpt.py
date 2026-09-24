# rptmain_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *---------------------------------------------------------------
# * RPTMAIN.RPT
# *
# * Output routine
# *    - creating flat dump for VEDA3 and paramaters for VEDA4
# *GG* VEDABE 'V4' override to avoid PUT related code (e.g., File & SOLSUBV calls)
# *---------------------------------------------------------------
# * Output routine for IER extensions
# *---------------------------------------------------------------
# *  - VAR_FLO/VAR_IRE are replaced by the parameters PAR_FLO/PAR_IRE
# *    which contain the values of the flow variables in the reduced model
# *    plus the recalculated values of substituted flows
# *  - calculation of annual cost terms

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Alias,
    Domain,
    Loop,
    Number,
    Parameter,
    Set,
    SpecialValues,
    Sum,
    sparse,
)

from core.base_class import GamsClass
from core.eqobjels_rpt import EqobjelsRpt, EqobjelsRptConfig
from core.eqobjfix_rpt import EqobjfixRpt
from core.eqobjinv_rpt import EqobjinvRpt
from core.eqobjvar_rpt import EqobjvarRpt, EqobjvarRptConfig
from core.eqobsalv_rpt import EqobsalvRpt
from core.par_uc_rpt import ParUcRpt, ParUcRptConfig
from core.sol_flo_red import SolFloRed, SolFloRedConfig
from core.sol_ire_rpt import SolIreRpt

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptmainRpt(GamsClass):
    """Translation unit for rptmain.rpt."""

    # Instance attributes
    module_name: str = "rptmain_rpt"
    gams_source: str = "rptmain.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.comp_declarations()
        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(arg1="PAR_FLO", arg2="", arg3=".L"),
            )
        )
        self.include(
            SolFloRed(
                self.tc,
                self.env,
                config=SolFloRedConfig(arg1="PAR_FLO", arg2="M", arg3=".M"),
            )
        )

        self.tc.enqueue(self.exec_loop)

        self.include(SolIreRpt(self.tc, self.env))

        # * Calculation of annual cost terms
        self.include(EqobjinvRpt(self.tc, self.env))
        self.include(EqobjfixRpt(self.tc, self.env, arg1="mod"))
        self.include(EqobsalvRpt(self.tc, self.env, arg1="rpt"))
        self.include(
            EqobjvarRpt(self.tc, self.env, config=EqobjvarRptConfig(arg1="mod"))
        )
        self.include(
            EqobjelsRpt(
                self.tc,
                self.env,
                config=EqobjelsRptConfig(
                    arg1=g.par_objels[g.r, g.YEoh, g.c, g.cur],
                    arg2=g.YEoh,
                    arg3=g.obj_disc[g.r, g.YEoh, g.cur],
                ),
            )
        )

        # * Include explicit EPS values for zero flows
        self.tc.enqueue(self.exec_objective_values, self.env.supzero)

        m = g.container
        r, allyear, cur, p, c, ts = g.r, g.allyear, g.cur, g.p, g.c, g.ts
        # **Aggregate Undiscounted Costs w/out CUR
        g.tot_objv = Parameter(m, name="TOT_OBJV", domain=[r, allyear])
        self.tc.enqueue(self.exec1)

        # * Discounted objective value by region
        if not g.declared(g.reg_obj):
            g.reg_obj = Parameter(m, name="REG_OBJ", domain=[g.Reg])
        self.tc.enqueue(self.exec2)

        # *calculate discounting for the period
        if not g.declared(g.vda_disc):
            g.vda_disc = Parameter(m, name="VDA_DISC", domain=[r, allyear])
        self.tc.enqueue(self.exec3)

        # * Annual undiscounted costs by process/commodity w/out CUR
        g.cst_invv = Parameter(m, name="CST_INVV", domain=[r, allyear, allyear, p])
        g.cst_decv = Parameter(m, name="CST_DECV", domain=[r, allyear, allyear, p])
        g.cst_fixv = Parameter(m, name="CST_FIXV", domain=[r, allyear, allyear, p])
        g.cst_salv = Parameter(m, name="CST_SALV", domain=[r, allyear, p])
        g.cst_latv = Parameter(m, name="CST_LATV", domain=[r, allyear, p])
        g.cst_actv = Parameter(m, name="CST_ACTV", domain=[r, allyear, allyear, p, ts])
        g.cst_flov = Parameter(
            m, name="CST_FLOV", domain=[r, allyear, allyear, p, c, ts]
        )
        g.cst_comv = Parameter(m, name="CST_COMV", domain=[r, allyear, c, ts])
        g.cst_elsv = Parameter(m, name="CST_ELSV", domain=[r, allyear, c])

        self.tc.enqueue(self.exec4)

        # * Shadow prices of user constraints
        # *--------------------------------------------------------------------------
        # * Note: undiscounting only done for user constraints having region and period as index
        if self.env.var_uc == "YES":
            # UC_VAR
            self.tc.enqueue(self.exec5)

        else:
            for config in (
                ParUcRptConfig(arg1="FXM", arg2="EQE"),
                ParUcRptConfig(arg1="LOM", arg2="EQG"),
                ParUcRptConfig(arg1="UPM", arg2="EQL"),
            ):
                self.include(ParUcRpt(self.tc, self.env, config=config))
        # UC_DONE
        self.tc.enqueue(self.exec_options)

        # * Add regional total discounted cost paramete
        if not g.declared(g.reg_wobj):
            g.reg_wobj = Parameter(m, name="REG_WOBJ", domain=[g.Reg, g.item, cur])
        self.tc.enqueue(self.exec6, self.env.timesed)

    def comp_declarations(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        m = g.container
        r, t, p, c, s, io, allyear, cur = (
            g.r,
            g.t,
            g.p,
            g.c,
            g.s,
            g.io,
            g.allyear,
            g.cur,
        )
        # * Declarations
        g.par_capl = Parameter(m, name="PAR_CAPL", domain=[r, t, p])
        g.par_capm = Parameter(m, name="PAR_CAPM", domain=[r, t, p])
        g.par_pasti = Parameter(m, name="PAR_PASTI", domain=[r, t, p])
        g.par_caplo = Parameter(m, name="PAR_CAPLO", domain=[r, t, p])
        g.par_capup = Parameter(m, name="PAR_CAPUP", domain=[r, t, p])
        g.par_ncapl = Parameter(m, name="PAR_NCAPL", domain=[r, allyear, p])
        g.par_ncapm = Parameter(m, name="PAR_NCAPM", domain=[r, allyear, p])
        g.par_actl = Parameter(
            m, name="PAR_ACTL", domain=[g.Reg, allyear, allyear, g.prc, g.allts]
        )
        g.par_actm = Parameter(
            m, name="PAR_ACTM", domain=[g.Reg, allyear, allyear, g.prc, g.allts]
        )
        g.par_comprdl = Parameter(m, name="PAR_COMPRDL", domain=[r, allyear, c, s])
        g.par_comprdm = Parameter(m, name="PAR_COMPRDM", domain=[r, allyear, c, s])
        g.par_comnetl = Parameter(m, name="PAR_COMNETL", domain=[r, allyear, c, s])
        g.par_comnetm = Parameter(m, name="PAR_COMNETM", domain=[r, allyear, c, s])
        g.par_combalem = Parameter(m, name="PAR_COMBALEM", domain=[r, allyear, c, s])
        g.par_combalgm = Parameter(m, name="PAR_COMBALGM", domain=[r, allyear, c, s])
        g.par_peakm = Parameter(m, name="PAR_PEAKM", domain=[r, allyear, g.comgrp, s])
        g.par_uclom = Parameter(m, name="PAR_UCLOM", domain=[g.ucn, "*", "*", "*"])
        g.par_ucupm = Parameter(m, name="PAR_UCUPM", domain=[g.ucn, "*", "*", "*"])
        g.par_ucfxm = Parameter(m, name="PAR_UCFXM", domain=[g.ucn, "*", "*", "*"])
        g.f_in = Parameter(m, name="F_IN", domain=[r, allyear, t, p, c, s])
        g.f_out = Parameter(m, name="F_OUT", domain=[r, allyear, t, p, c, s])
        if not g.declared(g.f_inout):
            g.f_inout = Parameter(m, name="F_INOUT", domain=[r, allyear, t, p, c, io])
        if not g.declared(g.f_inouts):
            g.f_inouts = Parameter(
                m, name="F_INOUTS", domain=[r, allyear, t, p, c, g.ts, io]
            )
        if not g.declared(g.FIoset):
            g.FIoset = Set(m, name="F_IOSET", domain=[r, allyear, t, p, c, g.ts, io])

        domain: list[Set | Alias] = [r, allyear, cur]
        g.tot_inv = Parameter(
            m,
            name="TOT_INV",
            domain=domain,
            description="Total annual disocunted investment costs",
        )
        g.tot_dec = Parameter(
            m,
            name="TOT_DEC",
            domain=domain,
            description="Total annual disocunted decommissioning costs",
        )
        g.tot_fix = Parameter(
            m,
            name="TOT_FIX",
            domain=domain,
            description="Total annual disocunted FOM costs",
        )
        g.tot_sal = Parameter(
            m,
            name="TOT_SAL",
            domain=domain,
            description="Total annual disocunted salvage value",
        )
        g.tot_lat = Parameter(
            m,
            name="TOT_LAT",
            domain=domain,
            description="Total annual disocunted late costs",
        )
        g.tot_act = Parameter(
            m,
            name="TOT_ACT",
            domain=domain,
            description="Total annual disocunted variable costs",
        )
        g.tot_com = Parameter(
            m,
            name="TOT_COM",
            domain=domain,
            description="Total annual disocunted commodity costs",
        )
        g.tot_flo = Parameter(
            m,
            name="TOT_FLO",
            domain=domain,
            description="Total annual disocunted flow costs",
        )
        g.tot_ble = Parameter(
            m,
            name="TOT_BLE",
            domain=domain,
            description="Total annual disocunted blending costs",
        )
        g.tot_obj = Parameter(
            m,
            name="TOT_OBJ",
            domain=domain,
            description="Annual discounted objective value ",
        )

    def exec_loop(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        r, v, t, p, c, ts, io, Com = g.r, g.v, g.t, g.p, g.c, g.ts, g.io, g.Com
        # * IRE auxiliary flows summed up from all IE flows
        with Loop(Domain(g.RpcIre[r, p, Com, g.ie], g.RpcsVar[r, p, Com, ts])):
            g.FIoset[g.RtpVintyr[r, v, t, p], c, ts, io].where[
                g.ire_flosum[r, t, p, Com, ts, g.ie, c, io]
            ] = g.Rc[r, c]

    def exec_objective_values(
        self: RptmainRpt,
        supzero: str,
    ) -> None:
        g = self.tc
        r, v, t, p, c, s, ts, cur, allyear = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.ts,
            g.cur,
            g.allyear,
        )
        RtpVintyr, RtpcsVarf, par_flo, par_ire = (
            g.RtpVintyr,
            g.RtpcsVarf,
            g.par_flo,
            g.par_ire,
        )
        if supzero != "YES":
            par_flo[RtpVintyr[r, v, t, p], c, s].where[
                RtpcsVarf[r, t, p, c, s] * g.RpFlo[r, p] * (~g.RpcNoflo[r, p, c])
            ] = sparse(Number(SpecialValues.EPS).where[~par_flo[r, v, t, p, c, s]])
        if supzero != "YES":
            par_ire[RtpVintyr[r, v, t, p], c, ts, g.impexp].where[
                RtpcsVarf[r, t, p, c, ts].where[g.RpcIre[r, p, c, g.impexp]]
            ] = sparse(
                Number(SpecialValues.EPS).where[~par_ire[r, v, t, p, c, ts, g.impexp]]
            )
        # *---------------------------------------------------------------------
        # * Annual discounted objective values by cost type(INV, FIX, VAR etc.)
        # *---------------------------------------------------------------------

        # * Total investment costs
        g.tot_inv[r, allyear, cur] = Sum(
            g.Rtp[r, v, p], g.par_objinv[r, v, allyear, p, cur]
        )
        # * Total decommissioning costs
        g.tot_dec[r, allyear, cur] = Sum(
            g.Rtp[r, v, p], g.par_objdec[r, v, allyear, p, cur]
        )
        # * Total fix costs
        g.tot_fix[r, allyear, cur] = Sum(
            g.Rtp[r, v, p], g.par_objfix[r, v, allyear, p, cur]
        )
        # * Total salvage value
        g.tot_sal[r, v, cur] = -Sum(p, g.par_objsal[r, v, p, cur])
        # * Total late revenues
        g.tot_lat[r, allyear, cur] = -Sum(p, g.par_objlat[r, allyear, p, cur])
        # * Total variable costs
        g.tot_act[r, allyear, cur] = Sum(
            Domain(RtpVintyr[r, v, t, p], ts).where[g.Periodyr[t, allyear]],
            g.par_objact[r, v, allyear, p, ts, cur],
        )
        # * Total flow related costs
        g.tot_flo[r, allyear, cur] = Sum(
            Domain(RtpVintyr[r, v, t, p], c, ts).where[g.Periodyr[t, allyear]],
            g.par_objflo[r, v, allyear, p, c, ts, cur],
        )
        # * Total commodity related costs
        g.tot_com[r, allyear, cur] = Sum(
            Domain(c, ts), g.par_objcom[r, allyear, c, ts, cur]
        )
        # * Total blending related costs
        g.tot_ble[r, allyear, cur] = Sum(c, g.par_objble[r, allyear, c, cur])
        # * Total yearly objective value
        g.tot_obj[r, allyear, cur] = (
            g.tot_inv[r, allyear, cur]
            + g.tot_dec[r, allyear, cur]
            + g.tot_fix[r, allyear, cur]
            + g.tot_sal[r, allyear, cur]
            + g.tot_lat[r, allyear, cur]
            + g.tot_act[r, allyear, cur]
            + g.tot_flo[r, allyear, cur]
            + g.tot_com[r, allyear, cur]
            + g.tot_ble[r, allyear, cur]
        )

    def exec1(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        g.tot_objv[g.r, g.t] = sparse(
            Sum(g.cur, g.tot_obj[g.r, g.t, g.cur] / g.obj_disc[g.r, g.t, g.cur])
        )

    def exec2(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        g.reg_obj[g.r] = Sum(Domain(g.cur, g.allyear), g.tot_obj[g.r, g.allyear, g.cur])

    def exec3(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        r, v, t, tt, p, c, s, pyr = g.r, g.v, g.t, g.tt, g.p, g.c, g.s, g.pyr
        vda_disc, coef_cpt, ncap_pasti, VAR_NCAP = (
            g.vda_disc,
            g.coef_cpt,
            g.ncap_pasti,
            g.VAR_NCAP,
        )
        # * Refined undiscounting method (MARKAL way not sufficient for TIMES)
        # *VDA_DISC(R,T) =  SUM(CUR,OBJ_DISC(R,T,CUR))*D(T);
        with Loop(g.Rdcur[r, g.cur]):
            vda_disc[r, t] = Sum(g.Periodyr[t, g.YEoh], g.obj_disc[r, g.YEoh, g.cur])

        # * Scenario index not supported in current version, use 1
        g.Sow["1"] = True

        # *---------------------------------------------------------------------
        # * Output of VAR_ACT
        # *---------------------------------------------------------------------

        g.par_actl[g.RtpVintyr[r, v, t, p], s].where[g.PrcTs[r, p, s]] = (
            SpecialValues.EPS
        )
        g.par_actl[r, v, t, p, s] = sparse(g.VAR_ACT.l[r, v, t, p, s])
        g.par_actm[r, v, t, p, s].where[g.VAR_ACT.m[r, v, t, p, s]] = (
            g.VAR_ACT.m[r, v, t, p, s] / vda_disc[r, t]
        )

        # *---------------------------------------------------------------------
        # * Output of VAR_CAP
        # *---------------------------------------------------------------------

        g.RtpCapyr[g.RtpCptyr[r, tt, t, p]].where[VAR_NCAP.l[r, tt, p]] = True
        g.RtpCapyr[g.RtpCptyr[r, pyr, t, p]].where[ncap_pasti[r, pyr, p]] = True

        g.par_pasti[g.Rtp[r, t, p]] = Sum(
            g.RtpCapyr[r, pyr, t, p], coef_cpt[r, pyr, t, p] * ncap_pasti[r, pyr, p]
        )
        g.par_capl[g.Rtp[r, t, p]] = (
            Sum(g.RtpCapyr[r, tt, t, p], coef_cpt[r, tt, t, p] * VAR_NCAP.l[r, tt, p])
            + g.par_pasti[r, t, p]
        )

        g.par_capm[g.Rtp[r, t, p]] = sparse(
            g.VAR_CAP.m[r, t, p] * (1.0 / vda_disc[r, t])
        )
        g.par_caplo[g.Rtp[r, t, p]] = sparse(g.cap_bnd[r, t, p, "LO"])
        g.par_capup[g.Rtp[r, t, p]].where[
            g.cap_bnd[r, t, p, "UP"] != SpecialValues.POSINF
        ] = sparse(g.cap_bnd[r, t, p, "UP"])

        g.par_ncapl[r, v, p] = sparse(VAR_NCAP.l[r, v, p])

        # * [UR]: undiscounting of dual variable of VAR_NCAP
        g.par_ncapm[r, t, p].where[VAR_NCAP.m[r, t, p] * g.coef_objinv[r, t, p]] = (
            VAR_NCAP.m[r, t, p] / g.coef_objinv[r, t, p]
        )

        # *---------------------------------------------------------------------
        # * Output of VAR_FLO
        # * - split by in/out
        # *---------------------------------------------------------------------
        # * emission tied to CAP/INV
        capacity = (
            VAR_NCAP.l[r, v, p].where[t[v]] + ncap_pasti[r, v, p].where[g.Pastyear[v]]
        )
        g.f_inout[g.RtpVintyr[r, v, t, p], c, "IN"].where[g.RpcCapflo[r, t, p, c]] = (
            coef_cpt[r, v, t, p] * g.ncap_com[r, v, p, c, "IN"] * capacity
            + g.coef_icom[r, v, t, p, c] * capacity
        )
        g.f_inout[g.RtpVintyr[r, v, t, p], c, "OUT"].where[g.RpcCapflo[r, t, p, c]] = (
            coef_cpt[r, v, t, p] * g.ncap_com[r, v, p, c, "OUT"] * capacity
            + g.coef_ocom[r, v, t, p, c] * capacity
        )

        # * Blending flows *** PENDING!!! Code below from EQCOMBAL ***
        # *PARAMETER F_BLND(R,T,C,TS,IO)  //;
        # *  SUM(OPR$BLE_OPR(R,C,OPR),
        # *    RTCS_TSFR(R,T,C,S,'ANNUAL') * BLE_BAL(R,T,C,OPR) * VAR_BLND(R,T,C,OPR)
        # *  ) +
        # * emissions due to blending operations
        # *  SUM(BLE_ENV(R,COM,BLE,OPR),
        # *      ENV_BL(R,COM,BLE,OPR,T) * VAR_BLND(R,T,BLE,OPR)
        # *  ) +

        # *---------------------------------------------------------------------
        # * Process flows
        # *---------------------------------------------------------------------
        f_in, f_out, f_inout, f_inouts, par_flo, par_ire = (
            g.f_in,
            g.f_out,
            g.f_inout,
            g.f_inouts,
            g.par_flo,
            g.par_ire,
        )
        # * Flow by IN/OUT
        # * main flows & emissions
        f_in[r, v, t, p, c, s].where[g.Top[r, p, c, "IN"]] = sparse(
            par_flo[r, v, t, p, c, s]
        )
        f_out[r, v, t, p, c, s].where[g.Top[r, p, c, "OUT"]] = sparse(
            par_flo[r, v, t, p, c, s]
        )
        # * IRE flows
        # * [UR] maybe exports as negativ values for net imports in primary energy balance ?
        f_in[r, v, t, p, c, s] = sparse(par_ire[r, v, t, p, c, s, "EXP"])
        f_out[r, v, t, p, c, s] = sparse(par_ire[r, v, t, p, c, s, "IMP"])
        # * Aux flows & emissions tied to INV/CAP
        f_in[r, v, t, p, c, "ANNUAL"].where[f_inout[r, v, t, p, c, "IN"]] = (
            f_in[r, v, t, p, c, "ANNUAL"] + f_inout[r, v, t, p, c, "IN"]
        )
        f_out[r, v, t, p, c, "ANNUAL"].where[f_inout[r, v, t, p, c, "OUT"]] = (
            f_out[r, v, t, p, c, "ANNUAL"] + f_inout[r, v, t, p, c, "OUT"]
        )
        # * IRE Aux flows & emissions
        f_in[r, v, t, p, c, s].where[f_inouts[r, v, t, p, c, s, "IN"]] = (
            f_in[r, v, t, p, c, s] + f_inouts[r, v, t, p, c, s, "IN"]
        )
        f_out[r, v, t, p, c, s].where[f_inouts[r, v, t, p, c, s, "OUT"]] = (
            f_out[r, v, t, p, c, s] + f_inouts[r, v, t, p, c, s, "OUT"]
        )
        # * Storage in/output flows
        f_in[r, v, t, p, c, s].where[g.RpcsVar[r, p, c, s]] = sparse(
            g.VAR_SIN.l[r, v, t, p, c, s]
        )
        f_out[r, v, t, p, c, s].where[g.RpcsVar[r, p, c, s]] = sparse(
            g.VAR_SOUT.l[r, v, t, p, c, s] * g.stg_eff[r, v, p]
        )

    def exec4(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        r, v, t, p, c, s, ts, cur = g.r, g.v, g.t, g.p, g.c, g.s, g.ts, g.cur
        RtpCptyr, RtpVintyr, Rtc, obj_disc, vda_disc = (
            g.RtpCptyr,
            g.RtpVintyr,
            g.Rtc,
            g.obj_disc,
            g.vda_disc,
        )
        with Loop(cur):
            g.cst_invv[RtpCptyr[r, v, t, p]] = sparse(
                g.par_objinv[r, v, t, p, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_decv[RtpCptyr[r, v, t, p]] = sparse(
                g.par_objdec[r, v, t, p, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_salv[r, v, p] = sparse(g.par_objsal[r, v, p, cur])
            g.cst_latv[g.Rtp[r, t, p]] = sparse(
                g.par_objlat[r, t, p, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_fixv[RtpCptyr[r, v, t, p]] = sparse(
                g.par_objfix[r, v, t, p, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_actv[RtpVintyr[r, v, t, p], ts] = sparse(
                g.par_objact[r, v, t, p, ts, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_elsv[Rtc[r, t, c]] = sparse(
                g.par_objels[r, t, c, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_flov[RtpVintyr[r, v, t, p], c, s] = sparse(
                g.par_objflo[r, v, t, p, c, s, cur] * (1.0 / obj_disc[r, t, cur])
            )
            g.cst_comv[Rtc[r, t, c], ts] = sparse(
                g.par_objcom[r, t, c, ts, cur] * (1.0 / obj_disc[r, t, cur])
            )

        # *--------------------------------------------------------------------------
        # * Production (PRD) and Difference between production and consumption (NET)
        # *--------------------------------------------------------------------------

        g.par_comprdl[r, t, c, s] = sparse(g.VAR_COMPRD.l[r, t, c, s])
        g.par_comprdm[r, t, c, s] = sparse(
            g.VAR_COMPRD.m[r, t, c, s] * (1.0 / vda_disc[r, t])
        )
        g.par_comnetl[r, t, c, s] = sparse(g.VAR_COMNET.l[r, t, c, s])
        g.par_comnetm[r, t, c, s] = sparse(
            g.VAR_COMNET.m[r, t, c, s] * (1.0 / vda_disc[r, t])
        )

        # *--------------------------------------------------------------------------
        # * Undiscounted annual shadow price of commodity balance and peaking equation
        # *--------------------------------------------------------------------------

        g.par_combalem[r, t, c, s] = sparse(
            g.eqe_combal.m[r, t, c, s] * (1.0 / vda_disc[r, t])
        )
        g.par_combalgm[r, t, c, s] = sparse(
            g.eqg_combal.m[r, t, c, s] * (1.0 / vda_disc[r, t])
        )
        g.par_peakm[r, t, g.cg, s] = sparse(
            g.eq_peak.m[r, t, g.cg, s] * (1.0 / vda_disc[r, t])
        )

    def exec5(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        r, t, s, ucn, par_ucfxm, vda_disc = (
            g.r,
            g.t,
            g.s,
            g.ucn,
            g.par_ucfxm,
            g.vda_disc,
        )
        par_ucfxm[ucn, "NONE", "NONE", "NONE"] = sparse(g.VAR_UC.m[ucn])
        par_ucfxm[ucn, r, "NONE", "NONE"] = sparse(g.VAR_UCR.m[ucn, r])
        par_ucfxm[ucn, "NONE", t, "NONE"] = sparse(g.VAR_UCT.m[ucn, t])
        par_ucfxm[ucn, r, t, "NONE"] = sparse(
            g.VAR_UCRT.m[ucn, r, t] * (1.0 / vda_disc[r, t])
        )
        par_ucfxm[ucn, "NONE", t, s] = sparse(g.VAR_UCTS.m[ucn, t, s])
        par_ucfxm[ucn, r, t, s] = sparse(
            g.VAR_UCRTS.m[ucn, r, t, s] * (1.0 / vda_disc[r, t])
        )

    def exec_options(
        self: RptmainRpt,
    ) -> None:
        g = self.tc
        g.f_inout.setRecords(None)
        g.f_inouts.setRecords(None)
        g.FIoset.setRecords(None)

    def exec6(self: RptmainRpt, timesed: str) -> None:
        g = self.tc
        r, cur, obv, sum_obj, VAR_OBJ = g.r, g.cur, g.obv, g.sum_obj, g.VAR_OBJ
        g.reg_wobj[r, "INV", cur] = (
            Sum(obv, sum_obj["OBJINV", obv] * VAR_OBJ.l[r, obv, cur])
            - VAR_OBJ.l[r, "OBJSAL", cur]
        )
        g.reg_wobj[r, "FIX", cur] = Sum(
            obv, sum_obj["OBJFIX", obv] * VAR_OBJ.l[r, obv, cur]
        )
        g.reg_wobj[r, "VAR", cur] = Sum(
            obv, sum_obj["OBJVAR", obv] * VAR_OBJ.l[r, obv, cur]
        )
        if timesed == "YES":
            g.reg_wobj[r, "ELS", cur] = (
                SpecialValues.EPS
                + g.VAR_OBJELS.l[r, "LO", cur]
                - g.VAR_OBJELS.l[r, "UP", cur]
            )
        else:
            # not EPS + 0: SpecialValues.EPS is -0.0, so Python would fold it to 0
            g.reg_wobj[r, "ELS", cur] = SpecialValues.EPS
