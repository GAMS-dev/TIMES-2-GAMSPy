# cost_ann_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COST_ANN: annual cost calculation
# *   - Investment Costs, Tax/Subsidies
# *   - Decommissioning
# *   - Fixed costs and taxes
# *   - Variable costs and Taxes/Subsidies
# *-----------------------------------------------------------------------------
# *  arg1 - Prefix for parameter names (optional)
# *  arg2 - SOW, (optional)
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import (
    Card,
    Domain,
    Else,
    If,
    Loop,
    Number,
    Ord,
    Smax,
    SpecialValues,
    Sum,
    sparse,
)
from gamspy.math import Max, Round, abs, aggregate, project

from core.base_class import GamsClass
from core.eqobjels_rpt import EqobjelsRptConfig, eqobjels_rpt, eqobjels_rpt_GP
from core.eqobjvar_rpt import EqobjvarRptConfig, eqobjvar_rpt, eqobjvar_rpt_GP
from core.powerflo_vda import powerflo_vda_rptb, powerflo_vda_rptb_GP
from core.utils import gams_if
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType, TpulseType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CostAnnRptConfig:
    """Strongly typed data contract for cost_ann.rpt."""

    # %1 - Prefix for parameter names (optional)
    arg1: str = ""
    # %2 - SOW, (optional): the leading index of the %1 prefixed parameters
    arg2: tuple[Set | Alias | str, ...] | tuple[()] = ()


class CostAnnRpt(GamsClass):
    """Translation unit for cost_ann.rpt."""

    # Instance attributes
    module_name: str = "cost_ann_rpt"
    gams_source: str = "cost_ann.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: CostAnnRptConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec1,
            config=self.config,
            stages=self.env.stages,
            etl=self.env.etl,
            invlif=self.env.invlif,
            anncost=self.env.anncost,
            sysprefix=self.env.sysprefix,
            pgprim=self.env.pgprim,
            tpulse_GP=self.env.tpulse_GP,
            is_vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv_GP,
            sws=self.env.sws_GP,
            varm=self.env.varm_GP,
            is_obj_combal_defined=self.tc.defined("OBJ_COMBAL"),
            sow=self.env.sow_GP,
            var=self.env.var,
            vart=self.env.vart_GP,
            micro=self.env.micro,
            is_mi_agc_defined=self.tc.defined("MI_AGC"),
        )

    def exec1(
        self: CostAnnRpt,
        config: CostAnnRptConfig,
        stages: str,
        etl: str,
        invlif: str,
        anncost: str,
        sysprefix: str,
        pgprim: str,
        tpulse_GP: TpulseType,
        is_vnret_defined: bool,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varm: tuple[str, ImplicitSet | None],
        is_obj_combal_defined: bool,
        sow: SowGPType,
        var: str,
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        micro: str,
        is_mi_agc_defined: bool,
    ) -> None:
        cost_ann_rpt_GP(
            g=self.tc,
            cc=config,
            stages=stages,
            etl=etl,
            invlif=invlif,
            anncost=anncost,
            sysprefix=sysprefix,
            pgprim=pgprim,
            tpulse_GP=tpulse_GP,
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


def cost_ann_rpt_GP(
    g: TimesModelClass,
    cc: CostAnnRptConfig,
    stages: str,
    etl: str,
    invlif: str,
    anncost: str,
    sysprefix: str,
    pgprim: str,
    tpulse_GP: TpulseType,
    is_vnret_defined: bool,
    varv: tuple[str, ImplicitSet | None],
    sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
    varm: tuple[str, ImplicitSet | None],
    is_obj_combal_defined: bool,
    sow: SowGPType,
    var: str,
    vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
    micro: str,
    is_mi_agc_defined: bool,
) -> None:
    cst_fixc = g.get_parameter(f"{cc.arg1}CST_FIXC")
    cst_fixx = g.get_parameter(f"{cc.arg1}CST_FIXX")
    cst_invc = g.get_parameter(f"{cc.arg1}CST_INVC")
    cst_invx = g.get_parameter(f"{cc.arg1}CST_INVX")
    ncap_invlif = g.get_parameter(f"NCAP_{invlif}")
    cst_decc = g.get_parameter(f"{cc.arg1}CST_DECC")
    cst_irec = g.get_parameter(f"{cc.arg1}CST_IREC")
    reg_irec = g.get_parameter(f"{cc.arg1}REG_IREC")
    reg_acost = g.get_parameter(f"{cc.arg1}REG_ACOST")
    cst_time = g.get_parameter(f"{cc.arg1}CST_TIME")
    cst_actc = g.get_parameter(f"{cc.arg1}CST_ACTC")
    cst_floc = g.get_parameter(f"{cc.arg1}CST_FLOC")
    cst_flox = g.get_parameter(f"{cc.arg1}CST_FLOX")
    cst_comc = g.get_parameter(f"{cc.arg1}CST_COMC")
    cst_come = g.get_parameter(f"{cc.arg1}CST_COME")
    cst_comx = g.get_parameter(f"{cc.arg1}CST_COMX")
    cst_salv = g.get_parameter(f"{cc.arg1}CST_SALV")
    cst_pvp = g.get_parameter(f"{cc.arg1}CST_PVP")
    cst_pvc = g.get_parameter(f"{cc.arg1}CST_PVC")

    g.ObjYes[g.NcapYes] = True
    g.coef_cap.setRecords(None)
    g.cnt[...] = Number(1.0).where[Round(g.rpt_opt["OBJ", "2"])]
    g.coef_cap[g.RtpCptyr[g.r, g.v, g.t, g.p]].where[
        (g.NcapYes[g.r, g.v, g.p].where[g.PrcRcap[g.r, g.p]])
    ] = g.VAR_SCAP.l[g.r, g.v, g.t, g.p] / g.rtp_capvl[g.r, g.v, g.p]

    # Levelized annual investment and fixed costs
    with gams_if(g, g.cnt):
        g.par_objcap.setRecords(None)
        g.par_objcap[g.ObjIcur[g.NcapYes[g.r, g.v, g.p], g.cur]] = Sum(
            g.RtpCptyr[g.r, g.v, g.t, g.p],
            g.coef_cpt[g.r, g.v, g.t, g.p] * g.obj_pvt[g.r, g.t, g.cur],
        )
        g.rtp_obj[g.j, g.r, g.v, g.p, g.cur].where[
            g.rtp_obj[g.j, g.r, g.v, g.p, g.cur]
        ] = (
            g.rtp_obj[g.j, g.r, g.v, g.p, g.cur] / g.par_objcap[g.r, g.v, g.p, g.cur]
        ).where[g.par_objcap[g.r, g.v, g.p, g.cur]]

        cst_invc[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p], g.Sysinv].where[
            g.NcapYes[g.r, g.v, g.p]
        ] = Sum(
            g.Rdcur[g.r, g.cur],
            g.rtp_obj["1", g.r, g.v, g.p, g.cur]
            * g.coef_cpt[g.r, g.v, g.t, g.p]
            * abs(g.sysone[g.Sysinv] - g.coef_crf[g.r, g.v, g.p, g.cur]),
        )
        cst_invx[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p], g.Sysinv].where[
            g.NcapYes[g.r, g.v, g.p]
        ] = Sum(
            g.Rdcur[g.r, g.cur],
            g.rtp_obj["2", g.r, g.v, g.p, g.cur]
            * g.coef_cpt[g.r, g.v, g.t, g.p]
            * abs(g.sysone[g.Sysinv] - g.coef_crf[g.r, g.v, g.p, g.cur]),
        )

        with gams_if(g, g.acl):
            g.par_objcap[g.ObjFcur[g.NcapYes[g.r, g.v, g.p], g.cur]] = Sum(
                g.RtpCptyr[g.r, g.v, g.t, g.p],
                g.coef_cpt[g.r, g.v, g.t, g.p]
                * (1.0 - g.coef_cap[g.r, g.v, g.t, g.p])
                * g.obj_pvt[g.r, g.t, g.cur],
            )
            g.rtp_npv[g.j, g.r, g.v, g.p, g.cur].where[
                g.rtp_npv[g.j, g.r, g.v, g.p, g.cur]
            ] = (
                g.rtp_npv[g.j, g.r, g.v, g.p, g.cur]
                / g.par_objcap[g.r, g.v, g.p, g.cur]
            ).where[g.par_objcap[g.r, g.v, g.p, g.cur]]
            cst_fixc[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]].where[
                g.NcapYes[g.r, g.v, g.p]
            ] = Sum(
                g.Rdcur[g.r, g.cur],
                g.rtp_npv["1", g.r, g.v, g.p, g.cur]
                * g.coef_cpt[g.r, g.v, g.t, g.p]
                * (1.0 - g.coef_cap[g.r, g.v, g.t, g.p]),
            )
            cst_fixx[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]].where[
                g.NcapYes[g.r, g.v, g.p]
            ] = Sum(
                g.Rdcur[g.r, g.cur],
                g.rtp_npv["2", g.r, g.v, g.p, g.cur]
                * g.coef_cpt[g.r, g.v, g.t, g.p]
                * (1.0 - g.coef_cap[g.r, g.v, g.t, g.p]),
            )
            g.coef_cap.setRecords(None)

        g.NcapYes.setRecords(None)

    # *------------------------------------------------------------------------------
    # * Cases I - Investment Cost and II - Taxes/Subsidies
    # *------------------------------------------------------------------------------
    # * Calculate Annual undiscounted investment costs CST_INVC

    tmp: Number | Expression = Number(1)
    x1 = ""
    sic: Expression | int = 1

    if stages.upper() == "YES":
        g.pastsum[g.NcapYes[g.r, g.t, g.p]] = Sum(
            g.SwTsw[g.Sow, g.t, g.ww], g.obj_sic[g.r, g.t, g.p, g.ww]
        )
        sic = 1 + g.pastsum[g.r, g.v, g.p]

    g.Fil.setRecords(None)
    aggregate(source=g.coef_cpt, target=g.coef_rvpt, direction="left")

    with gams_if(g, ~g.cnt):
        g.NcapYes[g.r, g.PyrS, g.p].where[g.prc_resid[g.r, "0", g.p]] = False

    with Loop(g.ObjIcur[g.NcapYes[g.r, g.v, g.p], g.cur]):
        g.Ykk.setRecords(None)
        g.my_f[...] = sic
        g.sysplit[g.Sysinv] = abs(g.sysone[g.Sysinv] - g.coef_crf[g.r, g.v, g.p, g.cur])
        g.f[...] = (
            g.rtp_capvl[g.r, g.v, g.p]
            * g.obj_crf[g.r, g.v, g.p, g.cur]
            / g.obj_divi[g.r, g.v, g.p]
        )

        with Loop(g.ObjSumii[g.r, g.v, g.p, g.life, g.KEoh, g.jot]):
            g.z[...] = Ord(g.life)
            g.Fil[g.t] = g.Vnt[g.v, g.t].where[
                (g.m[g.t] < g.yearval[g.KEoh] + Ord(g.jot) + g.z)
            ]
            g.Ykk[g.Yk[g.Fil[g.year], g.ll], g.k].where[
                (
                    (Ord(g.year) < Ord(g.ll) + g.z).where[
                        g.Invspred[g.KEoh, g.jot, g.ll, g.k]
                    ]
                )
            ] = True
            g.cstvpj[g.r, g.v, g.p, "1", g.Sysinv, g.t[g.Fil]] = (
                Sum(
                    g.Ykk[g.t, g.ll, g.k],
                    g.f * g.my_f * macro.obj_icost_GP(g.r, g.k, g.p, g.cur),
                )
                * g.sysplit[g.Sysinv]
            )
            g.cstvpj[g.r, g.v, g.p, "2", g.Sysinv, g.t[g.Fil]].where[
                macro.obj_itax_GP(g.r, g.v, g.p, g.cur)
                + macro.obj_isub_GP(g.r, g.v, g.p, g.cur)
            ] = (
                Sum(
                    g.Ykk[g.t, g.ll, g.k],
                    g.f
                    * (
                        macro.obj_itax_GP(g.r, g.k, g.p, g.cur)
                        - macro.obj_isub_GP(g.r, g.k, g.p, g.cur)
                    ),
                )
                * g.sysplit[g.Sysinv]
            )

    with gams_if(g, ~g.cnt):
        g.Fil[g.v] = g.PyrS[g.v]
        aggregate(source=g.cstvpj, target=g.cstvnt)
        g.cstvpj.setRecords(None)

    cst_invc[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv] = sparse(
        g.cstvnt["1", g.r, g.v, g.t, g.p, g.Sysinv]
    )
    cst_invx[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv] = sparse(
        g.cstvnt["2", g.r, g.v, g.t, g.p, g.Sysinv]
    )

    # Report approximate costs for RESID according to available capacity
    with Loop(g.ObjIcur[g.r, g.Fil[g.v], g.p, g.cur].where[g.prc_resid[g.r, "0", g.p]]):
        g.fil2[g.t] = (
            g.ncap_pasti[g.r, g.v, g.p] * g.coef_rvpt[g.r, g.v, g.p, g.t]
            - g.rtforc[g.r, g.v, g.t, g.p]
        ) * g.obj_crf[g.r, g.v, g.p, g.cur]
        cst_invc[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p], g.Sysinv] = (
            abs(g.sysone[g.Sysinv] - g.coef_crf[g.r, g.v, g.p, g.cur])
            * g.fil2[g.t]
            * macro.obj_icost_GP(g.r, g.v, g.p, g.cur)
        )
        cst_invx[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p], g.Sysinv] = (
            abs(g.sysone[g.Sysinv] - g.coef_crf[g.r, g.v, g.p, g.cur])
            * g.fil2[g.t]
            * (
                macro.obj_itax_GP(g.r, g.v, g.p, g.cur)
                - macro.obj_isub_GP(g.r, g.v, g.p, g.cur)
            )
        )
    # Handle ETL
    if etl == "YES":
        with Loop(
            g.ObjIcur[g.r, g.t, g.Teg[g.p], g.cur].where[g.VAR_IC.l[g.r, g.t, g.p]]
        ):
            g.Ykk.setRecords(None)
            g.f[...] = (
                g.VAR_IC.l[g.r, g.t, g.p]
                * g.obj_crf[g.r, g.t, g.p, g.cur]
                / g.obj_divi[g.r, g.t, g.p]
            )
            with Loop(
                Domain(
                    g.ObjSumii[g.r, g.t, g.p, g.life, g.KEoh, g.jot],
                    g.Invspred[g.KEoh, g.jot, g.ll, g.k],
                )
            ):
                g.z[...] = Ord(g.life)
                g.Ykk[g.Yk[g.tt, g.ll], g.k].where[
                    (g.yearval[g.tt] < g.yearval[g.ll] + g.z)
                ] = True
            cst_invc[*cc.arg2, g.r, g.Vnt[g.t, g.tt], g.p, g.Sysinv].where[
                g.sysone[g.Sysinv]
            ] = cst_invc[*cc.arg2, g.r, g.t, g.tt, g.p, g.Sysinv] + Sum(
                g.Ykk[g.tt, g.ll, g.k], g.f
            )

    # *------------------------------------------------------------------------------
    # * Cases III - Decommissioning
    # *------------------------------------------------------------------------------

    project(source=g.ObjSumiii, target=g.ObjSumsi, direction="left")
    # * Calculate decommissioning costs, annualized to operating years:
    with Loop(
        g.ObjIcur[g.NcapYes[g.r, g.v, g.p], g.cur].where[
            macro.obj_dcost_GP(g.r, g.v, g.p, g.cur)
        ]
    ):
        g.f[...] = g.rtp_capvl[g.r, g.v, g.p]
        g.f[...] = g.f * g.obj_crf[g.r, g.v, g.p, g.cur] / g.obj_diviii[g.r, g.v, g.p]
        g.z[...] = Round(ncap_invlif[g.r, g.v, g.p])
        cst_decc[*cc.arg2, g.r, g.Vnt[g.v, g.t], g.p] = Sum(
            g.ObjSumsi[g.r, g.v, g.p, g.ll].where[
                ((g.yearval[g.t] < g.yearval[g.ll] + g.z).where[g.Yk[g.t, g.ll]])
            ],
            (
                Sum(
                    g.ObjSumiii[g.r, g.v, g.p, g.ll, g.k, g.Y],
                    g.obj_disc[g.r, g.Y, g.cur]
                    * macro.obj_dcost_GP(g.r, g.k, g.p, g.cur),
                )
                * g.cor_salvd[g.r, g.v, g.p, g.cur]
                + Sum(
                    g.ObjSumivs[g.r, g.v, g.p, g.k[g.ll], g.Y],
                    g.obj_disc[g.r, g.Y, g.cur],
                )
                * macro.obj_dlagc_GP(g.r, g.ll, g.p, g.cur)
            )
            * g.f
            / g.obj_disc[g.r, g.ll, g.cur],
        )

    # *------------------------------------------------------------------------------
    # * Cases IV - Fixed costs
    # *------------------------------------------------------------------------------

    with gams_if(g, ~g.acl):
        g.fil2.setRecords(None)
        g.my_fil2.setRecords(None)
        with If(g.cnt):
            g.NcapYes[g.ObjYes] = True
            g.NcapYes[g.r, g.PyrS, g.p].where[g.prc_resid[g.r, "0", g.p]] = False
            g.Fil[g.PyrS] = 1.0
        with Else():
            g.coef_rvpt[g.NcapYes[g.Rtp], g.t].where[g.coef_rvpt[g.Rtp, g.t]] = (
                1.0 + g.rtp_cpx[g.Rtp, g.t].where[g.ncap_cpx[g.Rtp]]
            ) / Max(1.0, g.obj_diviv[g.Rtp])

    with Loop(g.ObjFcur[g.NcapYes[g.r, g.v, g.p], g.cur]):
        g.f[...] = g.rtp_capvl[g.r, g.v, g.p]
        g.Ykage.setRecords(None)
        g.my_fil2[g.t] = g.coef_rvpt[g.r, g.v, g.p, g.t]
        g.my_f[...] = g.b[g.v] + g.ncap_iled[g.r, g.v, g.p]
        with Loop(g.ObjSumiv[g.KEoh, g.r, g.v, g.p, g.jot, g.life]):
            g.z[...] = Ord(g.life) - 1.0
            g.fil2[g.t[g.year]] = (
                Ord(g.year)
                + (
                    Max(0.0, g.my_f - g.m[g.t]) - Max(0.0, g.m[g.t] - g.my_f - g.z)
                ).where[g.cnt]
            )
            g.Ykage[g.t, g.ll, g.age[g.life + (g.fil2[g.t] - Ord(g.ll) - g.z)]].where[
                g.Invstep[g.KEoh, g.jot, g.ll, g.jot].where[
                    g.Opyear[g.life, g.age].where[g.my_fil2[g.t]]
                ]
            ] = True
        g.fil2[g.t] = (
            g.f
            * g.my_fil2[g.t]
            / Max(1.0, Sum(g.Ykage[g.t, g.ll, g.age], 1.0).where[g.cnt])
        )
        g.cstvpj[g.r, g.v, g.p, "1", "FIX", g.t] = g.fil2[g.t] * Sum(
            g.Ykage[g.t, g.k, g.age],
            macro.obj_fom_GP(g.r, g.k, g.p, g.cur)
            * (
                1.0
                + Sum(
                    g.RtpShape[g.r, g.v, g.p, "1", g.j, g.jj],
                    g.shape[g.j, g.age] * g.multi[g.jj, g.t] - 1.0,
                )
            ),
        )
        g.cstvpj[g.r, g.v, g.p, "2", "FIX", g.t].where[
            (
                macro.obj_ftx_GP(g.r, g.v, g.p, g.cur)
                + macro.obj_fsb_GP(g.r, g.v, g.p, g.cur)
            )
        ] = g.fil2[g.t] * Sum(
            g.Ykage[g.t, g.k, g.age],
            (
                macro.obj_ftx_GP(g.r, g.k, g.p, g.cur)
                * (
                    1.0
                    + Sum(
                        g.RtpShape[g.r, g.v, g.p, "2", g.j, g.jj],
                        g.shape[g.j, g.age] * g.multi[g.jj, g.t] - 1.0,
                    )
                )
                - macro.obj_fsb_GP(g.r, g.k, g.p, g.cur)
                * (
                    1.0
                    + Sum(
                        g.RtpShape[g.r, g.v, g.p, "3", g.j, g.jj],
                        g.shape[g.j, g.age] * g.multi[g.jj, g.t] - 1.0,
                    )
                )
            ),
        )

    aggregate(source=g.cstvpj, target=g.cstvnt)
    g.cstvpj.setRecords(None)
    cst_fixc[*cc.arg2, g.r, g.v, g.t, g.p] = sparse(
        g.cstvnt["1", g.r, g.v, g.t, g.p, "FIX"]
    )
    cst_fixx[*cc.arg2, g.r, g.v, g.t, g.p] = sparse(
        g.cstvnt["2", g.r, g.v, g.t, g.p, "FIX"]
    )

    # * Report approximate costs for RESID according to available capacity
    with Loop(g.ObjFcur[g.r, g.Fil[g.v], g.p, g.cur].where[g.prc_resid[g.r, "0", g.p]]):
        cst_fixc[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]] = (
            g.ncap_pasti[g.r, g.v, g.p]
            * g.coef_rvpt[g.r, g.v, g.p, g.t]
            * macro.obj_fom_GP(g.r, g.v, g.p, g.cur)
            * (
                1.0
                + Sum(
                    g.RtpShape[g.r, g.v, g.p, "1", g.j, g.jj], g.multi[g.jj, g.t] - 1.0
                )
            )
        )
        cst_fixx[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]] = (
            g.ncap_pasti[g.r, g.v, g.p]
            * g.coef_rvpt[g.r, g.v, g.p, g.t]
            * (
                macro.obj_ftx_GP(g.r, g.v, g.p, g.cur)
                * (
                    1.0
                    + Sum(
                        g.RtpShape[g.r, g.v, g.p, "2", g.j, g.jj],
                        g.multi[g.jj, g.t] - 1.0,
                    )
                )
                - macro.obj_fsb_GP(g.r, g.v, g.p, g.cur)
                * (
                    1.0
                    + Sum(
                        g.RtpShape[g.r, g.v, g.p, "3", g.j, g.jj],
                        g.multi[g.jj, g.t] - 1.0,
                    )
                )
            )
        )
    with gams_if(g, Card(g.PrcRcap)):
        g.coef_cap[g.RtpCptyr[g.r, g.v, g.t, g.p]].where[
            g.coef_cap[g.r, g.v, g.t, g.p]
        ] = 1.0 - g.coef_cap[g.r, g.v, g.t, g.p] + SpecialValues.EPS
        cst_fixc[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]] = sparse(
            g.coef_cap[g.r, g.v, g.t, g.p] * cst_fixc[*cc.arg2, g.r, g.v, g.t, g.p]
        )
        cst_fixx[*cc.arg2, g.RtpCptyr[g.r, g.v, g.t, g.p]] = sparse(
            g.coef_cap[g.r, g.v, g.t, g.p] * cst_fixx[*cc.arg2, g.r, g.v, g.t, g.p]
        )
    g.NcapYes[g.ObjYes] = True

    # *-----------------------------------------------------------------------------
    # * Marginal costs of endogenous trade
    # *-----------------------------------------------------------------------------
    g.ObjYes.setRecords(None)
    g.cstvnt.setRecords(None)
    g.par_ipric.setRecords(None)
    g.par_ipric[g.Rtp[g.r, g.t, g.p], g.c, g.ts, "IMP"] = sparse(
        (-1.0) * g.eq_ire.m[g.r, g.t, g.p, g.c, "IMP", g.ts]
    )
    g.CgGrp[g.r, g.p, g.c, g.Com].where[g.TopIre[g.r, g.c, g.r, g.Com, g.p]] = True
    with Loop(
        g.CgGrp[g.Reg, g.p, g.com1, g.Com].where[g.RpcMarket[g.Reg, g.p, g.Com, "IMP"]]
    ):
        g.par_ipric[g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts], "IMP"].where[
            g.TopIre[g.Reg, g.com1, g.r, g.c, g.p]
        ] = -Sum(
            Domain(g.RsTree[g.r, g.allts, g.ts], g.s).where[
                (
                    g.ire_tscvt[g.r, g.allts, g.Reg, g.s].where[
                        g.eq_ire.m[g.Reg, g.t, g.p, g.Com, "IMP", g.s]
                    ]
                )
            ],
            g.eq_ire.m[g.Reg, g.t, g.p, g.Com, "IMP", g.s]
            * g.ire_ccvt[g.Reg, g.com1, g.Reg, g.Com]
            * g.ire_ccvt[g.r, g.c, g.Reg, g.com1]
            * g.rs_fr[g.r, g.allts, g.ts]
            * g.ire_tscvt[g.r, g.allts, g.Reg, g.s],
        )

    g.par_xpri[g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts], g.Reg, g.Com].where[
        (
            g.TopIre[g.r, g.c, g.Reg, g.Com, g.p].where[
                g.RpcIreio[g.r, g.p, g.c, "EXP", "IN"]
            ]
        )
    ] = Sum(
        Domain(g.RsTree[g.r, g.ts, g.allts], g.s).where[
            (
                g.ire_tscvt[g.r, g.allts, g.Reg, g.s].where[
                    g.eq_ire.m[g.Reg, g.t, g.p, g.Com, "IMP", g.s]
                ]
            )
        ],
        g.eq_ire.m[g.Reg, g.t, g.p, g.Com, "IMP", g.s]
        * g.ire_flo[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
        * g.ire_ccvt[g.r, g.c, g.Reg, g.Com]
        * g.rs_fr[g.r, g.allts, g.ts]
        * g.ire_tscvt[g.r, g.allts, g.Reg, g.s],
    )
    g.par_ipric[g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts], "EXP"].where[
        g.RpcIreio[g.r, g.p, g.c, "EXP", "IN"]
    ] = sparse(
        Smax(
            g.TopIre[g.r, g.c, g.Reg, g.Com, g.p],
            g.par_xpri[g.r, g.t, g.p, g.c, g.ts, g.Reg, g.Com],
        )
    )
    g.par_ipric[g.Rtp[g.r, g.t, g.p], g.c, g.ts, "EXP"] = sparse(
        g.eq_ire.m[g.r, g.t, g.p, g.c, "EXP", g.ts]
    )
    with Loop(g.RpcEqire[g.Reg, g.p, g.Com, "EXP"]):
        g.par_ipric[g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts], "IMP"].where[
            g.TopIre[g.Reg, g.Com, g.r, g.c, g.p]
        ] = -Sum(
            Domain(g.RsTree[g.r, g.allts, g.ts], g.s).where[
                g.ire_tscvt[g.r, g.allts, g.Reg, g.s]
            ],
            g.eq_ire.m[g.Reg, g.t, g.p, g.Com, "EXP", g.s]
            / g.ire_flo[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.ts]
            * g.ire_ccvt[g.r, g.c, g.Reg, g.Com]
            * g.rs_fr[g.r, g.allts, g.ts]
            * g.ire_tscvt[g.r, g.allts, g.Reg, g.s],
        )
    g.prc_ymax[g.RpIre[g.r, g.p]] = sparse(
        Sum(
            [
                g.RpcIreio[g.r, g.p, g.c, g.ie, "IN"],
                g.RtpVintyr[g.r, g.v, g.t, g.p],
                g.RpcsVar[g.r, g.p, g.c, g.s],
            ],
            g.par_ipric[g.r, g.t, g.p, g.c, g.s, g.ie]
            * g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
        )
    )

    reg_irec[*cc.arg2, g.r] = sparse(Sum(g.p, g.prc_ymax[g.r, g.p]))
    g.par_ipric[g.r, g.t, g.p, g.c, g.ts, g.ie].where[
        g.par_ipric[g.r, g.t, g.p, g.c, g.ts, g.ie]
    ] = g.par_ipric[g.r, g.t, g.p, g.c, g.ts, g.ie] * (1.0 / g.coef_pvt[g.r, g.t])

    if cc.arg1 == "S":
        spar_ipric = g.get_parameter("SPAR_IPRIC")
        spar_ipric[*cc.arg2, g.r, g.t, g.p, g.c, g.ts, g.ie] = sparse(
            g.par_ipric[g.r, g.t, g.p, g.c, g.ts, g.ie]
        )

    g.CgGrp.setRecords(None)
    g.par_objcap.setRecords(None)
    g.par_xpri.setRecords(None)
    g.rtp_obj.setRecords(None)
    g.rtp_npv.setRecords(None)
    g.coef_crf.setRecords(None)
    g.coef_rvpt.setRecords(None)

    # *------------------------------------------------------------------------------
    # * Marginal costs associated with endogenous imports/exports
    # * - note that price only applied when actually an internal region
    # *------------------------------------------------------------------------------

    cst_irec[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c].where[
        (g.Rpc[g.r, g.p, g.c].where[g.RpIre[g.r, g.p]])
    ] = sparse(
        Sum(
            [
                g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
                g.RpcIreio[g.r, g.p, g.c, g.ie, "IN"],
            ],
            g.par_ipric[g.r, g.t, g.p, g.c, g.s, g.ie]
            * g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
        )
    )

    # *------------------------------------------------------------------------------
    # * EQOBJVAR the objective function variable cost reporting
    # *------------------------------------------------------------------------------
    if anncost.upper() == "LEV":
        x1 = "LEV"
        tmp = 1 / g.obj_pvt[g.r, g.t, g.cur]

    cst_time[*cc.arg2, g.r, g.t, g.Annual, f"{sysprefix}{x1}COST"] = g.coef_pvt[
        g.r, g.t
    ]

    if anncost.upper() != "LEV":
        # $BATINCLUDE eqobjvar.rpt PAR J('1'), J('2'), T
        eqobjvar_rpt_GP(
            g=g,
            config=EqobjvarRptConfig(
                arg1="PAR", arg2=(g.j["1"],), arg3=(g.j["2"],), arg4=(g.t,)
            ),
            pgprim=pgprim,
            tpulse=tpulse_GP,
            tmp=tmp,
            stages=stages,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )

    cst_actc[*cc.arg2, g.r, g.v, g.t, g.p, "-"] = sparse(
        Sum(
            g.cur.where[g.par_actc["1", g.r, g.v, g.t, g.p, pgprim, g.cur]],
            g.par_actc["1", g.r, g.v, g.t, g.p, pgprim, g.cur] * tmp,
        )
    )
    cst_actc[*cc.arg2, g.r, g.v, g.t, g.p, "+"] = sparse(
        Sum(
            g.cur.where[g.par_actc["2", g.r, g.v, g.t, g.p, pgprim, g.cur]],
            g.par_actc["2", g.r, g.v, g.t, g.p, pgprim, g.cur] * tmp,
        )
    )
    cst_floc[*cc.arg2, g.r, g.v, g.t, g.p, g.c] = sparse(
        Sum(
            g.cur.where[g.par_floc["1", g.r, g.v, g.t, g.p, g.c, g.cur]],
            g.par_floc["1", g.r, g.v, g.t, g.p, g.c, g.cur] * tmp,
        )
    )
    cst_flox[*cc.arg2, g.r, g.v, g.t, g.p, g.c] = sparse(
        Sum(
            g.cur.where[g.par_floc["2", g.r, g.v, g.t, g.p, g.c, g.cur]],
            g.par_floc["2", g.r, g.v, g.t, g.p, g.c, g.cur] * tmp,
        )
    )
    cst_comc[*cc.arg2, g.r, g.t, g.c] = sparse(
        Sum(
            g.cur.where[g.par_comc["1", g.r, g.t, g.c, g.cur]],
            g.par_comc["1", g.r, g.t, g.c, g.cur] * tmp,
        )
    )
    cst_comx[*cc.arg2, g.r, g.t, g.c] = sparse(
        Sum(
            g.cur.where[g.par_comc["2", g.r, g.t, g.c, g.cur]],
            g.par_comc["2", g.r, g.t, g.c, g.cur] * tmp,
        )
    )
    if is_obj_combal_defined:
        powerflo_vda_rptb_GP(
            g=g,
            arg4=cc.arg1,
            arg5=cc.arg2,
            arg6=sow,
            var=var,
            vart=vart,
            sws=sws,
        )
    # *------------------------------------------------------------------------------
    # * EQOBJELS the objective function flexible demand cost reporting
    # *------------------------------------------------------------------------------
    eqobjels_rpt_GP(
        g=g,
        config=EqobjelsRptConfig(
            arg1=cst_come[*cc.arg2, g.r, g.tt, g.c],
            arg2=g.tt,
        ),
        micro=micro,
        if_mi_agc_defined=is_mi_agc_defined,
    )

    with gams_if(g, Card(cst_pvp)):
        cst_pvc[*cc.arg2, f"{sysprefix}ELS", g.r, g.c].where[
            Sum(g.Rcj[g.r, g.c, "1", g.Bdneq], 1.0)
        ] = Sum(g.t, cst_come[*cc.arg2, g.r, g.t, g.c] * g.coef_pvt[g.r, g.t])
        cst_pvp[*cc.arg2, f"{sysprefix}IRE", g.RpIre[g.Rp]] = sparse(g.prc_ymax[g.Rp])

    # *------------------------------------------------------------------------------
    # * Regional annual costs

    reg_acost[*cc.arg2, g.r, g.t, "INV"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p, g.Sysinv).where[
            cst_invc[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv]
        ],
        cst_invc[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv],
    )
    reg_acost[*cc.arg2, g.r, g.t, "INVX"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p, g.Sysinv).where[
            cst_invx[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv]
        ],
        cst_invx[*cc.arg2, g.r, g.v, g.t, g.p, g.Sysinv],
    )
    reg_acost[*cc.arg2, g.r, g.t, "FIX"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p).where[cst_fixc[*cc.arg2, g.r, g.v, g.t, g.p]],
        cst_fixc[*cc.arg2, g.r, g.v, g.t, g.p],
    )
    reg_acost[*cc.arg2, g.r, g.t, "FIXX"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p).where[cst_fixx[*cc.arg2, g.r, g.v, g.t, g.p]],
        cst_fixx[*cc.arg2, g.r, g.v, g.t, g.p],
    )
    reg_acost[*cc.arg2, g.r, g.t, "VAR"] = (
        Sum(
            Domain(g.Vnt[g.v, g.t], g.p, g.rpm).where[
                cst_actc[*cc.arg2, g.r, g.v, g.t, g.p, g.rpm]
            ],
            cst_actc[*cc.arg2, g.r, g.v, g.t, g.p, g.rpm],
        )
        + Sum(
            Domain(g.Vnt[g.v, g.t], g.p, g.c).where[
                cst_floc[*cc.arg2, g.r, g.v, g.t, g.p, g.c]
            ],
            cst_floc[*cc.arg2, g.r, g.v, g.t, g.p, g.c],
        )
        + Sum(
            g.c.where[cst_comc[*cc.arg2, g.r, g.t, g.c]],
            cst_comc[*cc.arg2, g.r, g.t, g.c],
        )
    )
    reg_acost[*cc.arg2, g.r, g.t, "VARX"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p, g.c).where[
            cst_flox[*cc.arg2, g.r, g.v, g.t, g.p, g.c]
        ],
        cst_flox[*cc.arg2, g.r, g.v, g.t, g.p, g.c],
    ) + Sum(
        g.c.where[cst_comx[*cc.arg2, g.r, g.t, g.c]],
        cst_comx[*cc.arg2, g.r, g.t, g.c],
    )
    reg_acost[*cc.arg2, g.r, g.t, "IRE"] = Sum(
        Domain(g.Vnt[g.v, g.t], g.p, g.c).where[
            cst_irec[*cc.arg2, g.r, g.v, g.t, g.p, g.c]
        ],
        cst_irec[*cc.arg2, g.r, g.v, g.t, g.p, g.c],
    )
    reg_acost[*cc.arg2, g.r, g.t, "ELS"] = Sum(
        g.c.where[cst_come[*cc.arg2, g.r, g.t, g.c]],
        cst_come[*cc.arg2, g.r, g.t, g.c],
    )

    g.par_actc.setRecords(None)
    g.par_comc.setRecords(None)
    g.par_floc.setRecords(None)
    g.prc_ymax.setRecords(None)
    g.pastsum.setRecords(None)

    # *------------------------------------------------------------------------------

    # *------------------------------------------------------------------------------
    # * Salvage costs (not for stochastic runs)
    # *------------------------------------------------------------------------------
    # * Calculate actual Salvage values
    if cc.arg1 != "S":
        g.par_objsal[g.ObjIcur[g.r, g.t, g.p, g.cur]] = (
            g.par_objsal[g.r, g.t, g.p, g.cur] * g.VAR_NCAP.l[g.r, g.t, g.p]
        )

        if etl == "YES":
            g.par_objsal[g.Rtp[g.r, g.t, g.Teg[g.p]], g.cur].where[
                g.GRcur[g.r, g.cur]
            ] = (
                g.par_objsal[g.Rtp, g.cur]
                + Sum(g.ObjSums[g.Rtp], g.objsic[g.Rtp] * g.VAR_IC.l[g.Rtp])
                * g.obj_dceoh[g.r, g.cur]
            )
        cst_salv[*cc.arg2, g.r, g.t, g.p] = sparse(
            Sum(g.Rdcur[g.r, g.cur], g.par_objsal[g.r, g.t, g.p, g.cur])
        )
        g.reg_obj[g.r] = Sum(
            Domain(g.Rdcur[g.r, g.cur], g.item, g.obv).where[g.sum_obj[g.item, g.obv]],
            g.VAR_OBJ.l[g.r, g.obv, g.cur] * g.sum_obj[g.item, g.obv],
        )


def cost_ann_rpt(
    arg1: str,
    arg2: str,
    stages: str,
    etl: str,
    invlif: str,
    anncost: str,
    sysprefix: str,
    pgprim: str,
    tpulse: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
    is_obj_combal_defined: bool,
    sow: str,
    var: str,
    vart: str,
    micro: str,
    is_mi_agc_defined: bool,
) -> str:
    return_str = rf"""
  OBJ_YES(NCAP_YES)=YES;
  OPTION CLEAR=COEF_CAP; CNT=1$ROUND(RPT_OPT('OBJ','2'));
  COEF_CAP(RTP_CPTYR(R,V,T,P))$(NCAP_YES(R,V,P)$PRC_RCAP(R,P)) = VAR_SCAP.L(R,V,T,P)/RTP_CAPVL(R,V,P);
* Levelized annual investment and fixed costs
  IF(CNT, OPTION CLEAR=PAR_OBJCAP;
    PAR_OBJCAP(OBJ_ICUR(NCAP_YES(R,V,P),CUR)) = SUM(RTP_CPTYR(R,V,T,P),COEF_CPT(R,V,T,P)*OBJ_PVT(R,T,CUR));
    RTP_OBJ(J,R,V,P,CUR)$RTP_OBJ(J,R,V,P,CUR) = (RTP_OBJ(J,R,V,P,CUR)/PAR_OBJCAP(R,V,P,CUR))$PAR_OBJCAP(R,V,P,CUR);
    {arg1}CST_INVC({arg2}RTP_CPTYR(R,V,T,P),SYSINV)$NCAP_YES(R,V,P) =
       SUM(RDCUR(R,CUR),RTP_OBJ('1',R,V,P,CUR)*COEF_CPT(R,V,T,P)*ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)));
    {arg1}CST_INVX({arg2}RTP_CPTYR(R,V,T,P),SYSINV)$NCAP_YES(R,V,P) =
       SUM(RDCUR(R,CUR),RTP_OBJ('2',R,V,P,CUR)*COEF_CPT(R,V,T,P)*ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)));
  IF(ACL,
    PAR_OBJCAP(OBJ_FCUR(NCAP_YES(R,V,P),CUR)) = SUM(RTP_CPTYR(R,V,T,P),COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P))*OBJ_PVT(R,T,CUR));
    RTP_NPV(J,R,V,P,CUR)$RTP_NPV(J,R,V,P,CUR) = (RTP_NPV(J,R,V,P,CUR)/PAR_OBJCAP(R,V,P,CUR))$PAR_OBJCAP(R,V,P,CUR);
    {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P))$NCAP_YES(R,V,P) = SUM(RDCUR(R,CUR),RTP_NPV('1',R,V,P,CUR)*COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P)));
    {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P))$NCAP_YES(R,V,P) = SUM(RDCUR(R,CUR),RTP_NPV('2',R,V,P,CUR)*COEF_CPT(R,V,T,P)*(1-COEF_CAP(R,V,T,P)));
    OPTION CLEAR=COEF_CAP);
    OPTION CLEAR=NCAP_YES;
  );
*------------------------------------------------------------------------------
* Cases I - Investment Cost and II - Taxes/Subsidies
*------------------------------------------------------------------------------
* Calculate Annual undiscounted investment costs CST_INVC
"""
    tmp = ""
    x1 = ""
    sic = "1"

    if stages.upper() == "YES":
        return_str += (
            "PASTSUM(NCAP_YES(R,T,P)) = SUM(SW_TSW(SOW,T,WW),OBJ_SIC(R,T,P,WW));"
        )
        sic = "1+PASTSUM(R,V,P)"

    return_str += rf"""
OPTION CLEAR=FIL,COEF_RVPT<=COEF_CPT; IF(NOT CNT,NCAP_YES(R,PYR_S,P)$PRC_RESID(R,'0',P)=NO);

LOOP(OBJ_ICUR(NCAP_YES(R,V,P),CUR), OPTION CLEAR=YKK; MY_F={sic};
  SYSPLIT(SYSINV)=ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR));
  F = RTP_CAPVL(R,V,P)*OBJ_CRF(R,V,P,CUR)/OBJ_DIVI(R,V,P);
  LOOP(OBJ_SUMII(R,V,P,LIFE,K_EOH,JOT), Z=ORD(LIFE); FIL(T)=VNT(V,T)$(M(T)<YEARVAL(K_EOH)+ORD(JOT)+Z);
    YKK(YK(FIL(YEAR),LL),K)$((ORD(YEAR) < ORD(LL)+Z)$INVSPRED(K_EOH,JOT,LL,K)) = YES);
  CSTVPJ(R,V,P,'1',SYSINV,T(FIL)) = SUM(YKK(T,LL,K), F * MY_F * {
        macro.obj_icost("R", "K", "P", "CUR")
    })*SYSPLIT(SYSINV);
  CSTVPJ(R,V,P,'2',SYSINV,T(FIL))$({macro.obj_itax("R", "V", "P", "CUR")}+{
        macro.obj_isub("R", "V", "P", "CUR")
    }) =
       SUM(YKK(T,LL,K), F * ({macro.obj_itax("R", "K", "P", "CUR")}-{
        macro.obj_isub("R", "K", "P", "CUR")
    }))*SYSPLIT(SYSINV);
);

 IF(NOT CNT, FIL(V)=PYR_S(V); OPTION CSTVNT < CSTVPJ, CLEAR=CSTVPJ);
 {arg1}CST_INVC({arg2}R,V,T,P,SYSINV) $= CSTVNT('1',R,V,T,P,SYSINV);
 {arg1}CST_INVX({arg2}R,V,T,P,SYSINV) $= CSTVNT('2',R,V,T,P,SYSINV);

* Report approximate costs for RESID according to available capacity
LOOP(OBJ_ICUR(R,FIL(V),P,CUR)$PRC_RESID(R,'0',P),
 FIL2(T)=(NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T)-RTFORC(R,V,T,P))*OBJ_CRF(R,V,P,CUR);
 {arg1}CST_INVC({
        arg2
    }RTP_CPTYR(R,V,T,P),SYSINV) = ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)) * FIL2(T) * {
        macro.obj_icost("R", "V", "P", "CUR")
    };
 {arg1}CST_INVX({
        arg2
    }RTP_CPTYR(R,V,T,P),SYSINV) = ABS(SYSONE(SYSINV)-COEF_CRF(R,V,P,CUR)) * FIL2(T) * ({
        macro.obj_itax("R", "V", "P", "CUR")
    }-{macro.obj_isub("R", "V", "P", "CUR")});
);

* Handle ETL
{
        ""
        if etl != "YES"
        else (
            f'''
LOOP(OBJ_ICUR(R,T,TEG(P),CUR)$VAR_IC.L(R,T,P), OPTION CLEAR=YKK;
  F = VAR_IC.L(R,T,P) * OBJ_CRF(R,T,P,CUR)/OBJ_DIVI(R,T,P);
  LOOP((OBJ_SUMII(R,T,P,LIFE,K_EOH,JOT),INVSPRED(K_EOH,JOT,LL,K)),
    Z=ORD(LIFE); YKK(YK(TT,LL),K)$(YEARVAL(TT) < YEARVAL(LL)+Z) = YES);
  {arg1}CST_INVC({arg2}R,VNT(T,TT),P,SYSINV)$SYSONE(SYSINV) = {arg1}CST_INVC({arg2}R,T,TT,P,SYSINV)+SUM(YKK(TT,LL,K),F);
);
'''
        )
    }

*------------------------------------------------------------------------------
* Cases III - Decommissioning
*------------------------------------------------------------------------------
OPTION OBJ_SUMSI <= OBJ_SUMIII;
* Calculate decommissioning costs, annualized to operating years:
LOOP(OBJ_ICUR(NCAP_YES(R,V,P),CUR)${
        macro.obj_dcost("R", "V", "P", "CUR")
    }, F = RTP_CAPVL(R,V,P);
  F = F*OBJ_CRF(R,V,P,CUR)/OBJ_DIVIII(R,V,P); Z = ROUND(NCAP_{invlif}(R,V,P));
  {arg1}CST_DECC({
        arg2
    }R,VNT(V,T),P) = SUM(OBJ_SUMSI(R,V,P,LL)$((YEARVAL(T) < YEARVAL(LL)+Z)$YK(T,LL)),
      (SUM(OBJ_SUMIII(R,V,P,LL,K,Y),OBJ_DISC(R,Y,CUR)*{
        macro.obj_dcost("R", "K", "P", "CUR")
    })*COR_SALVD(R,V,P,CUR) +
       SUM(OBJ_SUMIVS(R,V,P,K(LL),Y),OBJ_DISC(R,Y,CUR))*{
        macro.obj_dlagc("R", "LL", "P", "CUR")
    })*F/OBJ_DISC(R,LL,CUR));
);

*------------------------------------------------------------------------------
* Cases IV - Fixed costs
*------------------------------------------------------------------------------
 IF(NOT ACL,OPTION CLEAR=FIL2,CLEAR=MY_FIL2;
   IF(CNT,NCAP_YES(OBJ_YES)=YES; NCAP_YES(R,PYR_S,P)$PRC_RESID(R,'0',P)=NO; FIL(PYR_S)=1;
   ELSE COEF_RVPT(NCAP_YES(RTP),T)$COEF_RVPT(RTP,T) = (1+RTP_CPX(RTP,T)$NCAP_CPX(RTP))/MAX(1,OBJ_DIVIV(RTP))));
 LOOP(OBJ_FCUR(NCAP_YES(R,V,P),CUR), F = RTP_CAPVL(R,V,P);
   OPTION CLEAR=YKAGE; MY_FIL2(T)=COEF_RVPT(R,V,P,T); MY_F = B(V)+NCAP_ILED(R,V,P);
   LOOP(OBJ_SUMIV(K_EOH,R,V,P,JOT,LIFE), Z=ORD(LIFE)-1;
     FIL2(T(YEAR))=ORD(YEAR)+(MAX(0,MY_F-M(T))-MAX(0,M(T)-MY_F-Z))$CNT;
     YKAGE(T,LL,AGE(LIFE+(FIL2(T)-ORD(LL)-Z)))$(INVSTEP(K_EOH,JOT,LL,JOT)$OPYEAR(LIFE,AGE)$MY_FIL2(T)) = YES);
   FIL2(T)=F*MY_FIL2(T)/MAX(1,SUM(YKAGE(T,LL,AGE),1)$CNT);
   CSTVPJ(R,V,P,'1','FIX',T) = FIL2(T) *
     SUM(YKAGE(T,K,AGE), {
        macro.obj_fom("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1)));
   CSTVPJ(R,V,P,'2','FIX',T)$({macro.obj_ftx("R", "V", "P", "CUR")}+{
        macro.obj_fsb("R", "V", "P", "CUR")
    }) = FIL2(T) *
     SUM(YKAGE(T,K,AGE), ({
        macro.obj_ftx("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1)) -
                          {
        macro.obj_fsb("R", "K", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),SHAPE(J,AGE)*MULTI(JJ,T)-1))));
 );
 OPTION CSTVNT < CSTVPJ, CLEAR=CSTVPJ;
 {arg1}CST_FIXC({arg2}R,V,T,P) $= CSTVNT('1',R,V,T,P,'FIX');
 {arg1}CST_FIXX({arg2}R,V,T,P) $= CSTVNT('2',R,V,T,P,'FIX');

* Report approximate costs for RESID according to available capacity
LOOP(OBJ_FCUR(R,FIL(V),P,CUR)$PRC_RESID(R,'0',P),
 {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P)) = NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T) * {
        macro.obj_fom("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'1',J,JJ),MULTI(JJ,T)-1));
 {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P)) = NCAP_PASTI(R,V,P)*COEF_RVPT(R,V,P,T) *({
        macro.obj_ftx("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'2',J,JJ),MULTI(JJ,T)-1)) -
                                                                          {
        macro.obj_fsb("R", "V", "P", "CUR")
    } * (1+SUM(RTP_SHAPE(R,V,P,'3',J,JJ),MULTI(JJ,T)-1)));
);

 IF(CARD(PRC_RCAP),
  COEF_CAP(RTP_CPTYR(R,V,T,P))$COEF_CAP(R,V,T,P) = 1-COEF_CAP(R,V,T,P)+EPS;
  {arg1}CST_FIXC({arg2}RTP_CPTYR(R,V,T,P)) $= COEF_CAP(R,V,T,P)*{arg1}CST_FIXC({
        arg2
    }R,V,T,P);
  {arg1}CST_FIXX({arg2}RTP_CPTYR(R,V,T,P)) $= COEF_CAP(R,V,T,P)*{arg1}CST_FIXX({
        arg2
    }R,V,T,P);
 );
 NCAP_YES(OBJ_YES)=YES;

*-----------------------------------------------------------------------------
* Marginal costs of endogenous trade
*-----------------------------------------------------------------------------
  OPTION CLEAR=OBJ_YES,CLEAR=CSTVNT,CLEAR=PAR_IPRIC;
  PAR_IPRIC(RTP(R,T,P),C,TS,'IMP') $= (-1) * EQ_IRE.M(R,T,P,C,'IMP',TS);
  CG_GRP(R,P,C,COM)$TOP_IRE(R,C,R,COM,P) = YES;
  LOOP(CG_GRP(REG,P,COM1,COM)$RPC_MARKET(REG,P,COM,'IMP'),
    PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'IMP')$TOP_IRE(REG,COM1,R,C,P) =
      -SUM((RS_TREE(R,ALL_TS,TS),S)$(IRE_TSCVT(R,ALL_TS,REG,S)$EQ_IRE.M(REG,T,P,COM,'IMP',S)),
               EQ_IRE.M(REG,T,P,COM,'IMP',S) *
               IRE_CCVT(REG,COM1,REG,COM) * IRE_CCVT(R,C,REG,COM1) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S)));

  PAR_XPRI(RTPCS_VARF(R,T,P,C,TS),REG,COM)$(TOP_IRE(R,C,REG,COM,P)$RPC_IREIO(R,P,C,'EXP','IN')) =
    SUM((RS_TREE(R,TS,ALL_TS),S)$(IRE_TSCVT(R,ALL_TS,REG,S)$EQ_IRE.M(REG,T,P,COM,'IMP',S)),
              EQ_IRE.M(REG,T,P,COM,'IMP',S) * IRE_FLO(R,T,P,C,REG,COM,S) *
              IRE_CCVT(R,C,REG,COM) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S));
  PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'EXP')$RPC_IREIO(R,P,C,'EXP','IN') $= SMAX(TOP_IRE(R,C,REG,COM,P),PAR_XPRI(R,T,P,C,TS,REG,COM));

  PAR_IPRIC(RTP(R,T,P),C,TS,'EXP') $= EQ_IRE.M(R,T,P,C,'EXP',TS);
  LOOP(RPC_EQIRE(REG,P,COM,'EXP'),
    PAR_IPRIC(RTPCS_VARF(R,T,P,C,TS),'IMP')$TOP_IRE(REG,COM,R,C,P) =
      -SUM((RS_TREE(R,ALL_TS,TS),S)$IRE_TSCVT(R,ALL_TS,REG,S),
               EQ_IRE.M(REG,T,P,COM,'EXP',S) / IRE_FLO(REG,T,P,COM,R,C,TS) *
               IRE_CCVT(R,C,REG,COM) * RS_FR(R,ALL_TS,TS) * IRE_TSCVT(R,ALL_TS,REG,S)));

  PRC_YMAX(RP_IRE(R,P)) $= SUM((RPC_IREIO(R,P,C,IE,'IN'),RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,S)),
                                PAR_IPRIC(R,T,P,C,S,IE)*PAR_IRE(R,V,T,P,C,S,IE));
  {arg1}REG_IREC({arg2}R) $= SUM(P,PRC_YMAX(R,P));
  PAR_IPRIC(R,T,P,C,TS,IE)$PAR_IPRIC(R,T,P,C,TS,IE) = PAR_IPRIC(R,T,P,C,TS,IE)*(1/COEF_PVT(R,T));
{
        f"{arg1}PAR_IPRIC({arg2}R,T,P,C,TS,IE) $= PAR_IPRIC(R,T,P,C,TS,IE);"
        if arg1 == "S"
        else ""
    }
  OPTION CLEAR=CG_GRP,CLEAR=PAR_OBJCAP,CLEAR=PAR_XPRI,CLEAR=RTP_OBJ,CLEAR=RTP_NPV,CLEAR=COEF_CRF,CLEAR=COEF_RVPT;

*------------------------------------------------------------------------------
* Marginal costs associated with endogenous imports/exports
* - note that price only applied when actually an internal region
*------------------------------------------------------------------------------
  {arg1}CST_IREC({arg2}RTP_VINTYR(R,V,T,P),C)$(RPC(R,P,C)$RP_IRE(R,P)) $=
     SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'IN')),PAR_IPRIC(R,T,P,C,S,IE)*PAR_IRE(R,V,T,P,C,S,IE));
*------------------------------------------------------------------------------
* EQOBJVAR the objective function variable cost reporting
*------------------------------------------------------------------------------
"""

    if anncost.upper() == "LEV":
        x1 = "LEV"
        tmp = "*(1/OBJ_PVT(R,T,CUR))"

    return_str += rf"""
{arg1}CST_TIME({arg2}R,T,ANNUAL,'{sysprefix}{x1}COST') = COEF_PVT(R,T);
"""

    if anncost.upper() != "LEV":
        return_str += eqobjvar_rpt(
            arg1="PAR",
            arg2="J('1'),",
            arg3="J('2'),",
            arg4="T",
            arg5="",
            pgprim=pgprim,
            tpulse=tpulse,
            tmp=tmp,
            stages=stages,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )

    return_str += rf"""
  {arg1}CST_ACTC({arg2}R,V,T,P,'-') $= SUM(CUR$PAR_ACTC('1',R,V,T,P,'{pgprim}',CUR),PAR_ACTC('1',R,V,T,P,'{pgprim}',CUR){tmp});
  {arg1}CST_ACTC({arg2}R,V,T,P,'+') $= SUM(CUR$PAR_ACTC('2',R,V,T,P,'{pgprim}',CUR),PAR_ACTC('2',R,V,T,P,'{pgprim}',CUR){tmp});
  {arg1}CST_FLOC({arg2}R,V,T,P,C) $= SUM(CUR$PAR_FLOC('1',R,V,T,P,C,CUR),PAR_FLOC('1',R,V,T,P,C,CUR){tmp});
  {arg1}CST_FLOX({arg2}R,V,T,P,C) $= SUM(CUR$PAR_FLOC('2',R,V,T,P,C,CUR),PAR_FLOC('2',R,V,T,P,C,CUR){tmp});
  {arg1}CST_COMC({arg2}R,T,C)     $= SUM(CUR$PAR_COMC('1',R,T,C,CUR),PAR_COMC('1',R,T,C,CUR){tmp});
  {arg1}CST_COMX({arg2}R,T,C)     $= SUM(CUR$PAR_COMC('2',R,T,C,CUR),PAR_COMC('2',R,T,C,CUR){tmp});
"""
    if is_obj_combal_defined:
        return_str += powerflo_vda_rptb(
            arg4=arg1,
            arg5=arg2,
            arg6=sow,
            var=var,
            vart=vart,
            sws=sws,
        )
    # *------------------------------------------------------------------------------
    # * EQOBJELS the objective function flexible demand cost reporting
    # *------------------------------------------------------------------------------
    return_str += eqobjels_rpt(
        arg1=f"{arg1}CST_COME({arg2}R,TT,C)",
        arg2="TT",
        arg3="",
        micro=micro,
        if_mi_agc_defined=is_mi_agc_defined,
    )

    return_str += rf"""
  IF(CARD({arg1}CST_PVP),
   {arg1}CST_PVC({arg2}'{sysprefix}ELS',R,C)$SUM(RCJ(R,C,'1',BDNEQ),1) = SUM(T,{
        arg1
    }CST_COME({arg2}R,T,C)*COEF_PVT(R,T));
   {arg1}CST_PVP({arg2}'{sysprefix}IRE',RP_IRE(RP)) $= PRC_YMAX(RP);
  );
*------------------------------------------------------------------------------
* Regional annual costs
  {arg1}REG_ACOST({arg2}R,T,'INV') =  SUM((VNT(V,T),P,SYSINV)${arg1}CST_INVC({
        arg2
    }R,V,T,P,SYSINV),{arg1}CST_INVC({arg2}R,V,T,P,SYSINV));
  {arg1}REG_ACOST({arg2}R,T,'INVX') = SUM((VNT(V,T),P,SYSINV)${arg1}CST_INVX({
        arg2
    }R,V,T,P,SYSINV),{arg1}CST_INVX({arg2}R,V,T,P,SYSINV));
  {arg1}REG_ACOST({arg2}R,T,'FIX') =  SUM((VNT(V,T),P)${arg1}CST_FIXC({arg2}R,V,T,P),{
        arg1
    }CST_FIXC({arg2}R,V,T,P));
  {arg1}REG_ACOST({arg2}R,T,'FIXX') = SUM((VNT(V,T),P)${arg1}CST_FIXX({arg2}R,V,T,P),{
        arg1
    }CST_FIXX({arg2}R,V,T,P));
  {arg1}REG_ACOST({arg2}R,T,'VAR') =  SUM((VNT(V,T),P,RPM)${arg1}CST_ACTC({
        arg2
    }R,V,T,P,RPM),{arg1}CST_ACTC({arg2}R,V,T,P,RPM)) +
                              SUM((VNT(V,T),P,C)${arg1}CST_FLOC({arg2}R,V,T,P,C),{
        arg1
    }CST_FLOC({arg2}R,V,T,P,C)) +
                              SUM(C${arg1}CST_COMC({arg2}R,T,C),{arg1}CST_COMC({
        arg2
    }R,T,C));
  {arg1}REG_ACOST({arg2}R,T,'VARX') = SUM((VNT(V,T),P,C)${arg1}CST_FLOX({
        arg2
    }R,V,T,P,C),{arg1}CST_FLOX({arg2}R,V,T,P,C)) +
                              SUM(C${arg1}CST_COMX({arg2}R,T,C),{arg1}CST_COMX({
        arg2
    }R,T,C));
  {arg1}REG_ACOST({arg2}R,T,'IRE') =  SUM((VNT(V,T),P,C)${arg1}CST_IREC({
        arg2
    }R,V,T,P,C),{arg1}CST_IREC({arg2}R,V,T,P,C));
  {arg1}REG_ACOST({arg2}R,T,'ELS') =  SUM(C${arg1}CST_COME({arg2}R,T,C),{arg1}CST_COME({
        arg2
    }R,T,C));
*------------------------------------------------------------------------------
  OPTION CLEAR=PAR_ACTC,CLEAR=PAR_COMC,CLEAR=PAR_FLOC,CLEAR=PRC_YMAX,CLEAR=PASTSUM;
{
        ""
        if arg1 == "S"
        else (
            f'''
*------------------------------------------------------------------------------
* Salvage costs (not for stochastic runs)
*------------------------------------------------------------------------------
* Calculate actual Salvage values
  PAR_OBJSAL(OBJ_ICUR(R,T,P,CUR)) = PAR_OBJSAL(R,T,P,CUR)*VAR_NCAP.L(R,T,P);
  {"PAR_OBJSAL(RTP(R,T,TEG(P)),CUR)$G_RCUR(R,CUR) = PAR_OBJSAL(RTP,CUR)+SUM(OBJ_SUMS(RTP),OBJSIC(RTP)*VAR_IC.L(RTP))*OBJ_DCEOH(R,CUR);" if etl == "YES" else ""}
  {arg1}CST_SALV({arg2}R,T,P) $= SUM(RDCUR(R,CUR),PAR_OBJSAL(R,T,P,CUR));
  REG_OBJ(R) = SUM((RDCUR(R,CUR),ITEM,OBV)$SUM_OBJ(ITEM,OBV),VAR_OBJ.L(R,OBV,CUR)*SUM_OBJ(ITEM,OBV));
'''
        )
    }
"""
    return return_str
