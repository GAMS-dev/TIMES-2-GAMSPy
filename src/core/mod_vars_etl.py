# mod_vars_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_VARS.ETL endogenous technology change variables
# *=============================================================================*
# * args1 - source code extension
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsEtl(GamsClass):
    """Translation unit for mod_vars.etl."""

    # Instance attributes
    module_name: str = "mod_vars_etl"
    gams_source: str = "mod_vars.etl"

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
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
*  VARIABLES
*-----------------------------------------------------------------------------
POSITIVE VARIABLES
  {self.env.var}_LAMBD(R,ALLYEAR, PRC, KP {self.env.swd})
  {self.env.var}_CCAP(R,ALLYEAR,PRC {self.env.swd})
  {self.env.var}_CCOST(R,ALLYEAR,PRC {self.env.swd})
  {self.env.var}_IC(R,ALLYEAR,PRC {self.env.swd})

BINARY VARIABLES
  {self.env.var}_DELTA(R,ALLYEAR,PRC,KP {self.env.swd})

*-----------------------------------------------------------------------------
*  EQUATIONS
*-----------------------------------------------------------------------------
EQUATIONS
  {self.env.eq}_CUINV(R,ALLYEAR, PRC {self.env.swtd})     Cumulative Capacity Definition
  {self.env.eq}_CC(R,ALLYEAR, PRC {self.env.swtd})        Cumulative Capacity Interpolation
  {self.env.eq}_DEL(R,ALLYEAR, PRC {self.env.swtd})       Delta to 1
  {self.env.eq}_COS(R,ALLYEAR, PRC {self.env.swtd})       Cumulative Cost
  {self.env.eq}_LA1(R,ALLYEAR, PRC, KP {self.env.swtd})   Constraints on lambda 1
  {self.env.eq}_LA2(R,ALLYEAR, PRC, KP {self.env.swtd})   Constraints on lambda 2
  {self.env.eq}_EXPE1(R,ALLYEAR, PRC, KP {self.env.swtd}) Experience grows 1
  {self.env.eq}_EXPE2(R,ALLYEAR, PRC, KP {self.env.swtd}) Experience grows 2
  {self.env.eq}_IC1(R,ALLYEAR, PRC {self.env.swtd})       Investments tech. change 1st period
  {self.env.eq}_IC2(R,ALLYEAR, PRC {self.env.swtd})       Investments tech. change other periods
* cluster
  {self.env.eq}_CLU(R,ALLYEAR, PRC {self.env.swtd})       Cluster
  {self.env.eq}_MRCLU(R,ALLYEAR, PRC {self.env.swtd})     Multi-regional Cluster
;
""",
        )
