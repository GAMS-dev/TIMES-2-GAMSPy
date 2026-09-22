# eqstgips_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTG Inter-Period Storage (IPS) and TIME-Slice Storage (TSS)               *
# *=============================================================================*
# *UR Questions/Comments:
# *
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Sum
from gamspy.math import power

from core.base_class import GamsClass
from core.utils import wrap_in_sum

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgipsMod(GamsClass):
    """Translation unit for eqstgips.mod."""

    # Instance attributes
    module_name: str = "eqstgips_mod"
    gams_source: str = "eqstgips.mod"

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
            ips,
            r,
            v,
            t,
            lim,
            io,
            Modlyear,
            Miyr1,
            ll,
            lead,
            tt,
            PrcVint,
            stg_loss,
            d,
            Top,
            PrcStgips,
            c,
            Periodyr,
            YEoh,
            e,
            yearval,
            prc_actflo,
            stg_chrg,
            PrcMap,
        ) = (
            g.RtpVintyr,
            g.p,
            g.ips,
            g.r,
            g.v,
            g.t,
            g.lim,
            g.io,
            g.Modlyear,
            g.Miyr1,
            g.ll,
            g.lead,
            g.tt,
            g.PrcVint,
            g.stg_loss,
            g.d,
            g.Top,
            g.PrcStgips,
            g.c,
            g.Periodyr,
            g.YEoh,
            g.e,
            g.yearval,
            g.prc_actflo,
            g.stg_chrg,
            g.PrcMap,
        )

        r_v_t = self.env.r_v_t_GP
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        swt = self.env.swt_GP
        var = self.env.var
        vartt_id, vartt_set = self.env.vartt_GP

        VAR_ACT = g.get_variable(f"{var}_ACT")
        VARTT_ACT = g.get_variable(f"{vartt_id}_ACT")
        VAR_SIN = g.get_variable(f"{var}_SIN")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")

        VARTT_ACT_V = wrap_in_sum(VARTT_ACT[r, v, tt, p, "ANNUAL", *sws], vartt_set)
        VARTT_ACT_TT = wrap_in_sum(VARTT_ACT[r, tt, tt, p, "ANNUAL", *sws], vartt_set)

        eq_stgips = g.get_equation(f"{self.env.eq}_STGIPS")

        eq_stgips[RtpVintyr[*r_v_t, p], ips, *swt].where[
            ((Miyr1[v] * Miyr1[t] + lim[ips]) * Sum(PrcStgips[r, p, c], 1)).where[
                PrcMap[r, "STK", p]
            ]
        ] = VAR_ACT[r, v, t, p, "ANNUAL", *sow].where[lim[ips]] + Sum(
            Domain(io[ips], Modlyear, Miyr1[ll]).where[RtpVintyr[r, Modlyear, t, p]],
            VAR_ACT[r, Modlyear, ll - lead[ll], p, "ANNUAL", *sow],
        ) == (
            (
                Sum(
                    tt[t - 1],
                    (VARTT_ACT_V.where[RtpVintyr[r, v, tt, p] & PrcVint[r, p]])
                    + (VARTT_ACT_TT.where[RtpVintyr[r, tt, tt, p] & (~PrcVint[r, p])]),
                )
                + (
                    Sum(
                        Miyr1[ll],
                        VAR_ACT[r, v, ll - lead[ll], p, "ANNUAL", *sow],
                    )
                ).where[Miyr1[t]]
            )
            * power(1 - stg_loss[r, v, p, "ANNUAL"], d[t])
            + Sum(
                Top[PrcStgips[r, p, c], io],
                (
                    VAR_SIN[r, v, t, p, c, "ANNUAL", *sow].where[ips[io]]
                    - VAR_SOUT[r, v, t, p, c, "ANNUAL", *sow].where[~ips[io]]
                )
                * Sum(
                    Periodyr[t, YEoh],
                    (1 - stg_loss[r, v, p, "ANNUAL"]) ** (e[t] - yearval[YEoh] + 0.5),
                )
                / prc_actflo[r, v, p, c],
            )
        ).where[lim[ips]] + Sum(
            Domain(io[ips], Miyr1[ll]), stg_chrg[r, ll - lead[ll], p, "ANNUAL"]
        )
