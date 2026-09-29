# clearsol_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CLEARSOL.stc: Clear solution values
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.eqdeclr_mod import EqdeclrMod
from core.mod_vars_mod import ModVarsMod
from core.utils import apply_sw_notags

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ClearsolStc(GamsClass):
    """Translation unit for clearsol.stc."""

    module_name: str = "clearsol_stc"
    gams_source: str = "clearsol.stc"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc

        if self.arg1 != "":
            apply_sw_notags(env=self.env)

            self.include(ModVarsMod(tc=self.tc, env=self.env))
            self.include(EqdeclrMod(tc=self.tc, env=self.env, arg1=""))

            g.VAR_CUMFLO.setRecords(None)
            g.VAR_CUMCOM.setRecords(None)
            g.VAR_CUMCST.setRecords(None)
            g.VAR_ACT.setRecords(None)
            g.VAR_FLO.setRecords(None)
            g.VAR_IRE.setRecords(None)
            g.VAR_SIN.setRecords(None)
            g.VAR_SOUT.setRecords(None)
            g.VAR_COMNET.setRecords(None)
            g.VAR_COMPRD.setRecords(None)
            g.VAR_ELAST.setRecords(None)
            g.VAR_SCAP.setRecords(None)
            g.VAR_UPS.setRecords(None)
            g.VAR_UPT.setRecords(None)
            g.VAR_UDP.setRecords(None)
            g.VAR_UC.setRecords(None)
            if self.arg1.upper() == "DEF":
                return

        self.tc.enqueue(
            self.exec1,
            var_dam_defined=self.tc.defined(f"{self.env.var}_DAM"),
            var_scap_defined=self.tc.defined(f"{self.env.var}_SCAP"),
        )

    def exec1(self: ClearsolStc, var_dam_defined: bool, var_scap_defined: bool) -> None:
        clearsol_stc(self.tc, var_dam_defined, var_scap_defined)


# arg1 is only used in the definition part, if arg1 is empty only the function is executed
def clearsol_stc(
    g: TimesModelClass,
    var_dam_defined: bool,
    var_scap_defined: bool,
    inline: bool = False,
) -> str | None:
    # A module whose execution part can be $BATINCLUDEd inside GAMS control flow cannot be translated to
    # GAMSPy statements until the enclosing loop is translated too. Hence, the inline is needed for
    # rptmain_stc.py and (via the raw GAMS variant of pextlevs.stc) solve_stp.py. Inline part can be
    # removed once they are translated.
    if inline:
        return rf"""
  IF(YES,DISPLAY 'Solution store cleared';
  OPTION CLEAR=VAR_ACT;
  OPTION CLEAR=VAR_BLND;
  OPTION CLEAR=VAR_COMNET;
  OPTION CLEAR=VAR_COMPRD;
  OPTION CLEAR=VAR_IRE;
  OPTION CLEAR=VAR_ELAST;
  OPTION CLEAR=VAR_FLO;
  OPTION CLEAR=VAR_SIN,CLEAR=VAR_SOUT;
  OPTION CLEAR=VAR_CAP,CLEAR=VAR_NCAP;
  OPTION CLEAR=VAR_UC,CLEAR=VAR_UCR;
  OPTION CLEAR=VAR_UCT,CLEAR=VAR_UCRT;
  OPTION CLEAR=VAR_UCTS,CLEAR=VAR_UCRTS;
  OPTION CLEAR=VAR_UPS,CLEAR=VAR_UPT,CLEAR=VAR_UDP;
  OPTION CLEAR=VAR_OBJ,CLEAR=VAR_OBJELS;
* Delicate bounds
  VAR_CUMCOM.L(R,C,COM_VAR,ALLYEAR,YEAR)=0;
  VAR_CUMFLO.L(R,P,C,ALLYEAR,YEAR)=0;
{"  VAR_DAM.L(R,T,C,BD,J)=0;" if var_dam_defined else ""}
{"  VAR_SCAP.L(R,YEAR,T,P)=0;" if var_scap_defined else ""}
* Equations
  OPTION CLEAR=EQE_COMBAL,CLEAR=EQG_COMBAL,CLEAR=EQE_COMPRD;
  OPTION CLEAR=EQ_PEAK,CLEAR=EQ_IRE,CLEAR=EQE_CPT;
  OPTION CLEAR=EQE_FLOMRK,CLEAR=EQG_FLOMRK,CLEAR=EQL_FLOMRK;
  OPTION CLEAR=EQE_ACTBND,CLEAR=EQG_ACTBND,CLEAR=EQL_ACTBND;
  );
"""

    print("Solution store cleared")
    r, c, comvar, allyear, year, p = g.r, g.c, g.comvar, g.allyear, g.year, g.p
    t, j, bd = g.t, g.j, g.bd

    g.VAR_ACT.setRecords(None)
    g.VAR_BLND.setRecords(None)
    g.VAR_COMNET.setRecords(None)
    g.VAR_COMPRD.setRecords(None)
    g.VAR_IRE.setRecords(None)
    g.VAR_ELAST.setRecords(None)
    g.VAR_FLO.setRecords(None)
    g.VAR_SIN.setRecords(None)
    g.VAR_SOUT.setRecords(None)
    g.VAR_CAP.setRecords(None)
    g.VAR_NCAP.setRecords(None)
    g.VAR_UC.setRecords(None)
    g.VAR_UCR.setRecords(None)
    g.VAR_UCT.setRecords(None)
    g.VAR_UCRT.setRecords(None)
    g.VAR_UCTS.setRecords(None)
    g.VAR_UCRTS.setRecords(None)
    g.VAR_UPS.setRecords(None)
    g.VAR_UPT.setRecords(None)
    g.VAR_UDP.setRecords(None)
    g.VAR_OBJ.setRecords(None)
    g.VAR_OBJELS.setRecords(None)
    # Delicate bounds
    g.VAR_CUMCOM.l[r, c, comvar, allyear, year] = 0
    g.VAR_CUMFLO.l[r, p, c, allyear, year] = 0

    if var_dam_defined:
        g.VAR_DAM.l[r, t, c, bd, j] = 0

    if var_scap_defined:
        g.VAR_SCAP.l[r, year, t, p] = 0

    # Equations
    g.eqe_combal.setRecords(None)
    g.eqg_combal.setRecords(None)
    g.eqe_comprd.setRecords(None)
    g.eq_peak.setRecords(None)
    g.eq_ire.setRecords(None)
    g.eqe_cpt.setRecords(None)
    g.eqe_flomrk.setRecords(None)
    g.eqg_flomrk.setRecords(None)
    g.eql_flomrk.setRecords(None)
    g.eqe_actbnd.setRecords(None)
    g.eqg_actbnd.setRecords(None)
    g.eql_actbnd.setRecords(None)

    return None
