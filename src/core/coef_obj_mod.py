# coef_obj_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_OBJ.MOD do coefficient calculations for the OBJ
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# *  responsible for moving cost data to EACHYEAR from each input period
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Alias,
    Domain,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Smax,
    Smin,
    Sum,
    sparse,
)
from gamspy.math import Max, Min, abs, aggregate, ceil, project

from core.base_class import GamsClass
from core.fillcost_gms import FillcostGms, FillcostGmsConfig
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefObjMod(GamsClass):
    """Translation unit for coef_obj.mod."""

    # Instance attributes
    module_name: str = "coef_obj_mod"
    gams_source: str = "coef_obj.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc

        r, p, c, s, ie, cur, costype = g.r, g.p, g.c, g.s, g.ie, g.cur, g.costype
        Rp, Rdcur, Fil, ComTs, RpcsVar = g.Rp, g.Rdcur, g.Fil, g.ComTs, g.RpcsVar

        self.declaration1()
        self.tc.enqueue(self.exec1)
        self.declaration2()
        self.tc.enqueue(
            self.check_year_matches_doc,
            condition1=(self.env.anncost.upper() == "LEV"),
            condition2=(f"{self.env.anncost}{self.env.ctst}".upper() == "LEV"),
        )

        # * interpolate discount rates
        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.g_drate,
                    arg2=(g.r,),
                    tail1=(g.cur,),
                    arg4=("", "", "", "", ""),
                    arg5=g.allyear,
                    arg6=g.ll,
                    arg7=g.Fil[g.ll],  # "FIL(LL)$" handle $ at end
                    arg8=g.Fil[g.ll],  # "FIL(LL)$" handle $ at end
                ),
            )
        )

        self.tc.enqueue(self.set_obj_disc)
        self.env.set_scoped("take", "RDCUR(R,CUR)")
        take: ImplicitSet | Literal[1] = Rdcur[r, cur]
        self.env.set_scoped("tmp", "1")
        tmp = 1
        # * Can we use macroes?
        if self.env.obmac == "YES":
            self.env.set_scoped("tmp", "2")
            tmp = 2

        if self.tc.defined("R_CUREX"):
            self.env.set_scoped("take", "1")
            take = 1

        self.tc.enqueue(
            self.determine_min_max_year, condition=self.env.validata == "YES"
        )

        self.env.set_local("bext", "(YEARVAL(FIL) GE PRC_YMIN(R,P))$")
        bext = g.yearval[Fil] >= g.prc_ymin[r, p]
        self.env.set_local("fext", "(YEARVAL(FIL) LE PRC_YMAX(R,P))$")
        fext = g.yearval[Fil] <= g.prc_ymax[r, p]

        # * investment related costs
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_icost, arg2=r, arg3=(p,cur), arg4=('0','0','0'),arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_cost, arg10="OB_ICOST", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_isub, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_isub, arg10="OB_ISUB", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_itax, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_itax, arg10="OB_ITAX", arg11=tmp),
            FillcostGmsConfig(arg1=g.ncap_ispct, arg2=r, arg3=(p,), arg4=('0','0','0','0'), arg5=Fil, arg6=1, bext=bext, fext=fext, arg9=g.ncap_ispct, arg10="X_RP", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        self.tc.enqueue(self.exec2)

        # * fixed O&M and taxes
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_fom, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_fom, arg10="OB_FOM", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_fsb, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_fsub, arg10="OB_FSB", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_ftx, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_ftax, arg10="OB_FTX", arg11=tmp),
            # * decommissioning (actual & surveillance)
            FillcostGmsConfig(arg1=g.obj_dcost, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_dcost, arg10="OB_DCC", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_dlagc, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=take, bext=bext, fext=fext, arg9=g.ncap_dlagc, arg10="OB_DLC", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        self.tc.enqueue(
            self.exec3,
            condition1=self.env.varcost.upper() == "LIN",
            condition2=self.env.validate == "YES",
        )

        # * variable costs
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_acost, arg2=r, arg3=(p,cur), arg4=('0','0','0'), arg5=Fil, arg6=Rp[r,p], bext=1, fext=1, arg9=g.act_cost, arg10="OB_ACT", arg11=tmp),
            # * commodity costs
            FillcostGmsConfig(arg1=g.obj_comnt, arg2=r, arg3=(c,s,costype,cur), arg4=('0',), arg5=Fil, arg6=ComTs[r,c,s], bext=1, fext=1, arg9=g.obj_comnt, arg10="OB_COM"),
            FillcostGmsConfig(arg1=g.obj_compd, arg2=r, arg3=(c,s,costype,cur), arg4=('0',), arg5=Fil, arg6=ComTs[r,c,s], bext=1, fext=1, arg9=g.obj_compd, arg10="OB_COM"),
            FillcostGmsConfig(arg1=g.obj_ipric, arg2=r, arg3=(p,c,s,ie,cur), arg4=(), arg5=Fil, arg6=RpcsVar[r,p,c,s], bext=1, fext=1, arg9=g.obj_ipric, arg10="OB_IRE"),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        # * flow cost
        self.env.set_scoped("take", "(RPCS_VAR(R,P,C,S)+ANNUAL(S))")
        take = RpcsVar[r, p, c, s] + g.Annual[s]  # type: ignore[assignment]
        # fmt: off
        fillcost_gms_batincludes = [
            FillcostGmsConfig(arg1=g.obj_fcost, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.flo_cost, arg10="OB_FCOS", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_fdelv, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.flo_deliv, arg10="OB_FDEL", arg11=tmp),
            FillcostGmsConfig(arg1=g.obj_ftax, arg2=r, arg3=(p,c,s,cur), arg4=('0',), arg5=Fil, arg6=take, bext=1, fext=1, arg9=g.obj_fsub, arg10="OB_FTAX", arg11=tmp),
        ]
        # fmt: on
        for config in fillcost_gms_batincludes:
            self.include(FillcostGms(self.tc, self.env, config))

        self.tc.enqueue(self.exec4)

        if self.env.obmac == "YES":
            self.compile_macros()

        # *-----------------------------------------------------------------------------*
        # * investment related costs
        # *-----------------------------------------------------------------------------*
        # * capital recovery factors: CRFs now defined in eqobjinv.mod / eqobsalv.mod
        # *    OBJ_CRF(RTP(R,V,P),CUR)    = (1-(1/(1+(G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP))))) /
        # *                                 (1-(1/(1+G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP)))**NCAP_ELIFE(RTP));
        # *    OBJ_CRFD(RTP(R,V,P),CUR)$NCAP_DELIF(RTP)  = (1-(1/(1+(G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP))))) /
        # *                                 (1-(1/(1+G_DRATE(R,V,CUR)$(NOT NCAP_DRATE(RTP)) + NCAP_DRATE(RTP)))**NCAP_DELIF(RTP));

        if (self.env.validate != "YES") and (self.env.timesed != "YES"):
            # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
            pass
        else:
            self.tc.enqueue(self.exec5)
            if self.env.validate != "YES":
                # * ignore investment cost for learned technologies when ETL active: COEF_EXT.ETL
                pass
            else:
                self.tc.enqueue(self.exec6)

    def declaration1(self: CoefObjMod) -> None:
        g = self.tc
        m = g.container

        g.k = Alias(m, name="K", alias_with=g.Eachyear)
        g.Y = Set(m, name="Y", domain=[g.allyear])
        g.YEoh = Set(m, name="Y_EOH", domain=[g.allyear])
        g.Yk = Set(m, name="YK", domain=[g.allyear, g.allyear])
        g.TsAnn = Set(m, name="TS_ANN", domain=[g.s, g.s])

    def declaration2(self: CoefObjMod) -> None:
        g = self.tc
        m = g.container

        g.yr_v1 = Parameter(m, name="YR_V1", records=0)
        g.yr_vl = Parameter(m, name="YR_VL", records=0)
        g.acl = Parameter(m, name="ACL", records=0)
        # For shaped demand elasticises
        g.span = Alias(m, name="SPAN", alias_with=g.age)
        g.Shedj = Set(
            m,
            name="SHEDJ",
            domain=[g.lim, g.j],
            description="Elastic demand shape indexes",
        )
        g.shaped = Parameter(
            m,
            name="SHAPED",
            domain=[g.bd, g.j, g.age],
            description="Elastic demand shape curves",
        )

    def exec1(self: CoefObjMod) -> None:
        g = self.tc

        g.TsAnn[g.s, g.s] = True
        g.TsAnn[g.s, g.Annual] = True

    def check_year_matches_doc(
        self: CoefObjMod, condition1: bool, condition2: bool
    ) -> None:
        g = self.tc
        (
            yr_vl,
            miyr_vl,
            dur_max,
            Rtp,
            r,
            Pastmile,
            ll,
            p,
            ncap_iled,
            k,
            Y,
            yearval,
            minyr,
            Yk,
            acl,
            miyr_v1,
            rpt_opt,
            YEoh,
            Eohyears,
            Fil,
            yr_v1,
            Datayear,
            pyr_v1,
        ) = (
            g.yr_vl,
            g.miyr_vl,
            g.dur_max,
            g.Rtp,
            g.r,
            g.Pastmile,
            g.ll,
            g.p,
            g.ncap_iled,
            g.k,
            g.Y,
            g.yearval,
            g.minyr,
            g.Yk,
            g.acl,
            g.miyr_v1,
            g.rpt_opt,
            g.YEoh,
            g.Eohyears,
            g.Fil,
            g.yr_v1,
            g.Datayear,
            g.pyr_v1,
        )
        # establish eachyear sets matching documentation
        yr_vl[...] = miyr_vl + dur_max
        with Loop(Rtp[r, Pastmile[ll], p].where[ncap_iled[r, ll, p]]):
            k[ll + ncap_iled[r, ll, p]] = True
        Y[k].where[(yearval[k] >= minyr) * (yearval[k] <= yr_vl)] = True
        Yk[Y, k].where[yearval[k] <= yearval[Y]] = True

        if condition1:
            acl[...] = minyr
            minyr[...] = miyr_v1
            rpt_opt["OBJ", "2"] = 1

        if condition2:
            minyr[...] = acl

        YEoh[Eohyears].where[yearval[Eohyears] >= minyr] = True
        Fil.setRecords(None)
        yr_v1[...] = Min(Smin(Datayear, yearval[Datayear]), pyr_v1)
        yr_vl[...] = Max(Smax(Datayear, yearval[Datayear]), yr_vl)
        Fil[ll].where[(yearval[ll] >= yr_v1) * (yearval[ll] <= yr_vl)] = True

    def set_obj_disc(self: CoefObjMod) -> None:
        g = self.tc
        (
            obj_disc,
            r,
            ll,
            cur,
            Rdcur,
            yearval,
            yr_v1,
            g_dyear,
            Miyr1,
            t,
            Fil,
            g_drate,
            f,
            yr_vl,
            z,
            v,
            GRcur,
            d,
            obj_pvt,
            Periodyr,
            YEoh,
            coef_pvt,
            obj_rfr,
            g_rfrir,
            obj_comnt,
            Datayear,
            c,
            s,
            costype,
            ComTs,
            obj_compd,
            allr,
            Reg,
            obj_ipric,
            p,
            ie,
            RpcIreio,
            ire_price,
            xpt,
            flo_cost,
            Top,
            RpcStg,
            flo_deliv,
            obj_fsub,
            flo_tax,
            flo_sub,
            ObjVflo,
            RpcCur,
            ncap_ispct,
            ncap_isub,
            prc_ymax,
            obj_blndv,
            Ble,
            Opr,
            BleOpr,
            bl_varomc,
            Com,
            bl_inp,
            bl_delivc,
        ) = (
            g.obj_disc,
            g.r,
            g.ll,
            g.cur,
            g.Rdcur,
            g.yearval,
            g.yr_v1,
            g.g_dyear,
            g.Miyr1,
            g.t,
            g.Fil,
            g.g_drate,
            g.f,
            g.yr_vl,
            g.z,
            g.v,
            g.GRcur,
            g.d,
            g.obj_pvt,
            g.Periodyr,
            g.YEoh,
            g.coef_pvt,
            g.obj_rfr,
            g.g_rfrir,
            g.obj_comnt,
            g.Datayear,
            g.c,
            g.s,
            g.costype,
            g.ComTs,
            g.obj_compd,
            g.allr,
            g.Reg,
            g.obj_ipric,
            g.p,
            g.ie,
            g.RpcIreio,
            g.ire_price,
            g.xpt,
            g.flo_cost,
            g.Top,
            g.RpcStg,
            g.flo_deliv,
            g.obj_fsub,
            g.flo_tax,
            g.flo_sub,
            g.ObjVflo,
            g.RpcCur,
            g.ncap_ispct,
            g.ncap_isub,
            g.prc_ymax,
            g.obj_blndv,
            g.Ble,
            g.Opr,
            g.BleOpr,
            g.bl_varomc,
            g.Com,
            g.bl_inp,
            g.bl_delivc,
        )
        # set discounting factor OBJ_DISC in 'cumulative' way, covering EACHYEAR
        # First, initialize the discount factor for YR_V1 to 1.0:
        obj_disc[r, ll, cur].where[Rdcur[r, cur].where[yearval[ll] == yr_v1]] = 1
        if g_dyear.toValue() == 0:
            g_dyear[...] = Sum(Miyr1[t], yearval[t])
        # Calculate all discount factors with respect to YR_V1:
        with Loop(Fil[ll - 1]):
            obj_disc[r, ll, cur] = obj_disc[r, Fil, cur] / (1 + g_drate[r, ll, cur])
        # Find the year among FIL that is closest to the base year G_DYEAR:
        f[...] = Sum(Miyr1[ll], yearval[ll] - Max(Min(yr_vl, g_dyear), yr_v1))
        # Normalize all discount factors so that the base year discount factor = 1.0:
        with Loop(Rdcur[r, cur]):
            z[...] = Sum(
                Miyr1[ll + f],
                obj_disc[r, ll, cur]
                * (1 + g_drate[r, ll, cur]) ** (-(g_dyear - yearval[ll])),
            )
            obj_disc[r, Fil[ll], cur] = obj_disc[r, ll, cur] / z
        # Prevent divide-by-zero if zero discount rate
        g_drate[r, v, cur].where[(g_drate[r, v, cur] <= 0).where[Rdcur[r, cur]]] = 1e-11
        # -----------------------------------------------------------------------------
        # Calculate present value factors for time in periods
        with Loop(r.where[~Sum(GRcur[Rdcur[r, cur]], 1)]):
            z[...] = Smax(Rdcur[r, cur], Sum(t, d[t] * obj_disc[r, t, cur]))
            with Loop(Rdcur[r, cur].where[z]):
                f[...] = Sum(t, d[t] * obj_disc[r, t, cur])
                with If(abs(f - z) < 1e-07):
                    GRcur[r, cur] = True
                    z[...] = 0
        obj_pvt[r, t, cur].where[Rdcur[r, cur]] = Sum(
            Periodyr[t, YEoh], obj_disc[r, YEoh, cur]
        )
        coef_pvt[r, t] = Sum(GRcur[r, cur], obj_pvt[r, t, cur])
        obj_rfr[r, v, cur] = sparse(g_drate[r, v, cur])
        obj_rfr[r, v, cur].where[Rdcur[r, cur]] = sparse(g_rfrir[r, v])
        # -----------------------------------------------------------------------------
        # move original data from input to annual value arrays
        # commodity costs
        obj_comnt[r, Datayear, c, s, costype, cur].where[~ComTs[r, c, s]] = 0
        obj_compd[r, Datayear, c, s, costype, cur].where[~ComTs[r, c, s]] = 0
        # IRE_PRICE - exports negative
        # Take IRE_PRICE into account ONLY if the trade is exogenous; map ALL_R into R:
        # Additionally allow using R directly as a placeholder of any external region
        with Loop(allr.where[~Reg[allr]]):
            obj_ipric[r, Datayear, p, c, s, ie, cur].where[
                RpcIreio[r, p, c, ie, "OUT"]
            ] = sparse(
                ire_price[r, Datayear, p, c, s, allr, ie, cur]
                * (1 - (Number(2)).where[xpt[ie]])
            )
        obj_ipric[r, Datayear, p, c, s, ie, cur].where[RpcIreio[r, p, c, ie, "OUT"]] = (
            sparse(
                ire_price[r, Datayear, p, c, s, r, ie, cur]
                * (1 - (Number(2)).where[xpt[ie]])
            )
        )
        # flow costs; remove invalid costs on storage flows
        flo_cost[r, ll, p, c, s, cur].where[
            (~Top[r, p, c, "IN"]).where[RpcStg[r, p, c]]
        ] = 0
        flo_deliv[r, ll, p, c, s, cur].where[
            (~Top[r, p, c, "OUT"]).where[RpcStg[r, p, c]]
        ] = 0
        obj_fsub[r, ll, p, c, s, cur] = sparse(flo_tax[r, ll, p, c, s, cur])
        obj_fsub[r, ll, p, c, s, cur].where[flo_sub[r, ll, p, c, s, cur]] = (
            obj_fsub[r, ll, p, c, s, cur] - flo_sub[r, ll, p, c, s, cur]
        )
        obj_fsub[r, ll, p, c, s, cur].where[
            (~v[ll]).where[ObjVflo[r, p, c, cur, "SUB"]]
        ] = 0
        project(source=flo_cost, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "COST"] = True
        project(source=flo_deliv, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "COST"] = True
        project(source=flo_tax, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "TAX"] = True
        project(source=flo_sub, target=RpcCur, direction="left")
        ObjVflo[RpcCur, "SUB"] = True
        # remove proportional subsidy if absolute defined
        if len(ncap_ispct):
            aggregate(source=ncap_isub, target=prc_ymax)
            ncap_ispct[r, ll, p].where[prc_ymax[r, p]] = 0
        # V07_1b blending
        obj_blndv[r, YEoh, Ble, Opr, cur].where[
            Rdcur[r, cur].where[BleOpr[r, Ble, Opr]]
        ] = bl_varomc[r, Ble, cur] + Sum(
            Com.where[bl_delivc[r, Ble, Com, cur]],
            bl_inp[r, Ble, Com] * bl_delivc[r, Ble, Com, cur],
        )

    def determine_min_max_year(self: CoefObjMod, condition: bool) -> None:
        g = self.tc
        (
            my_array,
            v,
            b,
            m,
            ipd,
            prc_ymin,
            Rp,
            r,
            p,
            Rtp,
            prc_ymax,
            pyr,
            yearval,
            t,
            z,
            e,
            lagt,
            ncap_iled,
            ncap_tlife,
            coef_rpti,
            Fil,
            k,
        ) = (
            g.my_array,
            g.v,
            g.b,
            g.m,
            g.ipd,
            g.prc_ymin,
            g.Rp,
            g.r,
            g.p,
            g.Rtp,
            g.prc_ymax,
            g.pyr,
            g.yearval,
            g.t,
            g.z,
            g.e,
            g.lagt,
            g.ncap_iled,
            g.ncap_tlife,
            g.coef_rpti,
            g.Fil,
            g.k,
        )
        # Establish process-wise subset of EACHYEAR by determining the MIN and MAX years
        my_array[v] = Min(b[v], m[v] - ipd[v])
        prc_ymin[Rp[r, p]] = Smin(Rtp[r, v, p], my_array[v])
        prc_ymax[Rp[r, p]] = Smax(Rtp[r, pyr, p], yearval[pyr])
        # Make sure last commissioning year of repeated investments is included
        with Loop(t):
            z[...] = m[t] - e[t] + lagt[t]
            prc_ymax[Rp[r, p]].where[Rtp[r, t, p]] = Max(
                prc_ymax[r, p],
                e[t]
                + ncap_iled[r, t, p]
                + (Max(z, ncap_tlife[r, t, p])).where[coef_rpti[r, t, p] > 1],
            )
        # -----------------------------------------------------------------------------*
        # Interpolation/extrapolation of cost parameters
        # EACHYEAR will be sufficient for all capacity related costs
        z[...] = Smax(Rp, prc_ymax[Rp])
        Fil.setRecords(None)
        my_array.setRecords(None)
        Fil[k].where[yearval[k] <= z] = True

        if condition:
            Fil[k] = v[k]

    def exec2(self: CoefObjMod) -> None:
        g = self.tc
        x_rp, ob_isub, Rp, cur, year, ob_icost = (
            g.x_rp,
            g.ob_isub,
            g.Rp,
            g.cur,
            g.year,
            g.ob_icost,
        )
        if len(x_rp):
            ob_isub[Rp, cur, year].where[x_rp[Rp, year]] = sparse(
                ob_icost[Rp, cur, year] * x_rp[Rp, year]
            )
            x_rp.setRecords(None)

    def exec3(self: CoefObjMod, condition1: bool, condition2: bool) -> None:
        g = self.tc
        Fil, YEoh, yearval, miyr_v1, t = g.Fil, g.YEoh, g.yearval, g.miyr_v1, g.t
        Fil.setRecords(None)
        Fil[YEoh].where[yearval[YEoh] >= miyr_v1] = True
        if condition1:
            Fil.setRecords(None)
            Fil[t] = True
        if condition2:
            Fil.setRecords(None)
            Fil[t] = True

    def exec4(self: CoefObjMod) -> None:
        g = self.tc

        g.prc_ymin.setRecords(None)
        g.prc_ymax.setRecords(None)
        g.RpcCur.setRecords(None)
        g.obj_fsub.setRecords(None)

    def compile_macros(self: CoefObjMod) -> None:
        macro.obj_icost_active = True
        macro.obj_isub_active = True
        macro.obj_itax_active = True
        macro.obj_fom_active = True
        macro.obj_fsb_active = True
        macro.obj_ftx_active = True
        macro.obj_dcost_active = True
        macro.obj_dlagc_active = True
        macro.obj_acost_active = True
        macro.obj_fcost_active = True
        macro.obj_fdelv_active = True
        macro.obj_ftax_active = True

    def exec5(self: CoefObjMod) -> None:
        g = self.tc
        (
            Shedj,
            bd,
            j,
            RtcShed,
            r,
            t,
            c,
            Bdneq,
            bdsig,
            com_voc,
            shaped,
            age,
            shape,
            span,
            Bdupx,
        ) = (
            g.Shedj,
            g.bd,
            g.j,
            g.RtcShed,
            g.r,
            g.t,
            g.c,
            g.Bdneq,
            g.bdsig,
            g.com_voc,
            g.shaped,
            g.age,
            g.shape,
            g.span,
            g.Bdupx,
        )
        # Calculate coefficients for shaped demand elasticises
        # Collect all tuples (J,BD) from COM_ELASTX to SHEDJ(BD,J)
        Shedj[bd, j] = sparse(Sum(RtcShed[r, t, c, bd, j], 1))
        Shedj[Bdneq, "1"] = True
        # Calculate price changes by percent, and cumulate
        bdsig[Bdneq] = ceil(
            Smax(RtcShed[r, t, c, Bdneq, j], com_voc[r, t, c, Bdneq]) * 100
        )
        bdsig["LO"] = Min(100, bdsig["LO"])
        shaped[Shedj[Bdneq, j], age].where[Ord(age) <= bdsig[Bdneq]] = (
            1 + 0.01 / (1 + (Ord(age) - 1) / 100)
        ) ** (1 / Max(0.001, shape[j, age]))
        with Loop(Domain(age, span[age - 1], Bdneq[bd]).where[Ord(age) <= bdsig[bd]]):
            shaped[Shedj[bd, j], age] = shaped[bd, j, age] * shaped[bd, j, span]
        bdsig[Bdneq] = 1 - (Number(2)).where[Bdupx[Bdneq]]

    def exec6(self: CoefObjMod) -> None:
        g = self.tc
        (
            v,
            Fil,
            k,
            Periodyr,
            r,
            p,
            cur,
            obj_ipric,
            c,
            s,
            ie,
        ) = (
            g.v,
            g.Fil,
            g.k,
            g.Periodyr,
            g.r,
            g.p,
            g.cur,
            g.obj_ipric,
            g.c,
            g.s,
            g.ie,
        )
        # Flat period assignment
        # As original parameters are not filled, flat data must be taken from OBJ_xxx
        with Loop(v):
            Fil[Fil] = False
            Fil[k].where[Periodyr[v, k]] = True

            macro.obj_icost_GP(r, Fil, p, cur)[...] = sparse(
                macro.obj_icost_GP(r, v, p, cur)
            )

            macro.obj_fom_GP(r, Fil, p, cur)[...] = sparse(
                macro.obj_fom_GP(r, v, p, cur)
            )

            macro.obj_acost_GP(r, Fil, p, cur)[...] = sparse(
                macro.obj_acost_GP(r, v, p, cur)
            )

            obj_ipric[r, Fil, p, c, s, r, ie, cur] = sparse(
                obj_ipric[r, v, p, c, s, r, ie, cur]
            )

            macro.obj_fcost_GP(r, Fil, p, c, s, cur)[...] = sparse(
                macro.obj_fcost_GP(r, v, p, c, s, cur)
            )

            macro.obj_fdelv_GP(r, Fil, p, c, s, cur)[...] = sparse(
                macro.obj_fdelv_GP(r, v, p, c, s, cur)
            )

        # print(obj_icost.records)
        # print(obj_fom.records)
