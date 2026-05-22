# pp_chp_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------
# * Convert capacity related CHP data from electricity to input commodity
# *-----------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpChpIer(GamsClass):
    """Translation unit for pp_chp.ier."""

    # Instance attributes
    module_name: str = "pp_chp_ier"
    gams_source: str = "pp_chp.ier"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str = ""):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(self.electricity_commodity_pg)
        self.tc.enqueue(self.commodity_group)
        self.tc.enqueue(self.calculate_electricity_heat_ratio)
        self.tc.enqueue(self.convert_input_capacity)
        self.tc.enqueue(self.extrapolate_past_years)

    def electricity_commodity_pg(self: PpChpIer) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Assumption: electricity commodity is given by PG
ECT_ELC(RP_PG(ECT_CHP,C)) = YES;
RP_PG(ECT_ELC(R,P,C))     = NO;
""",
        )

    def commodity_group(self: PpChpIer) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Assumption only one commodity group exists on the ouput side with electricity and heat as its members
OPTION CG_GRP <= FLO_FUNC;
LOOP(ECT_ELC(R,P,COM),
   LOOP((CG_GRP(R,P,CG,CG2),COM_GMAP(R,CG,COM))$(SUM(TOP(R,P,C,'OUT')$(COM_GMAP(R,CG,C)*COM_TMAP(R,'NRG',C)),1)=2),
       ECT_DHT(R,P,C)$(COM_GMAP(R,CG,C)*COM_TMAP(R,'NRG',C)*(NOT ECT_ELC(R,P,C))) = YES;
       ECT_CGOUT(R,P,CG)=YES; ECT_CGIN(R,P,CG2)=YES));
* input CG is new PCG
RP_PG(ECT_CGIN) = YES; OPTION CLEAR=CG_GRP;
""",
        )

    def calculate_electricity_heat_ratio(self: PpChpIer) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Calculation of Ratio of electricity to heat: REH
ECT_REH(R,T,P)$ECT_CHP(R,P) $= 1/SUM((ECT_CGOUT(R,P,CG1),ECT_ELC(R,P,COM))$FLO_SHAR(R,T,P,COM,CG1,'ANNUAL','LO'),1/(FLO_SHAR(R,T,P,COM,CG1,'ANNUAL','LO')) - 1);
            """,
        )

    def convert_input_capacity(self: PpChpIer) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Conversion factor from input capacity to electricity capacity in backpressure point
ECT_INP2ELC(R,T,P)$ECT_CHP(R,P) $=
  SUM((ECT_CGIN(R,P,CG2),ECT_ELC(R,P,C)),
     SUM(ECT_CGOUT(R,P,CG1)$FLO_FUNC(R,T,P,CG1,CG2,'ANNUAL'),FLO_FUNC(R,T,P,CG1,CG2,'ANNUAL')*(1 + SUM(ECT_DHT(R,P,COM)$FLO_SHAR(R,T,P,C,CG1,'ANNUAL','LO'),FLO_SUM(R,T,P,CG1,COM,CG2,'ANNUAL'))
                                                         *(1/(FLO_SHAR(R,T,P,C,CG1,'ANNUAL','LO')) - 1))
     )
  );
ECT_INP2ELC(R,T,P)$ECT_INP2ELC(R,T,P) $= 1/ECT_INP2ELC(R,T,P);

* Conversion factor from input capacity to electricity capacity in condensing mode
ECT_INP2CON(R,T,P)$ECT_CHP(R,P) $= SUM((ECT_CGOUT(R,P,CG1),ECT_CGIN(R,P,CG2))$FLO_FUNC(R,T,P,CG1,CG2,'ANNUAL'),1/FLO_FUNC(R,T,P,CG1,CG2,'ANNUAL'));

* Conversion factor from input capacity to heat capacity in backpressure point
ECT_INP2DHT(R,T,P)$(ECT_CHP(R,P)*ECT_REH(R,T,P)) $= ECT_INP2ELC(R,T,P)/ECT_REH(R,T,P);
""",
        )

    def extrapolate_past_years(self: PpChpIer) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Extrapolate backwards for pastyears
ECT_INP2ELC(R,V,P)$NCAP_PASTI(R,V,P) $= SUM(MIYR_1(T),ECT_INP2ELC(R,T,P));
ECT_INP2DHT(R,V,P)$NCAP_PASTI(R,V,P) $= SUM(MIYR_1(T),ECT_INP2DHT(R,T,P));
ECT_INP2CON(R,V,P)$NCAP_PASTI(R,V,P) $= SUM(MIYR_1(T),ECT_INP2CON(R,T,P));
ECT_REH(R,V,P)$(ECT_CHP(R,P)*NCAP_PASTI(R,V,P)) $= SUM(MIYR_1(T),ECT_REH(R,T,P));

LOOP(ECT_CHP(R,P),
   NCAP_COST(R,T,P,CUR) $= NCAP_COST(R,T,P,CUR)*ECT_INP2CON(R,T,P);
   NCAP_FOM(R,T,P,CUR)  $= NCAP_FOM(R,T,P,CUR)*ECT_INP2CON(R,T,P);
   ACT_COST(R,T,P,CUR)  $= ACT_COST(R,T,P,CUR)*ECT_INP2CON(R,T,P);
   ACT_BND(R,T,P,S,BD)  $= ACT_BND(R,T,P,S,BD)/ECT_INP2ELC(R,T,P);
   CAP_BND(R,T,P,BD)    $= CAP_BND(R,T,P,BD)/ECT_INP2ELC(R,T,P);
   NCAP_BND(R,T,P,BD)   $= NCAP_BND(R,T,P,BD)/ECT_INP2ELC(R,T,P);
   NCAP_PASTI(R,V,P)$NCAP_PASTI(R,V,P)  $= NCAP_PASTI(R,V,P)/ECT_INP2ELC(R,V,P);
   NCAP_PKCNT(R,T,P,S)  $= ECT_INP2ELC(R,T,P);
);

* Default values for condensing and backpressure mode efficiencies
* [UR] 04/23/2003 removed default values because of numerical difficulties in sensitivity analysis
*ECT_AFCON(R,T,P,'UP')$(ECT_CHP(R,P)*(NOT SUM(BD,ECT_AFCON(R,T,P,BD)))) = 1;
*ECT_AFBPT(R,T,P,'UP')$(ECT_CHP(R,P)*(NOT SUM(BD,ECT_AFBPT(R,T,P,BD)))) = 1;

*display ect_elc, ect_dht, ect_cgin, ect_cgout, ect_inp2elc, ect_inp2dht, ect_inp2con, ect_reh;
""",
        )
