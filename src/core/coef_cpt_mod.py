# coef_cpt_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * COEF_CPT.MOD coefficient calculations related to capacity transfer          *
# *   %1 - mod or v# for the source code to be used                             *
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_RPTI calculated in PPMAIN.MOD
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Loop, Number, Ord, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, project

from core.base_class import GamsClass
from core.pp_shapr_mod import PpShaprMod
from core.utils import resolve_ctst

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefCptMod(GamsClass):
    """Translation unit for coef_cpt.mod."""

    module_name: str = "coef_cpt_mod"
    gams_source: str = "coef_cpt.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self: CoefCptMod) -> None:
        g = self.tc

        r, v, p, s, t, bd = g.r, g.v, g.p, g.s, g.t, g.bd

        self.tc.enqueue(
            self.exec_capacity_transfer,
            ctst=self.env.ctst,
            validate=self.env.validate == "YES",
        )

        self.tc.enqueue(self.exec_prepare_af_shape)

        self.include(
            PpShaprMod(
                self.tc,
                self.env,
                arg1=g.ncap_af,
                arg2=(r, v, p, s, bd),
                arg3=g.Trackp[r, p] * g.rp_afb[r, p, bd] * g.PrcTs[r, p, s],
                arg4=g.coef_af[g.RtpCptyr[r, v, t, p], s, bd],
                arg5=g.ncap_afm[r, v, p],
                arg6=g.ncap_afbx,
            )
        )

        self.tc.enqueue(self.exec_copy_non_shaped_af)

        self.include(
            PpShaprMod(
                self.tc,
                self.env,
                arg1=g.ncap_afs,
                arg2=(r, v, p, s, bd),
                arg3=g.RtpsBd[r, v, p, s, bd],
                arg4=g.coef_af[g.RtpCptyr[r, v, t, p], s, bd],
                arg5=g.ncap_afsm[r, v, p],
                arg6=g.ncap_afsx,
            )
        )

        self.tc.enqueue(self.exec_finalize)

    def exec_capacity_transfer(
        self: CoefCptMod, ctst: Literal["", "**EPS", "**0", "1"], validate: bool
    ) -> None:
        g = self.tc
        r, p, t, v = g.r, g.p, g.t, g.v

        # copy the period values into the years within the period
        with Loop(g.Periodyr[t, v].where[(~g.Phyr[v]).where[g.Vnt[v, t]]]):
            g.b[v] = g.b[t]
            g.e[v] = g.e[t]
            g.m[v] = g.m[t]
            g.d[v] = g.d[t]

        # capacity transfer - set here only when no alternate objective
        g.Fil.setRecords(None)
        g.Fil[v] = ~resolve_ctst(Number(0), ctst)

        g.pastsum[r, v, p].where[g.Rtp[r, v, p] & g.Fil[v] & g.PrcCap[r, p]] = (
            g.b[v] + g.ncap_iled[r, v, p] + g.coef_rpti[r, v, p] * g.ncap_tlife[r, v, p]
        )

        min_con = Min(g.e[t] + 1, g.pastsum[r, v, p])
        max_con = Max(g.b[v] + g.ncap_iled[r, v, p], g.b[t])
        g.coef_cpt[g.RtpCptyr[r, g.Fil[v], t, p]].where[g.pastsum[r, v, p]] = Max(
            0, (min_con - max_con) / g.d[t]
        )

        if validate:
            g.coef_cpt[g.RtpCptyr[r, t, t, p]] = 1

        g.pastsum.setRecords(None)

    def exec_prepare_af_shape(self: CoefCptMod) -> None:
        g = self.tc

        # Sets
        r, p, s, v, bd = g.r, g.p, g.s, g.v, g.bd
        ll, Rtp = g.ll, g.Rtp

        # Set NCAP_AF to be the minimum of NCAP_AF and NCAP_AFS, if both at same timeslice
        g.MyTs[s] = ~g.Annual[s]

        min_1 = (
            g.ncap_af[Rtp, s, bd]
            + Number(SpecialValues.POSINF).where[~g.ncap_af[Rtp, s, bd]]
        )
        min_2 = g.ncap_afs[Rtp, s, bd]
        g.ncap_af[Rtp[r, v, p], g.MyTs[s], bd].where[
            g.PrcTs[r, p, s].where[g.ncap_afs[Rtp, s, bd]]
        ] = Min(min_1, min_2)

        g.ncap_af[Rtp[r, v, p], s, g.Bdneq].where[
            g.PrcTs[r, p, s].where[g.ncap_afs[Rtp, s, "FX"]]
        ] = 0

        # Remove NCAP_AFS from timeslices that are not above PRC_TS:
        g.ncap_afs[Rtp[r, v, p], g.MyTs[s], bd].where[
            g.PrcTs[r, p, s] | (~g.RpsPrcts[r, p, s])
        ] = 0

        # * have COEF_AF SHAPEd
        # * [AL] Rules for vintage-dependent availabilities:
        # * -- If P is Vintaged, both NCAP_AF and NCAP_AFS are vintage-dependent;
        # * -- If P is NOT Vintaged but NCAP_AFX is specified, then only NCAP_AF is vintage-dependent;
        # * -- If P is NOT Vintaged nor NCAP_AFX is specified, then neither is vintage-dependent (except AFS(ANNUAL));
        # * -- NCAP_AFA is always non-vintage-dependent, but NCAP_AFS(ANNUAL) overrides it and is always vintaged.

        g.ncap_afx[r, ll.lag(Ord(ll), "circular"), p] = sparse(g.ncap_afm[r, ll, p])

        project(source=g.ncap_afx, target=g.Trackp)

        g.Trackp[g.Rp].where[~g.PrcCap[g.Rp]] = False
        g.Trackp[g.Rp].where[g.RpUpl[g.Rp, "FX"]] = False
        g.Trackp[g.PrcCap[g.PrcVint]] = True
        g.ncap_afbx[Rtp[r, v, p], bd].where[g.rp_afb[r, p, bd] > 0] = sparse(
            g.ncap_afx[Rtp]
        )

    def exec_copy_non_shaped_af(self: CoefCptMod) -> None:
        g = self.tc

        r, p, s, v, t, bd = g.r, g.p, g.s, g.v, g.t, g.bd
        Annual, Rtp = g.Annual, g.Rtp

        g.Trackp[g.PrcCap[r, p]] = ~g.Trackp[r, p]
        g.coef_af[g.RtpCptyr[r, v, t, p], s, bd].where[
            g.PrcTs[r, p, s].where[g.Trackp[r, p]]
        ] = sparse(g.ncap_af[r, t, p, s, bd])
        g.coef_af[g.RtpCptyr[r, v, t, p], Annual, bd].where[g.PrcCap[r, p]] = sparse(
            g.ncap_afa[r, t, p, bd]
        )

        # V07_2 add seasonal AF in addition to process tslvl
        project(source=g.ncap_afsm, target=g.RpPrc)

        g.ncap_afsm[r, v, p].where[~g.RpPrc[r, p]] = sparse(g.ncap_afm[r, v, p])
        g.ncap_afsx[Rtp, bd].where[g.ncap_afsm[Rtp]] = (
            g.ncap_afsx[Rtp, bd] + SpecialValues.EPS
        )
        g.RtpsBd[Rtp[r, v, p], s, bd].where[
            (g.PrcVint[r, p] | Annual[s] | (g.ncap_afsx[Rtp, bd] != 0))
            & g.ncap_afs[Rtp, s, bd]
        ] = True

        project(source=g.ncap_afsx, target=g.RpPrc)

        g.ncap_afsx[r, v, p, bd].where[Sum(g.RtpsBd[r, v, p, s, bd], 1)] = sparse(
            g.ncap_afx[r, v, p].where[~g.RpPrc[r, p]]
        )

    def exec_finalize(self: CoefCptMod) -> None:
        g = self.tc
        r, v, t, p, s, bd = g.r, g.v, g.t, g.p, g.s, g.bd

        # Assignments
        g.coef_af[g.RtpCptyr[r, v, t, p], s, bd].where[~g.RtpsBd[r, v, p, s, bd]] = (
            sparse(g.ncap_afs[r, t, p, s, bd].where[g.PrcCap[r, p]])
        )
        g.coef_af[g.RtpCptyr[r, v, t, p], g.Annual, g.Bdneq].where[
            g.ncap_afa[r, t, p, "FX"]
        ] = 0

        g.Trackp.setRecords(None)
        g.RtpsBd.setRecords(None)
        g.ncap_afbx.setRecords(None)
