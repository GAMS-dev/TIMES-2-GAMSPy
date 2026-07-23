# prep_ext_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.VDA oversees all the added inperpolation activities needed by VEDA
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*
# * Comments: RVP can be used to control flow-related attribs instead of RTP
# *------------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Else, If, Loop, Number, Ord, SpecialValues, Sum
from gamspy.math import Max, Round, abs, map_value, project

from core.base_class import GamsClass
from core.equcrtp_vda import EqucrtpVda, EqucrtpVdaConfig
from core.fillparm_gms import FillparmGms
from core.fillvint_gms import FillvintGms, FillvintGmsConfig
from core.powerflo_vda import PowerfloVda
from core.resloadc_vda import ResloadcVda

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepExtVda(GamsClass):
    """Translation unit for prep_ext.vda."""

    # Instance attributes
    module_name: str = "prep_ext_vda"
    gams_source: str = "prep_ext.vda"

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
        self.arg2 = arg2
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.tc.enqueue(self.prepare_availabilities)

        # fmt: off
        batincludes = [
            ("VDA_EMCB",   "R",      "C,COM",        ",'0','0','0','0'",     "V", "1",          "GE 0",           ""),
            ("NCAP_AFC",   "R",      "P,CG,STL",     ",'0','0','0'",         "V", "RTP(R,V,P)", "GE -1$ACTCG(CG)",""),
            ("ACT_EFF",    "R",      "P,CG,TS",      ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           "X_RPGS"),
            ("VDA_FLOP",   "R",      "P,CG,TS",      ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           "X_RPGS"),
            ("FLO_EMIS",   "R",      "P,CG,COM,S",   ",'0','0'",             "V", "RVP(R,V,P)", "GE 0",           "X_RPGCS"),
            ("ACT_UPS",    "R",      "P,S,BD",       ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_LOSPL",  "R",      "P,L",          ",'0','0','0','0'",     "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_LOSSD",  "R",      "P,UPT,BD",     ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_SDTIME", "R",      "P,UPT,BD",     ",'0','0','0'",         "V", "RVP(R,V,P)", "GE 0",           ""),
            ("ACT_MAXNON", "R",      "P,UPT",        ",'0','0','0','0'",     "V", "RVP(R,V,P)", "GE 0",           ""),
            ("STG_MAXCYC", "R",      "P",            ",'0','0','0','0','0'", "V", "RTP(R,V,P)", "GE 0",           ""),
        ]
        # fmt: on

        if self.tc.defined("UC_FLOBET"):
            batincludes.append(("UC_FLOBET", "UC_N,R", "P,C", ",'0','0','0'", "T", "1", "GE 0", ""))  # fmt: skip

        if self.tc.defined("COM_CSTBAL"):
            batincludes.append(("COM_CSTBAL", "R", "C,S,ITEM,CUR", ",'0','0'", "T", "1", "GE 0", ""))  # fmt: skip

        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                )
            )

        if self.env.powerflo.upper() == "YES":
            self.include(PowerfloVda(self.tc, self.env, arg1="PREP"))
        if self.tc.defined("GR_VARGEN"):
            self.include(ResloadcVda(self.tc, self.env))

        self.include(EqucrtpVda(self.tc, self.env, EqucrtpVdaConfig(arg1="PREP_EXT")))

        if self.env.vintopt == "1":
            self.include(
                FillvintGms(
                    self.tc,
                    self.env,
                    config=FillvintGmsConfig(
                        arg1=g.vda_flop,
                        arg2=g.r,
                        arg3=(g.p, g.cg, g.ts),
                        arg4="X_RPGS",
                    ),
                )
            )
            self.include(
                FillvintGms(
                    self.tc,
                    self.env,
                    config=FillvintGmsConfig(
                        arg1=g.act_eff,
                        arg2=g.r,
                        arg3=(g.p, g.cg, g.ts),
                        arg4="X_RPGS",
                    ),
                )
            )
        self.tc.enqueue(
            self.tailored_interpolation, waver=self.env.waver.upper() == "YES"
        )

    def prepare_availabilities(self: PrepExtVda) -> None:
        g = self.tc
        r, p, s, c, ll, cg = g.r, g.p, g.s, g.c, g.ll, g.cg

        # Prepare commodity-specific availabilities; NCAP_AFAC overrides NCAP_AFC
        project(g.ncap_afac, g.RpGrp)
        g.ncap_afc[r, g.Datayear, p, cg, "ANNUAL"].where[g.RpGrp[r, p, cg]] = (
            g.ncap_afac[r, g.Datayear, p, cg]
        )
        sparseExpr = g.ncap_afcs[r, ll, p, cg, s]
        g.ncap_afc[r, ll, p, cg, g.stl[s]].where[sparseExpr] = sparseExpr
        g.ncap_afcs.setRecords(None)
        # Collect ACT_EFF groups
        project(g.act_eff, g.RpGrp)
        g.Uncd7.setRecords(None)
        sparseExpr2 = (g.act_eff[r, ll, p, cg, s] > 0).where[g.act_eff[r, ll, p, cg, s]]
        g.Uncd7[
            r,
            ll.lag(Ord(g.ll), "circular"),
            p,
            cg,
            g.s.lag(Ord(g.s), "circular"),
            "",
            "",
        ].where[g.bohyear[g.ll] & sparseExpr2] = sparseExpr2
        with Loop(g.Uncd7[r, ll, p, cg, s, "", ""]):
            g.RpcAce[r, p, cg] = True
        g.Rpg1ace[g.RpGrp[g.Rpc[r, p, c]], c].where[~g.RpcAce[g.Rpc]] = True
        g.RpGrp.setRecords(None)
        sparseExpr3 = g.vda_flop[r, ll, p, c, s]
        g.act_flo[r, ll.lag(Ord(g.ll), "circular"), p, c, s].where[
            g.stoa[s] & sparseExpr3
        ] = sparseExpr3

    def tailored_interpolation(self: PrepExtVda, waver: bool) -> None:
        g = self.tc
        r, p, c, s, t, ll, cg = g.r, g.p, g.c, g.s, g.t, g.ll, g.cg

        g.flo_funcx[r, ll, p, c, cg].where[~g.PrcVint[r, p]] = 0.0
        # ------------------------------------------------------------------------------
        #  Tailored interpolation of PRC_RESID
        g.prc_ymax.setRecords(None)
        g.my_array.setRecords(None)
        sparseExpr = g.prc_resid[r, "0", p]
        g.Trackp[r, p].where[sparseExpr] = sparseExpr
        g.prc_ymax[g.Trackp[r, p]] = Round(g.prc_resid[r, "0", p])

        with Loop(g.PyrS[g.pyr[ll]]):
            g.prc_resid[r, "0", p].where[g.Trackp[r, p]] = Max(
                1.0,
                g.ncap_tlife[r, ll, p] + g.g_tlife.where[~g.ncap_tlife[r, ll, p]],
            )
            with Loop(g.Trackp[r, p]):
                g.dfunc[...] = g.prc_ymax[r, p]
                g.my_array[g.DmYear] = g.prc_resid[r, g.DmYear, p]
                g.my_f[...] = 0.0
                g.f[...] = 0.0
                g.z[...] = 0.0
                # do interpolate
                with Loop(g.DmYear.where[g.my_array[g.DmYear]]):
                    g.last_val[...] = g.my_f
                    g.my_f[...] = g.my_array[g.DmYear]
                    g.z[...] = g.yearval[g.DmYear]
                    with If(g.last_val):
                        g.prc_resid[r, t, p].where[
                            ((g.z > g.m[t]).where[(g.m[t] > g.my_fyear)])
                        ] = g.my_f - (g.my_f - g.last_val) / (g.z - g.my_fyear) * (
                            g.z - g.m[t]
                        )
                    with Else():  # type: ignore[no-untyped-call]
                        g.f[...] = g.z
                    g.my_fyear[...] = g.z
                    g.cnt[...].where[(g.last_val + g.my_f > 0.0)] = g.z
                # If only one RESID Interpolate towards EPS at Z+TLIFE
                with If(abs(g.dfunc - 10.0) == 5.0):
                    g.dfunc[...] = g.f
                    g.f[...] = g.z
                with Else():  # type: ignore[no-untyped-call]
                    g.f[...].where[g.dfunc] = 0.0
                with If(g.z == g.f):
                    g.cnt[...] = g.prc_resid[r, "0", p]
                    g.z[...] = g.f + g.cnt
                    g.dfunc[...] = g.dfunc + g.cnt
                    g.prc_resid[r, t, p].where[(g.m[t] > g.f)] = g.my_f * Max(
                        0.0, 1.0 - (g.m[t] - g.f).where[(g.m[t] >= g.dfunc)] / g.cnt
                    )
                    g.my_f[...] = 0.0
                with Else():  # type: ignore[no-untyped-call]
                    g.z[...] = g.cnt
                if waver:
                    g.prc_ymax[r, p] = g.z + Number(1.0).where[(g.my_f > 0.0)]
                    with If(g.my_f == 0.0):
                        g.prc_resid[r, ll + (g.z - g.miyr_boh), p] = SpecialValues.EPS
            # Initialize PRC_RESID capacity availability:
            g.ncap_tlife[r, ll, p].where[g.Trackp[r, p]] = 1.0
            g.ncap_iled[r, ll, p].where[g.Trackp[r, p]] = 0.0
            g.RtpCptyr[r, ll, t, p].where[
                (
                    ((g.prc_resid[r, t, p] > 0.0) + (g.b[t] < g.prc_ymax[r, p])).where[
                        g.Trackp[r, p]
                    ]
                )
            ] = True
        g.Trackp.setRecords(None)
        # INF-QA override
        g.ifq[...].where[Sum(g.ComType[g.cg[g.r]], 1)] = 0.0
        g.ComLim[g.Rc, g.Bdneq].where[g.ComLim[g.Rc, "FX"]] = False
        # -----------------------------------------------------------------------------
        sparseExpr2 = g.act_ups[g.Rtp, "ANNUAL", "FX"]
        g.act_minld[g.Rtp].where[sparseExpr2] = sparseExpr2
        # Move non-standard share parameters to dedicated parameter
        sparseExpr3 = g.flo_shar[r, g.DmYear, p, c, cg, s, g.bd].where[
            ~(g.ComGmap[r, cg, c] * g.Rpc[r, p, c])
        ]
        g.flo_ashar[r, g.DmYear, p, c, cg, s, g.bd].where[sparseExpr3] = sparseExpr3
        # Process cost-neutral ILEDs
        sparseExpr4 = Sum(
            g.Periodyr[t, g.year].where[g.ncap_bnd[r, g.year, p, "N"]],
            g.ncap_bnd[r, g.year, p, "N"],
        )
        g.rvprl[g.Rtp[r, t, p]].where[sparseExpr4] = sparseExpr4

        if g.rvprl.number_records:
            with Loop(g.Rtp[r, t, p].where[g.rvprl[g.Rtp]]):
                g.z[...] = g.rvprl[g.Rtp]
                g.z[...] = g.z / Round(g.z / g.m[t])
                g.ncap_bnd[g.Rtp, "N"] = g.z
                g.coef_iled[g.Rtp] = abs(g.ncap_iled[g.Rtp]) + 1000.0
                g.ncap_iled[g.Rtp] = Max(SpecialValues.EPS, g.z + 1.0 - g.b[t])
            g.ncap_bnd[g.Rtp, g.Bdupx].where[
                (map_value(g.ncap_bnd[g.Rtp, g.Bdupx]).where[g.rvprl[g.Rtp]])
            ] = 0.0
            g.rvprl.setRecords(None)
