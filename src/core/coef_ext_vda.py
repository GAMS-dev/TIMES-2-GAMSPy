# coef_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_EXT.vda oversees extended preprocessor activities after COEF_MAIN
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Else, If, Loop, Number, Parameter, Smax, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, Round, mod, power, project

from core.base_class import GamsClass
from core.eqashar_vda import EqasharVda, EqasharVdaConfig
from core.eqlducs_vda import EqlducsVda
from core.fillwave_gms import FillwaveGms
from core.powerflo_vda import PowerfloVda
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefExtVda(GamsClass):
    """Translation unit for coef_ext.vda."""

    # Instance attributes
    module_name: str = "coef_ext_vda"
    gams_source: str = "coef_ext.vda"

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
        self.compile()

    def compile(self) -> None:
        self.comp1()
        if self.env.waver.upper() == "YES":
            # fmt: off
            batincludes = [
                ("PRC_RESID", "PRC", "0" ),
                ("COM_PROJ", "COM", "1" ),
            ]
            # fmt: on
            for arg in batincludes:
                self.include(
                    FillwaveGms(
                        self.tc,
                        self.env,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                    )
                )
            self.tc.enqueue(self.exec1)

        # RESID
        self.tc.enqueue(self.make_sensible_resid_pasti)

        macro.upscaps.activate(
            g=self.tc, var=self.env.var, sow=self.env.sow, sow_GP=self.env.sow_GP
        )

        macro.var_sts.activate(
            g=self.tc, var=self.env.var, sow=self.env.sow, sow_GP=self.env.sow_GP
        )

        self.tc.enqueue(
            self.exec2,
            pgprim=self.env.pgprim,
            condition1=self.env.stsflx.upper() != "YES",
            condition2=self.env.sensis.upper() != "YES",
        )

        self.include(EqlducsVda(self.tc, self.env))
        self.include(EqasharVda(self.tc, self.env, config=EqasharVdaConfig()))

        if self.tc.defined("COM_CSTBAL"):
            self.include(PowerfloVda(self.tc, self.env, arg1="CSTBAL"))

        self.tc.enqueue(self.exec3)

    def comp1(self: CoefExtVda) -> None:
        g = self.tc
        m = g.container
        g.vda_disc = Parameter(m, name="VDA_DISC", domain=[g.r, g.allyear])
        g.vda_disc.setRecords(None)

    def exec1(self: CoefExtVda) -> None:
        g = self.tc
        vda_disc = g.vda_disc
        vda_disc.setRecords(None)

    def make_sensible_resid_pasti(self: CoefExtVda) -> None:
        g = self.tc
        (
            t,
            Trackp,
            r,
            p,
            prc_resid,
            PyrS,
            v,
            PrcRcap,
            z,
            rtforc,
            RtpCptyr,
            ncap_pasti,
            d,
            coef_cpt,
        ) = (
            g.t,
            g.Trackp,
            g.r,
            g.p,
            g.prc_resid,
            g.PyrS,
            g.v,
            g.PrcRcap,
            g.z,
            g.rtforc,
            g.RtpCptyr,
            g.ncap_pasti,
            g.d,
            g.coef_cpt,
        )
        # Try making sensible RESID PASTI (although it does not affect solution)
        # Finalize PRC_RESID capacity coefficients:
        with Loop(t):
            Trackp[r, p].where[(prc_resid[r, t, p] > 0) & prc_resid[r, t, p]] = True
        with Loop(PyrS[v]):
            with Loop(PrcRcap[Trackp[r, p]]):
                z[...] = Smax(t, prc_resid[r, t, p])
                rtforc[RtpCptyr[r, v, t, p]] = (
                    z - prc_resid[r, t, p] + SpecialValues.EPS
                )
                prc_resid[r, t, p].where[rtforc[r, v, t, p]] = z
            ncap_pasti[r, v, p].where[prc_resid[r, "0", p]] = (
                Sum(t, prc_resid[r, t, p] * d[t])
                / Sum(t.where[prc_resid[r, t, p] > 0], d[t])
            ).where[Trackp[r, p]]
        prc_resid[r, "0", p].where[~Trackp[r, p]] = 0
        coef_cpt[RtpCptyr[r, PyrS[v], t, p]].where[Trackp[r, p]] = (
            prc_resid[r, t, p] / ncap_pasti[r, v, p]
        )

    def exec2(
        self: CoefExtVda, pgprim: str, condition1: bool, condition2: bool
    ) -> None:
        g = self.tc
        (
            RpStl,
            RpSts,
            tsl,
            bd,
            coef_afups,
            Rtp,
            r,
            v,
            p,
            s,
            RpsCaflac,
            ncap_af,
            RpsStg,
            stl,
            ncap_afc,
            PrcCap,
            act_cstup,
            cur,
            Rdcur,
            stg_maxcyc,
            g_drate,
            ncap_tlife,
            Trackp,
            RhsCombal,
            Trackc,
            ire_flosum,
            Rcs,
            c,
            Top,
            RpcIre,
            Rc,
            Dem,
            RpcNoflo,
            RcsCombal,
            RtcsVarc,
            t,
            lA,
            ComUnit,
            RhsComprd,
            TopIre,
            uc_time,
            RUc,
            ucnA,
            UcOn,
            UcRSum,
            Reg,
            RpCgc,
            Rpg1ace,
            Trackpc,
            RpGrp,
            RpcFfunc,
            act_flo,
            RpcsVar,
            cg,
            micro,
            act_eff,
            rtp_ffcx,
            CgGrp,
            RpcgPtran,
            Rp,
            Com,
            cg2,
            RpDcgg,
            RpcAct,
            RtpCapyr,
            Actcg,
            bdsig,
            coef_ptran,
            RpcPg,
            prc_actflo,
            ll,
            RpccFfunc,
        ) = (
            g.RpStl,
            g.RpSts,
            g.tsl,
            g.bd,
            g.coef_afups,
            g.Rtp,
            g.r,
            g.v,
            g.p,
            g.s,
            g.RpsCaflac,
            g.ncap_af,
            g.RpsStg,
            g.stl,
            g.ncap_afc,
            g.PrcCap,
            g.act_cstup,
            g.cur,
            g.Rdcur,
            g.stg_maxcyc,
            g.g_drate,
            g.ncap_tlife,
            g.Trackp,
            g.RhsCombal,
            g.Trackc,
            g.ire_flosum,
            g.Rcs,
            g.c,
            g.Top,
            g.RpcIre,
            g.Rc,
            g.Dem,
            g.RpcNoflo,
            g.RcsCombal,
            g.RtcsVarc,
            g.t,
            g.lA,
            g.ComUnit,
            g.RhsComprd,
            g.TopIre,
            g.uc_time,
            g.RUc,
            g.ucnA,
            g.UcOn,
            g.UcRSum,
            g.Reg,
            g.RpCgc,
            g.Rpg1ace,
            g.Trackpc,
            g.RpGrp,
            g.RpcFfunc,
            g.act_flo,
            g.RpcsVar,
            g.cg,
            g.micro,
            g.act_eff,
            g.rtp_ffcx,
            g.CgGrp,
            g.RpcgPtran,
            g.Rp,
            g.Com,
            g.cg2,
            g.RpDcgg,
            g.RpcAct,
            g.RtpCapyr,
            g.Actcg,
            g.bdsig,
            g.coef_ptran,
            g.RpcPg,
            g.prc_actflo,
            g.ll,
            g.RpccFfunc,
        )
        if condition1:
            RpStl[RpSts, tsl, bd] = 0  # type: ignore[assignment]
        # -----------------------------------------------------------------------------
        # Get AF-UPs for processes having storage level constrained
        coef_afups[Rtp[r, v, p], s].where[~RpsCaflac[r, p, s, "UP"]] = sparse(
            ncap_af[Rtp, s, "UP"].where[RpsStg[r, p, s]]
        )
        coef_afups[Rtp[r, v, p], s[stl]].where[RpsStg[r, p, s]] = sparse(
            ncap_afc[Rtp, pgprim, stl]
        )
        coef_afups[r, v, p, s].where[~PrcCap[r, p]] = False
        # Cycling cost annuity
        act_cstup[Rtp[r, v, p], tsl[s], cur].where[Rdcur[r, cur] & stg_maxcyc[Rtp]] = (
            act_cstup[Rtp, tsl, cur]
            * g_drate[r, v, cur]
            / (1 - (1 + g_drate[r, v, cur]) ** -ncap_tlife[Rtp])
        )
        # -----------------------------------------------------------------------------
        # Remove commodity balance equations from non-demand sinks
        project(source=Rtp, target=Trackp)
        project(source=RhsCombal, target=Trackc)
        project(source=ire_flosum, target=Rcs)
        with Loop(Trackp[r, p]):
            Trackc[r, c].where[Top[r, p, c, "IN"]] = True
        Trackc[r, c] = sparse(Sum(RpcIre[Trackp[r, p], c, "EXP"], 1))
        Trackc[Rc] = sparse(Sum(Rcs[Rc, s], 1))
        Trackc[Dem] = True
        Trackc[r, c] = sparse(Sum(RpcNoflo[Trackp[r, p], c], 1))
        RcsCombal[RtcsVarc[r, t, c, s], lA].where[~Trackc[r, c]] = False
        # Reduce overhead from UCU trades
        Trackc[Rc] = ComUnit[Rc, "UCU"].where[~Trackc[Rc]]
        RtcsVarc[r, t, c, s].where[(~RhsComprd[r, t, c, s]).where[Trackc[r, c]]] = False
        TopIre["IMPEXP", c, Trackc, p] = False
        Trackc.setRecords(None)
        Trackp.setRecords(None)
        Rcs.setRecords(None)
        # Filter out UC constraints
        if len(uc_time):
            project(source=uc_time, target=RUc)
            with Loop(RUc[r, ucnA].where[Round(uc_time[ucnA, r, "0"]) == -13]):
                UcOn[RUc] = False
                with If(UcRSum[RUc]):  # type: ignore[arg-type]
                    UcOn[UcRSum[Reg, ucnA]] = False
            uc_time[ucnA, r, t].where[(~UcOn[r, ucnA]).where[RUc[r, ucnA]]] = 0
            RUc.setRecords(None)
        # -----------------------------------------------------------------------------
        # Add singleton ACT_EFFs to COEF_PTRANS or ACT_FLO
        RpCgc[Rpg1ace] = True
        project(source=Rpg1ace, target=Trackpc)
        project(source=RpCgc, target=RpGrp)
        # Convert ACT_EFF factors for reduced flows
        Trackpc[Trackpc] = RpcFfunc[Trackpc]
        act_flo[Rtp[r, v, p], c, s].where[RpcsVar[r, p, c, s] & Trackpc[r, p, c]] = (
            1
            / Sum(
                RpCgc[r, p, cg, c],
                Max(
                    micro,
                    act_eff[Rtp, cg, s]
                    * (1 + (act_eff[Rtp, c, s] - 1).where[act_eff[Rtp, c, s]]),
                ),
            )
        )
        # Convert FLO_FUNCX factors for all reduced flows
        project(source=rtp_ffcx, target=CgGrp, direction="left")
        with Loop(RpcgPtran[Rp, c, Com, cg, cg2].where[CgGrp[Rp, cg, cg2]]):
            with If(RpcFfunc[Rp, c]):  # type: ignore[arg-type]
                RpDcgg[Rp, c, cg, cg2, "UP"] = True
            with Else():  # type: ignore[no-untyped-call]
                RpDcgg[Rp, Com, cg, cg2, "LO"] = True
        RpDcgg[Trackpc[Rp, Com], cg, c, "UP"].where[
            RpCgc[Rp, cg, Com] & RpcAct[Rp, c]
        ] = sparse(CgGrp[Rp, cg, c])
        rtp_ffcx[RtpCapyr[r, v, t, p], Actcg, c].where[RpcFfunc[r, p, c]] = sparse(
            Sum(
                RpDcgg[r, p, c, cg, cg2, lA],
                (power(rtp_ffcx[r, v, t, p, cg, cg2] + 1, bdsig[lA]) - 1).where[  # type: ignore[arg-type]
                    rtp_ffcx[r, v, t, p, cg, cg2] - Min(0, bdsig[lA])
                ],
            )
        )
        with Loop(RpDcgg[r, p, c, cg, cg2, lA]):
            rtp_ffcx[r, v, t, p, cg, cg2] = 0
        # Default to COEF_PTRAN
        RpCgc[r, p, cg, c].where[Trackpc[r, p, c]] = False
        coef_ptran[Rtp[r, v, p], cg, c, Com, s].where[
            RpcsVar[r, p, c, s] & RpcPg[r, p, Com] & RpCgc[r, p, cg, c]
        ] = (
            act_eff[Rtp, cg, s]
            * prc_actflo[Rtp, Com]
            * (1 + (act_eff[Rtp, c, s] - 1).where[act_eff[Rtp, c, s]])
        )
        act_eff[r, ll, p, cg, s].where[RpGrp[r, p, cg]] = 0
        project(source=RpCgc, target=RpGrp)
        RpccFfunc[RpGrp[r, p, cg], Com].where[RpcPg[r, p, Com]] = True

        if condition2:
            RpcgPtran.setRecords(None)

        Trackpc.setRecords(None)
        RpGrp.setRecords(None)
        CgGrp.setRecords(None)
        RpDcgg.setRecords(None)
        RtpCapyr.setRecords(None)
        RpCgc.setRecords(None)

    def exec3(self: CoefExtVda) -> None:
        g = self.tc
        coef_pvt, r, t, fpd, vda_disc, coef_iled, Rtp, p, ncap_bnd, ncap_iled = (
            g.coef_pvt,
            g.r,
            g.t,
            g.fpd,
            g.vda_disc,
            g.coef_iled,
            g.Rtp,
            g.p,
            g.ncap_bnd,
            g.ncap_iled,
        )
        coef_pvt[r, t].where[~coef_pvt[r, t]] = fpd[t]
        vda_disc[r, t] = sparse(coef_pvt[r, t])
        coef_iled[Rtp[r, t, p]].where[ncap_bnd[Rtp, "N"]] = (
            mod(coef_iled[Rtp], 1000) + Number(SpecialValues.EPS).where[ncap_iled[Rtp]]
        )
