# solve_stp.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * SOLVE.stp is the code for handling stepped solution of TIMES
# *   arg1 - mod
# *=============================================================================*


from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from gamspy import (
    Domain,
    Equation,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Smax,
    Smin,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, abs, floor, power, project, same_as

from core.base_class import GamsClass
from core.bnd_cum_mod import bnd_cum_mod_GP
from core.bnd_ucw_mod import bnd_ucw_mod_GP
from core.bndmain_mod import bndmain_mod_GP
from core.clearsol_stc import ClearsolStc
from core.clearsol_stp import clearsol_stp_GP
from core.coef_alt_lin import CoefAltLin
from core.eqobsalv_mod import eqobsalv_prepro_GP
from core.pextlevs_stc import pextlevs_stc
from core.solve_mod import solve_mod_GP

if TYPE_CHECKING:
    from gamspy import Alias
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

# The queue entries a compile-time $BATINCLUDE left behind, replayed once per
# pass of the stepped solution loop.
DeferredQueue = list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]]


def scalar_value(param: Parameter) -> float:
    """Read a GAMS scalar the way GAMS does.

    ``Parameter.toValue()`` raises ``ValidationError`` while the scalar has never
    been assigned; GAMS reads that state as ``0``.
    """
    if param.records is None:
        return 0.0
    return float(param.toValue())


def capture_deferred(
    g: TimesModelClass, build: Callable[[], GamsClass]
) -> tuple[GamsClass, DeferredQueue]:
    """Compile a sub-module now, but keep its execution-time statements for later.

    ``solve.stp`` ``$BATINCLUDE``s modules from inside its ``WHILE`` body: GAMS
    expands the include once at compile time and re-executes the statements on
    every pass. ``TimesModelClass.run`` iterates ``execution_list``, so a child
    cannot enqueue while the loop is running - its entries are lifted out of the
    queue here and replayed per iteration instead.
    """
    start = len(g.execution_list)
    module = build()
    pending = g.execution_list[start:]
    del g.execution_list[start:]
    return module, pending


def replay(pending: DeferredQueue) -> None:
    for func, args, kwargs in pending:
        func(*args, **kwargs)


class SolveStp(GamsClass):
    """Translation unit for solve.stp"""

    # Instance attributes
    module_name: str = "solve_stp"
    gams_source: str = "solve.stp"

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
        self.env.set_scoped("stepped", "YES")
        if (self.env.spines.upper() != "YES") and (self.env.stages.upper() == "YES"):
            self.env.set_scoped("stepped", "NO")

        if self.env.stepped == "NO" and self.env.is_set("timestep"):
            raise Exception("Stepped TIMES Not available with STAGES/SENSIS!")

        if not self.env.var_uc == "YES":
            raise Exception("Invalid VAR_UC setting for stepped mode.")

        if self.env.rpoint != "NO":
            self.env.set_scoped("solve_now", "NO")

        if not self.env.is_set("timestep"):
            self.env.set_scoped("timestep", "999")
            self.env.set_scoped("stepped", "NO")

        self.declarations()

        # * Copy previous marginals to preseve freezed results
        if self.env.is_set("fixboh") and self.env.stages == "YES":
            self.tc.enqueue(
                self.set_previous_marginals, eq=self.env.eq, swt=self.env.swt_GP
            )

        g = self.tc
        # $ SETLOCAL SW1 '' SETLOCAL SW2
        # $ IFI %STAGES%==YES $SETLOCAL SW2 ",'1',SOW" SETLOCAL SW1 S_
        sw1 = ""
        sw2: tuple[str | Set | Alias, ...] = ()
        if self.env.stages.upper() == "YES":
            sw2 = ("1", g.Sow)
            sw1 = "S_"

        if self.env.spines.upper() == "YES":
            self.include(ClearsolStc(self.tc, self.env, arg1="DEF"))

        var = self.env.var
        self.tc.enqueue(
            self.exec_solve_stp_before_solve,
            timestep=int(self.env.timestep),
            fixboh=self.env.fixboh if self.env.is_set("fixboh") else 0,
            fixboh_is_set=self.env.is_set("fixboh"),
            rtpx=self.env.rtpx,
            cli=self.env.cli,
            sysprefix=self.env.sysprefix,
            sw1=sw1,
            sw2=sw2,
            var=var,
            sow=self.env.sow_GP,
            stages=self.env.stages,
            uc_cli_defined=self.tc.defined("UC_CLI"),
            macro=self.env.macro,
            eq=self.env.eq,
            swt=self.env.swt_GP,
            abs_=self.env.abs,
        )

        # $IF NOT '%CTST%'=='' $BATINCLUDE coef_alt.lin STP
        coef_alt_lin_stp: DeferredQueue = []
        if self.env.ctst != "":
            module, coef_alt_lin_stp = capture_deferred(
                self.tc,
                lambda: CoefAltLin(tc=self.tc, env=self.env, arg1="STP"),
            )
            self.include(module)

        self.tc.enqueue(
            self.exec_solve_stp_stepped_solve_and_tail,
            arg1=self.arg1,
            stepped=self.env.stepped,
            cli=self.env.cli,
            sensis=self.env.sensis,
            ctst=self.env.ctst,
            capjd=self.env.capjd_GP,
            declif=self.env.declif,
            vnret_defined=self.tc.defined("VNRET"),
            rtpx=self.env.rtpx,
            spines=self.env.spines,
            solve_now=self.env.solve_now,
            damage=self.env.damage,
            micro=self.env.micro,
            macro=self.env.macro,
            etl=self.env.etl,
            solmip=self.env.solmip,
            mixlp=self.env.mixlp if self.env.is_set("mixlp") else "",
            nonlp=self.env.nonlp if self.env.is_set("nonlp") else "",
            memclean=self.env.memclean,
            eq=self.env.eq,
            var=self.env.var,
            timesed=self.env.timesed,
            var_dam_defined=self.tc.defined(f"{var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
            sow=self.env.sow_GP,
            swt=self.env.swt_GP,
            reduce=self.env.reduce,
            dflbl=self.env.dflbl,
            mx=self.env.mx,
            pgprim=self.env.pgprim,
            swd_GP=self.env.swd_GP,
            r_t_GP=self.env.r_t_GP,
            var_uc=self.env.var_uc,
            rts=self.env.rts(),
            stochastic_symbols_declared={
                "S_NCAP_BND": self.tc.defined("S_NCAP_BND"),
                "S_CAP_BND": self.tc.defined("S_CAP_BND"),
                "S_COM_BNDNET": self.tc.defined("S_COM_BNDNET"),
                "S_COM_BNDPRD": self.tc.defined("S_COM_BNDPRD"),
            },
            stages=self.env.stages,
            eotime=self.env.eotime,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
            bnd_ucw_defined={
                f"{var}_UC": self.tc.defined(f"{var}_UC"),
                f"{var}_UCR": self.tc.defined(f"{var}_UCR"),
                f"{var}_UCT": self.tc.defined(f"{var}_UCT"),
                f"{var}_UCRT": self.tc.defined(f"{var}_UCRT"),
                f"{var}_UCTS": self.tc.defined(f"{var}_UCTS"),
                f"{var}_UCRTS": self.tc.defined(f"{var}_UCRTS"),
            },
            tm_hsx_defined=self.tc.defined("TM_HSX"),
            sw1=sw1,
            sw2=sw2,
            coef_alt_lin_stp=coef_alt_lin_stp,
        )

        self.tc.enqueue(
            self.exec_solve_stp_cleanup,
            var=self.env.var,
            sow=self.env.sow_GP,
            swt=self.env.swt_GP,
            eq=self.env.eq,
        )

    def declarations(self) -> None:
        g = self.tc
        m = g.container

        g.presol = Parameter(m, name="PRESOL", records=1)
        g.UcRn = Set(m, name="UC_RN", domain=[g.ucn, g.allr])
        g.RtpIre = Set(
            m,
            name="RTP_IRE",
            domain=[g.r, g.t, g.p, g.ie],
            description="IRE equations with fixed regions",
        )
        g.IreRpr = Set(
            m,
            name="IRE_RPR",
            domain=[g.r, g.p, g.r, g.ie],
            description="All regions REG linked to IRE process by equations in R",
        )
        g.IreFxt = Set(
            m,
            name="IRE_FXT",
            domain=[g.r, g.t, g.p],
            description="IRE with some linked regions fixed at T",
        )
        g.stp_uct = Parameter(m, name="STP_UCT", domain=[g.j, g.allr, g.ucnA, g.ll])
        g.stp_div = Parameter(m, name="STP_DIV", domain=[g.j, g.r, g.t, g.p])
        g.uc_bnd = Parameter(
            m, name="UC_BND", domain=[g.j, g.allr, g.ucnA, g.ll, g.s, g.lA]
        )
        g.par_cumflom = Parameter(
            m, name="PAR_CUMFLOM", domain=[g.r, g.p, g.c, g.ll, g.ll]
        )
        g.par_ucr = Parameter(m, name="PAR_UCR", domain=[g.ucn, g.allr])

    def set_previous_marginals(
        self: SolveStp,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
    ) -> None:
        g = self.tc
        Rtc, s = g.Rtc, g.s
        g.get_equation(f"{eq}G_COMBAL").m[Rtc, s, *swt] = sparse(g.eqg_combal.m[Rtc, s])
        g.get_equation(f"{eq}E_COMBAL").m[Rtc, s, *swt] = sparse(g.eqe_combal.m[Rtc, s])
        g.get_equation(f"{eq}_PEAK").m[Rtc, s, *swt] = sparse(g.eq_peak.m[Rtc, s])

    def exec_solve_stp_before_solve(
        self,
        timestep: int,
        fixboh: int,
        fixboh_is_set: bool,
        rtpx: str,
        cli: str,
        sysprefix: str,
        sw1: str,
        sw2: tuple[str | Set | Alias, ...],
        var: str,
        sow: SowGPType,
        stages: str,
        uc_cli_defined: bool,
        macro: str,
        eq: str,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
        abs_: str,
    ) -> None:
        g = self.tc
        (r, v, t, tt, p, c, s, ie, ll, bd, side, ucn) = (
            g.r,
            g.v,
            g.t,
            g.tt,
            g.p,
            g.c,
            g.s,
            g.ie,
            g.ll,
            g.bd,
            g.side,
            g.ucn,
        )
        (Subt, Backward, Forward, RtPp, no_rt, reg_fixt, Bdneq) = (
            g.Subt,
            g.Backward,
            g.Forward,
            g.RtPp,
            g.no_rt,
            g.reg_fixt,
            g.Bdneq,
        )
        UcRn, ucgrptype, comvar = g.UcRn, g.ucgrptype, g.comvar

        # *---------------------------------------------------------------------
        # * Establish partitioning of T into fixed, current, and pending
        # * BACKWARD(T) = fixed T
        # * SUBT(T) = current T
        # * FORWARD(T) = pending T
        g.yr_v1[...] = 0
        g.yr_vl[...] = timestep
        g.my_fyear[...] = 0
        reg_fixt[r].where[Number(0)] = 0
        if scalar_value(g.g_overlap):
            g.g_overlap[...] = Max(SpecialValues.EPS, g.g_overlap)
        else:
            g.g_overlap[...] = floor(g.yr_vl / 2)
        if fixboh_is_set:
            g.yr_v1[...] = abs(fixboh)
            reg_fixt[r].where[~reg_fixt[r]] = g.yr_v1
        if rtpx == "X":
            g.my_fyear[...] = 1
        g.f[...] = Sum(g.Miyr1[t], g.m[t])
        reg_fixt[r].where[reg_fixt[r] < g.f] = 0
        g.yr_v1[...] = Smin(Domain(r, t).where[g.m[t] > reg_fixt[r]], g.m[t])
        g.z[...] = g.yr_v1 + g.yr_vl
        Subt[t].where[g.m[t] < g.yr_v1] = False
        Subt[t].where[g.m[t] >= g.z] = False
        Backward.setRecords(None)
        Forward.setRecords(None)
        project(source=g.RhsCombal, target=g.RtcNet)  # type: ignore[arg-type]
        project(source=g.RhsComprd, target=g.RtcPrd)  # type: ignore[arg-type]
        Backward[t].where[g.m[t] < g.yr_v1] = True
        Forward[t] = tt[t] - Backward[t] - Subt[t]
        RtPp[r, t] = g.m[t] > reg_fixt[r]
        no_rt[r, t] = ~RtPp[r, t]

        # *---------------------------------------------------------------------
        # * Clear previous solution for projection years & ensure VAR_ACT loadpoint
        clearsol_stp_GP(
            g=g,
            arg1="",
            var=var,
            sow=sow,
            eq=eq,
            swt=swt,
            cli=cli,
            abs_=abs_,
            macro=macro,
            stages=stages,
        )
        g.VAR_ACT.m[g.Rvt, p, s] = 0
        if (g.VAR_UC.l[f"{sysprefix}SOLVE_STATUS"] + 0).toValue() == 0:
            Trackp, RpPrc = g.Trackp, g.RpPrc
            project(source=g.VAR_ACT, target=Trackp)  # type: ignore[arg-type]
            project(source=g.VAR_FLO, target=RpPrc)  # type: ignore[arg-type]
            RpPrc[Trackp] = False
            g.VAR_ACT.l[g.RtpVintyr[r, v, t, p], s].where[RpPrc[r, p]] = sparse(
                Sum(
                    g.RpcPg[g.RpStd[r, p], c],
                    g.VAR_FLO.l[r, v, t, p, c, s] * (1 / g.prc_actflo[r, v, p, c]),
                )
            )
            g.VAR_ACT.l[g.RtpVintyr[r, v, t, p], s].where[~Trackp[r, p]] = sparse(
                Sum(
                    g.RpcIre[g.RpcPg[r, p, c], ie].where[g.RpAire[r, p, ie]],
                    g.VAR_IRE.l[r, v, t, p, c, s, ie] * (1 / g.prc_actflo[r, v, p, c]),
                )
            )
            Trackp.setRecords(None)
            RpPrc.setRecords(None)
        g.VAR_COMNET.l[g.RhsCombal[g.Rtc, s]].where[~g.com_proj[g.Rtc]] = sparse(
            g.eqg_combal.l[g.Rtc, s]
        )

        # *---------------------------------------------------------------------
        # * Copy FX UC RHS, COM_CUM and CAP_BND to UP/LO to support relaxation,
        # * removing FX bounds at the same time
        sw1_cap_bnd = g.get_parameter(f"{sw1}CAP_BND")
        sw1_cap_bnd[r, t, p, bd, *sw2].where[sw1_cap_bnd[r, t, p, "FX", *sw2]] = (
            sw1_cap_bnd[r, t, p, "FX", *sw2].where[Bdneq[bd]]
        )
        g.uc_rhs[ucn, bd].where[g.uc_rhs[ucn, "FX"]] = g.uc_rhs[ucn, "FX"].where[
            Bdneq[bd]
        ]
        g.uc_rhsr[r, ucn, bd].where[g.uc_rhsr[r, ucn, "FX"]] = g.uc_rhsr[
            r, ucn, "FX"
        ].where[Bdneq[bd]]
        g.uc_rhst[ucn, t, bd].where[g.uc_rhst[ucn, t, "FX"]] = g.uc_rhst[
            ucn, t, "FX"
        ].where[Bdneq[bd]]
        g.uc_rhsts[ucn, t, s, bd].where[g.uc_rhsts[ucn, t, s, "FX"]] = g.uc_rhsts[
            ucn, t, s, "FX"
        ].where[Bdneq[bd]]
        g.uc_rhsrt[r, ucn, t, bd].where[g.uc_rhsrt[r, ucn, t, "FX"]] = g.uc_rhsrt[
            r, ucn, t, "FX"
        ].where[Bdneq[bd]]
        g.uc_rhsrts[r, ucn, t, s, bd].where[g.uc_rhsrts[r, ucn, t, s, "FX"]] = (
            g.uc_rhsrts[r, ucn, t, s, "FX"].where[Bdneq[bd]]
        )
        g.prc_dynuc[ucn, side, r, ll, p, ucgrptype, bd].where[
            g.prc_dynuc[ucn, "RHS", r, ll, p, ucgrptype, "FX"]
        ] = g.prc_dynuc[ucn, side, r, ll, p, ucgrptype, "FX"].where[Bdneq[bd]]

        # * Find UC equations with negative coefficients
        uc_coefficients: list[tuple[Parameter, tuple[SET_OR_ALIAS, ...]]] = [
            (g.uc_cap, (ucn, side, r, t, p)),
            (g.uc_ncap, (ucn, side, r, t, p)),
            (g.uc_act, (ucn, side, r, t, p, s)),
            (g.uc_flo, (ucn, side, r, t, p, c, s)),
            (g.uc_ire, (ucn, side, r, t, p, c, s, ie)),
            (g.uc_com, (ucn, comvar, side, r, t, c, s, ucgrptype)),
        ]
        for coefficient, indices in uc_coefficients:
            with (
                Loop(
                    Domain(*indices).where[(~UcRn[ucn, r]).where[coefficient[*indices]]]
                ),
                If(coefficient[*indices] * g.uc_sign[side] < 0),
            ):
                UcRn[ucn, r] = True
        with Loop(g.UcMapIre[ucn, r, p, c, "IMP"].where[g.ComUnit[r, c, "UCU"]]):
            UcRn[ucn, r] = True
        if uc_cli_defined:
            cmvar = g.CmVar
            with (
                Loop(
                    Domain(ucn, side, r, t, cmvar).where[
                        g.uc_cli[ucn, side, r, t, cmvar]
                    ]
                ),
                If(g.uc_cli[ucn, side, r, t, cmvar] * g.uc_sign[side] < 0),
            ):
                UcRn[ucn, r] = True
        UcRn[ucn, "IMPEXP"] = sparse(Sum(UcRn[ucn, r], Number(1)))

        # * Collect all capacity-related UCs
        with Loop(Domain(ucn, side, r, t, p).where[g.uc_cap[ucn, side, r, t, p]]):
            g.RUc[r, ucn] = True
        # * Flag to use variables for all CAP_BND
        Rtp = g.Rtp
        g.RtpVarp[Rtp[r, t, p]].where[g.cap_bnd[Rtp, "UP"] + g.cap_bnd[Rtp, "LO"]] = (
            True
        )
        g.RtpCapyr.setRecords(None)
        g.RtpCapyr[g.RtpCptyr[r, v, t, p]].where[
            g.VAR_NCAP.l[r, v, p] + g.ncap_pasti[r, v, p]
        ] = True
        g.VAR_CAP.l[g.RtpVarp[RtPp[r, t], p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.coef_cpt[r, v, t, p]
            * (g.VAR_NCAP.l[r, v, p].where[tt[v]] + g.ncap_pasti[r, v, p]),
        )

        # *---------------------------------------------------------------------
        # * Save some original data
        g.stp_uct["1", g.UcTSum] = 1
        g.stp_uct["2", g.UcTSucc] = 1
        g.stp_uct["3", g.UcTEach] = 1
        if scalar_value(g.altobj) > 1:
            g.stp_div["1", r, t, p] = sparse(g.obj_divi[r, t, p])
            g.stp_div["2", r, t, p] = sparse(g.obj_diviv[r, t, p])
            g.stp_div["3", r, t, p] = sparse(g.obj_diviii[r, t, p])

    def exec_solve_stp_stepped_solve_and_tail(
        self,
        arg1: str,
        cufscal: int,
        cucscal: int,
        stepped: str,
        rtpx: str,
        spines: str,
        solve_now: str,
        damage: str,
        micro: str,
        macro: str,
        etl: str,
        solmip: str,
        mixlp: str,
        nonlp: str,
        memclean: str,
        eq: str,
        var: str,
        timesed: str,
        var_dam_defined: bool,
        var_scap_defined: bool,
        sow: SowGPType,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
        reduce: str,
        mx: str,
        pgprim: str,
        swd_GP: tuple[Set | Alias] | tuple[()],
        r_t_GP: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        var_uc: str,
        rts: str,
        stochastic_symbols_declared: dict[str, bool],
        stages: str,
        eotime: int,
        dflbl: str,
        bnd_ucw_defined: dict[str, bool],
        ctst: Literal["", "**EPS", "**0", "1"],
        capjd: ImplicitParameter | Number,
        declif: str,
        vnret_defined: bool,
        sensis: str,
        tm_hsx_defined: bool,
        sw1: str,
        sw2: tuple[str | Set | Alias, ...],
        cli: str,
        coef_alt_lin_stp: DeferredQueue,
    ) -> None:
        g = self.tc
        # $ SETLOCAL TOLR '3E-6' SETLOCAL TOLA '1E-4' SETLOCAL TOLX '1E-5'
        # $IF DEFINED TM_HSX $SETLOCAL TOLR '1E-7' SETLOCAL TOLA 1E-6
        tolr = 1e-7 if tm_hsx_defined else 3e-6
        tola = 1e-6 if tm_hsx_defined else 1e-4
        tolx = 1e-5

        (r, v, t, tt, p, c, s, ie, j, ll, year, bd, lA, ucn, cur) = (
            g.r,
            g.v,
            g.t,
            g.tt,
            g.p,
            g.c,
            g.s,
            g.ie,
            g.j,
            g.ll,
            g.year,
            g.bd,
            g.lA,
            g.ucn,
            g.cur,
        )
        (cg, k, jot, life, age, allr, allreg, upt, comvar, ucgrptype) = (
            g.cg,
            g.k,
            g.jot,
            g.life,
            g.age,
            g.allr,
            g.allreg,
            g.upt,
            g.comvar,
            g.ucgrptype,
        )
        (Subt, Backward, Forward, RtPp, no_rt, reg_fixt, Fil, Rtp, Bdneq) = (
            g.Subt,
            g.Backward,
            g.Forward,
            g.RtPp,
            g.no_rt,
            g.reg_fixt,
            g.Fil,
            g.Rtp,
            g.Bdneq,
        )
        (UcT, UcTSum, UcTSucc, UcTEach, UcRSum, UcREach, RUc, RUct) = (
            g.UcT,
            g.UcTSum,
            g.UcTSucc,
            g.UcTEach,
            g.UcRSum,
            g.UcREach,
            g.RUc,
            g.RUct,
        )
        (uc_bnd, uc_rhs, uc_rhsr, uc_rhst, uc_rhsts, uc_rhsrt, uc_rhsrts) = (
            g.uc_bnd,
            g.uc_rhs,
            g.uc_rhsr,
            g.uc_rhst,
            g.uc_rhsts,
            g.uc_rhsrt,
            g.uc_rhsrts,
        )
        (RtpVintyr, RtpCptyr, RpcsVar, PrcTs, ComTs, Rtc) = (
            g.RtpVintyr,
            g.RtpCptyr,
            g.RpcsVar,
            g.PrcTs,
            g.ComTs,
            g.Rtc,
        )
        sw1_cap_bnd = g.get_parameter(f"{sw1}CAP_BND")
        sw1_com_cum = g.get_parameter(f"{sw1}COM_CUM")
        sw1_flo_cum = g.get_parameter(f"{sw1}FLO_CUM")

        (VAR_ACT, VAR_FLO, VAR_IRE, VAR_SIN, VAR_SOUT, VAR_UPS, VAR_UPT, VAR_UDP) = (
            g.get_variable(f"{var}_ACT"),
            g.get_variable(f"{var}_FLO"),
            g.get_variable(f"{var}_IRE"),
            g.get_variable(f"{var}_SIN"),
            g.get_variable(f"{var}_SOUT"),
            g.get_variable(f"{var}_UPS"),
            g.get_variable(f"{var}_UPT"),
            g.get_variable(f"{var}_UDP"),
        )
        (VAR_COMNET, VAR_COMPRD, VAR_ELAST, VAR_NCAP, VAR_CAP, VAR_SCAP) = (
            g.get_variable(f"{var}_COMNET"),
            g.get_variable(f"{var}_COMPRD"),
            g.get_variable(f"{var}_ELAST"),
            g.get_variable(f"{var}_NCAP"),
            g.get_variable(f"{var}_CAP"),
            g.get_variable(f"{var}_SCAP"),
        )
        (VAR_CUMFLO, VAR_CUMCOM, VAR_BLND) = (
            g.get_variable(f"{var}_CUMFLO"),
            g.get_variable(f"{var}_CUMCOM"),
            g.get_variable(f"{var}_BLND"),
        )

        # $IF %STEPPED%==YES WHILE(CARD(SUBT),
        # A GAMSPy `While` cannot hold a `Model.solve()`, so the GAMS WHILE is a
        # Python loop over SUBT instead: each pass solves, which synchronises the
        # container, so SUBT shrinks exactly as the GAMS loop makes it. For
        # STEPPED != YES, GAMS never compiles the WHILE wrapper at all - the body
        # runs once as straight-line code and `$GOTO ENDSTEP` (solve.stp:295)
        # skips the post-solve tail below. We mirror that with an explicit
        # `break` right after the solve instead of relying on SUBT to empty.
        while len(g.Subt):
            Backward[t] = g.m[t] < g.yr_v1
            Forward[Subt] = False
            no_rt[r, t[Backward]] = 1
            RtPp[r, t] = Subt[t].where[~no_rt[r, t]]
            v[Forward] = False
            # * Re-define End-of-Horizon
            if Subt.number_records:
                g.miyr_vl[...] = Smax(Subt[t], g.e[t])
            g.YEoh.setRecords(None)
            g.MiyrL.setRecords(None)
            g.YEoh[g.Eohyears].where[
                (g.yearval[g.Eohyears] <= g.miyr_vl).where[
                    g.yearval[g.Eohyears] >= g.minyr
                ]
            ] = True
            with Loop(g.Miyr1[year]):
                g.z[...] = g.miyr_vl - g.yearval[year]
                g.MiyrL[year + g.z] = True

            # *-----------------------------------------------------------------
            # * Complete adjusted model
            # * Adjust divisor data when appropriate
            replay(coef_alt_lin_stp)
            # * We must recompute OBJ_LIFE and salvage values
            g.obj_life[k[ll], r, jot, life, cur].where[
                g.obj_life[k, r, jot, life, cur]
            ] = (
                Sum(
                    Domain(g.Opyear[life, age], g.YEoh[ll + (Ord(age) - 1)]),
                    g.obj_disc[r, g.YEoh, cur],
                )
                + SpecialValues.EPS
            )
            if stepped == "YES":
                eqobsalv_prepro_GP(
                    g=g,
                    arg1="STP",
                    timestep_is_set=True,
                    stepped=stepped,
                    ctst=ctst,
                    capjd=capjd,
                    etl=etl,
                    declif=declif,
                    vnret_defined=vnret_defined,
                )
            g.rvprl[r, k, p].where[g.rvprl[r, k, p]] = Max(
                1,
                Smax(RtpCptyr[r, g.Vnt[k, v[t]], p], g.yearval[v]) - g.yearval[k],
            )

            # *-----------------------------------------------------------------
            # * Handle Dynamic constraints and Multi-regional UC relaxation
            # * Remove UC_T_SUM if it does not overlap with SUBT
            Rxx, uncd1 = g.Rxx, g.uncd1
            Rxx.setRecords(None)
            uncd1.setRecords(None)
            Rxx[UcREach[r, ucn], r].where[
                Sum(UcTSum[r, ucn, t].where[RtPp[r, t]], Number(1))
            ] = True
            uncd1[ucn].where[
                Sum(UcTSum[UcRSum[r, ucn], t].where[RtPp[r, t]], Number(1))
            ] = True
            UcTSum[r, ucn, t].where[Forward[t]] = False
            UcTSum[r, ucn, t].where[(~uncd1[ucn]).where[~Rxx[r, ucn, r]]] = False
            if scalar_value(g.presol):
                g.VAR_UC.l[ucn[uncd1]] = 0
                g.VAR_UCR.l[ucn, r].where[Rxx[r, ucn, r]] = 0
            # * Remove UC_T_EACH for all but SUBT
            # * Remove UC_T_SUCC until not completely fixed or if even partly pending
            UcT.setRecords(None)
            with Loop(UcTEach[UcRSum[r, ucn], t].where[RtPp[r, t]]):
                UcT[ucn, t] = True
            with Loop(UcTSucc[UcRSum[r, ucn], t].where[RtPp[r, t]]):
                UcT[ucn, t] = True
            UcTEach[UcRSum[r, ucn], t].where[~UcT[ucn, t]] = False
            UcTSucc[UcRSum[r, ucn], t].where[
                g.UcDyndir[r, ucn, "RHS"].where[~UcT[ucn, t]]
            ] = False
            UcTEach[UcREach[r, ucn], t].where[~RtPp[r, t]] = False
            UcTSucc[UcREach[r, ucn], t].where[
                g.UcDyndir[r, ucn, "RHS"].where[~RtPp[r, t]]
            ] = False
            UcTSucc[UcTSucc[r, ucn, t - 1]] = g.UcDyndir[r, ucn, "RHS"] + RtPp[r, t]
            UcT[ucn, t].where[~Sum(r.where[no_rt[r, t]], 1)] = False
            if cli.upper() == "YES":
                with Loop(t.where[~Sum(r, ~no_rt[r, t])]):
                    g.cm_maxc[ll, cg].where[g.Superyr[t, ll]] = 0

            with Loop(bd):
                UcTSucc[r, ucn, t].where[g.UcDynbnd[ucn, bd]] = RtPp[r, t]

            # * RHS and Bounds Relaxation
            if Backward.number_records or scalar_value(g.my_fyear):
                uc_bnd.setRecords(None)
                RUct.setRecords(None)
                RUct[RUc[r, ucn], t].where[UcTEach[r, ucn, t] + UcTSucc[r, ucn, t]] = (
                    True
                )
                with Loop(UcRSum[RUc[r, ucn]]):
                    UcT[ucn, t].where[RUct[r, ucn, t]] = True
                RUct[r, ucn, t].where[~reg_fixt[r]] = False
                # * Set into UC_BND the RHS corrected by actual slack level,
                # * if RHS already violated
                uc_bnd["1", "IMPEXP", ucn, "0", "ANNUAL", "UP"].where[
                    uc_rhs[ucn, "UP"]
                ] = Max(
                    uc_rhs[ucn, "UP"],
                    g.VAR_UC.l[ucn]
                    - Number(SpecialValues.POSINF).where[~g.VAR_UC.l[ucn]],
                )
                uc_bnd["2", r, ucn, "0", "ANNUAL", "UP"].where[
                    uc_rhsr[r, ucn, "UP"]
                ] = Max(
                    uc_rhsr[r, ucn, "UP"],
                    g.VAR_UCR.l[ucn, r]
                    - Number(SpecialValues.POSINF).where[~g.VAR_UCR.l[ucn, r]],
                )
                uc_bnd["3", "IMPEXP", ucn, t, "ANNUAL", "UP"].where[
                    uc_rhst[ucn, t, "UP"]
                ] = Max(
                    uc_rhst[ucn, t, "UP"],
                    g.VAR_UCT.l[ucn, t]
                    - Number(SpecialValues.POSINF).where[~g.VAR_UCT.l[ucn, t]],
                )
                uc_bnd["4", "IMPEXP", ucn, t, s, "UP"].where[
                    uc_rhsts[ucn, t, s, "UP"]
                ] = Max(
                    uc_rhsts[ucn, t, s, "UP"],
                    g.VAR_UCTS.l[ucn, t, s]
                    - Number(SpecialValues.POSINF).where[~g.VAR_UCTS.l[ucn, t, s]],
                )
                uc_bnd["5", r, ucn, t, "ANNUAL", "UP"].where[
                    uc_rhsrt[r, ucn, t, "UP"]
                ] = Max(
                    uc_rhsrt[r, ucn, t, "UP"],
                    g.VAR_UCRT.l[ucn, r, t]
                    - Number(SpecialValues.POSINF).where[~g.VAR_UCRT.l[ucn, r, t]],
                )
                uc_bnd["6", r, ucn, t, s, "UP"].where[uc_rhsrts[r, ucn, t, s, "UP"]] = (
                    Max(
                        uc_rhsrts[r, ucn, t, s, "UP"],
                        g.VAR_UCRTS.l[ucn, r, t, s]
                        - Number(SpecialValues.POSINF).where[
                            ~g.VAR_UCRTS.l[ucn, r, t, s]
                        ],
                    )
                )
                uc_bnd["1", "IMPEXP", ucn, "0", "ANNUAL", "LO"].where[
                    uc_rhs[ucn, "LO"]
                ] = Min(
                    uc_rhs[ucn, "LO"],
                    g.VAR_UC.l[ucn]
                    + Number(SpecialValues.POSINF).where[~g.VAR_UC.l[ucn]],
                )
                uc_bnd["2", r, ucn, "0", "ANNUAL", "LO"].where[
                    uc_rhsr[r, ucn, "LO"]
                ] = Min(
                    uc_rhsr[r, ucn, "LO"],
                    g.VAR_UCR.l[ucn, r]
                    + Number(SpecialValues.POSINF).where[~g.VAR_UCR.l[ucn, r]],
                )
                uc_bnd["3", "IMPEXP", ucn, t, "ANNUAL", "LO"].where[
                    uc_rhst[ucn, t, "LO"]
                ] = Min(
                    uc_rhst[ucn, t, "LO"],
                    g.VAR_UCT.l[ucn, t]
                    + Number(SpecialValues.POSINF).where[~g.VAR_UCT.l[ucn, t]],
                )
                uc_bnd["4", "IMPEXP", ucn, t, s, "LO"].where[
                    uc_rhsts[ucn, t, s, "LO"]
                ] = Min(
                    uc_rhsts[ucn, t, s, "LO"],
                    g.VAR_UCTS.l[ucn, t, s]
                    + Number(SpecialValues.POSINF).where[~g.VAR_UCTS.l[ucn, t, s]],
                )
                uc_bnd["5", r, ucn, t, "ANNUAL", "LO"].where[
                    uc_rhsrt[r, ucn, t, "LO"]
                ] = Min(
                    uc_rhsrt[r, ucn, t, "LO"],
                    g.VAR_UCRT.l[ucn, r, t]
                    + Number(SpecialValues.POSINF).where[~g.VAR_UCRT.l[ucn, r, t]],
                )
                uc_bnd["6", r, ucn, t, s, "LO"].where[uc_rhsrts[r, ucn, t, s, "LO"]] = (
                    Min(
                        uc_rhsrts[r, ucn, t, s, "LO"],
                        g.VAR_UCRTS.l[ucn, r, t, s]
                        + Number(SpecialValues.POSINF).where[
                            ~g.VAR_UCRTS.l[ucn, r, t, s]
                        ],
                    )
                )
                # * Add relaxation tolerances;
                # * absolute only if both positive+negative coefficients
                uc_bnd[j, allr, ucn, ll, s, "UP"].where[
                    uc_bnd[j, allr, ucn, ll, s, "UP"]
                ] = (
                    uc_bnd[j, allr, ucn, ll, s, "UP"]
                    + abs(uc_bnd[j, allr, ucn, ll, s, "UP"]) * tolr
                    + Number(tola).where[g.UcRn[ucn, allr]]
                )
                uc_bnd[j, allr, ucn, ll, s, "LO"].where[
                    uc_bnd[j, allr, ucn, ll, s, "LO"]
                ] = (
                    uc_bnd[j, allr, ucn, ll, s, "LO"]
                    - abs(uc_bnd[j, allr, ucn, ll, s, "LO"]) * tolr
                    - Number(tola).where[g.UcRn[ucn, allr]]
                )
                # * Copy back to RHS
                # * (VAR bounds would be cleared in sensitivity analysis)
                uc_rhs[ucn, Bdneq[bd]] = sparse(
                    uc_bnd["1", "IMPEXP", ucn, "0", "ANNUAL", bd]
                )
                uc_rhsr[r, ucn, Bdneq[bd]].where[reg_fixt[r]] = sparse(
                    uc_bnd["2", r, ucn, "0", "ANNUAL", bd]
                )
                uc_rhst[UcT[ucn, t], Bdneq[bd]] = sparse(
                    uc_bnd["3", "IMPEXP", ucn, t, "ANNUAL", bd]
                )
                uc_rhsts[UcT[ucn, t], s, Bdneq[bd]] = sparse(
                    uc_bnd["4", "IMPEXP", ucn, t, s, bd]
                )
                uc_rhsrt[RUct[r, ucn, t], Bdneq[bd]] = sparse(
                    uc_bnd["5", r, ucn, t, "ANNUAL", bd]
                )
                uc_rhsrts[RUct[r, ucn, t], s, Bdneq[bd]] = sparse(
                    uc_bnd["6", r, ucn, t, s, bd]
                )
                # * Handle other important dynamic constraints
                with Loop(
                    Domain(r, t, tt).where[no_rt[r, t].where[same_as(t + 1, tt)]]
                ):
                    g.prc_dynuc[ucn, "LHS", Rtp[r, tt, p], ucgrptype, "UP"].where[
                        g.prc_dynuc[ucn, "RHS", r, "0", p, ucgrptype, "UP"]
                    ] = g.prc_dynuc[ucn, "LHS", r, tt, p, ucgrptype, "UP"] * (1 + tolr)
                    g.prc_dynuc[ucn, "LHS", Rtp[r, tt, p], ucgrptype, "LO"].where[
                        g.prc_dynuc[ucn, "RHS", r, "0", p, ucgrptype, "LO"]
                    ] = g.prc_dynuc[ucn, "LHS", r, tt, p, ucgrptype, "LO"] * (1 - tolx)
                sw1_com_cum[r, comvar, year, ll, c, "UP", *sw2].where[
                    reg_fixt[r].where[sw1_com_cum[r, comvar, year, ll, c, "UP", *sw2]]
                ] = Max(
                    sw1_com_cum[r, comvar, year, ll, c, "UP", *sw2],
                    Min(
                        sw1_com_cum[r, comvar, year, ll, c, "UP", *sw2],
                        g.VAR_CUMCOM.l[r, c, comvar, year, ll] * cucscal,
                    )
                    * (1 + tolr),
                )
                sw1_com_cum[r, comvar, year, ll, c, "LO", *sw2].where[reg_fixt[r]] = (
                    sparse(sw1_com_cum[r, comvar, year, ll, c, "LO", *sw2] * (1 - tolr))
                )
                sw1_flo_cum[r, p, c, year, ll, "UP", *sw2].where[
                    reg_fixt[r].where[sw1_flo_cum[r, p, c, year, ll, "UP", *sw2]]
                ] = Max(
                    sw1_flo_cum[r, p, c, year, ll, "UP", *sw2],
                    Min(
                        sw1_flo_cum[r, p, c, year, ll, "UP", *sw2],
                        g.VAR_CUMFLO.l[r, p, c, year, ll] * cufscal,
                    )
                    * (1 + tolr),
                )
                sw1_flo_cum[r, p, c, year, ll, "LO", *sw2].where[reg_fixt[r]] = sparse(
                    sw1_flo_cum[r, p, c, year, ll, "LO", *sw2] * (1 - tolr)
                )
                sw1_cap_bnd[r, t, p, "UP", *sw2].where[
                    sw1_cap_bnd[r, t, p, "UP", *sw2]
                ] = Max(
                    sw1_cap_bnd[r, t, p, "UP", *sw2],
                    g.VAR_CAP.l[r, t, p] * (1 + tolr),
                )
                sw1_cap_bnd[r, t, p, "LO", *sw2] = sparse(
                    sw1_cap_bnd[r, t, p, "LO", *sw2] * (1 - tolr)
                )

            # $BATINCLUDE bnd_ucw.%1
            bnd_ucw_mod_GP(
                g=g,
                arg1=Number(1),
                var=var,
                stages=stages,
                swd_GP=swd_GP,
                sow_GP=sow,
                defined_symbols=bnd_ucw_defined,
            )
            # * Redefine UC_T according to current flags
            project(source=UcTSucc, target=g.UcRtsuc)  # type: ignore[arg-type]
            if g.reg_cumcst.number_records:
                with Loop(Domain(r, t).where[no_rt[r, t]]):
                    g.reg_cumcst[r, year, ll, g.costcat, cur, "UP"].where[
                        g.Superyr[t, ll]
                    ] = 0

            # *-----------------------------------------------------------------
            def fix_backward_levels() -> None:
                """The body of ``LOOP(R, ...)`` guarded by ``'%RTPX%'==X``."""
                # * Activities and flows
                VAR_ACT.fx[RtpVintyr[r, v, Backward[t], p], s, *sow].where[
                    PrcTs[r, p, s]
                ] = g.VAR_ACT.l[r, v, t, p, s]
                VAR_FLO.fx[RtpVintyr[r, v, Backward[t], p], c, s, *sow].where[
                    RpcsVar[r, p, c, s] * g.RpFlo[r, p]
                ] = g.VAR_FLO.l[r, v, t, p, c, s]
                VAR_IRE.fx[RtpVintyr[r, v, Backward[t], p], c, s, ie, *sow].where[
                    RpcsVar[r, p, c, s] * g.RpcIre[r, p, c, ie]
                ] = g.VAR_IRE.l[r, v, t, p, c, s, ie]
                VAR_SIN.fx[RtpVintyr[r, v, Backward[t], p], c, s, *sow].where[
                    RpcsVar[r, p, c, s] * g.RpcStg[r, p, c]
                ] = g.VAR_SIN.l[r, v, t, p, c, s]
                VAR_SOUT.fx[RtpVintyr[r, v, Backward[t], p], c, s, *sow].where[
                    RpcsVar[r, p, c, s] * g.RpcStg[r, p, c]
                ] = g.VAR_SOUT.l[r, v, t, p, c, s]
                VAR_UPS.fx[RtpVintyr[r, v, Backward[t], p], s, bd[lA], *sow].where[
                    g.RpsUps[r, p, s]
                ] = g.VAR_UPS.l[r, v, t, p, s, lA]
                VAR_UPT.fx[RtpVintyr[r, v, Backward[t], p], s, upt, *sow].where[
                    g.RpsUps[r, p, s].where[g.RpDp[r, p]]
                ] = g.VAR_UPT.l[r, v, t, p, s, upt]
                VAR_UDP.fx[RtpVintyr[r, v, Backward[t], p], s, bd[lA], *sow].where[
                    PrcTs[r, p, s].where[g.RpUpr[r, p, bd]]
                ] = g.VAR_UDP.l[r, v, t, p, s, lA]
                # * Commodities
                VAR_COMNET.fx[g.RtcNet[r, Backward[t], c], s, *sow].where[
                    ComTs[r, c, s]
                ] = g.VAR_COMNET.l[r, t, c, s]
                VAR_COMPRD.fx[g.RtcPrd[r, Backward[t], c], s, *sow].where[
                    ComTs[r, c, s]
                ] = g.VAR_COMPRD.l[r, t, c, s]
                VAR_ELAST.fx[Rtc[r, Backward[t], c], s, j, bd, *sow].where[
                    ComTs[r, c, s].where[g.Rcj[r, c, j, bd]]
                ] = g.VAR_ELAST.l[Rtc, s, j, bd]
                if var_dam_defined:
                    VAR_DAM = g.get_variable(f"{var}_DAM")
                    g.VAR_DAM.l[r, t, c, bd, j].where[Number(0)] = 0
                    VAR_DAM.fx[r, t[Backward], c, bd, j, *sow].where[
                        (Ord(j) <= g.dam_step[r, c, bd]).where[g.dam_step[r, c, "FX"]]
                    ] = g.VAR_DAM.l[r, t, c, bd, j]
                # * Capacities
                VAR_NCAP.fx[r, Backward[t], p, *sow].where[g.Rp[r, p]] = Max(
                    SpecialValues.EPS, g.VAR_NCAP.l[r, t, p]
                )
                VAR_CAP.up[Rtp[r, Backward[t], p], *sow] = SpecialValues.POSINF
                VAR_CAP.lo[Rtp[r, Backward[t], p], *sow] = 0
                NoRvp = g.NoRvp
                NoRvp.setRecords(None)
                NoRvp[g.RtpVarp[r, Subt[t], p]].where[
                    Sum(RtpCptyr[r, Backward[tt], t, p], 1)
                ] = True
                VAR_CAP.up[NoRvp[r, t, p], *sow].where[g.cap_bnd[r, t, p, "UP"]] = (
                    g.cap_bnd[r, t, p, "UP"]
                )
                VAR_CAP.lo[NoRvp[r, t, p], *sow].where[g.cap_bnd[r, t, p, "LO"]] = (
                    g.cap_bnd[r, t, p, "LO"]
                )
                VAR_SCAP.fx[RtpCptyr[r, v, Backward[t], p], *sow].where[
                    g.PrcRcap[r, p]
                ] = g.VAR_SCAP.l[r, v, t, p]
                # * Cumulative variables
                g.z[...] = Smax(t, g.m[t]) > g.miyr_vl
                Fil[ll] = g.z * (g.miyr_vl < g.yearval[ll])
                # * Get new modifiers for flexible model horizon
                if sensis.upper() != "YES":
                    bnd_cum_mod_GP(
                        g=g,
                        arg1=comvar,
                        stages=stages,
                        eotime=eotime,
                        var=var,
                        sow=sow,
                        cufscal=cufscal,
                        cucscal=cucscal,
                        macro=macro,
                    )
                # * Remove LO bounds if years only partially in current horizon
                # * and no adjustment for shorter horizon
                VAR_CUMFLO.lo[r, p, c, year, ll, *sow].where[
                    (~g.flo_cum[r, p, c, year, ll, "N"]).where[Fil[ll]]
                ] = 0
                VAR_CUMCOM.lo[r, c, comvar, year, ll, *sow].where[
                    (~g.com_cum[r, comvar, year, ll, c, "N"]).where[Fil[ll]]
                ] = 0
                # * Blending
                g.VAR_BLND.l[RtPp, g.Ble, g.Opr] = 0
                VAR_BLND.fx[r, Backward[t], g.Ble, g.Opr, *sow].where[
                    g.BleOpr[r, g.Ble, g.Opr]
                ] = g.VAR_BLND.l[r, t, g.Ble, g.Opr]

            if rtpx == "X":
                with Loop(r):
                    Backward[t] = no_rt[r, t]  # type: ignore[assignment]
                    Subt[t] = RtPp[r, t]
                    fix_backward_levels()
                Backward[t] = g.m[t] < g.yr_v1
                Subt[t] = tt[t] - Backward[t] - Forward[t]
            else:
                fix_backward_levels()

            # *-----------------------------------------------------------------
            if scalar_value(g.my_fyear):
                Trackpc, IreRpr, Rtpx, IreFxt, RtpIre = (
                    g.Trackpc,
                    g.IreRpr,
                    g.Rtpx,
                    g.IreFxt,
                    g.RtpIre,
                )
                Reg, Com = g.Reg, g.Com
                # * Find all regions REG linked to IRE equations in region R
                Trackpc[g.Rpc[r, p, c]].where[
                    g.RpcEqire[r, p, c, "EXP"] + g.RpcMarket[r, p, c, "EXP"]
                ] = True
                with Loop(Domain(Trackpc[r, p, c], g.TopIre[r, c, Reg, Com, p])):
                    IreRpr[r, p, Reg, "EXP"] = True
                Trackpc.setRecords(None)
                with Loop(
                    Domain(g.TopIre[r, c, Reg, Com, p], g.RpcEqire[Reg, p, Com, "IMP"])
                ):
                    IreRpr[Reg, p, r, "IMP"] = True
                Rtpx.setRecords(None)
                Rtpx[Rtp[r, t, p]].where[g.RpIre[r, p]] = RtPp[r, t]
                with Loop(Domain(Reg, ie)):
                    Rtpx[Rtp[r, t, p]].where[
                        RtPp[Reg, t].where[IreRpr[r, p, Reg, ie]]
                    ] = True
                IreFxt[Rtp[r, t, p]].where[no_rt[r, t].where[g.RpIre[r, p]]] = True
                with Loop(Domain(Reg, ie)):
                    IreFxt[r, t, p].where[
                        no_rt[Reg, t].where[IreRpr[r, p, Reg, ie]]
                    ] = True
                # * Remove RTP for IRE fixed in all linked regions,
                # * and save marginals
                if scalar_value(g.presol):
                    g.par_ipric.setRecords(None)
                    g.eq_ire.m[r, t, p, c, ie, s].where[Number(0)] = 0
                g.par_ipric[IreFxt, c, s, ie].where[
                    g.par_ipric[IreFxt, c, s, ie] == 0
                ] = sparse(g.eq_ire.m[IreFxt, c, ie, s])
                # * Relax all fixed flows in regions with IRE equations
                RtpIre.setRecords(None)
                with Loop(Reg):
                    RtpIre[Rtpx[r, t, p], ie].where[
                        IreRpr[r, p, Reg, ie].where[no_rt[r, t]]
                    ] = True
                VAR_IRE.up[RtpVintyr[r, v, t, p], c, s, ie, *sow].where[
                    RtpIre[r, t, p, ie]
                    * RpcsVar[r, p, c, s]
                    * g.RpcIreio[r, p, c, ie, "IN"]
                ] = g.VAR_IRE.l[r, v, t, p, c, s, ie] * (
                    1 + tolx * power(8, -Number(1).where[g.xpt[ie]])
                )
                VAR_IRE.lo[RtpVintyr[r, v, t, p], c, s, ie, *sow].where[
                    RtpIre[r, t, p, ie]
                    * RpcsVar[r, p, c, s]
                    * g.RpcIreio[r, p, c, ie, "IN"]
                ] = g.VAR_IRE.l[r, v, t, p, c, s, ie] * (
                    1 - tolx * power(8, -Number(1).where[g.imp[ie]])
                )
                if reduce == "YES":
                    with Loop(ie):
                        VAR_ACT.up[RtpVintyr[r, v, t, p], s, *sow].where[
                            RtpIre[r, t, p, ie] * PrcTs[r, p, s] * g.RpPgact[r, p]
                        ] = g.VAR_ACT.l[r, v, t, p, s] * (
                            1 + tolx * power(8, -Number(1).where[g.xpt[ie]])
                        )
                        VAR_ACT.lo[RtpVintyr[r, v, t, p], s, *sow].where[
                            RtpIre[r, t, p, ie] * PrcTs[r, p, s] * g.RpPgact[r, p]
                        ] = g.VAR_ACT.l[r, v, t, p, s] * (
                            1 - tolx * power(8, -Number(1).where[g.imp[ie]])
                        )
                # * Remove IRE_BND from fixed regions with no related IRE equation,
                # * and all IRE_XBND from fixed regions
                Rxx.setRecords(None)
                with (
                    Loop(
                        Domain(r, t, c, s, allreg, ie, bd).where[
                            no_rt[r, t].where[g.ire_bnd[r, t, c, s, allreg, ie, bd]]
                        ]
                    ),
                    If(~Sum(g.RpcEqire[r, p, c, ie].where[Rtpx[r, t, p]], 1)),
                    If(~Sum(g.RpcMarket[r, p, c, ie].where[Rtpx[r, t, p]], 1)),
                ):
                    Rxx[r, c, ie] = True
                g.ire_bnd[r, t, c, s, allreg, ie, bd].where[
                    no_rt[r, t].where[Rxx[r, c, ie]]
                ] = 0
                g.ire_xbnd[r, t, c, s, ie, bd].where[no_rt[r, t]] = 0

            # *-----------------------------------------------------------------
            def fix_forward_levels() -> None:
                """The body of ``LOOP(R, ...)`` guarded by ``'%RTPX%'==X``."""
                # * Activities and flows
                g.VAR_ACT.fx[RtpVintyr[r, v, Forward[t], p], s].where[
                    PrcTs[r, p, s]
                ] = 0
                g.VAR_FLO.fx[RtpVintyr[r, v, Forward[t], p], c, s].where[
                    RpcsVar[r, p, c, s] * g.RpFlo[r, p]
                ] = 0
                # VAR_IRE is deliberately left free (commented out upstream)
                g.VAR_SIN.fx[RtpVintyr[r, v, Forward[t], p], c, s].where[
                    RpcsVar[r, p, c, s] * g.RpcStg[r, p, c]
                ] = 0
                g.VAR_SOUT.fx[RtpVintyr[r, v, Forward[t], p], c, s].where[
                    RpcsVar[r, p, c, s] * g.RpcStg[r, p, c]
                ] = 0
                # * Commodities
                g.VAR_COMNET.fx[g.RtcsVarc[r, Forward[t], c, s]] = 0
                g.VAR_COMPRD.fx[g.RtcsVarc[r, Forward[t], c, s]] = 0
                g.VAR_ELAST.fx[g.RtcsVarc[r, Forward[t], c, s], j, bd].where[
                    g.Rcj[r, c, j, bd]
                ] = 0
                # * Capacities
                g.VAR_CAP.lo[Rtp[r, Forward[t], p]] = 0
                g.VAR_CAP.up[Rtp[r, Forward[t], p]] = sparse(g.cap_bnd[Rtp, "UP"])
                # * Blending
                g.VAR_BLND.fx[r, Forward[t], g.Ble, g.Opr].where[
                    g.BleOpr[r, g.Ble, g.Opr]
                ] = 0

            if rtpx == "X":
                Fil[t] = Forward[t]
                with Loop(r):
                    Forward[t] = Fil[t].where[~no_rt[r, t]]
                    fix_forward_levels()
                Forward[t] = Fil[t]
            else:
                fix_forward_levels()

            # *-----------------------------------------------------------------
            # BRATIO / SOLVEOPT are GAMS solve options. GAMSPy runs every
            # statement as its own GAMS job, so an OPTION statement here cannot
            # reach the solve; main.py pins basis_detection_threshold/
            # merge_strategy on the shared Options instead. Emitted verbatim to
            # keep the generated source in step with solve.stp.
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code="""
* Reject starting basis if equations were removed:
IF(CARD(NO_RT)+CARD(FORWARD), OPTION BRATIO=1);
OPTION SOLVEOPT=MERGE;
""",
            )
            # * Save last cum marginal
            if scalar_value(g.presol) == 0:
                g.par_cumflom[r, p, c, year, ll] = sparse(
                    g.VAR_CUMFLO.m[r, p, c, year, ll]
                )
                g.par_ucr[ucn, "IMPEXP"] = sparse(g.VAR_UC.m[ucn])
                g.par_ucr[ucn, r] = sparse(g.VAR_UCR.m[ucn, r])

            # *-----------------------------------------------------------------
            # $ SET EXT mod / $IFI %STAGES%==YES $SET EXT stc
            # $ IFI %SPINES%==YES $SET EXT mod / $ BATINCLUDE solve.%EXT%
            ext = (
                "stc"
                if (stages.upper() == "YES" and spines.upper() != "YES")
                else "mod"
            )
            if ext == "mod":
                solve_mod_GP(
                    module=self,
                    equations=self.equations,
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
                )
            elif ext == "stc":
                raise NotImplementedError("Still needs implementation")
            else:
                raise ValueError(f"Unexpected value {ext} for solve_<ext>.")

            g.presol[...] = 0
            # $IF NOT %STEPPED%==YES $GOTO ENDSTEP - skip the rest of this pass
            if stepped != "YES":
                break
            # *-----------------------------------------------------------------
            # * Restore last cum marginal
            g.VAR_UC.m[ucn].where[g.VAR_UC.m[ucn] == 0] = sparse(
                g.par_ucr[ucn, "IMPEXP"]
            )
            g.VAR_UCR.m[ucn, r].where[g.VAR_UCR.m[ucn, r] == 0] = sparse(
                g.par_ucr[ucn, r]
            )
            g.VAR_CUMFLO.m[r, p, c, year, ll].where[
                g.VAR_CUMFLO.m[r, p, c, year, ll] == 0
            ] = sparse(g.par_cumflom[r, p, c, year, ll])
            # * Adjust SUBT
            Subt[t] = Subt[t - 1]
            g.z[...] = Smin(Forward[t], g.b[t])
            g.yr_v1[...] = Smin(Subt[t].where[g.m[t] >= g.z - g.g_overlap], g.m[t])
            g.z[...] = g.yr_v1 + g.yr_vl
            Subt[t].where[g.m[t] < g.z] = True
            Subt[t].where[g.m[t] < g.yr_v1] = False
            # *-----------------------------------------------------------------
            # * Restore some original data
            v[t] = True
            UcTSum[r, ucn, t] = sparse(g.stp_uct["1", r, ucn, t])
            UcTSucc[r, ucn, t] = sparse(g.stp_uct["2", r, ucn, t])
            UcTEach[r, ucn, t] = sparse(g.stp_uct["3", r, ucn, t])
            if spines.upper() == "YES":
                # pextlevs.stc has no GAMSPy twin for the period control (arg2),
                # so the fragment - including its LOOP(R,...) wrapper - stays raw.
                loop_open = "LOOP(R, BACKWARD(T)=NO_RT(R,T);" if rtpx == "X" else ""
                loop_close = ");" if rtpx == "X" else ""
                self.tc.add_gams_code(
                    module=self,
                    phase="run",
                    code=loop_open
                    + pextlevs_stc(
                        tc=self.tc,
                        arg1="'1'",
                        arg2="(BACKWARD)",
                        eq=eq,
                        var=var,
                        timesed=timesed,
                        var_dam_defined=var_dam_defined,
                        var_scap_defined=var_scap_defined,
                    )
                    + loop_close,
                )
            elif rtpx == "X":
                with Loop(r):
                    Backward[t] = no_rt[r, t]  # type: ignore[assignment]
            # * Reset bounds
            # $BATINCLUDE bndmain.%1 %1 1
            bndmain_mod_GP(
                g=self.tc,
                module=self,
                arg1=arg1,
                arg2="1",
                var=var,
                swd_GP=swd_GP,
                sow_GP=sow,
                swt_GP=swt,
                r_t_GP=r_t_GP,
                stages=stages,
                timesed=timesed,
                reduce=reduce,
                dflbl=dflbl,
                mx=mx,
                pgprim=pgprim,
                eotime=eotime,
                cufscal=cufscal,
                cucscal=cucscal,
                macro=macro,
                var_uc=var_uc,
                rts=rts,
                model_name=self.model_name,
                bnd_ucw_defined=bnd_ucw_defined,
                stochastic_symbols_declared=stochastic_symbols_declared,
            )

    def exec_solve_stp_cleanup(
        self: SolveStp,
        var: str,
        sow: SowGPType,
        swt: tuple[SET_OR_ALIAS, ...] | tuple[()],
        eq: str,
    ) -> None:
        g = self.tc
        r, v, t, p, c, s, ie = (g.r, g.v, g.t, g.p, g.c, g.s, g.ie)
        (VAR_NCAP, VAR_ACT, VAR_FLO, VAR_IRE) = (
            g.get_variable(f"{var}_NCAP"),
            g.get_variable(f"{var}_ACT"),
            g.get_variable(f"{var}_FLO"),
            g.get_variable(f"{var}_IRE"),
        )
        # *---------------------------------------------------------------------
        # * Remove superfluous values
        VAR_NCAP.l[r, t, p, *sow].where[
            (VAR_NCAP.l[r, t, p, *sow] == 0).where[VAR_NCAP.l[r, t, p, *sow]]
        ] = 0
        VAR_NCAP.m[r, t, p, *sow].where[g.no_rt[r, t]] = 0
        VAR_ACT.m[r, v, t, p, s, *sow].where[g.no_rt[r, t]] = 0
        VAR_FLO.m[r, v, t, p, c, s, *sow].where[g.no_rt[r, t]] = 0
        VAR_IRE.m[r, v, t, p, c, s, ie, *sow].where[g.no_rt[r, t]] = 0
        if scalar_value(g.my_fyear):
            g.get_equation(f"{eq}_IRE").m[g.IreFxt[r, t, p], c, ie, s, *swt] = sparse(
                g.par_ipric[r, t, p, c, s, ie]
            )
