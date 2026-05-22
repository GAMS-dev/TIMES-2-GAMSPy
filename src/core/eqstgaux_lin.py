# eqstgaux_lin.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQSTGAUX auxiliary commodities for storage
# *=============================================================================*
# *AL Questions/Comments:
# * Assumption is that all auxiliary flows are at PRC_TS level; NST primary flows can be also above
# *-----------------------------------------------------------------------------*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqstgauxLin(GamsClass):
    """Translation unit for eqstgaux.lin."""

    # Instance attributes
    module_name: str = "eqstgaux_lin"
    gams_source: str = "eqstgaux.lin"

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
*$ONLISTING


  {self.env.eq}_STGAUX(RTP_VINTYR({self.env.r_v_t},P),C,RTS(S){self.env.swt})$((RPCS_VAR(R,P,C,S)*(NOT RPC_STG(R,P,C)+RPC_EMIS(R,P,C)))$RP_STG(R,P))..

* Auxiliary flow variable
    {self.env.var}_FLO(R,V,T,P,C,S {self.env.sow})

    =E=

* flow depends on storage level in period T
    SUM(ANNUAL(SL),PRC_ACTFLO(R,V,P,C) *
        (
         SUM(PRC_TS(R,P,TS)$TS_MAP(R,TS,S),{self.env.var}_ACT(R,V,T,P,TS {self.env.sow})/RS_STGPRD(R,TS)) * G_YRFR(R,S) -
* subtract in- and output flows to/from storage during latter half of milestone year
         SUM(TOP(PRC_STGIPS(R,P,COM),IO), 0.5 *
           ({self.env.var}_SIN(R,V,T,P,COM,SL{self.env.sow})$IPS(IO) - {self.env.var}_SOUT(R,V,T,P,COM,SL{self.env.sow})$(NOT IPS(IO))) / PRC_ACTFLO(R,V,P,COM) *
* storage losses (assume that Inflows and outflows occur at the mid-point of each year)
           ((1-STG_LOSS(R,V,P,SL))**0.5))
* For IPS, MID storage level is (1-LOSS)**(0.5) higher
        ) * (1+((1-STG_LOSS(R,V,P,SL))**(-0.5)-1)$PRC_MAP(R,'STK',P))) +

* flow depends on storage in- or outflow in period T
    SUM((COM_GMAP(R,CG,COM),TOP(RPC_STG(R,P,COM),'IN'),RPCS_VAR(R,P,COM,TS))$COEF_PTRAN(R,V,P,CG,COM,C,TS),
        ({self.env.var}_SIN(R,V,T,P,COM,TS {self.env.sow}) * COEF_PTRAN(R,V,P,CG,COM,C,TS))$((NOT PRC_MAP(R,'NST',P))+PRC_NSTTS(R,P,TS)) *
         RS_FR(R,S,TS) * (1+RTCS_FR(R,T,C,S,TS))) +
    SUM((COM_GMAP(R,CG,C),TOP(RPC_STG(R,P,COM),'OUT'),RPCS_VAR(R,P,COM,TS))$COEF_PTRAN(R,V,P,CG,C,COM,S),
        ({self.env.var}_SOUT(R,V,T,P,COM,TS {self.env.sow}) * (1/COEF_PTRAN(R,V,P,CG,C,COM,S)))$(PRC_NSTTS(R,P,TS) EQV RPC_STGN(R,P,COM,'OUT')) *
         RS_FR(R,S,TS) * (1+RTCS_FR(R,T,C,S,TS)))

;

$OFFLISTING
""",
        )
