# initmty_etl.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# ******************************************************************************
# * INITMTY.ETL - declarations for technological change                        *
# ******************************************************************************
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyEtl(GamsClass):
    """Translation unit for initmty.etl."""

    # Instance attributes
    module_name: str = "initmty_etl"
    gams_source: str = "initmty.etl"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        # OPTCR from default 0.1 to 0.000001, may want to adjust in *.RUN file
        self.tc.enqueue(self.exec1)

        # Input data
        self.env.set_scoped("etl", "YES")
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
  SET TEG(PRC)                //;
  PARAMETER TL_SC0(R,PRC)     //;
  PARAMETER TL_PRAT(R,PRC)    //;
  PARAMETER TL_SEG(R,PRC)     //;
  PARAMETER TL_CCAP0(R,PRC)   //;
  PARAMETER TL_CCAPM(R,PRC)   //;
* Cluster technologies: TEG plus PRC coupled to TEG, mapping and coupling factors
  PARAMETER TL_CLUSTER(R,P,P) //;
  PARAMETER TL_MRCLUST(R,P,R,P) //;
* Input aliases
  PARAMETER SC0(R,PRC)        //;
  PARAMETER PRAT(R,PRC)       //;
  PARAMETER SEG(R,PRC)        //;
  PARAMETER CCAP0(R,PRC)      //;
  PARAMETER CCAPM(R,PRC)      //;
  PARAMETER CLUSTER(R,P,P)    //;
""",
        )

        # Internal parameters
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
* KP up to 6 as default, can be re-assigned in *.RUN file if desired
  SET KP / 1*6 /;
""",
        )

        kp = self.tc.container["KP"]
        Alias(container=self.tc.container, name="KP2", alias_with=kp)

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
  PARAMETER PAT(R,PRC)        //;
  PARAMETER PBT(R,PRC)        //;
  PARAMETER CCOST0(R,PRC)     //;
  PARAMETER CCOSTM(R,PRC)     //;
  PARAMETER WEIG(R,KP,PRC)    //;
  PARAMETER CCOSTK(R,KP,PRC)  //;
  PARAMETER CCAPK(R,KP,PRC)   //;
  PARAMETER BETA(R,KP,PRC)    //;
  PARAMETER ALPH(R,KP,PRC)    //;
  PARAMETER NTCHTEG(R,PRC) Number of technologies in cluster //;
* report specific
  PARAMETER INVC_UNIT(R,T,P)  //;
  PARAMETER PREV(R,PRC)       //;

* Starting periods for learning technologies
  SET TL_START(R,T,P)   //;
* sets of cluster2 technologies and key components
  SET TL_RP_CT(REG,PRC) //;
  SET TL_RP_KC(REG,PRC) //;

* SET and parameter Declarations for LIC Reporting Module
  PARAMETER TL_CT_COST(R,ALLYEAR,PRC,CUR) //;

*=====================================================*
* ETL Iteration parameters used during TESTing        *
*=====================================================*
* new SET MLITER (1*1 default) to enable iterative SOLVE, can be re-assigned in RUN
SET MLITER /1*1/;
* default MLITERM in RUN
SCALAR MLITERM /10.0/;
* CCDIFCRIT is termination criterion for average difference in CCAPM - CCAP(TLAST)
*   or for CCAPM values in two subsequent iterations, now set to 0.1
SCALAR CCDIFCRIT /0.1/;
""",
        )

    def exec1(self: InitmtyEtl) -> None:
        self.tc.add_gams_code(module=self, phase="run", code="OPTION OPTCR = 0.000001;")
