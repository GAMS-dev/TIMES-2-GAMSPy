# equ_ext_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# *  EQETL.ETL technological change equations, with clusters
# *============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Ord, Sum

from core.base_class import GamsClass
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitVariable

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtEtl(GamsClass):
    """Translation unit for equ_ext.etl."""

    # Instance attributes
    module_name: str = "equ_ext_etl"
    gams_source: str = "equ_ext.etl"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc

        r, t, v, p, prc, Reg = g.r, g.t, g.v, g.p, g.prc, g.Reg
        kp, kp2, Teg, Rtp, Milestonyr = g.kp, g.kp2, g.Teg, g.Rtp, g.Milestonyr
        seg, ccap0, ccost0, beta, alph, ccapk = (
            g.seg,
            g.ccap0,
            g.ccost0,
            g.beta,
            g.alph,
            g.ccapk,
        )
        coef_rpti, ntchteg, cluster = g.coef_rpti, g.ntchteg, g.cluster
        tl_start, tl_rp_kc, tl_rp_ct, tl_mrclust = (
            g.tl_start,
            g.tl_rp_kc,
            g.tl_rp_ct,
            g.tl_mrclust,
        )

        eq = self.env.eq
        var = self.env.var
        r_t = self.env.r_t_GP
        swt = self.env.swt_GP
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        varv_id, varv_set = self.env.varv_GP

        VAR_CCAP = g.get_variable(f"{var}_CCAP")
        VAR_CCOST = g.get_variable(f"{var}_CCOST")
        VAR_LAMBD = g.get_variable(f"{var}_LAMBD")
        VAR_DELTA = g.get_variable(f"{var}_DELTA")
        VAR_IC = g.get_variable(f"{var}_IC")
        VARV_CCOST = g.get_variable(f"{varv_id}_CCOST")
        VARV_DELTA = g.get_variable(f"{varv_id}_DELTA")

        eq_cuinv = g.get_equation(f"{eq}_CUINV")
        eq_cc = g.get_equation(f"{eq}_CC")
        eq_del = g.get_equation(f"{eq}_DEL")
        eq_cos = g.get_equation(f"{eq}_COS")
        eq_la1 = g.get_equation(f"{eq}_LA1")
        eq_la2 = g.get_equation(f"{eq}_LA2")
        eq_expe1 = g.get_equation(f"{eq}_EXPE1")
        eq_expe2 = g.get_equation(f"{eq}_EXPE2")
        eq_ic1 = g.get_equation(f"{eq}_IC1")
        eq_ic2 = g.get_equation(f"{eq}_IC2")
        eq_clu = g.get_equation(f"{eq}_CLU")
        eq_mrclu = g.get_equation(f"{eq}_MRCLU")

        # %VARV%_<var>(...%SWS%) is either the plain vintage-indexed variable or,
        # under STAGES, the state-of-the-world weighted SUM(SW_TSW(SOW,V,W),VAS_...(...,W)).
        ccost_v: ImplicitVariable | Sum = VARV_CCOST[r, v, Teg, *sws]
        delta_v: ImplicitVariable | Sum = VARV_DELTA[r, v, Teg, kp2, *sws]
        if varv_set is not None:
            ccost_v = Sum(varv_set, ccost_v)
            delta_v = Sum(varv_set, delta_v)

        # ORD(KP) GE 2 and below the number of segments of the learning curve
        kp_active = (Ord(kp) >= 2) & (Ord(kp) <= seg[r, Teg] + 1)

        # *-----------------------------------------------------------------------------
        # * Cumulative capacity definition
        # * [AL] May-2006: Added COEF_RPTI multiplier; It is also added to EQ_IC1 and EQ_IC2.
        eq_cuinv[*r_t, Teg, *swt].where[Rtp[r, t, Teg] * seg[r, Teg]] = VAR_CCAP[
            r, t, Teg, *sow
        ] == (
            Sum(
                Rtp[r, v[Milestonyr], Teg].where[Ord(Milestonyr) <= Ord(t)],
                macro.VAR_NCAP_GP(self.env.varv_GP, r, v, Teg, sws)
                * coef_rpti[r, v, Teg],
            )
            + ccap0[r, Teg]
        )

        # * Cumulative Capacity Interpolation
        eq_cc[Rtp[*r_t, Teg], *swt].where[seg[r, Teg]] = VAR_CCAP[
            r, t, Teg, *sow
        ] == Sum(kp.where[kp_active], VAR_LAMBD[r, t, Teg, kp, *sow])

        # * Force sum of binary variables delta to 1
        eq_del[Rtp[*r_t, Teg], *swt].where[seg[r, Teg]] = (
            Sum(kp.where[kp_active], VAR_DELTA[r, t, Teg, kp, *sow]) == 1
        )

        # * Cumulative Cost Interpolation
        eq_cos[Rtp[*r_t, Teg], *swt].where[seg[r, Teg]] = VAR_CCOST[
            r, t, Teg, *sow
        ] == Sum(
            kp.where[kp_active],
            VAR_LAMBD[r, t, Teg, kp, *sow] * beta[r, kp, Teg]
            + VAR_DELTA[r, t, Teg, kp, *sow] * alph[r, kp, Teg],
        )

        # * Constraints on lambda
        eq_la1[Rtp[*r_t, Teg], kp, *swt].where[kp_active & seg[r, Teg]] = (
            VAR_LAMBD[r, t, Teg, kp, *sow]
            >= ccapk[r, kp.lag(1), Teg] * VAR_DELTA[r, t, Teg, kp, *sow]
        )

        eq_la2[Rtp[*r_t, Teg], kp, *swt].where[kp_active & seg[r, Teg]] = (
            VAR_LAMBD[r, t, Teg, kp, *sow]
            <= ccapk[r, kp, Teg] * VAR_DELTA[r, t, Teg, kp, *sow]
        )

        # * Additional constraints to improve solution time
        # * The GAMS source spells the right-hand-side filter as
        # *   ORD(KP2) LE ORD(KP)$(ORD(KP2) GE 2)
        # * which zeroes out ORD(KP) for KP2='1' and is therefore the very same
        # * condition as the left-hand side; both use kp2_le_kp here.
        kp2_le_kp = (Ord(kp2) <= Ord(kp)) & (Ord(kp2) >= 2)
        eq_expe1[Rtp[r, v[t.lag(1)], Teg], kp, *swt].where[kp_active & seg[r, Teg]] = (
            Sum(kp2.where[kp2_le_kp], delta_v)
            >= Sum(kp2.where[kp2_le_kp], VAR_DELTA[r, t, Teg, kp2, *sow])
        )

        eq_expe2[Rtp[r, v[t.lag(1)], Teg], kp, *swt].where[kp_active & seg[r, Teg]] = (
            Sum(kp2.where[Ord(kp2) >= Ord(kp)], delta_v)
            <= Sum(kp2.where[Ord(kp2) >= Ord(kp)], VAR_DELTA[r, t, Teg, kp2, *sow])
        )

        # * Investments 1st period
        eq_ic1[tl_start[*r_t, Teg], *swt].where[seg[r, Teg]] = (
            VAR_IC[r, t, Teg, *sow] * coef_rpti[r, t, Teg]
            == VAR_CCOST[r, t, Teg, *sow] - ccost0[r, Teg]
        )

        # * Investments other periods
        eq_ic2[Rtp[*r_t, Teg], *swt].where[~tl_start[r, t, Teg] & seg[r, Teg]] = VAR_IC[
            r, t, Teg, *sow
        ] * coef_rpti[r, t, Teg] == VAR_CCOST[r, t, Teg, *sow] - Sum(
            v[t.lag(1)], ccost_v
        )

        # * Salvage of learning investments: Handled in TIMES by EQOBSALV.mod

        # * Coupling equation for key in TEG to cluster TCH's, only if TCH in cluster TEG and TEG NE TCH
        eq_clu[Rtp[*r_t, Teg], *swt].where[ntchteg[r, Teg]] = macro.VAR_NCAP_GP(
            var, r, t, Teg, sow
        ) == Sum(
            prc.where[Rtp[r, t, prc] * cluster[r, Teg, prc]],
            cluster[r, Teg, prc] * macro.VAR_NCAP_GP(var, r, t, prc, sow),
        )

        # *-----------------------------------------------------------------------------
        # * new clustering equation
        eq_mrclu[Rtp[*r_t, Teg], *swt].where[tl_rp_kc[r, Teg]] = macro.VAR_NCAP_GP(
            var, r, t, Teg, sow
        ) == Sum(
            tl_rp_ct[Reg, p].where[Rtp[Reg, t, p]],
            tl_mrclust[r, Teg, Reg, p] * macro.VAR_NCAP_GP(var, Reg, t, p, sow),
        )
