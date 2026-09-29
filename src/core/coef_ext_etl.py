# coef_ext_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# ******************************************************************************
# * COEF_ETL.ETL - Calculate technological change parameters                   *
# ******************************************************************************

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Ord, SpecialValues, Sum, sparse
from gamspy.math import Round, log

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefExtEtl(GamsClass):
    """Translation unit for coef_ext.etl."""

    # Instance attributes
    module_name: str = "coef_ext_etl"
    gams_source: str = "coef_ext.etl"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.exec1)

    def exec1(self: CoefExtEtl) -> None:
        g = self.tc

        r, p, prc, t, Reg, cur = g.r, g.p, g.prc, g.t, g.Reg, g.cur
        kp, kp2, Teg, Rp, Rtp, Miyr1, Eachyear = (
            g.kp,
            g.kp2,
            g.Teg,
            g.Rp,
            g.Rtp,
            g.Miyr1,
            g.Eachyear,
        )
        cnt, prc_ymin = g.cnt, g.prc_ymin
        sc0, prat, seg, ccap0, ccapm, cluster = (
            g.sc0,
            g.prat,
            g.seg,
            g.ccap0,
            g.ccapm,
            g.cluster,
        )
        tl_sc0, tl_prat, tl_seg, tl_ccap0, tl_ccapm, tl_cluster, tl_mrclust = (
            g.tl_sc0,
            g.tl_prat,
            g.tl_seg,
            g.tl_ccap0,
            g.tl_ccapm,
            g.tl_cluster,
            g.tl_mrclust,
        )
        pat, pbt, ccost0, ccostm, weig, ccostk, ccapk, beta, alph, ntchteg = (
            g.pat,
            g.pbt,
            g.ccost0,
            g.ccostm,
            g.weig,
            g.ccostk,
            g.ccapk,
            g.beta,
            g.alph,
            g.ntchteg,
        )
        tl_start, tl_rp_kc, tl_rp_ct = g.tl_start, g.tl_rp_kc, g.tl_rp_ct

        # * copy aliases
        sc0[r, p] = sparse(tl_sc0[r, p])
        prat[r, p] = sparse(tl_prat[r, p])
        seg[r, p] = sparse(tl_seg[r, p])
        ccap0[r, p] = sparse(tl_ccap0[r, p])
        ccapm[r, p] = sparse(tl_ccapm[r, p])
        cluster[r, p, prc] = sparse(tl_cluster[r, p, prc])

        # * ensure integral SEG; set TEG on from SEG
        seg[r, p].where[seg[r, p]] = Round(seg[r, p]).where[Rp[r, p]]
        with Loop(r):
            Teg[p].where[seg[r, p]] = Rp[r, p]

        # * Starting periods for learning technologies
        prc_ymin.setRecords(None)
        with Loop(t):
            prc_ymin[r, Teg[p]].where[(~prc_ymin[r, p]) * Rtp[r, t, p]] = (
                Ord(t) - 1 + SpecialValues.EPS
            )
        with Loop(Miyr1[t]):
            tl_start[Rtp[r, t.lead(prc_ymin[r, p]), Teg[p]]] = True

        # * computation of the learning curve exponent
        pbt[r, Teg].where[seg[r, Teg]] = -log(prat[r, Teg]) / log(2)

        # * computation of the learning curve coefficient
        pat[r, Teg].where[seg[r, Teg]] = sc0[r, Teg] * (ccap0[r, Teg] ** pbt[r, Teg])

        # * assignment of the initial cumulative cost
        ccost0[r, Teg].where[seg[r, Teg]] = (pat[r, Teg] / (1 - pbt[r, Teg])) * (
            ccap0[r, Teg] ** (1 - pbt[r, Teg])
        )

        # * assignment of the maximum cumulative cost
        ccostm[r, Teg].where[seg[r, Teg]] = (pat[r, Teg] / (1 - pbt[r, Teg])) * (
            ccapm[r, Teg] ** (1 - pbt[r, Teg])
        )

        # * assignment of the kink points for cumulative cost
        with Loop(kp.where[Ord(kp) >= 2]):
            cnt[...] = Ord(kp) - 2
            weig[r, kp, Teg].where[seg[r, Teg]] = (2 ** (-seg[r, Teg] + cnt)) / Sum(
                kp2.where[Ord(kp2) <= seg[r, Teg]],
                2 ** (-seg[r, Teg] + Ord(kp2) - 1),
            )

        # *$ IF NOT %ETL%==YES $GOTO NOMIP
        ccostk[r, "1", Teg] = ccost0[r, Teg]
        with Loop(kp.where[Ord(kp) >= 2]):
            ccostk[r, kp, Teg].where[seg[r, Teg]] = ccostk[r, kp.lag(1), Teg] + (
                (ccostm[r, Teg] - ccost0[r, Teg]) * weig[r, kp, Teg]
            )

        # * assignment of the kink points for cumulative capacity
        ccapk[r, kp, Teg].where[(Ord(kp) <= seg[r, Teg] + 1) * seg[r, Teg]] = (
            ((1 - pbt[r, Teg]) / pat[r, Teg]) * ccostk[r, kp, Teg]
        ) ** (1 / (1 - pbt[r, Teg]))

        # * assignment of beta coeff. for interpolation of cumulative cost
        beta[r, kp, Teg].where[(Ord(kp) <= seg[r, Teg] + 1) * seg[r, Teg]] = (
            ccostk[r, kp, Teg] - ccostk[r, kp.lag(1), Teg]
        ) / (ccapk[r, kp, Teg] - ccapk[r, kp.lag(1), Teg])

        # * assignment of alpha coeff. for interpolation of cumulative cost
        alph[r, kp, Teg].where[(Ord(kp) <= seg[r, Teg] + 1) * seg[r, Teg]] = (
            ccostk[r, kp.lag(1), Teg] - beta[r, kp, Teg] * ccapk[r, kp.lag(1), Teg]
        )

        # * determine NTCHTEG, number of PRC's in learning cluster
        ntchteg[r, Teg].where[seg[r, Teg]] = Sum(prc.where[cluster[r, Teg, prc] > 0], 1)

        # * perhaps other defaults for testing purposes: growth factors etc.

        # *-----------------------------------------------------------------------------
        # * Create a set of all key components of cluster technologies
        # * Create a set of all cluster technologies
        with Loop(
            Domain(Rp[r, p], Reg, prc).where[
                (tl_mrclust[r, p, Reg, prc] > 0.0) * tl_mrclust[r, p, Reg, prc]
            ]
        ):
            tl_rp_kc[r, p] = True
            tl_rp_ct[Reg, prc] = True

        # *-----------------------------------------------------------------------------
        # * setting normal NCAP_COST of ETL technologies to zero to exclude this
        # * contribution fro the objective function
        macro.obj_icost_GP(r, Eachyear, p, cur)[...].where[seg[r, p]] = 0
        # *-----------------------------------------------------------------------------
        print(ccapk.records)
        print(beta.records)
        print(alph.records)
        # *$LABEL NOMIP
