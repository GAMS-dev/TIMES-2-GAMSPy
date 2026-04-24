# ppm_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PPM_ext.abs oversees preliminary preprocessing activity needed by CLI
# *   arg1 - mod or v# for the source code to be used
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillparm_gms import FillparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtCli(GamsClass):
    """Translation unit for ppm_ext.cli."""

    # Instance attributes
    module_name: str = "ppm_ext_cli"
    gams_source: str = "ppm_ext.cli"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.comp1()
        self.tc.enqueue(self.user_defined_emissions)

        # * Interpolation/extrapolation
        self.env.set_scoped("reset", "0")
        self.include(
            FillparmGms(
                self.tc,
                self.env,
                arg1="CM_COUPLE",
                arg2="CG1",
                arg3="CG,CM_Q",
                arg4=",'0','0','0','0'",
                arg5="T",
                arg6="YES",
                arg7=">=0",
            )
        )

        self.tc.enqueue(self.statistic_mappings)

    def comp1(self: PpmExtCli):
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
* Additional declarations
  SET CM_USUBS(CM_ITEM);
  SET CM_COUPMAP(CM_ITEM,CM_ITEM,CM_Q);
  SET CM_REBOX(CM_Q,CM_Q) / CM-ATM.ATM, CM-UP.UP, CM-LO.LO /;
""",
        )

    def user_defined_emissions(self: PpmExtCli):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Add user-defined emissions
  CM_GHGMAP(R,COM,C)$(NOT CM_GHGMAP(R,COM,C)) $= IRE_CCVT(R,COM,R,C);
  CM_USUBS(CM_ITEM)$SUM(RC(R,COM)$CM_GHGMAP(R,COM,CM_ITEM),1) = CM_PPM(CM_ITEM);
  OPTION CLEAR=UNCD1; UNCD1(CM_USUBS) = CM_HISTS(CM_USUBS);
  CM_HISTS(CM_USUBS) = YES;
  CM_EMIS(CM_USUBS) = YES;
* Prepare coupled agents
  CM_COUPLE(CG,LL,CM_ITEM,'ATM') = 0;
  UNCD7(CG,LL--ORD(LL),CM_ITEM,LIM(CM_Q),'','','')$CM_COUPLE(CG,LL,CM_ITEM,CM_Q) = YES;
  LOOP(UNCD7(CG,LL,CM_ITEM,L('N'),'','',''),
    IF(CM_EMIS(CG), CM_COUPLE(CG,YEAR,CM_ITEM,'ATM')$=CM_COUPLE(CG,YEAR,CM_ITEM,L);
    ELSE LOOP((RC(R,C(CG)),CM_VAR)$(CM_GHGMAP(R,C,CM_VAR)$CM_EMIS(CM_VAR)),
      CM_COUPLE(CM_VAR,YEAR,CM_ITEM,'ATM') $= CM_COUPLE(CG,YEAR,CM_ITEM,L);
      CM_COUPLE(CM_VAR,YEAR,CM_ITEM,CM_Q) $= CM_COUPLE(CG,YEAR,CM_ITEM,CM_Q))));
  OPTION CM_COUPMAP <= CM_COUPLE;
  CM_COUPLE(CG,LL,CM_ITEM,'N') = 0;
  CM_COUPLE(CG,LL,CM_ITEM,CM_Q)$(NOT CM_COUPMAP(CG,CM_ITEM,'ATM')) = 0;
  OPTION CM_USUBS < CM_COUPMAP;
  LOOP(CM_USUBS(CM_ITEM),
    CM_PPM(CM_ITEM)$(NOT CM_PPM(CM_ITEM)) = 1;
    CM_STAT0(CM_ITEM,'LIFE')$(NOT CM_STAT0(CM_ITEM,'LIFE'))=1;
    IF(NOT (UNCD1(CM_ITEM) OR CM_DECAY(CM_ITEM,'ATM')),CM_DECAY(CM_ITEM,'ATM') = 1;
       CM_COUPLE(CM_VAR,T,CM_ITEM,'FX')$CM_COUPMAP(CM_VAR,CM_ITEM,'ATM') = 1);
    CM_EMIS(CM_ITEM) = YES);
""",
        )

    def statistic_mappings(self: PpmExtCli):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Statistics mappings
  CM_STATS(CM_HISTS,LL,'ATM')    $= CM_STATS(CM_HISTS,LL,'N');
  CM_STATS('FORCING',LL,CM_BOX)  $= CM_STATS('DELTA',LL,CM_BOX);
  CM_STAT0(CM_VAR,'LIFE')$((CM_DECAY(CM_VAR,'UP')>0)$CM_DECAY(CM_VAR,'UP'))=1/CM_DECAY(CM_VAR,'UP');

* Add missing forcings if functions defined
  OPTION CLEAR=UNCD1, CM_USUBS < CM_LINFOR;
  UNCD1(CM_USUBS) = YES;
  OPTION CM_USUBS < CM_FORCMAP;
  CM_USUBS(CM_EMIS) = NOT CM_USUBS(CM_EMIS);
  CM_USUBS(CM_USUBS) = UNCD1(CM_USUBS);
  CM_USUBS('CO2-GTC') = NO;
  CM_FORCMAP(CM_USUBS,CM_USUBS) = YES;
  CM_OFOR(CM_USUBS) = YES;
""",
        )
