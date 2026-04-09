# mod_vars_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==================================================================*
# * MOD_VARS.EXT EXTENSION VARIABLES
# * called from MAINDRV.MOD
# *==================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class ModVarsAbs(GamsClass):
    """Translation unit for mod_vars.abs."""

    # Instance attributes
    module_name: str = "mod_vars_abs"
    gams_source: str = "mod_vars.abs"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
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
  POSITIVE VARIABLES
  {self.env.var}_COMLV(CLVT,R,YEAR,C,S{self.env.swd})   Commodity levels
  {self.env.var}_BSPRS(R,YEAR,T,P,C,S,L{self.env.swd})  Balancing services //
  {self.env.var}_RLD(R,T,S,ITEM{self.env.swd})          Reserve-defining load levels
  ;

  EQUATIONS
  EQ_BS00(R,T,C,S,ALLSOW)             Overall demands for balancing services
  EQ_BS01(R,YEAR,C,S,ITEM,L,ALLSOW)   Max and Diff over stochastic & determistic demand
  EQ_BS02(R,T,S,ITEM,ALLSOW)          Load levels by process category
  EQ_BS03(R,T,C,S,ALLSOW)             Stochastic demand for balancing services
  EQ_BS04(R,T,C,S,P,ALLSOW)           Deterministic demand for balancing services
  EQ_BS05(R,YEAR,T,P,TSL,L,S,ALLSOW)  Minimum online - offline times
  EQ_BS07(R,YEAR,T,P,S,BD,ALLSOW)     Ramping constraints
  EQ_BS09(R,YEAR,T,P,S,L,ALLSOW)      Capacity margin constraints - positive
  EQ_BS10(R,YEAR,T,P,S,ALLSOW)        Capacity margin constraints - negative
  EQ_BS11(R,YEAR,T,P,C,S,BD,ALLSOW)   Limits for spinning reserve by type
  EQ_BS18(R,YEAR,T,P,S,BD,ALLSOW)     Lower limits for non-spinning reserve by type
  EQ_BS19(R,YEAR,T,P,C,S,BD,ALLSOW)   Upper limits for non-spinning reserve by type
  EQ_BS22(R,YEAR,T,P,S,ALLSOW)        Limit for positive reserve from storage
  EQ_BS23(R,YEAR,T,P,S,ALLSOW)        Limit for negative reserve from storage
  EQ_BS24(R,YEAR,T,P,S,ALLSOW)        Limits for negative reserve from end-use
  EQ_BS25(R,YEAR,T,P,S,ALLSOW)        Limits for positive reserve from end-use
  EQ_BS26(R,T,P,C,S,ALLSOW)           Bounds for process reserves
  EQ_BS27(R,YEAR,T,P,S,ALLSOW)        Maintenance 1
  EQ_BS28(R,YEAR,T,P,S,ALLSOW)        Maintenance 2
  ;
""",
        )
        self.tc.enqueue(
            self.mod_vars_abs_exec,
            var=self.env.var,
            sow=self.env.sow,
        )

        if self.env.obmac.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* Spines macros
$ macro Z_COMLV VAS_COMLV
$ macro Z_BSPRS VAS_BSPRS
""",
            )

    def mod_vars_abs_exec(
        self: ModVarsAbs,
        var: str,
        sow: str,
    ):
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set minimum exogenous demand
  BS_CAPACT(R)$(NOT BS_CAPACT(R)) = MAX(0,SMAX(RP_STD(R,P)$GR_GENMAP(R,P,'SI'),PRC_CAPACT(R,P)));
  BS_CAPACT(R)$(NOT BS_CAPACT(R)) = MAX(0,SMAX(BS_SUPP(RP_STD(R,P)),PRC_CAPACT(R,P)));
  {var}_COMLV.LO('DET',RTCS_VARC(R,T,C,S){sow}) $= BS_RTCS('EXOGEN',R,T,C,S)*BS_CAPACT(R);
  RPT_OPT('RATE','1')$(RPT_OPT('RATE','1')<=0)=SMAX(R,BS_CAPACT(R))$(RPT_OPT('RATE','1')=0);

* Set bounds on reserve flows
  BS_BNDPRS(RTP,C,S,BDNEQ)$=BS_BNDPRS(RTP,C,S,'FX');
  BS_BNDPRS(RTP,C,S,'N')$SUM(BDNEQ$BS_BNDPRS(RTP,C,S,BDNEQ),1) = 1;
  LOOP((L(BDUPX),BD)$(BDSIG(L)*BDSIG(BD)<0),
  {var}_bsprs.LO(r,t,t,p,c,s,l{sow})$(RTP(R,T,P)$BS_COMTS(R,C,S)) $= BS_BNDPRS(R,T,P,C,S,BD);
  {var}_bsprs.UP(r,t,t,p,c,s,l{sow})$(RTP(R,T,P)$BS_COMTS(R,C,S)) $= BS_BNDPRS(R,T,P,C,S,L));
""",
        )
