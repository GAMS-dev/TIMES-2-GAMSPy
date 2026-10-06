# eqlducs_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQLDUCS - implements linear and discrete unit commitment
# *   arg1 - Section
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Domain,
    Equation,
    Loop,
    Number,
    Ord,
    Parameter,
    Smin,
    SpecialValues,
    Sum,
    Variable,
    sparse,
)
from gamspy.math import Max, Min, diag, mod, project

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqlducsVdaConfig:
    """Strongly typed data contract for eqlducs.vda."""

    # %1 - Section
    arg1: Literal["EQU", ""] = ""


class EqlducsVda(GamsClass):
    """Translation unit for eqlducs.vda."""

    # Instance attributes
    module_name: str = "eqlducs_vda"
    gams_source: str = "eqlducs.vda"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqlducsVdaConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        cc = self.config
        if self.env.obmac != "YES":
            return

        if cc.arg1 != "EQU":
            g = self.tc
            m = g.container
            # * Internal attributes for equation control
            g.dp_non = Parameter(
                m,
                name="DP_NON",
                domain=[g.r, g.ll, g.p, g.upt, g.tsl, g.bd],
                description="Bounds on non-operational time between shut-down and next start-up",
            )

            self.tc.enqueue(self.exec1)

        else:  # EQU
            self.tc.enqueue(self.disable_linear_dispatch)
            self.set_macros(
                var=self.env.var,
                sow=self.env.sow,
                condition=self.env.abs.upper() == "YES",
            )

            g = self.tc
            if (
                isinstance(self.env.rcapsub_GP, Number)
                and self.env.rcapsub_GP_value == 1
            ):
                raise ValueError("rcapsub_GP cannot be Number(1) in this assignment.")

            self.env.set_scoped(
                "capon_GP",
                g.coef_cpt[g.r, g.v, g.t, g.p]
                * (
                    macro.VAR_NCAP_GP(
                        self.env.varv_GP, g.r, g.v, g.p, self.env.sws_GP
                    ).where[g.t[g.v]]
                    + g.ncap_pasti[g.r, g.v, g.p]
                    + self.env.rcapsub_GP
                ).where[g.PrcVint[g.r, g.p]]
                + macro.VAR_CAP_GP(self.env.var, g.r, g.t, g.p, self.env.sow_GP).where[
                    g.RpUx[g.r, g.p]
                ],
            )

            capups = self.env.capon_GP - Sum(
                g.RsBelow[g.r, g.allts, g.s].where[g.RpsUps[g.r, g.p, g.allts]],
                macro.eqlducs.var_off_GP(g.r, g.v, g.t, g.p, g.allts),
            )
            self.define_equation1(
                capon=self.env.capon_GP,
                capups=capups,
                r_v_t=self.env.r_v_t_GP,
                swx=self.env.swx_GP,
                swtx=self.env.swtx_GP,
            )
            # * Discrete Unit Commitment
            if self.env.duc.upper() != "YES":
                return

            self.env.set_global("solmip", "YES")

            self.tc.enqueue(
                self.prepare_unit_size,
                condition1=self.tc.defined("PRC_DSCNCAP"),
                condition2=self.env.stages == "YES",
            )
            self.var_equ_indicators()
            self.tc.enqueue(self.exec2)

            ind = Path("indic.txt").read_text() if Path("indic.txt").exists() else ""
            if Path("cplex.opt").exists():
                Path("cplex.op2").write_text(Path("cplex.opt").read_text() + ind)
            if Path("xpress.opt").exists():
                Path("xpress.op2").write_text(Path("xpress.opt").read_text() + ind)

            self.define_equation2(
                r_v_t=self.env.r_v_t_GP, capon=self.env.capon_GP, capups=capups
            )

    def exec1(self: EqlducsVda) -> None:
        g = self.tc
        # * Assume valid UPTs must have a cost or SD-time; reset simplified UC options
        project(source=g.act_cstsd, target=g.RpUpt)
        project(source=g.RpUpt, target=g.Trackp)
        g.RpDp[g.Trackp[g.Rp]] = sparse(g.RpUpl[g.Rp, "FX"])
        g.RpDp[g.Rp].where[Sum(g.RpsCaflac[g.PrcTs[g.Rp, g.s], g.bd], 1.0)] = False
        g.RpDpl[g.PrcTsl[g.RpDp, g.tsl]] = True
        g.RpDpl[g.RpDp[g.r, g.p], g.tsl].where[
            (g.Rlup[g.r, "DAYNITE", g.tsl].where[g.PrcTsl[g.r, g.p, "DAYNITE"]])
        ] = Ord(g.tsl) > 1.0
        g.act_cstup[g.Rtp[g.r, g.v, g.p], g.tsl, g.cur].where[g.RpDp[g.r, g.p]] = 0.0
        g.act_cstsd[g.Rtp[g.r, g.v, g.p], g.upt, "FX", g.cur].where[
            (g.Rdcur[g.r, g.cur].where[g.RpDp[g.r, g.p]])
        ] = (
            g.act_cstsd[g.Rtp, g.upt, "UP", g.cur]
            + g.act_cstsd[g.Rtp, "HOT", "LO", g.cur]
        )
        g.act_cstup[g.Rtp[g.r, g.v, g.p], g.tsl, g.cur].where[
            g.RpDpl[g.r, g.p, g.tsl]
        ] = sparse(
            Sum(
                g.upt.where[g.act_cstsd[g.Rtp, g.upt, "FX", g.cur]],
                SpecialValues.EPS,
            )
        )
        g.RpUpt[g.RpDp, g.upt, "LO"] = diag("HOT", g.upt)
        with Loop(g.v):
            g.RpUpt[g.r, g.p, g.upt, g.bd["UP"]].where[
                g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd]
            ] = True
        # *------------------------------------
        # * Max. non-op. time processing
        g.act_maxnon[g.r, g.v, g.p, g.upt].where[
            ((~(g.act_maxnon[g.r, g.v, g.p, g.upt])).where[g.RpDp[g.r, g.p]])
        ] = SpecialValues.EPS
        g.dp_non[g.Rtp[g.r, g.v, g.p], g.upt, g.tsl, "UP"].where[
            (
                (g.act_maxnon[g.Rtp, g.upt] < 8760.0 / g.g_cycle[g.tsl]).where[
                    g.RpDpl[g.r, g.p, g.tsl]
                ]
            )
        ] = g.act_maxnon[g.Rtp, g.upt] / 8760.0
        g.dp_non[g.Rtp[g.r, g.v, g.p], "WARM", g.tsl, "LO"].where[g.RpDp[g.r, g.p]] = (
            g.dp_non[g.Rtp, "HOT", g.tsl, "UP"]
        )
        g.dp_non[g.Rtp[g.r, g.v, g.p], g.upt, g.tsl, "LO"].where[g.RpDp[g.r, g.p]] = (
            Max(g.dp_non[g.Rtp, g.upt, g.tsl, "LO"], g.act_time[g.Rtp, "LO"] / 8760.0)
        )
        g.dp_non[g.Rtp[g.r, g.v, g.p], g.upt, g.tsl, g.Bdneq[g.bd]].where[
            g.RpDp[g.r, g.p]
        ] = (
            g.dp_non[g.Rtp, g.upt, g.tsl, g.bd]
            + (g.act_sdtime[g.Rtp, g.upt, "UP"] + g.act_sdtime[g.Rtp, "HOT", "LO"])
            / 8760.0
        )
        g.dp_non[g.Rtp[g.r, g.v, g.p], g.upt, g.tsl, "UP"].where[
            (g.dp_non[g.Rtp, g.upt, g.tsl, "UP"].where[g.RpDp[g.r, g.p]])
        ] = g.dp_non[g.Rtp, g.upt, g.tsl, "UP"] - g.dp_non[g.Rtp, g.upt, g.tsl, "LO"]
        g.dp_non[g.Rtp, "COLD", g.tsl, "UP"] = 0.0
        # *------------------------------------
        # * Partial loss processing
        g.act_sdtime[g.Rtp[g.r, g.v, g.p], g.upt, g.bd].where[
            (~(g.RpUpt[g.r, g.p, g.upt, g.bd]))
        ] = 0.0
        g.dp_psud[g.Rtp, g.upt, g.Bdneq[g.bd]].where[
            (
                (g.act_sdtime[g.Rtp, g.upt, g.bd] > 0.0).where[
                    g.act_sdtime[g.Rtp, g.upt, g.bd]
                ]
            )
        ] = g.act_minld[g.Rtp] / g.act_sdtime[g.Rtp, g.upt, g.bd]
        g.act_lossd[g.Rtp, g.upt, g.bd].where[
            (
                g.act_minld[g.Rtp].where[g.dp_psud[g.Rtp, g.upt, g.bd]]
                <= g.dp_psud[g.Rtp, g.upt, g.bd]
            )
        ] = 0.0
        g.Trackp.setRecords(None)
        project(source=g.act_lossd, target=g.DpLosd)
        g.DpLosd[g.Rtp[g.r, g.v, g.p]].where[g.RpPl[g.r, g.p, "N"]] = sparse(
            g.RpPl[g.r, g.p, "FX"]
        )
        g.act_lospl[g.DpLosd[g.Rtp[g.r, g.v, g.p]], "FX"].where[
            (g.act_lospl[g.Rtp, "FX"] == 0.0)
        ] = 0.01 ** (Number(1.0).where[g.RpPl[g.r, g.p, "N"]])
        g.act_lossd[g.Rtp, g.upt, g.bd].where[
            (
                (g.act_lossd[g.Rtp, g.upt, g.bd] < g.act_lospl[g.Rtp, "FX"]).where[
                    g.act_lossd[g.Rtp, g.upt, g.bd]
                ]
            )
        ] = 0.0
        g.dp_psud[g.DpLosd[g.Rtp[g.r, g.v, g.p]], g.upt, g.Bdneq[g.bd]] = (
            g.dp_psud[g.Rtp, g.upt, g.bd]
            * (
                g.act_lossd[g.Rtp, g.upt, g.bd] / g.act_lospl[g.Rtp, "FX"]
                - Number(1.0).where[g.RpPl[g.r, g.p, "N"]]
            )
            / (g.act_minld[g.Rtp] - g.dp_psud[g.Rtp, g.upt, g.bd])
        ).where[g.act_lossd[g.Rtp, g.upt, g.bd]]

    def disable_linear_dispatch(self: EqlducsVda) -> None:
        g = self.tc
        # * Disable inconsistent linear dispatch features, add UX control for CAP
        g.RpUps[g.RpDp, g.tsl, g.lA] = False
        g.RpUpc[g.RpDp, g.tsl, g.bd] = False
        g.Afups[g.r, g.t, g.p, g.s].where[g.RpDp[g.r, g.p]] = False
        g.RpsUps[g.PrcTs[g.RpDp, g.s]] = True
        g.RpUx[g.Rp].where[(~(g.PrcVint[g.Rp]))] = sparse(g.RpDp[g.Rp])
        g.RtpVarp[g.Rtp[g.r, g.t, g.p]].where[g.RpUx[g.r, g.p]] = True
        g.RpUps[g.RpDp[g.r, g.p], g.tsl, "FX"] = sparse(
            Sum(g.Rlup[g.r, g.tslvl, g.tsl].where[g.PrcTsl[g.r, g.p, g.tslvl]], 1.0)
        )

    def set_macros(self: EqlducsVda, var: str, sow: str, condition: bool) -> None:
        # Activates all macros except sdtol which is now used as a local variable
        macro.eqlducs.activate(
            g=self.tc,
            var=var,
            sow=sow,
            sow_GP=self.env.sow_GP,
            sprsv_condition=condition,
        )

    def define_equation1(
        self: EqlducsVda,
        capon: Expression | Condition,
        capups: Expression,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...],
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
        swtx: Number | ImplicitSet,
    ) -> None:
        g = self.tc
        rts = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        sdtol = 0.001  # $macro sdtol .001 -- only used within this method

        # *-----------------------------------------------------------------------------

        g.eq_sdlogic[g.RtpVintyr[*r_v_t, g.p], g.tsl, rts, g.Lnx[g.lA], *swx].where[
            swtx.where[g.TsGroup[g.r, g.tsl, g.s].where[g.RpDpl[g.r, g.p, g.tsl]]]
        ] = (
            Sum(
                g.ts[g.s.lag(g.rs_stg[g.r, g.s], "circular")],
                macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                - macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.s),
            )
            - Sum(
                g.bd,
                macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.s, g.bd)
                * g.bdsig[g.bd],
            )
        ).where[g.ips[g.lA]] + (
            macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.s, "UP")
            - Sum(
                g.RpUpt[g.r, g.p, g.upt, "UP"],
                macro.eqlducs.v_u_GP("UPT", g.r, g.v, g.t, g.p, g.s, g.upt),
            )
        ).where[g.bd[g.lA]] == 0.0

        # *-----------------------------------------------------------------------------

        g.eq_sudupt[g.RtpVintyr[*r_v_t, g.p], g.tsl, rts, g.upt, *swx].where[
            swtx.where[
                g.dp_non[g.r, g.v, g.p, g.upt, g.tsl, "UP"].where[
                    g.TsGroup[g.r, g.tsl, g.s].where[g.RpDpl[g.r, g.p, g.tsl]]
                ]
            ]
        ] = macro.eqlducs.v_u_GP("UPT", g.r, g.v, g.t, g.p, g.s, g.upt) <= Sum(
            Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                Ord(g.s) != Ord(g.sl)
            ],
            macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.sl, "LO").where[
                mod(
                    g.rs_hr[g.r, g.s]
                    - g.rs_hr[g.r, g.sl]
                    - g.dp_non[g.r, g.v, g.p, g.upt, g.tsl, "LO"]
                    + (g.g_yrfr[g.r, g.sl] / 4.0 + g.g_yrfr[g.r, g.s])
                    / g.rs_stgprd[g.r, g.s]
                    + 2.0 / g.js_ccl[g.r, g.Js],
                    1.0 / g.js_ccl[g.r, g.Js],
                )
                < g.dp_non[g.r, g.v, g.p, g.upt, g.tsl, "UP"] * (1.0 + sdtol)
                + g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 2.0
            ],
        )

        # *-----------------------------------------------------------------------------

        g.eq_sdslant[g.RtpVintyr[*r_v_t, g.p], g.tsl, rts, *swx].where[
            swtx.where[g.TsGroup[g.r, g.tsl, g.s].where[g.RpDpl[g.r, g.p, g.tsl]]]
        ] = macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.s) == Sum(
            g.RsBelow1[g.r, g.ts, g.s],
            macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.ts, "FX") - capups,
        ).where[g.PrcTs[g.r, g.p, g.s]] + capups - macro.eqlducs.var_off_GP(
            g.r, g.v, g.t, g.p, g.s
        ) - Sum(
            g.RpUpt[g.r, g.p, g.upt, g.bd],
            Sum(
                Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                    g.rs_modus[g.r, g.sl, g.Js, g.s]
                    < g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0 * (1.0 + sdtol)
                ],
                macro.eqlducs.v_u_GP("UPT", g.r, g.v, g.t, g.p, g.sl, g.upt)
                * (
                    Number(0.0).where[diag(g.s, g.sl)]
                    + Max(
                        0.0,
                        1.0
                        - mod(
                            g.rs_hr[g.r, g.sl]
                            - g.rs_hr[g.r, g.s]
                            + macro.eqlducs.sudhfr_GP(g.r, g.sl, "-", g.s)
                            + 2.0 / g.js_ccl[g.r, g.Js],
                            1.0 / g.js_ccl[g.r, g.Js],
                        )
                        / (g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0),
                    )
                    * (1.0 - diag(g.s, g.sl))
                ),
            ).where[g.Bdupx[g.bd]]
            + Sum(
                Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                    g.rs_modus[g.r, g.s, g.Js, g.sl]
                    < g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0 * (1.0 + sdtol)
                ],
                macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.sl, g.bd)
                * (
                    Number(1.0).where[diag(g.s, g.sl)]
                    + Max(
                        0.0,
                        1.0
                        - mod(
                            g.rs_hr[g.r, g.s]
                            - g.rs_hr[g.r, g.sl]
                            + macro.eqlducs.sudhfr_GP(g.r, g.sl, "-", g.s)
                            + 2.0 / g.js_ccl[g.r, g.Js],
                            1.0 / g.js_ccl[g.r, g.Js],
                        )
                        / (g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0),
                    )
                    * (1.0 - diag(g.s, g.sl))
                ),
            ).where[g.Bdlox[g.bd]],
        )

        # *-----------------------------------------------------------------------------

        g.eq_sdminon[g.RtpVintyr[*r_v_t, g.p], rts, *swx].where[
            swtx.where[g.PrcTs[g.r, g.p, g.s].where[g.RpDp[g.r, g.p]]]
        ] = (
            macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.s)
            + Sum(
                g.RsBelow1[g.r, g.ts, g.s],
                macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.ts),
            )
            >= macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.s)
            + macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.s, "UP")
            + (
                Sum(
                    g.RpUpt[g.r, g.p, g.upt, "UP"].where[
                        g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 2.0
                        <= g.act_sdtime[g.r, g.v, g.p, g.upt, "UP"] / 8760.0
                    ],
                    macro.eqlducs.v_u_GP("UPT", g.r, g.v, g.t, g.p, g.s, g.upt),
                )
                - macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.s, "UP")
            ).where[
                Smin(
                    g.RpUpt[g.r, g.p, g.upt, "UP"],
                    g.act_sdtime[g.r, g.v, g.p, g.upt, "UP"] / 8760.0,
                )
                < g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 2.0
            ]
        )

        # *-----------------------------------------------------------------------------

        g.eq_sudload[g.RtpVintyr[*r_v_t, g.p], rts, *swx].where[
            swtx.where[g.PrcTs[g.r, g.p, g.s].where[g.RpDp[g.r, g.p]]]
        ] = (
            macro.eqlducs.var_load_GP(g.r, g.v, g.t, g.p, g.s)
            == (capon + macro.upscaps.render_GP()) * g.act_minld[g.r, g.v, g.p]
            + macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.s)
            * (g.coef_af[g.r, g.v, g.t, g.p, g.s, "UP"] - g.act_minld[g.r, g.v, g.p])
            + macro.eqlducs.sprsv_GP()
        )

        # *-----------------------------------------------------------------------------

        g.eq_sudtime[g.RtpVintyr[*r_v_t, g.p], g.tsl, rts, g.bd, *swx].where[
            swtx.where[
                g.PrcTsl[g.r, g.p, g.tsl].where[
                    g.TsGroup[g.r, g.tsl, g.s].where[
                        g.act_time[g.r, g.v, g.p, g.bd].where[g.RpDp[g.r, g.p]]
                    ]
                ]
            ]
        ] = (
            Sum(
                g.Bdlox[g.bd],
                macro.eqlducs.var_off_GP(g.r, g.v, g.t, g.p, g.s)
                - Sum(
                    Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]),
                    macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.sl, g.bd).where[
                        mod(
                            g.rs_hr[g.r, g.s]
                            - g.rs_hr[g.r, g.sl]
                            - g.act_sdtime[g.r, g.v, g.p, "HOT", "LO"] / 8760.0
                            + g.g_yrfr[g.r, g.s] / g.rs_stgprd[g.r, g.s] / 2.0
                            + 2.0 / g.js_ccl[g.r, g.Js],
                            1.0 / g.js_ccl[g.r, g.Js],
                        )
                        < g.act_time[g.r, g.v, g.p, g.bd] / 8760.0
                    ],
                ),
            )
            + Sum(
                g.Bdupx[g.bd],
                macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.s)
                - Sum(
                    Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]),
                    Sum(
                        g.RpUpt[g.r, g.p, g.upt, g.bd],
                        macro.eqlducs.v_u_GP(
                            "UPT", g.r, g.v, g.t, g.p, g.sl, g.upt
                        ).where[
                            mod(
                                g.rs_hr[g.r, g.s]
                                - g.rs_hr[g.r, g.sl]
                                + 1.0 / g.js_ccl[g.r, g.Js],
                                1.0 / g.js_ccl[g.r, g.Js],
                            )
                            < (
                                g.act_time[g.r, g.v, g.p, g.bd]
                                - g.act_sdtime[g.r, g.v, g.p, "HOT", "LO"]
                                - g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd]
                            )
                            / 8760.0
                            + g.g_yrfr[g.r, g.sl] / g.rs_stgprd[g.r, g.s] / 2.0
                        ],
                    ),
                ),
            )
            >= 0.0
        )

        # *-----------------------------------------------------------------------------

        g.eq_sudpll[g.RtpVintyr[*r_v_t, g.p], g.tsl, rts, *swx].where[
            swtx.where[
                g.TsGroup[g.r, g.tsl, g.s].where[
                    g.PrcTsl[g.r, g.p, g.tsl].where[
                        g.DpLosd[g.r, g.v, g.p].where[g.RpDp[g.r, g.p]]
                    ]
                ]
            ]
        ] = (
            macro.eqlducs.v_u_GP("UPS", g.r, g.v, g.t, g.p, g.s, "FX")
            >= Sum(
                g.RpUpt[g.r, g.p, g.upt, g.bd],
                Sum(
                    Domain(g.RsUp[g.r, g.s, g.Js], g.RjSl[g.r, g.Js, g.sl]).where[
                        mod(
                            (g.rs_hr[g.r, g.s] - g.rs_hr[g.r, g.sl]) * g.bdsig[g.bd]
                            + g.g_yrfr[g.r, g.sl] / g.rs_stgprd[g.r, g.s] / 2.0
                            + 2.0 / g.js_ccl[g.r, g.Js],
                            1.0 / g.js_ccl[g.r, g.Js],
                        )
                        < g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd]
                        / 8760.0
                        * (1.0 + sdtol)
                    ],
                    (
                        1.0
                        + Min(
                            1.0,
                            mod(
                                (g.rs_hr[g.r, g.s] - g.rs_hr[g.r, g.sl]) * g.bdsig[g.bd]
                                + macro.eqlducs.sudhfr_GP(g.r, g.sl, "-", g.s)
                                + 2.0 / g.js_ccl[g.r, g.Js],
                                1.0 / g.js_ccl[g.r, g.Js],
                            )
                            / (g.act_sdtime[g.r, g.v, g.p, g.upt, g.bd] / 8760.0),
                        )
                        * (g.dp_psud[g.r, g.v, g.p, g.upt, g.bd] - 1.0)
                    )
                    * (
                        macro.eqlducs.v_u_GP(
                            "UPT", g.r, g.v, g.t, g.p, g.sl, g.upt
                        ).where[g.Bdupx[g.bd]]
                        + macro.eqlducs.v_u_GP(
                            "UPS", g.r, g.v, g.t, g.p, g.sl, g.bd
                        ).where[g.Bdlox[g.bd]]
                    ),
                ),
            )
            * g.prc_capact[g.r, g.p]
            * g.g_yrfr[g.r, g.s]
            * g.act_minld[g.r, g.v, g.p]
        )

    def prepare_unit_size(self: EqlducsVda, condition1: bool, condition2: bool) -> None:
        g = self.tc
        # * Prepare min. unit sizes for semi-continuous modeling
        g.ncap_semi[g.Rvp] = sparse(0.0)
        g.Trackp[g.RpDp[g.Rp]].where[(g.prc_semi[g.Rp] < 10.0)] = True
        g.coef_cap[g.RtpVintyr[g.r, g.t, g.t, g.p]].where[g.Trackp[g.r, g.p]] = Min(
            g.ncap_semi[g.r, g.t, g.p],
            Sum(
                g.RtpCptyr[g.r, g.pyr[g.v], g.t, g.p],
                g.ncap_pasti[g.r, g.v, g.p] * g.coef_cpt[g.r, g.v, g.t, g.p],
            ),
        )
        g.coef_cap[g.RtpVintyr[g.r, g.pyr[g.v], g.t, g.p]].where[
            (g.PrcVint[g.r, g.p].where[g.Trackp[g.r, g.p]])
        ] = Min(
            g.ncap_semi[g.r, g.v, g.p],
            g.ncap_pasti[g.r, g.v, g.p] * g.coef_cpt[g.r, g.v, g.t, g.p],
        )
        g.coef_cap[g.RtpVintyr[g.r, g.tt, g.t, g.p]].where[
            ((g.coef_cap[g.r, g.tt, g.t, g.p] == 0.0).where[g.Trackp[g.r, g.p]])
        ] = g.ncap_semi[g.r, g.tt, g.p]
        g.dp_uns[g.RtpVintyr[g.r, g.v, g.t, g.p], g.tsl, "IN", g.Lnx].where[
            g.RpDpl[g.r, g.p, g.tsl]
        ] = sparse(g.coef_cap[g.r, g.v, g.t, g.p])
        g.dp_uns[g.RtpVintyr[g.r, g.v, g.t, g.p], g.tsl, "IN", g.lA].where[
            (g.RpUps[g.r, g.p, g.tsl, "FX"].where[g.RpDp[g.r, g.p]])
        ] = sparse(g.coef_cap[g.r, g.v, g.t, g.p])
        g.dp_uns[g.RtpVintyr[g.r, g.v, g.t, g.p], g.tsl, g.ips[g.lA], g.lA].where[
            (
                (~(g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, "IN", g.lA])).where[
                    g.RpDpl[g.r, g.p, g.tsl]
                ]
            )
        ] = 1.0

        if condition1:
            g.PrcDscncap[g.Trackp] = 0.0

        g.Trackp.setRecords(None)
        g.coef_cap.setRecords(None)

        if condition2:
            g.dp_uns.setRecords(None)

    def var_equ_indicators(self: EqlducsVda) -> None:
        g = self.tc
        m = g.container
        r, ll, t, p, s, lA = g.r, g.ll, g.t, g.p, g.s, g.lA

        # *Variables, Equations and Indicators
        g.VAR_ONIND = Variable(
            m,
            name="VAR_ONIND",
            domain=[r, ll, t, p, s, lA],
            description="on-line status of unit in timeslice s",
            type="BINARY",
        )
        # GAMS declares these without a domain; their dimension is fixed by first use
        g.eq_sdind_1 = Equation(m, name="eq_sdind_1", domain=["*"] * 8)
        g.eq_sdind_0 = Equation(m, name="eq_sdind_0", domain=["*"] * 8)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET INDIC(J) /
  1 "eq_sdind_0(r,v,t,p,tsl,s,ips,l)$var_onind(r,v,t,p,s,l) 0"
  2 "eq_sdind_1(r,v,t,p,tsl,s,ips,l)$var_onind(r,v,t,p,s,l) 1"
  /;
*--------------------------------------
  FILE INDFILE / INDIC.TXT /;
  """,
        )

    def exec2(self: EqlducsVda) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
  IF(SUM(RP_DP,1),PUT INDFILE; LOOP(INDIC(J)$(ORD(J)<3), put "indic ",INDIC.TE(J) /);
   PUTCLOSE INDFILE; OPTFILEID=2;
  );
   """,
        )

    def define_equation2(
        self: EqlducsVda,
        r_v_t: tuple[Set | Alias | ImplicitSet, ...],
        capon: Expression | Condition,
        capups: Expression,
    ) -> None:
        g = self.tc

        g.eq_sdind_1[
            g.RtpVintyr[*r_v_t, g.p],
            g.tsl,
            g.ts[g.s.lag(g.rs_stg[g.r, g.s], "circular")],
            g.ips,
            g.lA,
        ].where[
            g.TsGroup[g.r, g.tsl, g.s].where[
                g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA]
            ]
        ] = (
            g.VAR_ONIND[g.r, g.v, g.t, g.p, g.ts, g.lA] * SpecialValues.EPS
            + (
                macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                - Sum(
                    g.RsBelow1[g.r, g.sl, g.s].where[g.PrcTs[g.r, g.p, g.s]],
                    g.VAR_UPS[g.r, g.v, g.t, g.p, g.sl, "FX"] - capups,
                )
                - (
                    capups
                    + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "LO"]
                    + g.VAR_UPS[g.r, g.v, g.t, g.p, g.s, "UP"]
                )
            ).where[g.lA[g.ips]]
            + (
                (
                    macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                    - macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.ts).where[
                        ~g.PrcTsl[g.r, g.p, g.tsl]
                    ]
                    - Max(
                        g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA],
                        g.ncap_semi[g.r, g.v, g.p].where[g.PrcTsl[g.r, g.p, g.tsl]]
                        / 2.0,
                    )
                ).where[g.ips[g.lA]]
                + (
                    g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "UP"]
                    + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "LO"]
                    - Max(
                        g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA],
                        g.ncap_semi[g.r, g.v, g.p].where[g.PrcTsl[g.r, g.p, g.tsl]]
                        / 2.0,
                    )
                ).where[diag("FX", g.lA)]
                + (
                    capon
                    - macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                    - g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA]
                ).where[diag("LO", g.lA)]
                + (
                    macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.ts)
                    - g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA]
                ).where[diag("UP", g.lA)]
            ).where[g.io[g.ips]]
            >= 0.0
        )

        # *-----------------------------------------------------------------------------

        g.eq_sdind_0[
            g.RtpVintyr[*r_v_t, g.p],
            g.tsl,
            g.ts[g.s.lag(g.rs_stg[g.r, g.s], "circular")],
            g.ips,
            g.lA,
        ].where[
            g.TsGroup[g.r, g.tsl, g.s].where[
                g.dp_uns[g.r, g.v, g.t, g.p, g.tsl, g.ips, g.lA]
            ]
        ] = (
            macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
            + Sum(
                g.RsBelow1[g.r, g.sl, g.s],
                macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.sl)
                + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "UP"],
            ).where[g.PrcTs[g.r, g.p, g.s]]
        ).where[g.lA[g.ips]] + (
            (
                macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                - macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.ts).where[
                    ~g.PrcTsl[g.r, g.p, g.tsl]
                ]
                + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "UP"]
            ).where[g.ips[g.lA]]
            + (
                g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "UP"]
                + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "LO"]
            ).where[diag("FX", g.lA)]
            + (
                capon
                - macro.eqlducs.var_on_GP(g.r, g.v, g.t, g.p, g.ts)
                + g.VAR_UPS[g.r, g.v, g.t, g.p, g.ts, "LO"]
            ).where[diag("LO", g.lA)]
            + (macro.eqlducs.var_gap_GP(g.r, g.v, g.t, g.p, g.ts)).where[
                diag("UP", g.lA)
            ]
        ).where[g.io[g.ips]] <= 0.0
