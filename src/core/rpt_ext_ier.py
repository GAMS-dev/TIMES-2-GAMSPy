# rpt_ext_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * CHP reporting for the IER extension
# *=============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Sum, sparse

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtIer(GamsClass):
    """Translation unit for rpt_ext.ier."""

    # Instance attributes
    module_name: str = "rpt_ext_ier"
    gams_source: str = "rpt_ext.ier"

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
        if self.env.stages == "YES":
            return
        if self.env.vda == "YES":
            self.env.set_scoped("sow", ",'0'")
            self.env.set_scoped("sow_GP", ("0",))

        g = self.tc
        m = g.container

        g.par_bptl = Parameter(m, name="PAR_BPTL", domain=[g.r, g.t, g.p])
        g.par_bptm = Parameter(m, name="PAR_BPTM", domain=[g.r, g.t, g.p])
        g.par_condl = Parameter(m, name="PAR_CONDL", domain=[g.r, g.t, g.p])
        g.par_condm = Parameter(m, name="PAR_CONDM", domain=[g.r, g.t, g.p])
        g.par_heatl = Parameter(m, name="PAR_HEATL", domain=[g.r, g.t, g.p])
        g.par_heatm = Parameter(m, name="PAR_HEATM", domain=[g.r, g.t, g.p])
        g.ele_condl = Parameter(
            m, name="ELE_CONDL", domain=[g.r, g.year, g.year, g.p, g.c, g.s]
        )
        g.ele_condm = Parameter(
            m, name="ELE_CONDM", domain=[g.r, g.year, g.year, g.p, g.c, g.s]
        )
        g.ele_bptl = Parameter(
            m, name="ELE_BPTL", domain=[g.r, g.year, g.year, g.p, g.c, g.ts]
        )
        g.ele_bptm = Parameter(
            m, name="ELE_BPTM", domain=[g.r, g.year, g.year, g.p, g.c, g.ts]
        )

        self.tc.enqueue(self.exec1, self.env.sow_GP)

    def exec1(self: RptExtIer, sow: tuple[str | Set | Alias, ...]) -> None:
        g = self.tc
        r, t, v, p, c, ts = g.r, g.t, g.v, g.p, g.c, g.ts
        VAR_NCAP, VAR_FLO = g.VAR_NCAP, g.VAR_FLO

        # PAR_ACTL(R,V,T,P,S)$ECT_CHP(R,P)                       $= PAR_ACTL(R,V,T,P,S)*ECT_INP2ELC(R,V,P);
        # PAR_ACTM(R,V,T,P,S)$(PAR_ACTM(R,V,T,P,S)$ECT_CHP(R,P)) $= PAR_ACTM(R,V,T,P,S)/ECT_INP2ELC(R,V,P);

        # ---------------------------------------------------------------------
        # Output of VAR_CAP
        # ---------------------------------------------------------------------

        # The backpressure/condensing capacities are expressed in electricity
        # terms, so the input capacity is scaled by the ECT conversion factors.
        capl = Sum(
            g.RtpCptyr[r, v, t, p],
            g.ect_inp2elc[r, v, p]
            * g.coef_cpt[r, v, t, p]
            * (VAR_NCAP.l[r, v, p].where[t[v]] + g.ncap_pasti[r, v, p]),
        )
        capm = Sum(
            g.RtpCptyr[r, v, t, p],
            g.coef_cpt[r, v, t, p]
            / g.ect_inp2elc[r, v, p]
            * (VAR_NCAP.m[r, v, p] / g.vda_disc[r, v]).where[t[v]],
        )

        g.par_bptl[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = capl
        g.par_bptm[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = capm

        g.par_capl[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = capl
        g.par_pasti[g.Rtp[r, t, p], *sow].where[g.EctChp[r, p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.ect_inp2elc[r, v, p] * g.coef_cpt[r, v, t, p] * g.ncap_pasti[r, v, p],
        )
        g.par_capm[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = capm

        g.par_ncapl[g.Rtp[r, v, p]].where[g.EctChp[r, p]] = (
            VAR_NCAP.l[r, v, p] * g.ect_inp2elc[r, v, p]
        )
        g.par_ncapm[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = (
            VAR_NCAP.m[r, t, p] / g.ect_inp2elc[r, t, p] / g.coef_objinv[r, t, p]
        ).where[g.coef_objinv[r, t, p]]

        # ---------------------------------------------------------------------
        # ONLY for extraction condensing CHP plants
        # ---------------------------------------------------------------------

        g.par_condl[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.ect_inp2con[r, v, p]
            * g.coef_cpt[r, v, t, p]
            * (VAR_NCAP.l[r, v, p].where[t[v]] + g.ncap_pasti[r, v, p]),
        )
        g.par_condm[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.coef_cpt[r, v, t, p]
            / g.ect_inp2con[r, v, p]
            * VAR_NCAP.m[r, v, p].where[t[v]],
        )
        g.par_heatl[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.ect_inp2dht[r, v, p]
            * g.coef_cpt[r, v, t, p]
            * (VAR_NCAP.l[r, v, p].where[t[v]] + g.ncap_pasti[r, v, p]),
        )
        g.par_heatm[g.Rtp[r, t, p]].where[g.EctChp[r, p]] = Sum(
            g.RtpCptyr[r, v, t, p],
            g.coef_cpt[r, v, t, p]
            / g.ect_inp2dht[r, v, p]
            * VAR_NCAP.m[r, v, p].where[t[v]],
        )

        varf = g.RtpcsVarf[r, t, p, c, ts].where[g.EctElc[r, p, c]]
        heatl = Sum(
            g.EctDht[r, p, g.Com], g.ect_reh[r, v, p] * VAR_FLO.l[r, v, t, p, g.Com, ts]
        )
        heatm = Sum(
            g.EctDht[r, p, g.Com], VAR_FLO.m[r, v, t, p, g.Com, ts] / g.ect_reh[r, v, p]
        )

        g.ele_bptl[g.RtpVintyr[r, v, t, p], c, ts].where[varf] = sparse(heatl)
        g.ele_bptm[g.RtpVintyr[r, v, t, p], c, ts].where[varf] = sparse(heatm)
        g.ele_condl[g.RtpVintyr[r, v, t, p], c, ts].where[varf] = (
            VAR_FLO.l[r, v, t, p, c, ts] - heatl
        )
        g.ele_condm[g.RtpVintyr[r, v, t, p], c, ts].where[varf] = (
            VAR_FLO.m[r, v, t, p, c, ts] - heatm
        )
