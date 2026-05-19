# initmty_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INITMTY.MOD has all the EMPTY declarations for system & user data           *
# *  %1..%6 - File extensions of code extensions to be included                 *
# *=============================================================================*
# * All the EMPTY declarations for user data                                    *
# *=============================================================================*
# *GaG Questions/Comments:
# *   - all but LOCAL (in single BATINCLUDE and its immediate lower routines)
# *   - consider PRC_MAP(PRC_GRP,PRC_SUBGRP,PRC) where PRC_SUBGRP = PRC_RSOURC + any user-provided sub-groupings
# *   - SOW/COM/PRC/CUR master sets (merged) == entire list, that is not REG
# *   - lists (eg, DEM_SECT) for _MAP sets not REG (but individual mappings are)
# *   - HAVE THE USER *.DD files OMIT the declarations to ease maintenance changes
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter

from core.err_stat_mod import ErrStatMod
from core.initmty_abs import InitmtyAbs
from core.initmty_cli import InitmtyCli
from core.initmty_dsc import InitmtyDsc
from core.initmty_etl import InitmtyEtl
from core.initmty_mlf import InitmtyMlf
from core.initmty_msa import InitmtyMsa
from core.initmty_stc import InitmtyStc
from core.initmty_tm import InitmtyTm
from core.initmty_vda import InitmtyVda
from core.main_ext_mod import include_extension
from core.maindrv_mod import MainDrvMod

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyMod(GamsClass):
    """Translation unit for initmty.mod."""

    # Instance attributes
    module_name: str = "initmty_mod"
    gams_source: str = "initmty.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.compile()

    def compile(self) -> None:
        self.version_control()

        # Easy access gamspy.Container
        m = self.tc.container

        def set_section() -> None:
            """
            SET SECTION
            Note: the *-out user SETs are declared in INITSYS.MOD
            """
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* commodities
*  SET COM_GRP                       'All CGs and each individal commodity';
*  SET COM(COM_GRP)                  'All Commodities'                       //;
  SET COM_DESC(REG,COM)              'Region-based commodity descriptions'   //;
*  SET COM_TYPE(COM_GRP)             'Primary grouping of commodities'       //;
  SET COM_GMAP(REG,COM_GRP,COM)      'User groups of individual commodities' //;
  SET COM_LIM(REG,COM,LIM)           'List of equation type for balance'     //;
  SET COM_OFF(REG,COM,*,*)           'Periods for which a commodity is unavailable' //;
  SET COM_TMAP(REG,COM_TYPE,COM)     'Primary grouping of commodities'       //;
  SET COM_TS(REG,COM,ALL_TS)         'List of commodity timeslices'          //;
  SET COM_TSL(REG,COM,TSLVL)         'Level at which a commodity tracked'    //;
  SET COM_UNIT(REG,COM,UNITS_COM)    'Units associated with each commodity'  //;

* currency
*  SET CUR                           'Currencies (c$)'              //;
  SET CUR_MAP(REG,CUR_GRP,CUR)       'Grouping of the currenies'    //;

* demands / emissions / financials
  SET DEM_SMAP(REG,DEM_SECT,COM)     'Grouping of DEMs (commodities) to their sector' //;
  SET ENV_MAP(REG,ENV_GRP,COM)       'Grouping of ENVs (commodities) to their emissions group' //;
  SET FIN_MAP(REG,FIN_GRP,COM)       'Grouping of FINs (commodities) to their financial group' //;

* materials
  SET MAT_GMAP(REG,MAT_GRP,COM)      'Grouping of materials'             //;
  SET MAT_TMAP(REG,MAT_TYPE,COM)     'Material by type'                  //;
  SET MAT_VOL(REG,COM)               'Material accounted for by volume'  //;
  SET MAT_WT(REG,COM)                'Material accounted for by weight'  //;

* energy
  SET NRG_FMAP(REG,NRG_FORM,COM)     'Grouping of NRG by Solid/Liquid/Gas' //;
  SET NRG_GMAP(REG,NRG_GRID,COM)     'Association of energy carriers to grids'//;
  SET NRG_TMAP(REG,NRG_TYPE,COM)     'Grouping of energy carriers by type' //;

* process
*  SET PRC                             'List of all processes'           //;
  SET PRC_AOFF(REG,PRC,*,*)            'Periods for which activity is unavailable' //;
  SET PRC_ACTUNT(REG,PRC,CG,UNITS_ACT) 'Primary commodity (or group) & activity unit' //;
  SET PRC_CAPUNT(REG,PRC,CG,UNITS_CAP) 'Unit of capacity'                //;
  SET PRC_CG(R,PRC,COM_GRP)            'Commodity groups for a process'  //;
  SET PRC_DESC(R,P)                    'Process descriptions by region'  //;
  SET PRC_FOFF(REG,PRC,COM,ALL_TS,*,*) 'Periods/timeslices for which flow is not possible'//;
  SET PRC_MAP(REG,PRC_GRP,PRC)         'Grouping of processes to nature' //;
  SET PRC_NOFF(REG,PRC,*,*)            'Periods for which new capacity can NOT be built' //;
  SET PRC_RMAP(REG,PRC_RSOURC,PRC)     'Grouping of XTRACT processes'    //;
  SET PRC_SPG(REG,PRC,COM_GRP)         'Shadow Primary Group'            //;
  SET PRC_TS(ALL_REG,PRC,ALL_TS)       'Timeslices for a process'        //;
  SET PRC_TSL(REG,PRC,TSLVL)           'Timeslice level for a process'   //;
  SET PRC_VINT(REG,PRC)                'Process is to be vintaged'       //;
  SET PRC_DSCNCAP(R,P)                 'Process with discrete capacity additions';
  SET PRC_RCAP(REG,PRC)                'Process with early retirement';
  SET PRC_SIMV(REG,PRC)                'Process is to be vintage-simulated';

* region
*  SET REG(ALL_REG)                   'List of Regions'                  //;
  SET REG_GRP(*)                      'List of regional groups'          //;
  SET REG_RMAP(REG_GRP,ALL_REG)       'Grouping of regions in/out of area of study' //;

* time
*  SET TS(ALL_TS)                     'Time slices of the year               //;
""",
            )

            #   ALIAS(ALL_TS,TS,S,SL,S2);
            all_ts = m["ALL_TS"]
            Alias(m, "TS", alias_with=all_ts)
            Alias(m, "S", alias_with=all_ts)
            Alias(m, "SL", alias_with=all_ts)
            Alias(m, "S2", alias_with=all_ts)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
  SET TS_OFF(REG,TS,BOHYEAR,EOHYEAR)  'Timeslices turned off';
  SET TS_GROUP(ALL_REG,TSLVL,TS)      'Timeslice Level assignment'           //;
  SET TS_MAP(ALL_REG,ALL_TS,ALL_TS)   'Timeslice hierarchy tree: node+below' //;
  SET MILESTONYR(ALLYEAR)             'Projection years for which model to be run' //;
""",
            )

            #   ALIAS(MILESTONYR,T,TT);
            milestonyr = m["MILESTONYR"]
            Alias(m, "T", alias_with=milestonyr)
            Alias(m, "TT", alias_with=milestonyr)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
  SET DATAYEAR(ALLYEAR)               'Years for which user data is provided' //;
  SET PASTYEAR(ALLYEAR)               'Years before 1st MILESTONYR for which PASTI needs to be handled' //;
  SET MODLYEAR(ALLYEAR)               'Years for which the model is to be run (MILESTONYR+PASTYEAR)' //;
""",
            )
            #    ALIAS(TSLVL,TSL);
            tslvl = m["TSLVL"]
            Alias(m, "TSL", alias_with=tslvl)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* topology
  SET TOP(REG,PRC,COM,IO)                  'Topology for all process'        //;
  SET TOP_IRE(ALL_REG,COM,ALL_REG,COM,PRC) 'Trade within area of study'      //;

* peaking
  SET COM_PEAK(REG,COM_GRP)           'Peaking required flag'                //;
  SET COM_PKTS(REG,COM_GRP,TS)        'Peaking time-slices'                  //;
  SET PRC_PKNO(ALL_REG,PRC)           'Processes which cannot be involved in peaking' //;
  SET PRC_PKAF(ALL_REG,PRC)           'Flag for default value of NCAP_PKCNT' //;

* storage
  SET PRC_NSTTS(REG,PRC,ALL_TS)       'Night storage process and time-slice for storaging' //;
  SET PRC_STGTSS(REG,PRC,COM)         'Storage process and stored commodity for time-slice storage' //;
  SET PRC_STGIPS(REG,PRC,COM)         'Storage process and stored commodity for inter-period storage' //;

* user constraints
  SET UC_N(*)                         'Names of all manual constraints'     / OBJVAR /;
  SET UC_T_SUCC(ALL_R,UC_N,ALLYEAR)   'Specification of periods, if UC_DYN=SUCC'    //;
  SET UC_T_SUM(ALL_R,UC_N,ALLYEAR)    'Specification of periods, if UC_DYN=SEVERAL' //;
  SET UC_T_EACH(ALL_R,UC_N,ALLYEAR)   'Specification of periods, if UC_DYN=EACH'    //;
  SET UC_R_SUM(ALL_R,UC_N)            'Specification of regions, if UC_REG=SUM'     //;
  SET UC_R_EACH(ALL_R,UC_N)           'Specification of regions, if UC_REG=EACH'    //;
  SET UC_TS_SUM(ALL_R,UC_N,ALL_TS)    'Specification of time-slices, if UC_TS=SUM'  //;
  SET UC_TS_EACH(ALL_R,UC_N,ALL_TS)   'Specification of time-slices, if UC_TS=EACH' //;
  SET UC_ATTR(ALL_R,UC_N,SIDE,UC_GRPTYPE,UC_NAME) 'Mapping of parameter names to groups' //;
  SET UC_TSL(ALL_R,UC_N,SIDE,TSLVL)   'UC timeslice level' //;
""",
            )
            # ALIAS(UC_N,UCN);
            uc_n = self.tc.container["UC_N"]
            Alias(container=self.tc.container, name="UCN", alias_with=uc_n)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* miscellaneous
*  SET SOW                       'Stochastic State-of-the-World'         //;
  SET SW_T(ALLYEAR,ALLSOW)       'Stochastic state indexes by period'    //;
  SET G_UAMAT(U)                 'Unit for activity of material process' //;
  SET G_UANRG(U)                 'Unit for activity of energy process'   //;
  SET G_UCMAT(U)                 'Unit for capacity of material process' //;
  SET G_UCNRG(U)                 'Unit for capacity of energy process'   //;
  SET G_RCUR(REG,CUR)            'Main currency unit by region'          //;

""",
            )

            # * Predefined system CGs and one COM:
            # $IF NOT SET PGPRIM $SETGLOBAL PGPRIM "'ACT'"
            self.env.set_if_not_exists("pgprim", "ACT", scope="global")
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
$onMulti
    SET COM_GRP   / {self.env.pgprim}, CAPFLO /;
    SET ACTCG(CG) / {self.env.pgprim} /;
    SET COM       / {self.env.pgprim} /;
    """,
            )

        def parameters_section() -> None:
            """Parameters section"""
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
* time
  PARAMETER B(ALLYEAR)      'Beginning year of each model period' //;
  PARAMETER E(ALLYEAR)      'Ending year of each model period'    //;
  PARAMETER M(ALLYEAR)      'Middle year of each Period'          //;
  PARAMETER D(ALLYEAR)      'Length of each period'               //;

* Activity
  PARAMETER ACT_BND(REG,ALLYEAR,PRC,TS,BD)      'Bound on activity of a process' //;
  PARAMETER ACT_COST(REG,ALLYEAR,PRC,CUR)       'Variable costs associated with activity of a process' //;
  PARAMETER ACT_CSTUP(R,ALLYEAR,P,TSLVL,CUR)    'Variable costs associated with startup of a process' //;
  PARAMETER ACT_CSTSD(R,ALLYEAR,P,UPT,BD,CUR)   'Start-up (BD=UP) and shutdown costs (BD=LO) per unit of started-up capacity, by start-up type'//;
  PARAMETER ACT_CSTRMP(R,ALLYEAR,P,L,CUR)       'Ramp-up (L=UP) or ramp-down (L=LO) cost per unit of load change' //;
  PARAMETER ACT_FLO(REG,ALLYEAR,PRC,CG,S)       'General process transformation parameter'//
  PARAMETER ACT_TIME(R,ALLYEAR,P,L)             'Minimum online/offline hours' //;
  PARAMETER ACT_CUM(REG,PRC,ITEM,ITEM,LIM)      'Bound on cumulative activity' //;

* New Capacity
  PARAMETER NCAP_AF(REG,ALLYEAR,PRC,TS,BD)      'Availability of capacity'                //;
  PARAMETER NCAP_AFA(REG,ALLYEAR,PRC,BD)        'Annual Availability of capacity'         //;
  PARAMETER NCAP_AFS(REG,ALLYEAR,PRC,TS,BD)     'Seasonal Availability of capacity'       //;
  PARAMETER NCAP_AFX(R,ALLYEAR,P)               'Change in capacity availability'         //;
  PARAMETER NCAP_AFSX(R,ALLYEAR,P,BD)           'Change in seasonal capacity availability'//;
  PARAMETER NCAP_AFM(R,ALLYEAR,P)               'Pointer to availity change multiplier'   //;
  PARAMETER NCAP_BND(REG,ALLYEAR,PRC,LIM)       'Bound on overall capacity in a period'   //;
  PARAMETER NCAP_BPME(REG,ALLYEAR,PRC)          'Back pressure mode efficiency (or total eff.)' //;
  PARAMETER NCAP_CDME(REG,ALLYEAR,PRC)          'Condensing mode efficiency'              //;
  PARAMETER NCAP_CEH(REG,ALLYEAR,PRC)           'Coefficient of electricity to heat'      //;
  PARAMETER NCAP_CHPR(REG,ALLYEAR,PRC,LIM)      'Combined heat:power ratio'               //;
  PARAMETER NCAP_CLED(REG,ALLYEAR,PRC,COM)      'Leadtime of a commodity before new capacity ready' //;
  PARAMETER NCAP_CLAG(REG,ALLYEAR,PRC,COM,IO)   'Lagtime of a commodity after new capacity ready' //;
  PARAMETER NCAP_COM(REG,ALLYEAR,PRC,COM,IO)    'Use (but +) of commodity based upon capacity' //;
  PARAMETER NCAP_COST(REG,ALLYEAR,PRC,CUR)      'Investment cost for new capacity'        //;
  PARAMETER NCAP_CPX(REG,ALLYEAR,PRC)           'Pointer to capacity transfer multiplier' //;
  PARAMETER NCAP_DRATE(REG,ALLYEAR,PRC)         'Process specific discount (hurdle) rate' //;
  PARAMETER NCAP_FDR(REG,ALLYEAR,PRC)           'Functional depreciation rate of process' //;
  PARAMETER NCAP_ELIFE(REG,ALLYEAR,PRC)         'Economic (payback) lifetime'             //;
  PARAMETER NCAP_FOM(REG,ALLYEAR,PRC,CUR)       'Fixed annual O&M costs'                  //;
  PARAMETER NCAP_FOMX(REG,ALLYEAR,PRC)          'Change in fixed O&M'                     //;
  PARAMETER NCAP_FOMM(REG,ALLYEAR,PRC)          'Pointer to fixed O&M change multiplier'  //;
  PARAMETER NCAP_FSUB(REG,ALLYEAR,PRC,CUR)      'Fixed tax on installed capacity'         //;
  PARAMETER NCAP_FSUBX(REG,ALLYEAR,PRC)         'Change in fixed tax'                     //;
  PARAMETER NCAP_FSUBM(REG,ALLYEAR,PRC)         'Pointer to fixed subsidy change multiplier' //;
  PARAMETER NCAP_FTAX(REG,ALLYEAR,PRC,CUR)      'Fixed tax on installed capacity'         //;
  PARAMETER NCAP_FTAXX(REG,ALLYEAR,PRC)         'Change in fixed tax'                     //;
  PARAMETER NCAP_FTAXM(REG,ALLYEAR,PRC)         'Pointer to fixed tax change multiplier'  //;
  PARAMETER NCAP_ICOM(REG,ALLYEAR,PRC,COM)      'Input of commodity for install of new capacity' //;
  PARAMETER NCAP_ILED(REG,ALLYEAR,PRC)          'Lead-time required for building a new capacity' //;
  PARAMETER NCAP_ISUB(REG,ALLYEAR,PRC,CUR)      'Subsidy for a new investment in capacity' //;
  PARAMETER NCAP_ITAX(REG,ALLYEAR,PRC,CUR)      'Tax on a new investment in capacity'     //;
  PARAMETER NCAP_ISPCT(REG,ALLYEAR,PRC)         'Subsidy as % of new investment cost'     //;
  PARAMETER NCAP_LCOST(REG,ALLYEAR,PRC)         '% labor cost of new investment'          //;
  PARAMETER NCAP_LFOM(REG,ALLYEAR,PRC)          '% labor cost of fixed O&M'               //;
  PARAMETER NCAP_PASTI(REG,ALLYEAR,PRC)         'Capacity install prior to study years'   //;
  PARAMETER NCAP_PASTY(REG,ALLYEAR,PRC)         'Buildup years for past investments'      //;
  PARAMETER NCAP_TLIFE(REG,ALLYEAR,PRC)         'Technical lifetime of a process'         //;
  PARAMETER NCAP_OLIFE(REG,ALLYEAR,PRC)         'Operating lifetime of a process';
  PARAMETER RCAP_BLK(REG,ALLYEAR,PRC)           'Retirement block size'                   //;
  PARAMETER RCAP_BND(REG,ALLYEAR,PRC,LIM)       'Retirement bounds';

* decommissioning of Capacity
  PARAMETER NCAP_DCOST(REG,ALLYEAR,PRC,CUR)     'Cost of decomissioning'                  //;
  PARAMETER NCAP_DLAG(REG,ALLYEAR,PRC)          'Delay to begin decomissioning'           //;
  PARAMETER NCAP_DLAGC(REG,ALLYEAR,PRC,CUR)     'Cost of decomissioning delay'            //;
  PARAMETER NCAP_DELIF(REG,ALLYEAR,PRC)         'Economic lifetime to pay for decomissioning' //;
  PARAMETER NCAP_DLIFE(REG,ALLYEAR,PRC)         'Time for the actual decomissioning'      //;
  PARAMETER NCAP_OCOM(REG,ALLYEAR,PRC,COM)      'Commodity release during decomissioning' //;
  PARAMETER NCAP_VALU(REG,ALLYEAR,PRC,COM,CUR)  'Value of material released during decomissioning' //;

* capacity installed
  PARAMETER NCAP_START(REG,PRC)                 'Start year for new investments' //;
  PARAMETER NCAP_SEMI(R,ALLYEAR,P)              'Semi-continuous capacity, lower bound' //;
  PARAMETER CAP_BND(REG,ALLYEAR,PRC,BD)         'Bound on total installed capacity in a period' //;

* general commodities
  PARAMETER COM_BNDNET(REG,ALLYEAR,COM,TS,LIM)      'Net bound on commodity (e.g., emissions)' //;
  PARAMETER COM_BNDPRD(REG,ALLYEAR,COM,TS,LIM)      'Limit on production of a commodity'       //;
  PARAMETER COM_CUMNET(REG,BOHYEAR,EOHYEAR,COM,LIM) 'Cumulative net bound on commodity (e.g. emissions)' //;
  PARAMETER COM_CUMPRD(REG,BOHYEAR,EOHYEAR,COM,LIM) 'Cumulative limit on production of a commodity' //;
  PARAMETER COM_CSTNET(REG,ALLYEAR,COM,TS,CUR)      'Cost on Net of commodity (e.g. emissions tax)' //;
  PARAMETER COM_CSTPRD(REG,ALLYEAR,COM,TS,CUR)      'Cost on production of a commodity'        //;
  PARAMETER COM_FR(REG,ALLYEAR,COM,TS)              'Seasonal distribution of a commodity'     //;
  PARAMETER COM_IE(REG,ALLYEAR,COM,TS)              'Seasonal efficiency of commodity'         //;
  PARAMETER COM_SUBNET(REG,ALLYEAR,COM,TS,CUR)      'Subsidy on a commodity net'               //;
  PARAMETER COM_SUBPRD(REG,ALLYEAR,COM,TS,CUR)      'Subsidy on production of a commodity net' //;
  PARAMETER COM_TAXNET(REG,ALLYEAR,COM,TS,CUR)      'Tax on a commodity net'                   //;
  PARAMETER COM_TAXPRD(REG,ALLYEAR,COM,TS,CUR)      'Tax on production of a commodity net'     //;
  PARAMETER COM_AGG(REG,ALLYEAR,COM,COM)            'Commodity aggregation parameter'          //;

* demands
  PARAMETER COM_BPRICE(REG,ALLYEAR,COM,TS,CUR)      'Base price of elastic demands'     //;
  PARAMETER COM_BQTY(REG,COM,TS)                    'Base quantity for elastic demands' //;
  PARAMETER COM_ELAST(REG,ALLYEAR,COM,TS,LIM)       'Elasticity of demand'              //;
  PARAMETER COM_ELASTX(REG,ALLYEAR,COM,BD)          'Elasticity shape of demand'        //;
  PARAMETER COM_PROJ(REG,ALLYEAR,COM)               'Demand baseline projection'        //;
  PARAMETER COM_STEP(REG,COM,LIM)                   'Step size for elastic demand'      //;
  PARAMETER COM_VOC(REG,ALLYEAR,COM,BD)             'Variance of elastic demand'        //;

* flow of commodities through processes
  PARAMETER FLO_BND(REG,ALLYEAR,PRC,CG,TS,BD)       'Bound on the flow variable'                         //;
  PARAMETER FLO_BDLVL(REG,ALLYEAR,PRC,CG,S,BD)      'Bound on the flow variable by hourly rate level'    //;
  PARAMETER FLO_COST(REG,ALLYEAR,PRC,COM,TS,CUR)    'Added variable O&M of using a commodity'            //;
  PARAMETER FLO_DELIV(REG,ALLYEAR,PRC,COM,TS,CUR)   'Delivery cost for using a commodity'                //;
  PARAMETER FLO_FEQ(REG,ALLYEAR,PRC,COM)            'Fossil equivalent of a commodity in a process'      //;
  PARAMETER FLO_FR(REG,ALLYEAR,PRC,COM,TS,LIM)      'Load-curve limitations for a process commodity flow'//;
  PARAMETER FLO_FUNC(REG,ALLYEAR,PRC,CG,CG,TS)      'Relationship between 2 (group of) flows'            //;
  PARAMETER FLO_FUNCX(REG,ALLYEAR,PRC,CG,CG)        'Change in FLO_FUNC/FLO_SUM by age'                  //;
  PARAMETER FLO_SHAR(REG,ALLYEAR,PRC,C,CG,TS,BD)    'Relationship between members of the same flow group'//;
  PARAMETER FLO_SUB(REG,ALLYEAR,PRC,COM,TS,CUR)     'Subsidy for the production/use of a commodity'      //;
  PARAMETER FLO_SUM(REG,ALLYEAR,PRC,CG,C,CG,TS)     'Multipier for commodity in cg1 where each is summed into cg2'//;
  PARAMETER FLO_TAX(REG,ALLYEAR,PRC,COM,TS,CUR)     'Tax on the production/use of a commodity'           //;
  PARAMETER FLO_CUM(REG,PRC,COM,ITEM,ITEM,LIM)      'Bound on cumulative flow'                           //;
  PARAMETER FLO_MARK(REG,ALLYEAR,PRC,COM,BD)        'Process-wise market share in total commodity production' //;
  PARAMETER PRC_MARK(REG,ALLYEAR,PRC,ITEM,C,LIM)    'Process group-wise market share' //;
  PARAMETER PRC_RESID(REG,ALLYEAR,PRC)              'Residual capacity available in each period' //;
  PARAMETER PRC_REFIT(REG,PRC,PRC)                  'Process with retrofit or life-extension';

* peak
  PARAMETER NCAP_PKCNT(REG,ALLYEAR,PRC,ALL_TS)      'Fraction of capacity contributing to peaking in time-slice TS' //;
  PARAMETER COM_PKRSV(REG,ALLYEAR,COM)              'Peaking reserve margin'   //;
  PARAMETER COM_PKFLX(REG,ALLYEAR,COM,TS)           'Peaking flux ratio'       //;
  PARAMETER FLO_PKCOI(REG,ALLYEAR,PRC,COM,ALL_TS)   'Factor increasing the average demand' //;

* Storage
  PARAMETER STG_EFF(REG,ALLYEAR,PRC)                'Storage efficiency'       //;
  PARAMETER STG_LOSS(REG,ALLYEAR,PRC,S)             'Annual energy loss from a storage technology' //;
  PARAMETER STG_CHRG(REG,ALLYEAR,PRC,S)             'Exogeneous charging of a storage technology ' //;
  PARAMETER STG_SIFT(R,ALLYEAR,P,C,S)               'Max load sifting in proportion to total load' //;
  PARAMETER STGOUT_BND(REG,ALLYEAR,PRC,C,S,BD)      'Bound on output-flow of storage process'      //;
  PARAMETER STGIN_BND(REG,ALLYEAR,PRC,C,S,BD)       'Bound on output-flow of storage process'      //;

* Process units
  PARAMETER PRC_ACTFLO(REG,ALLYEAR,PRC,CG)          'Convert from process activity to particular commodity flow' //;
  PARAMETER PRC_CAPACT(REG,PRC)                     'Factor for going from capacity to activity' //;
  PARAMETER PRC_GMAP(REG,PRC,ITEM)                  'User-defined groupings of processes' //;

* globals
  PARAMETER G_CHNGMONY(REG,ALLYEAR,CUR)             'Exchange rate for currency'  //;
  PARAMETER G_DRATE(REG,ALLYEAR,CUR)                'Discount rate for a currency'//;
  PARAMETER G_RFRIR(REG,ALLYEAR)                    'Riskfree real interest rate' //;
  PARAMETER G_YRFR(ALL_REG,TS)                      'Seasonal fraction of the year' //;
  PARAMETER TS_CYCLE(REG,TS)                        'Length of cycles below timeslice, in days' //;
  PARAMETER G_OFFTHD(ALLYEAR)                       'Threshold for OFF ranges';
  PARAMETER G_OVERLAP                               'Overlap of stepped solutions (in years)' / 0 /;
  PARAMETER REG_FIXT(ALL_R)                         'Year up to which periods are fixed';
  PARAMETER REG_BDNCAP(ALL_R,L)                     'Year up to which VAR_NCAPs are to be fixed';
  PARAMETER G_CUREX(CUR,CUR)                        'Global currency conversions';
  PARAMETER R_CUREX(ALL_REG,CUR,CUR)                'Regional currency conversions';

* trade of commodities
  PARAMETERS
    IRE_BND(ALL_R,ALLYEAR,COM,TS,ALL_REG,IE,BD)     'Limit on inter-reg exchange of commodity' //
    IRE_FLO(ALL_R,ALLYEAR,PRC,COM,ALL_R,COM,TS)     'Efficiency of exchange for inter-regional trade' //
    IRE_FLOSUM(REG,ALLYEAR,PRC,COM,TS,IE,COM,IO)    'Aux. consumption/emissions from inter-regional trade'//
    IRE_PRICE(REG,ALLYEAR,PRC,COM,TS,ALL_R,IE,CUR)  'Exogenous price of import/export' //
    IRE_XBND(ALL_REG,ALLYEAR,COM,TS,IE,BD)          'Limit on all (external and inter-regional) exchange of commodity' //
    IRE_CCVT(ALL_REG,COM,ALL_REG,COM)               'Commodity unit conversion factor between regions' //
    IRE_TSCVT(ALL_REG,ALL_TS,ALL_REG,ALL_TS)        'Identification and TS-conversion factor between regions' //;

* Shape and Multi
  PARAMETER SHAPE(J,AGE)                            'Shaping table'       //;
  PARAMETER MULTI(J,ALLYEAR)                        'Multiplier table'    //;

* Regional Cost bounds
  PARAMETERS
    REG_BNDCST(REG,ALLYEAR,COSTAGG,CUR,BD)          'Bound on regional costs by type'    //
    REG_CUMCST(REG,ALLYEAR,ALLYEAR,COSTAGG,CUR,BD)  'Cumulative bound on regional costs' //;

* User Constraints

  PARAMETER UC_RHS(UC_N,LIM)                        'Constant in user constraint'  //;
  PARAMETER UC_RHST(UC_N,ALLYEAR,LIM)               'Constant in user constraint'  //;
  PARAMETER UC_RHSR(ALL_REG,UC_N,LIM)               'Constant in user constraint'  //;
  PARAMETER UC_RHSS(UC_N,TS,LIM)                    'Constant in user constraint'  //;
  PARAMETER UC_RHSRT(ALL_REG,UC_N,ALLYEAR,LIM)      'Constant in user constraint'  //;
  PARAMETER UC_RHSRS(ALL_REG,UC_N,TS,LIM)           'Constant in user constraint'  //;
  PARAMETER UC_RHSRTS(ALL_REG,UC_N,ALLYEAR,TS,LIM)  'Constant in user constraint'  //;
  PARAMETER UC_RHSTS(UC_N,ALLYEAR,TS,LIM)           'Constant in user constraint'  //;

  PARAMETERS
    UC_FLO(UC_N,SIDE,ALL_REG,ALLYEAR,PRC,COM,TS)    'Multiplier of flow variables' //
    UC_ACT(UC_N,SIDE,ALL_REG,ALLYEAR,PRC,ALL_TS)    'Multiplier of activity variables' //
    UC_CAP(UC_N,SIDE,ALL_REG,ALLYEAR,PRC)           'Multiplier of capacity variables' //
    UC_NCAP(UC_N,SIDE,ALL_REG,ALLYEAR,PRC)          'Multiplier of VAR_NCAP variables' //
    UC_COMCON(UC_N,SIDE,ALL_REG,ALLYEAR,COM,TS)     'Multiplier of VAR_COMCON variables' //
    UC_COMPRD(UC_N,SIDE,ALL_REG,ALLYEAR,COM,TS)     'Multiplier of VAR_COMPRD variables' //
    UC_COMNET(UC_N,SIDE,ALL_REG,ALLYEAR,COM,TS)     'Multiplier of VAR_COMNET variables' //
    UC_IRE(UC_N,SIDE,ALL_REG,ALLYEAR,PRC,COM,TS,IE) 'Multiplier of inter-regional exchange variables' //
    UC_CUMACT(UC_N,ALL_REG,PRC,ITEM,ITEM)           'Multiplier of cumulative process activity variable' //
    UC_CUMFLO(UC_N,ALL_REG,PRC,COM,ITEM,ITEM)       'Multiplier of cumulative process flow variable' //
    UC_CUMCOM(UC_N,ALL_REG,COM_VAR,COM,ITEM,ITEM)   'Multiplier of cumulative commodity variable' //
    UC_UCN(UC_N,SIDE,ALL_R,ALLYEAR,UC_N)            'Multiplier of user constraint variable' //
    UC_TIME(UC_N,ALL_R,ALLYEAR)                     'Multiplier of time in model periods (years)' //;
""",
            )

        def extensions_and_system_scalars() -> None:
            """Extensions & System scalars"""
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
* Damage input parameters
  PARAMETER DAM_COST(REG,ALLYEAR,COM,CUR) 'Marginal damage cost of emissions';
  PARAMETER DAM_BQTY(REG,COM)             'Base quantity of emissions'           //;
  PARAMETER DAM_ELAST(REG,COM,LIM)        'Elasticity of damage cost';
  PARAMETER DAM_STEP(REG,COM,LIM)         'Step number for emissions up to base' //;
  PARAMETER DAM_VOC(REG,COM,LIM)          'Variance of emissions'                //;
* Experimental parameters
  PARAMETER DAM_TQTY(REG,ALLYEAR,COM)     'Base quantity of emissions by year'   //;
  PARAMETER DAM_TVOC(REG,ALLYEAR,COM,LIM) 'Variance of emissions by year'        //;
  PARAMETER DAM_COEF(REG,ALLYEAR,COM,S)   'Coefficient from commodity to damage' //;
* Parameters used in report routine
  PARAMETER RPT_OPT(ITEM,J)               'Reporting options'                    //;
  PARAMETER CST_DAM(REG,T,COM)            'Damage costs'                         //;
  PARAMETER CM_RESULT(ITEM,ITEM,ALLYEAR)  'Climate module results'               //;
  PARAMETER CM_MAXC_M(ITEM,ALLYEAR)       'Shadow price of climate constraint'   //;
  PARAMETER TM_RESULT(ITEM,R,ALLYEAR)     'MACRO results'                        //;

* Scalars
  SCALARS MIYR_V1 /0/, MIYR_VL /0/, PYR_V1 /0/;
  SCALAR  MY_F /0/, F /0/, Z /0/, CNT /0/, DFUNC /0/, DONE /0/, IFQ /1/;
* maximum NCAP_ILED+NCAP_TLIFE+NCAP_DLAG+NCAP_DLIFE+NCAP_DELIF
  SCALAR  DUR_MAX / 0 /;
* first and last given data value to be extrapolated
  SCALAR FIRST_VAL /0/, LAST_VAL /0/, MY_FYEAR /0/;
""",
            )

            # * Placeholder for interpolation control option
            # $ SETGLOBAL DFLBL '0'
            self.env.set_global("dflbl", "0")
            dflbl = self.env.dflbl
            self.tc.enqueue(self.assign_yearval, dflbl=dflbl)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
SET LASTLL(LL) /{self.env.dflbl}/;
""",
            )
            self.tc.enqueue(self.assign_z)

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=r"""
* Interpolation defaults
SET INT_DEFAULT(*) //, UNCD1(*);
PARAMETER IE_DEFAULT(*) //;

    """,
            )

        def initializations_for_blending() -> None:
            """*GG* V07_2 Initializations for BLENDing"""
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code="""
* user provided Sets & Scalars
     SET BLE(COM)         //;
     SET OPR(COM)         //;
     SET SPE(*)           //;
     SET REF(R,PRC)       //;
     PARAMETER REFUNIT(R) //;

* internal Sets
     SET CVT  / DENS, WCV, VCV, SLF /;

* user provided Parameters
     PARAMETER CONVERT(OPR,CVT)              //;
     PARAMETER BL_START(R,COM,SPE)           //;
     PARAMETER BL_UNIT(R,COM,SPE)            //;
     PARAMETER BL_TYPE(R,COM,SPE)            //;
     PARAMETER BL_SPEC(R,COM,SPE)            //;
*     PARAMETER TBL_SPEC(COM,SPE,YEAR)       //;
     PARAMETER BL_COM(R,COM,OPR,SPE)         //;
*     PARAMETER TBL_COM(COM,SPE,OPR,YEAR)    //;
     PARAMETER BL_INP(R,COM,COM)             //;
*     PARAMETER TBL_INP(COM,SPE,COM,YEAR)    //;
     PARAMETER BL_VAROMC(R,COM,CUR)          //;
*     PARAMETER TBL_VAROM(COM,SPE,YEAR)      //;
     PARAMETER BL_DELIVC(R,COM,COM,CUR)      //;
*     PARAMETER TBL_DELIV(COM,SPE,COM,YEAR)  //;
     PARAMETER ENV_BL(R,COM,COM,OPR,YEAR)    //;
     PARAMETER PEAKDA_BL(R,COM,YEAR)         //;

* internal Parameters
     PARAMETER RU_CVT(R,BLE,SPE,OPR)         //;
     PARAMETER RU_FEQ(R,COM,YEAR)            //;

  PARAMETER OBJ_BLNDV(R,YEAR,C,C,CUR) 'annual variable costs for blending' //;
""",
            )

        def control_section() -> None:
            """CONTROL section"""
            self.env.set_global("gdxpath", "")
            # TODO: $ IFI EXIST gamssave\nul $SETGLOBAL GDXPATH 'gamssave/'
            self.env.set_global("sysprefix", "")
            self.env.set_global("prf", "FILE=1")

            # Alternative objective controls
            Parameter(container=m, name="ALTOBJ", records=1)
            objective = self.env.obj
            self.tc.enqueue(self.assign_alternative_objective, objective=objective)

            if self.env.macro == "YES":
                self.tc.enqueue(self.check_macro)
            if self.env.validate == "YES":
                self.tc.enqueue(self.validate)

            # $SETGLOBAL CTST
            self.env.set_global("ctst", "")
            if self.env.obj == "MOD":
                self.env.set_global("oblong", "YES")
            elif self.env.obj == "ALT":
                self.env.set_global("ctst", "**EPS")

            if self.env.oblong == "YES":
                self.env.set_global("ctst", "**0")

            if self.env.obj == "LIN":
                self.env.set_global("ctst", "**EPS")

            # $IFI '%OBLONG%%OBJ%'==YESALT $SETGLOBAL VARCOST LIN
            # $IFI '%OBLONG%%OBJ%'==YESALT ALTOBJ = -2;
            if self.env.objlong == "YES" and self.env.obj == "ALT":
                self.env.set_global("varcost", "LIN")
                self.tc.enqueue(self.assign_alternative_objective_long)

            # Stochastic extension
            # $IFI %SENSIS%==YES $SETLOCAL STAGES yes
            if self.env.sensis == "YES":
                self.env.set_local("stages", "YES")
            # $IFI %SPINES%==YES $SETLOCAL STAGES YES
            if self.env.spines == "YES":
                self.env.set_local("stages", "YES")
            # $IFI %STAGES%==YES $BATINCLUDE initmty.stc
            if self.tc.test_run:
                self.tc.save_test_state(
                    env=self.env, checkpoint="initmty_mod_prior_initmty_stc"
                )
            if self.env.stages == "YES":
                self.include(InitmtyStc(self.tc, self.env))

            # * Stepped extensions etc.
            # SET ITEM / "%FIXBOH%", "%TIMESTEP%", "%SPOINT%" /;
            # Remember: ITEM is a UniverseSet
            itemadd_records = [self.env.fixboh, self.env.timestep, self.env.spoint]
            self.add_records_to_universe_item(records=itemadd_records)

            self.env.set_global("rpoint", "NO")

            if self.env.is_set("spoint"):
                spoint = self.env.spoint
                self.tc.enqueue(self.catch_invalid_spoint_control, spoint=spoint)

            if self.env.is_set("timestep"):
                timestep = self.env.timestep
                self.tc.enqueue(self.catch_invalid_timestep_control, timestep=timestep)

            if self.env.is_set("fixboh"):
                fixboh = self.env.fixboh
                self.tc.enqueue(self.catch_invalid_fixboh_control, fixboh=fixboh)

            # $IF SET FIXBOH $SETGLOBAL STEPPED -
            if self.env.is_set("fixboh"):
                self.env.set_global("stepped", "-")
            # $IF SET TIMESTEP $SETGLOBAL STEPPED +
            if self.env.is_set("timestep"):
                self.env.set_global("stepped", "+")
            # $IF SET STEPPED $SETGLOBAL VAR_UC YES
            if self.env.is_set("stepped"):
                self.env.set_global("var_uc", "YES")
            # TODO: $IF %SYSTEM.LICENSELEVEL%==2 $SETGLOBAL VAR_UC YES

        def other_extensions() -> None:
            """Other extensions to TIMES code"""
            # Auto-activation of discrete capacity extensions
            # $IF %DSCAUTO%==YES $SETGLOBAL DSC YES
            if self.env.dscauto == "YES":
                self.env.set_global("dsc", "YES")
            # $IF %PGPRIM%==ACT  $SETGLOBAL RETIRE 'YES' SETGLOBAL DSCAUTO Yes
            if self.env.pgprim == "ACT":
                self.env.set_global("retire", "YES")
                self.env.set_global("dscauto", "Yes")
            # $IFI %DSC%==YES    $KILL RCAP_BLK
            if self.env.dsc == "YES":
                self.tc.add_gams_code(module=self, phase="init", code="$KILL RCAP_BLK")

            # Initialize list of standard extensions to be loaded
            # $SET VDA 'YES' SETGLOBAL EXTEND
            self.env.set_scoped("vda", "YES")

            # Load all extension declarations
            def collect_active_extensions() -> None:
                """Collect active extensions based on various env variables
                will be collected and passed to MainExtMod"""
                self.env.set_global("extend", "")

                # Add recognized extensions if defined
                # $IFI '%ECB%'==YES   $SETGLOBAL EXTEND '%EXTEND% ECB'
                if self.env.ecb == "YES":
                    # There is no initmty.ecb
                    self.env.set_global("extend", f"{self.env.extend} ECB".strip())
                # $IFI '%MACRO%'==CSA $SETGLOBAL EXTEND '%EXTEND% MSA'
                # $IFI '%MACRO%'==MSA $SETGLOBAL EXTEND '%EXTEND% MSA'
                if self.env.macro in ["CSA", "MSA"]:
                    self.env.set_global("extend", f"{self.env.extend} MSA".strip())
                # $IFI '%MACRO%'==MLF $SETGLOBAL EXTEND '%EXTEND% MLF'
                elif self.env.macro == "MLF":
                    self.env.set_global("extend", f"{self.env.extend} MLF".strip())

                if self.env.etl == "YES":
                    self.env.set_global("extend", f"{self.env.extend} ETL".strip())

                if self.env.cli == "YES":
                    self.env.set_global("extend", f"{self.env.extend} CLI".strip())

                if self.env.dsc == "YES":
                    self.env.set_global("extend", f"{self.env.extend} DSC".strip())

                if self.env.vda == "YES":
                    self.env.set_global("extend", f"{self.env.extend} VDA".strip())

                if self.env.abs == "YES":
                    self.env.set_global("extend", f"{self.env.extend} ABS".strip())

                if self.env.mca == "YES":
                    self.env.set_global("extend", f"{self.env.extend} MCA".strip())
                    # There is no initmty.mca
                    raise Exception("No module initmty MCA")

                # Finally, add args %1...%6 to list of extensions:
                # $SETGLOBAL EXTEND %EXTEND% %1 %2 %3 %4 %5 %6
                parts = [
                    self.env.extend,
                    self.arg1,
                    self.arg2,
                    self.arg3,
                    self.arg4,
                    self.arg5,
                    self.arg6,
                ]
                extend = " ".join(p.strip() for p in parts if p and p.strip())
                self.env.set_global("extend", extend)

            collect_active_extensions()

            if self.tc.test_run:
                self.tc.save_test_state(
                    env=self.env, checkpoint="initmty_mod_prior_main_ext_mod"
                )

            # $BATINCLUDE main_ext.mod initmty %EXTEND%
            extensions = {
                "ABS": InitmtyAbs,
                "CLI": InitmtyCli,
                "DSC": InitmtyDsc,
                "ETL": InitmtyEtl,
                "MLF": InitmtyMlf,
                "MSA": InitmtyMsa,
                "STC": InitmtyStc,
                "TM": InitmtyTm,
                "VDA": InitmtyVda,
            }
            requested_exts = set(self.env.extend.split())
            include_extension(
                module=self,
                extensions=extensions,
                requested_exts=requested_exts,
                source="initmty",
            )

            # $SET VAR VARIABLE OBJZ
            self.env.set_scoped("var", "VARIABLE OBJZ")
            # $IF %DATAGDXI%%INTEXT_ONLY%==YESyes $SET VAR *
            if self.env.datagdxi == "YES" and self.env.intext_only == "YES":
                self.env.set_scoped("var", "*")
            self.include(
                ErrStatMod(
                    tc=self.tc,
                    env=self.env,
                    arg1="$IF NOT ERRORFREE",
                    arg2="ABORT",
                    arg3="Errors in Compile",
                    arg4=self.env.var,
                    arg5=": Required _TIMES.g00 Restart File Missing",
                )
            )
            # $IF ERRORFREE $BATINCLUDE err_stat.mod '$IF NOT ERRORFREE' ABORT 'Errors in Compile' '%VAR%' ': Required _TIMES.g00 Restart File Missing'
            self.include(
                ErrStatMod(
                    tc=self.tc,
                    env=self.env,
                    arg1="$IF NOT ERRORFREE",
                    arg2="ABORT",
                    arg3="Errors in Compile",
                    arg4=f"{self.env.var}",
                    arg5=": Required _TIMES.g00 Restart File Missing",
                )
            )

        def call_macro_initmty_tm() -> None:
            if self.tc.test_run:
                self.tc.save_test_state(
                    env=self.env, checkpoint="initmty_mod_prior_initmty_tm"
                )
            if not self.env.is_set("macro"):
                self.env.set_global("macro", "N")
            if self.env.macro == "YES":
                self.include(InitmtyTm(tc=self.tc, env=self.env))
            if self.env.datagdxi == "YES":
                self.env.set_global("datagdx", "YES")
                if self.env.intext_only == "YES":
                    self.env.set_scoped("datagdx", "NO")

            # Load data from GDX if DATAGDX set and %RUN_NAME%~DATA exists
            # $ IF NOT SET DATAGDX $GOTO RUN
            if not self.env.is_set("datagdx"):
                return
            # $ IF NOT %G2X6%==YES $GOTO RUN
            if self.env.g2x6 != "YES":
                return
            # $ IF NOT SET RUN_NAME $SETNAMES "%SYSTEM.INCPARENT%" . RUN_NAME .
            if not self.env.is_set("run_name"):
                source_file = Path(__file__)
                self.env.set_scoped("run_name", source_file.stem)
            self.env.set_scoped("tmp", "0")

            # $ IF EXIST %RUN_NAME%~data.gdx $SET TMP %RUN_NAME%~data
            # GAMS: %RUN_NAME%~data.gdx
            target_file = Path(f"{self.env.run_name}~data.gdx")
            # IF EXIST
            if target_file.exists():
                # $SET TMP %RUN_NAME%~data
                self.env.set_scoped("tmp", f"{self.env.run_name}")

            # $ IFI %DATAGDXI%%DATAGDX%==YESNO
            # $ IF EXIST _dd_.gdx $SET TMP _dd_
            if (
                self.env.datagdxi == "YES"
                and self.env.datagdx == "NO"
                and Path("_dd_.gdx").exists()
            ):
                self.env.set_scoped("tmp", "_dd_")

            if self.env.tmp == "0":
                return

            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=rf"""
$ hiddencall gdxdump {self.env.tmp}.gdx NODATA > _dd_.dmp
$ hiddencall sed "/^\(Alias\|[^($]*(\*) Alias\|[^$].*empty *$\)/{{N;d;}}; /^\([^$].*$\|$\)/d; s/\$LOAD.. /\$LOAD /I" _dd_.dmp > _dd_.dd
$ INCLUDE _dd_.dd
$ hiddencall rm -f _dd_.dmp
$ TITLE %SYSTEM.TITLE%#
$ GDXIN
""",
            )

            if self.env.var == "*":
                self.include(MainDrvMod(self.tc, self.env, arg1="mod"))
                self.tc.add_gams_code(module=self, phase="init", code="$stop")

        set_section()
        parameters_section()
        extensions_and_system_scalars()
        initializations_for_blending()
        control_section()
        other_extensions()
        call_macro_initmty_tm()

    def version_control(self) -> None:
        # $IF NOT FUNTYPE gamsversion $ABORT TIMES Version 4.8 and above Requires GAMS 23.0 or above!
        self.env.set_global("g2x6", "YES")
        self.env.set_global("obmac", "YES")

    def assign_yearval(self, dflbl: str) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=f"YEARVAL('{dflbl}') = 0;",
        )

    def assign_z(self) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="Z=SUM(LASTLL(LL),ORD(LL)); ABORT$(Z NE CARD(LL)) 'FATAL';",
        )

    def assign_alternative_objective(self, objective: str) -> None:
        # Alternative objective controls
        alt_obj = self.tc.container["ALTOBJ"]
        if objective == "STD":
            alt_obj[...] = 0
        elif objective == "ALT":
            alt_obj[...] = 2
        elif objective == "LIN":
            alt_obj[...] = 3

    def check_macro(self) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="IF(ALTOBJ>1,ABORT 'MACRO Cannot be used with Alternative Objective');",
        )

    def validate(self) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="IF(ALTOBJ>1,ABORT 'VALIDATE Cancels Alternative Objective'); ALTOBJ=0;",
        )

    def assign_alternative_objective_long(self) -> None:
        alt_obj = self.tc.container["ALTOBJ"]
        alt_obj[...] = -2

    def catch_invalid_spoint_control(self, spoint: str) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=f"IF((NOT J('{spoint}'))$(NOT SAMEAS('{spoint}','YES')), ABORT 'Invalid Control: SPOINT');",
        )

    def catch_invalid_timestep_control(self, timestep: str) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=f"IIF(NOT AGE('{timestep}'), ABORT 'Invalid Control: TIMESTEP');",
        )

    def catch_invalid_fixboh_control(self, fixboh: str) -> None:
        phase: GamsPhase = "run"
        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code=f"IF(NOT ALLYEAR('{fixboh}'), ABORT 'Invalid Control: FIXBOH');",
        )
