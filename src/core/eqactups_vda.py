# eqactups_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQACTUPS - implements the linear dispatching equations
# *   arg1 - MX control
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Domain, Expression, Loop, Number, Ord, Set, Smax, Sum, sparse
from gamspy.math import Max, Min, diag, exp, mod, project

from core.base_class import GamsClass
from core.pp_lvlfc_mod import PpLvlfcModConfig, pp_lvlfc_mod
from core.utils import SET_OR_ALIAS
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqactupsVda(GamsClass):
    """Translation unit for eqactups.vda."""

    # Instance attributes
    module_name: str = "eqactups_vda"
    gams_source: str = "eqactups.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        self.tc.enqueue(self.set_indicators, pgprim=self.env.pgprim)

        self.env.set_scoped(
            "capon",
            f"(COEF_CPT(R,V,T,P)*({macro.VAR_NCAP(self.env.varv, 'R', 'V', 'P', self.env.sws)}$T(V)+NCAP_PASTI(R,V,P){self.env.rcapsub}))$PRC_VINT(R,P)+{macro.VAR_CAP(self.env.var, 'R', 'T', 'P', self.env.sow)}$RP_UX(R,P)",
        )

        sws = self.env.sws_GP
        sow = self.env.sow_GP
        rcapsub = self.env.rcapsub_GP
        if isinstance(rcapsub, Number) and rcapsub._value == 1:
            raise ValueError("rcapsub cannot be Number(1) in this assignment.")

        self.env.set_scoped(
            "capon_GP",
            (
                g.coef_cpt[g.r, g.v, g.t, g.p]
                * (
                    macro.VAR_NCAP_GP(self.env.varv_GP, g.r, g.v, g.p, sws).where[
                        g.t[g.v]
                    ]
                    + g.ncap_pasti[g.r, g.v, g.p]
                    + rcapsub
                ).where[g.PrcVint[g.r, g.p]]
                + macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, sow).where[
                    g.RpUx[g.r, g.p]
                ]
            ),
        )

        self.set_scoped_mx()

        tmp = (
            ~g.RpUx[g.r, g.p],
            macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, sow).where[g.RpUx[g.r, g.p]]
            + macro.upscaps.render_GP(),
        )

        self.equation_capload(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            capon=self.env.capon_GP,
            arg1=self.arg1,
        )

        rts = macro.rts_GP(s=g.s, g=self.tc, env=self.env)

        self.equation_acttramp(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            mx=self.env.mx_GP,
            tmp=tmp,
            rts=rts,
        )
        self.equation_actups(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            mx=self.env.mx_GP,
            tmp=tmp,
            rts=rts,
        )
        self.equation_actupc(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            capon=self.env.capon_GP,
            rts=rts,
        )
        self.equation_actpl(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            mx=self.env.mx_GP,
            tmp=tmp,
            rts=rts,
        )
        self.equation_actrmpc(
            eq=self.env.eq,
            r_v_t=self.env.r_v_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
        )
        self.equation_stgccl(
            r_v_t=self.env.r_v_t_GP,
            mx=self.env.mx_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            swx=self.env.swx_GP,
            swtx=self.env.swtx_GP,
        )

        if self.env.obmac.upper() == "YES":
            macro.var_sift.activate(
                g=self.tc, var=self.env.var, sow=self.env.sow, sow_GP=self.env.sow_GP
            )

        self.equation_slsift(
            eq=self.env.eq,
            r_t=self.env.r_t_GP,
            swt=self.env.swt_GP,
            var=self.env.var,
            sow=self.env.sow_GP,
            pgprim=self.env.pgprim,
            rts=rts,
        )

    def set_scoped_mx(self: EqactupsVda) -> None:
        g = self.tc

        r, v, p, k, t = g.r, g.v, g.p, g.k, g.t
        sws = self.env.sws_GP

        self.env.set_scoped(
            "mx",
            f"SUM(RVP_KMAP(R,V,P,MODLYEAR(K)),COEF_VNT(R,T,P,K)*({macro.VAR_NCAP(self.env.varm, 'R', 'K', 'P', self.env.sws)}$T(K)+NCAP_PASTI(R,K,P){self.env.rcapsbm}))",
        )

        mx_GP = Sum(
            g.RvpKmap[r, v, p, g.Modlyear[k]],
            g.coef_vnt[r, t, p, k]
            * macro.VAR_NCAP_GP(self.env.varm_GP, r, k, p, sws).where[t[k]]
            + g.ncap_pasti[r, k, p]
            + self.env.rcapsbm_GP,
        )

        self.env.set_scoped("mx_GP", mx_GP)

    def set_indicators(self: EqactupsVda, pgprim: str) -> None:
        g = self.tc
        RpUpl, RpPl, act_cstrmp = g.RpUpl, g.RpUpl, g.act_cstrmp

        # Set indicators
        # IF(CARD(RP_UPL)+CARD(RP_PL)+CARD(ACT_CSTRMP),
        if RpPl.number_records + RpUpl.number_records + act_cstrmp.number_records:
            g.Uncd7.setRecords(None)
            g.Afups[g.r, g.t, g.p, g.s].where[
                (~(g.RpsCaflac[g.r, g.p, g.s, "UP"])).where[g.PrcTs[g.r, g.p, g.s]]
            ] = sparse(g.Afs[g.r, g.t, g.p, g.s, "UP"].where[g.RpUpl[g.r, g.p, "FX"]])
            g.Afs[g.Afups, g.bd] = False
            g.RpsUps[g.r, g.p, g.s].where[
                (
                    (
                        g.stoal[g.r, g.s]
                        < 2.0 + Number(1.0).where[g.RpUpr[g.r, g.p, "N"]]
                    ).where[g.RpUpl[g.r, g.p, "FX"]]
                )
            ] = Sum(
                g.PrcTs[g.r, g.p, g.ts].where[g.RsBelow[g.r, g.s, g.ts]],
                (g.RsBelow1[g.r, g.s, g.ts]) | (g.stoa[g.s]),
            )
            g.RpUx[g.Rp].where[~(g.PrcVint[g.Rp])] = sparse(g.RpUpl[g.Rp, "FX"])
            g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[g.RpUx[g.r, g.p]] = True
            g.coef_af[g.r, g.t, g.t, g.p, g.s, "UP"].where[
                g.Afups[g.r, g.t, g.p, g.s]
            ] = sparse(g.ncap_af[g.r, g.t, g.p, g.s, "UP"].where[g.RpUx[g.r, g.p]])
            # * Check for startup costs
            g.Uncd7[
                g.r,
                g.ll.lag(Ord(g.ll), "circular"),
                g.p,
                g.tsl,
                g.Rdcur[g.r, g.cur],
                "UP",
            ] = sparse(g.act_cstup[g.r, g.ll, g.p, g.tsl, g.cur])
            g.Uncd7[
                g.r,
                g.ll.lag(Ord(g.ll), "circular"),
                g.p,
                g.bd,
                g.Rdcur[g.r, g.cur],
                "N",
            ] = sparse(g.act_cstrmp[g.r, g.ll, g.p, g.bd, g.cur])
            with Loop(g.Uncd7[g.r, g.ll, g.p, g.item, g.r, g.cur, g.lA]):
                g.RpUps[g.r, g.p, g.tsl[g.item], g.lA].where[
                    (g.tslvlnum[g.tsl].where[g.RpUpl[g.r, g.p, "FX"]] > 1.0)
                ] = True
                g.RpcCur[g.r, g.p, pgprim, g.cur] = True
            g.RpUps[g.Rp, g.tsl, g.lA].where[
                Sum(g.PrcTsl[g.Rp, g.tslvl].where[(Ord(g.tsl) > Ord(g.tslvl))], 1.0)
            ] = False
            g.RpsUps[g.Rp, g.s].where[
                Sum(g.RpUps[g.PrcTsl[g.Rp, g.tsl], g.lA], 1.0)
            ] = False
            g.RpsUps[g.r, g.p, g.s] = sparse(
                Sum(
                    g.RpUps[g.r, g.p, g.tsl, g.lA].where[g.TsGroup[g.r, g.tsl, g.s]],
                    1.0,
                )
            )
            g.RpUps[g.r, g.p, g.tsl, g.Lnx[g.lA]].where[
                g.RpUps[g.r, g.p, g.tsl, "UP"]
            ] = Sum(
                g.RpUps[g.r, g.p, g.tslvl, g.bd],
                g.Rlup[g.r, g.tslvl, g.tsl].where[g.bd[g.lA]]
                + g.Rlup[g.r, g.tsl, g.tslvl].where[g.ips[g.lA]],
            )
            g.RpUps[g.r, g.p, g.tsl, "FX"].where[
                (
                    Sum(
                        g.RpUps[g.PrcTsl[g.r, g.p, g.tslvl], g.lA],
                        g.Rlup[g.r, g.tslvl, g.tsl],
                    ).where[g.RpUpr[g.r, g.p, "UP"]]
                )
            ] = True
            # * Check partial loads
            with Loop(g.Uncd7[g.r, g.ll, g.p, g.tsl[g.Annual], g.r, g.cur, g.lA]):
                g.RpUps[g.r, g.p, g.tsl, g.lA] = True
                g.RpPl[g.r, g.p, "N"] = ~(g.RpPl[g.r, g.p, g.lA])
            g.act_lospl[g.Rtp[g.r, g.v, g.p], g.Bdneq[g.bd]].where[
                ((g.act_lospl[g.Rtp, g.bd] <= 0.0).where[g.RpPl[g.r, g.p, "N"]])
            ] = Max(0.1 + Number(0.5).where[g.Bdupx[g.bd]], g.act_minld[g.Rtp])

            pp_lvlfc_mod(
                module=self,
                cc=PpLvlfcModConfig(
                    arg1=g.act_ups,
                    arg2=(g.p,),
                    arg3=g.PrcTs,
                    arg4=(g.bd,),
                    arg5=("", "", ""),
                    arg6=g.allts,
                    arg7=(g.v,),
                    arg8=g.Rtp[g.r, g.v, g.p],
                    arg11="N",
                ),
            )

            g.RtpPl[g.Rtp[g.r, g.v, g.p]].where[
                (g.act_lospl[g.Rtp, "LO"] == g.act_minld[g.Rtp]).where[
                    g.RpUpl[g.r, g.p, "FX"]
                ]
            ] = sparse(g.RpPl[g.r, g.p, "N"])
            # * Check for cycling limits
            g.RpUpc[g.r, g.p, g.tsl, "N"].where[g.RpUpr[g.r, g.p, "N"]] = sparse(
                Sum(
                    g.RpUps[g.PrcTsl[g.r, g.p, g.tslvl], g.lA],
                    g.Rlup[g.r, g.tslvl, g.tsl],
                )
            )
            g.RpUpc[g.PrcTsl[g.Rp, g.tsl], g.Bdneq[g.bd]].where[
                g.RpUps[g.Rp, g.tsl, "UP"]
            ] = sparse(g.RpUpr[g.Rp, g.bd])

        g = self.tc
        project(source=g.act_cstrmp, target=g.RpUpr)

    def equation_capload(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        capon: Expression | Condition,
        arg1: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc

        eq_capload = g.get_equation(f"{eq}_CAPLOAD")
        var_act = g.get_variable(f"{var}_ACT")
        var_ups = g.get_variable(f"{var}_UPS")

        eq_capload[g.RtpVintyr[*r_v_t, g.p], g.s, g.Bdneq[g.bd], *swt].where[
            g.Afups[g.r, g.t, g.p, g.s]
        ] = (
            var_act[g.r, g.v, g.t, g.p, g.s, *sow] * g.bdsig[g.bd]
            >= var_ups[g.r, g.v, g.t, g.p, g.s, "FX", *sow].where[
                g.RtpPl[g.r, g.v, g.p] & g.Bdlox[g.bd]
            ]
            + (capon + macro.upscaps.render_GP())
            * Min(
                macro.coef_af_mx.coef_af_GP(arg1, g.r, g.v, g.t, g.p, g.s, "UP")
                * g.bdsig[g.bd],
                Sum(
                    g.TsAnn[g.s, g.ts].where[(~(g.RtpPl[g.r, g.v, g.p]))],
                    g.act_ups[g.r, g.v, g.p, g.ts, "FX"],
                ).where[g.Bdlox[g.bd]],
            )
            * g.prc_capact[g.r, g.p]
            * g.g_yrfr[g.r, g.s]
        )

    def equation_acttramp(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        tmp: tuple[Expression, Expression | ImplicitSet],
        rts: SET_OR_ALIAS,
    ) -> None:
        g = self.tc
        tmp_condtion, tmp_expr = tmp

        eq_actramp = g.get_equation(f"{eq}_ACTRAMP")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_ACT = g.get_variable(f"{var}_ACT")

        eq_actramp[g.RtpVintyr[*r_v_t, g.p], rts, g.Bdneq[g.bd], *swt].where[
            (
                Sum(
                    g.TsAnn[g.s, g.ts].where[g.act_ups[g.r, g.v, g.p, g.ts, g.bd]], 1.0
                ).where[g.PrcTs[g.r, g.p, g.s] & g.RpUpl[g.r, g.p, g.bd]]
            )
        ] = (
            # * max fraction of capacity
            Sum(
                g.RsPrev[g.r, g.s, g.ts].where[g.PrcTs[g.r, g.p, g.ts]],
                g.prc_capact[g.r, g.p]
                * Sum(g.TsAnn[g.s, g.sl], g.act_ups[g.r, g.v, g.p, g.sl, g.bd])
                * (
                    # TODO need to catch which mx is allowed here
                    mx.where[tmp_condtion]  # type: ignore
                    + tmp_expr
                    + (
                        VAR_UPS[g.r, g.v, g.t, g.p, g.s, "N", *sow]
                        - VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "N", *sow]
                    ).where[g.Bdlox[g.bd] & g.RpsUps[g.r, g.p, g.s]]
                )
                # * dynamic ramp limits
                + g.rs_stgprd[g.r, g.s]
                * 2.0
                / (g.g_yrfr[g.r, g.s] + g.g_yrfr[g.r, g.ts])
                / 8760.0
                * (
                    VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow] / g.g_yrfr[g.r, g.s]
                    - VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow] / g.g_yrfr[g.r, g.ts]
                    + (
                        (
                            VAR_UPS[g.r, g.v, g.t, g.p, g.s, "N", *sow]
                            - VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "N", *sow]
                        )
                        * g.prc_capact[g.r, g.p]
                        * g.act_minld[g.r, g.v, g.p]
                    ).where[g.RpsUps[g.r, g.p, g.s]]
                )
                * g.bdsig[g.bd],
            )
            >= 0.0
        )

    def equation_actups(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        tmp: tuple[Expression, Expression | ImplicitSet],
        rts: SET_OR_ALIAS,
    ) -> None:
        g = self.tc
        tmp_condtion, tmp_expr = tmp

        eqe_actups = g.get_equation(f"{eq}E_ACTUPS")
        eql_actups = g.get_equation(f"{eq}L_ACTUPS")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_UDP = g.get_variable(f"{var}_UDP")

        eqe_actups[g.RtpVintyr[*r_v_t, g.p], g.tsl, g.lA[g.BndType], rts, *swt].where[
            (g.TsGroup[g.r, g.tsl, g.s].where[g.RpUps[g.r, g.p, g.tsl, g.lA]])
        ] = (
            # * start-up/shut-down capacity
            Sum(
                g.RsPrev[g.r, g.s, g.ts],
                VAR_UPS[g.r, g.v, g.t, g.p, g.s, "N", *sow]
                - VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "N", *sow]
                - Sum(
                    g.bd,
                    VAR_UPS[g.r, g.v, g.t, g.p, g.s, g.bd, *sow] * g.bdsig[g.bd],
                ),
            ).where[g.stoa[g.s]]
            + Sum(
                g.Annual[g.s].where[g.RpPl[g.r, g.p, "N"]],
                VAR_UPS[g.r, g.v, g.t, g.p, g.s, g.lA, *sow]
                - Sum(
                    g.PrcTs[g.r, g.p, g.ts],
                    VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "FX", *sow],
                ),
            )
        ).where[(g.bdsig[g.lA] < 0.0)] + Sum(
            g.Bdlox[g.bd[g.lA]],
            # TODO need to catch which mx is allowed here
            (
                mx.where[tmp_condtion]  # type: ignore[union-attr]
                + tmp_expr
            )
            - VAR_UDP[g.r, g.v, g.t, g.p, g.s, "FX", *sow]
            - VAR_UPS[g.r, g.v, g.t, g.p, g.s, "FX", *sow].where[
                g.RpUpl[g.r, g.p, "FX"]
            ],
        ) == 0.0
        # *-----------------------------------------------------------------------
        eql_actups[g.RtpVintyr[*r_v_t, g.p], g.tsl, g.Lnx[g.lA], rts, *swt].where[
            (g.TsGroup[g.r, g.tsl, g.s].where[g.RpUps[g.r, g.p, g.tsl, g.lA]])
        ] = (
            # * balance at higher level
            VAR_UPS[g.r, g.v, g.t, g.p, g.s, g.lA, *sow]
            - Sum(
                g.RsBelow1[g.r, g.ts, g.s],
                VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "FX", *sow],
            )
        ).where[g.ips[g.lA]] + (
            VAR_UPS[g.r, g.v, g.t, g.p, g.s, g.lA, *sow]
            - Sum(
                g.RsBelow1[g.r, g.s, g.ts],
                VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "UP", *sow],
            )
        ).where[g.bd[g.lA]] <= 0.0

    def equation_actupc(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        capon: Expression | Condition,
        rts: SET_OR_ALIAS,
    ) -> None:
        g = self.tc
        eql_actupc = g.get_equation(f"{eq}L_ACTUPC")
        VAR_UPS = g.get_variable(f"{var}_UPS")

        eql_actupc[g.RtpVintyr[*r_v_t, g.p], g.tsl, g.lA, rts, *swt].where[
            (g.TsGroup[g.r, g.tsl, g.s].where[g.RpUpc[g.r, g.p, g.tsl, g.lA]])
        ] = (
            # * max number of cycles
            Sum(
                g.RsBelow1[g.r, g.s, g.sl],
                VAR_UPS[g.r, g.v, g.t, g.p, g.sl, "UP", *sow],
            )
            - (capon + macro.upscaps.render_GP()) * g.act_time[g.r, g.t, g.p, g.lA]
        ).where[g.ips[g.lA]] + Sum(
            #  *min UP/LO hours
            g.bd[g.lA],
            Sum(
                Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                    (
                        g.rs_modus[g.r, g.s, g.Js, g.sl]
                        < g.act_time[g.r, g.t, g.p, g.lA] / 8760.0
                    )
                ],
                VAR_UPS[g.r, g.v, g.t, g.p, g.sl, g.lA, *sow],
            )
            - Sum(
                g.RsUp[g.r, g.s, g.j, g.ts],
                VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "FX", *sow],
            ).where[g.Bdupx[g.bd]]
            - VAR_UPS[g.r, g.v, g.t, g.p, g.s, "N", *sow] * g.bdsig[g.lA],
        ) <= 0.0

    def equation_actpl(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        tmp: tuple[Expression, Expression | ImplicitSet],
        rts: SET_OR_ALIAS,
    ) -> None:
        g = self.tc
        tmp_condtion, tmp_expr = tmp

        eq_actpl = g.get_equation(f"{eq}_ACTPL")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_UPT = g.get_variable(f"{var}_UPT")

        eq_actpl[g.RtpVintyr[*r_v_t, g.p], rts, *swt].where[
            (g.PrcTs[g.r, g.p, g.s].where[g.RpPl[g.r, g.p, "N"]])
        ] = (
            # * partial loads
            VAR_UPS[g.r, g.v, g.t, g.p, g.s, "FX", *sow]
            >= (
                # TODO need to catch which mx is allowed here
                mx.where[tmp_condtion]  # type: ignore[union-attr]
                + tmp_expr
                * g.prc_capact[g.r, g.p]
                * g.g_yrfr[g.r, g.s]
                * (
                    g.act_lospl[g.r, g.v, g.p, "UP"]
                    + g.act_lospl[g.r, g.v, g.p, "LO"]
                    * (1.0 - g.act_lospl[g.r, g.v, g.p, "UP"])
                )
                - VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow]
            )
            / (
                g.act_lospl[g.r, g.v, g.p, "UP"]
                * (1.0 / g.act_lospl[g.r, g.v, g.p, "LO"] - 1.0)
            )
            + Sum(
                Domain(g.RpUpt[g.r, g.p, g.upt, g.bd], g.PrcTsl[g.r, g.p, g.tsl]).where[
                    g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, "IN", "N"]
                ],
                Sum(
                    Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                        (
                            mod(
                                (g.rs_hr[g.r, g.s] - g.rs_hr[g.r, g.sl]) * g.bdsig[g.bd]
                                + g.g_yrfr[g.r, g.sl] / g.rs_stgprd[g.r, g.s] / 2.0
                                + 2.0 / g.g_cycle[g.tsl],
                                1.0 / g.g_cycle[g.tsl],
                            )
                            < g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd]
                            / 8760.0
                            * (1.001)
                        )
                    ],
                    Min(
                        1.0,
                        mod(
                            (g.rs_hr[g.r, g.s] - g.rs_hr[g.r, g.sl]) * g.bdsig[g.bd]
                            + (g.g_yrfr[g.r, g.sl] - g.g_yrfr[g.r, g.s])
                            / 2.0
                            / g.rs_stgprd[g.r, g.s]
                            + 2.0 / g.g_cycle[g.tsl],
                            1.0 / g.g_cycle[g.tsl],
                        )
                        / (g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0),
                    )
                    * (1.0 - diag(g.s, g.sl))
                    * g.dp_psud[g.r, g.v, g.p, g.upt, g.bd]
                    * (
                        VAR_UPT[g.r, g.v, g.t, g.p, g.sl, g.upt, *sow].where[
                            g.Bdupx[g.bd]
                        ]
                        + VAR_UPS[g.r, g.v, g.t, g.p, g.sl, g.bd, *sow].where[
                            g.Bdlox[g.bd]
                        ]
                    ),
                )
                * g.prc_capact[g.r, g.p]
                * g.g_yrfr[g.r, g.s]
                * g.act_minld[g.r, g.v, g.p],
            ).where[g.DpLosd[g.r, g.v, g.p]]
        )

    def equation_actrmpc(
        self: EqactupsVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
    ) -> None:
        g = self.tc
        eq_actrmpc = g.get_equation(f"{eq}_ACTRMPC")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_UDP = g.get_variable(f"{var}_UDP")

        eq_actrmpc[g.RtpVintyr[*r_v_t, g.p], g.ts[g.s], *swt].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.RpStd[g.r, g.p] & Sum(g.RpUpr[g.r, g.p, g.bd], 1.0)
                ]
            )
        ] = (
            # * ramping costs
            VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow] / g.g_yrfr[g.r, g.ts]
            - VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow] / g.g_yrfr[g.r, g.s]
        ) / g.prc_capact[g.r, g.p] == Sum(
            g.Bdneq[g.bd],
            VAR_UDP[g.r, g.v, g.t, g.p, g.s, g.bd, *sow] * g.bdsig[g.bd],
        ) - g.act_minld[g.r, g.v, g.p] * (
            VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "N", *sow]
            - VAR_UPS[g.r, g.v, g.t, g.p, g.s, "N", *sow]
        ).where[g.RpsUps[g.r, g.p, g.s]]

    def equation_stgccl(
        self: EqactupsVda,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
        swtx: Number | ImplicitSet,
    ) -> None:
        g = self.tc
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")

        g.eql_stgccl[g.RtpVintyr[*r_v_t, g.p], *swx].where[
            (
                swtx.where[
                    Sum(
                        g.RpsStg[g.r, g.p, g.s].where[g.coef_afups[g.r, g.v, g.p, g.s]],
                        1.0,
                    )
                    & g.stg_maxcyc[g.r, g.v, g.p]
                    & g.RpStg[g.r, g.p]
                ]
            )
        ] = (
            # * Storage cycling penalty
            # TODO mx?
            mx + VAR_UPS[g.r, g.v, g.t, g.p, "ANNUAL", "UP", *sow]  # type: ignore
        ) / exp(g.prc_sc[g.r, g.p]) * Smax(
            g.RpsStg[g.r, g.p, g.s], g.coef_afups[g.r, g.v, g.p, g.s]
        ) * g.prc_capact[g.r, g.p] >= Sum(
            Domain(
                g.Top[g.RpcStg[g.r, g.p, g.c], "OUT"], g.RpcsVar[g.r, g.p, g.c, g.s]
            ),
            VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.s, *sow]
            / g.prc_actflo[g.r, g.v, g.p, g.c],
        ) * g.ncap_tlife[g.r, g.v, g.p] / g.stg_maxcyc[g.r, g.v, g.p]

    def equation_slsift(
        self: EqactupsVda,
        eq: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        pgprim: str,
        rts: SET_OR_ALIAS,
    ) -> None:
        g = self.tc
        eq_slsift = g.get_equation(f"{eq}_SLSIFT")
        VAR_UPS = g.get_variable(f"{var}_UPS")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
        # * Load Shifting
        eq_slsift[g.Rtp[*r_t, g.p], g.Com, rts, g.Lnx, g.lA, *swt].where[
            (
                (
                    g.PrcTs[g.r, g.p, g.s].where[g.act_time[g.Rtp, g.lA]]
                    + g.bd[g.Lnx].where[g.Lnx[g.lA]]
                ).where[g.RpsPrcts[g.r, g.p, g.s] & g.RpcLs[g.r, g.p, g.Com]]
            )
        ] = (
            Sum(
                g.RtpVintyr[g.r, g.v, g.t, g.p],
                # * Limit net and gross sifting flows
                Sum(
                    g.ips[g.lA].where[
                        (
                            g.PrcTs[g.r, g.p, g.s]
                            + Number(1).where[g.stg_sift[g.Rtp, pgprim, g.s]]
                            + g.Annual[g.s].where[g.Actcg[g.Com]]
                        )
                    ],
                    Sum(
                        g.PrcTs[g.r, g.p, g.ts].where[g.RsBelow1[g.r, g.s, g.ts]],
                        VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow],
                    ).where[g.stg_sift[g.Rtp, pgprim, g.s]]
                    + Sum(
                        Domain(
                            g.Top[g.RpcStg[g.r, g.p, g.c], "OUT"],
                            g.RpcsVar[g.r, g.p, g.c, g.ts],
                        ),
                        VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.ts, *sow],
                    ).where[g.Annual[g.s] & g.Actcg[g.Com]]
                    + (
                        VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.s, *sow]
                        + VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow]
                    ).where[g.PrcTs[g.r, g.p, g.s]]
                    + VAR_SOUT[g.r, g.t, g.t, g.p, pgprim, g.s, *sow]
                    - Sum(
                        Domain(
                            g.Top[g.RpcStg[g.r, g.p, g.c], "OUT"],
                            g.RtcsVarc[g.Rtc[g.r, g.t, g.c], g.ts],
                        ).where[g.rs_fr[g.r, g.s, g.ts]],
                        (
                            g.stg_sift[g.Rtp, g.c, g.ts].where[
                                (
                                    g.PrcTs[g.r, g.p, g.s]
                                    + g.Annual[g.s].where[g.Actcg[g.Com]]
                                )
                            ]
                            + g.stg_sift[g.Rtp, pgprim, g.s]
                        )
                        * VAR_COMPRD[g.r, g.t, g.c, g.ts, *sow]
                        / g.com_ie[g.Rtc, g.ts]
                        * g.rs_fr[g.r, g.s, g.ts]
                        * (
                            1.0
                            + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.c, g.s, g.ts, sow)
                        ),
                    ),
                )
                # * Get net sifting, force zero shifting at seasonal level
                - Sum(
                    g.bd[g.lA].where[g.Lnx[g.lA]],
                    (
                        Sum(
                            Domain(
                                g.Top[g.RpcStg[g.r, g.p, g.c], "OUT"],
                                g.RpcsVar[g.r, g.p, g.c, g.ts],
                            ).where[g.rs_fr[g.r, g.s, g.ts]],
                            VAR_SOUT[g.r, g.v, g.t, g.p, g.c, g.ts, *sow]
                            * g.rs_fr[g.r, g.s, g.ts]
                            * (
                                1.0
                                + macro.rtcs_fr.rtcs_fr_GP(
                                    g.r, g.t, g.c, g.s, g.ts, sow
                                )
                            ),
                        )
                        - Sum(
                            g.Top[g.RpcStg[g.r, g.p, g.c], "IN"],
                            VAR_SIN[g.r, g.v, g.t, g.p, g.c, g.s, *sow],
                        )
                        - (
                            VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow]
                            - VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.s, *sow]
                        )
                    ).where[g.PrcTs[g.r, g.p, g.s]]
                    + Sum(
                        g.PrcTs[g.r, g.p, g.ts].where[g.RsBelow1[g.r, g.s, g.ts]],
                        VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow]
                        - VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow],
                    ).where[(Sum(g.lim.where[g.act_time[g.Rtp, g.lim]], 1.0) == 0.0)],
                )
                # * Asymmetric advance or delay
                + Sum(
                    g.Bdneq[g.bd[g.lA]].where[g.act_time[g.Rtp, "LO"]],
                    macro.var_sift.render_GP(g.v, g.s, g.lA)
                    + macro.var_sift.render_GP("0", g.s, g.lA)
                    - Sum(
                        Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                            (
                                mod(
                                    (
                                        g.rs_hr[g.r, g.s]
                                        - g.rs_hr[g.r, g.sl]
                                        + g.g_yrfr[g.r, g.s]
                                        / g.rs_stgprd[g.r, g.s]
                                        / 9.0
                                    )
                                    * g.bdsig[g.lA]
                                    + 1.0 / g.js_ccl[g.r, g.Js],
                                    1.0 / g.js_ccl[g.r, g.Js],
                                )
                                < g.act_time[g.Rtp, g.lA] / 8760.0
                            )
                        ],
                        VAR_UPS[g.r, g.v, g.t, g.p, g.sl, g.lA, *sow],
                    ),
                ),
            ).where[g.bd[g.Lnx]]
            == Sum(
                g.RtpVintyr[g.r, g.v, g.t, g.p],
                # * Balance for sifting (LO=advance, UP=delay)
                Sum(
                    g.ts[g.s.lag(g.rs_stg[g.r, g.s], "circular")],
                    Sum(
                        g.Bdneq[g.bd],
                        (
                            macro.var_sift.render_GP(g.v, g.ts, g.bd)
                            - macro.var_sift.render_GP(g.v, g.s, g.bd)
                        )
                        * g.bdsig[g.bd],
                    )
                    + VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.s, *sow]
                    - VAR_ACT[g.r, g.v, g.t, g.p, g.s, *sow],
                ).where[(g.bdsig[g.lA] < 0.0)]
                + (
                    Sum(g.Bdneq[g.bd], VAR_UPS[g.r, g.v, g.t, g.p, g.s, g.bd, *sow])
                    - VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.s, *sow]
                ).where[(g.bdsig[g.lA] > 0.0)]
                # * Limit advance and delay or balancing time window
                + Sum(
                    g.Lastll.where[g.Lnx[g.lA]],
                    Sum(
                        g.lim.where[((g.ips[g.lA]) ^ (g.bd[g.lim]))],
                        macro.var_sift.render_GP(g.v, g.s, g.lim),
                    )
                    + Sum(
                        Domain(
                            g.RsUp[g.r, g.s, g.Js],
                            g.RjSl[
                                g.r,
                                g.Js,
                                g.ts[g.sl.lag(g.rs_stg[g.r, g.sl], "circular")],
                            ],
                        ).where[
                            (
                                mod(
                                    g.rs_hr[g.r, g.s]
                                    - g.rs_hr[g.r, g.sl]
                                    + g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 9.0
                                    + 1.0 / g.js_ccl[g.r, g.Js],
                                    1.0 / g.js_ccl[g.r, g.Js],
                                )
                                < g.act_time[g.Rtp, g.lA] / 8760.0
                            )
                        ],
                        (
                            VAR_ACT[g.r, g.v, g.t, g.p, g.sl, *sow].where[g.ips[g.lA]]
                            - VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.sl, *sow]
                            - (
                                macro.var_sift.render_GP(g.v, g.sl, "UP")
                                - macro.var_sift.render_GP(g.v, g.ts, "UP")
                            ).where[g.bd[g.lA]]
                        ),
                    ),
                ),
            ).where[g.ips[g.Lnx]]
        )
