# pp_actef_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * PP_ACTEF.MOD : Make the necessary preparations for EQE_ACTEFF equations
# *  - Aggregate / inherit ACT_EFF parameters
# *==============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Domain, Expression, If, Loop, Ord, Parameter, Set, Sum, sparse
from gamspy._symbols.implicits import ImplicitSet
from gamspy.math import abs, project, sqrt

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpActefVda(GamsClass):
    """Translation unit for pp_actef.vda."""

    # Instance attributes
    module_name: str = "pp_actef_vda"
    gams_source: str = "pp_actef.vda"

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
        m = g.container

        if self.arg1 == "LVL":
            g.micro = Parameter(m, "MICRO", records=1e-6)
            self.tc.enqueue(self.exec1)
        else:  # EQUA
            p, cg, rtp_ffcx, rtp_ffcs, r, v, t, PrcVint = (
                g.p,
                g.cg,
                g.rtp_ffcx,
                g.rtp_ffcs,
                g.r,
                g.v,
                g.t,
                g.PrcVint,
            )
            self.env.set_scoped("shg", (p, cg, self.env.pgprim))
            base_shp1 = 1 + rtp_ffcx[r, v, t, *self.env.shg].where[PrcVint[r, p]]
            if self.tc.defined("RTP_FFCS"):
                self.env.set_scoped(
                    "shp1",
                    base_shp1 * (1 + rtp_ffcs[r, v, *self.env.shg, *self.env.sow]),
                )
            else:
                self.env.set_scoped("shp1", base_shp1)

            self.define_equation(
                eq=self.env.eq,
                r_v_t=self.env.r_v_t_GP,
                swt=self.env.swt_GP,
                var=self.env.var,
                sow=self.env.sow_GP,
                shp1=self.env.shp1,
            )

    def define_equation(
        self: PpActefVda,
        eq: str,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...],
        swt: tuple[Set | Alias, ...] | tuple[()],
        var: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        shp1: Expression,
    ) -> None:
        g = self.tc
        rts = macro.rts(s=g.s, g=self.tc, env=self.env)
        (
            RtpVintyr,
            p,
            cg,
            io,
            RpcAce,
            r,
            c,
            ComGmap,
            TsMap,
            s,
            ts,
            act_eff,
            v,
            t,
            RtpcsVarf,
            TsAnn,
            PrcTs,
            rs_fr,
            RpPgflo,
            RpcPg,
            RpPgact,
            prc_actflo,
            RpgPace,
            RpPl,
            lA,
            act_lospl,
            RpsS1,
            RpgAce,
        ) = (
            g.RtpVintyr,
            g.p,
            g.cg,
            g.io,
            g.RpcAce,
            g.r,
            g.c,
            g.ComGmap,
            g.TsMap,
            g.s,
            g.ts,
            g.act_eff,
            g.v,
            g.t,
            g.RtpcsVarf,
            g.TsAnn,
            g.PrcTs,
            g.rs_fr,
            g.RpPgflo,
            g.RpcPg,
            g.RpPgact,
            g.prc_actflo,
            g.RpgPace,
            g.RpPl,
            g.lA,
            g.act_lospl,
            g.RpsS1,
            g.RpgAce,
        )

        VAR_FLO = g.get_variable(f"{var}_FLO")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_UPS = g.get_variable(f"{var}_UPS")

        eqe_acteff = g.get_equation(f"{eq}e_acteff")

        eqe_acteff[RtpVintyr[*r_v_t, p], cg, io, rts, *swt].where[
            RpsS1[r, p, s] & RpgAce[r, p, cg, io]
        ] = Sum(  # Sum over input flows
            Domain(RpcAce[r, p, c], ComGmap[r, cg, c], TsMap[r, s, ts]).where[
                RtpcsVarf[r, t, p, c, ts]
            ],
            (1 + (act_eff[r, v, p, c, ts] - 1).where[act_eff[r, v, p, c, ts]])
            * VAR_FLO[r, v, t, p, c, ts, *sow],
            # Multiply with group efficiency
        ) * Sum(TsAnn[s, ts], act_eff[r, v, p, cg, ts]) * shp1 == (
            Sum(
                PrcTs[r, p, ts].where[rs_fr[r, s, ts]],
                rs_fr[r, s, ts]
                * (
                    # COM_FR needs to be taken into account if process operates above S
                    VAR_ACT[r, v, t, p, ts, *sow].where[~RpPgflo[r, p]]
                    + (
                        Sum(
                            RpcPg[r, p, c],
                            (
                                VAR_ACT[r, v, t, p, ts, *sow].where[RpPgact[r, p]]
                                + (
                                    VAR_FLO[r, v, t, p, c, ts, *sow]
                                    / prc_actflo[r, v, p, c]
                                ).where[~RpPgact[r, p]]
                            )
                            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow)),
                        )
                    ).where[RpPgflo[r, p]]
                ),
            )
        ).where[~RpgPace[r, p, cg]] + (
            # Handle the special cases where ACT_EFF has been specified for PG commodities
            Sum(
                PrcTs[r, p, ts].where[rs_fr[r, s, ts]],
                rs_fr[r, s, ts]
                * Sum(
                    RpcPg[r, p, c],
                    (
                        VAR_ACT[r, v, t, p, ts, *sow].where[RpPgact[r, p]]
                        + (
                            VAR_FLO[r, v, t, p, c, ts, *sow] / prc_actflo[r, v, p, c]
                        ).where[~RpPgact[r, p]]
                    )
                    / (1 + (act_eff[r, v, p, c, ts] - 1).where[act_eff[r, v, p, c, ts]])
                    * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow)),
                ),
            )
        ).where[RpgPace[r, p, cg]] + Sum(  # Partial loads
            RpPl[r, p, lA["FX"]],
            act_lospl[r, v, p, lA]
            * Sum(
                PrcTs[r, p, ts].where[rs_fr[r, s, ts]],
                VAR_UPS[r, v, t, p, ts, lA, *sow] * rs_fr[r, s, ts],
            ),
        )

    def exec1(self: PpActefVda) -> None:
        g = self.tc
        (
            Uncd7,
            CgGrp,
            RpcAce,
            Rpc,
            r,
            p,
            c,
            Rpg1ace,
            KeepFlof,
            RpgAce,
            RpPgact,
            cg,
            io,
            Top,
            ComGmap,
            RpgPace,
            RpPl,
            RpGrp,
            act_eff,
            ll,
            s,
            RpcPg,
            RpcSpg,
            Rtp,
            v,
            vda_flop,
            tsl,
            stoa,
            RpcsVar,
            RpsS1,
            norts,
            Miyr1,
            t,
            j,
            item,
            ts,
            Pastmile,
            stl,
            MyTs,
            TsGroup,
            ts_array,
            RsTree,
            Finest,
            g_yrfr,
            RsBelow,
            allts,
            TsMap,
            sl,
            Fscks,
            Ffcks,
            stoal,
        ) = (
            g.Uncd7,
            g.CgGrp,
            g.RpcAce,
            g.Rpc,
            g.r,
            g.p,
            g.c,
            g.Rpg1ace,
            g.KeepFlof,
            g.RpgAce,
            g.RpPgact,
            g.cg,
            g.io,
            g.Top,
            g.ComGmap,
            g.RpgPace,
            g.RpPl,
            g.RpGrp,
            g.act_eff,
            g.ll,
            g.s,
            g.RpcPg,
            g.RpcSpg,
            g.Rtp,
            g.v,
            g.vda_flop,
            g.tsl,
            g.stoa,
            g.RpcsVar,
            g.RpsS1,
            g.norts,
            g.Miyr1,
            g.t,
            g.j,
            g.item,
            g.ts,
            g.Pastmile,
            g.stl,
            g.MyTs,
            g.TsGroup,
            g.ts_array,
            g.RsTree,
            g.Finest,
            g.g_yrfr,
            g.RsBelow,
            g.allts,
            g.TsMap,
            g.sl,
            g.Fscks,
            g.Ffcks,
            g.stoal,
        )
        Uncd7.setRecords(None)

        # Save commodity ACT_EFF partitions
        CgGrp[RpcAce[Rpc[r, p, c]], c] = True
        project(source=Rpg1ace, target=KeepFlof)
        Rpg1ace.setRecords(None)

        # Catch singleton groups
        with Loop(  # noqa: SIM117
            RpgAce[RpPgact[r, p], cg, io].where[
                Sum(Top[r, p, c, io].where[ComGmap[r, cg, c]], 1) <= 1
            ]
        ):
            with If(~RpgPace[r, p, cg] + RpPl[r, p, "FX"]):  # type: ignore[arg-type]
                RpGrp[r, p, cg] = True
                Rpg1ace[RpGrp[r, p, cg], c].where[
                    Top[r, p, c, io].where[ComGmap[r, cg, c]]
                ] = True
        # Accept EPS for shadow group flows only
        act_eff[r, ll, p, c, s].where[
            (RpcPg[r, p, c] + KeepFlof[r, p, c]).where[
                (act_eff[r, ll, p, c, s] == 0).where[act_eff[r, ll, p, c, s]]
            ]
        ] = 0
        with Loop(RpgAce[RpcSpg[r, p, c], io]):
            act_eff[Rtp[r, v, p], c, s].where[act_eff[Rtp, c, s]] = sqrt(
                abs(act_eff[Rtp, c, s])
            )
        # Store all flow level commodities in CG_GRP
        CgGrp[Rpg1ace] = True
        RpgAce[RpGrp, io] = False

        # Inherit values to target timeslices when possible
        vda_flop[r, ll.lag(Ord(ll)), p, cg, s.lag(Ord(s))].where[stoal[r, s]] = sparse(
            act_eff[r, ll, p, cg, s]
        )
        project(source=vda_flop, target=RpcAce)
        vda_flop.setRecords(None)
        Uncd7["1", CgGrp[RpcAce[r, p, cg], c], tsl, s + stoa[s]].where[
            TsGroup[r, tsl, s]
        ] = sparse(RpcsVar[r, p, c, s])
        Uncd7["2", RpgAce[RpcAce[r, p, cg], io], tsl, s + stoa[s]] = sparse(
            RpsS1[r, p, s]
        )
        CgGrp[RpcAce, c] = False
        if len(norts):
            with Loop((Miyr1[t], Uncd7[j, r, p, cg, item, ts, ts])):  # type: ignore[arg-type]
                act_eff[Rtp[r, v, p], cg, s].where[
                    norts[r, v, s] + norts[r, t, s].where[Pastmile[v]]
                ] = 0
        RpcAce.setRecords(None)

        # Aggregate values to target timeslices when inheritance could not be done
        with Loop(RpgAce[r, p, cg, io]):
            RpcAce[r, p, c].where[Top[r, p, c, io].where[ComGmap[r, cg, c]]] = True
        RpcAce[KeepFlof] = False
        with Loop(Uncd7[j, r, p, cg, item, tsl, stl]):
            MyTs[s] = TsGroup[r, tsl, s]
            with Loop(Rtp[r, v, p]):
                ts_array[s] = act_eff[r, v, p, cg, s]
                act_eff[r, v, p, cg, MyTs].where[~ts_array[MyTs]] = (
                    Sum(
                        RsTree[Finest[r, s], MyTs],
                        g_yrfr[r, s]
                        * (
                            ts_array[s]
                            + Sum(
                                RsBelow[r, allts, s].where[
                                    ~(
                                        Sum(
                                            TsMap[r, sl, s].where[
                                                RsBelow[r, allts, sl]
                                            ],
                                            ts_array[sl],
                                        ).where[ts_array[allts]]
                                    )
                                ],
                                ts_array[allts],
                            )
                        ),
                    )
                    / g_yrfr[r, MyTs]
                )

        Fscks[CgGrp[r, p, cg, c], cg, s].where[RpcsVar[r, p, c, s]] = True
        project(source=Fscks, target=Ffcks, direction="left")
        act_eff[Rtp[r, v, p], cg, s + stoa[s]].where[
            RpsS1[r, p, s] & stoa[s] & act_eff[Rtp, cg, s]
        ] = 0
        act_eff[Rtp[r, v, p], cg, s].where[~act_eff[Rtp, cg, s]] = sparse(
            Sum(Ffcks[r, p, cg, cg, s], act_eff[r, v, p, cg, "ANNUAL"])
        )
        Ffcks.setRecords(None)
        Fscks.setRecords(None)
        CgGrp.setRecords(None)
