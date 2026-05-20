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
from typing import TYPE_CHECKING

from core.clearsol_stc import clearsol_stc

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PextlevsStc(GamsClass):
    """Translation unit for pextlevs.stc"""

    # Instance attributes
    module_name: str = "pextlevs_stc"
    gams_source: str = "pextlevs.stc"

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
        self.tc.enqueue(
            self.exec_pextlevs_stc,
            arg1=self.arg1,
            arg2=self.arg2,
            eq=self.env.eq,
            var=self.env.var,
            timesed=self.env.timesed,
            var_dam_defined=self.tc.defined(f"{self.env.var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
        )

    def exec_pextlevs_stc(
        self: PextlevsStc,
        arg1: str,
        arg2: str,
        eq: str,
        var: str,
        timesed: str,
        var_dam_defined: bool,
        var_scap_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=pextlevs_stc(
                arg1=arg1,
                arg2=arg2,
                eq=eq,
                var=var,
                timesed=timesed,
                var_dam_defined=var_dam_defined,
                var_scap_defined=var_scap_defined,
            ),
        )


def pextlevs_stc(
    *,
    arg1: str,
    arg2: str,
    eq: str,
    var: str,
    timesed: str,
    var_dam_defined: bool,
    var_scap_defined: bool,
) -> str:
    return rf"""
{clearsol_stc(var_dam_defined=var_dam_defined, var_scap_defined=var_scap_defined)}
* Get the sum of weighted Marginals
  EQG_COMBAL.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}G_COMBAL.M(R,T,C,S,T,W));
  EQE_COMBAL.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}E_COMBAL.M(R,T,C,S,T,W));
  EQE_COMPRD.M(R,T{arg2},C,S) $= SUM(SW_T(T,W), {eq}E_COMPRD.M(R,T,C,S,T,W));
  EQ_PEAK.M(R,T{arg2},CG,S)   $= SUM(SW_T(T,W), {eq}_PEAK.M(R,T,CG,S,T,W));
  EQ_IRE.M(R,T{arg2},P,C,IE,S) $= SUM(SW_T(T,W), {eq}_IRE.M(R,T,P,C,IE,S,T,W));
  EQE_CPT.M(R,T{arg2},P)      $= SUM(SW_T(T,{arg1}),  {eq}E_CPT.M(R,T,P,T,{arg1}));
  EQN_UCRTP.M(UC_N,R,T{arg2},P,UC_GRPTYPE,BD('FX'))  $= SUM(SW_T(T,W), {eq}E_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W));
  EQN_UCRTP.M(UC_N,R,T{arg2},P,UC_GRPTYPE,BDNEQ(BD)) $= SUM(SW_T(T,W), {eq}N_UCRTP.M(UC_N,R,T,P,UC_GRPTYPE,BD,T,W));

* Get the expected Levels
  VAR_ACT.L(R,V,T{arg2},P,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_ACT.L(R,V,T,P,S,W));
  VAR_BLND.L(R,T{arg2},COM,C) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_BLND.L(R,T,COM,C,W));
  VAR_COMNET.L(R,T{arg2},COM,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_COMNET.L(R,T,COM,S,W));
  VAR_COMPRD.L(R,T{arg2},COM,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_COMPRD.L(R,T,COM,S,W));
  VAR_IRE.L(R,V,T{arg2},P,C,S,IE) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_IRE.L(R,V,T,P,C,S,IE,W));
  VAR_ELAST.L(R,T{arg2},C,S,J,BD) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_ELAST.L(R,T,C,S,J,BD,W));
  VAR_FLO.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_FLO.L(R,V,T,P,C,S,W));
  VAR_SIN.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_SIN.L(R,V,T,P,C,S,W));
  VAR_SOUT.L(R,V,T{arg2},P,C,S) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_SOUT.L(R,V,T,P,C,S,W));
  VAR_UPS.L(R,V,T{arg2},P,S,L) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_UPS.L(R,V,T,P,S,L,W));
  VAR_CUMCOM.L(R,C,COM_VAR,YEAR,LL)$RC_CUMCOM(R,COM_VAR,YEAR,LL,C) $= SUM(W, SW_PROB(W)*{var}_CUMCOM.L(R,C,COM_VAR,YEAR,LL,W));
  VAR_CUMFLO.L(RPC,YEAR,LL)$RPC_CUMFLO(RPC,YEAR,LL) $= SUM(W, SW_PROB(W)*{var}_CUMFLO.L(RPC,YEAR,LL,W));
{f"VAR_DAM.L(R,T{arg2},C,BD,J) $= SUM(SW_T(T,W), SW_TPROB(T,W)*{var}_DAM.L(R,T,C,BD,J,W));" if var_dam_defined else ""}
{f"VAR_OBJELS.L(R,BD,CUR)  $= SUM(W, SW_PROB(W)*{var}_OBJELS.L(R,BD,CUR,W));" if timesed == "YES" else ""}
  VAR_CAP.L(R,T{arg2},P)  $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_CAP.L(R,T,P,{arg1}));
  VAR_NCAP.L(R,T{arg2},P) $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_NCAP.L(R,T,P,{arg1}));
  VAR_SCAP.L(R,V,T{arg2},P) $= SUM(SW_T(T,SOW), SW_TPROB(T,SOW)*{var}_SCAP.L(R,V,T,P,{arg1}));

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
