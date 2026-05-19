# initmty_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * INITMTY.stc - Extension for Stochastics
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyStc(GamsClass):
    """Translation unit for initmty.stc"""

    # Instance attributes
    module_name: str = "initmty_stc"
    gams_source: str = "initmty.stc"

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
        self.env.set_global("stages", "YES")

        def input_control_parameters() -> None:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
$onMulti
  PARAMETER SW_START(J) //;
  PARAMETER SW_SUBS(J,ALLSOW) //;
  PARAMETER SW_SPROB(J,ALLSOW) //;
  PARAMETER SW_PROB(ALLSOW) //;
  PARAMETER SW_LAMBDA / 0 /;
* Predefined UC names for tradeoff analysis
  SET UC_N / OBJZ, OBJ1 /;
""",
            )

        def internal_sets_and_parameters() -> None:
            m = self.tc.container
            # ALIAS (ALLSOW,WW);
            allsow = m["ALLSOW"]
            Alias(m, "WW", alias_with=allsow)
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
  SET SW_CHILD(J,WW,WW) 'Child SOWs of parent SOW at stage J' //;
  SET SW_TREE(J,WW,WW)  'Finest level SOWs of SOW at stage J' //;
  SET SW_COPY(J,ALLSOW) 'Parent SOW of SOWs to be copied' //;
  SET SW_CPMAP(J,WW,WW) 'Copy map for attributes' //;
  SET SW_TSTG(LL,J)     'Valid stages J for each period T' //;
  SET SW_MAP(T,WW,J,WW) 'Map from internal to original SOW' //;
  SET SW_REV(WW,J,WW)   'Reverse SOW tree' //;
  SET SUPERYR(T,ALLYEAR) 'SUpremum PERiod YeaR' //;
  PARAMETER SW_DESC(J,ALLSOW) 'Number of finest level SOWs' //;
  SCALARS SW_PHASE / 0 /, SW_PARM / 0 /, SW_NORM / 1 /, DOITER / 0 /;
 """,
            )

        def available_sows_per_period() -> None:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
  SET SW_T(ALLYEAR,ALLSOW)          'Which SOWs are available at each period'               //;
  SET SW_TSW(ALLSOW,ALLYEAR,ALLSOW) 'Mapping from finest SOWs to unique SOW at each period' //;
  SET SW_STAGE(J,ALLSOW)            'Internal SOWs at each stage'                           //;
  SET SW_UCT(UC_N,T,ALLSOW) //;
  PARAMETER SW_TPROB(T,ALLSOW) //;
                             """,
            )

        def stochastic_input_parameters() -> None:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
  PARAMETER S_COM_PROJ(REG,ALLYEAR,COM,J,ALLSOW)  'Demand scenario projection' //;
  PARAMETER S_CAP_BND(REG,ALLYEAR,PRC,BD,J,ALLSOW) 'Bound on total installed capacity' //;
  PARAMETER S_COM_CUMPRD(R,BOHYEAR,EOHYEAR,C,BD,J,ALLSOW) 'Cumulative limit on COMPRD' //;
  PARAMETER S_COM_CUMNET(R,BOHYEAR,EOHYEAR,C,BD,J,ALLSOW) 'Cumulative limit on COMNET' //;
  PARAMETER S_COM_TAX(R,ALLYEAR,C,S,COM_VAR,CUR,J,ALLSOW) 'Tax on commodity NET/PRD' //;
  PARAMETER S_FLO_CUM(R,P,C,ITEM,ITEM,BD,J,ALLSOW) 'Cumulative limit on FLOW' //;
  PARAMETER S_FLO_FUNC(R,ALLYEAR,P,CG,CG,J,ALLSOW) 'Uncertain multiplier of process transformation';
  PARAMETER S_NCAP_COST(R,ALLYEAR,P,J,ALLSOW) 'Uncertain multiplier of investment cost' //;
  PARAMETER S_DAM_COST(R,ALLYEAR,C,CUR,J,ALLSOW) 'Damage costs';
  PARAMETER S_UC_RHS(UC_N,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_UC_RHSR(ALL_REG,UC_N,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_UC_RHST(UC_N,ALLYEAR,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_UC_RHSRT(ALL_REG,UC_N,ALLYEAR,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_UC_RHSTS(UC_N,ALLYEAR,TS,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_UC_RHSRTS(ALL_REG,UC_N,ALLYEAR,TS,LIM,J,ALLSOW) 'RHS of user constraint' //;
  PARAMETER S_CM_MAXCO2C(ALLYEAR,J,ALLSOW) 'Maximum allowable atmospheric CO2 concentration' //;
  PARAMETER S_CM_MAXC(ALLYEAR,ITEM,J,ALLSOW) 'Maximum allowable climatic quantity' //;
  PARAMETER S_CM_CONST(ITEM,J,ALLSOW) 'Climate constants' //;
  PARAMETER S_UCOBJ(UC_N,ALLSOW) 'Weight of UC objective component in tradeoff analysis' //;
  PARAMETER S_NCAP_AFS(R,ALLYEAR,P,S,J,ALLSOW) 'Seasonal availability factors';
  PARAMETER S_COM_FR(R,ALLYEAR,C,S,J,ALLSOW) 'Commodity fraction multipliers';
""",
            )

        def internal_work_sets_and_parameters() -> None:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
  PARAMETER S_COM_CUM(R,COM_VAR,ALLYEAR,ALLYEAR,C,BD,J,ALLSOW) 'Cumulative limit on COMPRD' //;
  SET T0(LL) 'Augmented periods';
  SET SW_T2W(WW,T,WW,LL) 'Augmented map for SOWs by period';
  SET RTCSW(R,T,C,S,WW) 'Indicator for uncertain timeslice fractions';
  SET RTPW(R,ALLYEAR,P,ALLSOW) 'Uncertain SOW by vintage';
  SET RP_FFSGG(R,P,CG,CG) 'Uncertain transformation groups';
  SET RP_FFSGGM(R,P,CG,CG,COM_GRP,COM_GRP) 'Map of transformation groups';
  PARAMETER OBJ_SIC(R,T,P,ALLSOW) 'Uncertainty in investments';
  PARAMETER SUC_L(ALL_R,UC_N) 'Dynamic type LHS' //;
  PARAMETER RTP_SAFS(R,T,P,S,WW) 'Uncertain availability factors';
  PARAMETER RTCS_SFR(R,LL,C,S,WW,TS) 'Uncertain COM_FR multipliers';
  PARAMETER RCS_SSFR(R,C,S,TS,WW,LL) 'Uncertain COM_FR multipliers';

 """,
            )

        def reporting() -> None:
            self.tc.add_gams_code(
                module=self,
                phase=phase,
                code=r"""
  PARAMETER SPAR_UCSL(WW,UC_N,*,*,*) //;
  PARAMETER CM_SRESULT(ALLSOW,ITEM,ITEM,ALLYEAR) 'Climate Module basic results' //;
  PARAMETER CM_SMAXC_M(ALLSOW,ITEM,ALLYEAR) 'Marginals for max constraints' //;
 """,
            )

        input_control_parameters()
        internal_sets_and_parameters()
        available_sows_per_period()
        stochastic_input_parameters()
        internal_work_sets_and_parameters()
        reporting()
