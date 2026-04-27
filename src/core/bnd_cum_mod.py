# bnd_cum_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# This file is part of the IEA-ETSAP TIMES model generator, licensed
# under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
# BND_CUM.MOD set the actual bounds for cumulative variables
# =============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class BndCumMod(GamsClass):
    """Translation unit for bnd_cum.mod."""

    # Instance attributes
    module_name: str = "bnd_cum"
    gams_source: str = "bnd_cum.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.env.stages == "YES":
            self.env.set_local("sw1", "S_")
            self.env.set_local("sw2", f",'1'{self.env.sow}")
        else:
            self.env.set_local("sw1", "")
            self.env.set_local("sw2", "")

        self.tc.enqueue(
            self.step_one,
            arg1=self.arg1,
            sw1=self.env.sw1,
            sw2=self.env.sw2,
            eotime=self.env.eotime,
            var=self.env.var,
            sow=self.env.sow,
            cufscal=self.env.cufscal,
            cucscal=self.env.cucscal,
        )

        if self.env.macro.upper() == "YES":
            return

        self.tc.enqueue(self.step_two, var=self.env.var, sow=self.env.sow)

    def step_one(
        self: BndCumMod,
        arg1: str,
        sw1: str,
        sw2: str,
        eotime: str,
        var: str,
        sow: str,
        cufscal: str,
        cucscal: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Ignore negative bounds; reset any N bounds at specific years
 {sw1}FLO_CUM(R,P,C,YEAR,LL,BD{sw2})$(({sw1}FLO_CUM(R,P,C,YEAR,LL,BD{sw2}) LT 0)${sw1}FLO_CUM(R,P,C,YEAR,LL,BD{sw2})) = 0;
 FLO_CUM(R,P,C,YEAR,'EOH','N') $= FLO_CUM(R,P,C,YEAR,'{eotime}','N');
 FLO_CUM(RPC_CUMFLO(R,P,C,YEAR,LL),'N') = 0;

 {sw1}FLO_CUM(R,P,C,YEAR,LL,BD{sw2})${sw1}FLO_CUM(R,P,C,YEAR,LL,'FX'{sw2}) = {sw1}FLO_CUM(R,P,C,YEAR,LL,'FX'{sw2})$BDNEQ(BD);

* Get modifiers for flexible model horizon
 LOOP((SAMEAS(J,'1'),MIYR_L), OPTION CLEAR=UNCD7; UNCD7(RPC_CUMFLO(R,P,C,YEAR,'{eotime}'),J+(FLO_CUM(R,P,C,YEAR,'EOH','N')-1),'')=YES;
   LOOP(UNCD7(R,P,C,YEAR,LL,JJ,''), FLO_CUM(R,P,C,YEAR,LL,'N') = MIN(0,ABS(MULTI(JJ,MIYR_L))-1)$MULTI(JJ,MIYR_L)));

* Set bounds
 {var}_CUMFLO.LO(R,P,C,YEAR,LL {sow})${sw1}FLO_CUM(R,P,C,YEAR,LL,'LO'{sw2}) = {sw1}FLO_CUM(R,P,C,YEAR,LL,'LO'{sw2})*(1/{cufscal})*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);
 {var}_CUMFLO.UP(R,P,C,YEAR,LL {sow})${sw1}FLO_CUM(R,P,C,YEAR,LL,'UP'{sw2}) = {sw1}FLO_CUM(R,P,C,YEAR,LL,'UP'{sw2})*(1/{cufscal})*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);

* Reset any N bounds at specific years
 COM_CUM(R,{arg1},YEAR,'0',C,'N') $= COM_CUM(R,{arg1},YEAR,'{eotime}',C,'N');
 COM_CUM(RC_CUMCOM(R,{arg1},YEAR,LL,C),'N') = 0;

 {sw1}COM_CUM(R,{arg1},YEAR,LL,C,BD{sw2})${sw1}COM_CUM(R,{arg1},YEAR,LL,C,'FX'{sw2}) = {sw1}COM_CUM(R,{arg1},YEAR,LL,C,'FX'{sw2})$BDNEQ(BD);
 {sw1}COM_CUM(RC_CUMCOM(R,{arg1},LL,YEAR,C),BD{sw2})$(YEARVAL(LL)>MIYR_VL)=EPS; RC_CUMCOM(R,{arg1},LL,YEAR,C)$(YEARVAL(LL)>MIYR_VL)=NO;

* Get modifiers for flexible model horizon
 LOOP((SAMEAS(J,'1'),MIYR_L), OPTION CLEAR=UNCD7; UNCD7(RC_CUMCOM(R,{arg1},YEAR,'{eotime}',C),J+(COM_CUM(R,{arg1},YEAR,'0',C,'N')-1),'')=YES;
   LOOP(UNCD7(R,{arg1},YEAR,LL,C,JJ,''), COM_CUM(R,{arg1},YEAR,LL,C,'N') = MIN(0,ABS(MULTI(JJ,MIYR_L))-1)$MULTI(JJ,MIYR_L)));

* Set bounds
 {sw1}COM_CUM(RC_CUMCOM(R,{arg1},YEAR,LL,C),L('LO'){sw2})$(NOT {sw1}COM_CUM(RC_CUMCOM,L{sw2})) = -INF$SUM((RTC(R,T,C),ANNUAL(S)),MIN(0,COM_BNDPRD(RTC,S,L)$DIAG({arg1},'PRD')+COM_BNDNET(RTC,S,L)$DIAG({arg1},'NET')+1-1));
 {var}_CUMCOM.LO(R,C,{arg1},YEAR,LL {sow})${sw1}COM_CUM(R,{arg1},YEAR,LL,C,'LO'{sw2}) = {sw1}COM_CUM(R,{arg1},YEAR,LL,C,'LO'{sw2})*(1/{cucscal})*(COM_CUM(R,{arg1},YEAR,LL,C,'N')+1);
 {var}_CUMCOM.UP(R,C,{arg1},YEAR,LL {sow})${sw1}COM_CUM(R,{arg1},YEAR,LL,C,'UP'{sw2}) = {sw1}COM_CUM(R,{arg1},YEAR,LL,C,'UP'{sw2})*(1/{cucscal})*(COM_CUM(R,{arg1},YEAR,LL,C,'N')+1);
""",
        )

    def step_two(self: BndCumMod, var: str, sow: str) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
* Set lower bound for combined costs to -INF
 LOOP(COST_GMAP(COSTCAT,COSTAGG,COSTYPE),
   {var}_CUMCST.LO(R,YEAR,ALLYEAR,COSTCAT,CUR {sow})$REG_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR,'UP') = -INF);
 {var}_CUMCST.UP(R,YEAR,ALLYEAR,COSTCAT,CUR {sow}) $= REG_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR,'UP');
 {var}_CUMCST.LO(R,YEAR,ALLYEAR,COSTCAT,CUR {sow}) $= REG_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR,'LO');
 {var}_CUMCST.FX(R,YEAR,ALLYEAR,COSTCAT,CUR {sow}) $= REG_CUMCST(R,YEAR,ALLYEAR,COSTCAT,CUR,'FX');
""",
        )
