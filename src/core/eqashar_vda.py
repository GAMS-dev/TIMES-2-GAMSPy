# eqashar_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQx_ASHAR is an ANNUAL level share constraint on flows
# *   %1 - equation declaration type
# *   %2 - BOUND type for %1
# *=============================================================================*
# * Comments:
# *-----------------------------------------------------------------------------
# *$ONLISTING


from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, If, Loop, Number, SpecialValues, Sum, sparse
from gamspy.math import Max, abs, exp, project, same_as

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from core.utils import EquationSenseTypes
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqasharVdaConfig:
    sense: EquationSenseTypes | Literal[""] = ""
    arg2: str = ""


class EqasharVda(GamsClass):
    """Translation unit for eqashar.vda."""

    # Instance attributes
    module_name: str = "eqashar_vda"
    gams_source: str = "eqashar.vda"

    def __init__(
        self: EqasharVda,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqasharVdaConfig,
    ):
        self.env = env.fork()
        self.tc = tc
        self.config = config
        self._sub_modules = {}
        self.compile()

    def compile(self: EqasharVda) -> None:
        g = self.tc
        cc = self.config
        if cc.sense != "":
            self.label_eqdef()
        else:
            self.tc.enqueue(self.collect_all_flo_ashar_groups)
            # * Levelize FLO_ASHAR
            self.include(
                PpLvlfcMod(
                    tc=self.tc,
                    env=self.env,
                    config=PpLvlfcModConfig(
                        arg1=g.flo_ashar,
                        arg2=(g.p,),
                        arg3=g.RpsS2,
                        arg4=(g.bd,),
                        arg5=("",),
                        arg6=g.allts,
                        arg7=(g.v,),
                        arg8=Number(1),
                        arg10=(g.c, g.cg),
                        arg11="N",
                    ),
                )
            )

    def collect_all_flo_ashar_groups(self: EqasharVda) -> None:
        g = self.tc
        r, v, p, c, cg, cg2 = g.r, g.v, g.p, g.c, g.cg, g.cg2
        s, ll, bd, tsl = g.s, g.ll, g.bd, g.tsl

        # Collect all FLO_ASHAR groups
        project(source=g.flo_ashar, target=g.CgGrp, direction="left")
        g.flo_shar[r, "0", p, c, cg, g.Annual, "LO"].where[g.CgGrp[r, p, c, cg]] = (
            SpecialValues.EPS
        )

        # We have been left with any C not in CG or not in RPC
        if g.CgGrp.number_records:
            with Loop(
                Domain(
                    g.CgGrp[g.Rpc[r, p, c], c],
                    g.ComTmap[r, g.ComType[cg], c],
                )
            ):
                g.rpcg_ashar[r, p, c, cg, s].where[
                    g.prc_sgl[r, p] == g.stoal[r, s]
                ] = -1
            g.flo_ashar[g.Rtp[r, v, p], c, g.ComType[cg], s, bd].where[
                g.ComTmap[r, g.ComType, c]
            ] = sparse(g.flo_ashar[r, v, p, c, c, s, bd])
            g.flo_ashar[r, ll, p, c, c, s, bd] = 0
            g.CgGrp[g.Rpc[g.Rp, c], c] = False
            g.RpPgflo[g.RpFlo[g.Rp]] = sparse(
                Sum(g.CgGrp[g.NoAct[g.Rp], c, g.Actcg], 1)
            )
            g.rpcg_ashar[g.CgGrp[g.Rpc, cg], s] = sparse(g.RpcsVar[g.Rpc, s])
            g.rpcg_ashar[g.CgGrp[g.RpcStg[g.Rp, c], g.Actcg], s] = (
                g.RpsStg[g.Rp, s] + g.PrcTsl[g.Rp, "ANNUAL"].where[g.Annual[s]]
            )
            g.CgGrp[g.Rpc, cg] = False
            with Loop(g.CgGrp[r, p, cg, cg2]):
                g.z[...] = 1
                with Loop(g.ComTsl[r, c[cg], tsl]):
                    g.z[...] = 0
                    g.rpcg_ashar[r, p, cg, cg2, s].where[g.TsGroup[r, tsl, s]] = 1
                with If(g.z):
                    g.rpcg_ashar[r, p, cg, cg2, g.Annual] = 1
            g.CgGrp.setRecords(None)

    def label_eqdef(self: EqasharVda) -> None:
        g = self.tc
        cc = self.config

        r, v, t, p, c, cg, cg2 = g.r, g.v, g.t, g.p, g.c, g.cg, g.cg2
        s, sl, ts, ie, io = g.s, g.sl, g.ts, g.ie, g.io
        Com, com1, Reg = g.Com, g.com1, g.Reg

        var = self.env.var
        sow = self.env.sow_GP
        swt = self.env.swt_GP
        r_v_t = self.env.r_v_t_GP
        bd = cc.arg2

        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_FLO = g.get_variable(f"{var}_FLO")
        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        rts = macro.rts_GP(s=s, g=self.tc, env=self.env)
        eq = g.get_equation(f"{self.env.eq}{cc.sense}_ASHAR")

        cal_red = self.env.cal_red
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        include_cal_red = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=Com,
                arg2=com1,
                arg3=ts,
                arg4=p,
                arg5=t,
                arg10=Number(1),
                pgprim=self.env.pgprim,
                def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                sow=sow,
                var=var,
            ),
        )

        assert cc.sense != "", "Sense cannot be empty."

        eq[g.RtpVintyr[*r_v_t, p], cg, cg2, rts, *swt].where[
            Sum(
                g.RsTree[r, s, ts].where[g.flo_ashar[r, v, p, cg, cg2, ts, bd]], 1
            ).where[g.rpcg_ashar[r, p, cg, cg2, s]]
        ] = generate_equation(
            # * sum over RPS_S2 timeslices
            Sum(
                g.RpsS2[g.RpFlo[r, p], sl].where[g.TsMap[r, s, sl]],
                Sum(g.TsAnn[sl, ts], g.flo_ashar[r, v, p, cg, cg2, ts, bd])
                * (
                    # * sum over all flows in the reference group CG2
                    Sum(
                        Domain(
                            g.RtpcsVarf[r, t, p, Com, ts], g.RsTree[r, sl, ts]
                        ).where[g.ComGmap[r, cg2, Com]],
                        include_cal_red
                        * Max(
                            g.rpcg_ashar[r, p, cg, cg2, s],
                            Number(1).where[
                                Sum(g.Top[r, p, c[cg], io], g.Top[r, p, Com, io]).where[
                                    g.ComType[cg2]
                                ]
                            ],
                        )
                        # * timeslice S coarser than variable or finer than variable
                        * g.rs_fr[r, sl, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, Com, sl, ts, sow)),
                    )
                    # * Allow referring to activity as well
                    + Sum(
                        Domain(g.PrcTs[r, p, ts], g.RtpVara[r, t, p]).where[
                            g.rs_fr[r, sl, ts]
                        ],
                        (
                            g.rs_fr[r, sl, ts]
                            * (
                                VAR_ACT[r, v, t, p, ts, *sow]
                                * exp(
                                    (-abs(g.stg_loss[r, v, p, ts]) / 2).where[
                                        g.RpStg[r, p]
                                    ]
                                )
                            )
                        ).where[~g.RpPgflo[r, p]]
                        + Sum(
                            g.RpcPg[g.RpStd[r, p], Com],
                            (
                                VAR_ACT[r, v, t, p, ts, *sow].where[g.RpPgact[r, p]]
                                + (
                                    VAR_FLO[r, v, t, p, Com, ts, *sow]
                                    / g.prc_actflo[r, v, p, Com]
                                ).where[~g.RpPgact[r, p]]
                            )
                            * g.rs_fr[r, sl, ts]
                            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, Com, sl, ts, sow)),
                        ).where[g.RpPgflo[r, p]],
                    ).where[g.Actcg[cg2]]
                ),
            )
            # * Allow ANNUAL share for IRE processes
            + Sum(
                g.Annual[s],
                Sum(
                    g.RpcIre[r, p, Com, ie].where[
                        g.ComGmap[r, cg, Com] * ((~g.impexp[cg2]) + same_as(ie, cg2))
                    ],
                    g.flo_ashar[r, v, p, cg, cg2, s, bd]
                    * (
                        Sum(
                            g.RtpcsVarf[Reg, t, p, c, ts].where[
                                (g.ComGmap[Reg, cg2, c] + g.impexp[cg2]).where[
                                    g.RpcIre[Reg, p, c, ie]
                                ]
                            ],
                            VAR_IRE[Reg, v, t, p, c, ts, ie, *sow].where[
                                ~g.RpcAire[Reg, p, c]
                            ]
                            + (
                                VAR_ACT[Reg, v, t, p, ts, *sow]
                                * g.prc_actflo[Reg, v, p, c]
                            ).where[g.RpcAire[Reg, p, c]],
                        )
                        + Sum(g.PrcTs[r, p, ts], VAR_ACT[r, v, t, p, ts, *sow]).where[
                            g.Actcg[cg2]
                        ]
                    )
                    - Sum(
                        g.RtpcsVarf[r, t, p, Com, ts],
                        VAR_IRE[r, v, t, p, Com, ts, ie, *sow].where[
                            ~g.RpcAire[r, p, Com]
                        ]
                        + (
                            VAR_ACT[r, v, t, p, ts, *sow] * g.prc_actflo[r, v, p, Com]
                        ).where[g.RpcAire[r, p, Com]],
                    ),
                ),
            ).where[g.RpIre[r, p]],
            cc.sense,
            # * derived commodities, summed for all flows in the group CG
            Sum(
                Domain(g.RtpcsVarf[r, t, p, Com, ts], g.ComGmap[r, cg, Com]).where[
                    g.TsMap[r, s, ts]
                ],
                include_cal_red,
            ).where[g.RpFlo[r, p]]
            + Sum(
                g.PrcTs[r, p, ts].where[g.TsMap[r, s, ts]],
                VAR_ACT[r, v, t, p, ts, *sow].where[~g.NoAct[r, p]]
                + Sum(
                    g.RpcPg[g.NoAct[r, p], c],
                    VAR_FLO[r, v, t, p, c, ts, *sow] / g.prc_actflo[r, v, p, c],
                ),
            ).where[g.Actcg[cg]]
            + Sum(
                Domain(g.Top[g.RpcStg[r, p, c[cg]], "OUT"], g.RpcsVar[r, p, c, ts]),
                g.rs_fr[r, s, ts]
                * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, s, ts, sow))
                * VAR_SOUT[r, v, t, p, c, ts, *sow]
                / g.prc_actflo[r, v, p, c],
            ).where[g.Actcg[cg2]],
        )
