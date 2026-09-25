# eqstgtss_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGTSS TIME-Slice Storage (TSS) and general storage (STS)
# *=============================================================================*
# * Questions/Comments:
# *   - the storage level does NOT need to be fixed to an initial storage level in some TS

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum
from gamspy.math import Max, exp

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgtssMod(GamsClass):
    """Translation unit for eqstgtss.mod."""

    # Instance attributes
    module_name: str = "eqstgtss_mod"
    gams_source: str = "eqstgtss.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        (
            RtpVintyr,
            p,
            r,
            v,
            t,
            s,
            RpsStg,
            allts,
            rs_stg,
            RpcsVar,
            RpcStg,
            c,
            ts,
            TsMap,
            Top,
            PrcNstts,
            RpcStgn,
            rs_fr,
            prc_actflo,
            PrcMap,
            PrcStgtss,
            PrcTs,
            RsBelow1,
            RpSts,
            stg_loss,
            stg_chrg,
            RpStg,
            tsl,
            lA,
            RsBelow,
            Annual,
            RpStl,
            sl,
            ips,
            bd,
            PrcStgips,
            io,
            TsGroup,
            rs_stgprd,
            stoa,
            stoal,
            prc_sgl,
        ) = (
            g.RtpVintyr,
            g.p,
            g.r,
            g.v,
            g.t,
            g.s,
            g.RpsStg,
            g.allts,
            g.rs_stg,
            g.RpcsVar,
            g.RpcStg,
            g.c,
            g.ts,
            g.TsMap,
            g.Top,
            g.PrcNstts,
            g.RpcStgn,
            g.rs_fr,
            g.prc_actflo,
            g.PrcMap,
            g.PrcStgtss,
            g.PrcTs,
            g.RsBelow1,
            g.RpSts,
            g.stg_loss,
            g.stg_chrg,
            g.RpStg,
            g.tsl,
            g.lA,
            g.RsBelow,
            g.Annual,
            g.RpStl,
            g.sl,
            g.ips,
            g.bd,
            g.PrcStgips,
            g.io,
            g.TsGroup,
            g.rs_stgprd,
            g.stoa,
            g.stoal,
            g.prc_sgl,
        )

        r_v_t = self.env.r_v_t_GP
        rts = macro.rts_GP(s=g.s, g=self.tc, env=self.env)
        swt = self.env.swt_GP
        sow = self.env.sow_GP
        swx = self.env.swx_GP
        swtx = self.env.swtx_GP
        pgprim = self.env.pgprim

        VAR_ACT = g.get_variable(f"{self.env.var}_ACT")
        VAR_SIN = g.get_variable(f"{self.env.var}_SIN")
        VAR_SOUT = g.get_variable(f"{self.env.var}_SOUT")
        VAR_UDP = g.get_variable(f"{self.env.var}_UDP")

        eq_stgtss = g.get_equation(f"{self.env.eq}_stgtss")

        eq_stgtss[RtpVintyr[*r_v_t, p], rts, *swt].where[
            RpsStg[r, p, s] & RpStg[r, p]
        ] = (
            VAR_ACT[r, v, t, p, s, *sow]
            == Sum(
                RpsStg[r, p, allts[s.lag(rs_stg[r, s])]],
                VAR_ACT[r, v, t, p, allts, *sow]
                + (
                    Sum(
                        Domain(RpcsVar[RpcStg[r, p, c], ts], TsMap[r, ts, allts]),
                        (
                            VAR_SIN[r, v, t, p, c, ts, *sow].where[
                                Top[r, p, c, "IN"] & PrcNstts[r, p, ts]
                            ]
                            - VAR_SOUT[r, v, t, p, c, ts, *sow].where[
                                Top[r, p, c, "OUT"].where[
                                    ~(PrcNstts[r, p, ts] ^ RpcStgn[r, p, c, "OUT"])
                                ]
                            ]
                        )
                        * rs_fr[r, allts, ts]
                        * (1 + macro.rtcs_fr.rtcs_fr_GP(r, t, c, allts, ts, sow))
                        / prc_actflo[r, v, p, c],
                    )
                ).where[PrcMap[r, "NST", p]]
                + Sum(
                    Top[PrcStgtss[r, p, c], "IN"],
                    VAR_SIN[r, v, t, p, c, allts, *sow] / prc_actflo[r, v, p, c],
                )
                - Sum(
                    Top[PrcStgtss[r, p, c], "OUT"],
                    VAR_SOUT[r, v, t, p, c, allts, *sow] / prc_actflo[r, v, p, c],
                )
                - (
                    Sum(
                        PrcTs[r, p, ts].where[RsBelow1[r, ts, s]],
                        VAR_SOUT[r, v, t, p, pgprim, ts, *sow] * rs_fr[r, allts, ts],
                    )
                ).where[RpSts[r, p]]
                - VAR_ACT[r, v, t, p, allts, *sow]
                * (
                    Max(
                        stg_loss[r, v, p, allts] / 2,
                        1
                        + stg_loss[r, v, p, allts]
                        / (1 / exp(stg_loss[r, v, p, allts]) - 1),
                    )
                ).where[stg_loss[r, v, p, allts]]
                - VAR_ACT[r, v, t, p, s, *sow]
                * (
                    Max(
                        stg_loss[r, v, p, allts] / 2,
                        stg_loss[r, v, p, allts] / (exp(stg_loss[r, v, p, allts]) - 1)
                        - 1,
                    )
                ).where[stg_loss[r, v, p, allts]],
            )
            + stg_chrg[r, t, p, s.lag(rs_stg[r, s])]
        )

        # storage level in time-slice s
        # storage level in time-slice s
        # for day-night storage; allow flow variable at or above ALL_TS
        # for storage processes without charging restriction
        # optional balancer flow
        # storage losses: average storage level per cycle * loss fraction by cycle * cycles
        # equilibrium loss (STG_LOSS<0): Act0 * (1-Loss/(1/EXP(-Loss)-1))
        # equilibrium loss (STG_LOSS<0): Act1 * (-Loss/(EXP(-Loss)-1)-1)
        # storage charge
        # --- Balancer Equation ---

        eq_stsbal = g.get_equation(f"{self.env.eq}_stsbal")

        eq_stsbal[RtpVintyr[*r_v_t, p], tsl, rts, lA, *swt].where[
            TsGroup[r, tsl, s] & PrcTs[r, p, s] & RpStl[r, p, tsl, lA]
        ] = Sum(
            RsBelow[r, Annual, s],
            VAR_ACT[r, v, t, p, s, *sow]
            + (
                VAR_SIN[r, v, t, p, pgprim, s, *sow]
                + macro.var_sts.render_GP(r, v, t, p, s, "N")
            ).where[RpStl[r, p, tsl, "UP"]],
        ) == Sum(
            RsBelow[r, Annual, sl[s.lag(rs_stg[r, s])]],
            VAR_ACT[r, v, t, p, sl, *sow].where[ips[lA]]
            + VAR_UDP[r, v, t, p, sl, "LO", *sow].where[bd[lA]]
            + (
                VAR_SIN[r, v, t, p, pgprim, sl, *sow]
                + macro.var_sts.render_GP(r, v, t, p, sl, lA)
            ).where[RpStl[r, p, tsl, "UP"]]
            + (
                VAR_SOUT[r, v, t, p, pgprim, sl, *sow]
                - Sum(
                    PrcTs[r, p, ts].where[RsBelow1[r, ts, s]],
                    VAR_SOUT[r, v, t, p, pgprim, ts, *sow] * rs_fr[r, sl, ts],
                )
                - VAR_ACT[r, v, t, p, sl, *sow].where[rs_stg[r, s]]
                * (
                    Max(
                        stg_loss[r, v, p, sl] / 2,
                        1
                        + stg_loss[r, v, p, sl] / (1 / exp(stg_loss[r, v, p, sl]) - 1),
                    )
                ).where[stg_loss[r, v, p, sl]]
                - (
                    VAR_ACT[r, v, t, p, s, *sow].where[rs_stg[r, s]]
                    + (
                        VAR_SIN[r, v, t, p, pgprim, s, *sow]
                        - VAR_SIN[r, v, t, p, pgprim, sl, *sow]
                    ).where[RpStl[r, p, tsl, "UP"]]
                )
                * (
                    Max(
                        stg_loss[r, v, p, sl] / 2,
                        stg_loss[r, v, p, sl] / (exp(stg_loss[r, v, p, sl]) - 1) - 1,
                    )
                ).where[stg_loss[r, v, p, sl]]
            ).where[ips[lA]],
        ) + Sum(
            Annual[s],
            Sum(
                Top[PrcStgips[r, p, c], io],
                1
                / prc_actflo[r, v, p, c]
                * VAR_SIN[r, v, t, p, c, s, *sow].where[ips[io]]
                - VAR_SOUT[r, v, t, p, c, s, *sow].where[~ips[io]],
            )
            - VAR_SOUT[r, v, t, p, pgprim, s, *sow],
        )
        # storage level in time-slice s
        # storage level in time-slice s
        # balancer flows
        # storage losses: average storage level * year fraction * loss fraction
        # equilibrium loss (STG_LOSS<0): Act0 * (1-Loss/(1/EXP(-Loss)-1))
        # equilibrium loss (STG_LOSS<0): Act1 * (-Loss/(EXP(-Loss)-1)-1)
        # net charging into IPS
        # balancer flow
        # --- Levelizer Equation ---
        g.eq_stslev[RtpVintyr[*r_v_t, p], tsl, rts, *swx].where[
            swtx.where[stoal[r, s] == prc_sgl[r, p]]
            & TsGroup[r, tsl, s]
            & RpStl[r, p, tsl, "UP"]
        ] = Sum(
            TsMap[r, ts, s].where[stoa[ts]],
            (
                VAR_SIN[r, v, t, p, pgprim, ts, *sow]
                + VAR_UDP[r, v, t, p, ts, "LO", *sow]
                + macro.var_sts.render_GP(r, v, t, p, ts, "N")
            )
            / rs_stgprd[r, ts],
        ) <= Sum(
            RsBelow1[r, s, ts].where[rs_fr[r, ts, s]],
            VAR_ACT[r, v, t, p, ts, *sow] / rs_stgprd[r, ts] * rs_fr[r, ts, s],
        )
