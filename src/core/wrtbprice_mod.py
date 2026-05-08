# wrtbprice_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================
# * Saving shadow prices of commodity balances to be used as base prices
# * for elastic demands into gdx files com_bprice.gdx & <RUN_NAME>_DP.dgx
# *==============================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class WrtbpriceMod(GamsClass):
    """Translation unit for wrtbprice.mod."""

    module_name: str = "wrtbprice_mod"
    gams_source: str = "wrtbprice.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  PARAMETER DINV(R,YEAR,CUR) //;
  PARAMETER SOL_BPRICE(REG,ALLYEAR,COM,ALL_TS,CUR) //;
  PARAMETER SOL_ACFR(R,UC_COST,YEAR) //;
  SET ANCAT(UC_COST,ITEM) / COST.(INV, FIX, VAR, DAM), TAX.(INVX, FIXX, VARX) /;
""",
        )

        self.tc.enqueue(
            self.exec_wrtbprice_mod,
            stages=self.env.stages,
            anncost=self.env.anncost,
            gdxpath=self.env.gdxpath,
            run_name=self.env.run_name,
            dam_elast_defined=self.tc.defined("DAM_ELAST"),
            dam_cost_defined=self.tc.defined("DAM_COST"),
        )

    def exec_wrtbprice_mod(
        self: WrtbpriceMod,
        stages: str,
        anncost: str,
        gdxpath: str,
        run_name: str,
        dam_elast_defined: bool,
        dam_cost_defined: bool,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*------------------------------------------------------------------------------
* Undiscounting via matrix inversion currently disabled; using direct method
  DINV(R,T,CUR)$G_RCUR(R,CUR) = 1/COEF_PVT(R,T);

  SOL_BPRICE(R,T,C,S,CUR)$(RCS_COMBAL(R,T,C,S,'LO')$DEM(R,C)) = DINV(R,T,CUR)*EQG_COMBAL.M(R,T,C,S);
  SOL_BPRICE(R,T,C,S,CUR)$(RCS_COMBAL(R,T,C,S,'FX')$DEM(R,C)) = DINV(R,T,CUR)*EQE_COMBAL.M(R,T,C,S);

* Check elastic supply curve requests
{"  TRACKC(RC)$((NOT DAM_BQTY(RC))$DAM_ELAST(RC,'N')) = YES;" if dam_elast_defined else ""}
{"  LOOP((R,T,C,CUR)$DAM_COST(R,T,C,CUR), TRACKC(R,C) = NO);" if dam_cost_defined else ""}
  OPTION CLEAR=DAM_COEF,CLEAR=DAM_TVOC;
  DAM_COEF(RTCS_VARC(R,T,C,S))$TRACKC(R,C) = EQE_COMPRD.M(R,T,C,S)/COEF_PVT(R,T)+EPS;
  DAM_TVOC(RTC(R,T,C),'N')$TRACKC(R,C) = SUM(RTCS_VARC(RTC,S),DAM_COEF(RTC,S)*VAR_COMPRD.L(RTC,S));

* Save also annual cost to expenditure ratios for TIMES CGE calibration
  RB(R,T) = SUM((COM_TS(DEM(R,C),S),RDCUR(R,CUR)),SOL_BPRICE(R,T,C,S,CUR)*COM_FR(R,T,C,S)*COM_PROJ(R,T,C))+1-1;
{"  SOL_ACFR(R,UC_COST,T)$RB(R,T)=SUM(SYSUCMAP(SYSUC,ITEM)$ANCAT(UC_COST,ITEM),REG_ACOST(R,T,SYSUC)) / RB(R,T);" if stages.upper() != "YES" and anncost.upper() == "LEV" else ""}
  OPTION CLEAR=RB,CLEAR=TRACKC;

  EXECUTE_UNLOAD 'com_bprice',sol_bprice,DAM_COEF,DAM_TVOC,SOL_ACFR;
  EXECUTE_UNLOAD '{gdxpath}{run_name}_DP',sol_bprice,DAM_COEF,DAM_TVOC,SOL_ACFR;
*------------------------------------------------------------------------------
""",
        )
