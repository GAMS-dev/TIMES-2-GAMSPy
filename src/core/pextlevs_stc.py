# pextlevs_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PEXTLEVS.stc: Get the expected values
# *  {arg1} - SOW control
# *  {arg2} - Period control
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Sum, sparse

from core.base_class import GamsClass
from core.clearsol_stc import clearsol_stc

if TYPE_CHECKING:
    from core.utils import SET_OR_ALIAS
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class PextlevsStcConfig:
    arg1: str = ""
    arg2: str = ""
    arg1_GP: tuple[SET_OR_ALIAS | str] | tuple[()] = ()


class PextlevsStc(GamsClass):
    """Translation unit for pextlevs.stc"""

    # Instance attributes
    module_name: str = "pextlevs_stc"
    gams_source: str = "pextlevs.stc"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: PextlevsStcConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        cc = self.config
        if cc.arg2 != "":
            raise NotImplementedError(
                "Period control (arg2) is only supported by the raw GAMS variant of "
                "pextlevs.stc, which is inlined into GAMS control flow by solve_stp.py."
            )
        if not cc.arg1_GP:
            raise NotImplementedError(
                f"No GAMSPy handle for the SOW control (arg1={cc.arg1!r}) of pextlevs.stc."
            )

        self.tc.enqueue(
            self.exec_pextlevs_stc,
            arg1_GP=cc.arg1_GP,
            eq=self.env.eq,
            var=self.env.var,
            timesed=self.env.timesed,
            var_dam_defined=self.tc.defined(f"{self.env.var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
        )

    def exec_pextlevs_stc(
        self: PextlevsStc,
        arg1_GP: tuple[SET_OR_ALIAS | str] | tuple[()],
        eq: str,
        var: str,
        timesed: str,
        var_dam_defined: bool,
        var_scap_defined: bool,
    ) -> None:
        pextlevs_stc_GP(
            g=self.tc,
            arg1_GP=arg1_GP,
            eq=eq,
            var=var,
            timesed=timesed,
            var_dam_defined=var_dam_defined,
            var_scap_defined=var_scap_defined,
        )


def pextlevs_stc_GP(
    *,
    g: TimesModelClass,
    arg1_GP: tuple[SET_OR_ALIAS | str] | tuple[()],
    eq: str,
    var: str,
    timesed: str,
    var_dam_defined: bool,
    var_scap_defined: bool,
) -> None:
    # * Clear results from previous
    clearsol_stc(
        g=g,
        var_dam_defined=var_dam_defined,
        var_scap_defined=var_scap_defined,
    )

    (r, v, t, p, s, c, cg, ie, j, bd, lA) = (
        g.r,
        g.v,
        g.t,
        g.p,
        g.s,
        g.c,
        g.cg,
        g.ie,
        g.j,
        g.bd,
        g.lA,
    )
    (Com, comvar, year, ll, w, Sow, ucn, ucgrptype, obv, cur) = (
        g.Com,
        g.comvar,
        g.year,
        g.ll,
        g.w,
        g.Sow,
        g.ucn,
        g.ucgrptype,
        g.obv,
        g.cur,
    )
    (Rpc, Bdneq, RcCumcom, RpcCumflo, SwT, sw_tprob, sw_prob) = (
        g.Rpc,
        g.Bdneq,
        g.RcCumcom,
        g.RpcCumflo,
        g.SwT,
        g.sw_tprob,
        g.sw_prob,
    )

    # %EQ%/%VAR% carry the stochastic prefixes (ES/VAS); the plain EQ*/VAR_*
    # symbols on the left-hand side hold the expected values.
    (
        esg_combal,
        ese_combal,
        ese_comprd,
        es_peak,
        es_ire,
        ese_cpt,
        ese_ucrtp,
        esn_ucrtp,
    ) = (
        g.get_equation(f"{eq}G_COMBAL"),
        g.get_equation(f"{eq}E_COMBAL"),
        g.get_equation(f"{eq}E_COMPRD"),
        g.get_equation(f"{eq}_PEAK"),
        g.get_equation(f"{eq}_IRE"),
        g.get_equation(f"{eq}E_CPT"),
        g.get_equation(f"{eq}E_UCRTP"),
        g.get_equation(f"{eq}N_UCRTP"),
    )

    # * Get the sum of weighted Marginals
    g.eqg_combal.m[r, t, c, s] = sparse(Sum(SwT[t, w], esg_combal.m[r, t, c, s, t, w]))
    g.eqe_combal.m[r, t, c, s] = sparse(Sum(SwT[t, w], ese_combal.m[r, t, c, s, t, w]))
    g.eqe_comprd.m[r, t, c, s] = sparse(Sum(SwT[t, w], ese_comprd.m[r, t, c, s, t, w]))
    g.eq_peak.m[r, t, cg, s] = sparse(Sum(SwT[t, w], es_peak.m[r, t, cg, s, t, w]))
    g.eq_ire.m[r, t, p, c, ie, s] = sparse(
        Sum(SwT[t, w], es_ire.m[r, t, p, c, ie, s, t, w])
    )
    g.eqe_cpt.m[r, t, p] = sparse(
        Sum(SwT[(t, *arg1_GP)], ese_cpt.m[(r, t, p, t, *arg1_GP)])
    )
    g.eqn_ucrtp.m[ucn, r, t, p, ucgrptype, bd["FX"]] = sparse(
        Sum(SwT[t, w], ese_ucrtp.m[ucn, r, t, p, ucgrptype, bd, t, w])
    )
    g.eqn_ucrtp.m[ucn, r, t, p, ucgrptype, Bdneq[bd]] = sparse(
        Sum(SwT[t, w], esn_ucrtp.m[ucn, r, t, p, ucgrptype, bd, t, w])
    )

    (
        VAS_ACT,
        VAS_BLND,
        VAS_COMNET,
        VAS_COMPRD,
        VAS_IRE,
        VAS_ELAST,
        VAS_FLO,
        VAS_SIN,
        VAS_SOUT,
        VAS_UPS,
        VAS_CUMCOM,
        VAS_CUMFLO,
    ) = (
        g.get_variable(f"{var}_ACT"),
        g.get_variable(f"{var}_BLND"),
        g.get_variable(f"{var}_COMNET"),
        g.get_variable(f"{var}_COMPRD"),
        g.get_variable(f"{var}_IRE"),
        g.get_variable(f"{var}_ELAST"),
        g.get_variable(f"{var}_FLO"),
        g.get_variable(f"{var}_SIN"),
        g.get_variable(f"{var}_SOUT"),
        g.get_variable(f"{var}_UPS"),
        g.get_variable(f"{var}_CUMCOM"),
        g.get_variable(f"{var}_CUMFLO"),
    )

    # * Get the expected Levels
    g.VAR_ACT.l[r, v, t, p, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_ACT.l[r, v, t, p, s, w])
    )
    g.VAR_BLND.l[r, t, Com, c] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_BLND.l[r, t, Com, c, w])
    )
    g.VAR_COMNET.l[r, t, Com, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_COMNET.l[r, t, Com, s, w])
    )
    g.VAR_COMPRD.l[r, t, Com, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_COMPRD.l[r, t, Com, s, w])
    )
    g.VAR_IRE.l[r, v, t, p, c, s, ie] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_IRE.l[r, v, t, p, c, s, ie, w])
    )
    g.VAR_ELAST.l[r, t, c, s, j, bd] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_ELAST.l[r, t, c, s, j, bd, w])
    )
    g.VAR_FLO.l[r, v, t, p, c, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_FLO.l[r, v, t, p, c, s, w])
    )
    g.VAR_SIN.l[r, v, t, p, c, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_SIN.l[r, v, t, p, c, s, w])
    )
    g.VAR_SOUT.l[r, v, t, p, c, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_SOUT.l[r, v, t, p, c, s, w])
    )
    g.VAR_UPS.l[r, v, t, p, s, lA] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_UPS.l[r, v, t, p, s, lA, w])
    )
    g.VAR_CUMCOM.l[r, c, comvar, year, ll].where[RcCumcom[r, comvar, year, ll, c]] = (
        sparse(Sum(w, sw_prob[w] * VAS_CUMCOM.l[r, c, comvar, year, ll, w]))
    )
    g.VAR_CUMFLO.l[Rpc, year, ll].where[RpcCumflo[Rpc, year, ll]] = sparse(
        Sum(w, sw_prob[w] * VAS_CUMFLO.l[Rpc, year, ll, w])
    )
    if var_dam_defined:
        VAS_DAM = g.get_variable(f"{var}_DAM")
        g.VAR_DAM.l[r, t, c, bd, j] = sparse(
            Sum(SwT[t, w], sw_tprob[t, w] * VAS_DAM.l[r, t, c, bd, j, w])
        )
    if timesed == "YES":
        VAS_OBJELS = g.get_variable(f"{var}_OBJELS")
        g.VAR_OBJELS.l[r, bd, cur] = sparse(
            Sum(w, sw_prob[w] * VAS_OBJELS.l[r, bd, cur, w])
        )

    (VAS_CAP, VAS_NCAP, VAS_SCAP) = (
        g.get_variable(f"{var}_CAP"),
        g.get_variable(f"{var}_NCAP"),
        g.get_variable(f"{var}_SCAP"),
    )
    g.VAR_CAP.l[r, t, p] = sparse(
        Sum(SwT[t, Sow], sw_tprob[t, Sow] * VAS_CAP.l[(r, t, p, *arg1_GP)])
    )
    g.VAR_NCAP.l[r, t, p] = sparse(
        Sum(SwT[t, Sow], sw_tprob[t, Sow] * VAS_NCAP.l[(r, t, p, *arg1_GP)])
    )
    g.VAR_SCAP.l[r, v, t, p] = sparse(
        Sum(SwT[t, Sow], sw_tprob[t, Sow] * VAS_SCAP.l[(r, v, t, p, *arg1_GP)])
    )

    (VAS_UC, VAS_UCR, VAS_UCT, VAS_UCRT, VAS_UCTS, VAS_UCRTS, VAS_OBJ) = (
        g.get_variable(f"{var}_UC"),
        g.get_variable(f"{var}_UCR"),
        g.get_variable(f"{var}_UCT"),
        g.get_variable(f"{var}_UCRT"),
        g.get_variable(f"{var}_UCTS"),
        g.get_variable(f"{var}_UCRTS"),
        g.get_variable(f"{var}_OBJ"),
    )
    g.VAR_UC.l[ucn] = sparse(Sum(w, sw_prob[w] * VAS_UC.l[ucn, w]))
    g.VAR_UCR.l[ucn, r] = sparse(Sum(w, sw_prob[w] * VAS_UCR.l[ucn, r, w]))
    g.VAR_UCT.l[ucn, t] = sparse(Sum(SwT[t, w], sw_tprob[t, w] * VAS_UCT.l[ucn, t, w]))
    g.VAR_UCRT.l[ucn, r, t] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_UCRT.l[ucn, r, t, w])
    )
    g.VAR_UCTS.l[ucn, t, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_UCTS.l[ucn, t, s, w])
    )
    g.VAR_UCRTS.l[ucn, r, t, s] = sparse(
        Sum(SwT[t, w], sw_tprob[t, w] * VAS_UCRTS.l[ucn, r, t, s, w])
    )
    g.VAR_OBJ.l[r, obv, cur] = sparse(Sum(w, sw_prob[w] * VAS_OBJ.l[r, obv, cur, w]))

    # * Get the sum of weighted Marginals
    g.VAR_ACT.m[r, v, t, p, s] = sparse(Sum(SwT[t, w], VAS_ACT.m[r, v, t, p, s, w]))
    g.VAR_COMNET.m[r, t, Com, s] = sparse(Sum(SwT[t, w], VAS_COMNET.m[r, t, Com, s, w]))
    g.VAR_COMPRD.m[r, t, Com, s] = sparse(Sum(SwT[t, w], VAS_COMPRD.m[r, t, Com, s, w]))
    g.VAR_CUMFLO.m[r, p, c, year, ll] = sparse(
        Sum(w, VAS_CUMFLO.m[r, p, c, year, ll, w])
    )
    g.VAR_CAP.m[r, t, p] = sparse(
        Sum(SwT[(t, *arg1_GP)], VAS_CAP.m[(r, t, p, *arg1_GP)])
    )
    g.VAR_NCAP.m[r, t, p] = sparse(
        Sum(SwT[(t, *arg1_GP)], VAS_NCAP.m[(r, t, p, *arg1_GP)])
    )

    g.VAR_UC.m[ucn] = sparse(Sum(w, VAS_UC.m[ucn, w]))
    g.VAR_UCR.m[ucn, r] = sparse(Sum(w, VAS_UCR.m[ucn, r, w]))
    g.VAR_UCT.m[ucn, t] = sparse(Sum(SwT[t, w], VAS_UCT.m[ucn, t, w]))
    g.VAR_UCRT.m[ucn, r, t] = sparse(Sum(SwT[t, w], VAS_UCRT.m[ucn, r, t, w]))
    g.VAR_UCTS.m[ucn, t, s] = sparse(Sum(SwT[t, w], VAS_UCTS.m[ucn, t, s, w]))
    g.VAR_UCRTS.m[ucn, r, t, s] = sparse(Sum(SwT[t, w], VAS_UCRTS.m[ucn, r, t, s, w]))


# The raw GAMS variant is still needed by solve_stp.py, which inlines pextlevs.stc
# into a GAMS LOOP that has not been translated yet.
def pextlevs_stc(
    *,
    tc: TimesModelClass,
    arg1: str,
    arg2: str,
    eq: str,
    var: str,
    timesed: str,
    var_dam_defined: bool,
    var_scap_defined: bool,
) -> str:
    return rf"""
{
        clearsol_stc(
            g=tc,
            var_dam_defined=var_dam_defined,
            var_scap_defined=var_scap_defined,
            inline=True,
        )
    }
* Get the sum of weighted Marginals
  EQG_COMBAL.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}G_COMBAL.M(R,T,C,S,T,W));
  EQE_COMBAL.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}E_COMBAL.M(R,T,C,S,T,W));
  EQE_COMPRD.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}E_COMPRD.M(R,T,C,S,T,W));
  EQ_PEAK.M(R,T{arg2},CG,S)   $= SUM(SW_T(T,W), {eq}_PEAK.M(R,T,CG,S,T,W));
  EQ_IRE.M(R,T{arg2},P,C,IE,S) $= SUM(SW_T(T,W), {eq}_IRE.M(R,T,P,C,IE,S,T,W));
  EQE_CPT.M(R,T{arg2},P)      $= SUM(SW_T(T,{arg1}),  {eq}E_CPT.M(R,T,P,T,{arg1}));
  EQN_UCRTP.M(UC_N,R,T{arg2},P,UC_GRPTYPE,BD('FX'))  $= SUM(SW_T(T,W), {
        eq
    }E_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W));
  EQN_UCRTP.M(UC_N,R,T{arg2},P,UC_GRPTYPE,BDNEQ(BD)) $= SUM(SW_T(T,W), {
        eq
    }N_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W));

* Get the expected Levels
  VAR_ACT.L(R,V,T{arg2},P,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_ACT.L(R,V,T,P,S,W));
  VAR_BLND.L(R,T{arg2},COM,C) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_BLND.L(R,T,COM,C,W));
  VAR_COMNET.L(R,T{arg2},COM,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_COMNET.L(R,T,COM,S,W));
  VAR_COMPRD.L(R,T{arg2},COM,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_COMPRD.L(R,T,COM,S,W));
  VAR_IRE.L(R,V,T{arg2},P,C,S,IE) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_IRE.L(R,V,T,P,C,S,IE,W));
  VAR_ELAST.L(R,T{arg2},C,S,J,BD) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_ELAST.L(R,T,C,S,J,BD,W));
  VAR_FLO.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_FLO.L(R,V,T,P,C,S,W));
  VAR_SIN.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_SIN.L(R,V,T,P,C,S,W));
  VAR_SOUT.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_SOUT.L(R,V,T,P,C,S,W));
  VAR_UPS.L(R,V,T{arg2},P,S,L) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{
        var
    }_UPS.L(R,V,T,P,S,L,W));
  VAR_CUMCOM.L(R,C,COM_VAR,YEAR,LL)$RC_CUMCOM(R,COM_VAR,YEAR,LL,C) $= SUM(W, SW_PROB(W)*{
        var
    }_CUMCOM.L(R,C,COM_VAR,YEAR,LL,W));
  VAR_CUMFLO.L(RPC,YEAR,LL)$RPC_CUMFLO(RPC,YEAR,LL) $= SUM(W, SW_PROB(W)*{
        var
    }_CUMFLO.L(RPC,YEAR,LL,W));
{
        f"VAR_DAM.L(R,T{arg2},C,BD,J) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_DAM.L(R,T,C,BD,J,W));"
        if var_dam_defined
        else ""
    }
{
        f"VAR_OBJELS.L(R,BD,CUR)  $= SUM(W, SW_PROB(W)*{var}_OBJELS.L(R,BD,CUR,W));"
        if timesed == "YES"
        else ""
    }
  VAR_CAP.L(R,T{arg2},P)  $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_CAP.L(R,T,P,{
        arg1
    }));
  VAR_NCAP.L(R,T{arg2},P) $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_NCAP.L(R,T,P,{
        arg1
    }));
  VAR_SCAP.L(R,V,T{arg2},P) $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_SCAP.L(R,V,T,P,{
        arg1
    }));

  VAR_UC.L(UC_N) $= SUM(W, SW_PROB(W)*{var}_UC.L(UC_N,W));
  VAR_UCR.L(UC_N,R) $= SUM(W, SW_PROB(W)*{var}_UCR.L(UC_N,R,W));
  VAR_UCT.L(UC_N,T) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_UCT.L(UC_N,T,W));
  VAR_UCRT.L(UC_N,R,T) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_UCRT.L(UC_N,R,T,W));
  VAR_UCTS.L(UC_N,T,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_UCTS.L(UC_N,T,S,W));
  VAR_UCRTS.L(UC_N,R,T,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_UCRTS.L(UC_N,R,T,S,W));
  VAR_OBJ.L(R,OBV,CUR) $= SUM(W, SW_PROB(W)*{var}_OBJ.L(R,OBV,CUR,W));

* Get the sum of weighted Marginals
  VAR_ACT.M(R,V,T{arg2},P,S) $= SUM(SW_T(T,W), {var}_ACT.M(R,V,T,P,S,W));
  VAR_COMNET.M(R,T{arg2},COM,S) $= SUM(SW_T(T,W), {var}_COMNET.M(R,T,COM,S,W));
  VAR_COMPRD.M(R,T{arg2},COM,S) $= SUM(SW_T(T,W), {var}_COMPRD.M(R,T,COM,S,W));
  VAR_CUMFLO.M(R,P,C,YEAR,LL) $= SUM(W, {var}_CUMFLO.M(R,P,C,YEAR,LL,W));
  VAR_CAP.M(R,T{arg2},P)     $= SUM(SW_T(T,{arg1}), {var}_CAP.M(R,T,P,{arg1}));
  VAR_NCAP.M(R,T{arg2},P)    $= SUM(SW_T(T,{arg1}), {var}_NCAP.M(R,T,P,{arg1}));

  VAR_UC.M(UC_N) $= SUM(W, {var}_UC.M(UC_N,W));
  VAR_UCR.M(UC_N,R) $= SUM(W, {var}_UCR.M(UC_N,R,W));
  VAR_UCT.M(UC_N,T) $= SUM(SW_T(T,W), {var}_UCT.M(UC_N,T,W));
  VAR_UCRT.M(UC_N,R,T) $= SUM(SW_T(T,W), {var}_UCRT.M(UC_N,R,T,W));
  VAR_UCTS.M(UC_N,T,S) $= SUM(SW_T(T,W), {var}_UCTS.M(UC_N,T,S,W));
  VAR_UCRTS.M(UC_N,R,T,S) $= SUM(SW_T(T,W), {var}_UCRTS.M(UC_N,R,T,S,W));
"""
