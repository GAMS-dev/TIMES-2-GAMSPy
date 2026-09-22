# prepret_dsc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREPRET.dsc oversees pre-processing for retirements
# *=============================================================================*
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, get_args

from gamspy import (
    Container,
    Domain,
    Else,
    Equation,
    Expression,
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
    Variable,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, floor, map_value, mod, project, same_as

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.prepparm_gms import PrepparmGms, PrepparmGmsConfig
from core.utils import wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class PrepretDscConfig:
    # NOTE: arg1 includes its own values and everything from arg2 and arg3 to satisfy type-checker
    # This is due to the shift operation on argument values in comp_prep()
    arg1: Literal[
        "PREP", "DECL", "EQOBJ", "OBJFIX", "OBSALV", "", "PRC_RCAP", "RCAP_BND"
    ]
    # arg2 includes its own values, PLUS arg3
    arg2: Literal["PRC_RCAP", "", "RCAP_BND"] = ""
    arg3: Literal["RCAP_BND", ""] = ""


class PrepretDsc(GamsClass):
    """Translation unit for prepret.dsc."""

    # Instance attributes
    module_name: str = "prepret_dsc"
    gams_source: str = "prepret.dsc"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: PrepretDscConfig
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules: dict[str, GamsClass] = {}
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("mip", f"{self.env.solmip}==YES")
        cc = self.config

        arg_upper = cc.arg1.upper() if cc.arg1 else ""
        if arg_upper == "PREP":
            self.comp_prep()
        elif arg_upper == "DECL":
            self.comp_decl()
        elif arg_upper == "EQOBJ":
            self.comp_eqobj()
        elif arg_upper == "OBJFIX":
            raise NotImplementedError("Need to call as function")
            # return objfix(capwd=self.env.capwd, vart=self.env.vart, sws=self.env.sws)
        elif arg_upper == "OBSALV":
            objsalv(
                var=self.env.var, varv=self.env.varv, sws=self.env.sws, sow=self.env.sow
            )
        else:
            allowed = ", ".join(
                repr(v)
                for v in get_args(get_args(PrepretDscConfig.__annotations__["arg1"])[0])
            )
            raise ValueError(
                f"Unknown argument '{cc.arg1}'. Expected one of: {allowed}"
            )

    def comp_prep(self: PrepretDsc) -> None:
        g = self.tc
        cc = self.config
        m = g.container

        r, p, lA, v = g.r, g.p, g.lA, g.v

        self.env.set_scoped("tst", cc.arg2)
        if self.tc.defined("PRC_REFIT"):
            try:
                arg2_set = g.get_set(cc.arg2)
            except KeyError as e:
                error_message = str(e.args[0])
                if f"`{cc.arg2}` does not exist in the Container." in error_message:
                    arg2_set = Set(m, name=cc.arg2)
                    g.set_set(name=cc.arg2, set=arg2_set, domain=False)
                else:
                    raise
            g.register_assignment(arg2_set)

            self.create_parameter_from_arg3(g, m)

        if self.env.retire.upper() == "NO":
            self.tc.add_gams_code(module=self, phase="init", code=rf"$KILL {cc.arg2}")

        if self.tc.defined(cc.arg2.upper()):
            self.create_parameter_from_arg3(g, m)
            self.tc.enqueue(self.exec_prep1, sym2=cc.arg2, sym3=cc.arg3)

        if self.env.retire.upper() == "YES":
            cc.arg1 = cc.arg2
            cc.arg2 = cc.arg3
            cc.arg3 = ""

        self.tc.enqueue(self.exec_prep2)

        if self.tc.defined(cc.arg2.upper()):
            # Declarations
            g.Vnret = Set(m, name="VNRET", domain=[g.year, g.ll])
            g.rp_rtf = Parameter(m, name="RP_RTF", domain=[g.r, g.p])

            # Interpolate RCAP_BND
            if self.env.tst == cc.arg1:
                self.tc.enqueue(self.exec_prep3, tst=self.env.tst, arg2=cc.arg2)
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    FillparmGmsConfig(
                        arg1=g.rcap_blk,
                        arg2=(g.r,),
                        arg3=(g.p,),
                        arg4=("",) * 5,
                        arg5=g.v,
                        arg6=g.Rtp[g.r, g.v, g.p],
                        arg7=Number(0),
                    ),
                )
            )
            self.include(
                PrepparmGms(
                    self.tc,
                    self.env,
                    config=PrepparmGmsConfig(
                        arg1="RCAP_BND",
                        arg2=(r,),
                        arg3=(p, lA),
                        arg4=("", "", ""),
                        arg5=v,
                        arg6=g.Rtp[r, v, p],
                        arg7=1,
                    ),
                )
            )
            if self.tc.defined("NCAP_OLIFE"):
                self.include(
                    FillparmGms(
                        self.tc,
                        self.env,
                        FillparmGmsConfig(
                            arg1=g.ncap_olife,
                            arg2=(g.r,),
                            arg3=(g.p,),
                            arg4=("",) * 5,
                            arg5=g.v,
                            arg6=g.Rtp[g.r, g.v, g.p],
                            arg7=Number(0),
                        ),
                    )
                )
                self.tc.enqueue(self.exec_prep4)
            # Preprocess refits
            self.tc.enqueue(self.exec_prep5)
            # Activate MIP solution if requested
            if self.env.dsc.upper() == "YES":
                self.env.set_global("solmip", self.env.retire)
            if self.env.retire.upper() == "MIP":
                self.env.set_global("solmip", "YES")

    def create_parameter_from_arg3(self, g: TimesModelClass, m: Container) -> None:
        cc = self.config
        param = g.get_parameter(name=cc.arg3)
        if param is None:
            param = Parameter(m, name=cc.arg3)
            g.set_parameter(name=cc.arg3, parameter=param)
        g.register_assignment(param)

    def exec_prep1(self: PrepretDsc, sym2: str, sym3: str) -> None:
        g = self.tc

        sym2_set: Set = g.get_set(name=sym2)
        sym3_param: Parameter = g.get_parameter(name=sym3)

        sym3_param[g.r, "0", g.p, "N"].where[
            (sym3_param[g.r, "0", g.p, "N"] == 0.0) & sym2_set[g.r, g.p]
        ] = sym2_set[g.r, g.p]

    def exec_prep2(self: PrepretDsc) -> None:
        g = self.tc
        g.prc_refit[g.Rp, g.p].where[False] = False  # type: ignore[index]

    def exec_prep3(self: PrepretDsc, tst: str, arg2: str) -> None:
        g = self.tc
        set_tst: Set = g.get_set(name=tst)
        set_arg2: Set = g.get_set(name=arg2)
        project(set_arg2, set_tst)

    def exec_prep4(self: PrepretDsc) -> None:
        g = self.tc
        project(source=g.ncap_elife, target=g.PrcCap)
        g.ncap_elife[g.r, g.v, g.p].where[(~(g.PrcCap[g.r, g.p]))] = sparse(
            g.ncap_olife[g.r, g.v, g.p]
        )
        g.PrcCap[g.r, g.p] = 0.0  # type: ignore

    def exec_prep5(self: PrepretDsc) -> None:
        g = self.tc

        with Loop(
            Domain(g.Rp[g.r, g.prc], g.p).where[
                (g.Rp[g.r, g.p].where[g.prc_refit[g.Rp, g.p]])
            ]
        ):
            g.ncap_iled[g.Rtp[g.r, g.v, g.p]] = -abs(g.ncap_iled[g.Rtp])
            g.PrcRcap[g.Rp] = True
            g.Trackp[g.r, g.p].where[(g.prc_refit[g.Rp, g.p] < 0.0)] = True
        g.RtpVarp[g.Rtp[g.r, g.t, g.p]] = sparse(g.PrcRcap[g.r, g.p])
        g.PrcRcap[g.Trackp] = True
        g.Trackp.setRecords(None)

    def comp_decl(self: PrepretDsc) -> None:
        g = self.tc
        m = g.container

        if self.env.mip == "YES==YES":
            var = Variable(
                m,
                name=f"{self.env.var}_DRCAP",
                type="integer",
                domain=[g.r, g.allyear, g.ll, g.p, *self.env.swd_GP, g.j],
            )
        else:
            var = Variable(
                m,
                name=f"{self.env.var}_DRCAP",
                domain=[g.r, g.allyear, g.ll, g.p, *self.env.swd_GP, g.j],
            )

        g.set_variable(name=f"{self.env.var}_DRCAP", var=var)
        g.set_equation(
            name=f"{self.env.eq}_DSCRET",
            eq=Equation(
                m,
                name=f"{self.env.eq}_DSCRET",
                domain=[g.r, g.allyear, g.allyear, g.p, *self.env.swtd_GP],
            ),
        )

        self.tc.register_assignment(self.tc.rcap_bnd)
        self.tc.register_assignment(self.tc.Vnret)
        self.tc.enqueue(self.exec_decl1, var=self.env.var)

    def exec_decl1(self: PrepretDsc, var: str) -> None:
        g = self.tc
        sow_GP = self.env.sow_GP

        # * Maps for refit vintages & types
        g.PrcRcap[g.PrcRcap[g.Rp]] = g.PrcCap[g.Rp]
        with Loop(Domain(g.PrcRcap[g.r, g.prc])):
            g.f[...] = 0.0
            g.my_f[...] = 0.0
            g.cnt[...] = SpecialValues.EPS
            with Loop(g.p.where[g.prc_refit[g.r, g.prc, g.p]]):
                g.z[...] = g.prc_refit[g.r, g.prc, g.p]
                g.cnt[...].where[g.cnt] = g.cnt + 1.0
                with If(abs(g.z) > 2.0):
                    g.f[...] = g.f + 1.0
                with If(mod(g.z, 2.0) == 0.0):
                    g.my_f[...].where[(abs(g.z) - 4.0)] = 3.0
                with If(g.z < 0.0):
                    g.RtpTt[g.r, g.t, g.tt, g.prc].where[
                        g.coef_cpt[g.r, g.t, g.tt, g.p]
                    ] = True
                with Else():  # type: ignore
                    g.RtpTt[g.r, g.t, g.t, g.prc].where[g.Rtp[g.r, g.t, g.p]] = True
                    g.cnt[...] = 0.0
            with If(g.cnt):
                g.z[...] = (-1.0 + Number(2.0).where[(g.f == g.cnt)]) * Max(1.0, g.my_f)
            with Else():  # type: ignore
                g.z[...] = -2.0
            with If(~(map_value(g.cnt))):
                g.rp_rtf[g.r, g.prc] = g.z
            with If(g.f):
                filter = g.prc_refit[g.r, g.prc, g.p]
                g.rcap_bnd[g.Rtp[g.r, g.t, g.prc], "UP"].where[
                    (
                        ~(
                            Sum(
                                g.p.where[filter],
                                g.Rtp[g.r, g.t, g.p].where[abs(filter) > 2.0],  # type: ignore
                            )
                        )
                    )
                ] = SpecialValues.EPS
        # * Force obj type 2a/2b
        g.Vnret[g.Vnt[g.v, g.t]].where[(~(same_as(g.v, g.t)))] = True
        g.rvprl[g.Rtp[g.r, g.v, g.p]].where[g.PrcRcap[g.r, g.p]] = Max(
            0.0,
            Smax(g.RtpCptyr[g.r, g.Vnret[g.v, g.t], g.p], g.yearval[g.t])
            - g.yearval[g.v],
        )
        g.Rvp[g.Rtp] = sparse(g.rvprl[g.Rtp])
        g.ncap_iled[g.Rvp] = g.ncap_iled[g.Rvp] + SpecialValues.EPS
        # * Set bounds for continuous retirements
        g.rcap_bnd[g.r, g.t, g.p, g.Bdneq] = sparse(g.rcap_bnd[g.r, g.t, g.p, "FX"])
        g.pastsum[g.Rvp[g.r, g.v, g.p]].where[g.rcap_bnd[g.Rvp, "N"]] = (
            g.b[g.v] + g.ncap_iled[g.Rvp] + abs(g.rcap_bnd[g.Rvp, "N"])
        )
        g.pastsum[g.Rvp].where[
            ((g.rcap_bnd[g.Rvp, "N"] < 0.0) + map_value(g.rcap_blk[g.Rvp]))
        ] = Max(1.0, abs(g.pastsum[g.Rvp]))
        var_rcap = g.get_variable(name=f"{var}_RCAP")
        var_scap = g.get_variable(name=f"{var}_SCAP")
        with Loop(g.tt[g.t.lag(1, "circular")]):
            g.z[...] = Ord(g.t) - 1.0
            var_rcap.lo[g.RtpCptyr[g.r, g.Vnret[g.v, g.t], g.p], *sow_GP].where[
                g.Rvp[g.r, g.v, g.p]
            ] = g.rcap_bnd[g.r, g.t, g.p, "LO"].where[
                (~(map_value(g.rcap_blk[g.r, g.v, g.p])))
            ] + Min(
                0.0,
                g.rtforc[g.r, g.v, g.t, g.p] - g.rtforc[g.r, g.v, g.tt, g.p].where[g.z],
            )
            var_rcap.up[g.RtpCptyr[g.r, g.Vnret[g.v, g.t], g.p], *sow_GP].where[
                g.rcap_bnd[g.r, g.t, g.p, "UP"]
            ] = Min(
                Smin(g.Pastmile[g.v], g.ncap_pasti[g.r, g.v, g.p]),
                g.rcap_bnd[g.r, g.t, g.p, "UP"]
                + Max(
                    0.0,
                    g.rtforc[g.r, g.v, g.t, g.p]
                    - g.rtforc[g.r, g.v, g.tt, g.p].where[g.z],
                ),
            )
        var_scap.lo[g.RtpCptyr[g.r, g.Vnret[g.v, g.t], g.p], *sow_GP].where[
            g.Rvp[g.r, g.v, g.p]
        ] = Max(g.rcap_bnd[g.r, g.t, g.p, "LO"], g.rtforc[g.r, g.v, g.t, g.p])
        var_scap.up[g.RtpCptyr[g.r, g.Pastmile[g.v], g.t, g.p], *sow_GP].where[
            g.Rvp[g.r, g.v, g.p]
        ] = Max(g.rtforc[g.r, g.v, g.t, g.p], g.ncap_pasti[g.r, g.v, g.p])
        dom = (g.r, g.v, g.t, g.p, *sow_GP)
        with Loop(g.Rvp[g.r, g.v, g.p]):
            g.z[...] = 1.0
            with Loop(g.RtpCptyr[g.r, g.Vnret[g.v, g.t], g.p].where[g.z]):
                g.z[...] = 0.0
                var_scap.up[*dom] = Min(
                    var_rcap.up[*dom],
                    var_scap.up[*dom],
                )
        var_scap.fx[g.RtpCptyr[g.r, g.v, g.t, g.p], *sow_GP].where[
            (
                (
                    (g.m[g.t] < abs(g.pastsum[g.r, g.v, g.p]))
                    + ((g.m[g.t] - g.lead[g.t]) / g.pastsum[g.r, g.v, g.p] >= 1.0)
                ).where[g.pastsum[g.r, g.v, g.p]]
            )
        ] = g.rtforc[g.r, g.v, g.t, g.p]
        # * Force refits = retirements on request
        g.prc_ymax[g.PrcRcap[g.Rp]] = Min(
            0.0,
            Sum(
                g.p.where[g.prc_refit[g.Rp, g.p]],
                Max(SpecialValues.EPS, 3.0 - abs(g.prc_refit[g.Rp, g.p])),
            ),
        )
        g.rvprl[g.r, "0", g.p] = sparse(g.prc_ymax[g.r, g.p])
        var_rcap.up[
            g.RtpTt[g.r, g.t[g.tt.lead(1, "circular")], g.t, g.p], *sow_GP
        ].where[((g.rp_rtf[g.r, g.p] < 3.0).where[g.prc_ymax[g.r, g.p]])] = Max(
            0.0,
            Sum(
                Domain(g.Rtp[g.r, g.PyrS[g.v], g.p]),
                g.rtforc[g.r, g.v, g.t, g.p] - g.rtforc[g.r, g.v, g.tt, g.p],
            ).where[(g.Vnt[g.tt, g.t]) & (mod(g.rp_rtf[g.r, g.p], 2.0) == 0.0)],
        )
        g.pastsum.setRecords(None)
        g.Rvp.setRecords(None)

    def comp_eqobj(self: PrepretDsc) -> None:
        g = self.tc
        r, t, p, v, Modlyear = g.r, g.t, g.p, g.v, g.Modlyear

        vart_id, vart_set = self.env.vart_GP
        sws = self.env.sws_GP
        VART_SCAP = g.get_variable(name=f"{vart_id}_SCAP")

        self.env.set_global(
            "rcapsub",
            rf"-SUM(VNRET(V,T),{macro.VAR_SCAP(self.env.vart, 'R', 'V', 'T', 'P', self.env.sws)})$PRC_RCAP(R,P)",
        )

        shared_vart_scap = VART_SCAP[r, v, t, p, *sws]
        VART_SCAP_expr = (
            shared_vart_scap if vart_set is None else Sum(vart_set, shared_vart_scap)
        )
        self.env.set_global(
            "rcapsub_GP",
            -Sum(g.Vnret[v, t], VART_SCAP_expr).where[g.PrcRcap[r, p]],
        )
        self.env.set_global(
            "rcapsbm",
            rf"-SUM(VNRET(MODLYEAR,T),{macro.VAR_SCAP(self.env.vart, 'R', 'MODLYEAR', 'T', 'P', self.env.sws)})$PRC_RCAP(R,P)",
        )

        shared_vart_scap = VART_SCAP[r, Modlyear, t, p, *sws]
        VART_SCAP_expr = (
            shared_vart_scap if vart_set is None else Sum(vart_set, shared_vart_scap)
        )
        self.env.set_global(
            "rcapsbm_GP",
            -Sum(g.Vnret[Modlyear, t], VART_SCAP_expr).where[g.PrcRcap[r, p]],
        )

        # Equations
        self.dscret_equation()
        self.cumulative_retirments_equation()
        self.max_salvage_capacity_equation()
        self.retrofit_equation()

        if self.env.varmac in ["0==0", "1==1"]:
            self.env.set_scoped("var", self.env.vas)
        self.tc.enqueue(
            self.exec_eqobj1,
            notmip=self.env.mip != "YES==YES",
            var=self.env.var,
        )

    def dscret_equation(self: PrepretDsc) -> None:
        g = self.tc
        sow_GP = self.env.sow_GP

        eq, swt = macro.EQ_DSCRET_GP(self.env.eq, self.env.swt_GP)
        var_scap = g.get_variable(name=f"{self.env.var}_SCAP")
        var_drcap = g.get_variable(name=f"{self.env.var}_DRCAP")
        dom1 = (g.r, g.v, g.t, g.p)
        dom2 = (g.r, g.v, g.p)

        # * Allow retirements in integer multiples of a user-defined block-size or the full residual capacity
        eq[g.RtpCptyr[*self.env.r_v_t_GP, g.p], *swt].where[
            (g.Vnret[g.v, g.t].where[g.rcap_blk[*dom2]])
        ] = (
            var_scap[*dom1, *sow_GP] - g.rtforc[*dom1]
            == g.rcap_blk[*dom2] * var_drcap[*dom1, *sow_GP, "2"]
            + (g.ncap_pasti[*dom2] - g.rtforc[*dom1]) * var_drcap[*dom1, *sow_GP, "1"]
        )

    def cumulative_retirments_equation(self: PrepretDsc) -> None:
        g = self.tc

        eq_cumret, swt = macro.EQ_CUMRET_GP(self.env.eq, self.env.swt_GP)
        var_scap = g.get_variable(name=f"{self.env.var}_SCAP")
        var_rcap = g.get_variable(name=f"{self.env.var}_RCAP")

        varm_id, varm_set = self.env.varm_GP
        varm_scap = g.get_variable(name=f"{varm_id}_SCAP")

        dom1 = (g.r, g.v, g.t, g.p)

        sum_a = Sum(
            g.RtpCptyr[g.r, g.v, g.k, g.p],
            var_scap[*dom1, *self.env.sow_GP] - var_rcap[*dom1, *self.env.sow_GP],
        )

        inner_sum = (
            varm_scap[g.r, g.v, g.Y, g.p, *self.env.sws_GP]
            if varm_set is None
            else Sum(varm_set, varm_scap[g.r, g.v, g.Y, g.p, *self.env.sws_GP])
        )

        sum_b = Sum(
            g.RtpCptyr[g.r, g.v, g.Modlyear[g.Y[g.t.lag(1)]], g.p].where[
                g.Vnret[g.v, g.Y]
            ],
            inner_sum,
        )
        # * Cumulative retirements
        eq_cumret[
            g.r,
            g.Vnret[g.v, g.k[g.t.lag(1 - Number(1).where[g.rp_rtf[g.r, g.p]])]],
            g.p,
            *swt,
        ].where[(g.RtpCptyr[*dom1].where[g.PrcRcap[g.r, g.p]])] = sum_a - sum_b == 0.0

    def max_salvage_capacity_equation(self: PrepretDsc) -> None:
        g = self.tc
        sws_GP = self.env.sws_GP
        sow_GP = self.env.sow_GP

        eq_l_scap, eq_sow_GP = macro.EQL_SCAP_GP(self.env.eq, sow_GP)
        var_scap = g.get_variable(name=f"{self.env.var}_SCAP")

        var_v_id, var_v_set = self.env.varv_GP
        var_v_ncap = g.get_variable(name=f"{var_v_id}_NCAP")

        var_t_id, var_t_set = self.env.vart_GP
        var_t_scap = g.get_variable(name=f"{var_t_id}_SCAP")

        vartt_id, vartt_set = self.env.vartt_GP
        var_tt_act = g.get_variable(name=f"{vartt_id}_ACT")

        inner_sum_1 = wrap_in_sum(
            var_tt_act[g.r, g.v, g.tt, g.p, g.s, *sws_GP], vartt_set
        )

        inner_sum_2 = (
            var_t_scap[g.r, g.v, g.t, g.p, *sws_GP]
            if var_t_set is None
            else Sum(var_t_set, var_t_scap[g.r, g.v, g.t, g.p, *sws_GP])
        )

        inner_sum_3 = (
            var_v_ncap[g.r, g.v, g.p, *sws_GP]
            if var_v_set is None
            else Sum(var_v_set, var_v_ncap[g.r, g.v, g.p, *sws_GP])
        )
        # * Maximum salvage capacity
        eq_l_scap[g.Rtp[g.r, g.v[g.ll], g.p], g.ips, *eq_sow_GP].where[
            (
                (
                    (
                        (
                            g.ObjSums[g.Rtp] + (~(g.PrcVint[g.r, g.p])).where[g.t[g.v]]
                        ).where[g.rvprl[g.Rtp] & g.lA[g.ips]]
                    )
                    | (g.ncap_olife[g.Rtp].where[g.io[g.ips]])
                ).where[g.PrcRcap[g.r, g.p]]
            )
        ] = (
            Sum(
                g.io[g.ips],
                Sum(
                    [g.RtpCptyr[g.r, g.v, g.tt, g.p], g.PrcTs[g.r, g.p, g.s]],  # type: ignore
                    inner_sum_1 * g.fpd[g.tt],
                )
                / g.prc_capact[g.r, g.p]
                / g.ncap_olife[g.Rtp],
            )
            + Sum(
                g.Vnret[g.v, g.t[g.ll + g.rvprl[g.Rtp]]],
                inner_sum_2,
            ).where[g.lim[g.ips]]
            <= inner_sum_3.where[g.t[g.v]]
            + g.ncap_pasti[g.r, g.v, g.p]
            - var_scap[g.r, g.v, "0", g.p, *sow_GP].where[
                g.ObjSums[g.r, g.v, g.p] & g.rvprl[g.r, g.v, g.p]
            ]
        )

    def retrofit_equation(self: PrepretDsc) -> None:
        g = self.tc

        eq_l_refit, swt = macro.EQL_REFIT_GP(self.env.eq, self.env.swt_GP)
        var_rcap = g.get_variable(name=f"{self.env.var}_RCAP")

        var_v_id, var_v_set = self.env.varv_GP
        var_v_ncap = g.get_variable(name=f"{var_v_id}_NCAP")

        vartt_id, vartt_set = self.env.vartt_GP
        vartt_rcap = g.get_variable(name=f"{vartt_id}_RCAP")

        inner_sum_1 = (
            var_v_ncap[g.r, g.v, g.p, *self.env.sws_GP]
            if var_v_set is None
            else Sum(var_v_set, var_v_ncap[g.r, g.v, g.p, *self.env.sws_GP])
        )

        inner_sum_2 = wrap_in_sum(
            vartt_rcap[g.r, g.v, g.tt, g.prc, *self.env.sws_GP], vartt_set
        )

        # * Retrofits and life-extensions
        eq_l_refit[g.RtpTt[g.r, g.tt, g.t, g.prc], g.Lnx[g.lA], *swt].where[
            (
                (
                    g.bd[g.lA] + g.Vnt[g.t, g.tt].where[(g.rp_rtf[g.r, g.prc] == 3.0)]
                ).where[g.RtPp[g.r, g.t]]
            )
        ] = (
            Sum(
                Domain(g.v[g.tt], g.p).where[
                    (
                        (
                            (g.Vnt[g.t, g.v]) | (g.prc_refit[g.r, g.prc, g.p] < 0.0)
                        ).where[g.prc_refit[g.r, g.prc, g.p]]
                    )
                ],
                g.coef_cpt[g.r, g.v, g.t, g.p] * (inner_sum_1 + self.env.rcapsub_GP),
            )
            + var_rcap[g.r, g.t, g.tt, g.prc, *self.env.sow_GP].where[
                (g.rp_rtf[g.r, g.prc].where[g.Vnt[g.t, g.tt] & g.bd[g.lA]] < 3.0)
            ]
            == Sum(
                g.RtpCptyr[g.r, g.Vnret[g.v, g.tt], g.prc],
                g.coef_cpt[g.r, g.v, g.t, g.prc]
                * (
                    inner_sum_2
                    - Sum(
                        g.Modlyear[g.k[g.tt - 1]].where[g.Vnt[g.v, g.k]],
                        Min(
                            Number(SpecialValues.POSINF).where[
                                mod(g.rp_rtf[g.r, g.prc], 2.0)
                            ],
                            g.rtforc[g.r, g.v, g.tt, g.prc]
                            - g.rtforc[g.r, g.v, g.k, g.prc],
                        ),
                    )
                ),
            )
            + Sum(
                g.k[g.tt - 1].where[g.RtpTt[g.r, g.k, g.t, g.prc]],
                var_rcap[g.r, g.t, g.k, g.prc, *self.env.sow_GP],
            ).where[(g.rp_rtf[g.r, g.prc].where[g.bd[g.lA]] > 0.0)]
        )

    def exec_eqobj1(self: PrepretDsc, notmip: bool, var: str) -> None:
        g = self.tc

        if notmip:
            g.rcap_blk.setRecords(None)

        var_drcap = g.get_variable(name=f"{var}_DRCAP")
        var_scap = g.get_variable(name=f"{var}_SCAP")

        # * Set bounds for integer retirements
        if g.rcap_blk.number_records:
            g.rcap_blk[g.Rtp].where[(g.rcap_blk[g.Rtp] <= 0.0)] = 0.0
            # *  Define upper bound of 1 for binary variable if past investments
            g.coef_cap[g.RtpCptyr[g.r, g.v, g.t, g.p]].where[
                g.rcap_blk[g.r, g.v, g.p]
            ] = (
                g.ncap_pasti[g.r, g.v, g.p] - g.rtforc[g.r, g.v, g.t, g.p]
            ) / g.rcap_blk[g.r, g.v, g.p]
            var_drcap.up[g.RtpCptyr[g.r, g.v, g.t, g.p], *self.env.sow_GP, "1"].where[
                g.PrcRcap[g.r, g.p]
            ] = Number(1.0).where[
                (
                    abs(
                        g.coef_cap[g.r, g.v, g.t, g.p]
                        - Min(10.0, Round(g.coef_cap[g.r, g.v, g.t, g.p]))
                    )
                    > 1e-09
                )
            ]
            # *  Define upper bound for integer multiples
            var_drcap.up[g.RtpCptyr[g.r, g.v, g.t, g.p], *self.env.sow_GP, "2"].where[
                g.rcap_blk[g.r, g.v, g.p]
            ] = Min(
                10.0,
                floor(
                    var_scap.up[g.r, g.v, g.t, g.p, *self.env.sow_GP]
                    / g.rcap_blk[g.r, g.v, g.p]
                    + 1e-08
                ),
            )
        g.rvprl[g.r, g.PyrS, g.p].where[g.prc_resid[g.r, "0", g.p]] = False
        g.ncap_olife[g.r, g.t, g.p].where[(~(g.PrcVint[g.r, g.p]))] = False
        g.coef_cap.setRecords(None)


def objfix_GP(
    g: TimesModelClass,
    capwd: ImplicitParameter | Number,
    vart: tuple[str, ImplicitSet | None],
    sws: tuple[Set | Alias, ...] | tuple[()],
) -> Any:
    """GAMSPy counterpart of objfix(): the retirement credit terms of EQ_OBJFIX."""
    r, v, t, p, cur, k, ll = g.r, g.v, g.t, g.p, g.cur, g.k, g.ll
    age, jot, life, j, jj = g.age, g.jot, g.life, g.j, g.jj
    KEoh, YEoh = g.KEoh, g.YEoh

    vart_id, vart_set = vart
    vart_scap = g.get_variable(f"{vart_id}_SCAP")
    scap: Any = vart_scap[r, v, t, p, *sws]
    if vart_set is not None:
        scap = Sum(vart_set, scap)

    def shaped(cost: Any, index: str, with_shape: bool) -> Any:
        """cost * (1+SUM(RTP_SHAPE(R,V,P,index,J,JJ),[SHAPE(J,AGE)*]MULTI(JJ,Y_EOH)-1))"""
        multiplier: Any = g.multi[jj, YEoh]
        if with_shape:
            multiplier = g.shape[j, age] * multiplier
        return cost * (1 + Sum(g.RtpShape[r, v, p, index, j, jj], multiplier - 1))

    def costs(with_shape: bool) -> Any:
        return (
            shaped(macro.obj_fom_GP(r, k, p, cur), "1", with_shape)
            + shaped(macro.obj_ftx_GP(r, k, p, cur), "2", with_shape)
            - shaped(macro.obj_fsb_GP(r, k, p, cur), "3", with_shape)
        )

    # * Credit retired capacity for the avoided fixed costs
    credit = Sum(
        Domain(g.ObjSumiv[KEoh, r, v, p, jot, life], g.Vnret[v, t]).where[
            g.rvprl[r, v, p]
        ],
        Sum(
            Domain(g.Invspred[KEoh, jot, ll, k], g.Ktyage[ll, t, YEoh, age]).where[
                g.Opyear[life, age]
            ],
            -g.obj_disc[r, YEoh, cur]
            * (1 + g.rtp_cpx[r, v, p, t].where[g.ncap_cpx[r, v, p]])
            * capwd
            * costs(with_shape=True),
        )
        * scap
        / g.obj_diviv[r, v, p],
    )

    # * RESIDS require special handling
    resid = Sum(
        g.RtpCptyr[r, g.PyrS[v[k]], t, p].where[
            (~g.rvprl[r, v, p]).where[g.PrcRcap[r, p]]
        ],
        Sum(
            g.Periodyr[t, YEoh],
            -g.obj_disc[r, YEoh, cur] * costs(with_shape=False),
        )
        * scap,
    )

    return credit + resid


def objfix(capwd: str, vart: str, sws: str) -> str:
    return rf"""
* Credit retired capacity for the avoided fixed costs
   SUM((OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE),VNRET(V,T))$RVPRL(R,V,P),
     SUM((INVSPRED(K_EOH,JOT,LL,K),KTYAGE(LL,T,Y_EOH,AGE))$OPYEAR(LIFE,AGE),
          -OBJ_DISC(R,Y_EOH,CUR) * (1+RTP_CPX(R,V,P,T)$NCAP_CPX(R,V,P)) * {capwd}
             (
                {macro.obj_fom("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) +
                {macro.obj_ftx("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1)) -
                {macro.obj_fsb("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,Y_EOH)-1))
             )
        ) *
        {macro.VAR_SCAP(vart, "R", "V", "T", "P", sws)} / OBJ_DIVIV(R,V,P)) +

* RESIDS require special handling
   SUM(RTP_CPTYR(R,PYR_S(V(K)),T,P)$((NOT RVPRL(R,V,P))$PRC_RCAP(R,P)),
        SUM(PERIODYR(T,Y_EOH), -OBJ_DISC(R,Y_EOH,CUR) *
             (
                {macro.obj_fom("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),MULTI(JJ,Y_EOH)-1)) +
                {macro.obj_ftx("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),MULTI(JJ,Y_EOH)-1)) -
                {macro.obj_fsb("R", "K", "P", "CUR")} * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),MULTI(JJ,Y_EOH)-1))
             )) *
        {macro.VAR_SCAP(vart, "R", "V", "T", "P", sws)}) +
"""


def objsalv(var: str, varv: str, sws: str, sow: str) -> str:
    return rf"""
* Discredit salvage value for retired capacity
   SUM(OBJ_SUMS(R,V,P)$((NOT NCAP_FDR(R,V,P)$RVPRL(R,'0',P))$RVPRL(R,V,P)),
     OBJSCC(R,V,P,CUR) * OBJ_DCEOH(R,CUR) *
     ({macro.VAR_SCAP(var, "R", "V", "'0'", "P", sow)}-{macro.VAR_NCAP(varv, "R", "V", "P", sws)}$T(V)-NCAP_PASTI(R,V,P))) +
"""


def objsalv_GP(g: TimesModelClass, env: CompileEnvironment) -> Expression | Sum:
    """
    NOTE: The Original function returned the expression with a plus
    """
    var_scap = g.get_variable(name=f"{env.var}_SCAP")

    varv_id, varv_set = env.varv_GP
    varv_ncap = g.get_variable(name=f"{varv_id}_NCAP")

    inner_sum = (
        varv_ncap[g.r, g.v, g.p, *env.sws_GP].where[g.t[g.v]]
        if varv_set is None
        else Sum(varv_set, varv_ncap[g.r, g.v, g.p, *env.sws_GP].where[g.t[g.v]])
    )

    expression = Sum(
        g.ObjSums[g.r, g.v, g.p].where[
            (
                (~(g.ncap_fdr[g.r, g.v, g.p].where[g.rvprl[g.r, "0", g.p]])).where[
                    g.rvprl[g.r, g.v, g.p]
                ]
            )
        ],
        g.objscc[g.r, g.v, g.p, g.cur]
        * g.obj_dceoh[g.r, g.cur]
        * (
            var_scap[g.r, g.v, "0", g.p, *env.sow_GP]
            - inner_sum
            - g.ncap_pasti[g.r, g.v, g.p]
        ),
    )
    return expression


def prepret_dsc() -> None:
    raise NotImplementedError()
