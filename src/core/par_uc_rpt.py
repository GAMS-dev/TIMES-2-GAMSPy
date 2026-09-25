# par_uc_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *====================================================================
# * Par_uc.rpt : reporting parameters for UCs (no STAGES/SENSIS)
# * arg1 - parameter suffix
# * arg2 - equation prefix
# *--------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Loop, Parameter, sparse

from core.base_class import GamsClass

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def declare_par_uc_rpt_params(g: TimesModelClass) -> None:
    """Declare PAR_RTUS/PAR_URTS immediately (init phase).

    PAR_RTUS/PAR_URTS are declarative statements -- in real GAMS they are part
    of the single compile pass and exist regardless of when %BATINCLUDE
    par_uc.rpt happens to be lexically reached. Callers that embed
    par_uc_rpt()'s output in "run"-phase code must call this once themselves
    beforehand (rather than letting the declaration ride along with the rest
    of the block).
    """
    if g.par_rtus is None:
        m = g.container
        r, year, ucn, s = g.r, g.year, g.ucn, g.s
        g.par_rtus = Parameter(m, name="PAR_RTUS", domain=[r, year, ucn, s])
        g.par_urts = Parameter(m, name="PAR_URTS", domain=[ucn, r, year, s])


@dataclass
class ParUcRptConfig:
    """Strongly typed data contract for par_uc.rpt."""

    # %1 - parameter suffix
    arg1: Literal["", "SM", "FXM", "LOM", "UPM"] = ""
    # %2 - equation prefix
    arg2: Literal["", "EQE", "EQG", "EQL"] = ""
    # %3 - prefix on the PAR_UC%1 symbol name (e.g. "S" for rptlite.rpt's
    #      STAGES variant, giving SPAR_UCSM/SPAR_UCSL)
    arg3: Literal["", "S"] = ""
    # %4 - extra leading domain element ahead of UC_N (e.g. the SOW alias
    #      that variant reports on)
    arg4: tuple[Alias | Set | Literal["1"], ...] = ()


class ParUcRpt(GamsClass):
    """Translation unit for par_uc.rpt."""

    # Instance attributes
    module_name: str = "par_uc_rpt"
    gams_source: str = "par_uc.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: ParUcRptConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        declare_par_uc_rpt_params(self.tc)
        self.tc.enqueue(self.exec_par_uc_rpt, config=self.config)

    def exec_par_uc_rpt(self: ParUcRpt, config: ParUcRptConfig) -> None:
        arg3 = config.arg3
        arg4 = config.arg4
        if arg3 or arg4:
            # rptlite.rpt is the only caller that ever passes a non-empty
            # arg3/arg4 (its STAGES variant reporting into
            # S{arg1}PAR_UC{arg2} with an extra leading SOW-like dimension),
            # and rptlite_rpt.py hasn't been translated to GAMSPy yet -- so
            # there is no real caller to derive/verify the native domain
            # threading against.
            raise NotImplementedError(
                "par_uc.rpt: a non-empty arg3/arg4 is only reachable through "
                "rptlite.rpt's STAGES variant, and rptlite_rpt.py is not yet "
                "translated to GAMSPy."
            )
        par_uc_rpt_GP(self.tc, config)


def par_uc_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
) -> str:
    return rf"""
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE','NONE','NONE') $= {arg2}_UC.M(UC_N);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,'NONE')      $= {arg2}_UCT.M(UC_N,T);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,S)           $= {arg2}_UCTS.M(UC_N,T,S);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,'NONE')      $= {arg2}_UCSU.M(UC_N,T);
  {arg3}PAR_UC{arg1}({arg4}UC_N,'NONE',T,S)           $= {arg2}_UCSUS.M(UC_N,T,S);
* Handle shuffled indexes
  PAR_RTUS(R,'0',UC_N,ANNUAL)             $= {arg2}_UCR.M(R,UC_N);
  PAR_RTUS(R,T,UC_N,ANNUAL)               $= {arg2}_UCRT.M(R,T,UC_N);
  PAR_RTUS(R,T,UC_N,ANNUAL)               $= {arg2}_UCRSU.M(R,T,UC_N);
  OPTION PAR_URTS<PAR_RTUS,CLEAR=PAR_RTUS;
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,'NONE','NONE')      $= PAR_URTS(UC_N,R,'0','ANNUAL');
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,T,'NONE')           $= PAR_URTS(UC_N,R, T, 'ANNUAL')*(1/COEF_PVT(R,T));
  PAR_RTUS(R,T,UC_N,S)                    $= {arg2}_UCRTS.M(R,T,UC_N,S);
  PAR_RTUS(R,T,UC_N,S)                    $= {arg2}_UCRSUS.M(R,T,UC_N,S);
  LOOP(TSL,PAR_RTUS(R,T,UC_N,S)           $= {arg2}_UCRS.M(R,T,UC_N,TSL,S));
  OPTION PAR_URTS<PAR_RTUS,CLEAR=PAR_RTUS;
  {arg3}PAR_UC{arg1}({arg4}UC_N,R,T,S)                $= PAR_URTS(UC_N,R,T,S)*(1/COEF_PVT(R,T));
  OPTION CLEAR=PAR_URTS;

"""


def par_uc_rpt_GP(g: TimesModelClass, config: ParUcRptConfig) -> None:
    """Native variant of :func:`par_uc_rpt`.

    ``config.arg3``/``config.arg4`` mirror the raw GAMS ``%3``/``%4`` macros:
    ``arg3`` prefixes the ``PAR_UC{arg1}`` symbol name (e.g. ``"S"`` for
    rptlite.rpt's STAGES variant, giving ``SPAR_UCSM``/``SPAR_UCSL``) and
    ``arg4`` is an extra leading domain element prepended ahead of ``UC_N``
    (e.g. the SOW alias that variant reports on). Every currently-reachable
    caller (rptmain.rpt, rptmain.tm, rpt_ext.mlf) passes neither, so callers
    should pass the defaults; ``ParUcRpt`` raises ``NotImplementedError``
    rather than calling this with a non-empty arg3/arg4, since
    rptlite_rpt.py (the only caller that needs them) is not yet translated
    to GAMSPy.
    """
    arg1 = config.arg1
    arg2 = config.arg2
    arg3 = config.arg3
    arg4 = config.arg4
    r, t, s, ucn, tsl, annual, coef_pvt = (
        g.r,
        g.t,
        g.s,
        g.ucn,
        g.tsl,
        g.Annual,
        g.coef_pvt,
    )
    par_uc = g.get_parameter(name=f"{arg3}PAR_UC{arg1}")
    eq_uc = g.get_equation(name=f"{arg2}_UC")
    eq_uct = g.get_equation(name=f"{arg2}_UCT")
    eq_ucts = g.get_equation(name=f"{arg2}_UCTS")
    eq_ucsu = g.get_equation(name=f"{arg2}_UCSU")
    eq_ucsus = g.get_equation(name=f"{arg2}_UCSUS")
    eq_ucr = g.get_equation(name=f"{arg2}_UCR")
    eq_ucrt = g.get_equation(name=f"{arg2}_UCRT")
    eq_ucrsu = g.get_equation(name=f"{arg2}_UCRSU")
    eq_ucrts = g.get_equation(name=f"{arg2}_UCRTS")
    eq_ucrsus = g.get_equation(name=f"{arg2}_UCRSUS")
    eq_ucrs = g.get_equation(name=f"{arg2}_UCRS")

    par_uc[(*arg4, ucn, "NONE", "NONE", "NONE")] = sparse(eq_uc.m[ucn])
    par_uc[(*arg4, ucn, "NONE", t, "NONE")] = sparse(eq_uct.m[ucn, t])
    par_uc[(*arg4, ucn, "NONE", t, s)] = sparse(eq_ucts.m[ucn, t, s])
    par_uc[(*arg4, ucn, "NONE", t, "NONE")] = sparse(eq_ucsu.m[ucn, t])
    par_uc[(*arg4, ucn, "NONE", t, s)] = sparse(eq_ucsus.m[ucn, t, s])

    # Handle shuffled indexes
    par_rtus, par_urts, year = g.par_rtus, g.par_urts, g.year
    par_rtus[r, "0", ucn, annual] = sparse(eq_ucr.m[r, ucn])
    par_rtus[r, t, ucn, annual] = sparse(eq_ucrt.m[r, t, ucn])
    par_rtus[r, t, ucn, annual] = sparse(eq_ucrsu.m[r, t, ucn])
    par_urts[ucn, r, year, s] = par_rtus[r, year, ucn, s]
    par_rtus.setRecords(None)
    par_uc[(*arg4, ucn, r, "NONE", "NONE")] = sparse(par_urts[ucn, r, "0", "ANNUAL"])
    par_uc[(*arg4, ucn, r, t, "NONE")] = sparse(
        par_urts[ucn, r, t, "ANNUAL"] * (1 / coef_pvt[r, t])
    )
    par_rtus[r, t, ucn, s] = sparse(eq_ucrts.m[r, t, ucn, s])
    par_rtus[r, t, ucn, s] = sparse(eq_ucrsus.m[r, t, ucn, s])
    with Loop(tsl):
        par_rtus[r, t, ucn, s] = sparse(eq_ucrs.m[r, t, ucn, tsl, s])
    par_urts[ucn, r, year, s] = par_rtus[r, year, ucn, s]
    par_rtus.setRecords(None)
    par_uc[(*arg4, ucn, r, t, s)] = sparse(
        par_urts[ucn, r, t, s] * (1 / coef_pvt[r, t])
    )
    par_urts.setRecords(None)
