# rptmisc_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * RPTMISC.rpt: Miscellaneous shared reportings
# *  arg1 - Prefix for parameter names (optional)
# *  arg2 - SOW, (optional)
# *  arg3 - SOW
# *=============================================================================*
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import (
    Card,
    Domain,
    Else,
    For,
    If,
    Loop,
    Ord,
    Parameter,
    Product,
    Set,
    Smin,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, project, sign

from core.base_class import GamsClass
from core.utils import extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias

    from core.utils import SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

_ONCE_COUNTER_NAME = "RPTMISC_ONCE"


def _once_counter(tc: TimesModelClass) -> Parameter:
    """A dedicated scalar counter used only to give a one-pass ``For()`` loop
    something to iterate over -- not a TIMES model parameter, not referenced
    anywhere else. A numeric ``Parameter`` never adds an element to the
    shared GAMS universe (``*``) the way a driver ``Set`` with a literal
    record would -- that leaked into every other universal-alias symbol
    (``ITEM``, ``U2``, ``U3``, ``U4``, ...), since they're all aliases of the
    same universe. Created lazily so repeated ``RptmiscRpt`` instantiations
    (once each from rpt_ext_mlf.py and rptmain_tm.py) share the same symbol
    instead of colliding on the name.
    """
    if tc.declared(_ONCE_COUNTER_NAME):
        once: Parameter = tc.container[_ONCE_COUNTER_NAME]  # type: ignore
    else:
        once = Parameter(
            tc.container,
            name=_ONCE_COUNTER_NAME,
            description="Singleton driver counter; forces exactly one For pass.",
        )
    return once


@dataclass
class RptmiscRptConfig:
    """Strongly typed data contract for rptmisc.rpt."""

    # %1 - Prefix for parameter names (optional)
    arg1: str = ""
    # %2 - SOW, (optional): the leading index of the %1 prefixed parameters
    arg2: tuple[Set | Alias | str, ...] | tuple[()] = ()
    # %3 - %SOW%: the trailing SOW index of the solution variables
    arg3: tuple[Set | Alias | str, ...] | tuple[()] = ()
    # %4 / %5 - extra trailing index/weight of the %VART%/%VAR% variables;
    # only supplied by rptmain.stc, which is not yet routed through this class
    arg4: tuple[Set | Alias | str, ...] | tuple[()] = ()
    arg5: tuple[Set | Alias | str, ...] | tuple[()] = ()


class RptmiscRpt(GamsClass):
    """Translation unit for rptmisc.rpt."""

    # Instance attributes
    module_name: str = "rptmisc_rpt"
    gams_source: str = "rptmisc.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: RptmiscRptConfig | None = None,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config if config is not None else RptmiscRptConfig()
        self.compile()

    def compile(self) -> None:
        cc = self.config
        if cc.arg4:
            # A non-blank %4 (this class's arg4) is only ever supplied by
            # rptmain.stc's own BATINCLUDE -- no other real caller passes one
            # (see the NOTE in exec_rptmisc_rpt_GP for the full grep-confirmed
            # list). That caller's raw text still goes through the legacy
            # module-level rptmisc_rpt() function directly, not this class, so
            # a non-blank arg4 reaching here is genuinely unimplemented rather
            # than silently wrong -- fail loudly instead of guessing how to
            # route it through wrap_in_sum/vart_domain.
            raise NotImplementedError(
                "rptmisc.rpt: a non-blank %4 (this class's arg4) is not supported."
            )
        self.tc.enqueue(
            self.exec_rptmisc_rpt_GP,
            arg1=cc.arg1,
            arg2=cc.arg2,
            arg3=cc.arg3,
            arg4=cc.arg4,
            arg5=cc.arg5,
            var=self.env.var,
            cufscal=self.env.cufscal,
            var_uc=self.env.var_uc,
            sysprefix=self.env.sysprefix,
            vart_GP=self.env.vart_GP,
            sws_GP=self.env.sws_GP,
            sow_GP=self.env.sow_GP,
            eq=self.env.eq,
            rpt_flots=self.env.rpt_flots,
            stages=self.env.stages,
            solans=self.env.solans,
            if_defined_vnret=self.tc.defined("VNRET"),
            if_defined_eqe_ucrtp=self.tc.defined("EQE_UCRTP"),
            if_not_defined_eq_g_ucmax=not self.tc.defined(f"{self.env.eq}G_UCMAX"),
        )

    def exec_rptmisc_rpt_GP(
        self: RptmiscRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        arg3: tuple[Set | Alias | str, ...] | tuple[()],
        arg4: tuple[Set | Alias | str, ...] | tuple[()],
        arg5: tuple[Set | Alias | str, ...] | tuple[()],
        var: str,
        cufscal: int,
        var_uc: str,
        sysprefix: str,
        vart_GP: tuple[str, object],
        sws_GP: tuple[Set | Alias | str, ...] | tuple[()],
        sow_GP: SowGPType,
        eq: str,
        rpt_flots: str,
        stages: str,
        solans: str,
        if_defined_vnret: bool,
        if_defined_eqe_ucrtp: bool,
        if_not_defined_eq_g_ucmax: bool,
    ) -> None:
        with For(_once_counter(self.tc), 1, 1):
            self.rptmisc_rpt_GP(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
                arg4=arg4,
                arg5=arg5,
                var=var,
                cufscal=cufscal,
                var_uc=var_uc,
                sysprefix=sysprefix,
                vart=vart_GP,
                sws=sws_GP,
                sow=sow_GP,
                eq=eq,
                rpt_flots=rpt_flots,
                stages=stages,
                solans=solans,
                if_defined_vnret=if_defined_vnret,
                if_defined_eqe_ucrtp=if_defined_eqe_ucrtp,
                if_not_defined_eq_g_ucmax=if_not_defined_eq_g_ucmax,
            )

    def rptmisc_rpt_GP(
        self: RptmiscRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        arg3: tuple[Set | Alias | str, ...] | tuple[()],
        arg4: tuple[Set | Alias | str, ...] | tuple[()],
        arg5: tuple[Set | Alias | str, ...] | tuple[()],
        var: str,
        cufscal: int,
        var_uc: str,
        sysprefix: str,
        vart: tuple[str, object],
        sws: tuple[Set | Alias | str, ...] | tuple[()],
        sow: SowGPType,
        eq: str,
        rpt_flots: str,
        stages: str,
        solans: str,
        if_defined_vnret: bool,
        if_defined_eqe_ucrtp: bool,
        if_not_defined_eq_g_ucmax: bool,
    ) -> None:
        g = self.tc

        PAR_ACTL = g.get_parameter(f"{arg1}PAR_ACTL")
        PAR_ACTM = g.get_parameter(f"{arg1}PAR_ACTM")
        PAR_CAPL = g.get_parameter(f"{arg1}PAR_CAPL")
        PAR_PASTI = g.get_parameter(f"{arg1}PAR_PASTI")
        PAR_CUMRET = g.get_parameter(f"{arg1}PAR_CUMRET")
        PAR_CAPM = g.get_parameter(f"{arg1}PAR_CAPM")
        PAR_CAPBD = g.get_parameter(f"{arg1}PAR_CAPBD")
        PAR_NCAPL = g.get_parameter(f"{arg1}PAR_NCAPL")
        PAR_NCAPM = g.get_parameter(f"{arg1}PAR_NCAPM")
        PAR_COMPRDL = g.get_parameter(f"{arg1}PAR_COMPRDL")
        PAR_COMPRDM = g.get_parameter(f"{arg1}PAR_COMPRDM")
        PAR_COMNETL = g.get_parameter(f"{arg1}PAR_COMNETL")
        PAR_COMNETM = g.get_parameter(f"{arg1}PAR_COMNETM")
        AGG_OUT = g.get_parameter(f"{arg1}AGG_OUT")
        PAR_COMBALEM = g.get_parameter(f"{arg1}PAR_COMBALEM")
        PAR_PEAKM = g.get_parameter(f"{arg1}PAR_PEAKM")
        PAR_COMBALGM = g.get_parameter(f"{arg1}PAR_COMBALGM")
        F_IN = g.get_parameter(f"{arg1}F_IN")
        F_OUT = g.get_parameter(f"{arg1}F_OUT")
        P_OUT = g.get_parameter(f"{arg1}P_OUT")
        PAR_UCRTP = g.get_parameter(f"{arg1}PAR_UCRTP")
        PAR_UCMRK = g.get_parameter(f"{arg1}PAR_UCMRK")
        PAR_EOUT = g.get_parameter(f"{arg1}PAR_EOUT")
        PAR_NCAPR = g.get_parameter(f"{arg1}PAR_NCAPR")
        CST_ACTC = g.get_parameter(f"{arg1}CST_ACTC")
        CST_FLOC = g.get_parameter(f"{arg1}CST_FLOC")
        CST_FLOX = g.get_parameter(f"{arg1}CST_FLOX")
        PAR_CUMFLOL = g.get_parameter(f"{arg1}PAR_CUMFLOL")
        PAR_CUMFLOM = g.get_parameter(f"{arg1}PAR_CUMFLOM")
        PAR_CUMCST = g.get_parameter(f"{arg1}PAR_CUMCST")
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_CUMFLO = g.get_variable(f"{var}_CUMFLO")
        VAR_CUMCST = g.get_variable(f"{var}_CUMCST")

        g.r_df[g.r, g.t] = sign(g.coef_pvt[g.r, g.t]) / Max(
            1e-09, abs(g.coef_pvt[g.r, g.t])
        )
        rvtp = (g.r, g.v, g.t, g.p)
        rtcs = (g.r, g.t, g.c, g.s)
        # -------------------------------------------------------------------
        # Activity levels & marginals
        # -------------------------------------------------------------------
        PAR_ACTL[*arg2, g.RtpVintyr[*rvtp], g.s].where[g.PrcTs[g.r, g.p, g.s]] = sparse(
            g.VAR_ACT.l[*rvtp, g.s]
        )
        # * Shift up STS activity levels
        with Loop(
            Domain(g.RpStl[g.r, g.p, g.tsl, g.bd], g.TsGroup[g.r, g.tsl, g.ts]).where[
                g.Rlup[g.r, "DAYNITE", g.tsl]
            ]
        ):
            g.z[...] = g.g_yrfr[g.r, g.ts] * 365.0 / g.ts_cycle[g.r, g.ts]
            g.ykval[g.Vnt[g.v, g.t]] = Smin(
                g.RsBelow[g.r, g.ts, g.s], g.VAR_ACT.l[g.r, g.Vnt, g.p, g.s] / g.z
            ).where[g.NcapYes[g.r, g.v, g.p]]
            PAR_ACTL[*arg2, g.r, g.Vnt, g.p, g.s].where[
                (g.TsMap[g.r, g.ts, g.s].where[g.ykval[g.Vnt]])
            ] = g.VAR_ACT.l[g.r, g.Vnt, g.p, g.s] + g.ykval[g.Vnt] * (
                1.0 - (1.0 + g.z).where[g.RsBelow[g.r, g.ts, g.s]]
            )
        g.z[...] = g.rpt_opt["ACT", "2"] >= 0.0
        PAR_ACTM[*arg2, *rvtp, g.s].where[g.VAR_ACT.m[*rvtp, g.s]] = Round(
            g.VAR_ACT.m[*rvtp, g.s] * g.r_df[g.r, g.t], 7
        ).where[g.z]
        PAR_ACTM[*arg2, g.r, "0", g.t, g.p, g.s] = sparse(
            g.eql_actbnd.m[g.r, g.t, g.p, g.s] * g.r_df[g.r, g.t]
        )
        PAR_ACTM[*arg2, g.r, "0", g.t, g.p, g.s] = sparse(
            g.eqg_actbnd.m[g.r, g.t, g.p, g.s] * g.r_df[g.r, g.t]
        )
        PAR_ACTM[*arg2, g.r, "0", g.t, g.p, g.s] = sparse(
            g.eqe_actbnd.m[g.r, g.t, g.p, g.s] * g.r_df[g.r, g.t]
        )

        # -------------------------------------------------------------------
        # Capacity
        # -------------------------------------------------------------------
        g.RtpCapyr.setRecords(None)
        g.coef_cap.setRecords(None)
        g.RtpCapyr[g.RtpCptyr[g.r, g.tt, g.t, g.p]].where[
            g.VAR_NCAP.l[g.r, g.tt, g.p]
        ] = True
        g.VAR_CAP.m[g.Rtp].where[(~(g.VAR_CAP.m[g.Rtp]))] = sparse(g.eqe_cpt.m[g.Rtp])
        PAR_CAPL[*arg2, g.Rtp[g.r, g.t, g.p]] = Sum(
            g.RtpCapyr[g.r, g.tt, g.t, g.p],
            g.coef_cpt[g.r, g.tt, g.t, g.p] * g.VAR_NCAP.l[g.r, g.tt, g.p],
        )
        PAR_PASTI[*arg2, g.Rtp[g.r, g.t, g.p], "0"] = Sum(
            g.pyr[g.k].where[g.coef_cpt[g.r, g.k, g.t, g.p]],
            g.coef_cpt[g.r, g.k, g.t, g.p] * g.ncap_pasti[g.r, g.k, g.p]
            - g.rtforc[g.r, g.k, g.t, g.p].where[g.PyrS[g.k]],
        )
        if if_defined_vnret:
            g.coef_cap[*rvtp] = sparse(g.VAR_SCAP.l[*rvtp])
            PAR_PASTI[*arg2, g.Rtp[g.r, g.t, g.p], "€"].where[
                g.PrcRcap[g.r, g.p]
            ] = -Sum(
                g.Vnret[g.v, g.t],
                g.coef_cap[*rvtp] * g.coef_cpt[*rvtp] - g.rtforc[*rvtp],
            )
        with If(g.rpt_opt["CAP", "5"] > 0.0):
            PAR_CUMRET[*arg2, g.RtpCptyr] = sparse(g.coef_cap[g.RtpCptyr])
        PAR_CAPM[*arg2, g.Rtp[g.r, g.t, g.p]] = sparse(
            g.VAR_CAP.m[g.Rtp] * g.r_df[g.r, g.t]
        )
        PAR_CAPBD[*arg2, g.Rtp, "LO"] = sparse(g.cap_bnd[g.Rtp, "LO"])
        PAR_CAPBD[*arg2, g.RtpOff[g.Rtp], "UP"].where[g.rcap_bnd[g.Rtp, "N"]] = sparse(
            g.prc_resid[g.Rtp]
        )
        PAR_CAPBD[*arg2, g.Rtp, "UP"].where[
            (g.cap_bnd[g.Rtp, "UP"] != SpecialValues.POSINF)
        ] = sparse(g.cap_bnd[g.Rtp, "UP"])
        PAR_NCAPL[*arg2, g.Rtp[g.r, g.v, g.p]] = sparse(g.VAR_NCAP.l[g.Rtp])
        PAR_NCAPM[*arg2, g.Rtp].where[(g.VAR_NCAP.m[g.Rtp] * g.coef_objinv[g.Rtp])] = (
            g.VAR_NCAP.m[g.Rtp] / g.coef_objinv[g.Rtp]
        )

        # -------------------------------------------------------------------
        # Commodities
        # -------------------------------------------------------------------
        # Variables
        PAR_COMPRDL[*arg2, *rtcs] = sparse(g.VAR_COMPRD.l[*rtcs])
        PAR_COMPRDM[*arg2, *rtcs] = sparse(g.VAR_COMPRD.m[*rtcs] * g.r_df[g.r, g.t])
        PAR_COMNETL[*arg2, *rtcs] = sparse(g.VAR_COMNET.l[*rtcs])
        PAR_COMNETM[*arg2, *rtcs] = sparse(g.VAR_COMNET.m[*rtcs] * g.r_df[g.r, g.t])
        project(source=g.com_agg, target=g.Agr)
        AGG_OUT[*arg2, *rtcs].where[(g.RtcsVarc[*rtcs].where[g.Agr[g.r, g.c]])] = Sum(
            g.Rtc[g.r, g.t, g.Com].where[g.com_agg[g.Rtc, g.c]],
            g.com_agg[g.Rtc, g.c]
            * Sum(
                g.RtcsVarc[g.Rtc, g.ts].where[g.rs_fr[g.r, g.s, g.ts]],
                g.rs_fr[g.r, g.s, g.ts]
                * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow))
                * (
                    g.VAR_COMNET.l[g.Rtc, g.ts].where[g.RcAgp[g.r, g.Com, "LO"]]
                    + g.VAR_COMPRD.l[g.Rtc, g.ts].where[g.RcAgp[g.r, g.Com, "FX"]]
                ),
            ),
        )
        g.Agr.setRecords(None)
        # Equations
        PAR_COMBALEM[*arg2, *rtcs] = sparse(g.eqg_combal.m[*rtcs] * g.r_df[g.r, g.t])
        PAR_COMBALEM[*arg2, *rtcs] = sparse(g.eqe_combal.m[*rtcs] * g.r_df[g.r, g.t])
        PAR_PEAKM[*arg2, g.r, g.t, g.cg, g.s] = sparse(
            g.eq_peak.m[g.r, g.t, g.cg, g.s] * g.r_df[g.r, g.t]
        )
        if arg1 == "S":
            PAR_COMBALGM[*arg2, g.Rtc, g.s] = sparse(g.eqg_combal.l[g.Rtc, g.s])

        # -------------------------------------------------------------------
        # Process flows
        # -------------------------------------------------------------------
        g.uncd1.setRecords(None)
        g.RtpCapyr.setRecords(None)
        g.f_inout.setRecords(None)
        g.f_inout[*rvtp, g.c, "IN"].where[g.coef_icom[*rvtp, g.c]] = (
            g.coef_icom[*rvtp, g.c] * g.rtp_capvl[g.r, g.v, g.p]
        )
        g.f_inout[*rvtp, g.c, "OUT"].where[g.coef_ocom[*rvtp, g.c]] = (
            g.coef_ocom[*rvtp, g.c] * g.rtp_capvl[g.r, g.v, g.p]
        )
        g.f_inout[g.RtpCptyr[*rvtp], g.c, g.io].where[
            g.ncap_com[g.r, g.v, g.p, g.c, g.io]
        ] = g.f_inout[*rvtp, g.c, g.io] + (
            g.rtp_capvl[g.r, g.v, g.p] - g.coef_cap[*rvtp]
        ) * g.coef_cpt[*rvtp] * g.ncap_com[g.r, g.v, g.p, g.c, g.io] * (
            1.0 + g.coef_cio[*rvtp, g.c, g.io]
        )
        g.f_inouts[*rvtp, g.c, g.Annual[g.s], g.io].where[
            g.f_inout[*rvtp, g.c, g.io]
        ] = g.f_inouts[*rvtp, g.c, g.s, g.io] + g.f_inout[*rvtp, g.c, g.io]
        # inputs: main flows & emissions, aux flows & emissions
        F_IN[*arg2, *rvtp, g.c, g.s].where[g.Top[g.r, g.p, g.c, "IN"]] = sparse(
            g.par_flo[*rvtp, g.c, g.s]
        )
        F_IN[*arg2, *rvtp, g.c, g.s] = sparse(g.par_ire[*rvtp, g.c, g.s, "EXP"])
        F_IN[*arg2, *rvtp, g.c, g.s].where[g.RpcsVar[g.r, g.p, g.c, g.s]] = sparse(
            g.VAR_SIN.l[*rvtp, g.c, g.s]
        )
        F_IN[*arg2, *rvtp, g.c, g.s].where[g.f_inouts[*rvtp, g.c, g.s, "IN"]] = (
            F_IN[*arg2, *rvtp, g.c, g.s] + g.f_inouts[*rvtp, g.c, g.s, "IN"]
        )
        # outputs: main flows & emissions, aux flows & emissions
        g.par_flo[*rvtp, g.c, g.s].where[g.RpcsVar[g.r, g.p, g.c, g.s]] = sparse(
            g.VAR_SOUT.l[*rvtp, g.c, g.s] * g.stg_eff[g.r, g.v, g.p]
        )
        F_OUT[*arg2, *rvtp, g.c, g.s].where[g.Top[g.r, g.p, g.c, "OUT"]] = sparse(
            g.par_flo[*rvtp, g.c, g.s]
        )
        F_OUT[*arg2, *rvtp, g.c, g.s] = sparse(g.par_ire[*rvtp, g.c, g.s, "IMP"])
        F_OUT[*arg2, *rvtp, g.c, g.s].where[g.f_inouts[*rvtp, g.c, g.s, "OUT"]] = (
            F_OUT[*arg2, *rvtp, g.c, g.s] + g.f_inouts[*rvtp, g.c, g.s, "OUT"]
        )
        # -------------------------------------------------------------------
        # Filter out small values if requested
        with If(Sum(g.ucgrptype.where[g.rpt_opt[g.ucgrptype, "9"]], 1.0)):
            g.rpt_opt[g.ucgrptype, "9"].where[(g.rpt_opt[g.ucgrptype, "9"] > 0.1)] = 0.0
            g.z[...] = g.rpt_opt["ACT", "9"]
            with If(g.z > 0.0):
                PAR_ACTL[*arg2, *rvtp, g.s].where[
                    (
                        (PAR_ACTL[*arg2, *rvtp, g.s] < g.z).where[
                            PAR_ACTL[*arg2, *rvtp, g.s]
                        ]
                    )
                ] = 0.0
            g.z[...] = g.rpt_opt["CAP", "9"]
            with If(g.z > 0.0):
                PAR_CAPL[*arg2, g.Rtp].where[
                    ((PAR_CAPL[*arg2, g.Rtp] < g.z).where[PAR_CAPL[*arg2, g.Rtp]])
                ] = 0.0
                PAR_PASTI[*arg2, g.Rtp[g.r, g.t, g.p], "€"].where[
                    (
                        (abs(PAR_PASTI[*arg2, g.Rtp, "€"]) < g.z).where[
                            PAR_PASTI[*arg2, g.Rtp, "€"]
                        ]
                    )
                ] = 0.0
            g.z[...] = g.rpt_opt["NCAP", "9"]
            with If(g.z > 0.0):
                PAR_NCAPL[*arg2, g.Rtp].where[
                    ((PAR_NCAPL[*arg2, g.Rtp] < g.z).where[PAR_NCAPL[*arg2, g.Rtp]])
                ] = 0.0
            g.z[...] = g.rpt_opt["FLO", "9"]
            with If(g.z > 0.0):
                F_OUT[*arg2, *rvtp, g.c, g.s].where[
                    (
                        (abs(F_OUT[*arg2, *rvtp, g.c, g.s]) < g.z).where[
                            F_OUT[*arg2, *rvtp, g.c, g.s]
                        ]
                    )
                ] = 0.0
                F_IN[*arg2, *rvtp, g.c, g.s].where[
                    (
                        (abs(F_IN[*arg2, *rvtp, g.c, g.s]) < g.z).where[
                            F_IN[*arg2, *rvtp, g.c, g.s]
                        ]
                    )
                ] = 0.0
        # -------------------------------------------------------------------
        # If power levels or fall-back to ANNUAL is requested, set reporting at com_TS
        g.uncd1[g.ComType[g.u2]].where[g.rpt_opt[g.u2, "3"]] = (
            True  # NOTE: The OG code has domain U2(COM_TYPE), U2(NRG_TYPE), U2(NRG_TYPE)
        )
        # However, u2 is an universal alias and thus cannot be indexed.
        g.uncd1[g.nrgtype[g.u2]].where[g.rpt_opt[g.u2, "1"]] = True
        g.uncd1[g.nrgtype[g.u2]].where[g.rpt_opt[g.u2, "3"]] = True
        g.rpt_opt["FLO", "1"].where[Card(g.uncd1)] = True
        g.MyTs[g.s] = Ord(g.s) == Card(g.s)
        g.rtp_capvl.setRecords(None)
        g.Rvtpc.setRecords(None)
        g.f_inouts.setRecords(None)
        g.Rcs.setRecords(None)
        # Check for unused COM variables
        g.Rttc[g.Rtc].where[(~(Sum(g.RhsComprd[g.Rtc, g.s], 1.0)))] = True
        g.Rxx.setRecords(None)
        g.Rxx[g.Rtc].where[(~(Sum(g.RcsCombal[g.Rtc, g.s, g.bd], 1.0)))] = True
        g.z[...] = g.rpt_opt["COMPRD", "1"] <= 0.0
        with If(g.z):
            g.Rttc[g.Rtc].where[(~(g.Rxx[g.Rtc]))] = False
        with If(g.rpt_opt["FLO", "1"] < 1.0):
            if rpt_flots.upper() == "ANNUAL":
                g.Rcs[g.Rc, g.Annual] = True
        with Else():
            g.Rcs[g.ComTs] = True
        with If(Card(g.Rcs)):
            # Represent all process flows at requested timeslices
            g.f_ios[*rvtp, g.c, g.s].where[(~(g.Rcs[g.r, g.c, g.s]))] = sparse(
                F_IN[*arg2, *rvtp, g.c, g.s]
            )
            project(source=g.f_ios, target=g.Rvtpc)
            F_IN[*arg2, g.Rvtpc, g.s].where[g.f_ios[g.Rvtpc, g.s]] = 0.0
            F_IN[*arg2, g.Rvtpc[*rvtp, g.c], g.ts].where[g.Rcs[g.r, g.c, g.ts]] = F_IN[
                *arg2, g.Rvtpc, g.ts
            ] + Sum(
                g.RsTree[g.r, g.ts, g.s].where[g.f_ios[g.Rvtpc, g.s]],
                g.rs_fr[g.r, g.ts, g.s]
                * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.ts, g.s, sow))
                * g.f_ios[g.Rvtpc, g.s],
            )
            g.Rvtpc.setRecords(None)
            g.f_ios.setRecords(None)
            g.f_ios[*rvtp, g.c, g.s].where[(~(g.Rcs[g.r, g.c, g.s]))] = sparse(
                F_OUT[*arg2, *rvtp, g.c, g.s]
            )
            project(source=g.f_ios, target=g.Rvtpc)
            F_OUT[*arg2, g.Rvtpc, g.s].where[g.f_ios[g.Rvtpc, g.s]] = 0.0
            F_OUT[*arg2, g.Rvtpc[*rvtp, g.c], g.ts].where[g.Rcs[g.r, g.c, g.ts]] = (
                F_OUT[*arg2, g.Rvtpc, g.ts]
                + Sum(
                    g.RsTree[g.r, g.ts, g.s].where[g.f_ios[g.Rvtpc, g.s]],
                    g.rs_fr[g.r, g.ts, g.s]
                    * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.ts, g.s, sow))
                    * g.f_ios[g.Rvtpc, g.s],
                )
            )
            g.Rcs.setRecords(None)
            g.Rvtpc.setRecords(None)
            g.f_ios.setRecords(None)
            PAR_COMPRDL[*arg2, g.RtcsVarc[g.Rttc[g.r, g.t, g.c], g.s]] = Sum(
                Domain(g.Vnt[g.v, g.t], g.p).where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                F_OUT[*arg2, *rvtp, g.c, g.s],
            )
            # ...optional power levels
            with Loop(g.nrgtype[g.u2].where[g.rpt_opt[g.u2, "1"]]):
                g.f[...] = Round(g.rpt_opt[g.u2, "3"]) == 2.0
                P_OUT[*arg2, g.Rtpc[g.r, g.t, g.p, g.c], g.s].where[
                    (g.ComTs[g.r, g.c, g.s].where[g.NrgTmap[g.r, g.nrgtype, g.c]])
                ] = (
                    Sum(
                        g.Vnt[g.v, g.t].where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                        F_OUT[*arg2, *rvtp, g.c, g.s]
                        / g.g_yrfr[g.r, g.s]
                        / g.rpt_opt[g.u2, "1"],
                    )
                    - Sum(
                        g.Vnt[g.v, g.t].where[F_IN[*arg2, *rvtp, g.c, g.s]],
                        F_IN[*arg2, *rvtp, g.c, g.s]
                        / g.g_yrfr[g.r, g.s]
                        / g.rpt_opt[g.u2, "1"],
                    ).where[g.f]
                )
        with Else():
            PAR_COMPRDL[*arg2, g.Rttc[g.r, g.t, g.c], g.Annual] = Sum(
                Domain(g.Vnt[g.v, g.t], g.p, g.s).where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                F_OUT[*arg2, *rvtp, g.c, g.s],
            )

        if stages.upper() == "YES":
            g.rpt_opt["FLO", "3"] = 0.0
        with If(g.rpt_opt["FLO", "3"]):
            g.val_flo[*rvtp, g.c] = sparse(
                Sum(
                    g.s.where[F_IN[*arg2, *rvtp, g.c, g.s]],
                    F_IN[*arg2, *rvtp, g.c, g.s] * PAR_COMBALEM[*arg2, *rtcs],
                )
            )
            g.f_inouts[*rvtp, g.c, g.Annual, "OUT"] = sparse(
                Sum(
                    g.s.where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                    F_OUT[*arg2, *rvtp, g.c, g.s] * PAR_COMBALEM[*arg2, *rtcs],
                )
            )
            g.val_flo[*rvtp, g.c].where[g.f_inouts[*rvtp, g.c, "ANNUAL", "OUT"]] = (
                g.val_flo[*rvtp, g.c] - g.f_inouts[*rvtp, g.c, "ANNUAL", "OUT"]
            )
            g.f_inouts.setRecords(None)

        # Complete COMPRDL & COMNETL reporting
        PAR_COMPRDL[*arg2, g.Rttc[g.r, g.t, g.c], g.s].where[
            AGG_OUT[*arg2, g.Rttc, g.s]
        ] = PAR_COMPRDL[*arg2, g.Rttc, g.s] + AGG_OUT[*arg2, g.Rttc, g.s]
        PAR_COMNETL[*arg2, g.Rtc[g.Rxx[g.r, g.t, g.c]], g.s] = sparse(
            PAR_COMPRDL[*arg2, g.Rtc, g.s]
        )
        PAR_COMNETL[*arg2, g.RtcsVarc[g.Rxx[g.r, g.t, g.c], g.Annual[g.s]]] = (
            PAR_COMPRDL[*arg2, *rtcs]
            * Product(g.Rttc[g.r, g.t, g.c], g.com_ie[g.Rttc, g.s])
            - Sum(
                g.RpcCapflo[g.r, g.v, g.p, g.c].where[g.Vnt[g.v, g.t]],
                g.f_inout[*rvtp, g.c, "IN"],
            )
        )
        PAR_COMPRDL[*arg2, g.Rxx[g.Rttc[g.r, g.t, g.c]], g.s] = 0.0
        VAR_COMNET.l[g.Rtc[g.Rxx[g.r, g.t, g.c]], g.s, *arg3] = sparse(
            PAR_COMNETL[*arg2, g.Rtc, g.s]
        )
        # -------------------------------------------------------------------
        # Cumflo results (unscaling)
        PAR_CUMFLOL[*arg2, g.r, g.p, g.c, g.year, g.ll] = sparse(
            VAR_CUMFLO.l[g.r, g.p, g.c, g.year, g.ll, *arg3] * cufscal
        )
        PAR_CUMFLOM[*arg2, g.r, g.p, g.c, g.year, g.ll] = sparse(
            VAR_CUMFLO.m[g.r, g.p, g.c, g.year, g.ll, *arg5] * (1.0 / cufscal)
        )
        PAR_CUMCST[*arg2, g.r, g.year, g.ll, g.costagg, g.cur] = sparse(
            VAR_CUMCST.l[g.r, g.year, g.ll, g.costagg, g.cur, *arg3]
        )
        # Marginals of Dynamic process bounds
        if if_defined_eqe_ucrtp:
            g.eqn_ucrtp.m[g.ucn, g.r, g.t, g.p, g.ucgrptype, g.bd["FX"]] = sparse(
                g.eqe_ucrtp.m[g.ucn, g.r, g.t, g.p, g.ucgrptype, g.bd]
            )
        PAR_UCRTP[*arg2, g.ucn, g.r, g.t, g.p, g.ucgrptype] = sparse(
            Sum(
                g.bd.where[g.prc_dynuc[g.ucn, "RHS", g.r, g.t, g.p, g.ucgrptype, g.bd]],
                g.eqn_ucrtp.m[g.ucn, g.r, g.t, g.p, g.ucgrptype, g.bd]
                * (1.0 / g.coef_objinv[g.r, g.t, g.p]).where[
                    g.coef_objinv[g.r, g.t, g.p]
                ],
            )
        )
        PAR_UCRTP[*arg2, g.ucn, g.r, g.t, g.p, "ACT"] = sparse(
            Sum(
                g.bd.where[g.prc_dynuc[g.ucn, "RHS", g.r, g.t, g.p, "ACT", g.bd]],
                g.eqn_ucrtp.m[g.ucn, g.r, g.t, g.p, "ACT", g.bd] * g.r_df[g.r, g.t],
            )
        )
        with If(g.rpt_opt["COMPRD", "4"]):
            PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s] = sparse(
                g.eql_flomrk.m[g.r, g.t, g.item, g.c, g.s]
            )
            PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s] = sparse(
                g.eqg_flomrk.m[g.r, g.t, g.item, g.c, g.s]
            )
            PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s] = sparse(
                g.eqe_flomrk.m[g.r, g.t, g.item, g.c, g.s]
            )
            PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s].where[
                PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s]
            ] = (
                PAR_UCMRK[*arg2, g.r, g.t, g.item, g.c, g.s] / g.coef_pvt[g.r, g.t]
            ).where[(~(Sum(g.RxMark[g.r, g.ll, g.item, g.c, g.bd], 1.0)))]

        # -------------------------------------------------------------------
        # User constraints
        # -------------------------------------------------------------------
        if var_uc == "YES":
            VAR_UC = g.get_variable(f"{var}_UC")
            VAR_UCR = g.get_variable(f"{var}_UCR")
            # vart_GP's declared type is broader than extract_var_domain's own
            # signature (str | tuple[str, Any]) -- every real value it's ever set
            # to (utils.py's apply_sw_tags/apply_sw_notags) is a 2-tuple with a
            # str first element, matching that narrower signature.
            vart_id, vart_domain = extract_var_domain(vart)  # type: ignore[arg-type]
            VART_UCT = g.get_variable(f"{vart_id}_UCT")
            VART_UCRT = g.get_variable(f"{vart_id}_UCRT")
            VART_UCTS = g.get_variable(f"{vart_id}_UCTS")
            VART_UCRTS = g.get_variable(f"{vart_id}_UCRTS")
            PAR_UCSL = g.get_parameter(f"{arg1}PAR_UCSL")
            PAR_UCSM = g.get_parameter(f"{arg1}PAR_UCSM")

            # Levels
            ms = g.model_status_GP
            VAR_UC.l[f"{sysprefix}SOLVE_STATUS", *arg3].where[ms] = ms
            PAR_UCSL[*arg2, g.ucn, "NONE", "NONE", "NONE"] = sparse(
                VAR_UC.l[g.ucn, *arg3]
            )
            PAR_UCSL[*arg2, g.ucn, g.r, "NONE", "NONE"] = sparse(
                VAR_UCR.l[g.ucn, g.r, *arg3]
            )
            PAR_UCSL[*arg2, g.ucn, "NONE", g.t, "NONE"] = sparse(
                wrap_in_sum(target=VART_UCT.l[g.ucn, g.t, *sws], domain=vart_domain)  # type: ignore[type-var]
            )
            PAR_UCSL[*arg2, g.ucn, g.r, g.t, "NONE"] = sparse(
                wrap_in_sum(
                    target=VART_UCRT.l[g.ucn, g.r, g.t, *sws], domain=vart_domain
                )  # type: ignore[type-var]
            )
            PAR_UCSL[*arg2, g.ucn, "NONE", g.t, g.s] = sparse(
                wrap_in_sum(
                    target=VART_UCTS.l[g.ucn, g.t, g.s, *sws], domain=vart_domain
                )  # type: ignore[type-var]
            )
            PAR_UCSL[*arg2, g.ucn, g.r, g.t, g.s] = sparse(
                wrap_in_sum(
                    target=VART_UCRTS.l[g.ucn, g.r, g.t, g.s, *sws],
                    domain=vart_domain,
                )  # type: ignore[type-var]
            )
            # NOTE: the raw source suffixes these %VART%-prefixed marginal references with
            # %4 (this class's own arg4), not %SWS% -- and every real GAMS caller of
            # rptmisc.rpt that reaches this class (confirmed via `grep -rn "rptmisc.rpt"
            # TIMES_source/source`: rptmain.tm, rptlite.rpt, and rpt_ext.mlf --
            # `BATINCLUDE rptmisc.rpt '%1' "%3"` / `BATINCLUDE rptmisc.rpt '' ''`) leaves
            # arg4 permanently unsupplied/blank, so `compile()` raises NotImplementedError
            # if arg4 is ever non-blank rather than silently mishandling it.
            #
            # The one real caller that DOES supply a non-blank %4 is rptmain.stc, which
            # never routes through this class -- it still calls the legacy module-level
            # rptmisc_rpt() function directly with raw text. Its actual BATINCLUDE line
            # (TIMES_source/source/rptmain.stc:95):
            #   $ BATINCLUDE rptmisc.rpt S SOW, ,SOW ,W)*SW_UNPB(T,W) ,SOW)*SW_UNPB('0',SOW
            # i.e. arg4=",W)*SW_UNPB(T,W)" -- closing %VART%'s SUM(...) paren *and*
            # multiplying in the stochastic probability weight SW_UNPB(T,W). That's a
            # structurally different closing expression than vart_domain/wrap_in_sum can
            # build (a paren-close plus an extra multiplicative term, not just a Sum
            # wrap), so if this class ever needs to support it: don't reuse wrap_in_sum for
            # the arg4 case -- multiply the whole VART_*.m[...] target by an explicit
            # SW_UNPB(...)-shaped term instead, mirroring this exact string.
            # Marginals
            #  {arg1}PAR_UCSM({arg2}UCN,R,T,ANNUAL)$UC_R_SUM(R,UCN) $= {vart}_UCT.M(UCN,T{
            #                 arg4
            #             })*R_DF(R,T);
            #   {arg1}PAR_UCSM({arg2}UCN,R,T,S)$UC_TS_EACH(R,UCN,S)  $= {vart}_UCTS.M(UCN,T,S{
            #                 arg4
            #             })*R_DF(R,T);
            #   {arg1}PAR_UCSM({arg2}UC_N,'NONE','NONE','NONE') $= {var}_UC.M(UC_N{arg5});
            #   {arg1}PAR_UCSM({arg2}UC_N,R,'NONE','NONE')      $= {var}_UCR.M(UC_N,R{arg5});
            #   {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,'NONE')      $= {vart}_UCT.M(UC_N,T{arg4});
            #   {arg1}PAR_UCSM({arg2}UC_N,R,T,'NONE')           $= {vart}_UCRT.M(UC_N,R,T{
            #                 arg4
            #             })*R_DF(R,T);
            #   {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,S)           $= {vart}_UCTS.M(UC_N,T,S{arg4});
            #   {arg1}PAR_UCSM({arg2}UC_N,R,T,S)                $= {vart}_UCRTS.M(UC_N,R,T,S{
            #                 arg4
            #             })*R_DF(R,T);
            PAR_UCSM[*arg2, g.ucn, g.r, g.t, g.Annual].where[g.UcRSum[g.r, g.ucn]] = (
                sparse(VART_UCT.m[g.ucn, g.t, *arg4] * g.r_df[g.r, g.t])
            )
            PAR_UCSM[*arg2, g.ucn, g.r, g.t, g.s].where[g.UcTsEach[g.r, g.ucn, g.s]] = (
                sparse(VART_UCTS.m[g.ucn, g.t, g.s, *arg4] * g.r_df[g.r, g.t])
            )
            PAR_UCSM[*arg2, g.ucn, "NONE", "NONE", "NONE"] = sparse(
                VAR_UC.m[g.ucn, *arg5]
            )
            PAR_UCSM[*arg2, g.ucn, g.r, "NONE", "NONE"] = sparse(
                VAR_UCR.m[g.ucn, g.r, *arg5]
            )
            PAR_UCSM[*arg2, g.ucn, "NONE", g.t, "NONE"] = sparse(
                VART_UCT.m[g.ucn, g.t, *arg4]
            )
            PAR_UCSM[*arg2, g.ucn, g.r, g.t, "NONE"] = sparse(
                VART_UCRT.m[g.ucn, g.r, g.t, *arg4] * g.r_df[g.r, g.t]
            )
            PAR_UCSM[*arg2, g.ucn, "NONE", g.t, g.s] = sparse(
                VART_UCTS.m[g.ucn, g.t, g.s, *arg4]
            )
            PAR_UCSM[*arg2, g.ucn, g.r, g.t, g.s] = sparse(
                VART_UCRTS.m[g.ucn, g.r, g.t, g.s, *arg4] * g.r_df[g.r, g.t]
            )

            # UCMAX equations
            if not if_not_defined_eq_g_ucmax:
                UcGmax = g.get_set("UC_GMAX")
                EQ_G_UCMAX = g.get_equation(f"{eq}G_UCMAX")
                PAR_UCMAX = g.get_parameter(f"{arg1}PAR_UCMAX")
                PAR_UCMAX[*arg2, g.ucn, g.allr, "-", g.c].where[
                    UcGmax[g.ucn, g.allr, "N", g.c, "N"]
                ] = (
                    VAR_UC.l[g.ucn, *arg3]
                    - EQ_G_UCMAX.l[g.ucn, g.allr, "N", g.c, "N", *arg3]
                )
                PAR_UCMAX[*arg2, g.ucn, g.allr, g.p, g.c].where[
                    UcGmax[g.ucn, g.allr, g.p, g.c, "EACH"]
                ] = (
                    VAR_UC.l[g.ucn, *arg3]
                    - EQ_G_UCMAX.l[g.ucn, g.allr, g.p, g.c, "EACH", *arg3]
                )
                PAR_UCMAX[*arg2, g.ucn, g.r, "-", g.c].where[
                    (g.UcREach[g.r, g.ucn].where[UcGmax[g.ucn, g.r, "N", g.c, "N"]])
                ] = (
                    VAR_UCR.l[g.ucn, g.r, *arg3]
                    - EQ_G_UCMAX.l[g.ucn, g.r, "N", g.c, "N", *arg3]
                )
                PAR_UCMAX[*arg2, g.ucn, g.r, g.p, g.c].where[
                    (g.UcREach[g.r, g.ucn].where[UcGmax[g.ucn, g.r, g.p, g.c, "EACH"]])
                ] = (
                    VAR_UCR.l[g.ucn, g.r, *arg3]
                    - EQ_G_UCMAX.l[g.ucn, g.r, g.p, g.c, "EACH", *arg3]
                )
        # -------------------------------------------------------------------
        # Prepare ELC supply by energy source
        if solans == "YES":
            g.rpt_opt["FLO", "5"] = 1.0
        with If(g.rpt_opt["FLO", "5"]):
            g.Trackp[g.r, g.p].where[
                Sum(g.Top[g.RpcSpg[g.r, g.p, g.c], "IN"].where[g.Nrgelc[g.r, g.c]], 1.0)
            ] = True
            g.Trackpc[g.Rpc[g.RpFlo[g.r, g.p], g.c]].where[
                (g.Top[g.Rpc, "OUT"].where[g.Nrgelc[g.r, g.c]])
            ] = True
            g.Trackpc[g.Trackp, g.c] = False
            project(source=g.Trackpc, target=g.Trackp)
            g.f_vio.setRecords(None)
            g.KeepFlof.setRecords(None)
            g.Trackpg[g.Trackp[g.r, g.p], g.c].where[
                (~(g.Nrgelc[g.r, g.c])).where[
                    g.Nrg[g.r, g.c] & g.Top[g.r, g.p, g.c, "IN"]
                ]
            ] = True
            g.f_vio[g.RtpVintyr[*rvtp], g.io].where[g.Trackp[g.r, g.p]] = (
                Sum(
                    Domain(g.Trackpc[g.r, g.p, g.c], g.s).where[(~(g.ips[g.io]))],
                    F_OUT[*arg2, *rvtp, g.c, g.s],
                )
                + Sum(
                    [g.Trackpg[g.r, g.p, g.c], g.ips[g.io], g.s],
                    F_IN[*arg2, *rvtp, g.c, g.s],
                )
                + 1.0
                - 1.0
            )
            PAR_EOUT[*arg2, g.RtpVintyr[*rvtp], g.c].where[
                (g.f_vio[*rvtp, "IN"].where[g.Trackpg[g.r, g.p, g.c]])
            ] = (
                g.f_vio[*rvtp, "OUT"]
                / g.f_vio[*rvtp, "IN"]
                * Sum(
                    g.s.where[F_IN[*arg2, *rvtp, g.c, g.s]],
                    F_IN[*arg2, *rvtp, g.c, g.s],
                )
            )
            g.Trackpc.setRecords(None)
            with Loop(g.TopIre[g.r, g.c, g.Nrgelc[g.r, g.Com], g.p]):
                g.Trackpc[g.r, g.p, g.c] = True
                g.Trackpc[g.r, g.p, g.Com] = True
            g.KeepFlof[g.Rpc[g.r, g.p, g.c]].where[(~(g.Trackpc[g.Rpc]))] = sparse(
                Sum(g.RpcIre[g.Rpc, g.ie], 1.0).where[g.Nrgelc[g.r, g.c]]
            )
            PAR_EOUT[*arg2, g.RtpVintyr[*rvtp], g.c].where[
                (g.KeepFlof[g.r, g.p, g.c].where[g.RpIre[g.r, g.p]])
            ] = (
                Sum(
                    g.s.where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                    F_OUT[*arg2, *rvtp, g.c, g.s],
                ).where[g.RpcIre[g.r, g.p, g.c, "IMP"]]
                - Sum(
                    g.s.where[F_IN[*arg2, *rvtp, g.c, g.s]],
                    F_IN[*arg2, *rvtp, g.c, g.s],
                ).where[g.RpcIre[g.r, g.p, g.c, "EXP"]]
            )
            g.KeepFlof[g.RpcSpg[g.Trackp, g.c]] = True
            g.f_vio.setRecords(None)
            g.Trackp.setRecords(None)
            g.Trackpc.setRecords(None)
            g.Trackpg.setRecords(None)
        # -------------------------------------------------------------------
        # Levelized cost calculation
        # -------------------------------------------------------------------
        g.f[...] = g.rpt_opt["NCAP", "1"]
        with Loop(Domain(g.sysuc[f"{sysprefix}LEVCOST"], g.Annual[g.sl]).where[g.f]):
            g.z[...] = g.f < 0.0
            g.f[...] = 1.0 - g.z + (g.f > 1.0)
            g.NcapYes[g.r, g.t, g.p].where[
                (
                    g.VAR_NCAP.l[g.r, g.t, g.p]
                    * g.coef_rtp[g.r, g.t, g.p].where[
                        (g.RpInout[g.r, g.p, "OUT"] + g.PrcPkaf[g.r, g.p])
                    ]
                    == 0.0
                )
            ] = False
            g.pastsum[g.r, g.t, g.p].where[PAR_CAPL[*arg2, g.r, g.t, g.p]] = (
                PAR_CAPL[*arg2, g.r, g.t, g.p]
                + Sum(g.pastcv, PAR_PASTI[*arg2, g.r, g.t, g.p, g.pastcv])
                + 1.0
                - 1.0
            )
            # Calculate ENV credit
            with Loop(g.ComLim[g.Env[g.r, g.c], "LO"].where[g.z]):
                g.Trackc[g.r, g.c] = True
                g.Trackp[g.r, g.p].where[
                    (g.PrcMap[g.r, "PRE", g.p].where[g.Top[g.r, g.p, g.c, "OUT"]])
                ] = True
            g.Trackpc[g.Trackp[g.r, g.p], g.c].where[
                (g.Nrg[g.r, g.c].where[g.Top[g.r, g.p, g.c, "OUT"]])
            ] = True
            g.Trackc[g.r, g.c].where[Sum(g.Trackpc[g.r, g.p, g.c], 1.0)] = True
            g.vda_emcb[g.r, g.t, g.c, g.c].where[
                (g.Nrg[g.r, g.c].where[g.Trackc[g.r, g.c]])
            ] = Min(
                Sum(
                    g.Trackc[g.Env[g.r, g.Com]],
                    Min(
                        0.0,
                        g.com_agg[g.r, g.t, g.c, g.Com]
                        * PAR_COMBALEM[*arg2, g.r, g.t, g.Com, g.sl],
                    ),
                ),
                Sum(
                    g.p.where[g.Trackpc[g.r, g.p, g.c]],
                    Sum(
                        Domain(g.Vnt[g.v, g.t], g.s).where[
                            F_OUT[*arg2, *rvtp, g.c, g.s]
                        ],
                        F_OUT[*arg2, *rvtp, g.c, g.s],
                    )
                    / Max(
                        g.micro,
                        Sum(
                            Domain(
                                g.Trackpc[g.r, g.p, g.com2], g.Vnt[g.v, g.t], g.s
                            ).where[F_OUT[*arg2, *rvtp, g.com2, g.s]],
                            F_OUT[*arg2, *rvtp, g.com2, g.s],
                        ),
                    )
                    * Sum(
                        Domain(g.Vnt[g.v, g.t], g.Trackc[g.Env[g.r, g.Com]]).where[
                            F_OUT[*arg2, *rvtp, g.Com, g.sl]
                        ],
                        F_OUT[*arg2, *rvtp, g.Com, g.sl]
                        * Min(0.0, PAR_COMBALEM[*arg2, g.r, g.t, g.Com, g.sl]),
                    ),
                )
                / Max(
                    g.micro,
                    Sum(
                        Domain(g.Vnt[g.v, g.t], g.p, g.s).where[
                            F_OUT[*arg2, *rvtp, g.c, g.s]
                        ],
                        F_OUT[*arg2, *rvtp, g.c, g.s],
                    )
                    + Sum(
                        g.s.where[AGG_OUT[*arg2, *rtcs]],
                        AGG_OUT[*arg2, *rtcs],
                    ),
                ),
            )
            g.Trackp.setRecords(None)
            g.Trackpc.setRecords(None)
            g.coef_cap.setRecords(None)
            g.Trackc[g.Nrg] = False
            # Credit for aux energy ouputs (ELE+CHP+HPL)
            project(source=g.NcapYes, target=g.RpPrc)
            g.Trackp[g.RpPrc[g.Rp]] = g.Ele[g.Rp] + g.Chp[g.Rp] + g.Hpl[g.Rp]
            g.Trackpc[g.Trackp[g.r, g.p], g.c].where[
                g.Top[g.r, g.p, g.c, "OUT"].where[
                    (
                        ~(
                            g.RpcPg[g.r, g.p, g.c]
                            * (g.Nrgelc[g.r, g.c] + (~(g.Chp[g.r, g.p])))
                        )
                    )
                    & g.Nrg[g.r, g.c]
                ]
            ] = True
            project(source=g.Trackpc, target=g.Trackp)
            with If(g.z):
                g.coef_cap[g.RtpVintyr[*rvtp]].where[g.Trackp[g.r, g.p]] = 1.0 - 1.0 / (
                    1.0
                    + Sum(
                        g.RpcsVar[g.Trackpc[g.r, g.p, g.c], g.s],
                        g.par_flo[*rvtp, g.c, g.s],
                    )
                    / Max(
                        g.micro,
                        Sum(
                            g.RpcsVar[g.RpcPg[g.r, g.p, g.c], g.s].where[
                                (~(g.Trackpc[g.r, g.p, g.c]))
                            ],
                            g.par_flo[*rvtp, g.c, g.s],
                        ),
                    )
                )
            with If(g.f == 1.0):
                g.RpGrp[g.RpcPg[g.RpPrc, g.c]].where[(~(g.Trackpc[g.RpcPg]))] = True
            # Credit for peak capacity
            with Loop(Domain(g.ComPeak[g.r, g.cg], g.ComGmap[g.r, g.cg, g.c])):
                g.Trackpg[g.RpPrc[g.r, g.p], g.c].where[g.Top[g.r, g.p, g.c, "OUT"]] = (
                    True
                )
                g.par_rtcs[g.RtcsVarc[*rtcs]] = (
                    Sum(
                        g.ComPkts[g.r, g.cg, g.ts].where[g.RsTree[g.r, g.s, g.ts]],
                        PAR_PEAKM[*arg2, g.r, g.t, g.cg, g.ts]
                        / (
                            1.0
                            + Max(
                                g.com_pkrsv[g.r, g.t, g.c],
                                Sum(g.Com[g.cg], g.com_pkrsv[g.r, g.t, g.Com]),
                            )
                        )
                        * g.rs_fr[g.r, g.ts, g.s],
                    )
                    * g.com_ie[*rtcs]
                )
            project(source=g.RpcPkc, target=g.RpPrc)
            g.RpPrc[g.Rp].where[(g.f < 2.0)] = False
            g.Trackpg[g.RpcPg[g.RpPrc, g.c]] = False
            # Cost ratio for vintaged
            PAR_NCAPR[*arg2, g.NcapYes[g.r, g.tt[g.v], g.p], g.sysuc].where[
                g.PrcVint[g.r, g.p]
            ] = (
                g.coef_rtp[g.r, g.v, g.p] * g.VAR_NCAP.l[g.r, g.v, g.p]
                + Sum(
                    g.RtpVintyr[*rvtp],
                    g.coef_pvt[g.r, g.t]
                    * (
                        Sum(g.rpm, CST_ACTC[*arg2, *rvtp, g.rpm])
                        + Sum(
                            g.Top[g.r, g.p, g.c, "IN"],
                            (1.0 - g.coef_cap[*rvtp])
                            * (
                                CST_FLOC[*arg2, *rvtp, g.c]
                                + CST_FLOX[*arg2, *rvtp, g.c]
                                + Sum(
                                    Domain(
                                        g.ComTs[g.r, g.c, g.s], g.RsTree[g.r, g.s, g.ts]
                                    ).where[F_IN[*arg2, *rvtp, g.c, g.ts]],
                                    (
                                        PAR_COMBALEM[*arg2, *rtcs]
                                        + g.vda_emcb[g.r, g.t, g.c, g.c]
                                    )
                                    * F_IN[*arg2, *rvtp, g.c, g.ts]
                                    * g.rs_fr[g.r, g.s, g.ts],
                                ).where[(~(g.Trackc[g.r, g.c]))]
                            ),
                        )
                        + Sum(
                            g.Top[g.r, g.p, g.c, "OUT"].where[
                                (~(g.Trackpc[g.r, g.p, g.c].where[g.z]))
                            ],
                            CST_FLOC[*arg2, *rvtp, g.c]
                            + CST_FLOX[*arg2, *rvtp, g.c]
                            - Sum(
                                Domain(
                                    g.ComTs[g.r, g.c, g.s], g.RsTree[g.r, g.s, g.ts]
                                ).where[F_OUT[*arg2, *rvtp, g.c, g.ts]],
                                (
                                    PAR_COMBALEM[*arg2, *rtcs] * g.com_ie[*rtcs]
                                    + (
                                        g.ncap_pkcnt[g.r, g.v, g.p, g.s]
                                        ** g.rpc_pkf[g.r, g.p, g.c]
                                    )
                                    * g.par_rtcs[*rtcs].where[g.Trackpg[g.r, g.p, g.c]]
                                )
                                * F_OUT[*arg2, *rvtp, g.c, g.ts]
                                * g.rs_fr[g.r, g.s, g.ts],
                            ).where[(~(g.RpGrp[g.r, g.p, g.c])) & g.f],
                        )
                        - Sum(
                            [g.RpcPg[g.RpPrc[g.r, g.p], g.c], g.ComTs[g.r, g.c, g.s]],
                            g.ncap_pkcnt[g.r, g.v, g.p, g.s]
                            * g.par_rtcs[*rtcs]
                            * g.VAR_NCAP.l[g.r, g.v, g.p]
                            * g.g_yrfr[g.r, g.s]
                            * g.prc_capact[g.r, g.p]
                            * g.prc_actflo[g.r, g.v, g.p, g.c],
                        )
                    ),
                )
            ) / Max(
                g.micro,
                Sum(
                    g.RtpCptyr[*rvtp],
                    g.coef_pvt[g.r, g.t]
                    * Sum(
                        g.RpcsVar[g.RpcPg[g.r, g.p, g.c], g.s].where[
                            (~(g.Trackpc[g.r, g.p, g.c]))
                        ],
                        g.par_flo[*rvtp, g.c, g.s],
                    ),
                ),
            )
            # Cost ratio for non-vintaged
            PAR_NCAPR[*arg2, g.NcapYes[g.r, g.tt[g.v], g.p], g.sysuc].where[
                (~(g.PrcVint[g.r, g.p]))
            ] = (
                g.coef_rtp[g.r, g.v, g.p]
                + Sum(
                    g.RtpCptyr[*rvtp].where[g.pastsum[g.r, g.t, g.p]],
                    g.coef_pvt[g.r, g.t]
                    * g.coef_cpt[*rvtp]
                    / g.pastsum[g.r, g.t, g.p]
                    * (
                        Sum(g.rpm, CST_ACTC[*arg2, g.r, g.t, g.t, g.p, g.rpm])
                        + Sum(
                            g.Top[g.r, g.p, g.c, "IN"],
                            (1.0 - g.coef_cap[g.r, g.t, g.t, g.p])
                            * (
                                CST_FLOC[*arg2, g.r, g.t, g.t, g.p, g.c]
                                + CST_FLOX[*arg2, g.r, g.t, g.t, g.p, g.c]
                                + Sum(
                                    Domain(
                                        g.ComTs[g.r, g.c, g.s], g.RsTree[g.r, g.s, g.ts]
                                    ).where[F_IN[*arg2, g.r, g.t, g.t, g.p, g.c, g.ts]],
                                    (
                                        PAR_COMBALEM[*arg2, *rtcs]
                                        + g.vda_emcb[g.r, g.t, g.c, g.c]
                                    )
                                    * F_IN[*arg2, g.r, g.t, g.t, g.p, g.c, g.ts]
                                    * g.rs_fr[g.r, g.s, g.ts],
                                ).where[(~(g.Trackc[g.r, g.c]))]
                            ),
                        )
                        + Sum(
                            g.Top[g.r, g.p, g.c, "OUT"].where[
                                (~(g.Trackpc[g.r, g.p, g.c].where[g.z]))
                            ],
                            CST_FLOC[*arg2, g.r, g.t, g.t, g.p, g.c]
                            + CST_FLOX[*arg2, g.r, g.t, g.t, g.p, g.c]
                            - Sum(
                                Domain(
                                    g.ComTs[g.r, g.c, g.s], g.RsTree[g.r, g.s, g.ts]
                                ).where[F_OUT[*arg2, g.r, g.t, g.t, g.p, g.c, g.ts]],
                                (
                                    PAR_COMBALEM[*arg2, *rtcs] * g.com_ie[*rtcs]
                                    + (
                                        g.ncap_pkcnt[g.r, g.v, g.p, g.s]
                                        ** g.rpc_pkf[g.r, g.p, g.c]
                                    )
                                    * g.par_rtcs[*rtcs].where[g.Trackpg[g.r, g.p, g.c]]
                                )
                                * F_OUT[*arg2, g.r, g.t, g.t, g.p, g.c, g.ts]
                                * g.rs_fr[g.r, g.s, g.ts],
                            ).where[(~(g.RpGrp[g.r, g.p, g.c])) & g.f],
                        )
                        - Sum(
                            [g.RpcPg[g.RpPrc[g.r, g.p], g.c], g.ComTs[g.r, g.c, g.s]],
                            g.ncap_pkcnt[g.r, g.v, g.p, g.s]
                            * g.par_rtcs[*rtcs]
                            * g.pastsum[g.r, g.t, g.p]
                            * g.g_yrfr[g.r, g.s]
                            * g.prc_capact[g.r, g.p]
                            * g.prc_actflo[g.r, g.v, g.p, g.c],
                        )
                    ),
                )
            ) / Max(
                g.micro,
                Sum(
                    g.RtpCptyr[*rvtp].where[g.pastsum[g.r, g.t, g.p]],
                    g.coef_pvt[g.r, g.t]
                    * g.coef_cpt[*rvtp]
                    / g.pastsum[g.r, g.t, g.p]
                    * Sum(
                        g.RpcsVar[g.RpcPg[g.r, g.p, g.c], g.s].where[
                            (~(g.Trackpc[g.r, g.p, g.c]))
                        ],
                        g.par_flo[g.r, g.t, g.t, g.p, g.c, g.s],
                    ),
                ),
            )
            g.Trackp.setRecords(None)
            g.Trackc.setRecords(None)
            g.Trackpc.setRecords(None)
            g.Trackpg.setRecords(None)
            g.vda_emcb.setRecords(None)
            g.pastsum.setRecords(None)
            g.par_rtcs.setRecords(None)
            g.coef_cap.setRecords(None)

        # Fallback of flows to ANNUAL level
        with Loop(g.Annual[g.ts].where[Card(g.uncd1)]):
            with Loop(g.uncd1[g.ComType[g.cg]]):
                g.Trackc[g.r, g.c].where[g.ComTmap[g.r, g.ComType, g.c]] = (
                    g.rpt_opt[g.cg, "3"] < 0.0
                )
            with Loop(g.uncd1[g.nrgtype[g.u2]].where[g.rpt_opt[g.u2, "3"]]):
                g.Trackc[g.r, g.c].where[g.NrgTmap[g.r, g.nrgtype, g.c]] = (
                    g.rpt_opt[g.u2, "3"] < 0.0
                )
            g.Rvtpc[*rvtp, g.c].where[g.Trackc[g.r, g.c]] = sparse(
                Sum(
                    g.s.where[F_IN[*arg2, *rvtp, g.c, g.s]],
                    g.stoa[g.s],
                )
            )
            g.f_ios[g.Rvtpc, g.ts] = Sum(
                g.s.where[F_IN[*arg2, g.Rvtpc, g.s]],
                F_IN[*arg2, g.Rvtpc, g.s],
            )
            F_IN[*arg2, g.Rvtpc, g.s] = 0.0
            F_IN[*arg2, g.Rvtpc, g.s] = sparse(g.f_ios[g.Rvtpc, g.s])
            g.Rvtpc.setRecords(None)
            g.f_ios.setRecords(None)
            g.Rvtpc[*rvtp, g.c].where[g.Trackc[g.r, g.c]] = sparse(
                Sum(
                    g.s.where[F_OUT[*arg2, *rvtp, g.c, g.s]],
                    g.stoa[g.s],
                )
            )
            g.f_ios[g.Rvtpc, g.ts] = Sum(
                g.s.where[F_OUT[*arg2, g.Rvtpc, g.s]],
                F_OUT[*arg2, g.Rvtpc, g.s],
            )
            F_OUT[*arg2, g.Rvtpc, g.s] = 0.0
            F_OUT[*arg2, g.Rvtpc, g.s] = sparse(g.f_ios[g.Rvtpc, g.s])
            g.Trackc.setRecords(None)
            g.Rvtpc.setRecords(None)
            g.f_ios.setRecords(None)


# NOTE: The module-level raw-GAMS-string generator below is kept -- not a
# leftover -- because it is still imported and called directly by two other
# not-yet-translated modules. This function
# should be deleted once rptlite_rpt.py and rptmain_stc.py are themselves
# translated to call the native class.
def rptmisc_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    var: str,
    cufscal: str,
    sysprefix: str,
    model_name: str,
    vart: str,
    sws: str,
    eq: str,
    if_defined_vnret: bool,
    rpt_flots: str,
    stages: str,
    if_defined_eqe_ucrtp: bool,
    var_uc: str,
    if_not_defined_eq_g_ucmax: bool,
    solans: str,
) -> str:
    g_ucmax_code = ""
    if not if_not_defined_eq_g_ucmax:
        g_ucmax_code = f"""
      {arg1}PAR_UCMAX({arg2}UC_N,ALL_R,'-',C)$UC_GMAX(UC_N,ALL_R,'N',C,'N') = {var}_UC.L(UC_N{arg3})-{eq}G_UCMAX.L(UC_N,ALL_R,'N',C,'N'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,ALL_R,P,C)$UC_GMAX(UC_N,ALL_R,P,C,'EACH')  = {var}_UC.L(UC_N{arg3})-{eq}G_UCMAX.L(UC_N,ALL_R,P,C,'EACH'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,R,'-',C)$(UC_R_EACH(R,UC_N)$UC_GMAX(UC_N,R,'N',C,'N')) = {var}_UCR.L(UC_N,R{arg3})-{eq}G_UCMAX.L(UC_N,R,'N',C,'N'{arg3});
      {arg1}PAR_UCMAX({arg2}UC_N,R,P,C)$(UC_R_EACH(R,UC_N)$UC_GMAX(UC_N,R,P,C,'EACH'))  = {var}_UCR.L(UC_N,R{arg3})-{eq}G_UCMAX.L(UC_N,R,P,C,'EACH'{arg3});
    """
    return rf"""
  R_DF(R,T) = SIGN(COEF_PVT(R,T))/MAX(1E-9,ABS(COEF_PVT(R,T)));
*-----------------------------------------------------------------------------
* Activity levels & marginals
*-----------------------------------------------------------------------------
  {arg1}PAR_ACTL({arg2}RTP_VINTYR(R,V,T,P),S)$PRC_TS(R,P,S) $= VAR_ACT.L(R,V,T,P,S);
* Shift up STS activity levels
  LOOP((RP_STL(R,P,TSL,BD),TS_GROUP(R,TSL,TS))$RLUP(R,'DAYNITE',TSL),Z=G_YRFR(R,TS)*365/TS_CYCLE(R,TS);
    YKVAL(VNT(V,T))=SMIN(RS_BELOW(R,TS,S),VAR_ACT.L(R,VNT,P,S)/Z)$NCAP_YES(R,V,P);
    {arg1}PAR_ACTL({
        arg2
    }R,VNT,P,S)$(TS_MAP(R,TS,S)$YKVAL(VNT))=VAR_ACT.L(R,VNT,P,S)+YKVAL(VNT)*(1-(1+Z)$RS_BELOW(R,TS,S)));
  Z = (RPT_OPT('ACT','2') GE 0);
  {arg1}PAR_ACTM({
        arg2
    }R,V,T,P,S)$VAR_ACT.M(R,V,T,P,S) = ROUND(VAR_ACT.M(R,V,T,P,S)*R_DF(R,T),7)$Z;
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQL_ACTBND.M(R,T,P,S)*R_DF(R,T);
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQG_ACTBND.M(R,T,P,S)*R_DF(R,T);
  {arg1}PAR_ACTM({arg2}R,'0',T,P,S) $= EQE_ACTBND.M(R,T,P,S)*R_DF(R,T);

*-----------------------------------------------------------------------------
* Capacity
*-----------------------------------------------------------------------------
  OPTION CLEAR=RTP_CAPYR,CLEAR=COEF_CAP;
  RTP_CAPYR(RTP_CPTYR(R,TT,T,P))$VAR_NCAP.L(R,TT,P) = YES;
  VAR_CAP.M(RTP)$(NOT VAR_CAP.M(RTP)) $= EQE_CPT.M(RTP);

  {arg1}PAR_CAPL({
        arg2
    }RTP(R,T,P))  = SUM(RTP_CAPYR(R,TT,T,P), COEF_CPT(R,TT,T,P)*VAR_NCAP.L(R,TT,P));
  {arg1}PAR_PASTI({
        arg2
    }RTP(R,T,P),'0') = SUM(PYR(K)$COEF_CPT(R,K,T,P),COEF_CPT(R,K,T,P)*NCAP_PASTI(R,K,P)-RTFORC(R,K,T,P)$PYR_S(K));

{
        f"COEF_CAP(R,V,T,P)$=VAR_SCAP.L(R,V,T,P); {arg1}PAR_PASTI({arg2}RTP(R,T,P),'€')$PRC_RCAP(R,P) = -SUM(VNRET(V,T),COEF_CAP(R,V,T,P)*COEF_CPT(R,V,T,P)-RTFORC(R,V,T,P));"
        if if_defined_vnret
        else ""
    }
  IF(RPT_OPT('CAP','5')>0,{arg1}PAR_CUMRET({arg2}RTP_CPTYR) $= COEF_CAP(RTP_CPTYR));
  {arg1}PAR_CAPM({arg2}RTP(R,T,P))   $= VAR_CAP.M(RTP)*R_DF(R,T);
  {arg1}PAR_CAPBD({arg2}RTP,'LO')    $= CAP_BND(RTP,'LO');
  {arg1}PAR_CAPBD({arg2}RTP_OFF(RTP),'UP')$RCAP_BND(RTP,'N') $= PRC_RESID(RTP);
  {arg1}PAR_CAPBD({arg2}RTP,'UP')$(CAP_BND(RTP,'UP') NE INF) $= CAP_BND(RTP,'UP');

  {arg1}PAR_NCAPL({arg2}RTP(R,V,P))  $= VAR_NCAP.L(RTP);
  {arg1}PAR_NCAPM({
        arg2
    }RTP)$(VAR_NCAP.M(RTP)*COEF_OBJINV(RTP)) = VAR_NCAP.M(RTP)/COEF_OBJINV(RTP);

*-----------------------------------------------------------------------------
* Commodities
*-----------------------------------------------------------------------------
* Variables
  {arg1}PAR_COMPRDL({arg2}R,T,C,S) $= VAR_COMPRD.L(R,T,C,S);
  {arg1}PAR_COMPRDM({arg2}R,T,C,S) $= VAR_COMPRD.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_COMNETL({arg2}R,T,C,S) $= VAR_COMNET.L(R,T,C,S);
  {arg1}PAR_COMNETM({arg2}R,T,C,S) $= VAR_COMNET.M(R,T,C,S)*R_DF(R,T);
  OPTION AGR < COM_AGG;
  {arg1}AGG_OUT({arg2}R,T,C,S)$(RTCS_VARC(R,T,C,S)$AGR(R,C)) =
    SUM(RTC(R,T,COM)$COM_AGG(RTC,C),COM_AGG(RTC,C) *
       SUM(RTCS_VARC(RTC,TS)$RS_FR(R,S,TS),RS_FR(R,S,TS)*(1+{
        macro.rtcs_fr.rtcs_fr("R", "T", "COM", "S", "TS")
    }) *
         (VAR_COMNET.L(RTC,TS)$RC_AGP(R,COM,'LO') + VAR_COMPRD.L(RTC,TS)$RC_AGP(R,COM,'FX'))));
  OPTION CLEAR=AGR;

* Equations
  {arg1}PAR_COMBALEM({arg2}R,T,C,S) $= EQG_COMBAL.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_COMBALEM({arg2}R,T,C,S) $= EQE_COMBAL.M(R,T,C,S)*R_DF(R,T);
  {arg1}PAR_PEAKM({arg2}R,T,CG,S)   $= EQ_PEAK.M(R,T,CG,S)*R_DF(R,T);
{f"{arg1}PAR_COMBALGM({arg2}RTC,S) $= EQG_COMBAL.L(RTC,S);" if arg1 == "S" else ""}

*-----------------------------------------------------------------------------
* Process flows
*-----------------------------------------------------------------------------
  OPTION CLEAR=UNCD1,CLEAR=RTP_CAPYR,CLEAR=F_INOUT;
  F_INOUT(R,V,T,P,C,'IN')$COEF_ICOM(R,V,T,P,C) = COEF_ICOM(R,V,T,P,C) * RTP_CAPVL(R,V,P);
  F_INOUT(R,V,T,P,C,'OUT')$COEF_OCOM(R,V,T,P,C) = COEF_OCOM(R,V,T,P,C) * RTP_CAPVL(R,V,P);
  F_INOUT(RTP_CPTYR(R,V,T,P),C,IO)$NCAP_COM(R,V,P,C,IO) = F_INOUT(R,V,T,P,C,IO) +
    (RTP_CAPVL(R,V,P)-COEF_CAP(R,V,T,P)) * COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,IO) * (1+COEF_CIO(R,V,T,P,C,IO));
  F_INOUTS(R,V,T,P,C,ANNUAL(S),IO)$F_INOUT(R,V,T,P,C,IO) = F_INOUTS(R,V,T,P,C,S,IO)+F_INOUT(R,V,T,P,C,IO);

* inputs: main flows & emissions, aux flows & emissions
  {arg1}F_IN({arg2}R,V,T,P,C,S)$TOP(R,P,C,'IN')   $= PAR_FLO(R,V,T,P,C,S);
  {arg1}F_IN({arg2}R,V,T,P,C,S)                   $= PAR_IRE(R,V,T,P,C,S,'EXP');
  {arg1}F_IN({arg2}R,V,T,P,C,S)$RPCS_VAR(R,P,C,S) $= VAR_SIN.L(R,V,T,P,C,S);
  {arg1}F_IN({arg2}R,V,T,P,C,S)$F_INOUTS(R,V,T,P,C,S,'IN') = {arg1}F_IN({
        arg2
    }R,V,T,P,C,S)+F_INOUTS(R,V,T,P,C,S,'IN');
* outputs: main flows & emissions, aux flows & emissions
  PAR_FLO(R,V,T,P,C,S)$RPCS_VAR(R,P,C,S)  $= VAR_SOUT.L(R,V,T,P,C,S)*STG_EFF(R,V,P);
  {arg1}F_OUT({arg2}R,V,T,P,C,S)$TOP(R,P,C,'OUT') $= PAR_FLO(R,V,T,P,C,S);
  {arg1}F_OUT({arg2}R,V,T,P,C,S)                  $= PAR_IRE(R,V,T,P,C,S,'IMP');
  {arg1}F_OUT({arg2}R,V,T,P,C,S)$F_INOUTS(R,V,T,P,C,S,'OUT') = {arg1}F_OUT({
        arg2
    }R,V,T,P,C,S)+F_INOUTS(R,V,T,P,C,S,'OUT');
*-----------------------------------------------------------------------------
* Filter out small values if requested
  IF(SUM(UC_GRPTYPE$RPT_OPT(UC_GRPTYPE,'9'),1),RPT_OPT(UC_GRPTYPE,'9')$(RPT_OPT(UC_GRPTYPE,'9')>.1)=0;
    Z=RPT_OPT('ACT','9'); IF(Z>0,{arg1}PAR_ACTL({arg2}R,V,T,P,S)$(({arg1}PAR_ACTL({
        arg2
    }R,V,T,P,S)<Z)${arg1}PAR_ACTL({arg2}R,V,T,P,S))=0);
    Z=RPT_OPT('CAP','9');
    IF(Z>0,{arg1}PAR_CAPL({arg2}RTP)$(({arg1}PAR_CAPL({arg2}RTP)<Z)${arg1}PAR_CAPL({
        arg2
    }RTP))=0;
           {arg1}PAR_PASTI({arg2}RTP(R,T,P),'€')$((ABS({arg1}PAR_PASTI({
        arg2
    }RTP,'€'))<Z)${arg1}PAR_PASTI({arg2}RTP,'€'))=0);
    Z=RPT_OPT('NCAP','9');IF(Z>0,{arg1}PAR_NCAPL({arg2}RTP)$(({arg1}PAR_NCAPL({
        arg2
    }RTP)<Z)${arg1}PAR_NCAPL({arg2}RTP))=0);
    Z=RPT_OPT('FLO','9');
    IF(Z>0,{arg1}F_OUT({arg2}R,V,T,P,C,S)$((ABS({arg1}F_OUT({arg2}R,V,T,P,C,S))<Z)${
        arg1
    }F_OUT({arg2}R,V,T,P,C,S)) = 0;
           {arg1}F_IN({arg2}R,V,T,P,C,S)$((ABS({arg1}F_IN({arg2}R,V,T,P,C,S))<Z)${
        arg1
    }F_IN({arg2}R,V,T,P,C,S)) = 0));
*-----------------------------------------------------------------------------
* If power levels or fall-back to ANNUAL is requested, set reporting at com_TS
  UNCD1(U2(COM_TYPE))$RPT_OPT(U2,'3')=YES;
  UNCD1(U2(NRG_TYPE))$RPT_OPT(U2,'1')=YES;
  UNCD1(U2(NRG_TYPE))$RPT_OPT(U2,'3')=YES;
  RPT_OPT('FLO','1')$CARD(UNCD1)=YES;
  MY_TS(S) = ORD(S) EQ CARD(S);
  OPTION CLEAR=RTP_CAPVL,CLEAR=RVTPC,CLEAR=F_INOUTS,CLEAR=RCS;
* Check for unused COM variables
  RTTC(RTC)$(NOT SUM(RHS_COMPRD(RTC,S),1)) = YES;
  OPTION CLEAR=RXX; RXX(RTC)$(NOT SUM(RCS_COMBAL(RTC,S,BD),1))=YES;
  Z = (RPT_OPT('COMPRD','1') LE 0); IF(Z,RTTC(RTC)$(NOT RXX(RTC))=NO);
  IF(RPT_OPT('FLO','1')<1,
{"RCS(RC,ANNUAL)=YES;" if rpt_flots.upper() == "ANNUAL" else ""}
  ELSE RCS(COM_TS)=YES);
  IF(CARD(RCS),
* Represent all process flows at requested timeslices
    F_IOS(R,V,T,P,C,S)$(NOT RCS(R,C,S)) $= {arg1}F_IN({
        arg2
    }R,V,T,P,C,S); OPTION RVTPC<F_IOS;
    {arg1}F_IN({arg2}RVTPC,S)$F_IOS(RVTPC,S)=0;
    {arg1}F_IN({arg2}RVTPC(R,V,T,P,C),TS)$RCS(R,C,TS) = {arg1}F_IN({arg2}RVTPC,TS) +
      SUM(RS_TREE(R,TS,S)$F_IOS(RVTPC,S),RS_FR(R,TS,S)*(1+{
        macro.rtcs_fr.rtcs_fr("R", "T", "C", "TS", "S")
    })*F_IOS(RVTPC,S));
    OPTION CLEAR=RVTPC,CLEAR=F_IOS;
    F_IOS(R,V,T,P,C,S)$(NOT RCS(R,C,S)) $= {arg1}F_OUT({
        arg2
    }R,V,T,P,C,S); OPTION RVTPC<F_IOS;
    {arg1}F_OUT({arg2}RVTPC,S)$F_IOS(RVTPC,S)=0;
    {arg1}F_OUT({arg2}RVTPC(R,V,T,P,C),TS)$RCS(R,C,TS) = {arg1}F_OUT({arg2}RVTPC,TS) +
      SUM(RS_TREE(R,TS,S)$F_IOS(RVTPC,S),RS_FR(R,TS,S)*(1+{
        macro.rtcs_fr.rtcs_fr("R", "T", "C", "TS", "S")
    })*F_IOS(RVTPC,S));
    OPTION CLEAR=RCS,CLEAR=RVTPC,CLEAR=F_IOS;
    {arg1}PAR_COMPRDL({arg2}RTCS_VARC(RTTC(R,T,C),S)) = SUM((VNT(V,T),P)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S));
*...optional power levels
    LOOP(NRG_TYPE(U2)$RPT_OPT(U2,'1'), F=(ROUND(RPT_OPT(U2,'3'))=2);
     {arg1}P_OUT({
        arg2
    }RTPC(R,T,P,C),S)$(COM_TS(R,C,S)$NRG_TMAP(R,NRG_TYPE,C))=SUM(VNT(V,T)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S)/G_YRFR(R,S)/RPT_OPT(U2,'1'))
        - SUM(VNT(V,T)${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S)/G_YRFR(R,S)/RPT_OPT(U2,'1'))$F);
  ELSE {arg1}PAR_COMPRDL({arg2}RTTC(R,T,C),ANNUAL)=SUM((VNT(V,T),P,S)${arg1}F_OUT({
        arg2
    }R,V,T,P,C,S),{arg1}F_OUT({arg2}R,V,T,P,C,S));
 );
{"RPT_OPT('FLO','3')=0;" if stages.upper() == "YES" else ""}
 IF(RPT_OPT('FLO','3'),
   VAL_FLO(R,V,T,P,C) $= SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S)*{arg1}PAR_COMBALEM({arg2}R,T,C,S));
   F_INOUTS(R,V,T,P,C,ANNUAL,'OUT') $= SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),{
        arg1
    }F_OUT({arg2}R,V,T,P,C,S)*{arg1}PAR_COMBALEM({arg2}R,T,C,S));
   VAL_FLO(R,V,T,P,C)$F_INOUTS(R,V,T,P,C,'ANNUAL','OUT') = VAL_FLO(R,V,T,P,C)-F_INOUTS(R,V,T,P,C,'ANNUAL','OUT');
   OPTION CLEAR=F_INOUTS;
 );
* Complete COMPRDL & COMNETL reporting
  {arg1}PAR_COMPRDL({arg2}RTTC(R,T,C),S)${arg1}AGG_OUT({arg2}RTTC,S) = {
        arg1
    }PAR_COMPRDL({arg2}RTTC,S)+{arg1}AGG_OUT({arg2}RTTC,S);
  {arg1}PAR_COMNETL({arg2}RTC(RXX(R,T,C)),S) $= {arg1}PAR_COMPRDL({arg2}RTC,S);
  {arg1}PAR_COMNETL({arg2}RTCS_VARC(RXX(R,T,C),ANNUAL(S))) = {arg1}PAR_COMPRDL({
        arg2
    }R,T,C,S)*PROD(RTTC(R,T,C),COM_IE(RTTC,S))-SUM(RPC_CAPFLO(R,V,P,C)$VNT(V,T),F_INOUT(R,V,T,P,C,'IN'));
  {arg1}PAR_COMPRDL({arg2}RXX(RTTC(R,T,C)),S)=0;
  {var}_COMNET.L(RTC(RXX(R,T,C)),S{arg3}) $= {arg1}PAR_COMNETL({arg2}RTC,S);
*-----------------------------------------------------------------------------
* Cumflo results (unscaling)
  {arg1}PAR_CUMFLOL({arg2}R,P,C,YEAR,LL) $= {var}_CUMFLO.L(R,P,C,YEAR,LL{arg3})*{
        cufscal
    };
  {arg1}PAR_CUMFLOM({arg2}R,P,C,YEAR,LL) $= {var}_CUMFLO.M(R,P,C,YEAR,LL{arg5})*(1/{
        cufscal
    });
  {arg1}PAR_CUMCST({arg2}R,YEAR,LL,COSTAGG,CUR) $= {var}_CUMCST.L(R,YEAR,LL,COSTAGG,CUR{
        arg3
    });
* Marginals of Dynamic process bounds
{
        "EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD('FX')) $= EQE_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD);"
        if if_defined_eqe_ucrtp
        else ""
    }
  {arg1}PAR_UCRTP({
        arg2
    }UC_N,R,T,P,UC_GRPTYPE) $= SUM(BD$PRC_DYNUC(UC_N,'RHS',R,T,P,UC_GRPTYPE,BD),EQN_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD)*(1/COEF_OBJINV(R,T,P))$COEF_OBJINV(R,T,P));
  {arg1}PAR_UCRTP({
        arg2
    }UC_N,R,T,P,'ACT') $= SUM(BD$PRC_DYNUC(UC_N,'RHS',R,T,P,'ACT',BD),EQN_UCRTP.M(UC_N,R,T,P,'ACT',BD)*R_DF(R,T));
  IF(RPT_OPT('COMPRD','4'), {arg1}PAR_UCMRK({
        arg2
    }R,T,ITEM,C,S) $= EQL_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S) $= EQG_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S) $= EQE_FLOMRK.M(R,T,ITEM,C,S);
    {arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S)${arg1}PAR_UCMRK({arg2}R,T,ITEM,C,S)=({
        arg1
    }PAR_UCMRK({arg2}R,T,ITEM,C,S)/COEF_PVT(R,T))$(NOT SUM(RX_MARK(R,LL,ITEM,C,BD),1)));
*-----------------------------------------------------------------------------
* User constraints
*-----------------------------------------------------------------------------
{
        ""
        if var_uc != "YES"
        else (
            f'''
* Levels
  {var}_UC.L('{sysprefix}SOLVE_STATUS'{arg3}) $= {model_name}.MODELSTAT;
  {arg1}PAR_UCSL({arg2}UC_N,'NONE','NONE','NONE') $= {var}_UC.L(UC_N{arg3});
  {arg1}PAR_UCSL({arg2}UC_N,R,'NONE','NONE')      $= {var}_UCR.L(UC_N,R{arg3});
  {arg1}PAR_UCSL({arg2}UC_N,'NONE',T,'NONE')      $= {vart}_UCT.L(UC_N,T{sws});
  {arg1}PAR_UCSL({arg2}UC_N,R,T,'NONE')           $= {vart}_UCRT.L(UC_N,R,T{sws});
  {arg1}PAR_UCSL({arg2}UC_N,'NONE',T,S)           $= {vart}_UCTS.L(UC_N,T,S{sws});
  {arg1}PAR_UCSL({arg2}UC_N,R,T,S)                $= {vart}_UCRTS.L(UC_N,R,T,S{sws});
* Marginals
  {arg1}PAR_UCSM({arg2}UCN,R,T,ANNUAL)$UC_R_SUM(R,UCN) $= {vart}_UCT.M(UCN,T{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UCN,R,T,S)$UC_TS_EACH(R,UCN,S)  $= {vart}_UCTS.M(UCN,T,S{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UC_N,'NONE','NONE','NONE') $= {var}_UC.M(UC_N{arg5});
  {arg1}PAR_UCSM({arg2}UC_N,R,'NONE','NONE')      $= {var}_UCR.M(UC_N,R{arg5});
  {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,'NONE')      $= {vart}_UCT.M(UC_N,T{arg4});
  {arg1}PAR_UCSM({arg2}UC_N,R,T,'NONE')           $= {vart}_UCRT.M(UC_N,R,T{
                arg4
            })*R_DF(R,T);
  {arg1}PAR_UCSM({arg2}UC_N,'NONE',T,S)           $= {vart}_UCTS.M(UC_N,T,S{arg4});
  {arg1}PAR_UCSM({arg2}UC_N,R,T,S)                $= {vart}_UCRTS.M(UC_N,R,T,S{
                arg4
            })*R_DF(R,T);

* UCMAX equations
{g_ucmax_code}
'''
        )
    }
*-----------------------------------------------------------------------------
* Prepare ELC supply by energy source
{"RPT_OPT('FLO','5')=1;" if solans == "YES" else ""}
  IF(RPT_OPT('FLO','5'),
  TRACKP(R,P)$SUM(TOP(RPC_SPG(R,P,C),'IN')$NRGELC(R,C),1) = YES;
  TRACKPC(RPC(RP_FLO(R,P),C))$(TOP(RPC,'OUT')$NRGELC(R,C)) = YES;
  TRACKPC(TRACKP,C) = NO; OPTION TRACKP < TRACKPC, CLEAR=F_VIO, CLEAR=KEEP_FLOF;
  TRACKPG(TRACKP(R,P),C)$((NOT NRGELC(R,C))$NRG(R,C)$TOP(R,P,C,'IN')) = YES;
  F_VIO(RTP_VINTYR(R,V,T,P),IO)$TRACKP(R,P) =
    SUM((TRACKPC(R,P,C),S)$(NOT IPS(IO)),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))+SUM((TRACKPG(R,P,C),IPS(IO),S),{arg1}F_IN({arg2}R,V,T,P,C,S))+1-1;
  {arg1}PAR_EOUT({arg2}RTP_VINTYR(R,V,T,P),C)$(F_VIO(R,V,T,P,'IN')$TRACKPG(R,P,C)) =
    F_VIO(R,V,T,P,'OUT') / F_VIO(R,V,T,P,'IN') * SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{
        arg1
    }F_IN({arg2}R,V,T,P,C,S));
  OPTION CLEAR=TRACKPC; LOOP(TOP_IRE(R,C,NRGELC(R,COM),P),TRACKPC(R,P,C)=YES; TRACKPC(R,P,COM)=YES);
  KEEP_FLOF(RPC(R,P,C))$(NOT TRACKPC(RPC)) $= SUM(RPC_IRE(RPC,IE),1)$NRGELC(R,C);
  {arg1}PAR_EOUT({arg2}RTP_VINTYR(R,V,T,P),C)$(KEEP_FLOF(R,P,C)$RP_IRE(R,P)) =
    SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))$RPC_IRE(R,P,C,'IMP') -
    SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),{arg1}F_IN({
        arg2
    }R,V,T,P,C,S))$RPC_IRE(R,P,C,'EXP');
  KEEP_FLOF(RPC_SPG(TRACKP,C)) = YES;
  OPTION CLEAR=F_VIO,CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=TRACKPG);

*-----------------------------------------------------------------------------
* Levelized cost calculation
*-----------------------------------------------------------------------------
 F=RPT_OPT('NCAP','1');
 LOOP((SYSUC('{sysprefix}LEVCOST'),ANNUAL(SL))$F, Z=F<0; F=1-Z+(F>1);
  NCAP_YES(R,T,P)$(VAR_NCAP.L(R,T,P)*COEF_RTP(R,T,P)$(RP_INOUT(R,P,'OUT')+PRC_PKAF(R,P))=0)=NO;
  PASTSUM(R,T,P)${arg1}PAR_CAPL({arg2}R,T,P) = {arg1}PAR_CAPL({arg2}R,T,P)+SUM(PASTCV,{
        arg1
    }PAR_PASTI({arg2}R,T,P,PASTCV))+1-1;
* Calculate ENV credit
  LOOP(COM_LIM(ENV(R,C),'LO')$Z,TRACKC(R,C)=YES;TRACKP(R,P)$(PRC_MAP(R,'PRE',P)$TOP(R,P,C,'OUT'))=YES);
  TRACKPC(TRACKP(R,P),C)$(NRG(R,C)$TOP(R,P,C,'OUT'))=YES; TRACKC(R,C)$SUM(TRACKPC(R,P,C),1)=YES;
  VDA_EMCB(R,T,C,C)$(NRG(R,C)$TRACKC(R,C)) =
   MIN(SUM(TRACKC(ENV(R,COM)),MIN(0,COM_AGG(R,T,C,COM)*{arg1}PAR_COMBALEM({
        arg2
    }R,T,COM,SL))),
    SUM(P$TRACKPC(R,P,C),
     SUM((VNT(V,T),S)${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))/MAX(MICRO,SUM((TRACKPC(R,P,COM2),VNT(V,T),S)${arg1}F_OUT({
        arg2
    }R,V,T,P,COM2,S),{arg1}F_OUT({arg2}R,V,T,P,COM2,S))) *
     SUM((VNT(V,T),TRACKC(ENV(R,COM)))${arg1}F_OUT({arg2}R,V,T,P,COM,SL),{arg1}F_OUT({
        arg2
    }R,V,T,P,COM,SL)*MIN(0,{arg1}PAR_COMBALEM({arg2}R,T,COM,SL)))) /
    MAX(MICRO,SUM((VNT(V,T),P,S)${arg1}F_OUT({arg2}R,V,T,P,C,S),{arg1}F_OUT({
        arg2
    }R,V,T,P,C,S))+SUM(S${arg1}AGG_OUT({arg2}R,T,C,S),{arg1}AGG_OUT({arg2}R,T,C,S))));
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=COEF_CAP; TRACKC(NRG)=NO;
* Credit for aux energy ouputs (ELE+CHP+HPL)
  OPTION RP_PRC < NCAP_YES; TRACKP(RP_PRC(RP))=ELE(RP)+CHP(RP)+HPL(RP);
  TRACKPC(TRACKP(R,P),C)$(TOP(R,P,C,'OUT')$(NOT RPC_PG(R,P,C)*(NRGELC(R,C)+(NOT CHP(R,P))))$NRG(R,C))=YES;
  OPTION TRACKP < TRACKPC;
  IF(Z,COEF_CAP(RTP_VINTYR(R,V,T,P))$TRACKP(R,P)=1-1/(1+SUM(RPCS_VAR(TRACKPC(R,P,C),S),PAR_FLO(R,V,T,P,C,S))/MAX(MICRO,SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,V,T,P,C,S)))));
  IF(F=1,RP_GRP(RPC_PG(RP_PRC,C))$(NOT TRACKPC(RPC_PG))=YES);
* Credit for peak capacity
  LOOP((COM_PEAK(R,CG),COM_GMAP(R,CG,C)),TRACKPG(RP_PRC(R,P),C)$TOP(R,P,C,'OUT')=YES;
    PAR_RTCS(RTCS_VARC(R,T,C,S))=SUM(COM_PKTS(R,CG,TS)$RS_TREE(R,S,TS),{arg1}PAR_PEAKM({
        arg2
    }R,T,CG,TS)/(1+MAX(COM_PKRSV(R,T,C),SUM(COM(CG),COM_PKRSV(R,T,COM))))*RS_FR(R,TS,S))*COM_IE(R,T,C,S));
  OPTION RP_PRC < RPC_PKC; RP_PRC(RP)$(F<2)=NO; TRACKPG(RPC_PG(RP_PRC,C))=NO;
* Cost ratio for vintaged
 {arg1}PAR_NCAPR({arg2}NCAP_YES(R,TT(V),P),SYSUC)$PRC_VINT(R,P) =
   (COEF_RTP(R,V,P)*VAR_NCAP.L(R,V,P) +
    SUM(RTP_VINTYR(R,V,T,P),COEF_PVT(R,T) *
        (SUM(RPM,{arg1}CST_ACTC({arg2}R,V,T,P,RPM)) +
         SUM(TOP(R,P,C,'IN'),(1-COEF_CAP(R,V,T,P)) * ({arg1}CST_FLOC({arg2}R,V,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,V,T,P,C) +
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_IN({arg2}R,V,T,P,C,TS),
                ({arg1}PAR_COMBALEM({arg2}R,T,C,S)+VDA_EMCB(R,T,C,C))*{arg1}F_IN({
        arg2
    }R,V,T,P,C,TS)*RS_FR(R,S,TS))$(NOT TRACKC(R,C)))) +
         SUM(TOP(R,P,C,'OUT')$(NOT TRACKPC(R,P,C)$Z),{arg1}CST_FLOC({arg2}R,V,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,V,T,P,C) -
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_OUT({arg2}R,V,T,P,C,TS),
                ({arg1}PAR_COMBALEM({
        arg2
    }R,T,C,S)*COM_IE(R,T,C,S)+(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))*PAR_RTCS(R,T,C,S)$TRACKPG(R,P,C))*{
        arg1
    }F_OUT({arg2}R,V,T,P,C,TS)*RS_FR(R,S,TS))$(NOT RP_GRP(R,P,C))$F) -
         SUM((RPC_PG(RP_PRC(R,P),C),COM_TS(R,C,S)),NCAP_PKCNT(R,V,P,S)*PAR_RTCS(R,T,C,S)*VAR_NCAP.L(R,V,P)*G_YRFR(R,S)*PRC_CAPACT(R,P)*PRC_ACTFLO(R,V,P,C))))) /
    MAX(MICRO,SUM(RTP_CPTYR(R,V,T,P),COEF_PVT(R,T)*SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,V,T,P,C,S))));
* Cost ratio for non-vintaged
 {arg1}PAR_NCAPR({arg2}NCAP_YES(R,TT(V),P),SYSUC)$(NOT PRC_VINT(R,P)) =
   (COEF_RTP(R,V,P) +
    SUM(RTP_CPTYR(R,V,T,P)$PASTSUM(R,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)/PASTSUM(R,T,P) *
        (SUM(RPM,{arg1}CST_ACTC({arg2}R,T,T,P,RPM)) +
         SUM(TOP(R,P,C,'IN'),(1-COEF_CAP(R,T,T,P)) * ({arg1}CST_FLOC({arg2}R,T,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,T,T,P,C) +
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_IN({arg2}R,T,T,P,C,TS),
                ({arg1}PAR_COMBALEM({arg2}R,T,C,S)+VDA_EMCB(R,T,C,C))*{arg1}F_IN({
        arg2
    }R,T,T,P,C,TS)*RS_FR(R,S,TS))$(NOT TRACKC(R,C)))) +
         SUM(TOP(R,P,C,'OUT')$(NOT TRACKPC(R,P,C)$Z),{arg1}CST_FLOC({arg2}R,T,T,P,C)+{
        arg1
    }CST_FLOX({arg2}R,T,T,P,C) -
            SUM((COM_TS(R,C,S),RS_TREE(R,S,TS))${arg1}F_OUT({arg2}R,T,T,P,C,TS),
                ({arg1}PAR_COMBALEM({
        arg2
    }R,T,C,S)*COM_IE(R,T,C,S)+(NCAP_PKCNT(R,V,P,S)**RPC_PKF(R,P,C))*PAR_RTCS(R,T,C,S)$TRACKPG(R,P,C))*{
        arg1
    }F_OUT({arg2}R,T,T,P,C,TS)*RS_FR(R,S,TS))$(NOT RP_GRP(R,P,C))$F) -
         SUM((RPC_PG(RP_PRC(R,P),C),COM_TS(R,C,S)),NCAP_PKCNT(R,V,P,S)*PAR_RTCS(R,T,C,S)*PASTSUM(R,T,P)*G_YRFR(R,S)*PRC_CAPACT(R,P)*PRC_ACTFLO(R,V,P,C))))) /
    MAX(MICRO,SUM(RTP_CPTYR(R,V,T,P)$PASTSUM(R,T,P),COEF_PVT(R,T)*COEF_CPT(R,V,T,P)/PASTSUM(R,T,P)*SUM(RPCS_VAR(RPC_PG(R,P,C),S)$(NOT TRACKPC(R,P,C)),PAR_FLO(R,T,T,P,C,S))));
 OPTION CLEAR=TRACKP,CLEAR=TRACKC,CLEAR=TRACKPC,CLEAR=TRACKPG,CLEAR=VDA_EMCB,CLEAR=PASTSUM,CLEAR=PAR_RTCS,CLEAR=COEF_CAP;
 );
* Fallback of flows to ANNUAL level
 LOOP(ANNUAL(TS)$CARD(UNCD1),
   LOOP(UNCD1(COM_TYPE(CG)),TRACKC(R,C)$COM_TMAP(R,COM_TYPE,C)=RPT_OPT(CG,'3')<0);
   LOOP(UNCD1(NRG_TYPE(U2))$RPT_OPT(U2,'3'),TRACKC(R,C)$NRG_TMAP(R,NRG_TYPE,C)=RPT_OPT(U2,'3')<0);
   RVTPC(R,V,T,P,C)$TRACKC(R,C) $= SUM(S${arg1}F_IN({arg2}R,V,T,P,C,S),STOA(S));
   F_IOS(RVTPC,TS) = SUM(S${arg1}F_IN({arg2}RVTPC,S),{arg1}F_IN({arg2}RVTPC,S));
   {arg1}F_IN({arg2}RVTPC,S) = 0;  {arg1}F_IN({arg2}RVTPC,S) $= F_IOS(RVTPC,S);
   OPTION CLEAR=RVTPC,CLEAR=F_IOS;
   RVTPC(R,V,T,P,C)$TRACKC(R,C) $= SUM(S${arg1}F_OUT({arg2}R,V,T,P,C,S),STOA(S));
   F_IOS(RVTPC,TS) = SUM(S${arg1}F_OUT({arg2}RVTPC,S),{arg1}F_OUT({arg2}RVTPC,S));
   {arg1}F_OUT({arg2}RVTPC,S) = 0; {arg1}F_OUT({arg2}RVTPC,S) $= F_IOS(RVTPC,S);
   OPTION CLEAR=TRACKC,CLEAR=RVTPC,CLEAR=F_IOS;
 );
"""
