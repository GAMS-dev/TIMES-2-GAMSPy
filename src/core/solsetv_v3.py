# solsetv_v3.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * SOLSETV.VDA
# *
# * Output routine - creating flat Sets for VEDA
# *
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.solsysd_v3 import SolsysdV3

from .base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolsetvV3(GamsClass):
    """Translation unit for solsetv.v3."""

    module_name: str = "solsetv_v3"
    gams_source: str = "solsetv.v3"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        if self.arg1 != "":
            if self.arg1 == "ADESCVDD":
                self._label_adescvdd()
                self._label_rest()
                return
            if self.arg1 == "REST":
                self._label_rest()
                return
            if self.arg1 == "FINISHUP":
                self._label_finishup()
                return
            raise ValueError(f"Unknown label for solsetv.v3: {self.arg1}")

        # Scenario index defaulting to 1
        if self.env.stages != "YES":
            self.tc.enqueue(self.exec1)

        # Make sure CLI attributes are defined
        if self.env.cli == "YES":
            self._label_adescvdd()
            self._label_rest()
            return

        if self.env.solveda == "1":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
PARAMETER CM_SRESULT(ALLSOW,ITEM,ITEM,ALLYEAR) //;
PARAMETER CM_SMAXC_M(ALLSOW,ITEM,ALLYEAR) //;
""",
            )

        self._label_adescvdd()
        self._label_rest()

    def _label_adescvdd(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=r"""
SET ADESC Attribute Descriptions /

* variables (and their marginals)
VAR_act     'Process Activity'
VAR_actM    'Process Activity - Marginals'
VAR_cap     'Technology Capacity'
VAR_capM    'Technology Capacity - Marginals'
VAR_ncap    'Technology Investment - New capacity'
VAR_ncapM   'Technology Investment - Marginals'
VAR_ncapR   'Technology Investment - BenCost + ObjRange'
VAR_fin     'Commodity Consumption by Process'
VAR_fout    'Commodity Production by Process'
VAR_Pout    'Commodity Output Level by Process'
VAR_comprd  'Commodity Total Production'
VAR_comprdM 'Commodity Total Production - Marginal'
VAR_comnet  'Commodity Net'
VAR_comnetM 'Commodity Net - Marginal'
VAR_eout    'Electricity supply by technology and energy source'
VAR_CumCst  'Cumulative costs by type (if constrained)'

* equations (and their marginals)
EQ_combal  'Commodity Slack/Levels'
EQ_combalM 'Commodity Slack/Levels - Marginals'
EQ_peak    'Peaking Constraint Slack'
EQ_peakM   'Peaking Constraint Slack - Marginals'
EQ_Cumflo  'Cumulative flow constraint - Levels'
EQ_CumfloM 'Cumulative flow constraint - Marginals'
EQ_IreM    'Inter-regional trade equations - Marginals'

* calculated parameters
PAR_capLO  'Capacity Lower Limit'
PAR_capUP  'Capacity Upper Limit'
PAR_CapRet 'Cumulative Retirements of Technology Capacity by Vintage'
PAR_Top    'Process topology (Opted out - SET RPT_TOP YES to activate)'
Cap_New    'Newly installed capacity and lumpsum investment by vintage and commissioning period'

* calculated costs
COST_inv   'Annual investment costs'
COST_dec   'Annual decommissioning costs'
COST_salv  'Salvage values of capacities at EOH+1'
COST_late  'Annual late costs'
COST_fom   'Annual fixed operating and maintenance costs'
COST_act   'Annual activity costs'
COST_flo   'Annual flow costs (including import/export prices)'
COST_com   'Annual commodity costs'
COST_els   'Annual elastic demand cost term'
COST_dam   'Annual damage cost term'
COST_invx  'Annual investment taxes/subsidies'
COST_fixx  'Annual fixed taxes/subsidies'
COST_flox  'Annual flow taxes/subsidies'
COST_comx  'Annual commodity taxes/subsidies'
COST_ire   'Annual implied costs of endogenous trade'
COST_NPV   'Total discounted costs by process/commodity (optional)'
Time_NPV   'Discounted value of time by period'
VAL_Flo    'Annual commodity flow values'
ObjZ       'Total discounted system cost'
Reg_wobj   'Regional total expected discounted system cost'
Reg_obj    'Regional total discounted system cost'
Reg_irec   'Regional total discounted implied trade cost'
Reg_ACost  'Regional total annualized costs by period'
User_Con   'Level of user constraint'
User_ConFXM 'Marginal cost of user constraint (or group-wise market share)'
User_ConLOM 'Marginal cost of lower bound user constraint'
User_ConUPM 'Marginal cost of upper bound user constraint'
User_DynbM  'Marginal cost of dynamic process bound constraint'
User_Maxbet 'Level of MaxBet constraint'

* Climate module and MACRO
VAR_climate 'Climate result variables'
Dual_Clic   'Shadow price of climate constraint'
VAR_Macro   'MACRO result variables'
/;
""",
        )

    def _label_rest(self) -> None:
        if "IRE" in self.tc.container.listSymbols():
            raise ValueError(
                "Illegal Declaration of Internal TIMES Identifier: IRE - Run Aborted"
            )
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
SETS
  IRE(IRE)   'Inter-regional Exchange (Exports & Imports)',
  IRELX(IRE) 'Electricity Exchange Processes',
  IRENX(IRE) 'Enodogenous Trade Exchange',
  STG(IRE)   'Storage Processes (genuine)',
  STS(IRE)   'General Multilevel Storage',
  RCAP(IRE)  'Processes with Retirements',
  NST(IRE)   'Night Storage';
SETS
  DMD(R,P)   'Demand Devices'
  PRE(R,P)   'Energy Processes'
  PRW(R,P)   'Material Processes - Weight'
  PRV(R,P)   'Material Processes - Volume'
  REF(R,P)   'Refineries'
  ELE(R,P)   'Electric Power Plants'
  CHP(R,P)   'Coupled Heat+Power Plants'
  HPL(R,P)   'Heating Plants'
  DISTR(R,P) 'Distribution Technologies'
  RENEW(R,P) 'Renewables Processes'
  XTRACT(R,P)'Extraction Processes'
;
""",
        )
        self.tc.enqueue(self.exec2)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
SETS
  RES(R,COM)   'Residential Sector Demands'
  COMM(R,COM)  'Commercial Sector Demands'
  TRN(R,COM)   'Transporation Sector Demands'
  AGR(REG,COM) 'Agriculature Sector Demands'
  OTHD(R,COM)  'Other Demands'
  IND(REG,COM) 'Industrial Demands'
  NRGFOS(R,C)  'Fossil'
  NRGREN(R,C)  'Renewable'
  NRGSYN(R,C)  'Synthetic'
  NRGELC(ALL_R,C) 'Electricity'
  NRGHET(ALL_R,C) 'Heat'
;
""",
        )

        self.tc.enqueue(self.exec3)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* timeslices
  SET RS(R,ALL_TS);
""",
        )

        self.tc.enqueue(self.exec4)
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code="""
* UCs and completion of missing labels
  SETS
   NONSET / NONE /
   PLUSET / '+' /
   OTHCOM(ITEM) //
   SET REG_ACT(ITEM,C)
   UC_CONST(*,UC_N) 'Genuine TIMES UC constraints'
   UC_MARKS(R,ITEM) 'PRC_MARK Share UC constraints'
   UC_DYNBD(R,UC_N) 'Dynamic UC bound constraints';
""",
        )

        self.tc.enqueue(
            self.exec5,
            pgprim=self.env.pgprim,
        )

        if self.env.punits.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
  SET PRC_UNITS(R,P,UC_GRPTYPE,UNITS);
""",
            )

            self.tc.enqueue(self.exec6)

    def _label_finishup(self) -> None:
        self.tc.enqueue(self.exec7)
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYMBOL",
                base_name="REG_ACOST",
                index_block="SOW,R",
                extra_index=",T,",
                suffix="",
                symbol_prefixes=["S", "R"],
                map=False,
            )
        )
        self.include(
            SolsysdV3(
                self.tc,
                self.env,
                mode="SYMBOL",
                base_name="REG_WOBJ",
                index_block="SOW,R",
                extra_index=",",
                suffix=",CUR",
                symbol_prefixes=["S", "R"],
                map=False,
            )
        )
        self.tc.enqueue(self.exec8)

        if self.env.rpt_top.upper() == "YES":
            self.tc.add_gams_code(
                module=self,
                phase="run",
                code=r"""
SET ADESC / PAR_Top 'Process topology indicator' /;
""",
            )
            self.tc.enqueue(self.exec9)
        self.tc.enqueue(self.exec10)

    def exec1(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="SOW('1') = YES;",
        )

    def exec2(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* set the regional memebers of the reporting sets
  DMD(RP(R,P))   $= PRC_MAP(R,'DMD',P);
  PRE(RP(R,P))   $= PRC_MAP(R,'PRE',P);
  PRW(RP(R,P))   $= PRC_MAP(R,'PRW',P);
  PRV(RP(R,P))   $= PRC_MAP(R,'PRV',P);
  REF(RP(R,P))   $= PRC_MAP(R,'REF',P);
  ELE(RP(R,P))   $= PRC_MAP(R,'ELE',P);
  CHP(RP(R,P))   $= PRC_MAP(R,'CHP',P);
  HPL(RP(R,P))   $= PRC_MAP(R,'HPL',P);
  DISTR(RP(R,P)) $= PRC_MAP(R,'DISTR',P);
  RENEW(RP(R,P)) $= PRC_MAP(R,'RENEW',P);
  XTRACT(RP(R,P))$= PRC_MAP(R,'XTRACT',P);
""",
        )

    def exec3(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* set the regional memebers of the reporting sets
  RES(RC(R,C))  $= DEM_SMAP(R,'RES',C);
  COMM(RC(R,C)) $= DEM_SMAP(R,'COM',C);
  TRN(RC(R,C))  $= DEM_SMAP(R,'TRN',C);
  AGR(RC(R,C))  $= DEM_SMAP(R,'AGR',C);
  IND(RC(R,C))  $= DEM_SMAP(R,'IND',C);
  OTHD(RC(R,C)) $= DEM_SMAP(R,'OTH',C);
  NE(RC(R,C))   $= DEM_SMAP(R,'NE',C);
  NRGELC(NRG(R,C)) $= NRG_TMAP(R,'ELC',C);
  NRGHET(NRG(R,C)) $= NRG_TMAP(R,'LTHEAT',C);
  NRGHET(NRG(R,C)) $= NRG_TMAP(R,'HTHEAT',C);
  NRGFOS(NRG(R,C)) $= NRG_TMAP(R,'FOSSIL',C);
  NRGREN(NRG(R,C)) $= NRG_TMAP(R,'RENEN',C);
  NRGREN(NRG(R,C)) $= NRG_TMAP(R,'FRERENEW',C);
  NRGREN(NRG(R,C)) $= NRG_TMAP(R,'LIMRENEW',C);
  NRGSYN(NRG(R,C)) $= NRG_TMAP(R,'SYNTH',C);

*GG* set the REGional descriptions if not provided
* Use the RC / RP masks
  COM_DESC(RC(R,C))$(NOT COM_DESC(R,C)) = COM_GRP(C);
  PRC_DESC(RP(R,P))$(NOT PRC_DESC(R,P)) = PRC(P);
""",
        )

    def exec4(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
OPTION RS < RS_TSLVL;
""",
        )

    def exec5(
        self: SolsetvV3,
        pgprim: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  LOOP(R,UC_CONST('NONE',UC_N)$UC_R_SUM(R,UC_N)=YES);
  LOOP(RMKC(R,ITEM,C)$RPT_OPT('COMPRD','4'),UC_MARKS(R,ITEM)=YES);
  REG_ACT(ALL_R,'{pgprim}') = ALL_REG(ALL_R);
  REG_ACT(NONSET,'{pgprim}') = YES;
  OTHCOM(CG) $= SUM(COM_PEAK(R,CG),1);
  OTHCOM(CUR) $= SUM(RDCUR(R,CUR),1);
""",
        )

    def exec6(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Add default capacity unit and conversion if missing
  G_UNCA(UNITS_ACT,UNITS_ACT)$(NOT SUM(UNITS$(G_UNCA(UNITS,UNITS_ACT)=1),1)) = 1;
  PRC_UNITS(RP,'ACT',UNITS_ACT)$SUM(PRC_ACTUNT(RP,CG,UNITS_ACT),1) = YES;
  LOOP(UNITS_ACT,
    PRC_UNITS(PRC_CAP(RP),'CAP',UNITS)$((ABS(G_UNCA(UNITS,UNITS_ACT)-PRC_CAPACT(RP))<PRC_CAPACT(RP)/1280)$G_UNCA(UNITS,UNITS_ACT)$PRC_UNITS(RP,'ACT',UNITS_ACT)) = YES);
  TRACKP(PRC_CAP(RP))$PROD(PRC_UNITS(RP,'CAP',UNITS),SUM(PRC_CAPUNT(RP,CG,UNITS_CAP),1)$PRC_UNITS(RP,'ACT',UNITS)) = YES;
  PRC_UNITS(TRACKP(RP),'CAP',UNITS) = SUM(PRC_CAPUNT(RP,CG,UNITS_CAP(UNITS)),1);
  OPTION CLEAR=TRACKP;
""",
        )

    def exec7(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
* Finally, do some cleanup and set optional TOP indicators
  OPTION CLEAR=RP_UX, UC_DYNBD < PRC_DYNUC;
  RP_SGS(R,P) $= PRC_MAP(R,'NST',P);
  IRE_DIST(RP_IRE(R,P)) $= SUM(RPC_IREIO(R,P,C,IE,'IN'),1);
  RP_UX(RP_IRE(R,P)) $= SUM(RPC_IRE(R,P,C,IE),NRGELC(R,C));
""",
        )

    def exec8(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  OPTION CLEAR=AFS,CLEAR=PAR_OBJSAL,CLEAR=RTPC,CLEAR=RTTC,CLEAR=COEF_VNT,CLEAR=RVP_KMAP,CLEAR=RTP_VNTBYR,CLEAR=PAR_TOP;
""",
        )

    def exec9(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
RPT_OPT('FLO','7')=1;
""",
        )

    def exec10(self: SolsetvV3) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code="""
  IF(RPT_OPT('FLO','7'),
    PAR_TOP(R,T(MIYR_1),P,C,IO)$TOP(R,P,C,IO) = EPS;
    PAR_TOP(R,T(MIYR_1),P,C,'OUT')$RPC_IRE(R,P,C,'IMP') = EPS;
    PAR_TOP(R,T(MIYR_1),P,C,'IN')$RPC_IRE(R,P,C,'EXP')  = EPS;
    PAR_TOP(R,T-(ORD(T)-1),P,C,IO)$NCAP_COM(R,T,P,C,IO) = EPS;
  );
""",
        )
