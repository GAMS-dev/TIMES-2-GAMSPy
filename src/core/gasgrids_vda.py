# gasgrids_vda.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# Gasgrids - define gasgrid equations
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Card,
    Domain,
    Else,
    Equation,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Set,
    Sum,
    Variable,
    set_options,
    sparse,
)
from gamspy.math import Max, Min, Round, ceil, exp, log, power, project, sqrt

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

PhaseName = Literal["", "DECL", "MODEL"]


class GasgridsVda(GamsClass):
    """Translation unit for gasgrids.vda."""

    # Instance attributes
    module_name: str = "gasgrids_vda"
    gams_source: str = "gasgrids.vda"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: PhaseName = ""
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self: GasgridsVda) -> None:
        # exit file if no records for GG_KGF
        gg_kgf = self.tc.gg_kgf
        if not gg_kgf.number_records:
            return

        # Manages $GOTO
        if self.arg1 == "":
            self._init_phase()
        elif self.arg1 == "DECL":
            self._declaration_phase()
        elif self.arg1 == "MODEL":
            self._model_phase()
        else:
            raise ValueError("Wrong argument passed.")

    def _init_phase(self: GasgridsVda) -> None:
        g = self.tc
        m = g.container

        r, t, p, c, j, year = g.r, g.t, g.p, g.c, g.j, g.year

        gg_wn = 19
        # Internal SETs and Parameters

        g.GgArc = Set(
            m,
            name="GG_ARC",
            domain=[g.allreg, c, g.allreg, c],
            description="Undirected grid edges",
        )
        g.GgTop = Set(
            m,
            name="GG_TOP",
            domain=[g.allr, c, g.allr, c, p],
            description="Undirected grid pipeline topology",
        )
        g.GgLink = Set(
            m,
            name="GG_LINK",
            domain=[g.allr, p, c, g.allr, c],
            description="Directed grid pipeline topology",
        )
        g.GgEdge = Set(
            m,
            name="GG_EDGE",
            domain=[g.allr, p, g.allr],
            description="Undirected grid pipeline topology",
        )
        g.GgWink = Set(
            m,
            name="GG_WINK",
            domain=[g.allr, p, c, g.allr, c],
            description="Alternate Weymouth topology",
        )
        g.GgRtc = Set(
            m, name="GG_RTC", domain=[r, year, c], description="Grid nodes by period"
        )
        g.GgRtpc = Set(
            m,
            name="GG_RTPC",
            domain=[r, g.Milestonyr, p, c],
            description="Grid pipelines by period",
        )
        g.GgWtx = Set(
            m,
            name="GG_WTX",
            domain=[r, p, c],
            description="Pipelines with Taylor expansion",
        )
        g.Omg = Set(m, name="OMG", domain=[j], records=list(range(1, 52)))
        g.GgO = Set(m, name="GG_O", domain=[j], records=list(range(1, gg_wn + 1)))
        g.GgVi = Set(m, name="GG_VI", domain=[j], records=["1", "2", "99"])

        g.gg_m1 = Parameter(m, name="GG_M1", records=0)
        g.gg_mm = Parameter(
            m, name="GG_MM", domain=[r, t, p, c], description="Big-M estimates"
        )
        g.gg_ppm = Parameter(
            m,
            name="GG_PPM",
            domain=[r, year, p, c, r, c, j],
            description="Alternate pressure points",
        )
        g.gg_ppw = Parameter(
            m,
            name="GG_PPW",
            domain=[r, year, p, c, r, c, j],
            description="Alternate Weymouth points",
        )

        # Set global SOLMIP to True if G_PP has records
        if g.gg_pp.number_records:
            self.env.set_global("solmip", "YES")

        self.tc.enqueue(self.collect_gas_grid_node)
        self.tc.enqueue(self.prepare_control_sets)
        self.tc.enqueue(self.sync_kgf_and_klp)
        self.tc.enqueue(self.bounds_gamma_links)
        self.tc.enqueue(self.assign_gg, solmip=self.env.solmip)
        self.tc.enqueue(self.autogenerate_pressure_points)
        self.tc.register_assignment(self.tc.gg_mm)
        self.tc.enqueue(self.gamma_controls_bigM)

    def collect_gas_grid_node(self: GasgridsVda) -> None:
        g = self.tc
        r, c, j = g.r, g.c, g.j
        project(g.gg_pp, g.GgWtx)
        g.Trackc[r, c] = sparse(Sum(g.NrgGmap[r, "GAS", c], g.gg_dens[r, c]))
        # Collect gas grid nodes according to GG_DEMS
        with Loop(g.GrGrid[j, g.Trackc]):
            g.gg_dens[r, c].where[(~g.gg_dens[r, c]) & g.GrGrid[j, r, c]] = g.gg_dens[
                g.Trackc
            ]
        project(source=g.gg_dens, target=g.Trackc)

    def prepare_control_sets(self: GasgridsVda) -> None:
        g = self.tc
        r, c, p, t, Rc = g.r, g.c, g.p, g.t, g.Rc

        g.GgRtc[g.RcGrid[r, t, c]] = sparse(g.Trackc[r, c])
        g.Trackp[g.RpIre[r, p]].where[
            Sum(g.Trackc[r, c].where[g.gr_flow[r, p, c]], 1)
        ] = True
        g.GgRtpc[g.Rtp[r, t, p], c].where[
            (g.GgRtc[r, t, c].where[g.gr_flow[r, p, c]])
        ] = True
        g.GgArc[g.GrArc[g.Trackc[r, c], Rc]] = True
        g.GgTop[g.TopIre[g.Trackc[r, c], Rc, p]].where[g.Trackp[r, p]] = True
        project(source=g.GgTop, target=g.GgLink, direction="left")
        g.GgTop.setRecords(None)
        project(source=g.GgLink, target=g.GgEdge, direction="left")
        g.GgTop[g.GrTop[g.Trackc[r, c], Rc, p]] = True

    def sync_kgf_and_klp(self: GasgridsVda) -> None:
        g = self.tc
        r, c, p, t, Reg, Com, com2 = g.r, g.c, g.p, g.t, g.Reg, g.Com, g.com2

        with Loop(g.GgTop[r, c, Reg, Com, p]):
            g.gg_kgf[r, t, p, c].where[~(g.gg_kgf[r, t, p, c])] = sparse(
                g.gg_kgf[Reg, t, p, Com]
            )

            g.gg_kgf[Reg, t, p, Com].where[~(g.gg_kgf[Reg, t, p, Com])] = sparse(
                g.gg_kgf[r, t, p, c]
            )

            g.gg_klp[r, t, p, c].where[~(g.gg_klp[r, t, p, c])] = sparse(
                g.gg_klp[Reg, t, p, Com]
            )

            g.gg_klp[r, t, p, com2[g.Actcg]].where[~(g.gg_klp[r, t, p, com2])] = (
                g.gg_klp[Reg, t, p, com2]
            )

            g.gg_klp[Reg, t, p, Com] = 0

            with If(~r.sameAs(Reg)):
                g.gg_klp[Reg, t, p, com2] = 0

    def bounds_gamma_links(self: GasgridsVda) -> None:
        g = self.tc
        r, c, p, t, Reg, Com, Rtc, bd = g.r, g.c, g.p, g.t, g.Reg, g.Com, g.Rtc, g.bd

        # * Try ensuring all nodes have pressure bounds
        g.gg_prbd[g.GgRtc[Rtc], bd["UP"]].where[
            g.gg_prbd[Rtc, bd] < g.gg_prbd[Rtc, "LO"]
        ] = sparse(g.gg_prbd[Rtc, "LO"])
        g.gg_prbd[g.GgRtc[Rtc], bd["LO"]].where[
            g.gg_prbd[Rtc, bd] > g.gg_prbd[Rtc, "UP"]
        ] = sparse(g.gg_prbd[Rtc, "UP"])
        # * Default for Gamma
        g.gg_gamma[g.GgRtpc[r, t, p, c]].where[~(g.RpcIre[r, p, c, "EXP"])] = 1.0
        g.gg_gamma[g.GgRtpc[r, t, p, c]].where[
            (g.gg_gamma[r, t, p, c] < 1.0 + 1.0 / 128.0)
        ] = 1.0
        # * Get bidirectional links
        with Loop(g.GgLink[r, p, c, Reg, Com].where[g.GgLink[Reg, p, Com, r, c]]):
            g.Trackpc[r, p, c] = True

    def assign_gg(self: GasgridsVda, solmip: str) -> None:
        g = self.tc
        if solmip.upper() == "YES":
            g.gg_m1[...] = 1
        else:
            g.GgWtx[g.Trackpc] = False

    def autogenerate_pressure_points(self: GasgridsVda) -> None:
        g = self.tc
        (r, c, p, t, f, z, j, ll, Reg, Com, my_f, Rc) = (
            g.r,
            g.c,
            g.p,
            g.t,
            g.f,
            g.z,
            g.j,
            g.ll,
            g.Reg,
            g.Com,
            g.my_f,
            g.Rc,
        )

        # * Autogenerate pressure points when needed
        g.GgWtx[g.Trackpc[r, p, c]].where[
            Sum(g.GgLink[r, p, c, Reg, Com].where[g.GgWtx[Reg, p, Com]], 1)
        ] = True
        with Loop(Domain(g.GgRtpc[r, t, p, c], g.GgLink[r, p, c, Reg, Com])):
            g.cnt[...] = Round(
                Max(
                    0.0,
                    g.gg_pp[r, "0", p, c, "N", "1"],
                    g.gg_pp[Reg, "0", p, Com, "N", "1"],
                )
            )
            f[...] = z
            g.dfunc[...] = g.GgWtx[r, p, c].where[g.cnt]
            with If((~g.dfunc) | g.cnt):
                g.cnt[...] = Min(50, g.cnt)
                f[...] = g.gg_prbd[r, t, c, "UP"] * Max(1.0, g.gg_gamma[r, t, p, c])
                z[...] = Max(f * 0.1, g.gg_prbd[Reg, t, Com, "LO"])

            with If(f > z):
                with If(g.dfunc):
                    with If(g.cnt < 9.0):
                        my_f[...] = 1.25
                    with Else():  # type: ignore
                        my_f[...] = ((1.0 - z[...] / f[...]) / 0.001) ** (1.0 / g.cnt)
                    g.cnt[...] = (
                        ceil(log((1.0 - z[...] / f[...]) / 0.001) / log(my_f) - 0.001)
                        + 1.0
                    )
                    g.gg_pp[r, t, p, c, "UP", g.Omg[j]].where[(Ord(j) <= g.cnt)] = f
                    g.gg_pp[Reg, t, p, Com, "LO", g.Omg[j]].where[(Ord(j) <= g.cnt)] = (
                        f * (1.0 - 0.001 * power(my_f, Ord(j) - 1.0))
                    )
                with Else():  # type: ignore
                    g.cnt[...] = Card(g.GgO)  # type: ignore
                    my_f[...] = 1.283
                    g.dfunc[...] = 0.233
                    g.done[...] = (
                        (1.0 - z / f) * g.dfunc / (g.cnt / 2.0 * (g.cnt - 1.0))
                    )
                    g.cnt[...] = g.cnt[...] - 1.0 + g.gg_m1 / 2.0
                    z[...] = (1.0 - z / f) * (1.0 - g.dfunc) / (my_f**g.cnt)
                    g.gg_ppm[r, t, p, c, Reg, Com, g.GgO[j]] = f * (
                        1.0
                        - z * power(my_f, Ord(j) - 1.0)
                        - Ord(j) / 2.0 * (Ord(j) - 1.0) * g.done
                    )

        g.gg_pp[r, ll, p, c, "N", g.Omg] = 0.0

        project(source=g.gg_pp, target=g.GgWtx)
        project(source=g.gg_pp, target=g.Omg)
        g.gg_ppm[g.GgRtpc[r, t, p, c], r, c, g.GgO[j]].where[~(g.GgWtx[r, p, c])] = (
            g.gg_prbd[r, t, c, "UP"] * Max(1.0, g.gg_gamma[r, t, p, c])
        )
        g.gg_ppw[g.GgRtpc[r, t, p, c], Rc, g.GgO[j]].where[
            (~(g.GgWtx[r, p, c])).where[g.gg_ppm[r, t, p, c, Rc, j]]
        ] = sqrt(
            power(g.gg_ppm[r, t, p, c, r, c, j], 2.0)
            - power(g.gg_ppm[r, t, p, c, Rc, j], 2.0)
        )

    def gamma_controls_bigM(self: GasgridsVda) -> None:
        g = self.tc
        r, c, p, t, j, ie, Rc, Com, Reg, Annual = (
            g.r,
            g.c,
            g.p,
            g.t,
            g.j,
            g.ie,
            g.Rc,
            g.Com,
            g.Reg,
            g.Annual,
        )
        # * Reset GAMMA for non-compressor links (no bidirectional reset)
        g.gg_gamma[g.GgRtpc[r, t, p, c]].where[
            (g.gg_gamma[r, t, p, c] < 1.0 + 1.0 / 128.0)
        ] = 0.0
        # * Finalise some controls
        g.GgRtpc[r, t, p, c].where[~(g.gg_kgf[r, t, p, c])] = False
        set_options({"VALIDATION": 0})
        g.gg_klp[g.Rtpc[r, t, p, c]].where[~(g.GgRtpc[g.Rtpc])] = 0.0
        set_options({"VALIDATION": 1})
        with Loop(g.GgLink[g.GgWtx[r, p, c], Reg, Com]):
            g.gg_pp[r, t, p, c, "UP", g.Omg].where[
                (
                    g.gg_pp[r, t, p, c, "UP", g.Omg]
                    <= g.gg_pp[Reg, t, p, Com, "LO", g.Omg]
                )
            ] = 0.0
        g.ire_flosum[g.GgRtpc[r, t, p, c], Annual, ie, c, "IN"].where[
            ~(g.RpcIre[r, p, c, ie])
        ] = sparse(g.RpcIre[r, p, c, "IMP"])
        g.GgWink[g.GgLink[r, p, c, Rc]].where[~(g.GgWtx[r, p, c])] = True
        # * Estimates for Big-M
        g.gg_mm[g.GgRtpc[r, t, p, c]] = (
            Max(60.0, g.gg_prbd[r, t, c, "UP"])
            * Max(1.0, g.gg_gamma[r, t, p, c])
            * g.gg_kgf[r, t, p, c]
        )
        g.gg_ppw[g.GgRtpc[r, t, p, c], r, c, "1"].where[g.GgWtx[r, p, c]] = Sum(
            g.Omg.where[g.gg_pp[r, t, p, c, "UP", g.Omg]], 1
        )
        g.gg_kgf[g.GgRtpc].where[
            ~(Sum(Domain(Rc, j).where[g.gg_ppw[g.GgRtpc, Rc, j]], 1))
        ] = 0.0
        g.Trackc.setRecords(None)
        g.Trackpc.setRecords(None)
        g.Trackp.setRecords(None)

    def _declaration_phase(self: GasgridsVda) -> None:
        g = self.tc
        m = g.container
        r, c, p, t, j, s = (
            g.r,
            g.c,
            g.p,
            g.t,
            g.j,
            g.s,
        )

        g.VAR_GG_PR = Variable(
            m,
            name="VAR_GG_PR",
            domain=[r, t, c, s],
            description="Nodal pressures",
            type="POSITIVE",
        )
        g.VAR_GG_MF = Variable(
            m,
            name="VAR_GG_MF",
            domain=[r, t, p, c, r, c, s],
            description="Mass flows of gases",
            type="POSITIVE",
        )
        g.VAR_GG_PDIF = Variable(
            m,
            name="VAR_GG_PDIF",
            domain=[r, t, p, c, r, c, s],
            description="Pressure differences over pipeline",
            type="POSITIVE",
        )
        g.VAR_GG_PADD = Variable(
            m,
            name="VAR_GG_PADD",
            domain=[r, t, p, c, s],
            description="Pressure boost due to compressor at input node",
            type="POSITIVE",
        )
        g.VAR_GG_STEP = Variable(
            m,
            name="VAR_GG_STEP",
            domain=[r, t, p, c, s, j],
            description="Alternate step variables",
            type="POSITIVE",
        )

        var_type = "BINARY" if self.env.solmip.upper() == "YES" else "POSITIVE"
        g.VAR_GG_Y = Variable(m, name="VAR_GG_Y", domain=[r, t, p, c, s], type=var_type)

        self.tc.enqueue(self.delete_eq_ire)
        self.tc.enqueue(self.bounds_for_pressure_and_linepack, pgprim=self.env.pgprim)
        self.tc.enqueue(self.fix_reserve_pressure_difference)
        self.equations()

    def delete_eq_ire(self: GasgridsVda) -> None:
        """Delete EQ_IRE for all with gg_klp defined"""
        g = self.tc
        r, c, p, ie, Reg, Com = (
            g.r,
            g.c,
            g.p,
            g.ie,
            g.Reg,
            g.Com,
        )

        project(source=g.gg_klp, target=g.Trackpc)
        g.Trackpc[r, p, c].where[~(g.gr_flow[r, p, c])] = False
        with Loop(g.GgLink[g.Trackpc[r, p, c], Reg, Com]):
            g.RpcEqire[Reg, p, Com, ie] = False

    def bounds_for_pressure_and_linepack(self: GasgridsVda, pgprim: str) -> None:
        """Bounds for pressures and linepack"""
        g = self.tc
        r, c, p, t, s, Reg, Com = (
            g.r,
            g.c,
            g.p,
            g.t,
            g.s,
            g.Reg,
            g.Com,
        )
        with Loop(g.GgTop[r, c, Reg, Com, p]):
            g.VAR_GG_PR.lo[g.GgRtc[r, t, c], s].where[g.PrcTs[r, p, s]] = g.gg_prbd[
                r, t, c, "LO"
            ]
            g.VAR_GG_PR.up[g.GgRtc[r, t, c], s].where[g.PrcTs[r, p, s]] = g.gg_prbd[
                r, t, c, "UP"
            ]
            g.VAR_GG_PR.lo[g.Rtc[Reg, t, Com], s].where[g.PrcTs[r, p, s]] = g.gg_prbd[
                g.Rtc, "LO"
            ]
            g.VAR_GG_PR.up[g.Rtc[Reg, t, Com], s].where[g.PrcTs[r, p, s]] = g.gg_prbd[
                g.Rtc, "UP"
            ]

        g.VAR_GG_PADD.lo[g.Rtp[r, t, p], Com[pgprim], s].where[
            (g.PrcTs[r, p, s].where[g.gg_klp[r, t, p, Com]])
        ] = Sum(
            g.RpcIre[g.Trackpc[r, p, c], "EXP"],
            Min(
                (
                    g.gg_prbd[r, t, c, "UP"] * Max(1.0, g.gg_gamma[r, t, p, c])
                    + g.gg_prbd[r, t, c, "LO"]
                )
                / 2.0
                * g.gg_klp[r, t, p, c],
                g.gg_klp[r, t, p, Com],
            )
            * g.gg_dens[r, c]
            * g.rs_stgprd[r, s],
        )

    def fix_reserve_pressure_difference(self: GasgridsVda) -> None:
        """Fix reverse pressure difference to zero for unidirectional case"""
        g = self.tc
        r, c, p, t, s, Rc, Reg, Com = (
            g.r,
            g.c,
            g.p,
            g.t,
            g.s,
            g.Rc,
            g.Reg,
            g.Com,
        )
        g.VAR_GG_PDIF.fx[g.GgRtpc[Reg, t, p, Com], r, c, s].where[
            (
                (~(g.GgLink[Reg, p, Com, r, c])).where[
                    g.GgLink[r, p, c, Reg, Com] & g.PrcTs[Reg, p, s]
                ]
            )
        ] = 0.0
        g.VAR_GG_STEP.up[g.RtpcsVarf[g.GgRtpc[r, t, p, c], s], g.GgO].where[
            Sum(g.GgLink[r, p, c, Rc].where[g.gg_ppw[r, t, p, c, Rc, g.GgO]], 1)
        ] = exp(1)
        g.VAR_GG_Y.up[g.RtpcsVarf[g.GgRtpc, s]] = 1.0
        g.Trackpc.setRecords(None)

    def equations(self: GasgridsVda) -> None:
        g = self.tc
        m = g.container

        r, t, p, c, ts, lA, s, j = g.r, g.t, g.p, g.c, g.ts, g.lA, g.s, g.j
        g.eq_gg_gama = Equation(
            m,
            name="EQ_GG_GAMA",
            domain=[r, t, p, c, r, c, ts],
            description="Maximum pressure increase due to compressor",
        )
        g.eq_gg_mflo = Equation(
            m,
            name="EQ_GG_MFLO",
            domain=[r, t, p, c, r, c, ts],
            description="Standard IRE flows to mass flows (2-way)",
        )
        g.eq_gg_mbnd = Equation(
            m,
            name="EQ_GG_MBND",
            domain=[r, t, p, c, r, c, lA, ts],
            description="Mass flow bound by pressure difference (2-way)",
        )
        g.eq_gg_hlip = Equation(
            m,
            name="EQ_GG_HLIP",
            domain=[r, t, p, c, r, c, ts],
            description="Linepack storage balance (1-way)",
        )
        g.eq_gg_hlev = Equation(
            m,
            name="EQ_GG_HLEV",
            domain=[r, t, p, c, r, c, ts],
            description="Linepack as a funtion of average pressure (1-way)",
        )
        g.eq_gg_step = Equation(
            m,
            name="EQ_GG_STEP",
            domain=[r, t, p, c, r, c, ts],
            description="Stepped linearization (1-way)",
        )
        g.eq_gg_prio = Equation(
            m,
            name="EQ_GG_PRIO",
            domain=[r, t, p, c, r, c, lA, ts],
            description="Pressures at input and output node (2-way)",
        )
        g.eq_gg_pdif1 = Equation(
            m,
            name="EQ_GG_PDIF1",
            domain=[r, t, p, c, r, c, j, ts],
            description="Maximum pressure differences (2-way)",
        )
        g.eq_gg_pdif2 = Equation(
            m,
            name="EQ_GG_PDIF2",
            domain=[r, t, p, c, r, c, ts],
            description="Unsigned pressure differences",
        )
        g.eq_gg_weymst = Equation(
            m,
            name="EQ_GG_WEYMST",
            domain=[r, t, p, c, r, c, lA, ts],
            description="Weymouth stepped linearization (2-way)",
        )
        g.eq_gg_weymtx = Equation(
            m,
            name="EQ_GG_WEYMTX",
            domain=[r, t, p, c, r, c, s, j],
            description="Weymouth Taylor expansion formulation (2-way)",
        )

    def _model_phase(self: GasgridsVda) -> None:
        g = self.tc

        rts_GP = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        r_t_GP = self.env.r_t_GP

        macro.var_gg_pru_active = True
        macro.var_gg_y2_active = True
        macro.var_gg_prio_active = True
        macro.var_gg_hlip_active = True
        macro.var_gg_wslac_active = True
        # * Max pr-diffs in LP vs. MIP CASE
        macro.var_gg_pdmax_active = True

        # * Gas grid equation formulations
        g.eq_gg_mflo[g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.com1], rts_GP].where[
            (g.PrcTs[g.r, g.p, g.s].where[g.GgLink[g.r, g.p, g.c, g.Rc]])
        ] = g.VAR_GG_MF[g.r, g.t, g.p, g.c, g.Rc, g.s] * g.gg_dens[g.r, g.c] * g.g_yrfr[
            g.r, g.s
        ] * 8760.0 == Sum(
            g.TopIre[g.r, g.Com, g.Reg, g.com2, g.p].where[
                (
                    (~(g.GgEdge[g.r, g.p, g.r]))
                    | (
                        ((g.RpcPg[g.r, g.p, g.com2]) ^ (g.RpcPg[g.r, g.p, g.c]))
                        | (g.ComGmap[g.r, g.c, g.Com].where[g.ComGmap[g.Rc, g.com2]])
                    )
                )
            ],
            Sum(
                g.RtpVintyr[g.r, g.v, g.t, g.p],
                (
                    g.VAR_IRE[g.r, g.v, g.t, g.p, g.Com, g.s, "EXP"].where[
                        (~(g.RpcAire[g.r, g.p, g.Com]))
                    ]
                    + g.VAR_ACT[g.r, g.v, g.t, g.p, g.s]
                    * g.prc_actflo[g.r, g.v, g.p, g.Com].where[
                        g.RpcAire[g.r, g.p, g.Com]
                    ]
                )
                / 2.0,
            )
            + Sum(
                g.RtpVintyr[g.Reg, g.v, g.t, g.p],
                (
                    g.VAR_IRE[g.Reg, g.v, g.t, g.p, g.com2, g.s, "IMP"].where[
                        (~(g.RpcAire[g.Reg, g.p, g.com2]))
                    ]
                    + g.VAR_ACT[g.Reg, g.v, g.t, g.p, g.s]
                    * g.prc_actflo[g.Reg, g.v, g.p, g.com2].where[
                        g.RpcAire[g.Reg, g.p, g.com2]
                    ]
                )
                / 2.0,
            ),
        )

        g.eq_gg_gama[g.GgRtpc[*r_t_GP, g.p, g.c], g.Reg, g.Com, rts_GP].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.GgLink[g.r, g.p, g.c, g.Reg, g.Com]
                    & g.gg_gamma[g.r, g.t, g.p, g.c]
                ]
            )
        ] = (
            g.VAR_GG_PADD[g.r, g.t, g.p, g.c, g.s]
            <= (g.gg_gamma[g.r, g.t, g.p, g.c] - 1.0) * g.VAR_GG_PR[g.r, g.t, g.c, g.s]
        )

        g.eq_gg_mbnd[
            g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.Com], g.Lnx[g.lA], rts_GP
        ].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    (
                        g.GgLink[g.Reg, g.p, g.Com, g.r, g.c].where[g.bd[g.lA]]
                        + g.ips[g.lA].where[((~(g.gg_m1)) | (g.GgWtx[g.r, g.p, g.c]))]
                    )
                    & g.GgLink[g.r, g.p, g.c, g.Rc]
                ]
            )
        ] = (
            g.VAR_GG_MF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
            + macro.var_gg_wslac_GP(g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s).where[
                g.GgWink[g.Reg, g.p, g.Com, g.r, g.c]
            ]
            <= (
                (
                    g.gg_mm[g.r, g.t, g.p, g.c]
                    * (
                        macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s)
                        - macro.var_gg_prio_GP(g.Reg, g.t, g.p, g.Com, g.s)
                        + g.VAR_GG_PDIF[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.s].where[
                            g.GgLink[g.Reg, g.p, g.Com, g.r, g.c]
                        ]
                    )
                ).where[g.GgTop[g.r, g.c, g.Rc, g.p]]
                + (
                    g.gg_mm[g.r, g.t, g.p, g.c]
                    * g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
                ).where[g.GgTop[g.Rc, g.r, g.c, g.p]]
            ).where[g.ips[g.lA]]
            + (
                g.gg_kgf[g.r, g.t, g.p, g.c]
                * (
                    macro.var_gg_pdmax_GP(
                        g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s, Number(2), True
                    )
                )
            ).where[g.bd[g.lA]]
        )

        g.eq_gg_weymtx[g.GgRtpc[*r_t_GP, g.p, g.c], g.Reg, g.Com, rts_GP, g.Omg].where[
            (
                g.gg_pp[g.r, g.t, g.p, g.c, "UP", g.Omg].where[
                    g.PrcTs[g.r, g.p, g.s]
                    & g.GgLink[g.r, g.p, g.c, g.Reg, g.Com]
                    & g.GgWtx[g.r, g.p, g.c]
                ]
            )
        ] = g.VAR_GG_MF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s] <= g.gg_kgf[
            g.r, g.t, g.p, g.c
        ] * (
            g.gg_pp[g.r, g.t, g.p, g.c, "UP", g.Omg]
            / sqrt(
                power(g.gg_pp[g.r, g.t, g.p, g.c, "UP", g.Omg], 2.0)
                - power(g.gg_pp[g.Reg, g.t, g.p, g.Com, "LO", g.Omg], 2.0)
            )
            * macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s)
            - g.gg_pp[g.Reg, g.t, g.p, g.Com, "LO", g.Omg]
            / sqrt(
                power(g.gg_pp[g.r, g.t, g.p, g.c, "UP", g.Omg], 2.0)
                - power(g.gg_pp[g.Reg, g.t, g.p, g.Com, "LO", g.Omg], 2.0)
            )
            * (
                macro.var_gg_prio_GP(g.Reg, g.t, g.p, g.Com, g.s)
                - g.VAR_GG_PDIF[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.s].where[
                    g.GgLink[g.Reg, g.p, g.Com, g.r, g.c]
                ]
            )
        )

        g.eq_gg_hlip[g.GgRtpc[*r_t_GP, g.p, g.c], g.Reg, g.Com, rts_GP].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.gg_klp[g.r, g.t, g.p, g.c]
                    & g.GgLink[g.r, g.p, g.c, g.Reg, g.Com]
                    & g.GgArc[g.r, g.c, g.Reg, g.Com]
                ]
            )
        ] = macro.var_gg_hlip_GP(g.r, g.t, g.p, g.s) == macro.var_gg_hlip_GP(
            g.r, g.t, g.p, g.s.lag(g.rs_stg[g.r, g.s], "circular")
        ) + Sum(
            Domain(g.RtpVintyr[g.r, g.v, g.t, g.p], g.RpcIre[g.r, g.p, g.c, g.ie]),
            (
                g.VAR_IRE[g.r, g.v, g.t, g.p, g.c, g.s, g.ie].where[
                    (~(g.RpcAire[g.r, g.p, g.c]))
                ]
                + g.VAR_ACT[g.r, g.v, g.t, g.p, g.s]
                * g.prc_actflo[g.r, g.v, g.p, g.c].where[g.RpcAire[g.r, g.p, g.c]]
            )
            * (Number(2.0).where[g.xpt[g.ie]] - 1.0),
        ) + Sum(
            Domain(
                g.RtpVintyr[g.Reg, g.v, g.t, g.p], g.RpcIre[g.Reg, g.p, g.Com, g.ie]
            ),
            (
                g.VAR_IRE[g.Reg, g.v, g.t, g.p, g.Com, g.s, g.ie].where[
                    (~(g.RpcAire[g.Reg, g.p, g.Com]))
                ]
                + g.VAR_ACT[g.Reg, g.v, g.t, g.p, g.s]
                * g.prc_actflo[g.Reg, g.v, g.p, g.Com].where[
                    g.RpcAire[g.Reg, g.p, g.Com]
                ]
            )
            * (Number(2.0).where[g.xpt[g.ie]] - 1.0),
        )

        g.eq_gg_hlev[g.GgRtpc[*r_t_GP, g.p, g.c], g.Reg, g.Com, rts_GP].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.GgLink[g.r, g.p, g.c, g.Reg, g.Com]
                    & g.GgArc[g.r, g.c, g.Reg, g.Com]
                ]
            )
        ] = (
            macro.var_gg_hlip_GP(g.r, g.t, g.p, g.s)
            == g.gg_klp[g.r, g.t, g.p, g.c]
            * g.gg_dens[g.r, g.c]
            * g.rs_stgprd[g.r, g.s]
            * (
                macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s)
                + macro.var_gg_prio_GP(g.Reg, g.t, g.p, g.Com, g.s)
            )
            / 2.0
        )

        g.eq_gg_pdif1[
            g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.Com], g.GgVi[g.j], rts_GP
        ].where[
            (
                (~(g.GgWtx[g.r, g.p, g.c].where[g.GgO[g.j]])).where[
                    g.GgLink[g.Reg, g.p, g.Com, g.r, g.c]
                    & g.PrcTs[g.r, g.p, g.s]
                    & g.GgLink[g.r, g.p, g.c, g.Rc]
                ]
            )
        ] = (
            g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
            - (
                macro.var_gg_pdmax_GP(
                    g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s, Number(1), False
                )
            )
        ).where[(~(g.GgO[g.j]))] + Sum(
            g.GgO[g.j].where[(Ord(g.j) == 1.0)],
            macro.var_gg_pru_GP(g.r, g.t, g.p, g.c, g.s)
            - g.gg_prbd[g.r, g.t, g.c, "UP"]
            * macro.var_gg_y2_GP(g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s),
        ) + Sum(
            g.GgO[g.j].where[(Ord(g.j) == 2.0)],
            macro.var_gg_pru_GP(g.r, g.t, g.p, g.c, g.s)
            - (
                macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s)
                - g.gg_prbd[g.r, g.t, g.c, "LO"]
                * (1.0 - macro.var_gg_y2_GP(g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s))
            ),
        ) <= 0.0

        g.eq_gg_pdif2[g.GgRtpc[*r_t_GP, g.p, g.c], g.Reg, g.Com, rts_GP].where[
            (
                g.GgLink[g.Reg, g.p, g.Com, g.r, g.c].where[
                    g.PrcTs[g.r, g.p, g.s] & g.GgTop[g.r, g.c, g.Reg, g.Com, g.p]
                ]
            )
        ] = (
            g.VAR_GG_PDIF[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.s]
            == macro.var_gg_prio_GP(g.Reg, g.t, g.p, g.Com, g.s)
            - macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s)
            + g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
        )

        g.eq_gg_step[g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.Com], rts_GP].where[
            (
                ((~(g.gg_m1)) | (0.0)).where[
                    g.PrcTs[g.r, g.p, g.s]
                    & g.GgWink[g.Reg, g.p, g.Com, g.r, g.c]
                    & g.GgWink[g.r, g.p, g.c, g.Rc]
                    & g.GgArc[g.r, g.c, g.Rc]
                ]
            )
        ] = (
            Sum(
                g.j.where[g.gg_ppw[g.r, g.t, g.p, g.c, g.Rc, g.j]],
                g.VAR_GG_STEP[g.r, g.t, g.p, g.c, g.s, g.j],
            )
            + Sum(
                g.j.where[g.gg_ppw[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.j]],
                g.VAR_GG_STEP[g.Reg, g.t, g.p, g.Com, g.s, g.j],
            )
            <= 1.0
        )

        g.eq_gg_prio[
            g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.Com], g.Lnx[g.lA], rts_GP
        ].where[
            (
                g.PrcTs[g.r, g.p, g.s].where[
                    g.GgWink[g.r, g.p, g.c, g.Rc] & g.GgArc[g.r, g.c, g.Rc]
                ]
            )
        ] = (
            macro.var_gg_pru_GP(g.r, g.t, g.p, g.c, g.s)
            + macro.var_gg_pru_GP(g.Reg, g.t, g.p, g.Com, g.s)
            - g.VAR_GG_PDIF[g.Reg, g.t, g.p, g.Com, g.r, g.c, g.s].where[g.ips[g.lA]]
            - g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s].where[g.bd[g.lA]]
        ) == macro.var_gg_prio_GP(g.r, g.t, g.p, g.c, g.s).where[
            g.ips[g.lA]
        ] + macro.var_gg_prio_GP(g.Reg, g.t, g.p, g.Com, g.s).where[
            g.bd[g.lA]
        ] - g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.r, g.c, g.s]

        g.eq_gg_weymst[
            g.GgRtpc[*r_t_GP, g.p, g.c], g.Rc[g.Reg, g.Com], g.bd[g.lA], rts_GP
        ].where[(g.PrcTs[g.r, g.p, g.s].where[g.GgWink[g.r, g.p, g.c, g.Rc]])] = (
            g.VAR_GG_MF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s]
            + macro.var_gg_wslac_GP(g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s)
        ).where[g.Lnx[g.lA]] + (
            g.VAR_GG_PDIF[g.r, g.t, g.p, g.c, g.Reg, g.Com, g.s].where[g.Bdlox[g.bd]]
            + macro.var_gg_pru_GP(g.r, g.t, g.p, g.c, g.s).where[g.Bdupx[g.bd]]
        ).where[g.Bdneq[g.bd]] == (
            g.gg_kgf[g.r, g.t, g.p, g.c]
            * Sum(
                g.j.where[g.gg_ppw[g.r, g.t, g.p, g.c, g.Rc, g.j]],
                g.VAR_GG_STEP[g.r, g.t, g.p, g.c, g.s, g.j]
                * g.gg_ppw[g.r, g.t, g.p, g.c, g.Rc, g.j],
            )
        ).where[g.Lnx[g.lA]] + (
            Sum(
                g.j.where[g.gg_ppw[g.r, g.t, g.p, g.c, g.Rc, g.j]],
                g.VAR_GG_STEP[g.r, g.t, g.p, g.c, g.s, g.j]
                * (
                    g.gg_ppm[g.r, g.t, g.p, g.c, g.r, g.c, g.j]
                    - g.gg_ppm[g.r, g.t, g.p, g.c, g.Rc, g.j]
                ),
            ).where[g.Bdlox[g.bd]]
            + Sum(
                g.j.where[g.gg_ppw[g.r, g.t, g.p, g.c, g.Rc, g.j]],
                g.VAR_GG_STEP[g.r, g.t, g.p, g.c, g.s, g.j]
                * g.gg_ppm[g.r, g.t, g.p, g.c, g.r, g.c, g.j],
            ).where[g.Bdupx[g.bd]]
        ).where[g.Bdneq[g.bd]]
