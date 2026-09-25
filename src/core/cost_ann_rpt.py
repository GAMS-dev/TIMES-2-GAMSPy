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

from gamspy import Domain, Loop, Number, Ord, Smax, SpecialValues, Sum, sparse
from gamspy.math import Max, Round, abs, aggregate, project

from core.base_class import GamsClass
from core.eqobjels_rpt import EqobjelsRpt, EqobjelsRptConfig, eqobjels_rpt
from core.eqobjvar_rpt import EqobjvarRpt, EqobjvarRptConfig, eqobjvar_rpt
from core.powerflo_vda import PowerfloVda, powerflo_vda_rptb
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set

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


def arg2_repr(arg2: tuple[Set | Alias | str, ...] | tuple[()]) -> str:
    """GAMS text of the %2 index prefix, e.g. ('1',) -> "'1'," and (SOW,) -> "SOW,"."""
    return "".join(f"'{a}'," if isinstance(a, str) else f"{a.name}," for a in arg2)


class CostAnnRpt(GamsClass):
    """Translation unit for cost_ann.rpt."""

    # Instance attributes
    module_name: str = "cost_ann_rpt"
    gams_source: str = "cost_ann.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: CostAnnRptConfig | None = None,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config if config is not None else CostAnnRptConfig()
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        self.tc.enqueue(self.exec_levelized_costs, arg1=cc.arg1, arg2=cc.arg2)

        # *----------------------------------------------------------------------
        # * Cases I - Investment Cost and II - Taxes/Subsidies
        # *----------------------------------------------------------------------
        # $SET TMP '' SET X1 '' SETLOCAL SIC 1
        self.env.set_scoped("tmp", "")
        self.env.set_scoped("tmp_GP", 1)
        self.env.set_scoped("x1", "")
        self.env.set_local("sic", "1")
        self.env.set_local("sic_GP", 1)

        if self.env.stages.upper() == "YES":
            self.tc.enqueue(self.exec_pastsum)
            self.env.set_local("sic", "1+PASTSUM(R,V,P)")
            self.env.set_local("sic_GP", 1 + g.pastsum[g.r, g.v, g.p])

        self.tc.enqueue(
            self.exec_investment_costs,
            arg1=cc.arg1,
            arg2=cc.arg2,
            sic_GP=self.env.sic_GP,
            etl=self.env.etl,
        )
        self.tc.enqueue(
            self.exec_decommissioning,
            arg1=cc.arg1,
            arg2=cc.arg2,
            invlif=self.env.invlif,
        )
        self.tc.enqueue(self.exec_fixed_costs, arg1=cc.arg1, arg2=cc.arg2)
        self.tc.enqueue(self.exec_trade_marginals, arg1=cc.arg1, arg2=cc.arg2)

        # *----------------------------------------------------------------------
        # * EQOBJVAR the objective function variable cost reporting
        # *----------------------------------------------------------------------
        if self.env.anncost.upper() == "LEV":
            self.env.set_scoped("x1", "LEV")
            self.env.set_scoped("tmp", "*(1/OBJ_PVT(R,T,CUR))")
            self.env.set_scoped("tmp_GP", 1 / g.obj_pvt[g.r, g.t, g.cur])

        self.tc.enqueue(
            self.exec_cst_time,
            arg1=cc.arg1,
            arg2=cc.arg2,
            sysprefix=self.env.sysprefix,
            x1=self.env.x1,
        )

        if self.env.anncost.upper() != "LEV":
            self.include(
                EqobjvarRpt(
                    self.tc,
                    self.env,
                    config=EqobjvarRptConfig(
                        arg1="PAR",
                        arg2=(g.j["1"],),
                        arg3=(g.j["2"],),
                        arg4=g.t,
                    ),
                )
            )

        self.tc.enqueue(
            self.exec_variable_costs,
            arg1=cc.arg1,
            arg2=cc.arg2,
            tmp_GP=self.env.tmp_GP,
            pgprim=self.env.pgprim,
        )

        if self.tc.defined("OBJ_COMBAL"):
            self.include(
                PowerfloVda(
                    self.tc,
                    self.env,
                    arg1="RPTB",
                    arg2="",
                    arg3="",
                    arg4=cc.arg1,
                    arg5=arg2_repr(cc.arg2),
                    arg6=self.env.sow,
                )
            )

        # *----------------------------------------------------------------------
        # * EQOBJELS the objective function flexible demand cost reporting
        # *----------------------------------------------------------------------
        self.include(
            EqobjelsRpt(
                self.tc,
                self.env,
                config=EqobjelsRptConfig(
                    arg1=g.get_parameter(f"{cc.arg1}CST_COME")[
                        *cc.arg2, g.r, g.tt, g.c
                    ],
                    arg2=g.tt,
                ),
            )
        )

        self.tc.enqueue(
            self.exec_regional_costs,
            arg1=cc.arg1,
            arg2=cc.arg2,
            sysprefix=self.env.sysprefix,
        )

        # $IF %1==S $EXIT
        if cc.arg1 != "S":
            self.tc.enqueue(
                self.exec_salvage_costs,
                arg1=cc.arg1,
                arg2=cc.arg2,
                etl=self.env.etl,
            )

    def exec_levelized_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc
        r, v, t, p, j, cur = g.r, g.v, g.t, g.p, g.j, g.cur
        ObjYes, NcapYes, RtpCptyr, ObjIcur, ObjFcur, PrcRcap, Sysinv, Rdcur = (
            g.ObjYes,
            g.NcapYes,
            g.RtpCptyr,
            g.ObjIcur,
            g.ObjFcur,
            g.PrcRcap,
            g.Sysinv,
            g.Rdcur,
        )
        acl, cnt, coef_cap, coef_cpt, coef_crf, par_objcap, rpt_opt = (
            g.acl,
            g.cnt,
            g.coef_cap,
            g.coef_cpt,
            g.coef_crf,
            g.par_objcap,
            g.rpt_opt,
        )
        obj_pvt, rtp_capvl, rtp_npv, rtp_obj, sysone, VAR_SCAP = (
            g.obj_pvt,
            g.rtp_capvl,
            g.rtp_npv,
            g.rtp_obj,
            g.sysone,
            g.VAR_SCAP,
        )
        CST_FIXC = g.get_parameter(f"{arg1}CST_FIXC")
        CST_FIXX = g.get_parameter(f"{arg1}CST_FIXX")
        CST_INVC = g.get_parameter(f"{arg1}CST_INVC")
        CST_INVX = g.get_parameter(f"{arg1}CST_INVX")

        ObjYes[NcapYes[r, v, p]] = True
        coef_cap.setRecords(None)
        cnt[...] = Number(1).where[Round(rpt_opt["OBJ", "2"])]
        coef_cap[RtpCptyr[r, v, t, p]].where[NcapYes[r, v, p] & PrcRcap[r, p]] = (
            VAR_SCAP[r, v, t, p].l / rtp_capvl[r, v, p]
        )
        # * Levelized annual investment and fixed costs
        if cnt.toValue():
            par_objcap.setRecords(None)
            par_objcap[ObjIcur[NcapYes[r, v, p], cur]] = Sum(
                RtpCptyr[r, v, t, p], coef_cpt[r, v, t, p] * obj_pvt[r, t, cur]
            )
            rtp_obj[j, r, v, p, cur].where[rtp_obj[j, r, v, p, cur]] = (
                rtp_obj[j, r, v, p, cur] / par_objcap[r, v, p, cur]
            ).where[par_objcap[r, v, p, cur]]
            CST_INVC[*arg2, RtpCptyr[r, v, t, p], Sysinv].where[NcapYes[r, v, p]] = Sum(
                Rdcur[r, cur],
                rtp_obj["1", r, v, p, cur]
                * coef_cpt[r, v, t, p]
                * abs(sysone[Sysinv] - coef_crf[r, v, p, cur]),
            )
            CST_INVX[*arg2, RtpCptyr[r, v, t, p], Sysinv].where[NcapYes[r, v, p]] = Sum(
                Rdcur[r, cur],
                rtp_obj["2", r, v, p, cur]
                * coef_cpt[r, v, t, p]
                * abs(sysone[Sysinv] - coef_crf[r, v, p, cur]),
            )
            if acl.toValue():
                par_objcap[ObjFcur[NcapYes[r, v, p], cur]] = Sum(
                    RtpCptyr[r, v, t, p],
                    coef_cpt[r, v, t, p]
                    * (1 - coef_cap[r, v, t, p])
                    * obj_pvt[r, t, cur],
                )
                rtp_npv[j, r, v, p, cur].where[rtp_npv[j, r, v, p, cur]] = (
                    rtp_npv[j, r, v, p, cur] / par_objcap[r, v, p, cur]
                ).where[par_objcap[r, v, p, cur]]
                CST_FIXC[*arg2, RtpCptyr[r, v, t, p]].where[NcapYes[r, v, p]] = Sum(
                    Rdcur[r, cur],
                    rtp_npv["1", r, v, p, cur]
                    * coef_cpt[r, v, t, p]
                    * (1 - coef_cap[r, v, t, p]),
                )
                CST_FIXX[*arg2, RtpCptyr[r, v, t, p]].where[NcapYes[r, v, p]] = Sum(
                    Rdcur[r, cur],
                    rtp_npv["2", r, v, p, cur]
                    * coef_cpt[r, v, t, p]
                    * (1 - coef_cap[r, v, t, p]),
                )
                coef_cap.setRecords(None)
            NcapYes.setRecords(None)

    def exec_pastsum(self: CostAnnRpt) -> None:
        g = self.tc

        g.pastsum[g.NcapYes[g.r, g.t, g.p]] = Sum(
            g.SwTsw[g.Sow, g.t, g.ww], g.obj_sic[g.r, g.t, g.p, g.ww]
        )

    def exec_investment_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        sic_GP: Expression | int,
        etl: str,
    ) -> None:
        g = self.tc

        r, v, t, tt, p, k, ll, year, cur = (
            g.r,
            g.v,
            g.t,
            g.tt,
            g.p,
            g.k,
            g.ll,
            g.year,
            g.cur,
        )
        Fil, Invspred, NcapYes, ObjIcur, ObjSumii, PyrS, RtpCptyr = (
            g.Fil,
            g.Invspred,
            g.NcapYes,
            g.ObjIcur,
            g.ObjSumii,
            g.PyrS,
            g.RtpCptyr,
        )
        Sysinv, Teg, Vnt, Yk, Ykk = g.Sysinv, g.Teg, g.Vnt, g.Yk, g.Ykk
        jot, KEoh, life = g.jot, g.KEoh, g.life
        cnt, coef_crf, coef_cpt, coef_rvpt, cstvnt, cstvpj, f, fil2, m, my_f = (
            g.cnt,
            g.coef_crf,
            g.coef_cpt,
            g.coef_rvpt,
            g.cstvnt,
            g.cstvpj,
            g.f,
            g.fil2,
            g.m,
            g.my_f,
        )
        ncap_pasti, obj_crf, obj_divi, prc_resid, rtforc, rtp_capvl = (
            g.ncap_pasti,
            g.obj_crf,
            g.obj_divi,
            g.prc_resid,
            g.rtforc,
            g.rtp_capvl,
        )
        sysone, sysplit, yearval, z, VAR_IC = (
            g.sysone,
            g.sysplit,
            g.yearval,
            g.z,
            g.VAR_IC,
        )
        CST_INVC = g.get_parameter(f"{arg1}CST_INVC")
        CST_INVX = g.get_parameter(f"{arg1}CST_INVX")

        # * Calculate Annual undiscounted investment costs CST_INVC
        levelized = bool(cnt.toValue())
        Fil.setRecords(None)
        aggregate(source=coef_cpt, target=coef_rvpt, direction="left")
        if not levelized:
            NcapYes[r, PyrS, p].where[prc_resid[r, "0", p]] = False

        with Loop(ObjIcur[NcapYes[r, v, p], cur]):
            Ykk.setRecords(None)
            my_f[...] = sic_GP
            sysplit[Sysinv] = abs(sysone[Sysinv] - coef_crf[r, v, p, cur])
            f[...] = rtp_capvl[r, v, p] * obj_crf[r, v, p, cur] / obj_divi[r, v, p]
            with Loop(ObjSumii[r, v, p, life, KEoh, jot]):
                z[...] = Ord(life)
                Fil[t] = Vnt[v, t].where[m[t] < yearval[KEoh] + Ord(jot) + z]
                Ykk[Yk[Fil[year], ll], k].where[
                    (Ord(year) < Ord(ll) + z) & Invspred[KEoh, jot, ll, k]
                ] = True
            cstvpj[r, v, p, "1", Sysinv, t[Fil]] = (
                Sum(Ykk[t, ll, k], f * my_f * macro.obj_icost_GP(r, k, p, cur))
                * sysplit[Sysinv]
            )
            cstvpj[r, v, p, "2", Sysinv, t[Fil]].where[
                macro.obj_itax_GP(r, v, p, cur) + macro.obj_isub_GP(r, v, p, cur)
            ] = (
                Sum(
                    Ykk[t, ll, k],
                    f
                    * (
                        macro.obj_itax_GP(r, k, p, cur)
                        - macro.obj_isub_GP(r, k, p, cur)
                    ),
                )
                * sysplit[Sysinv]
            )

        if not levelized:
            Fil[v] = PyrS[v]
            project(source=cstvpj, target=cstvnt)  # type: ignore[arg-type]
            cstvpj.setRecords(None)
        CST_INVC[*arg2, r, v, t, p, Sysinv] = sparse(cstvnt["1", r, v, t, p, Sysinv])
        CST_INVX[*arg2, r, v, t, p, Sysinv] = sparse(cstvnt["2", r, v, t, p, Sysinv])

        # * Report approximate costs for RESID according to available capacity
        with Loop(ObjIcur[r, Fil[v], p, cur].where[prc_resid[r, "0", p]]):
            fil2[t] = (
                ncap_pasti[r, v, p] * coef_rvpt[r, v, p, t] - rtforc[r, v, t, p]
            ) * obj_crf[r, v, p, cur]
            CST_INVC[*arg2, RtpCptyr[r, v, t, p], Sysinv] = (
                abs(sysone[Sysinv] - coef_crf[r, v, p, cur])
                * fil2[t]
                * macro.obj_icost_GP(r, v, p, cur)
            )
            CST_INVX[*arg2, RtpCptyr[r, v, t, p], Sysinv] = (
                abs(sysone[Sysinv] - coef_crf[r, v, p, cur])
                * fil2[t]
                * (macro.obj_itax_GP(r, v, p, cur) - macro.obj_isub_GP(r, v, p, cur))
            )

        # * Handle ETL
        if etl == "YES":
            with Loop(ObjIcur[r, t, Teg[p], cur].where[VAR_IC[r, t, p].l]):
                Ykk.setRecords(None)
                f[...] = VAR_IC[r, t, p].l * obj_crf[r, t, p, cur] / obj_divi[r, t, p]
                with Loop(
                    Domain(
                        ObjSumii[r, t, p, life, KEoh, jot], Invspred[KEoh, jot, ll, k]
                    )
                ):
                    z[...] = Ord(life)
                    Ykk[Yk[tt, ll], k].where[yearval[tt] < yearval[ll] + z] = True
                CST_INVC[*arg2, r, Vnt[t, tt], p, Sysinv].where[sysone[Sysinv]] = (
                    CST_INVC[*arg2, r, t, tt, p, Sysinv] + Sum(Ykk[tt, ll, k], f)
                )

    def exec_decommissioning(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        invlif: str,
    ) -> None:
        g = self.tc

        r, v, t, p, k, ll, cur, Y = g.r, g.v, g.t, g.p, g.k, g.ll, g.cur, g.Y
        NcapYes, ObjIcur, ObjSumsi, ObjSumiii, ObjSumivs, Vnt, Yk = (
            g.NcapYes,
            g.ObjIcur,
            g.ObjSumsi,
            g.ObjSumiii,
            g.ObjSumivs,
            g.Vnt,
            g.Yk,
        )
        cor_salvd, f, obj_crf, obj_disc, obj_diviii, rtp_capvl, yearval, z = (
            g.cor_salvd,
            g.f,
            g.obj_crf,
            g.obj_disc,
            g.obj_diviii,
            g.rtp_capvl,
            g.yearval,
            g.z,
        )
        NCAP_INVLIF = g.get_parameter(f"NCAP_{invlif}")
        CST_DECC = g.get_parameter(f"{arg1}CST_DECC")

        project(source=ObjSumiii, target=ObjSumsi, direction="left")
        # * Calculate decommissioning costs, annualized to operating years:
        with Loop(
            ObjIcur[NcapYes[r, v, p], cur].where[macro.obj_dcost_GP(r, v, p, cur)]
        ):
            f[...] = rtp_capvl[r, v, p]
            f[...] = f * obj_crf[r, v, p, cur] / obj_diviii[r, v, p]
            z[...] = Round(NCAP_INVLIF[r, v, p])
            CST_DECC[*arg2, r, Vnt[v, t], p] = Sum(
                ObjSumsi[r, v, p, ll].where[(yearval[t] < yearval[ll] + z) & Yk[t, ll]],
                (
                    Sum(
                        ObjSumiii[r, v, p, ll, k, Y],
                        obj_disc[r, Y, cur] * macro.obj_dcost_GP(r, k, p, cur),
                    )
                    * cor_salvd[r, v, p, cur]
                    + Sum(ObjSumivs[r, v, p, k[ll], Y], obj_disc[r, Y, cur])
                    * macro.obj_dlagc_GP(r, ll, p, cur)
                )
                * f
                / obj_disc[r, ll, cur],
            )

    def exec_fixed_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc

        r, v, t, p, j, jj, k, ll, year, cur, age = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.j,
            g.jj,
            g.k,
            g.ll,
            g.year,
            g.cur,
            g.age,
        )
        Fil, Invstep, NcapYes, ObjFcur, ObjSumiv, ObjYes, Opyear, PrcRcap = (
            g.Fil,
            g.Invstep,
            g.NcapYes,
            g.ObjFcur,
            g.ObjSumiv,
            g.ObjYes,
            g.Opyear,
            g.PrcRcap,
        )
        PyrS, Rtp, RtpCptyr, RtpShape, Ykage, KEoh, jot, life = (
            g.PyrS,
            g.Rtp,
            g.RtpCptyr,
            g.RtpShape,
            g.Ykage,
            g.KEoh,
            g.jot,
            g.life,
        )
        acl, b, cnt, coef_cap, coef_rvpt, cstvnt, cstvpj, f, fil2, m, my_f = (
            g.acl,
            g.b,
            g.cnt,
            g.coef_cap,
            g.coef_rvpt,
            g.cstvnt,
            g.cstvpj,
            g.f,
            g.fil2,
            g.m,
            g.my_f,
        )
        multi, my_fil2, ncap_cpx, ncap_iled, ncap_pasti = (
            g.multi,
            g.my_fil2,
            g.ncap_cpx,
            g.ncap_iled,
            g.ncap_pasti,
        )
        obj_diviv, prc_resid, rtp_capvl, rtp_cpx, shape, z = (
            g.obj_diviv,
            g.prc_resid,
            g.rtp_capvl,
            g.rtp_cpx,
            g.shape,
            g.z,
        )
        CST_FIXC = g.get_parameter(f"{arg1}CST_FIXC")
        CST_FIXX = g.get_parameter(f"{arg1}CST_FIXX")

        if not acl.toValue():
            fil2.setRecords(None)
            my_fil2.setRecords(None)
            if cnt.toValue():
                NcapYes[ObjYes[r, v, p]] = True
                NcapYes[r, PyrS, p].where[prc_resid[r, "0", p]] = False
                Fil[PyrS] = True
            else:
                coef_rvpt[NcapYes[Rtp], t].where[coef_rvpt[Rtp, t]] = (
                    1 + rtp_cpx[Rtp, t].where[ncap_cpx[Rtp]]
                ) / Max(1, obj_diviv[Rtp])

        with Loop(ObjFcur[NcapYes[r, v, p], cur]):
            f[...] = rtp_capvl[r, v, p]
            Ykage.setRecords(None)
            my_fil2[t] = coef_rvpt[r, v, p, t]
            my_f[...] = b[v] + ncap_iled[r, v, p]
            with Loop(ObjSumiv[KEoh, r, v, p, jot, life]):
                z[...] = Ord(life) - 1
                fil2[t[year]] = (
                    Ord(year)
                    + (Max(0, my_f - m[year]) - Max(0, m[year] - my_f - z)).where[cnt]
                )
                Ykage[t, ll, age[life + (fil2[t] - Ord(ll) - z)]].where[
                    Invstep[KEoh, jot, ll, jot] & Opyear[life, age] & my_fil2[t]
                ] = True
            fil2[t] = f * my_fil2[t] / Max(1, Sum(Ykage[t, ll, age], 1).where[cnt])
            cstvpj[r, v, p, "1", "FIX", t] = fil2[t] * Sum(
                Ykage[t, k, age],
                macro.obj_fom_GP(r, k, p, cur)
                * (
                    1
                    + Sum(
                        RtpShape[r, v, p, "1", j, jj],
                        shape[j, age] * multi[jj, t] - 1,
                    )
                ),
            )
            cstvpj[r, v, p, "2", "FIX", t].where[
                macro.obj_ftx_GP(r, v, p, cur) + macro.obj_fsb_GP(r, v, p, cur)
            ] = fil2[t] * Sum(
                Ykage[t, k, age],
                macro.obj_ftx_GP(r, k, p, cur)
                * (
                    1
                    + Sum(
                        RtpShape[r, v, p, "2", j, jj],
                        shape[j, age] * multi[jj, t] - 1,
                    )
                )
                - macro.obj_fsb_GP(r, k, p, cur)
                * (
                    1
                    + Sum(
                        RtpShape[r, v, p, "3", j, jj],
                        shape[j, age] * multi[jj, t] - 1,
                    )
                ),
            )

        project(source=cstvpj, target=cstvnt)  # type: ignore[arg-type]
        cstvpj.setRecords(None)
        CST_FIXC[*arg2, r, v, t, p] = sparse(cstvnt["1", r, v, t, p, "FIX"])
        CST_FIXX[*arg2, r, v, t, p] = sparse(cstvnt["2", r, v, t, p, "FIX"])

        # * Report approximate costs for RESID according to available capacity
        with Loop(ObjFcur[r, Fil[v], p, cur].where[prc_resid[r, "0", p]]):
            CST_FIXC[*arg2, RtpCptyr[r, v, t, p]] = (
                ncap_pasti[r, v, p]
                * coef_rvpt[r, v, p, t]
                * macro.obj_fom_GP(r, v, p, cur)
                * (1 + Sum(RtpShape[r, v, p, "1", j, jj], multi[jj, t] - 1))
            )
            CST_FIXX[*arg2, RtpCptyr[r, v, t, p]] = (
                ncap_pasti[r, v, p]
                * coef_rvpt[r, v, p, t]
                * (
                    macro.obj_ftx_GP(r, v, p, cur)
                    * (1 + Sum(RtpShape[r, v, p, "2", j, jj], multi[jj, t] - 1))
                    - macro.obj_fsb_GP(r, v, p, cur)
                    * (1 + Sum(RtpShape[r, v, p, "3", j, jj], multi[jj, t] - 1))
                )
            )

        if PrcRcap.number_records:
            coef_cap[RtpCptyr[r, v, t, p]].where[coef_cap[r, v, t, p]] = (
                1 - coef_cap[r, v, t, p] + SpecialValues.EPS
            )
            CST_FIXC[*arg2, RtpCptyr[r, v, t, p]] = sparse(
                coef_cap[r, v, t, p] * CST_FIXC[*arg2, r, v, t, p]
            )
            CST_FIXX[*arg2, RtpCptyr[r, v, t, p]] = sparse(
                coef_cap[r, v, t, p] * CST_FIXX[*arg2, r, v, t, p]
            )
        NcapYes[ObjYes[r, v, p]] = True

    def exec_trade_marginals(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc

        r, v, t, p, c, s, ts, allts, ie, Reg, Com, com1 = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.ts,
            g.allts,
            g.ie,
            g.Reg,
            g.Com,
            g.com1,
        )
        CgGrp, ObjYes, RpIre, RpcEqire, RpcIreio, RpcMarket, Rpc = (
            g.CgGrp,
            g.ObjYes,
            g.RpIre,
            g.RpcEqire,
            g.RpcIreio,
            g.RpcMarket,
            g.Rpc,
        )
        RpcsVar, Rtp, RtpVintyr, RtpcsVarf, RsTree, TopIre = (
            g.RpcsVar,
            g.Rtp,
            g.RtpVintyr,
            g.RtpcsVarf,
            g.RsTree,
            g.TopIre,
        )
        coef_crf, coef_pvt, coef_rvpt, cstvnt, eq_ire, ire_ccvt, ire_flo = (
            g.coef_crf,
            g.coef_pvt,
            g.coef_rvpt,
            g.cstvnt,
            g.eq_ire,
            g.ire_ccvt,
            g.ire_flo,
        )
        ire_tscvt, par_ipric, par_ire, par_objcap, par_xpri = (
            g.ire_tscvt,
            g.par_ipric,
            g.par_ire,
            g.par_objcap,
            g.par_xpri,
        )
        prc_ymax, rs_fr, rtp_npv, rtp_obj = (
            g.prc_ymax,
            g.rs_fr,
            g.rtp_npv,
            g.rtp_obj,
        )
        CST_IREC = g.get_parameter(f"{arg1}CST_IREC")
        REG_IREC = g.get_parameter(f"{arg1}REG_IREC")

        ObjYes.setRecords(None)
        cstvnt.setRecords(None)
        par_ipric.setRecords(None)
        par_ipric[Rtp[r, t, p], c, ts, "IMP"] = sparse(
            (-1) * eq_ire[r, t, p, c, "IMP", ts].m
        )
        CgGrp[r, p, c, Com].where[TopIre[r, c, r, Com, p]] = True
        with Loop(CgGrp[Reg, p, com1, Com].where[RpcMarket[Reg, p, Com, "IMP"]]):
            par_ipric[RtpcsVarf[r, t, p, c, ts], "IMP"].where[
                TopIre[Reg, com1, r, c, p]
            ] = -Sum(
                Domain(RsTree[r, allts, ts], s).where[
                    ire_tscvt[r, allts, Reg, s] & eq_ire[Reg, t, p, Com, "IMP", s].m
                ],
                eq_ire[Reg, t, p, Com, "IMP", s].m
                * ire_ccvt[Reg, com1, Reg, Com]
                * ire_ccvt[r, c, Reg, com1]
                * rs_fr[r, allts, ts]
                * ire_tscvt[r, allts, Reg, s],
            )

        par_xpri[RtpcsVarf[r, t, p, c, ts], Reg, Com].where[
            TopIre[r, c, Reg, Com, p] & RpcIreio[r, p, c, "EXP", "IN"]
        ] = Sum(
            Domain(RsTree[r, ts, allts], s).where[
                ire_tscvt[r, allts, Reg, s] & eq_ire[Reg, t, p, Com, "IMP", s].m
            ],
            eq_ire[Reg, t, p, Com, "IMP", s].m
            * ire_flo[r, t, p, c, Reg, Com, s]
            * ire_ccvt[r, c, Reg, Com]
            * rs_fr[r, allts, ts]
            * ire_tscvt[r, allts, Reg, s],
        )
        par_ipric[RtpcsVarf[r, t, p, c, ts], "EXP"].where[
            RpcIreio[r, p, c, "EXP", "IN"]
        ] = sparse(Smax(TopIre[r, c, Reg, Com, p], par_xpri[r, t, p, c, ts, Reg, Com]))

        par_ipric[Rtp[r, t, p], c, ts, "EXP"] = sparse(eq_ire[r, t, p, c, "EXP", ts].m)
        with Loop(RpcEqire[Reg, p, Com, "EXP"]):
            par_ipric[RtpcsVarf[r, t, p, c, ts], "IMP"].where[
                TopIre[Reg, Com, r, c, p]
            ] = -Sum(
                Domain(RsTree[r, allts, ts], s).where[ire_tscvt[r, allts, Reg, s]],
                eq_ire[Reg, t, p, Com, "EXP", s].m
                / ire_flo[Reg, t, p, Com, r, c, ts]
                * ire_ccvt[r, c, Reg, Com]
                * rs_fr[r, allts, ts]
                * ire_tscvt[r, allts, Reg, s],
            )

        prc_ymax[RpIre[r, p]] = sparse(
            Sum(
                Domain(
                    RpcIreio[r, p, c, ie, "IN"],
                    RtpVintyr[r, v, t, p],
                    RpcsVar[r, p, c, s],
                ),
                par_ipric[r, t, p, c, s, ie] * par_ire[r, v, t, p, c, s, ie],
            )
        )
        REG_IREC[*arg2, r] = sparse(Sum(p, prc_ymax[r, p]))
        par_ipric[r, t, p, c, ts, ie].where[par_ipric[r, t, p, c, ts, ie]] = par_ipric[
            r, t, p, c, ts, ie
        ] * (1 / coef_pvt[r, t])
        if arg1 == "S":
            PAR_IPRIC = g.get_parameter(f"{arg1}PAR_IPRIC")
            PAR_IPRIC[*arg2, r, t, p, c, ts, ie] = sparse(par_ipric[r, t, p, c, ts, ie])
        CgGrp.setRecords(None)
        par_objcap.setRecords(None)
        par_xpri.setRecords(None)
        rtp_obj.setRecords(None)
        rtp_npv.setRecords(None)
        coef_crf.setRecords(None)
        coef_rvpt.setRecords(None)

        # *----------------------------------------------------------------------
        # * Marginal costs associated with endogenous imports/exports
        # * - note that price only applied when actually an internal region
        # *----------------------------------------------------------------------
        CST_IREC[*arg2, RtpVintyr[r, v, t, p], c].where[Rpc[r, p, c] & RpIre[r, p]] = (
            sparse(
                Sum(
                    Domain(RtpcsVarf[r, t, p, c, s], RpcIreio[r, p, c, ie, "IN"]),
                    par_ipric[r, t, p, c, s, ie] * par_ire[r, v, t, p, c, s, ie],
                )
            )
        )

    def exec_cst_time(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        sysprefix: str,
        x1: str,
    ) -> None:
        g = self.tc

        CST_TIME = g.get_parameter(f"{arg1}CST_TIME")
        CST_TIME[*arg2, g.r, g.t, g.Annual, f"{sysprefix}{x1}COST"] = g.coef_pvt[
            g.r, g.t
        ]

    def exec_variable_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        tmp_GP: Expression | int,
        pgprim: str,
    ) -> None:
        g = self.tc

        r, v, t, p, c, cur = g.r, g.v, g.t, g.p, g.c, g.cur
        par_actc, par_comc, par_floc = g.par_actc, g.par_comc, g.par_floc
        CST_ACTC = g.get_parameter(f"{arg1}CST_ACTC")
        CST_COMC = g.get_parameter(f"{arg1}CST_COMC")
        CST_COMX = g.get_parameter(f"{arg1}CST_COMX")
        CST_FLOC = g.get_parameter(f"{arg1}CST_FLOC")
        CST_FLOX = g.get_parameter(f"{arg1}CST_FLOX")

        CST_ACTC[*arg2, r, v, t, p, "-"] = sparse(
            Sum(
                cur.where[par_actc["1", r, v, t, p, pgprim, cur]],
                par_actc["1", r, v, t, p, pgprim, cur] * tmp_GP,
            )
        )
        CST_ACTC[*arg2, r, v, t, p, "+"] = sparse(
            Sum(
                cur.where[par_actc["2", r, v, t, p, pgprim, cur]],
                par_actc["2", r, v, t, p, pgprim, cur] * tmp_GP,
            )
        )
        CST_FLOC[*arg2, r, v, t, p, c] = sparse(
            Sum(
                cur.where[par_floc["1", r, v, t, p, c, cur]],
                par_floc["1", r, v, t, p, c, cur] * tmp_GP,
            )
        )
        CST_FLOX[*arg2, r, v, t, p, c] = sparse(
            Sum(
                cur.where[par_floc["2", r, v, t, p, c, cur]],
                par_floc["2", r, v, t, p, c, cur] * tmp_GP,
            )
        )
        CST_COMC[*arg2, r, t, c] = sparse(
            Sum(
                cur.where[par_comc["1", r, t, c, cur]],
                par_comc["1", r, t, c, cur] * tmp_GP,
            )
        )
        CST_COMX[*arg2, r, t, c] = sparse(
            Sum(
                cur.where[par_comc["2", r, t, c, cur]],
                par_comc["2", r, t, c, cur] * tmp_GP,
            )
        )

    def exec_regional_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        sysprefix: str,
    ) -> None:
        g = self.tc

        r, v, t, p, c, Rp, Bdneq, Rcj, RpIre, Sysinv, Vnt, rpm = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.Rp,
            g.Bdneq,
            g.Rcj,
            g.RpIre,
            g.Sysinv,
            g.Vnt,
            g.rpm,
        )
        coef_pvt, par_actc, par_comc, par_floc, pastsum, prc_ymax = (
            g.coef_pvt,
            g.par_actc,
            g.par_comc,
            g.par_floc,
            g.pastsum,
            g.prc_ymax,
        )
        CST_ACTC = g.get_parameter(f"{arg1}CST_ACTC")
        CST_COMC = g.get_parameter(f"{arg1}CST_COMC")
        CST_COME = g.get_parameter(f"{arg1}CST_COME")
        CST_COMX = g.get_parameter(f"{arg1}CST_COMX")
        CST_FIXC = g.get_parameter(f"{arg1}CST_FIXC")
        CST_FIXX = g.get_parameter(f"{arg1}CST_FIXX")
        CST_FLOC = g.get_parameter(f"{arg1}CST_FLOC")
        CST_FLOX = g.get_parameter(f"{arg1}CST_FLOX")
        CST_INVC = g.get_parameter(f"{arg1}CST_INVC")
        CST_INVX = g.get_parameter(f"{arg1}CST_INVX")
        CST_IREC = g.get_parameter(f"{arg1}CST_IREC")
        CST_PVC = g.get_parameter(f"{arg1}CST_PVC")
        CST_PVP = g.get_parameter(f"{arg1}CST_PVP")
        REG_ACOST = g.get_parameter(f"{arg1}REG_ACOST")

        if CST_PVP.number_records:
            CST_PVC[*arg2, f"{sysprefix}ELS", r, c].where[
                Sum(Rcj[r, c, "1", Bdneq], 1)
            ] = Sum(t, CST_COME[*arg2, r, t, c] * coef_pvt[r, t])
            CST_PVP[*arg2, f"{sysprefix}IRE", RpIre[Rp[r, p]]] = sparse(prc_ymax[r, p])
        # *----------------------------------------------------------------------
        # * Regional annual costs
        REG_ACOST[*arg2, r, t, "INV"] = Sum(
            Domain(Vnt[v, t], p, Sysinv).where[CST_INVC[*arg2, r, v, t, p, Sysinv]],
            CST_INVC[*arg2, r, v, t, p, Sysinv],
        )
        REG_ACOST[*arg2, r, t, "INVX"] = Sum(
            Domain(Vnt[v, t], p, Sysinv).where[CST_INVX[*arg2, r, v, t, p, Sysinv]],
            CST_INVX[*arg2, r, v, t, p, Sysinv],
        )
        REG_ACOST[*arg2, r, t, "FIX"] = Sum(
            Domain(Vnt[v, t], p).where[CST_FIXC[*arg2, r, v, t, p]],
            CST_FIXC[*arg2, r, v, t, p],
        )
        REG_ACOST[*arg2, r, t, "FIXX"] = Sum(
            Domain(Vnt[v, t], p).where[CST_FIXX[*arg2, r, v, t, p]],
            CST_FIXX[*arg2, r, v, t, p],
        )
        REG_ACOST[*arg2, r, t, "VAR"] = (
            Sum(
                Domain(Vnt[v, t], p, rpm).where[CST_ACTC[*arg2, r, v, t, p, rpm]],
                CST_ACTC[*arg2, r, v, t, p, rpm],
            )
            + Sum(
                Domain(Vnt[v, t], p, c).where[CST_FLOC[*arg2, r, v, t, p, c]],
                CST_FLOC[*arg2, r, v, t, p, c],
            )
            + Sum(c.where[CST_COMC[*arg2, r, t, c]], CST_COMC[*arg2, r, t, c])
        )
        REG_ACOST[*arg2, r, t, "VARX"] = Sum(
            Domain(Vnt[v, t], p, c).where[CST_FLOX[*arg2, r, v, t, p, c]],
            CST_FLOX[*arg2, r, v, t, p, c],
        ) + Sum(c.where[CST_COMX[*arg2, r, t, c]], CST_COMX[*arg2, r, t, c])
        REG_ACOST[*arg2, r, t, "IRE"] = Sum(
            Domain(Vnt[v, t], p, c).where[CST_IREC[*arg2, r, v, t, p, c]],
            CST_IREC[*arg2, r, v, t, p, c],
        )
        REG_ACOST[*arg2, r, t, "ELS"] = Sum(
            c.where[CST_COME[*arg2, r, t, c]], CST_COME[*arg2, r, t, c]
        )
        # *----------------------------------------------------------------------
        par_actc.setRecords(None)
        par_comc.setRecords(None)
        par_floc.setRecords(None)
        prc_ymax.setRecords(None)
        pastsum.setRecords(None)

    def exec_salvage_costs(
        self: CostAnnRpt,
        arg1: str,
        arg2: tuple[Set | Alias | str, ...] | tuple[()],
        etl: str,
    ) -> None:
        g = self.tc

        r, t, p, cur, item, obv = g.r, g.t, g.p, g.cur, g.item, g.obv
        GRcur, ObjIcur, ObjSums, Rdcur, Rtp, Teg = (
            g.GRcur,
            g.ObjIcur,
            g.ObjSums,
            g.Rdcur,
            g.Rtp,
            g.Teg,
        )
        obj_dceoh, objsic, par_objsal, reg_obj, sum_obj = (
            g.obj_dceoh,
            g.objsic,
            g.par_objsal,
            g.reg_obj,
            g.sum_obj,
        )
        VAR_IC, VAR_NCAP, VAR_OBJ = g.VAR_IC, g.VAR_NCAP, g.VAR_OBJ
        CST_SALV = g.get_parameter(f"{arg1}CST_SALV")

        # * Calculate actual Salvage values
        par_objsal[ObjIcur[r, t, p, cur]] = (
            par_objsal[r, t, p, cur] * VAR_NCAP[r, t, p].l
        )
        if etl == "YES":
            # A bare RTP on the right hand side reuses the indices controlled by
            # the assignment domain, i.e. R, T and P.
            par_objsal[Rtp[r, t, Teg[p]], cur].where[GRcur[r, cur]] = (
                par_objsal[r, t, p, cur]
                + Sum(ObjSums[r, t, p], objsic[r, t, p] * VAR_IC[r, t, p].l)
                * obj_dceoh[r, cur]
            )
        CST_SALV[*arg2, r, t, p] = sparse(Sum(Rdcur[r, cur], par_objsal[r, t, p, cur]))
        reg_obj[r] = Sum(
            Domain(Rdcur[r, cur], item, obv).where[  # type: ignore[arg-type]
                sum_obj[item, obv]
            ],
            VAR_OBJ[r, obv, cur].l * sum_obj[item, obv],
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
    """Legacy GAMS text of cost_ann.rpt.

    Still needed by the callers that embed it into raw GAMS blocks they build
    themselves - rptmain.stc and rpt_ext.mlf wrap it in a GAMS ``LOOP``, and
    solprep.msa hands its text on to further string consumers. Everything that
    is already translated goes through :class:`CostAnnRpt` instead.
    """
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
