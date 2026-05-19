# prep_ext_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PREP_ext.abs oversees all the added interpolation activities needed by ABS
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


class PrepExtAbs(GamsClass):
    """Translation unit for prep_ext.abs."""

    # Instance attributes
    module_name: str = "prep_ext_abs"
    gams_source: str = "prep_ext.abs"

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
        self.tc.enqueue(self.add_reserve_commodities)
        # fmt: off
        batincludes = [
            ("BS_LAMBDA", "R",     "C",         ",'0','0','0','0','0'", "T", "YES",        ">=0"),
            ("BS_DETWT",  "R",     "C",         ",'0','0','0','0','0'", "T", "YES",        ">=0"),
            ("BS_SIGMA",  "R",     "C,BS_K,S",  ",'0','0','0'",         "T", "YES",        ">=0"),
            ("BS_SHARE",  "R",     "C,BS_K,BD", ",'0','0','0'",         "T", "YES",        ">=0"),
            ("BS_RTCS",   "RSP,R", "C,S",       ",'0','0','0'",         "T", "YES",        ">=0"),
            ("BS_MAINT",  "R",     "P,S",       ",'0','0','0','0'",     "V", "RTP(R,V,P)", ">=0"),
            ("BS_RMAX",   "R",     "P,C,S",     ",'0','0','0'",         "V", "RTP(R,V,P)", ">=0"),
            ("BS_BNDPRS", "R",     "P,C,S,BD",  ",'0'",                 "T", "RTP(R,T,P)", "1"),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                )
            )
        self.tc.enqueue(self.intermediate_qa_clean_up)

    def add_reserve_commodities(self: PrepExtAbs) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Add reserve commodities to RC
  RC(R,C) $= BS_RTYPE(R,C);
  LOOP((RP,ITEM)$GR_GENMAP(RP,ITEM),BS_K(ITEM)=YES);
  LOOP((R,T,C,P,BD)$BS_SHARE(R,T,C,P,BD),BS_K(P)=YES);

* Bulk processing
  OPTION BS_RTCS < BS_DEMDET;
  BS_RTCS('OMEGA',R,YEAR,C,S) $= BS_OMEGA(R,YEAR,C,S);
  BS_RTCS('DELTA',R,YEAR,C,S) $= BS_DELTA(R,YEAR,C,S);
""",
        )

    def intermediate_qa_clean_up(self: PrepExtAbs) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Intermediate QA clean-up
  BS_RTCS(RSP('OMEGA'),R,T,C,S)$BS_RTCS(RSP,R,T,C,S) = ROUND(BS_RTCS(RSP,R,T,C,S));
  BS_SIGMA(R,T,C,BS_K,S)$(BS_LAMBDA(R,T,C)=0)=0;
  BS_RMAX(R,LL--ORD(LL),P,C,S+STOA(S)) $= (BS_RMAX(R,LL,P,C,S)>0);
  BS_RMAX(R,LL,P,C,S)$(NOT BS_RMAX(R,'0',P,C,'ANNUAL'))=0;
  BS_BNDPRS(R,T,P,C,S,BD)$((BS_LAMBDA(R,T,C)=0)$BS_BNDPRS(R,T,P,C,S,BD))=0;
  OPTION BS_BSC < BS_RMAX, CLEAR=BS_OMEGA;
""",
        )
