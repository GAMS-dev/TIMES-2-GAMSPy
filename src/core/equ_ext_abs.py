# equ_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * EQU_EXT.abs - Extension for Ancillery Balancing Services
# *-----------------------------------------------------------------------------
# * ABS Final pre-processing
# *-----------------------------------------------------------------------------
# ---------------------------------------------------------------------------


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, If, Loop, Number, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, Round, abs, diag, exp, mod, project, sign, sqrt

from core.base_class import GamsClass
from core.cal_nored_red import cal_nored_red_GP
from core.cal_red_red import CalRedRedConfig, cal_red_red_GP
from core.utils import apply_sw_stvars
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from collections.abc import Callable

    from gamspy import Alias, Expression, Parameter, Set
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SET_OR_ALIAS
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtAbs(GamsClass):
    """Translation unit for equ_ext.abs."""

    # Instance attributes
    module_name: str = "equ_ext_abs"
    gams_source: str = "equ_ext.abs"

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
        self.cal_red_func_GP = self._resolve_cal_red_func_GP()
        self.compile()

    def _resolve_cal_red_func_GP(
        self,
    ) -> Callable[[TimesModelClass, CalRedRedConfig], Expression | ImplicitSet | Sum]:
        """Helper method to determine and return the correct reduction function."""
        if self.env.cal_red == "cal_red.red":
            return cal_red_red_GP
        elif self.env.cal_red == "cal_nored.red":
            return cal_nored_red_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {self.env.cal_red}")

    def compile(self) -> None:
        g = self.tc
        self.tc.enqueue(self.exec1)

        macro.var_bs.activate(
            g=self.tc,
            var=self.env.var,
            sow=self.env.sow,
            sow_GP=self.env.sow_GP,
            pgprim=self.env.pgprim,
        )

        if self.env.stages == "YES":
            apply_sw_stvars(env=self.env, g=self.tc)

        r, v, t, p, k = g.r, g.v, g.t, g.p, g.k
        sws = self.env.sws_GP
        rcapsbm = self.env.rcapsbm_GP

        diag_ok = (~g.PrcVint[r, p]) | diag(v, k)
        varm = self.env.varm_GP
        tmp_GP = Sum(
            g.Modlyear[k].where[g.coef_vnt[r, t, p, k] & diag_ok],
            g.coef_vnt[r, t, p, k]
            * (
                macro.VAR_NCAP_GP(varm, r, k, p, sws).where[t[k]]
                + g.ncap_pasti[r, k, p]
                + rcapsbm
            ),
        )
        self.env.set_scoped("tmp_GP", tmp_GP)
        self.env.set_scoped("r_w_t_GP", (g.BsRvt[*self.env.r_v_t_GP],))

        rts = macro.rts_GP(s=g.s, env=self.env, g=self.tc)
        r_t = self.env.r_t_GP
        r_v_t = self.env.r_v_t_GP
        r_w_t = self.env.r_w_t_GP
        swx = self.env.swx_GP
        swtx = self.env.swtx_GP
        sow = self.env.sow_GP
        var = self.env.var
        mx = self.env.mx_GP
        pgprim = self.env.pgprim
        def_rtp_ffcs = self.tc.defined("RTP_FFCS")

        # ABS Equation Formulations - numbers refer to document (00=01)
        self.abs_eq_1(r_t=r_t, swx=swx, swtx=swtx, var=var, sow=sow, rts=rts)
        self.abs_eq_1p(r_t=r_t, var=var, sow=sow, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_2(
            r_t=r_t,
            swx=swx,
            swtx=swtx,
            var=var,
            sow=sow,
            rts=rts,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )
        self.abs_eq_3(r_t=r_t, swtx=swtx, swx=swx, var=var, sow=sow, rts=rts)
        self.abs_eq_4(r_t=r_t, swx=swx, swtx=swtx, tmp=tmp_GP, mx=mx, rts=rts)
        self.abs_eq_5_to_6(r_v_t=r_v_t, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_7_to_8(r_v_t=r_v_t, swx=swx, swtx=swtx, var=var, sow=sow, rts=rts)
        self.abs_eq_9(r_v_t=r_v_t, swx=swx, swtx=swtx, mx=mx, sow=sow, var=var, rts=rts)
        self.abs_eq_10(r_v_t=r_v_t, swx=swx, swtx=swtx, sow=sow, var=var, rts=rts)
        self.abs_eq_11_to_17(r_w_t=r_w_t, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_18_20(r_w_t=r_w_t, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_19_21(r_w_t=r_w_t, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_22(r_w_t=r_w_t, swx=swx, swtx=swtx, var=var, sow=sow, rts=rts)
        self.abs_eq_23(
            r_v_t=r_v_t, swx=swx, swtx=swtx, sow=sow, var=var, tmp=tmp_GP, rts=rts
        )
        self.abs_eq_24(
            r_w_t=r_w_t, swx=swx, swtx=swtx, var=var, mx=mx, sow=sow, rts=rts
        )
        self.abs_eq_25(
            r_w_t=r_w_t,
            swx=swx,
            swtx=swtx,
            var=var,
            sow=sow,
            rts=rts,
            pgprim=pgprim,
            def_rtp_ffcs=def_rtp_ffcs,
        )
        self.abs_eq_26(r_t=r_t, swx=swx, swtx=swtx, rts=rts)
        self.abs_eq_27(
            r_v_t=r_v_t,
            swx=swx,
            swtx=swtx,
            varm=varm,
            sws=sws,
            mx=mx,
            rcapsbm=rcapsbm,
            rts=rts,
        )
        self.abs_eq_28(r_v_t=r_v_t, swx=swx, swtx=swtx, tmp=tmp_GP, mx=mx, rts=rts)

    # -----------------------------------------------------------------------
    # exec1 - equation control adjustments (GAMS run phase)
    # -----------------------------------------------------------------------
    def exec1(self: EquExtAbs) -> None:
        g = self.tc
        r, v, t, p, s, c = g.r, g.v, g.t, g.p, g.s, g.c
        rtp = g.Rtp

        # * Adjust equation controls
        g.BsUpl[g.RpUpl[g.BsSupp, g.Bdneq]] = True
        g.BsUpc[g.PrcTsl[g.BsSupp[r, p], g.tsl], g.Bdneq].where[
            Sum(g.BsBsc[r, p, c].where[abs(g.bs_rtype[r, c]) > 2.0], 1.0)
        ] = sparse(g.RpUps[r, p, g.tsl, "UP"])
        g.RpUpl[g.BsUpl] = False
        g.RpUpc[g.BsUpc] = False

        # * Activate capacity equations
        project(source=g.BsBsc, target=g.Trackp)
        g.RpUpl[g.Trackp, "N"] = True
        g.RpUps[g.Trackp[r, p], g.tsl, "FX"].where[
            Sum(g.RpUps[g.PrcTsl[r, p, g.tslvl], g.lA], g.Rlup[r, g.tslvl, g.tsl])
        ] = True
        g.RpUps[g.Trackp[r, p], g.tsl, "LO"].where[
            Sum(
                g.PrcTsl[r, p, g.tslvl].where[g.Rlup[r, g.tslvl, g.tsl]],
                ~g.RpUps[r, p, g.tsl, "FX"],
            )
        ] = True
        g.RpUps[g.PrcTsl[g.Trackp, g.tsl[s]], "LO"] = True

        # * Remove other basic Capact equations
        project(source=g.Afups, target=g.Trackp)
        g.bs_maint[r, v, p, s].where[~(g.Trackp[r, p] + g.RpDp[r, p])] = 0.0
        project(source=g.BsSupp, target=g.Trackp)
        project(source=g.ncap_afx, target=g.RpPrc)
        g.Trackp[g.BsStgp] = True
        g.RpPrc[g.RpStd[g.Rp]].where[g.RpUpl[g.Rp, "FX"]] = False
        g.Afs[r, t, p, s, g.lA["UP"]].where[
            (~(g.RpsCaflac[r, p, s, "UP"] + g.RpPrc[r, p]))
            & g.Trackp[r, p]
            & g.BsPrs[r, p, s]
        ] = False
        g.Afups[r, t, p, s].where[g.BsSupp[r, p]] = False
        g.ncap_afc[r, v, p, self.env.pgprim, g.stl[s]].where[
            g.BsPrs[r, p, s] & g.BsStgp[r, p]
        ] = 0.0
        g.Uncd7.setRecords(None)
        g.Trackp.setRecords(None)
        g.RpPrc.setRecords(None)

        with Loop(
            Domain(rtp[r, v, p], g.RpsPrcts[r, p, s]).where[
                (~g.PrcTs[r, p, s]) & g.bs_maint[rtp, s]
            ]
        ):
            g.z[...] = g.bs_maint[rtp, s]
            g.f[...] = abs(g.z)
            with If(
                (g.f >= g.ts_cycle[r, s] * 24.0).where[g.f > 1.0]
                & (g.RpsUps[r, p, s] | (g.stoal[r, s] * sign(g.z) < 2.0))
            ):
                g.Uncd7[rtp, s, rtp] = True

        with Loop(g.Uncd7[rtp, s, r, t, p]):
            g.RpsUps[r, p, g.ts].where[g.stoal[r, g.ts] == 1.0] = True
            g.bs_maint[rtp, g.ts].where[g.RsTree[r, s, g.ts]] = Number(
                SpecialValues.EPS
            ).where[(g.bs_maint[rtp, g.ts] >= 0.0) & g.bs_maint[rtp, g.ts]]

        g.BsRvt[r, g.Vnt[v, t]] = sparse(
            Sum(g.Rc[r, c].where[g.bs_lambda[r, t, c]], 1.0)
        )

    def _coef_af(
        self,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
    ) -> Parameter:
        """COEF_AF%MX% -- MX selects a variant COEF_AF symbol (see eqactups_vda.py)."""
        g = self.tc
        if mx == ():
            return g.coef_af
        if isinstance(mx, tuple):
            if mx[0] not in ("UPS", ""):
                raise NotImplementedError(
                    f"Expected mx to be one of ['UPS',''] got {mx}"
                )
            # GAMS macro expands COEF_AF%MX% by literal string concatenation.
            return g.get_parameter(f"COEF_AF{''.join(str(x) for x in mx)}")
        raise TypeError(
            f"mx must be a tuple of strings for COEF_AF lookup, got {type(mx)}"
        )

    # -----------------------------------------------------------------------
    # ABS Equation Formulations - numbers refer to document (00=01)
    # -----------------------------------------------------------------------
    def abs_eq_1(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Demands for reserves"""
        g = self.tc
        r, t, c, s = g.r, g.t, g.c, g.s
        rtc = g.Rtc
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")

        g.eq_bs00[g.Rtc[*r_t, c], rts, *swx].where[
            swtx * (g.bs_omega[r, "0", c, s] & g.bs_lambda[rtc])
        ] = Sum(
            g.RhsCombal[rtc, g.ts].where[g.TsMap[r, g.ts, s]],
            VAR_COMPRD[rtc, g.ts, *sow] / g.g_yrfr[r, g.ts],
        ) <= Sum(
            # * Supply (converted to common flow units, as also demand)
            Domain(g.RhsCombal[rtc, g.sl], g.TsMap[r, g.sl, s]).where[
                g.bs_omega[rtc, g.sl]
            ],
            Sum(
                g.RtpVintyr[r, g.v, t, g.p].where[
                    g.BsBsc[r, g.p, c] + Number(1).where[g.bs_stime[r, g.p, c, "UP"]]
                ],
                g.prc_capact[r, g.p]
                * Sum(
                    g.BsPrs[r, g.p, g.ts].where[g.rs_fr[r, s, g.ts]],
                    (
                        macro.var_bs.var_bsfsp_GP(r, g.v, t, g.p, c, g.ts)
                        + Sum(
                            g.BsSupp[r, g.p].where[abs(g.bs_rtype[r, c]) > 2.0],
                            macro.var_bs.var_bsfnsp_GP(r, g.v, t, g.p, c, g.ts),
                        )
                    )
                    * g.rs_fr[r, g.ts, s],
                ),
            ),
        )

    def abs_eq_1p(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Max and ABS(diff) and Share equations"""
        g = self.tc
        r, t, c, s = g.r, g.t, g.c, g.s
        rtc = g.Rtc
        VAR_COMNET = g.get_variable(f"{var}_COMNET")

        g.eq_bs01[g.RhsCombal[g.Rtc[*r_t, c], rts], g.BsK, g.lA, *swx].where[
            swtx
            * (
                ((g.bs_omega[rtc, s] != 2.0) & g.ips[g.lA])
                & g.bs_share[rtc, g.BsK, g.lA]
                & g.bs_omega[rtc, s]
            )
        ] = (
            Sum(
                g.bd[g.lim[g.BsK]],
                VAR_COMNET[rtc, s, *sow] / g.g_yrfr[r, s]
                - g.bs_lambda[rtc]
                * (
                    macro.var_bs.var_bsd_GP("PRB", rtc, s).where[g.Bdupx[g.bd]]
                    - macro.var_bs.var_bsd_GP("DET", rtc, s).where[g.Bdlox[g.bd]]
                ).where[g.bs_omega[rtc, s] < 2.0]
                - (
                    (
                        macro.var_bs.var_bsd_GP("PRB", rtc, s)
                        - macro.var_bs.var_bsd_GP("DET", rtc, s)
                    )
                    * g.bdsig[g.bd]
                ).where[g.bs_omega[rtc, s] > 2.0],
            ).where[g.ips[g.lA]]
            + Sum(
                g.bd[g.lA],
                # * Supply by group
                Sum(
                    g.RtpVintyr[r, g.v, t, g.p].where[
                        (
                            g.BsBsc[r, g.p, c]
                            + Number(1).where[g.bs_stime[r, g.p, c, "UP"]]
                        )
                        & g.gr_genmap[r, g.p, g.BsK]
                    ],
                    g.prc_capact[r, g.p]
                    * Sum(
                        g.BsPrs[r, g.p, g.ts].where[g.rs_fr[r, s, g.ts]],
                        (
                            macro.var_bs.var_bsfsp_GP(r, g.v, t, g.p, c, g.ts)
                            + Sum(
                                g.BsSupp[r, g.p].where[abs(g.bs_rtype[r, c]) > 2.0],
                                macro.var_bs.var_bsfnsp_GP(r, g.v, t, g.p, c, g.ts),
                            )
                        )
                        * g.rs_fr[r, g.ts, s],
                    ),
                )
                # * Share in demand
                - g.bs_share[rtc, g.BsK, g.lA]
                * VAR_COMNET[rtc, s, *sow]
                / g.g_yrfr[r, s],
            )
            * g.bdsig[g.lA]
        ) >= 0.0

    def abs_eq_2(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        """Loads by source of imbalance for each user category k"""
        g = self.tc
        r, t, s, p = g.r, g.t, g.s, g.p

        cal_red = self.cal_red_func_GP(
            g,
            CalRedRedConfig(
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                arg1=g.c,
                arg2=g.Com,
                arg3=g.ts,
                arg4=p,
                arg5=t,
                arg10=Number(1),
            ),
        )

        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_RLD = g.get_variable(f"{var}_RLD")

        g.eq_bs02[*r_t, rts, g.BsK, *swx].where[
            swtx * (Sum(g.BsSbd[g.Finest[r, s], g.bd], 1.0) & g.BsRtk[r, t, g.BsK])
        ] = (
            Sum(
                g.BsTop[g.RpStd[r, p], g.c, g.io].where[g.gr_genmap[r, p, g.BsK]],
                Sum(
                    Domain(
                        g.RtpVintyr[r, g.v, t, p], g.RtpcsVarf[r, t, p, g.c, g.ts]
                    ).where[g.rs_fr[r, s, g.ts]],
                    cal_red
                    * g.rs_fr[r, s, g.ts]
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, g.c, s, g.ts, sow)),
                ),
            )
            + Sum(
                g.RpcStg[r, p, g.c].where[g.gr_genmap[r, p, g.BsK]],
                sign(g.gr_genmap[r, p, g.BsK])
                * Sum(
                    Domain(g.RtpVintyr[r, g.v, t, p], g.RpcsVar[r, p, g.c, g.ts]).where[
                        g.rs_fr[r, s, g.ts]
                    ],
                    g.rs_fr[r, s, g.ts]
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, g.c, s, g.ts, sow))
                    * Sum(
                        g.BsTop[r, p, g.c, "OUT"],
                        macro.eqlducs.v_u_GP("SOUT", r, g.v, t, p, g.c, g.ts)
                        * g.stg_eff[r, g.v, p],
                    )
                    - Sum(
                        g.BsTop[r, p, g.c, "IN"],
                        macro.eqlducs.v_u_GP("SIN", r, g.v, t, p, g.c, g.ts),
                    ),
                ),
            )
            + Sum(
                g.RpcIre[r, p, g.c, g.ie].where[
                    g.NrgTmap[r, "ELC", g.c] & g.gr_genmap[r, p, g.BsK]
                ],
                sign(g.gr_genmap[r, p, g.BsK])
                * Sum(
                    Domain(
                        g.RtpVintyr[r, g.v, t, p], g.RtpcsVarf[r, t, p, g.c, g.ts]
                    ).where[g.rs_fr[r, s, g.ts]],
                    (
                        VAR_IRE[r, g.v, t, p, g.c, g.ts, g.ie, *sow].where[
                            ~g.RpcAire[r, p, g.c]
                        ]
                        + (
                            VAR_ACT[r, g.v, t, p, g.ts, *sow]
                            * g.prc_actflo[r, g.v, p, g.c]
                        ).where[g.RpcAire[r, p, g.c]]
                    )
                    * (1.0 - Number(2).where[g.xpt[g.ie]])
                    * g.rs_fr[r, s, g.ts]
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, g.c, s, g.ts, sow)),
                ),
            )
        ) == (VAR_RLD[r, t, s, g.BsK, *sow] * g.g_yrfr[r, s])

    def abs_eq_3(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        swtx: Number | ImplicitSet,
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Stochastic or combined demand with variances"""
        g = self.tc
        r, t, c, s = g.r, g.t, g.c, g.s
        rtc = g.Rtc
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_RLD = g.get_variable(f"{var}_RLD")

        g.eq_bs03[g.Rtc[*r_t, c], rts, *swx].where[
            swtx * (g.Finest[r, s] & g.bs_lambda[rtc])
        ] = (
            Sum(
                Domain(g.RtcsVarc[rtc, g.ts], g.TsMap[r, g.ts, s]).where[
                    g.bs_omega[rtc, g.ts]
                ],
                (g.bs_lambda[rtc] * macro.var_bs.var_bsd_GP("PRB", rtc, g.ts)).where[
                    g.bs_omega[rtc, g.ts] != 2.0
                ]
                + (
                    VAR_COMNET[rtc, g.ts, *sow] / g.g_yrfr[r, g.ts]
                    - g.bs_lambda[rtc]
                    * macro.var_bs.var_bsd_GP("DET", rtc, g.ts)
                    * g.bs_detwt[rtc]
                ).where[g.bs_omega[rtc, g.ts] == 2.0]
                - g.bs_lambda[rtc]
                * (1.0 - g.bs_detwt[rtc].where[g.bs_omega[rtc, g.ts] == 2.0])
                * g.bs_delta[rtc, g.ts]
                * 3.0
                * Sum(
                    g.BsRtk[r, t, g.BsK],
                    g.bs_sigma[rtc, g.BsK, s] * VAR_RLD[r, t, s, g.BsK, *sow],
                ),
            )
            >= 0.0
        )

    def abs_eq_4(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        tmp: Expression | Sum | int,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Deterministic demand"""
        g = self.tc
        r, t, c, s, p = g.r, g.t, g.c, g.s, g.p
        rtc = g.Rtc
        coef_af = self._coef_af(mx)

        g.eq_bs04[g.RhsCombal[g.Rtc[*r_t, c], rts], p, *swx].where[
            swtx * (g.Rtp[r, t, p] & g.gr_genmap[r, p, "SI"] & g.bs_omega[rtc, s])
        ] = macro.var_bs.var_bsd_GP("DET", rtc, s) >= g.bs_rtcs[
            "EXOGEN", rtc, s
        ] * g.bs_capact[r] + g.prc_capact[r, p] * g.bs_rtcs["WMAXSI", rtc, s] * Sum(
            g.RtpVintyr[r, g.v, t, p],
            tmp
            * Sum(
                g.PrcTs[r, p, g.ts].where[g.rs_fr[r, g.ts, s]],
                Sum(g.Bdupx[g.bd], coef_af[r, g.v, t, p, g.ts, g.bd])
                * g.rs_fr[r, g.ts, s],
            ),
        )

    def abs_eq_5_to_6(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Minimum online and offline times (adjusted)"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s

        g.eq_bs05[g.RtpVintyr[*r_v_t, p], g.tsl, g.bd[g.lA], rts, *swx].where[
            swtx * (g.TsGroup[r, g.tsl, s] & g.BsUpc[r, p, g.tsl, g.lA])
        ] = (
            Sum(
                Domain(g.RsUp[r, s, g.Js], g.RjSl[r, g.Js, g.sl]),
                macro.eqlducs.v_u_GP("UPS", r, v, t, p, g.sl, g.lA).where[
                    g.rs_modus[r, s, g.Js, g.sl] < g.act_time[r, t, p, g.lA] / 8760.0
                ],
            )
            + Sum(
                g.lim[g.Bdneq].where[g.bdsig[g.lim] * g.bdsig[g.lA] < 0.0],
                macro.var_bs.var_bsupsr_GP(
                    r, v, t, p, s, g.lim, extra=g.BsSbd[r, s, g.lim]
                )
                - (
                    Sum(
                        g.RsUp[r, s, g.j, g.ts],
                        macro.eqlducs.v_u_GP("UPS", r, v, t, p, g.ts, "FX"),
                    ).where[g.Bdupx[g.lA]]
                    + macro.eqlducs.var_off_GP(r, v, t, p, s) * g.bdsig[g.lA]
                ).where[
                    g.BsSbd[r, s, g.lim] + Number(1).where[g.act_time[r, t, p, g.lA]]
                ],
            )
        ) <= 0.0

    def abs_eq_7_to_8(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Ramping rates (adjusted)"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")

        g.eq_bs07[g.RtpVintyr[*r_v_t, p], rts, g.Bdneq[g.bd], *swx].where[
            swtx
            * (
                Sum(g.TsAnn[s, g.ts].where[g.act_ups[r, v, p, g.ts, g.bd]], 1.0).where[
                    g.PrcTs[r, p, s] & g.BsUpl[r, p, g.bd]
                ]
                # * max fraction of capacity
            )
        ] = (
            Sum(
                g.PrcTs[r, p, g.ts[g.s.lag(g.rs_stg[r, s], "circular")]],
                g.prc_capact[r, p]
                * Sum(g.TsAnn[s, g.sl], g.act_ups[r, v, p, g.sl, g.bd])
                * (
                    macro.var_bs.var_bson_GP(r, v, t, p, s)
                    + (
                        macro.eqlducs.var_off_GP(r, v, t, p, s)
                        - macro.eqlducs.var_off_GP(r, v, t, p, g.ts)
                        - macro.var_bs.var_bsupsr_GP(
                            r,
                            v,
                            t,
                            p,
                            s,
                            g.bd,
                            extra=Sum(g.BsComts[g.BsAneg[r, g.c], s], 1.0),
                        )
                    ).where[g.Bdlox[g.bd] & g.RpsUps[r, p, s]]
                )
                # * dynamic ramp limits
                + g.rs_stgprd[r, s]
                * 2.0
                / (g.g_yrfr[r, s] + g.g_yrfr[r, g.ts])
                / 8760.0
                * (
                    VAR_ACT[r, v, t, p, s, *sow] / g.g_yrfr[r, s]
                    - VAR_ACT[r, v, t, p, g.ts, *sow] / g.g_yrfr[r, g.ts]
                    + (
                        (
                            macro.eqlducs.var_off_GP(r, v, t, p, s)
                            - macro.eqlducs.var_off_GP(r, v, t, p, g.ts)
                        )
                        * g.prc_capact[r, p]
                        * g.act_minld[r, v, p]
                    ).where[g.RpsUps[r, p, s]]
                )
                * g.bdsig[g.bd]
                - g.prc_capact[r, p]
                * Sum(
                    g.BsBsc[r, p, g.c].where[g.BsAbd[r, g.c, g.bd]],
                    macro.var_bs.var_bsfsp_GP(
                        r, v, t, p, g.c, s, extra=g.BsComts[r, g.c, s]
                    ),
                ),
            )
            >= 0.0
        )

    def abs_eq_9(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        var: str,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Capacity margin constraints - positive"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")
        coef_af = self._coef_af(mx)

        g.eq_bs09[g.RtpVintyr[*r_v_t, p], rts, g.lA["UP"], *swx].where[
            swtx * (g.BsPrs[r, p, s] & (~g.RpDp[r, p]) & g.BsSupp[r, p])
        ] = (
            Sum(
                g.BsComts[g.BsApos[r, g.c], s].where[g.BsBsc[r, p, g.c]],
                macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s),
            )
            * g.prc_capact[r, p]
            + (
                g.prc_capact[r, p]
                * (coef_af[r, v, t, p, s, g.lA] - g.act_minld[r, v, p])
                * macro.eqlducs.v_u_GP("UPS", r, v, t, p, s, g.lA)
                * Min(
                    1.0,
                    g.act_sdtime[r, v, p, "HOT", g.lA]
                    / 8760.0
                    / (g.g_yrfr[r, s] / g.rs_stgprd[r, s]),
                )
            ).where[g.RpsUps[r, p, s]]
        ) <= (
            g.prc_capact[r, p]
            * coef_af[r, v, t, p, s, g.lA]
            * macro.var_bs.var_bson_GP(r, v, t, p, s)
            - (
                VAR_ACT[r, v, t, p, s, *sow].where[g.RpStd[r, p]]
                + Sum(
                    g.Top[g.RpcStg[r, p, g.c], "OUT"],
                    macro.eqlducs.v_u_GP("SOUT", r, v, t, p, g.c, s)
                    * g.stg_eff[r, v, p],
                ).where[g.RpStg[r, p]]
            )
            / g.g_yrfr[r, s]
        )

    def abs_eq_10(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        var: str,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Capacity margin constraints - negative"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")

        g.eq_bs10[g.RtpVintyr[*r_v_t, p], rts, *swx].where[
            swtx * (g.BsPrs[r, p, s] & g.BsNegp[r, p] & g.BsSupp[r, p])
        ] = (
            Sum(
                g.BsComts[g.BsAneg[r, g.c], s].where[g.BsBsc[r, p, g.c]],
                macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s)
                + macro.var_bs.var_bsfnsp_GP(r, v, t, p, g.c, s, extra=g.RpStd[r, p]),
            )
            * g.prc_capact[r, p]
        ) <= (
            VAR_ACT[r, v, t, p, s, *sow].where[g.RpStd[r, p]]
            + Sum(
                g.Top[g.RpcStg[r, p, g.c], "OUT"],
                macro.eqlducs.v_u_GP("SOUT", r, v, t, p, g.c, s) * g.stg_eff[r, v, p],
            ).where[g.RpStg[r, p]]
        ) / g.g_yrfr[r, s] - g.prc_capact[r, p] * g.act_minld[r, v, p] * (
            macro.var_bs.var_bson_GP(r, v, t, p, s)
            - Sum(
                g.RpsUps[r, p, s],
                macro.var_bs.var_bsupsr_GP(
                    r, v, t, p, s, "LO", extra=Sum(g.BsComts[g.BsAneg[r, g.c], s], 1.0)
                ),
            )
        )

    def abs_eq_11_to_17(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Limit reserve by type and sign according to BS_RMAX"""
        g = self.tc
        r, v, t, p, c, s = g.r, g.v, g.t, g.p, g.c, g.s

        g.eq_bs11[g.RtpVintyr[*r_w_t, p], c, rts, g.bd, *swx].where[
            swtx
            * (
                g.BsPrs[r, p, s]
                & g.BsComts[r, c, s]
                & g.RpcConly[r, v, p, c]
                & g.BsAbd[r, c, g.bd]
            )
        ] = Sum(
            g.BsAbd[r, g.Com, g.bd].where[
                abs(g.bs_rtype[r, g.Com]) <= abs(g.bs_rtype[r, c])
            ],
            macro.var_bs.var_bsfsp_GP(
                r,
                v,
                t,
                p,
                g.Com,
                s,
                extra=g.BsBsc[r, p, g.Com] & g.BsComts[r, g.Com, s],
            ),
        ) <= (
            macro.var_bs.var_bson_GP(r, v, t, p, s)
            - Sum(
                g.RpsUps[r, p, s].where[g.Bdlox[g.bd]],
                macro.var_bs.var_bsupsr_GP(r, v, t, p, s, g.bd),
            )
        ) * Sum(g.TsAnn[s, g.ts], g.bs_rmax[r, v, p, c, g.ts])

    def abs_eq_18_20(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Limit the provision of TRT & RRR reserves according to quick start-up / shut-down capacity"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s

        g.eq_bs18[g.RtpVintyr[*r_w_t, p], rts, g.Bdneq[g.bd], *swx].where[
            swtx
            * (
                g.BsPrs[r, p, s]
                & g.RpsUps[r, p, s]
                & g.act_minld[r, v, p]
                & g.BsSupp[r, p]
            )
        ] = (
            macro.var_bs.var_bsupsr_GP(r, v, t, p, s, g.bd) * g.act_minld[r, v, p]
        ).where[g.BsSbd[r, s, g.bd]] <= Sum(
            g.BsAbd[r, g.c, g.bd].where[abs(g.bs_rtype[r, g.c]) > 2.0],
            macro.var_bs.var_bsfnsp_GP(
                r, v, t, p, g.c, s, extra=g.BsBsc[r, p, g.c] & g.BsComts[r, g.c, s]
            ),
        )

    def abs_eq_19_21(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Limit the provision of TRT & RRR reserves according to quick start-up / shut-down capacity"""
        g = self.tc
        r, v, t, p, c, s = g.r, g.v, g.t, g.p, g.c, g.s

        g.eq_bs19[g.RtpVintyr[*r_w_t, p], c, rts, g.bd, *swx].where[
            swtx
            * (
                (abs(g.bs_rtype[r, c]) > 2.0)
                & g.BsPrs[r, p, s]
                & g.BsSupp[r, p]
                & g.BsBsc[r, p, c]
                & g.BsAbd[r, c, g.bd]
            )
        ] = Sum(
            g.BsAbd[r, g.Com, g.bd].where[
                mod(abs(g.bs_rtype[r, g.Com]) - 1.0, g.bs_rtype[r, c]) > 1.0
            ],
            macro.var_bs.var_bsfnsp_GP(
                r,
                v,
                t,
                p,
                g.Com,
                s,
                extra=g.BsBsc[r, p, g.Com] & g.BsComts[r, g.Com, s],
            ),
        ) <= (
            macro.var_bs.var_bsupsr_GP(r, v, t, p, s, g.bd, extra=g.RpsUps[r, p, s])
            * Sum(g.TsAnn[s, g.ts], g.bs_rmax[r, v, p, c, g.ts]).where[
                g.BsComts[r, c, s]
            ]
        )

    def abs_eq_22(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Ensure sufficient storage level when contracted to reserve"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")

        g.eq_bs22[g.RtpVintyr[*r_w_t, p], rts, *swx].where[
            swtx * (g.BsStgp[r, p] & g.coef_afups[r, v, p, s] & g.RpsStg[r, p, s])
        ] = (
            # * storage: for single-day (true) activity divide by cycles under parent
            Sum(
                g.PrcTs[r, p, g.ts].where[g.rs_fr[r, g.ts, s]],
                VAR_ACT[r, v, t, p, g.ts, *sow]
                * g.rs_fr[r, g.ts, s]
                / g.rs_stgprd[r, g.ts],
            ).where[g.BsSbd[r, s, "UP"]]
            >= Sum(
                g.BsComts[g.BsApos[r, g.c], s],
                g.prc_capact[r, p]
                / sqrt(g.stg_eff[r, v, p])
                / 8760.0
                * macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s)
                * (
                    g.bs_stime[r, p, g.c, "LO"] / 2.0
                    + (g.bs_stime[r, p, g.c, "UP"] - g.bs_stime[r, p, g.c, "LO"])
                    * Max(
                        1.0,
                        g.g_yrfr[r, s]
                        / g.rs_stgprd[r, s]
                        * 8760.0
                        / (1.0 + g.bs_stime[r, p, g.c, "UP"]) ** 0.5,
                    )
                ),
            )
        )

    def abs_eq_23(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        var: str,
        tmp: Expression | Sum | int,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Limit storage level by capacity and contracted reserve"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")

        g.eq_bs23[g.RtpVintyr[*r_v_t, p], rts, *swx].where[
            swtx * (g.BsStgp[r, p] & g.coef_afups[r, v, p, s] & g.RpsStg[r, p, s])
        ] = (
            # * storage: for single-day (true) activity divide by cycles under parent
            Sum(
                g.PrcTs[r, p, g.ts].where[g.rs_fr[r, g.ts, s]],
                VAR_ACT[r, v, t, p, g.ts, *sow]
                * g.rs_fr[r, g.ts, s]
                / g.rs_stgprd[r, g.ts],
            )
            <=
            # * available process capacity - vintaged or not
            (tmp * g.coef_afups[r, v, p, s] / exp(g.prc_sc[r, p]) * g.prc_capact[r, p])
            - Sum(
                g.BsComts[g.BsAneg[r, g.c], s],
                g.prc_capact[r, p]
                * sqrt(g.stg_eff[r, v, p])
                / 8760.0
                * macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s)
                * (
                    g.bs_stime[r, p, g.c, "LO"] / 2.0
                    + (g.bs_stime[r, p, g.c, "UP"] - g.bs_stime[r, p, g.c, "LO"])
                    * Max(
                        1.0,
                        g.g_yrfr[r, s]
                        / g.rs_stgprd[r, s]
                        * 8760.0
                        / (1.0 + g.bs_stime[r, p, g.c, "UP"]) ** 0.5,
                    )
                ),
            )
        )

    def abs_eq_24(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """End-use - negative"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        VAR_ACT = g.get_variable(f"{var}_ACT")
        coef_af = self._coef_af(mx)

        g.eq_bs24[g.RtpVintyr[*r_w_t, p], rts, *swx].where[
            swtx
            * (
                g.BsPrs[r, p, s]
                & g.Afs[r, t, p, s, "UP"]
                & g.BsSbd[r, s, "LO"]
                & g.BsNegp[r, p]
                & g.BsEndp[r, p]
            )
        ] = (
            Sum(
                g.BsComts[g.BsAneg[r, g.c], s].where[g.BsBsc[r, p, g.c]],
                macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s),
            )
            <=
            # * available process capacity - activity level
            (
                macro.var_bs.var_bson_GP(r, v, t, p, s) * coef_af[r, v, t, p, s, "UP"]
                - VAR_ACT[r, v, t, p, s, *sow] / g.prc_capact[r, p] / g.g_yrfr[r, s]
            )
            * Sum(
                g.Top[r, p, g.c, "IN"].where[g.NrgTmap[r, "ELC", g.c]],
                (
                    g.prc_actflo[r, v, p, g.c].where[g.RpcPg[r, p, g.c]]
                    + Sum(
                        g.RtpcsVarf[r, t, p, g.c, g.ts].where[g.rs_fr[r, g.ts, s]],
                        g.rs_fr[r, g.ts, s]
                        * Sum(
                            g.RpcPg[r, p, g.Com],
                            g.act_flo[r, v, p, g.c, g.ts].where[g.RpcFfunc[r, p, g.c]]
                            + g.prc_actflo[r, v, p, g.Com]
                            * (
                                Sum(
                                    g.Rpg1ace[r, p, g.cg, g.c].where[
                                        g.coef_ptran[r, v, p, g.cg, g.c, g.Com, g.ts]
                                    ],
                                    1.0 / g.coef_ptran[r, v, p, g.cg, g.c, g.Com, g.ts],
                                )
                                + Sum(
                                    Domain(
                                        g.RpccFfunc[g.RpPg[r, p, g.cg], g.c],
                                        g.TsMap[r, g.sl, g.ts],
                                    ).where[g.RpsS1[r, p, g.sl]],
                                    (g.act_flo[r, v, p, g.c, g.sl] ** 1).where[
                                        g.RpcAflo[r, p, g.c]
                                    ]
                                    * g.coef_ptran[r, v, p, g.cg, g.Com, g.c, s],
                                )
                            ),
                        ),
                    ).where[~g.RpcPg[r, p, g.c]]
                ),
            )
        )

    def abs_eq_25(
        self: EquExtAbs,
        r_w_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        rts: SET_OR_ALIAS,
        pgprim: str,
        def_rtp_ffcs: bool,
    ) -> None:
        """End-use - positive"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s

        cal_red = self.cal_red_func_GP(
            g,
            CalRedRedConfig(
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                arg1=g.c,
                arg2=g.Com,
                arg3=g.ts,
                arg4=p,
                arg5=t,
                arg10=Number(1),
            ),
        )

        g.eq_bs25[g.RtpVintyr[*r_w_t, p], rts, *swx].where[
            swtx * (g.BsPrs[r, p, s] & g.BsSbd[r, s, "UP"] & g.BsEndp[r, p])
        ] = (
            Sum(
                g.BsComts[g.BsApos[r, g.c], s].where[g.BsBsc[r, p, g.c]],
                macro.var_bs.var_bsfsp_GP(r, v, t, p, g.c, s),
            )
            * g.prc_capact[r, p]
            * g.g_yrfr[r, s]
        ) <= Sum(
            g.Top[r, p, g.c, "IN"].where[g.NrgTmap[r, "ELC", g.c]],
            Sum(
                g.RtpcsVarf[r, t, p, g.c, g.ts].where[g.TsMap[r, s, g.ts]], cal_red
            ).where[g.RpStd[r, p]]
            + Sum(
                g.RpcsVar[g.RpcStg[r, p, g.c], g.ts].where[g.TsMap[r, s, g.ts]],
                macro.eqlducs.v_u_GP("SIN", r, v, t, p, g.c, g.ts).where[
                    g.PrcNstts[r, p, g.ts] + g.PrcStgtss[r, p, g.c]
                ],
            ),
        )

    def abs_eq_26(
        self: EquExtAbs,
        r_t: tuple[SET_OR_ALIAS, SET_OR_ALIAS],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        rts: SET_OR_ALIAS,
    ) -> None:
        """Bound on process reserve provision"""
        g = self.tc
        r, t, p, c, s = g.r, g.t, g.p, g.c, g.s

        g.eq_bs26[g.Rtp[*r_t, p], c, rts, *swx].where[
            swtx
            * (
                g.BsComts[r, c, s]
                & (g.BsBsc[r, p, c] + Number(1).where[g.bs_stime[r, p, c, "UP"]])
                & g.bs_bndprs[g.Rtp, c, s, "N"]
            )
        ] = Sum(
            Domain(g.RtpVintyr[r, g.v, t, p], g.BsPrs[r, p, g.ts]).where[
                g.rs_fr[r, g.ts, s]
            ],
            (
                macro.var_bs.var_bsfsp_GP(r, g.v, t, p, c, g.ts)
                + macro.var_bs.var_bsfnsp_GP(
                    r,
                    g.v,
                    t,
                    p,
                    c,
                    g.ts,
                    extra=(abs(g.bs_rtype[r, c]) > 2.0) & g.BsSupp[r, p],
                )
            )
            * g.rs_fr[r, g.ts, s],
        ) == macro.var_bs.var_bslack_GP(r, t, p, c, s)

    def abs_eq_27(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        varm: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        rcapsbm: Expression | Condition | Number,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Maintenence 1 - entrance to maintenance"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        coef_af = self._coef_af(mx)

        diag_ok = (~g.PrcVint[r, p]) | diag(v, g.k)

        g.eq_bs27[g.RtpVintyr[*r_v_t, p], rts, *swx].where[
            swtx * ((g.bs_maint[r, v, p, s] >= 0.0) & g.bs_maint[r, v, p, s])
        ] = Sum(
            g.TsMap[r, s, g.ts].where[g.RpsUps[r, p, g.ts]],
            (
                macro.var_bs.var_bsmup_GP(r, v, t, p, g.ts)
                * Min(
                    1.0,
                    Round(g.bs_maint[r, v, p, s], 1)
                    / 8760.0
                    * g.rs_stgprd[r, g.ts]
                    / g.g_yrfr[r, s],
                )
            ).where[g.PrcTs[r, p, g.ts]]
            + (
                macro.eqlducs.var_off_GP(r, v, t, p, g.ts)
                * g.rs_fr[r, g.ts, s].where[g.bs_maint[r, v, p, s] == 0.0]
            ).where[g.ts_cycle[r, g.ts]],
        ) >= Sum(
            # * unavailable process capacity - vintaged or not
            g.Modlyear[g.k].where[g.coef_vnt[r, t, p, g.k] & diag_ok],
            g.coef_vnt[r, t, p, g.k]
            * (
                macro.VAR_NCAP_GP(varm, r, g.k, p, sws).where[t[g.k]]
                + g.ncap_pasti[r, g.k, p]
                + rcapsbm
            )
            * (
                (1.0 - coef_af[r, g.k, t, p, s, "UP"]).where[
                    g.act_ups[r, t, p, s, "N"] == 0.0
                ]
                + g.act_ups[r, t, p, s, "N"]
            ),
        )

    def abs_eq_28(
        self: EquExtAbs,
        r_v_t: tuple[SET_OR_ALIAS, ...],
        swx: tuple[Literal["1"] | Set | Alias, ...] | tuple[()],
        swtx: Number | ImplicitSet,
        tmp: Expression | Sum | int,
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        rts: SET_OR_ALIAS,
    ) -> None:
        """Maintenence 2 - continuous duration"""
        g = self.tc
        r, v, t, p, s = g.r, g.v, g.t, g.p, g.s
        coef_af = self._coef_af(mx)

        g.eq_bs28[g.RtpVintyr[*r_v_t, p], rts, *swx].where[
            swtx * (g.PrcTs[r, p, s] & g.bs_maint[r, v, p, s])
        ] = Sum(
            Domain(g.RsUp[r, s, g.Js], g.RjSl[r, g.Js, g.sl]),
            macro.var_bs.var_bsmup_GP(r, v, t, p, g.sl).where[
                g.rs_modus[r, s, g.Js, g.sl] < abs(g.bs_maint[r, v, p, s]) / 8760.0
            ],
        ) <= tmp * (1.0 - coef_af[r, v, t, p, s, "UP"]) - (
            macro.upscaps.render_GP() * coef_af[r, v, t, p, s, "UP"]
        )
