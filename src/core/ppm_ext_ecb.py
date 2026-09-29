# ppm_ext_ecb.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * ppm_ext.ecb - coefficients for market sharing (economic choice behavior)
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number

from core.base_class import GamsClass
from core.fillparm_gms import FillparmGms, FillparmGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpmExtEcb(GamsClass):
    """Translation unit for ppm_ext.ecb."""

    # Instance attributes
    module_name: str = "ppm_ext_ecb"
    gams_source: str = "ppm_ext.ecb"

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
        g = self.tc
        self.comp1()
        if (
            self.env.stages.upper() == "YES"
            or self.env.macro == "YES"
            or self.env.macro.upper() in ["CSA", "MSA"]
            or self.env.stepped == "+"
        ):
            return

        self.env.set_global("ecb", "YES")
        self.comp2()
        self.env.set_scoped("reset", 0)

        # fmt: off
        batincludes: list[FillparmGmsConfig] = [
            FillparmGmsConfig(g.com_mshgv,  (g.r,), (g.c,),             ("",) * 5, g.t, g.Rtc[g.r, g.t, g.c], Number(0)),
            FillparmGmsConfig(g.ncap_msprf, (g.r,), (g.c, g.p, g.lA),   ("",) * 3, g.t, g.Rtc[g.r, g.t, g.p], Number(0)),
        ]
        # fmt: on
        for config in batincludes:
            self.include(FillparmGms(self.tc, self.env, config=config))

        self.tc.enqueue(self.init_probing_shares)

    def comp1(self: PpmExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET COM_GRP  / '_MSVIOL_' /;
  SET COM      / '_MSVIOL_' /;
  """,
        )

    def comp2(self: PpmExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
  SET COM_TMAP / (SET.REG).FIN.'_MSVIOL_'/;
  SET COM_LIM  / (SET.REG).'_MSVIOL_'.N  /;
  SET RTC_MS(R,YEAR,C)              'Commodities with market sharing' // ;
  PARAMETER COEF_LMS(R,ALLYEAR,C,P) 'Logit Market Share coefficients' // ;
  PARAMETER ECB_NCAPR(R,ALLYEAR,P)  'First pass LEC results' //;
  """,
        )

    def init_probing_shares(self: PpmExtEcb) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
* Initialize probing shares
  RTC_MS(RTC(R,T,C))$(SUM(TOP(RPC_PG(R,P,C),'OUT')$(NOT RTP_OFF(R,T,P)),ORD(T)>1)$COM_MSHGV(R,T,C)) = YES;
  LOOP(RTC_MS(R,T,C), OPTION CLEAR=PRC_YMAX;
    PRC_YMAX(RP_FLO(PRC_CAP(R,P)))$TOP(R,P,C,'OUT') = RPC_PG(R,P,C)$(NOT RTP_OFF(R,T,P));
    Z=SUM(P$PRC_YMAX(R,P),1); IF(Z, COEF_LMS(R,T,C,P)$PRC_YMAX(R,P) = -0.05 / Z));

* Complete flow controls for dummy
  OPTION TRACKPC < COEF_LMS, RVP < COEF_LMS, TRACKP < TRACKPC;
  TOP(TRACKP(R,P),'_MSVIOL_','IN') = YES;
  RPC_NOFLO(TRACKP,'_MSVIOL_') = YES;
  RPCS_VAR(TRACKP(R,P),'_MSVIOL_',ANNUAL) = YES;
  RTPCS_VARF(RTP_VARA(R,T,P),'_MSVIOL_',ANNUAL) = YES;
  IF(RPT_OPT('NCAP','1')<>1, RPT_OPT('NCAP','101')=ROUND(RPT_OPT('NCAP','1')); RPT_OPT('NCAP','1')=1);

* Default values
  NCAP_MSPRF(R,T,C,P,L('N'))$((NOT NCAP_MSPRF(R,T,C,P,L))$COEF_LMS(R,T,C,P)) = 1;
  NCAP_MSPRF(R,T,C(ACTCG),P,L('UP'))$((NOT NCAP_MSPRF(R,T,C,P,L))$RVP(R,T,P)) = MAX(0,SMAX(TRACKPC(R,P,COM),NCAP_MSPRF(R,T,COM,P,L)));
  NCAP_MSPRF(R,T,C(ACTCG),P,L('UP'))$((NOT NCAP_MSPRF(R,T,C,P,L))$RVP(R,T,P)) = 2;

* Initialize ceiling costs
  FLO_COST(R,DATAYEAR,P,C('_MSVIOL_'),ANNUAL,CUR)$TRACKP(R,P) $= NCAP_COST(R,DATAYEAR,P,CUR);
  FLO_DELIV(R,DATAYEAR,P,C('_MSVIOL_'),ANNUAL,CUR)$TRACKP(R,P) $= NCAP_FOM(R,DATAYEAR,P,CUR);
  OPTION CLEAR=TRACKP,CLEAR=TRACKPC,CLEAR=PRC_YMAX,CLEAR=RVP;
""",
        )
