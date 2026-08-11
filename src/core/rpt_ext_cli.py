# rpt_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * RPT_EXT.cli - Extension for Climate Module: Stochastic report
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------
# * Calculate Reporting parameters for Climate Module

# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass
from core.rpt_par_cli import rpt_par_cli
from core.utils import apply_sw_notags, apply_sw_tags

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtCli(GamsClass):
    """Translation unit for rpt_ext.cli."""

    # Instance attributes
    module_name: str = "rpt_ext_cli"
    gams_source: str = "rpt_ext.cli"

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
        self.compile()

    def compile(self) -> None:
        g = self.tc

        if self.env.sensis.upper() == "YES":
            return

        apply_sw_notags(env=self.env)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
EQUATIONS
  {self.env.eq}_CLITOT(CM_ITEM,T,LL {self.env.swd}) 'Balances for the total emissions or forcing'
  {self.env.eq}_CLIMAX(ALLYEAR,CM_ITEM {self.env.swd}) 'Constraint for maximum climate quantities'
;

VARIABLES
  {self.env.var}_CLITOT(CM_ITEM,LL {self.env.swd}) 'Total emissions or forcing by milestone year'
POSITIVE VARIABLES
  {self.env.var}_CLIBOX(CM_ITEM,CM_BOX,LL{self.env.swd}) 'Quantities in the climate reservoirs';
""",
        )

        if self.env.stages == "YES":
            apply_sw_tags(env=self.env, g=g)
            self.env.set_scoped("swsw", "SW_TSW(SOW,T,WW),")
            self.env.set_scoped("swsw_GP", (g.SwTsw[g.Sow, g.t, g.ww],))

        if self.env.scum == "1":
            self.env.set_scoped("swsw", "SW_T(T,WW),")
            self.env.set_scoped("swsw_GP", (g.SwT[g.t, g.ww],))
            self.env.set_scoped("scum", "*SW_TPROB(T,WW)")

        self.add_records_to_universe_item(
            ["FORC+CO2", "FORC+TOT", "DELTA+ATM", "DELTA+LO"]
        )
        self.tc.enqueue(
            self.exec_loop,
            self.env.stages,
            self.env.swsw,
            self.env.var,
            self.env.swd,
            self.env.scum,
            self.env.eq,
        )

    def exec_loop(
        self: RptExtCli,
        stages: str,
        swsw: str,
        var: str,
        swd: str,
        scum: str,
        eq: str,
    ) -> None:
        # * Results for each SOW
        code_str = "LOOP(SOW," if stages != "YES" else "LOOP(AUXSOW(SOW)$SW_PROB(SOW),"
        # * Clear results from previous SOW
        if stages == "YES":
            code_str += rf"""
   OPTION CLEAR=VAR_CLITOT,CLEAR=VAR_CLIBOX;
   OPTION CLEAR=EQ_CLITOT, CLEAR=EQ_CLIMAX;
   LOOP(SUPERYR(T,LL)$CM_LED(LL),
    VAR_CLITOT.L(CM_VAR,LL) $= SUM({swsw} {var}_CLITOT.L(CM_VAR,LL{swd}){scum});
    VAR_CLIBOX.L(CM_VAR,CM_BOX,LL) $= SUM({swsw} {var}_CLIBOX.L(CM_VAR,CM_BOX,LL{swd}){scum});
{f"VAR_CLIBOX.L(CM_VAR,CM_BOX,LL) $= {var}_CLIBOX.L(CM_VAR,CM_BOX,LL,SOW);" if f"{stages}{scum}" == "YES" else ""}
    EQ_CLIMAX.M(LL,CM_VAR)  $= SUM({swsw} {eq}_CLIMAX.M(LL,CM_VAR{swd})*SW_UNPB(T,WW)));
   EQ_CLITOT.M(CM_VAR,T,T)  $= SUM({swsw} {eq}_CLITOT.M(CM_VAR,T,T{swd})*SW_UNPB(T,WW));
"""

        code_str += rpt_par_cli()
        code_str += """
  );
IF(CARD(SOW)=1,DISPLAY CM_RESULT,CM_MAXC_M; ELSE DISPLAY CM_SRESULT,CM_SMAXC_M);
"""
        if stages == "YES":
            code_str += rf"""
* Expected marginals
  LOOP(SUPERYR(T,LL)$CM_LED(LL),
    EQ_CLIMAX.M(LL,CM_VAR)  $= SUM(SW_T(T,W),{eq}_CLIMAX.M(LL,CM_VAR,W));
    VAR_CLITOT.L(CM_VAR,LL) $= SUM(SW_T(T,W),SW_TPROB(T,W)*{var}_CLITOT.L(CM_VAR,LL,W));
    VAR_CLIBOX.L(CM_VAR,CM_BOX,LL) $= SUM(SW_T(T,W),SW_TPROB(T,W)*{var}_CLIBOX.L(CM_VAR,CM_BOX,LL,W)));

"""

        self.tc.add_gams_code(module=self, phase="run", code=code_str)
