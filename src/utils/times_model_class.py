# times_model_class.py
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, ParamSpec

from gamspy import (
    Alias,
    Container,
    Equation,
    Model,
    Options,
    Parameter,
    Set,
    UniverseAlias,
    Variable,
)

from core.base_class import GamsClass
from utils.config import RunConfig
from utils.macros import macro_config

if TYPE_CHECKING:
    from core.pp_qaput_mod import QALogger
    from utils.compile_environment import CompileEnvironment

GamsPhase = Literal["init", "run"]
P = ParamSpec("P")


@dataclass(slots=True)
class TimesModelClass:
    """
    Central orchestrator / shared state ("tc") for the TIMES model embedding workflow.
    """

    # REQUIRED ARGUMENTS
    env: CompileEnvironment
    config: RunConfig
    output_compile: Path
    output_execute: Path
    output_convert: Path
    test_run: bool
    solve: bool
    solve_options: Options
    pp_qaput_logger: QALogger

    # AUTO-GENERATED FACTORIES
    execution_list: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = (
        field(default_factory=list)
    )
    compile_states: dict[str, Any] = field(default_factory=dict)
    _modules: list[GamsClass] = field(default_factory=list)
    assigned_symbols: set[Set | Parameter | Variable] = field(default_factory=set)

    # POST-INIT VARIABLES
    logger: logging.Logger = field(init=False)
    container: Container = field(init=False)
    # Live %MODEL_NAME%.MODELSTAT of the most recently built Model, see
    # core.utils.model_status_symbol
    model_status_GP: Parameter = field(init=False)

    # region TIMES symbols
    allts: Set = None  # type: ignore[assignment] # [*] ALL_TS: The universe for time-slices
    rts: Alias = None  # type: ignore[assignment] # [*] RTS
    phantom: Set = None  # type: ignore[assignment] # [*] PHANTOM:
    item: UniverseAlias = None  # type: ignore[assignment] # [*] ITEM: Aliased with *
    name: UniverseAlias = None  # type: ignore[assignment] # [*] NAME: Aliased with *
    Clvt: Set = None  # type: ignore[assignment] # [*] CLVT
    bohyear: Set = None  # type: ignore[assignment] # [*] BOHYEAR: BOH + years
    allyear: Set = None  # type: ignore[assignment] # [*] ALLYEAR: All Years
    yearval: Parameter = None  # type: ignore[assignment] # [allyear] YEARVAL: Value of each year
    eohyear: Set = None  # type: ignore[assignment] # [*] EOHYEAR: 'BOH/EOH' + years
    beoh: Parameter = None  # type: ignore[assignment] # [*] BEOH: BOH / EOH offset
    Periodyr: Set = None  # type: ignore[assignment] # [allyear,allyear] PERIODYR: All years in each period
    Annual: Set = None  # type: ignore[assignment] # [allts] ANNUAL: Annual identifier
    tslvl: Set = None  # type: ignore[assignment] # [*] TSLVL: Timeslice levels
    tslvlnum: Parameter = None  # type: ignore[assignment] # [tslvl] TSLVLNUM: Timeslice level values
    year: Alias = None  # type: ignore[assignment] # [*] YEAR: Aliased with ALLYEAR
    ll: Alias = None  # type: ignore[assignment] # [*] LL: Aliased with ALLYEAR
    impexp: Set = None  # type: ignore[assignment] # [*] IMPEXP: Imports/Exports
    imp: Set = None  # type: ignore[assignment] # [*] IMP: Imports
    xpt: Set = None  # type: ignore[assignment] # [*] XPT: Exports
    inout: Set = None  # type: ignore[assignment] # [*] IN_OUT: Input/Output
    ie: Alias = None  # type: ignore[assignment] # [*] IE: Aliased with IMPEXP
    io: Alias = None  # type: ignore[assignment] # [*] IO: Aliased with IN_OUT
    lim: Set = None  # type: ignore[assignment] # [*] LIM: Limit Types
    BndType: Set = None  # type: ignore[assignment] # [lim] BND_TYPE: Bound Types
    lA: Alias = None  # type: ignore[assignment] # [*] L: Aliased with LIM
    limtype: Alias = None  # type: ignore[assignment] # [*] LIM_TYPE: Aliased with LIM
    bd: Alias = None  # type: ignore[assignment] # [*] BD: Aliased with BND_TYPE
    upt: Set = None  # type: ignore[assignment] # [*] UPT: Start-up types
    age: Set = None  # type: ignore[assignment] # [*] AGE: Age for SHAPEing
    j: Set = None  # type: ignore[assignment] # [*] J: Supply/demand steps 1*COM_STEP and SHAPE/MULTI
    jj: Alias = None  # type: ignore[assignment] # [*] JJ: Aliased with J
    allreg: Set = None  # type: ignore[assignment] # [*] ALL_REG: External + Internal Regions
    Reg: Set = None  # type: ignore[assignment] # [allreg] REG: Region
    allr: Alias = None  # type: ignore[assignment] # [*] ALL_R: Aliased with ALL_REG
    r: Alias = None  # type: ignore[assignment] # [*] R: Aliased with REG
    comgrp: Set = None  # type: ignore[assignment] # [*] COM_GRP: Commodities & Groups
    cg: Alias = None  # type: ignore[assignment] # [*] CG: Aliased with COM_GRP
    cg1: Alias = None  # type: ignore[assignment] # [*] CG1: Aliased with COM_GRP
    cg2: Alias = None  # type: ignore[assignment] # [*] CG2: Aliased with COM_GRP
    Com: Set = None  # type: ignore[assignment] # [comgrp] COM: Commodities
    c: Alias = None  # type: ignore[assignment] # [*] C: Aliased with COM
    com1: Alias = None  # type: ignore[assignment] # [*] COM1: Aliased with COM
    com2: Alias = None  # type: ignore[assignment] # [*] COM2: Aliased with COM
    prc: Set = None  # type: ignore[assignment] # [*] PRC: Processes
    p: Alias = None  # type: ignore[assignment] # [*] P: Aliased with PRC
    cur: Set = None  # type: ignore[assignment] # [*] CUR: Currencies = c$
    curr: Alias = None  # type: ignore[assignment] # [*] CURR: Aliased with CUR
    allsow: Set = None  # type: ignore[assignment] # [*] ALLSOW: State-of-the-World
    Sow: Set = None  # type: ignore[assignment] # [allsow] SOW: State-of-the-World
    w: Alias = None  # type: ignore[assignment] # [*] W: Aliased with SOW
    side: Set = None  # type: ignore[assignment] # [*] SIDE: LHS and RHS of an equation
    uc_sign: Parameter = None  # type: ignore[assignment] # [side] UC_SIGN: Sign of LHS and RHS expression
    comvar: Set = None  # type: ignore[assignment] # [*] COM_VAR:
    CovMap: Set = None  # type: ignore[assignment] # [*,*] COV_MAP:
    ucname: Set = None  # type: ignore[assignment] # [*] UC_NAME: Allowed parameters in user-constraints
    UcCost: Set = None  # type: ignore[assignment] # [ucname] UC_COST: UC cost attributes
    UcMapcost: Set = None  # type: ignore[assignment] # [UcCost,ucname] UC_MAPCOST: Compatibility map for cost attributes
    UcAnnul: Set = None  # type: ignore[assignment] # type: ignore[assignment] # [ucname] UC_ANNUL:
    UcDynt: Set = None  # type: ignore[assignment] # [ucname] UC_DYNT:
    ucnumber: Set = None  # type: ignore[assignment] # [*] UC_NUMBER: Determines way of handling REG,T and TS
    UcPerds: Set = None  # type: ignore[assignment] # [ucname] UC_PERDS:
    UcNewflo: Set = None  # type: ignore[assignment] # [ucname] UC_NEWFLO:
    ucgrptype: Set = None  # type: ignore[assignment] # [*] UC_GRPTYPE: Type of components within UC_GRP
    costagg: Set = None  # type: ignore[assignment] # [*] COSTAGG: Types of cost aggregations
    costcat: Alias = None  # type: ignore[assignment] # [*] COSTCAT: Aliased with COSTAGG
    costype: Alias = None  # type: ignore[assignment] # [*] COSTYPE: Aliased with UC_COST
    dump0: Parameter = None  # type: ignore[assignment] # DUMP0:
    optfileid: Parameter = None  # type: ignore[assignment] # OPTFILEID:
    units: Set = None  # type: ignore[assignment] # [*] UNITS: Units
    u: Alias = None  # type: ignore[assignment] # [*] U: Aliased with UNITS
    UnitsCom: Set = None  # type: ignore[assignment] # [units] UNITS_COM: Commodity Units
    UnitsCap: Set = None  # type: ignore[assignment] # [units] UNITS_CAP: Capacity Units
    UnitsAct: Set = None  # type: ignore[assignment] # [units] UNITS_ACT: Activity Units
    UnitsMony: Set = None  # type: ignore[assignment] # [units] UNITS_MONY: Monatary Units
    g_unca: Parameter = None  # type: ignore[assignment] # [units,UnitsAct] G_UNCA: Cap-to-Act conversions
    ComType: Set = None  # type: ignore[assignment] # [comgrp] COM_TYPE: List of main commodity types groups
    PgSmap: Set = None  # type: ignore[assignment] # [cg,j,cg] PG_SMAP: Map from PG to SPG
    curgrp: Set = None  # type: ignore[assignment] # [*] CUR_GRP: List of currency groups
    demsect: Set = None  # type: ignore[assignment] # [*] DEM_SECT: List of demand sectors
    envgrp: Set = None  # type: ignore[assignment] # [*] ENV_GRP: List of emission groups
    fingrp: Set = None  # type: ignore[assignment] # [*] FIN_GRP: List of financial groups
    matgrp: Set = None  # type: ignore[assignment] # [*] MAT_GRP: List of material groups
    mattype: Set = None  # type: ignore[assignment] # [*] MAT_TYPE: List of material types
    nrgform: Set = None  # type: ignore[assignment] # [*] NRG_FORM: List of energy forms
    nrggrid: Set = None  # type: ignore[assignment] # [*] NRG_GRID: List of grid types
    nrgtype: Set = None  # type: ignore[assignment] # [*] NRG_TYPE: List of energy types
    prcgrp: Set = None  # type: ignore[assignment] # [*] PRC_GRP: List of process groups
    prcrsourc: Set = None  # type: ignore[assignment] # [*] PRC_RSOURC: List of domestic resource supply groups
    CmVar: Alias = None  # type: ignore[assignment] # [*] CM_VAR: CM_HISTS

    uc_cli: Parameter = None  # type: ignore[assignment] # [UC_N,SIDE,REG,ALLYEAR,CM_ITEM] UC_CLI: Climate variable
    g_dyear: Parameter = None  # type: ignore[assignment] # G_DYEAR: Year to discount to
    g_iledno: Parameter = None  # type: ignore[assignment] # G_ILEDNO: 1/threshold at which to ignore ILED
    g_tlife: Parameter = None  # type: ignore[assignment] #  G_TLIFE: Default technology life if not provided
    g_vint: Parameter = None  # type: ignore[assignment] #  G_VINT: % annual change in input data for vintaging

    bs_capact: Parameter = None  # type: ignore[assignment] # [r] BS_CAPACT: Conversion factor from exogenous reserve demand to activity
    bs_rtype: Parameter = None  # type: ignore[assignment] # [r,c] BS_RTYPE: Types of reserve commodities, positive or negative 1-4
    bs_demdet: Parameter = None  # type: ignore[assignment] # [r, year, rsp, c, s] BS_DEMDET: Deterministic demands of reserves - EXOGEN and WMAXSI
    bs_stime: Parameter = None  # type: ignore[assignment] # [r, p, Com, bd] BS_STIME: Minimum times for reserve provision from storage (hours)
    bs_detwt: Parameter = None  # type: ignore[assignment] # [r, year, c] BS_DETWT: Weights for deterministic reserve demands
    bs_lambda: Parameter = None  # type: ignore[assignment] # [r, year, c] BS_LAMBDA: Fudge factors for dependencies in reserve requirements
    bs_sigma: Parameter = None  # type: ignore[assignment] # [r, year, c, item, s] BS_SIGMA: Standard deviation of imbalance source ITEM
    bs_omega: Parameter = None  # type: ignore[assignment] # [Reg, year, Com, ts] BS_OMEGA: Indicator of how to define reserve demand from deterministic and probabilistic component
    bs_maint: Parameter = None  # type: ignore[assignment] # [r, year, p, s] BS_MAINT: Continuous maintenance duration (hours)
    bs_rmax: Parameter = None  # type: ignore[assignment] # [r, year, p, c, s] BS_RMAX: Maximum contribution of process p to provision of reserve c as a fraction of capacity
    bs_delta: Parameter = None  # type: ignore[assignment] # [r, year, c, s] BS_DELTA: Calibration parameters for probabilistic reserve demands
    bs_share: Parameter = None  # type: ignore[assignment] # [r, year, c, item, lA] BS_SHARE: Share of group reserve provision
    bs_bndprs: Parameter = None  # type: ignore[assignment] # [r, year, p, c, s, lA] BS_BNDPRS: Bound on process reserve provision

    flo_mrkcon: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc, Com, ts, bd] FLO_MRKCON: Bound on the share of a flow in the total consumption of a commmodity
    flo_mrkprd: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc, Com, ts, bd] FLO_MRKPRD: Bound on the share of a flow in the total production of a commmodity

    EctChp: Set = None  # type: ignore[assignment]   # [Reg, prc] ECT_CHP: Set of extraction condensing CHP plants
    EctElc: Set = None  # type: ignore[assignment]   # [Reg, prc, Com] ECT_ELC: Electricity commodity of extraction condensing CHP plants
    EctDht: Set = None  # type: ignore[assignment]   # [Reg, prc, Com] ECT_DHT: Heat commodity of extraction condensing CHP plants
    EctCgout: Set = None  # type: ignore[assignment] # [Reg, prc, comgrp] ECT_CGOUT: Output commodity group ELC+HEAT of ECT CHP plant
    EctCgin: Set = None  # type: ignore[assignment] # [Reg, prc, comgrp] ECT_CGIN: Fuel input commodity group of ECT CHP plant

    ect_inp2elc: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc] ECT_INP2ELC: Conversion factor from input capacity to ELC capacity in BPT point
    ect_inp2dht: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc] ECT_INP2DHT: Conversion factor from input capacity to heat capacity in BPT point
    ect_inp2con: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc] ECT_INP2CON: Conversion factor from input capacity to heat capacity in BPT point
    ect_reh: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc] ECT_REH: Ratio of electricity to heat in brackpressure point
    ect_afcon: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc, bd] ECT_AFCON: Availability of condensing mode operation of extraction condensing CHP
    ect_afbpt: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc, bd] ECT_AFBPT: Availability of backpressure mode operation of extraction condensing CHP

    BsK: Set = None  # type: ignore[assignment] # [item] BS_K: Sources of imbalance or provision
    BsRtk: Set = None  # type: ignore[assignment] # [r, t, item] BS_RTK: Sources of imbalances by period
    BsComts: Set = None  # type: ignore[assignment] # [r, c, s] BS_COMTS: Reserve commodity timeslices
    BsApos: Set = None  # type: ignore[assignment] # [r, c] BS_APOS: Positive reserve commodities
    BsAneg: Set = None  # type: ignore[assignment] # [r, c] BS_ANEG: Negative reserve commodities
    BsAbd: Set = None  # type: ignore[assignment] # [r, c, lA] BS_ABD: Reserve commodities by direction
    BsBsc: Set = None  # type: ignore[assignment] # [r, p, c] BS_BSC: Reserve provisions by process
    BsUpl: Set = None  # type: ignore[assignment] # [r, p, lA] BS_UPL: Maximum ramping rate indicator
    BsUpc: Set = None  # type: ignore[assignment] # [r, p, tsl, lA] BS_UPC: Minimum uptime/downtime indicator
    BsTop: Set = None  # type: ignore[assignment] # [r, p, c, io] BS_TOP: Topology for imbalance process
    BsEndp: Set = None  # type: ignore[assignment] # [r, p] BS_ENDP: Reserve providion by demand
    BsSupp: Set = None  # type: ignore[assignment] # [r, p] BS_SUPP: Reserve provision by generation
    BsStgp: Set = None  # type: ignore[assignment] # [r, p] BS_STGP: Reserve provision by storage
    BsNegp: Set = None  # type: ignore[assignment] # [r, p] BS_NEGP: Processes with negative provision
    BsPrs: Set = None  # type: ignore[assignment] # [r, p, s] BS_PRS: Process slices for reserve tracking
    BsSbd: Set = None  # type: ignore[assignment] # [r, s, lA] BS_SBD: Timeslices for reserve provision
    BsUcmap: Set = None  # type: ignore[assignment] # [ucnA, side, r, p, c] BS_UCMAP: Map to refer to reserves in UC_FLO
    bs_rtcs: Parameter = None  # type: ignore[assignment] # [rsp, r, year, c, s] BS_RTCS: Temporary work parameter

    g_nointerp: Parameter = None  # type: ignore[assignment] # G_NOINTERP: Turn off interplation
    g_cycle: Parameter = None  # type: ignore[assignment]   # [tslvl] G_CYCLE: Number of cycles in average year
    ComDesc: Set = None  # type: ignore[assignment] # [Reg,Com] COM_DESC: Region-based commodity descriptions
    ComGmap: Set = None  # type: ignore[assignment] # [Reg,comgrp,Com] COM_GMAP: User groups of individual commodities
    ComLim: Set = None  # type: ignore[assignment] # [Reg,Com,lim] COM_LIM: List of equation type for balance
    ComOff: Set = None  # type: ignore[assignment] # [Reg,Com,*,*] COM_OFF: Periods for which a commodity is unavailable
    ComTmap: Set = None  # type: ignore[assignment] # [Reg,ComType,Com] COM_TMAP: Primary grouping of commodities
    ComTs: Set = None  # type: ignore[assignment] # [Reg,Com,allts] COM_TS: List of commodity timeslices
    ComTsl: Set = None  # type: ignore[assignment] # [Reg,Com,tslvl] COM_TSL: Level at which a commodity tracked
    ComUnit: Set = None  # type: ignore[assignment] # [Reg,Com,UnitsCom] COM_UNIT: Units associated with each commodity
    CurMap: Set = None  # type: ignore[assignment] # [Reg,curgrp,cur] CUR_MAP: Grouping of the currenies
    DemSmap: Set = None  # type: ignore[assignment] # [Reg,demsect,Com] DEM_SMAP: Grouping of DEMs (commodities) to their sector
    EnvMap: Set = None  # type: ignore[assignment] # [Reg,envgrp,Com] ENV_MAP: Grouping of ENVs (commodities) to their emissions group
    FinMap: Set = None  # type: ignore[assignment] # [Reg,fingrp,Com] FIN_MAP: Grouping of FINs (commodities) to their financial group
    MatGmap: Set = None  # type: ignore[assignment] # [Reg,matgrp,Com] MAT_GMAP: Grouping of materials
    MatTmap: Set = None  # type: ignore[assignment] # [Reg,mattype,Com] MAT_TMAP: Material by type
    MatVol: Set = None  # type: ignore[assignment] # [Reg,Com] MAT_VOL: Material accounted for by volume
    MatWt: Set = None  # type: ignore[assignment] # [Reg,Com] MAT_WT: Material accounted for by weight
    NrgFmap: Set = None  # type: ignore[assignment] # [Reg,nrgform,Com] NRG_FMAP: Grouping of NRG by Solid/Liquid/Gas
    NrgGmap: Set = None  # type: ignore[assignment] # [Reg,nrggrid,Com] NRG_GMAP: Association of energy carriers to grids
    NrgTmap: Set = None  # type: ignore[assignment] # [Reg,nrgtype,Com] NRG_TMAP: Grouping of energy carriers by type
    PrcAoff: Set = None  # type: ignore[assignment] # [Reg,prc,*,*] PRC_AOFF: Periods for which activity is unavailable
    PrcActunt: Set = None  # type: ignore[assignment] # [Reg,prc,cg,UnitsAct] PRC_ACTUNT: Primary commodity (or group) & activity unit
    PrcCapunt: Set = None  # type: ignore[assignment] # [Reg,prc,cg,UnitsCap] PRC_CAPUNT: Unit of capacity
    PrcCg: Set = None  # type: ignore[assignment] # [r,prc,comgrp] PRC_CG: Commodity groups for a process
    PrcDesc: Set = None  # type: ignore[assignment] # [r,p] PRC_DESC: Process descriptions by region
    PrcFoff: Set = None  # type: ignore[assignment] # [Reg,prc,Com,allts,*,*] PRC_FOFF: Periods/timeslices for which flow is not possible
    PrcMap: Set = None  # type: ignore[assignment] # [Reg,prcgrp,prc] PRC_MAP: Grouping of processes to nature
    PrcNoff: Set = None  # type: ignore[assignment] # [Reg,prc,*,*] PRC_NOFF: Periods for which new capacity can NOT be built
    PrcRmap: Set = None  # type: ignore[assignment] # [Reg,prcrsourc,prc] PRC_RMAP: Grouping of XTRACT processes
    PrcSpg: Set = None  # type: ignore[assignment] # [Reg,prc,comgrp] PRC_SPG: Shadow Primary Group
    PrcTs: Set = None  # type: ignore[assignment] # [allreg,prc,allts] PRC_TS: Timeslices for a process
    PrcTsl: Set = None  # type: ignore[assignment] # [Reg,prc,tslvl] PRC_TSL: Timeslice level for a process
    PrcVint: Set = None  # type: ignore[assignment] # [Reg,prc] PRC_VINT: Process is to be vintaged
    PrcDscncap: Set = None  # type: ignore[assignment] # [r,p] PRC_DSCNCAP: Process with discrete capacity additions
    PrcRcap: Set = None  # type: ignore[assignment] # [Reg,prc] PRC_RCAP: Process with early retirement
    PrcSimv: Set = None  # type: ignore[assignment] # [Reg,prc] PRC_SIMV: Process is to be vintage-simulated
    reggrp: Set = None  # type: ignore[assignment] # [*] REG_GRP: List of regional groups
    RegRmap: Set = None  # type: ignore[assignment] # [reggrp,allreg] REG_RMAP: Grouping of regions in/out of area of study
    ts: Alias = None  # type: ignore[assignment] # [*] TS: Aliased with ALL_TS
    s: Alias = None  # type: ignore[assignment] # [*] S: Aliased with ALL_TS
    sl: Alias = None  # type: ignore[assignment] # [*] SL: Aliased with ALL_TS
    s2: Alias = None  # type: ignore[assignment] # [*] S2: Aliased with ALL_TS
    kp: Set = None  # type: ignore[assignment] # [*] KP
    kp2: Alias = None  # type: ignore[assignment] # [*] KP1: Aliased with KP
    TsOff: Set = None  # type: ignore[assignment] # [Reg,ts,bohyear,eohyear] TS_OFF: Timeslices turned off
    TsGroup: Set = None  # type: ignore[assignment] # [allreg,tslvl,ts] TS_GROUP: Timeslice Level assignment
    TsMap: Set = None  # type: ignore[assignment] # [allreg,allts,allts] TS_MAP: Timeslice hierarchy tree: node+below

    Xtp: Set = None  # type: ignore[assignment] # [LL] XTP:
    mdm: Alias = None  # type: ignore[assignment] # [*] MDM: Aliased with IPS
    cmlpk: Set = None  # type: ignore[assignment] # [*] CM_LPK
    cmlpt: Set = None  # type: ignore[assignment] # [*] CM_LPT
    tm_xwt: Parameter = None  # type: ignore[assignment] # [R,LL] TM_XWT
    t1: Alias = None  # type: ignore[assignment] # [*] T_1: Aliased with TB

    Milestonyr: Set = None  # type: ignore[assignment] # [allyear] MILESTONYR: Projection years for which model to be run
    t: Alias = None  # type: ignore[assignment] # [*] T: Aliased with MILESTONYR
    tt: Alias = None  # type: ignore[assignment] # [*] TT: Aliased with MILESTONYR
    Datayear: Set = None  # type: ignore[assignment] # [allyear] DATAYEAR: Years for which user data is provided
    Pastyear: Set = None  # type: ignore[assignment] # [allyear] PASTYEAR: Years before 1st MILESTONYR for which PASTI needs to be handled
    Modlyear: Set = None  # type: ignore[assignment] # [allyear] MODLYEAR: Years for which the model is to be run (MILESTONYR+PASTYEAR)
    tsl: Alias = None  # type: ignore[assignment] # [*] TSL: Aliased with TSLVL
    Top: Set = None  # type: ignore[assignment] # [Reg,prc,Com,io] TOP: Topology for all process
    TopIre: Set = None  # type: ignore[assignment] # [allreg,Com,allreg,Com,prc] TOP_IRE: Trade within area of study
    ComPeak: Set = None  # type: ignore[assignment] # [Reg,comgrp] COM_PEAK: Peaking required flag
    ComPkts: Set = None  # type: ignore[assignment] # [Reg,comgrp,ts] COM_PKTS: Peaking time-slices
    PrcPkno: Set = None  # type: ignore[assignment] # [allreg,prc] PRC_PKNO: Processes which cannot be involved in peaking
    PrcPkaf: Set = None  # type: ignore[assignment] # [allreg,prc] PRC_PKAF: Flag for default value of NCAP_PKCNT
    PrcNstts: Set = None  # type: ignore[assignment] # [Reg,prc,allts] PRC_NSTTS: Night storage process and time-slice for storaging
    PrcStgtss: Set = None  # type: ignore[assignment] # [Reg,prc,Com] PRC_STGTSS: Storage process and stored commodity for time-slice storage
    PrcStgips: Set = None  # type: ignore[assignment] # [Reg,prc,Com] PRC_STGIPS: Storage process and stored commodity for inter-period storage
    ucn: Set = None  # type: ignore[assignment] # [*] UC_N: Names of all manual constraints
    UcTSucc: Set = None  # type: ignore[assignment] # [allr,ucn,allyear] UC_T_SUCC: Specification of periods, if UC_DYN=SUCC
    UcTSum: Set = None  # type: ignore[assignment] # [allr,ucn,allyear] UC_T_SUM: Specification of periods, if UC_DYN=SEVERAL
    UcTEach: Set = None  # type: ignore[assignment] # [allr,ucn,allyear] UC_T_EACH: Specification of periods, if UC_DYN=EACH
    UcRSum: Set = None  # type: ignore[assignment] # [allr,ucn] UC_R_SUM: Specification of regions, if UC_REG=SUM
    UcREach: Set = None  # type: ignore[assignment] # [allr,ucn] UC_R_EACH: Specification of regions, if UC_REG=EACH
    UcTsSum: Set = None  # type: ignore[assignment] # [allr,ucn,allts] UC_TS_SUM: Specification of time-slices, if UC_TS=SUM
    UcTsEach: Set = None  # type: ignore[assignment] # [allr,ucn,allts] UC_TS_EACH: Specification of time-slices, if UC_TS=EACH
    UcAttr: Set = None  # type: ignore[assignment] # [allr,ucn,side,ucgrptype,ucname] UC_ATTR: Mapping of parameter names to groups
    UcTsl: Set = None  # type: ignore[assignment] # [allr,ucn,side,tslvl] UC_TSL: UC timeslice level
    ucnA: Alias = None  # type: ignore[assignment] # [*] UCN: Aliased with UC_N
    SwT: Set = None  # type: ignore[assignment] # [allyear,allsow] SW_T: Stochastic state indexes by period
    GUamat: Set = None  # type: ignore[assignment] # [u] G_UAMAT: Unit for activity of material process
    GUanrg: Set = None  # type: ignore[assignment] # [u] G_UANRG: Unit for activity of energy process
    GUcmat: Set = None  # type: ignore[assignment] # [u] G_UCMAT: Unit for capacity of material process
    GUcnrg: Set = None  # type: ignore[assignment] # [u] G_UCNRG: Unit for capacity of energy process
    GRcur: Set = None  # type: ignore[assignment] # [Reg,cur] G_RCUR: Main currency unit by region
    Actcg: Set = None  # type: ignore[assignment] # [cg] ACTCG:
    b: Parameter = None  # type: ignore[assignment] # [allyear] B: Beginning year of each model period
    e: Parameter = None  # type: ignore[assignment] # [allyear] E: Ending year of each model period
    m: Parameter = None  # type: ignore[assignment] # [allyear] M: Middle year of each Period
    d: Parameter = None  # type: ignore[assignment] # [allyear] D: Length of each period
    act_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,ts,bd] ACT_BND: Bound on activity of a process
    act_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] ACT_COST: Variable costs associated with activity of a process
    act_cstup: Parameter = None  # type: ignore[assignment] # [r,allyear,p,tslvl,cur] ACT_CSTUP: Variable costs associated with startup of a process
    act_cstsd: Parameter = None  # type: ignore[assignment] # [r,allyear,p,upt,bd,cur] ACT_CSTSD: Start-up (BD=UP) and shutdown costs (BD=LO) per unit of started-up capacity, by start-up type
    act_cstrmp: Parameter = None  # type: ignore[assignment] # [r,allyear,p,l,cur] ACT_CSTRMP: Ramp-up (L=UP) or ramp-down (L=LO) cost per unit of load change
    act_flo: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,s] ACT_FLO: General process transformation parameter
    act_time: Parameter = None  # type: ignore[assignment] # [r,allyear,p,l] ACT_TIME: Minimum online/offline hours
    act_cum: Parameter = None  # type: ignore[assignment] # [Reg,prc,item,item,lim] ACT_CUM: Bound on cumulative activity
    ncap_af: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,ts,bd] NCAP_AF: Availability of capacity
    ncap_afa: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,bd] NCAP_AFA: Annual Availability of capacity
    ncap_afs: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,ts,bd] NCAP_AFS: Seasonal Availability of capacity
    s_ncap_afs: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,ts,bd] NCAP_AFS: Seasonal Availability of capacity
    ncap_afx: Parameter = None  # type: ignore[assignment] # [r,allyear,p] NCAP_AFX: Change in capacity availability
    ncap_afsx: Parameter = None  # type: ignore[assignment] # [r,allyear,p,bd] NCAP_AFSX: Change in seasonal capacity availability
    ncap_afm: Parameter = None  # type: ignore[assignment] # [r,allyear,p] NCAP_AFM: Pointer to availity change multiplier
    ncap_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,lim] NCAP_BND: Bound on overall capacity in a period
    ncap_bpme: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_BPME: Back pressure mode efficiency (or total eff.)
    ncap_cdme: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_CDME: Condensing mode efficiency
    ncap_ceh: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_CEH: Coefficient of electricity to heat
    ncap_chpr: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,lim] NCAP_CHPR: Combined heat:power ratio
    ncap_cled: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com] NCAP_CLED: Leadtime of a commodity before new capacity ready
    ncap_clag: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,io] NCAP_CLAG: Lagtime of a commodity after new capacity ready
    ncap_com: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,io] NCAP_COM: Use (but +) of commodity based upon capacity
    ncap_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_COST: Investment cost for new capacity
    s_ncap_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_COST: Investment cost for new capacity
    ncap_cpx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_CPX: Pointer to capacity transfer multiplier
    ncap_drate: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_DRATE: Process specific discount (hurdle) rate
    ncap_fdr: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FDR: Functional depreciation rate of process
    ncap_elife: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_ELIFE: Economic (payback) lifetime
    ncap_fom: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_FOM: Fixed annual O&M costs
    ncap_fomx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FOMX: Change in fixed O&M
    ncap_fomm: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FOMM: Pointer to fixed O&M change multiplier
    ncap_fsub: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_FSUB: Fixed tax on installed capacity
    ncap_fsubx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FSUBX: Change in fixed tax
    ncap_fsubm: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FSUBM: Pointer to fixed subsidy change multiplier
    ncap_ftax: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_FTAX: Fixed tax on installed capacity
    ncap_ftaxx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FTAXX: Change in fixed tax
    ncap_ftaxm: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_FTAXM: Pointer to fixed tax change multiplier
    ncap_icom: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com] NCAP_ICOM: Input of commodity for install of new capacity
    ncap_iled: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_ILED: Lead-time required for building a new capacity
    ncap_isub: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_ISUB: Subsidy for a new investment in capacity
    ncap_itax: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_ITAX: Tax on a new investment in capacity
    ncap_ispct: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_ISPCT: Subsidy as % of new investment cost
    ncap_lcost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_LCOST: % labor cost of new investment
    ncap_lfom: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_LFOM: % labor cost of fixed O&M
    ncap_pasti: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_PASTI: Capacity install prior to study years
    ncap_pasty: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_PASTY: Buildup years for past investments
    ncap_tlife: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_TLIFE: Technical lifetime of a process
    ncap_olife: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_OLIFE: Operating lifetime of a process
    rcap_blk: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] RCAP_BLK: Retirement block size
    rcap_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,lim] RCAP_BND: Retirement bounds
    ncap_dcost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_DCOST: Cost of decomissioning
    ncap_dlag: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_DLAG: Delay to begin decomissioning
    ncap_dlagc: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] NCAP_DLAGC: Cost of decomissioning delay
    ncap_delif: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_DELIF: Economic lifetime to pay for decomissioning
    ncap_dlife: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] NCAP_DLIFE: Time for the actual decomissioning
    ncap_ocom: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com] NCAP_OCOM: Commodity release during decomissioning
    ncap_valu: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,cur] NCAP_VALU: Value of material released during decomissioning
    ncap_start: Parameter = None  # type: ignore[assignment] # [Reg,prc] NCAP_START: Start year for new investments
    ncap_semi: Parameter = None  # type: ignore[assignment] # [r,allyear,p] NCAP_SEMI: Semi-continuous capacity, lower bound
    cap_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,bd] CAP_BND: Bound on total installed capacity in a period
    s_cap_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,bd] CAP_BND: Bound on total installed capacity in a period
    com_bndnet: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,lim] COM_BNDNET: Net bound on commodity (e.g., emissions)
    com_bndprd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,lim] COM_BNDPRD: Limit on production of a commodity
    com_cumnet: Parameter = None  # type: ignore[assignment] # [Reg,bohyear,eohyear,Com,lim] COM_CUMNET: Cumulative net bound on commodity (e.g. emissions)
    s_com_cumnet: Parameter = None  # type: ignore[assignment] # [Reg,bohyear,eohyear,Com,lim] COM_CUMNET: Cumulative net bound on commodity (e.g. emissions)
    com_cumprd: Parameter = None  # type: ignore[assignment] # [Reg,bohyear,eohyear,Com,lim] COM_CUMPRD: Cumulative limit on production of a commodity
    s_com_cumprd: Parameter = None  # type: ignore[assignment] # [Reg,bohyear,eohyear,Com,lim] COM_CUMPRD: Cumulative limit on production of a commodity
    com_cstnet: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_CSTNET: Cost on Net of commodity (e.g. emissions tax)
    com_cstprd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_CSTPRD: Cost on production of a commodity
    com_fr: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts] COM_FR: Seasonal distribution of a commodity
    s_com_fr: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts] COM_FR: Seasonal distribution of a commodity
    com_ie: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts] COM_IE: Seasonal efficiency of commodity
    com_subnet: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_SUBNET: Subsidy on a commodity net
    com_subprd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_SUBPRD: Subsidy on production of a commodity net
    com_taxnet: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_TAXNET: Tax on a commodity net
    com_taxprd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_TAXPRD: Tax on production of a commodity net
    s_com_tax: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] S_COM_TAX: Tax on production of a commodity net
    com_agg: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,Com] COM_AGG: Commodity aggregation parameter
    com_bprice: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,cur] COM_BPRICE: Base price of elastic demands
    com_bqty: Parameter = None  # type: ignore[assignment] # [Reg,Com,ts] COM_BQTY: Base quantity for elastic demands
    com_elast: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts,lim] COM_ELAST: Elasticity of demand
    com_elastx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,bd] COM_ELASTX: Elasticity shape of demand
    com_proj: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com] COM_PROJ: Demand baseline projection
    s_com_proj: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com] COM_PROJ: Demand baseline projection
    com_step: Parameter = None  # type: ignore[assignment] # [Reg,Com,lim] COM_STEP: Step size for elastic demand
    com_voc: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,bd] COM_VOC: Variance of elastic demand
    flo_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,ts,bd] FLO_BND: Bound on the flow variable
    flo_bdlvl: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,s,bd] FLO_BDLVL: Bound on the flow variable by hourly rate level
    flo_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,cur] FLO_COST: Added variable O&M of using a commodity
    flo_deliv: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,cur] FLO_DELIV: Delivery cost for using a commodity
    flo_feq: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com] FLO_FEQ: Fossil equivalent of a commodity in a process
    flo_fr: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,lim] FLO_FR: Load-curve limitations for a process commodity flow
    flo_func: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,cg,ts] FLO_FUNC: Relationship between 2 (group of) flows
    s_flo_func: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,cg,ts] FLO_FUNC: Relationship between 2 (group of) flows
    flo_funcx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,cg] FLO_FUNCX: Change in FLO_FUNC/FLO_SUM by age
    flo_shar: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,c,cg,ts,bd] FLO_SHAR: Relationship between members of the same flow group
    flo_sub: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,cur] FLO_SUB: Subsidy for the production/use of a commodity
    flo_sum: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,c,cg,ts] FLO_SUM: Multipier for commodity in cg1 where each is summed into cg2
    flo_tax: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,cur] FLO_TAX: Tax on the production/use of a commodity
    flo_cum: Parameter = None  # type: ignore[assignment] # [Reg,prc,Com,item,item,lim] FLO_CUM: Bound on cumulative flow
    s_flo_cum: Parameter = None  # type: ignore[assignment] # [Reg,prc,Com,item,item,lim] FLO_CUM: Bound on cumulative flow
    flo_mark: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,bd] FLO_MARK: Process-wise market share in total commodity production
    flo_ire: Parameter = None  # type: ignore[assignment] # [RR,LL,P,C,S,IE] FLO_IRE:
    prc_mark: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,item,c,lim] PRC_MARK: Process group-wise market share
    prc_resid: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] PRC_RESID: Residual capacity available in each period
    prc_refit: Parameter = None  # type: ignore[assignment] # [Reg,prc,prc] PRC_REFIT: Process with retrofit or life-extension
    ncap_pkcnt: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,allts] NCAP_PKCNT: Fraction of capacity contributing to peaking in time-slice TS
    com_pkrsv: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com] COM_PKRSV: Peaking reserve margin
    com_pkflx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,ts] COM_PKFLX: Peaking flux ratio
    flo_pkcoi: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,allts] FLO_PKCOI: Factor increasing the average demand
    stg_eff: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] STG_EFF: Storage efficiency
    stg_loss: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,s] STG_LOSS: Annual energy loss from a storage technology
    stg_chrg: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,s] STG_CHRG: Exogeneous charging of a storage technology
    stg_sift: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s] STG_SIFT: Max load sifting in proportion to total load
    stgout_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,c,s,bd] STGOUT_BND: Bound on output-flow of storage process
    stgin_bnd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,c,s,bd] STGIN_BND: Bound on output-flow of storage process
    prc_actflo: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg] PRC_ACTFLO: Convert from process activity to particular commodity flow
    prc_capact: Parameter = None  # type: ignore[assignment] # [Reg,prc] PRC_CAPACT: Factor for going from capacity to activity
    prc_gmap: Parameter = None  # type: ignore[assignment] # [Reg,prc,item] PRC_GMAP: User-defined groupings of processes
    g_chngmony: Parameter = None  # type: ignore[assignment] # [Reg,allyear,cur] G_CHNGMONY: Exchange rate for currency
    g_drate: Parameter = None  # type: ignore[assignment] # [Reg,allyear,cur] G_DRATE: Discount rate for a currency
    g_rfrir: Parameter = None  # type: ignore[assignment] # [Reg,allyear] G_RFRIR: Riskfree real interest rate
    g_yrfr: Parameter = None  # type: ignore[assignment] # [allreg,ts] G_YRFR: Seasonal fraction of the year
    ts_cycle: Parameter = None  # type: ignore[assignment] # [Reg,ts] TS_CYCLE: Length of cycles below timeslice, in days
    g_offthd: Parameter = None  # type: ignore[assignment] # [allyear] G_OFFTHD: Threshold for OFF ranges
    g_overlap: Parameter = None  # type: ignore[assignment] #  G_OVERLAP: Overlap of stepped solutions (in years)
    reg_fixt: Parameter = None  # type: ignore[assignment] # [allr] REG_FIXT: Year up to which periods are fixed
    reg_bdncap: Parameter = None  # type: ignore[assignment] # [allr,l] REG_BDNCAP: Year up to which VAR_NCAPs are to be fixed
    g_curex: Parameter = None  # type: ignore[assignment] # [cur,cur] G_CUREX: Global currency conversions
    r_curex: Parameter = None  # type: ignore[assignment] # [allreg,cur,cur] R_CUREX: Regional currency conversions
    ire_bnd: Parameter = None  # type: ignore[assignment] # [allr,allyear,Com,ts,allreg,ie,bd] IRE_BND: Limit on inter-reg exchange of commodity
    ire_flo: Parameter = None  # type: ignore[assignment] # [allr,allyear,prc,Com,allr,Com,ts] IRE_FLO: Efficiency of exchange for inter-regional trade
    ire_flosum: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,ie,Com,io] IRE_FLOSUM: Aux. consumption/emissions from inter-regional trade
    ire_price: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,Com,ts,allr,ie,cur] IRE_PRICE: Exogenous price of import/export
    ire_xbnd: Parameter = None  # type: ignore[assignment] # [allreg,allyear,Com,ts,ie,bd] IRE_XBND: Limit on all (external and inter-regional) exchange of commodity
    ire_ccvt: Parameter = None  # type: ignore[assignment] # [allreg,Com,allreg,Com] IRE_CCVT: Commodity unit conversion factor between regions
    ire_tscvt: Parameter = None  # type: ignore[assignment] # [allreg,allts,allreg,allts] IRE_TSCVT: Identification and TS-conversion factor between regions
    shape: Parameter = None  # type: ignore[assignment] # [j,age] SHAPE: Shaping table
    multi: Parameter = None  # type: ignore[assignment] # [j,allyear] MULTI: Multiplier table
    reg_bndcst: Parameter = None  # type: ignore[assignment] # [Reg,allyear,costagg,cur,bd] REG_BNDCST: Bound on regional costs by type
    reg_cumcst: Parameter = None  # type: ignore[assignment] # [Reg,allyear,allyear,costagg,cur,bd] REG_CUMCST: Cumulative bound on regional costs
    uc_rhs: Parameter = None  # type: ignore[assignment] # [ucn,lim] UC_RHS: Constant in user constraint
    s_uc_rhs: Parameter = None  # type: ignore[assignment] # [ucn,lim] UC_RHS: Constant in user constraint
    uc_rhst: Parameter = None  # type: ignore[assignment] # [ucn,allyear,lim] UC_RHST: Constant in user constraint
    s_uc_rhst: Parameter = None  # type: ignore[assignment] # [ucn,allyear,lim] UC_RHST: Constant in user constraint
    uc_rhsr: Parameter = None  # type: ignore[assignment] # [allreg,ucn,lim] UC_RHSR: Constant in user constraint
    s_uc_rhsr: Parameter = None  # type: ignore[assignment] # [allreg,ucn,lim] UC_RHSR: Constant in user constraint
    uc_rhss: Parameter = None  # type: ignore[assignment] # [ucn,ts,lim] UC_RHSS: Constant in user constraint
    s_uc_rhss: Parameter = None  # type: ignore[assignment] # [ucn,ts,lim] UC_RHSS: Constant in user constraint
    uc_rhsrt: Parameter = None  # type: ignore[assignment] # [allreg,ucn,allyear,lim] UC_RHSRT: Constant in user constraint
    s_uc_rhsrt: Parameter = None  # type: ignore[assignment] # [allreg,ucn,allyear,lim] UC_RHSRT: Constant in user constraint
    uc_rhsrs: Parameter = None  # type: ignore[assignment] # [allreg,ucn,ts,lim] UC_RHSRS: Constant in user constraint
    s_uc_rhsrs: Parameter = None  # type: ignore[assignment] # [allreg,ucn,ts,lim] UC_RHSRS: Constant in user constraint
    uc_rhsrts: Parameter = None  # type: ignore[assignment] # [allreg,ucn,allyear,ts,lim] UC_RHSRTS: Constant in user constraint
    s_uc_rhsrts: Parameter = None  # type: ignore[assignment] # [allreg,ucn,allyear,ts,lim] UC_RHSRTS: Constant in user constraint
    uc_rhsts: Parameter = None  # type: ignore[assignment] # [ucn,allyear,ts,lim] UC_RHSTS: Constant in user constraint
    s_uc_rhsts: Parameter = None  # type: ignore[assignment] # [ucn,allyear,ts,lim] UC_RHSTS: Constant in user constraint
    uc_flo: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,prc,Com,ts] UC_FLO: Multiplier of flow variables
    uc_act: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,prc,allts] UC_ACT: Multiplier of activity variables
    uc_cap: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,prc] UC_CAP: Multiplier of capacity variables
    uc_ncap: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,prc] UC_NCAP: Multiplier of VAR_NCAP variables
    uc_comcon: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,Com,ts] UC_COMCON: Multiplier of VAR_COMCON variables
    uc_comprd: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,Com,ts] UC_COMPRD: Multiplier of VAR_COMPRD variables
    uc_comnet: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,Com,ts] UC_COMNET: Multiplier of VAR_COMNET variables
    uc_ire: Parameter = None  # type: ignore[assignment] # [ucn,side,allreg,allyear,prc,Com,ts,ie] UC_IRE: Multiplier of inter-regional exchange variables
    uc_cumact: Parameter = None  # type: ignore[assignment] # [ucn,allreg,prc,item,item] UC_CUMACT: Multiplier of cumulative process activity variable
    uc_cumflo: Parameter = None  # type: ignore[assignment] # [ucn,allreg,prc,Com,item,item] UC_CUMFLO: Multiplier of cumulative process flow variable
    uc_cumcom: Parameter = None  # type: ignore[assignment] # [ucn,allreg,comvar,Com,item,item] UC_CUMCOM: Multiplier of cumulative commodity variable
    uc_ucn: Parameter = None  # type: ignore[assignment] # [ucn,side,allr,allyear,ucn] UC_UCN: Multiplier of user constraint variable
    uc_time: Parameter = None  # type: ignore[assignment] # [ucn,allr,allyear] UC_TIME: Multiplier of time in model periods (years)
    dam_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,cur] DAM_COST: Marginal damage cost of emissions
    s_dam_cost: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,cur] DAM_COST: Marginal damage cost of emissions
    dam_bqty: Parameter = None  # type: ignore[assignment] # [Reg,Com] DAM_BQTY: Base quantity of emissions
    dam_elast: Parameter = None  # type: ignore[assignment] # [Reg,Com,lim] DAM_ELAST: Elasticity of damage cost
    dam_step: Parameter = None  # type: ignore[assignment] # [Reg,Com,lim] DAM_STEP: Step number for emissions up to base
    dam_voc: Parameter = None  # type: ignore[assignment] # [Reg,Com,lim] DAM_VOC: Variance of emissions
    dam_tqty: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com] DAM_TQTY: Base quantity of emissions by year
    dam_tvoc: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,lim] DAM_TVOC: Variance of emissions by year
    dam_coef: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,s] DAM_COEF: Coefficient from commodity to damage
    dam_size: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,lim] DAM_SIZE: Size of emission steps
    damobj: Set = None  # type: ignore[assignment] # [*] DAMOBJ: Damage objective components (DAM, DAS, DAM-EXT)
    wwdam: Set = None  # type: ignore[assignment] # [*] WWDAM: Commodities damaged via total concentration/box rather than flow
    rtdam: Set = None  # type: ignore[assignment] # [Reg,allyear,Com,allsow] RTDAM: Region/period/commodity/SOW triples with an active damage cost
    sww: Set = None  # type: ignore[assignment] # [allsow,allsow] SWW: SOW-pair projection of SW_TSW, used to weight damage cost across sample windows
    Jsubj: Set = None  # type: ignore[assignment] # [j,j] JSUBJ: All steps up to J
    DamNum: Set = None  # type: ignore[assignment] # [r,c,j,bd] DAM_NUM: Damage steps per bound type
    rpt_opt: Parameter = None  # type: ignore[assignment] # [item,j] RPT_OPT: Reporting options
    cst_dam: Parameter = None  # type: ignore[assignment] # [Reg,t,Com] CST_DAM: Damage costs
    scst_dam: Parameter = None  # type: ignore[assignment] # [Reg,t,Com] CST_DAM: Damage costs
    cm_result: Parameter = None  # type: ignore[assignment] # [item,item,allyear] CM_RESULT: Climate module results
    cm_maxc_m: Parameter = None  # type: ignore[assignment] # [item,allyear] CM_MAXC_M: Shadow price of climate constraint
    tm_result: Parameter = None  # type: ignore[assignment] # [item,r,allyear] TM_RESULT: MACRO results
    miyr_v1: Parameter = None  # type: ignore[assignment] # MIYR_V1:
    miyr_vl: Parameter = None  # type: ignore[assignment] # MIYR_VL:
    pyr_v1: Parameter = None  # type: ignore[assignment] # PYR_V1:
    my_f: Parameter = None  # type: ignore[assignment] # MY_F:
    var_sift: Parameter = None  # type: ignore[assignment] # [LL,S,L] VAR_SIFT:
    f: Parameter = None  # type: ignore[assignment] # F:
    z: Parameter = None  # type: ignore[assignment] # Z:
    cnt: Parameter = None  # type: ignore[assignment] # CNT:
    dfunc: Parameter = None  # type: ignore[assignment] # DFUNC:
    done: Parameter = None  # type: ignore[assignment] # DONE:
    ifq: Parameter = None  # type: ignore[assignment] # IFQ:
    dur_max: Parameter = None  # type: ignore[assignment] # DUR_MAX:
    first_val: Parameter = None  # type: ignore[assignment] # FIRST_VAL:
    last_val: Parameter = None  # type: ignore[assignment] # LAST_VAL:
    my_fyear: Parameter = None  # type: ignore[assignment] # MY_FYEAR:
    Lastll: Set = None  # type: ignore[assignment] # [ll] LASTLL:
    intdefault: Set = None  # type: ignore[assignment] # [*] INT_DEFAULT:
    uncd1: Set = None  # type: ignore[assignment] # [*] UNCD1: Non-domain-controlled set
    ie_default: Parameter = None  # type: ignore[assignment] # [*] IE_DEFAULT:
    Ble: Set = None  # type: ignore[assignment] # [Com] BLE:
    Opr: Set = None  # type: ignore[assignment] # [Com] OPR:
    spe: Set = None  # type: ignore[assignment] # [*] SPE:
    Ref: Set = None  # type: ignore[assignment] # [r,prc] REF: Refineries
    refunit: Parameter = None  # type: ignore[assignment] # [r] REFUNIT:
    cvt: Set = None  # type: ignore[assignment] # [*] CVT:
    convert: Parameter = None  # type: ignore[assignment] # [Opr,cvt] CONVERT:
    bl_start: Parameter = None  # type: ignore[assignment] # [r,Com,spe] BL_START:
    bl_unit: Parameter = None  # type: ignore[assignment] # [r,Com,spe] BL_UNIT:
    bl_type: Parameter = None  # type: ignore[assignment] # [r,Com,spe] BL_TYPE:
    bl_spec: Parameter = None  # type: ignore[assignment] # [r,Com,spe] BL_SPEC:
    bl_com: Parameter = None  # type: ignore[assignment] # [r,Com,Opr,spe] BL_COM:
    bl_inp: Parameter = None  # type: ignore[assignment] # [r,Com,Com] BL_INP:
    bl_varomc: Parameter = None  # type: ignore[assignment] # [r,Com,cur] BL_VAROMC:
    bl_delivc: Parameter = None  # type: ignore[assignment] # [r,Com,Com,cur] BL_DELIVC:
    env_bl: Parameter = None  # type: ignore[assignment] # [r,Com,Com,Opr,year] ENV_BL:
    peakda_bl: Parameter = None  # type: ignore[assignment] # [r,Com,year] PEAKDA_BL:
    ru_cvt: Parameter = None  # type: ignore[assignment] # [r,Ble,spe,Opr] RU_CVT:
    ru_feq: Parameter = None  # type: ignore[assignment] # [r,Com,year] RU_FEQ:
    obj_blndv: Parameter = None  # type: ignore[assignment] # [r,year,c,c,cur] OBJ_BLNDV: annual variable costs for blending
    altobj: Parameter = None  # type: ignore[assignment] # ALTOBJ:
    unit: Set = None  # type: ignore[assignment] # [*] UNIT: Number of different units
    ncap_disc: Parameter = None  # type: ignore[assignment] # [r,allyear,p,unit] NCAP_DISC: Unit size of discrete capacity addition
    vda_flop: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,s] VDA_FLOP: General process transformation parameter
    vda_emcb: Parameter = None  # type: ignore[assignment] # [Reg,allyear,Com,Com] VDA_EMCB: Combustion emission parameter (aka EMI_comb)
    vda_ceh: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] VDA_CEH: The slope of pass-out turbine (alias NCAP_CEH)
    flo_emis: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,Com,s] FLO_EMIS: General process emission parameter
    flo_eff: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,Com,s] FLO_EFF: General process flow-relation parameter
    stl: Set = None  # type: ignore[assignment] # [*] STL:
    ncap_afac: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg] NCAP_AFAC: Annual availability of capacity for commodity group CG
    ncap_afc: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,stl] NCAP_AFC: Availability of capacity for commodity group CG
    ncap_afcs: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,ts] NCAP_AFCS: Availability of capacity for commodity group CG
    UcDynbnd: Set = None  # type: ignore[assignment] # [ucn,lim] UC_DYNBND: Dynamic process-wise UC bounds
    act_eff: Parameter = None  # type: ignore[assignment] # [Reg,year,prc,cg,ts] ACT_EFF: Activity efficiency for process
    act_ups: Parameter = None  # type: ignore[assignment] # [r,allyear,p,s,l] ACT_UPS: Max. ramp rate, fraction of capacity per hour
    act_minld: Parameter = None  # type: ignore[assignment] # [r,allyear,p] ACT_MINLD: Minimum stable operation level
    act_lospl: Parameter = None  # type: ignore[assignment] # [r,allyear,p,l] ACT_LOSPL: Fuel consumption increase at minimum load
    act_cstpl: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] ACT_CSTPL: Partial load cost penalty
    act_maxnon: Parameter = None  # type: ignore[assignment] # [r,ll,p,upt] ACT_MAXNON: Max. non-operational time before transition to next stand-by condition, by start-up type, in hours
    act_sdtime: Parameter = None  # type: ignore[assignment] # [r,ll,p,upt,bd] ACT_SDTIME: Duration of start-up (BD=UP) and shut-down BD=LO) phases, by start-up type, in hours
    act_lossd: Parameter = None  # type: ignore[assignment] # [r,ll,p,upt,bd] ACT_LOSSD: Efficiency at one hour from start-up (BD=UP) or at one hour to end of shut-down (BD=LO)
    stg_maxcyc: Parameter = None  # type: ignore[assignment] # [r,year,p] STG_MAXCYC: Maximum number of storage cycles over lifetime
    uc_actbet: Parameter = None  # type: ignore[assignment] # [ucn,allreg,allyear,prc] UC_ACTBET:
    uc_flobet: Parameter = None  # type: ignore[assignment] # [ucn,allreg,allyear,prc,cg] UC_FLOBET:
    com_cstbal: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s,item,cur] COM_CSTBAL: Cost on specific component of node balance
    prc_react: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PRC_REACT: Reactance of transmission line
    gr_ptdf: Parameter = None  # type: ignore[assignment] # [r,year,p,c,allr,c] GR_PTDF: PTDF of transmission line
    gr_genlev: Parameter = None  # type: ignore[assignment] # [r,c] GR_GENLEV: Grid connection category for electricity generation commodity
    gr_demfr: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] GR_DEMFR: Fraction of total electricity demand allocated to grid node
    gr_endfr: Parameter = None  # type: ignore[assignment] # [r,allyear,c,cg] GR_ENDFR: Fraction of sectoral electricity demand allocated to grid node
    gr_genfr: Parameter = None  # type: ignore[assignment] # [r,allyear,c,item] GR_GENFR: Fraction of electricity generation type allocated to grid node
    gr_genmap: Parameter = None  # type: ignore[assignment] # [r,p,item] GR_GENMAP: Mapping of technology to generation type
    gr_xbnd: Parameter = None  # type: ignore[assignment] # [r,allyear] GR_XBND: Maximum level of net imports to / exports from region
    gr_thmin: Parameter = None  # type: ignore[assignment] # [r,ll,p] GR_THMIN: Thermal minimum level
    gr_vargen: Parameter = None  # type: ignore[assignment] # [r,s,item,bd] GR_VARGEN: Variance in type of generation
    gg_dens: Parameter = None  # type: ignore[assignment] # [r,c] GG_DENS: Density of gases
    gg_gamma: Parameter = None  # type: ignore[assignment] # [r,year,p,c] GG_GAMMA: Comprossion factor
    gg_kgf: Parameter = None  # type: ignore[assignment] # [r,year,p,c] GG_KGF: Weymouth constants
    gg_klp: Parameter = None  # type: ignore[assignment] # [r,year,p,c] GG_KLP: Linepack constants
    gg_prbd: Parameter = None  # type: ignore[assignment] # [r,year,c,lim] GG_PRBD: Nodal pressure bounds
    gg_pp: Parameter = None  # type: ignore[assignment] # [r,year,p,c,l,j] GG_PP: Fixed pressure points
    com_mshgv: Parameter = None  # type: ignore[assignment] # [r,year,c] COM_MSHGV: Choices heterogeneity parameter
    ncap_msprf: Parameter = None  # type: ignore[assignment] # [r,year,c,p,lim] NCAP_MSPRF: Preference parameters in choice
    Solvestat: Set = None  # type: ignore[assignment] # [j] SOLVESTAT:
    OBJZ: Variable = None  # type: ignore[assignment]  #  OBJZ:
    Rc: Set = None  # type: ignore[assignment] # [r,c] RC: Commodities in each region
    Rcj: Set = None  # type: ignore[assignment] # [r,c,j,bd] RCJ: # of steps for elastic demands
    RcAgp: Set = None  # type: ignore[assignment] # [Reg,Com,lim] RC_AGP: Commodity aggregation of production
    RtcNet: Set = None  # type: ignore[assignment] # [r,allyear,c] RTC_NET: VAR_COMNETs within CUM constraint range
    RtcPrd: Set = None  # type: ignore[assignment] # [r,allyear,c] RTC_PRD: VAR_COMPRDs within CUM constraint range
    RhsCombal: Set = None  # type: ignore[assignment] # [r,allyear,c,s] RHS_COMBAL: VAR_COMNET needed on balance
    RhsComprd: Set = None  # type: ignore[assignment] # [r,allyear,c,s] RHS_COMPRD: VAR_COMPRD needed on production
    RcsCombal: Set = None  # type: ignore[assignment] # [r,allyear,c,s,lim] RCS_COMBAL: TS for balance given RHS requirements
    RcsComprd: Set = None  # type: ignore[assignment] # [r,allyear,c,s,lim] RCS_COMPRD: TS for production given RHS requirements
    RcsComts: Set = None  # type: ignore[assignment] # [r,c,allts] RCS_COMTS: All timeslices at/above the COM_TSL
    RdAgg: Set = None  # type: ignore[assignment] # [Reg,Com] RD_AGG: Micro aggregated demands
    MiDmas: Set = None  # type: ignore[assignment] # [Reg,Com,Com] MI_DMAS: Micro aggregation map
    Ne: Set = None  # type: ignore[assignment] # [allr,Com] NE: Non-energy Demands
    Rdcur: Set = None  # type: ignore[assignment] # [Reg,cur] RDCUR: Discounted currencies by region
    ObjIcur: Set = None  # type: ignore[assignment] # [Reg,allyear,p,cur] OBJ_ICUR: Capacity-related cost indicator
    Dem: Set = None  # type: ignore[assignment] # [Reg,Com] DEM: Demand commodities
    Env: Set = None  # type: ignore[assignment] # [Reg,Com] ENV: Environmental indicator commodities
    Fin: Set = None  # type: ignore[assignment] # [Reg,Com] FIN: Financial flow commodities
    Mat: Set = None  # type: ignore[assignment] # [Reg,Com] MAT: Material commodities
    Nrg: Set = None  # type: ignore[assignment] # [Reg,Com] NRG: Energy carrier commodities
    Rp: Set = None  # type: ignore[assignment] # [r,p] RP: Processes in each region
    RpFlo: Set = None  # type: ignore[assignment] # [r,p] RP_FLO: Processes with VAR_FLOs (not IRE)
    RpStd: Set = None  # type: ignore[assignment] # [r,p] RP_STD: Standard processes with VAR_FLOs
    RpStg: Set = None  # type: ignore[assignment] # [r,p] RP_STG: Storage processes
    RpIre: Set = None  # type: ignore[assignment] # [allreg,p] RP_IRE: Processes involved in inter-regional trade
    RpNrg: Set = None  # type: ignore[assignment] # [r,p] RP_NRG: Processes with an energy carrier PCG
    RpInout: Set = None  # type: ignore[assignment] # [r,p,io] RP_INOUT: Indicator if process input/output normalized (according to PG side)
    RpPg: Set = None  # type: ignore[assignment] # [Reg,prc,cg] RP_PG: Primary commodity group (PG)
    RpPgtype: Set = None  # type: ignore[assignment] # [r,p,cg] RP_PGTYPE: Group type of the primary group
    RpUpl: Set = None  # type: ignore[assignment] # [r,p,l] RP_UPL: Processes with dispatching equations
    RpUpr: Set = None  # type: ignore[assignment] # [r,p,l] RP_UPR: Processes with ramping costs
    RpUps: Set = None  # type: ignore[assignment] # [r,p,tslvl,l] RP_UPS: Timeslice levels for startup accounting
    RpUpt: Set = None  # type: ignore[assignment] # [r,p,upt,bd] RP_UPT: Start-up types for unit commitment
    RpDpl: Set = None  # type: ignore[assignment] # [r,p,tslvl] RP_DPL: Dispatching process timeslice levels
    RpAire: Set = None  # type: ignore[assignment] # [r,p,ie] RP_AIRE: Exchange process activity directions
    Rpc: Set = None  # type: ignore[assignment] # [r,p,c] RPC: Commodities in/out of a processes
    RpcCapflo: Set = None  # type: ignore[assignment] # [r,allyear,p,c] RPC_CAPFLO: Commodities involved in capacity
    RpcConly: Set = None  # type: ignore[assignment] # [r,allyear,p,c] RPC_CONLY: Commodities ONLY involved in capacity
    RpcNoflo: Set = None  # type: ignore[assignment] # [r,p,c] RPC_NOFLO: Commodities ONLY involved in capacity
    RpcIre: Set = None  # type: ignore[assignment] # [allreg,p,c,ie] RPC_IRE: Process/commodities involved in inter-regional trade
    RpcEqire: Set = None  # type: ignore[assignment] # [r,p,c,ie] RPC_EQIRE: Indicator for EQIRE equation generation
    RpcMarket: Set = None  # type: ignore[assignment] # [r,p,c,ie] RPC_MARKET: Market exchange process indicator
    RpcPg: Set = None  # type: ignore[assignment] # [r,p,c] RPC_PG: Commodities in the primary group
    RpcSpg: Set = None  # type: ignore[assignment] # [r,p,c] RPC_SPG: Commodities in the shadow primary group
    RpcsVar: Set = None  # type: ignore[assignment] # [r,p,c,allts] RPCS_VAR: Timeslices at which VAR_FLOs are to be created
    RpsS1: Set = None  # type: ignore[assignment] # [r,p,allts] RPS_S1: All timeslices at the PRC_TSL/COM_TSLspg
    RpsS2: Set = None  # type: ignore[assignment] # [r,p,allts] RPS_S2: All timeslices at/above PRC_TSL/COM_TSLspg
    RpsPrcts: Set = None  # type: ignore[assignment] # [r,p,allts] RPS_PRCTS: All timeslices at/above the PRC_TSL
    Rtc: Set = None  # type: ignore[assignment] # [r,allyear,c] RTC: Commodity/time
    RtcShed: Set = None  # type: ignore[assignment] # [r,year,c,bd,j] RTC_SHED: Elastic shape indexes
    RtcsVarc: Set = None  # type: ignore[assignment] # [r,allyear,c,allts] RTCS_VARC: The VAR_COMNET/PRDs control set
    Rtp: Set = None  # type: ignore[assignment] # [r,allyear,p] RTP: Process/time
    Rtpc: Set = None  # type: ignore[assignment] # [r,allyear,p,c] RTPC: Commodities of process in period
    RtpCptyr: Set = None  # type: ignore[assignment] # [r,allyear,allyear,p] RTP_CPTYR: Capcity transfer v/t years
    RtpOff: Set = None  # type: ignore[assignment] # [r,allyear,p] RTP_OFF: Periods for which VAR_NCAP.UP = 0
    RtpcsVarf: Set = None  # type: ignore[assignment] # [allreg,allyear,p,c,allts] RTPCS_VARF: The VAR_FLOs control set
    RtpVara: Set = None  # type: ignore[assignment] # [r,allyear,p] RTP_VARA: The VAR_ACT control set
    RtpVarp: Set = None  # type: ignore[assignment] # [r,t,p] RTP_VARP: RTPs that have a VAR_CAP
    RtpVintyr: Set = None  # type: ignore[assignment] # [Reg,allyear,allyear,prc] RTP_VINTYR: v/t years according to vintaging
    RtpVntbyr: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,allyear] RTP_VNTBYR: RTP_VINTYR with years swapped
    RtpTt: Set = None  # type: ignore[assignment] # [r,year,t,prc] RTP_TT: Retrofit control periods
    Rvp: Set = None  # type: ignore[assignment] # [r,allyear,p] RVP: ALIAS(RTP) for Process/time
    RtpCapyr: Set = None  # type: ignore[assignment] # [r,year,year,p] RTP_CAPYR: Capacity vintage years
    RtpIshpr: Set = None  # type: ignore[assignment] # [Reg,allyear,prc] RTP_ISHPR: Attribute existence indicator
    RtpCgc: Set = None  # type: ignore[assignment] # [r,year,p,cg,cg] RTP_CGC: Multi-purpose work set
    RtpsBd: Set = None  # type: ignore[assignment] # [r,allyear,p,s,bd] RTPS_BD: Multi-purpose work set
    CgGrp: Set = None  # type: ignore[assignment] # [Reg,prc,cg,cg] CG_GRP: Multi-purpose work set
    Fsck: Set = None  # type: ignore[assignment] # [Reg,prc,cg,c,cg] FSCK: Multi-purpose work set
    Fscks: Set = None  # type: ignore[assignment] # [Reg,prc,cg,c,cg,ts] FSCKS: Multi-purpose work set
    RpcIreio: Set = None  # type: ignore[assignment] # [r,p,c,ie,io] RPC_IREIO: Types of trade flows
    RpcLs: Set = None  # type: ignore[assignment] # [r,p,c] RPC_LS: Load sifting control
    Ele: Set = None  # type: ignore[assignment] # [r,p] ELE: Electric Power Plants
    Chp: Set = None  # type: ignore[assignment] # [r,p] CHP: Coupled Heat+Power Plants
    Hpl: Set = None  # type: ignore[assignment] # [r,p] HPL: Heat and Steam Plants
    Mreg: Set = None  # type: ignore[assignment] # [allr] MREG: Set of active regions
    Rreg: Set = None  # type: ignore[assignment] # [allreg,allreg] RREG: Set of paired regions
    Rhs: Set = None  # type: ignore[assignment] # [side] RHS:
    UcOn: Set = None  # type: ignore[assignment] # [allr,ucn] UC_ON: Active UCs by region
    UcGmax: Set = None  # type: ignore[assignment] # [UC_N,ALL_R,ITEM,C,ITEM]
    UcGmaxR: Set = None  # type: ignore[assignment] # [ALL_R,UC_N]
    UcGmapC: Set = None  # type: ignore[assignment] # [Reg,ucn,comvar,Com,ucgrptype] UC_GMAP_C: Assigning commodities to UC_GRP
    UcGmapP: Set = None  # type: ignore[assignment] # [Reg,ucn,ucgrptype,prc] UC_GMAP_P: Assigning processes to UC_GRP
    UcGmapU: Set = None  # type: ignore[assignment] # [allr,ucn,ucn] UC_GMAP_U: Assigning constraints to UC_GRP
    UcrtpSw1: Set = None  # type: ignore[assignment] # [ucgrptype,ww] UCRTPSW1: SPINES flag for which SOW(s) each UC_RTP process-type dynamic constraint applies to
    Objsw1: Set = None  # type: ignore[assignment] # [obv] OBJSW1: SPINES flag marking which objective components get the pinned-SOW EQ_OBW1 treatment
    UcJmap: Set = None  # type: ignore[assignment] # [j,ucn,side,Reg,t,prc,ucgrptype] UC_JMAP: Collecting all processes for GMAP
    UcDyndir: Set = None  # type: ignore[assignment] # [allr,ucn,side] UC_DYNDIR: Direction of dynamic constraint
    UcDs: Set = None  # type: ignore[assignment] # [allr,ucn,tslvl] UC_DS: Levels of TS-dynamic constraints
    UcQaflo: Set = None  # type: ignore[assignment] # [j,ucn,side,r,p,c] UC_QAFLO: QA_checks for UC FLO/IRE tuples
    UcRtsuc: Set = None  # type: ignore[assignment] # [allr,allyear,ucn] UC_RTSUC: RT-map for T_SUCC
    GUds: Set = None  # type: ignore[assignment] # [s,side,s] G_UDS: Timeslice-dynamic candidates
    RcCumcom: Set = None  # type: ignore[assignment] # [Reg,comvar,allyear,allyear,Com] RC_CUMCOM: Cumulative commodity PRD/NET
    RpcCumflo: Set = None  # type: ignore[assignment] # [Reg,prc,Com,allyear,allyear] RPC_CUMFLO: Cumulative process flows
    RsBelow: Set = None  # type: ignore[assignment] # [allreg,ts,ts] RS_BELOW: Timeslices stictly below a node
    RsBelow1: Set = None  # type: ignore[assignment] # [allreg,ts,ts] RS_BELOW1: Timeslices strictly one level below
    Rsp: Set = None  # type: ignore[assignment] # [*] RSP:
    RsTree: Set = None  # type: ignore[assignment] # [allreg,ts,ts] RS_TREE: Timeslice subtree
    RsPrev: Set = None  # type: ignore[assignment] # [r,s,s] RS_PREV: Previous timeslice in parent cycle
    Finest: Set = None  # type: ignore[assignment] # [r,allts] FINEST: Set of the finest timeslices in use
    Pastmile: Set = None  # type: ignore[assignment] # [allyear] PASTMILE: PAST years that are not MILESYONYR
    Eachyear: Set = None  # type: ignore[assignment] # [allyear] EACHYEAR: Each year from 1st PASTYEAR to last MILESTONYR + DUR_MAX
    Eohyears: Set = None  # type: ignore[assignment] # [allyear] EOHYEARS: Each year from 1st PASTYEAR to last MILESTONYR
    pyr: Alias = None  # type: ignore[assignment] # [*] PYR: Aliased with PASTYEAR
    v: Alias = None  # type: ignore[assignment] # [*] V: Aliased with MODLYEAR
    Miyr1: Set = None  # type: ignore[assignment] # [allyear] MIYR_1: First T
    MiyrL: Set = None  # type: ignore[assignment] # [allyear] MIYR_L: Last year
    ips: Set = None  # type: ignore[assignment] # [*] IPS:
    Lnx: Set = None  # type: ignore[assignment] # [l] LNX:
    Bdupx: Set = None  # type: ignore[assignment] # [bd] BDUPX:
    Bdlox: Set = None  # type: ignore[assignment] # [bd] BDLOX:
    Bdneq: Set = None  # type: ignore[assignment] # [bd] BDNEQ:
    RpPrc: Set = None  # type: ignore[assignment] # [r,p] RP_PRC:
    RpgRed: Set = None  # type: ignore[assignment] # [r,p,cg,io] RPG_RED:
    RpGrp: Set = None  # type: ignore[assignment] # [Reg,prc,cg] RP_GRP:
    RpCcg: Set = None  # type: ignore[assignment] # [Reg,prc,c,cg] RP_CCG:
    RpCgg: Set = None  # type: ignore[assignment] # [Reg,prc,c,cg,cg] RP_CGG:
    Trackc: Set = None  # type: ignore[assignment] # [r,c] TRACKC:
    Trackp: Set = None  # type: ignore[assignment] # [r,p] TRACKP:
    Trackpc: Set = None  # type: ignore[assignment] # [r,p,c] TRACKPC:
    Trackpg: Set = None  # type: ignore[assignment] # [r,p,cg] TRACKPG:
    Rvt: Set = None  # type: ignore[assignment] # [r,allyear,t] RVT:
    Rtpx: Set = None  # type: ignore[assignment] # [r,t,p] RTPX:
    SwTsw: Set = None  # type: ignore[assignment] #  [ALLSOW, ALLYEAR, ALLSOW] SW_TSW: 'Mapping from finest SOWs to unique SOW at each period'
    RtPp: Set = None  # type: ignore[assignment] # [r,t] RT_PP:
    u2: UniverseAlias = None  # type: ignore[assignment] # [*] U2: Aliased with *
    u3: UniverseAlias = None  # type: ignore[assignment] # [*] U3: Aliased with *
    u4: UniverseAlias = None  # type: ignore[assignment] # [*] U4: Aliased with *
    no_rt: Parameter = None  # type: ignore[assignment] # [allr,t] NO_RT:
    lead: Parameter = None  # type: ignore[assignment] # [allyear] LEAD:
    lagt: Parameter = None  # type: ignore[assignment] # [allyear] LAGT:
    fpd: Parameter = None  # type: ignore[assignment] # [allyear] FPD:
    ipd: Parameter = None  # type: ignore[assignment] # [allyear] IPD:
    rs_fr: Parameter = None  # type: ignore[assignment] # [r,s,s] RS_FR:
    js_ccl: Parameter = None  # type: ignore[assignment] # [r,j,s] JS_CCL:
    uc_com: Parameter = None  # type: ignore[assignment] # [ucn,comvar,side,Reg,allyear,Com,s,ucgrptype] UC_COM: Multiplier of VAR_COM variables
    com_cum: Parameter = None  # type: ignore[assignment] # [Reg,comvar,allyear,allyear,Com,lim] COM_CUM: Cumulative bound on commodity
    coef_af: Parameter = None  # type: ignore[assignment] # [r,allyear,t,prc,s,bd] COEF_AF: Capacity/Activity relationship
    coef_cpt: Parameter = None  # type: ignore[assignment] # [r,allyear,t,prc] COEF_CPT: Fraction of capacity available
    coef_icom: Parameter = None  # type: ignore[assignment] # [r,allyear,t,prc,c] COEF_ICOM: Commodity flow at investment time
    coef_ocom: Parameter = None  # type: ignore[assignment] # [r,allyear,t,prc,c] COEF_OCOM: Commodity flow at decommissioning time
    coef_cio: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,io] COEF_CIO: Capacity-related commodity in/out flows
    coef_ptran: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,c,cg,ts] COEF_PTRAN: Multiplier for EQ_PTRANS
    coef_rpti: Parameter = None  # type: ignore[assignment] # [r,allyear,p] COEF_RPTI: Repeated investment cycles
    coef_iled: Parameter = None  # type: ignore[assignment] # [r,allyear,p] COEF_ILED: Investment lead time
    coef_pvt: Parameter = None  # type: ignore[assignment] # [r,t] COEF_PVT: Present value of time in periods
    coef_vnt: Parameter = None  # type: ignore[assignment] # [r,t,prc,allyear] COEF_VNT: COEF_CPT with swapped indexes
    coef_cap: Parameter = None  # type: ignore[assignment] # [r,allyear,ll,p] COEF_CAP: Generic re-usable work parameter
    coef_csv: Parameter = None  # type: ignore[assignment] # [r,allyear,ll,p,allyear] COEF_CSV: Capacity transfer of simulated vintages
    coef_rtp: Parameter = None  # type: ignore[assignment] # [r,allyear,p] COEF_RTP: Generic re-usable work parameter
    coef_rvpt: Parameter = None  # type: ignore[assignment] # [r,allyear,prc,t] COEF_RVPT: Generic re-usable work parameter
    rtp_cpx: Parameter = None  # type: ignore[assignment] # [r,allyear,p,ll] RTP_CPX: Shape multipliers for capacity transfer
    ncap_afbx: Parameter = None  # type: ignore[assignment] # [r,allyear,p,bd] NCAP_AFBX: Shape multipliers for NCAP_AF factors
    ncap_afsm: Parameter = None  # type: ignore[assignment] # [r,allyear,p] NCAP_AFSM:
    rvprl: Parameter = None  # type: ignore[assignment] # [r,year,p] RVPRL:
    obj_icost: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_ICOST: NCAP_COST for each year
    obj_isub: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_ISUB: NCAP_ISUB for each year
    obj_itax: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_ITAX: NCAP_ITAX for each year
    obj_fom: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_FOM: NCAP_FOM for each year
    obj_fsb: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_FSB: NCAP_FSUB for each year
    obj_ftx: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_FTX: NCAP_FTX for each year
    obj_dcost: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_DCOST: NCAP_DCOST for each year
    obj_rfr: Parameter = None  # type: ignore[assignment] # [r,year,cur] OBJ_RFR: Risk-free rates
    obj_pvt: Parameter = None  # type: ignore[assignment] # [r,year,cur] OBJ_PVT: Present value of period
    obj_crf: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_CRF: Capital recovery factor
    obj_crfd: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_CRFD: Capital recovery factor for Decommissioning
    obj_disc: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] OBJ_DISC: Discounting factor
    obj_fsub: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s,cur] OBJ_FSUB: FLO_SUB for each year
    obj_comnt: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s,costype,cur] OBJ_COMNT: CSTNET for each year
    obj_compd: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s,costype,cur] OBJ_COMPD: CSTPRD for each year
    obj_ipric: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s,ie,cur] OBJ_IPRIC: IRE_PRICE for each year
    obj_dlagc: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_DLAGC: NCAP_DLAGC for each year
    obj_acost: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] OBJ_ACOST: ACT_COST for each year
    obj_fcost: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s,cur] OBJ_FCOST: FLO_COST for each year
    obj_fdelv: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s,cur] OBJ_FDELV: FLO_DELIV for each year
    obj_ftax: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,s,cur] OBJ_FTAX: FLO_TAX for each year
    prc_ymin: Parameter = None  # type: ignore[assignment] # [Reg,prc] PRC_YMIN: Generic process parameter
    prc_ymax: Parameter = None  # type: ignore[assignment] # [Reg,prc] PRC_YMAX: Generic process parameter
    prc_sc: Parameter = None  # type: ignore[assignment] # [Reg,prc] PRC_SC: Process storage cycles
    prc_sgl: Parameter = None  # type: ignore[assignment] # [Reg,prc] PRC_SGL: Process shadow level (< DAYNITE)
    prc_semi: Parameter = None  # type: ignore[assignment] # [r,p] PRC_SEMI: Semi-continuous indicator
    rd_nlp: Parameter = None  # type: ignore[assignment] # [r,c] RD_NLP: NLP demand indicator
    rd_shar: Parameter = None  # type: ignore[assignment] # [r,t,c,c] RD_SHAR: Demand aggregation share
    rp_afb: Parameter = None  # type: ignore[assignment] # [Reg,prc,bd] RP_AFB: Processes with NCAP_AF by bound type
    rs_stg: Parameter = None  # type: ignore[assignment] # [r,allts] RS_STG: Lead from previous storage timeslice
    rs_stgprd: Parameter = None  # type: ignore[assignment] # [r,allts] RS_STGPRD: Number of storage periods for each timeslice
    rs_stgav: Parameter = None  # type: ignore[assignment] # [r,allts] RS_STGAV: Average residence time for storage activity
    rs_tslvl: Parameter = None  # type: ignore[assignment] # [r,allts] RS_TSLVL: Timeslice levels
    ts_array: Parameter = None  # type: ignore[assignment] # [allts] TS_ARRAY: Array for leveling parameter values across timeslices
    stoa: Parameter = None  # type: ignore[assignment] # [allts] STOA: ORD Lag from each timeslice to ANNUAL
    stoal: Parameter = None  # type: ignore[assignment] # [allreg,ts] STOAL: ORD Lag from the LVL of each timeslice to ANNUAL
    bdsig: Parameter = None  # type: ignore[assignment] # [lim] BDSIG: Bound signum
    Fil: Set = None  # type: ignore[assignment] # [allyear] FIL:
    MyFil: Set = None  # type: ignore[assignment] # [allyear] MY_FIL:
    Vnt: Set = None  # type: ignore[assignment] # [allyear,allyear] VNT:
    Yk1: Set = None  # type: ignore[assignment] # [allyear,allyear] YK1:
    fil2: Parameter = None  # type: ignore[assignment] # [allyear] FIL2:
    my_fil2: Parameter = None  # type: ignore[assignment] # [allyear] MY_FIL2:
    my_array: Parameter = None  # type: ignore[assignment] # [allyear] MY_ARRAY:
    ykval: Parameter = None  # type: ignore[assignment] # [allyear,allyear] YKVAL:
    Backward: Set = None  # type: ignore[assignment] # [year] BACKWARD:
    Forward: Set = None  # type: ignore[assignment] # [year] FORWARD:
    DmYear: Set = None  # type: ignore[assignment] # [allyear] DM_YEAR:
    PyrS: Set = None  # type: ignore[assignment] # [allyear] PYR_S: Residual vintage
    MyTs: Set = None  # type: ignore[assignment] # [allts] MY_TS: Temporary set for timeslices
    RUc: Set = None  # type: ignore[assignment] # [allr,ucn] R_UC: Temporary set for UCs by region
    RUct: Set = None  # type: ignore[assignment] # [allreg,ucn,allyear] R_UCT: Set for UCs by reg & period
    UcT: Set = None  # type: ignore[assignment] # [ucn,t] UC_T: Temporary set for UCs by period
    Rxx: Set = None  # type: ignore[assignment] # [allr,*,*] RXX: General triples related to a region
    Uncd7: Set = None  # type: ignore[assignment] # [*,*,*,*,*,*,*] UNCD7: Non-domain-controlled set of 7-tuples
    life: Alias = None  # type: ignore[assignment] # [*] LIFE: Aliased with AGE
    Opyear: Set = None  # type: ignore[assignment] # [age,life] OPYEAR:
    NoAct: Set = None  # type: ignore[assignment] # [r,p] NO_ACT: Process not requiring activity variable
    RpPgact: Set = None  # type: ignore[assignment] # [r,p] RP_PGACT: Process with PCG consisting of 1 commodity
    RpPgflo: Set = None  # type: ignore[assignment] # [r,p] RP_PGFLO: Process with PCG having COM_FR
    RpXred: Set = None  # type: ignore[assignment]# [Reg,prc] RP_XRED: Process with extended reducable pcg flows
    RpcAct: Set = None  # type: ignore[assignment]# [Reg,prc,cg] RPC_ACT: PG commodity of Process with PCG consisting of 1
    RpcAflo: Set = None  # type: ignore[assignment]# [Reg,prc,cg] RPC_AFLO: ACT_FLO residual groups to be handled specially
    RpcAire: Set = None  # type: ignore[assignment]# [allreg,prc,Com] RPC_AIRE: Exchange process with only one commodity exchanged
    RpcEmis: Set = None  # type: ignore[assignment] # [r,p,comgrp] RPC_EMIS: Process with emission COM_GRP
    FsEmis: Set = None  # type: ignore[assignment]# [r,p,comgrp,c,Com] FS_EMIS: Indicator for emission related FLO_SUM
    FsEmit: Set = None  # type: ignore[assignment]# [r,p,Com,comgrp,c] FS_EMIT: Indicator for emission related FLO_SUM
    RcIop: Set = None  # type: ignore[assignment] # [r,c,io,p] RC_IOP: Processes associated with commodity
    RtcsSing: Set = None  # type: ignore[assignment] # [r,t,c,s,io] RTCS_SING: Commodity not being consumed
    RtpsOff: Set = None  # type: ignore[assignment] # [r,t,p,s] RTPS_OFF: Process being turned off
    RtpcsOut: Set = None  # type: ignore[assignment]# [r,allyear,p,c,s] RTPCS_OUT: Process flows being turned off
    RpcFfunc: Set = None  # type: ignore[assignment] # [r,p,c] RPC_FFUNC: RPC_ACT Commodity in FFUNC
    RpccFfunc: Set = None  # type: ignore[assignment]# [Reg,prc,cg,cg] RPCC_FFUNC: Pair of FFUNC commodities with RPC_ACT commodity
    PrcCap: Set = None  # type: ignore[assignment] # [Reg,prc] PRC_CAP: Process requiring capacity variable
    PrcAct: Set = None  # type: ignore[assignment] # [Reg,prc] PRC_ACT: Process requiring activity equation
    PrcTs2: Set = None  # type: ignore[assignment]# [Reg,prc,ts] PRC_TS2: Alias for PRC_TS of processes with RPC_ACT
    RpcgPtran: Set = None  # type: ignore[assignment]# [r,p,Com,c,cg,cg] RPCG_PTRAN: Set for FLO_FUNC/FLO_SUM based substitution
    KeepFlof: Set = None  # type: ignore[assignment]# [r,p,c] KEEP_FLOF: Set for FFUNC-defined flows retained
    cg3: Alias = None  # type: ignore[assignment] # [*] CG3: Aliased with COM_GRP
    cg4: Alias = None  # type: ignore[assignment] # [*] CG4: Aliased with COM_GRP
    par_flo: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,s] PAR_FLO: Flow parameter
    par_flom: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,s] PAR_FLOM: Reduced cost of flow variable
    par_ire: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,s,impexp] PAR_IRE: Parameter for im/export flow
    par_irem: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,s,impexp] PAR_IREM: Reduced cost of import/export flow
    par_objinv: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,cur] PAR_OBJINV: Annual discounted investment costs
    par_objdec: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,cur] PAR_OBJDEC: Annual discounted decommissioning costs
    par_objfix: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,cur] PAR_OBJFIX: Annual discounted FOM cost
    par_objsal: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] PAR_OBJSAL: Annual discounted salvage value
    spar_objsal: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] PAR_OBJSAL: Annual discounted salvage value
    par_objlat: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] PAR_OBJLAT: Annual discounted late costs
    par_objact: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,ts,cur] PAR_OBJACT: Annual discounted variable costs
    par_objflo: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,ts,cur] PAR_OBJFLO: Annual discounted flow costs (incl import/export)
    par_objcom: Parameter = None  # type: ignore[assignment] # [r,allyear,Com,ts,cur] PAR_OBJCOM: Annual discounted commodity costs
    par_objble: Parameter = None  # type: ignore[assignment] # [r,allyear,Com,cur] PAR_OBJBLE: Annual discounted blending costs
    par_objels: Parameter = None  # type: ignore[assignment] # [r,allyear,Com,cur] PAR_OBJELS: Annual discounted elastic demand cost term
    RpUx: Set = None  # type: ignore[assignment] # [r,p] RP_UX:
    RpPl: Set = None  # type: ignore[assignment] # [r,p,l] RP_PL:
    RtpPl: Set = None  # type: ignore[assignment] # [r,ll,p] RTP_PL:
    RpsUps: Set = None  # type: ignore[assignment] # [r,p,s] RPS_UPS:
    RpUpc: Set = None  # type: ignore[assignment] # [r,p,tsl,l] RP_UPC:
    Afups: Set = None  # type: ignore[assignment] # [r,t,p,s] AFUPS:
    RpDp: Set = None  # type: ignore[assignment] # [r,p] RP_DP:
    DpLosd: Set = None  # type: ignore[assignment] # [r,ll,p] DP_LOSD:
    FsEmcb: Set = None  # type: ignore[assignment] # [r,p,c,c] FS_EMCB:
    RpDcgg: Set = None  # type: ignore[assignment] # [r,p,c,cg,cg,l] RP_DCGG:
    RpCgc: Set = None  # type: ignore[assignment] # [Reg,prc,cg,Com] RP_CGC:
    RpcIrein: Set = None  # type: ignore[assignment] # [r,p,c,ie,io] RPC_IREIN:
    Rvps: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,ts] RVPS:
    RpsCaflac: Set = None  # type: ignore[assignment] # [r,p,s,bd] RPS_CAFLAC:
    Rvpcsl: Set = None  # type: ignore[assignment] # [r,year,p,c,s,l] RVPCSL:
    RpgAce: Set = None  # type: ignore[assignment] # [r,p,cg,io] RPG_ACE:
    RpgPace: Set = None  # type: ignore[assignment] # [r,p,cg] RPG_PACE:
    Rpg1ace: Set = None  # type: ignore[assignment] # [r,p,cg,c] RPG_1ACE:
    RpcAce: Set = None  # type: ignore[assignment] # [Reg,prc,cg] RPC_ACE:
    RvpKmap: Set = None  # type: ignore[assignment] # [r,year,p,year] RVP_KMAP:
    dumimp: Set = None  # type: ignore[assignment] # [*] DUMIMP:
    Nrgelc: Set = None  # type: ignore[assignment] # [allr,c] NRGELC: Electricity
    miyr_boh: Parameter = None  # type: ignore[assignment] # MIYR_BOH:
    rtforc: Parameter = None  # type: ignore[assignment] # [r,ll,ll,p] RTFORC:
    prc_dynuc: Parameter = None  # type: ignore[assignment] # [ucn,side,r,allyear,p,ucgrptype,bd] PRC_DYNUC:
    rpcg_ashar: Parameter = None  # type: ignore[assignment] # [r,p,cg,cg,s] RPCG_ASHAR:
    flo_ashar: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,cg,s,bd] FLO_ASHAR:
    par_ipric: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,ts,ie] PAR_IPRIC:
    spar_ipric: Parameter = None  # type: ignore[assignment] # [r,allyear,p,c,ts,ie] PAR_IPRIC:
    dp_psud: Parameter = None  # type: ignore[assignment] # [r,ll,p,upt,bd] DP_PSUD:
    coef_afups: Parameter = None  # type: ignore[assignment] # [r,year,p,s] COEF_AFUPS:
    Premile: Set = None  # type: ignore[assignment] # [allyear] PREMILE:
    putout: Parameter = None  # type: ignore[assignment] # PUTOUT:
    putgrp: Parameter = None  # type: ignore[assignment] # PUTGRP:
    errlev: Parameter = None  # type: ignore[assignment] # ERRLEV:
    startoff: Parameter = None  # type: ignore[assignment] # STARTOFF:
    endoff: Parameter = None  # type: ignore[assignment] # ENDOFF:
    Matprc: Set = None  # type: ignore[assignment] # [prcgrp] MATPRC:
    NoRvp: Set = None  # type: ignore[assignment] # [r,t,p] NO_RVP:
    IreDist: Set = None  # type: ignore[assignment] # [r,p] IRE_DIST:
    RpSgs: Set = None  # type: ignore[assignment] # [r,p] RP_SGS:
    RpSts: Set = None  # type: ignore[assignment] # [r,p] RP_STS:
    RpStl: Set = None  # type: ignore[assignment] # [r,p,tsl,l] RP_STL:
    RpsStg: Set = None  # type: ignore[assignment] # [r,p,s] RPS_STG:
    RpcStg: Set = None  # type: ignore[assignment] # [r,p,c] RPC_STG:
    RpcStgn: Set = None  # type: ignore[assignment] # [r,p,c,io] RPC_STGN:
    UcDt: Set = None  # type: ignore[assignment] # [allr,ucn] UC_DT:
    Rcs: Set = None  # type: ignore[assignment] # [Reg,Com,ts] RCS:
    RcRc: Set = None  # type: ignore[assignment] # [allreg,Com,allreg,Com] RC_RC:
    Phyr: Set = None  # type: ignore[assignment] # [allyear] PHYR:
    pastsum: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PASTSUM:
    minyr: Parameter = None  # type: ignore[assignment] # MINYR:
    Rjlvl: Set = None  # type: ignore[assignment] # [j,r,tslvl] RJLVL:
    Rlup: Set = None  # type: ignore[assignment] # [r,tsl,tsl] RLUP:
    rs_hr: Parameter = None  # type: ignore[assignment] # [r,s] RS_HR:
    my_sum: Parameter = None  # type: ignore[assignment] # MY_SUM:
    norts: Parameter = None  # type: ignore[assignment] # [r,year,s] NORTS:
    RsUp: Set = None  # type: ignore[assignment] # [r,ts,j,ts] RS_UP:
    RjSl: Set = None  # type: ignore[assignment] # [r,j,ts,ts] RJ_SL:
    Js: Set = None  # type: ignore[assignment] # [j,ts] JS:
    rs_modus: Parameter = None  # type: ignore[assignment] # [r,s,j,ts,s] RS_MODUS:
    ObjVflo: Set = None  # type: ignore[assignment] # [r,p,c,cur,UcCost] OBJ_VFLO:
    RpcCur: Set = None  # type: ignore[assignment] # [Reg,prc,Com,cur] RPC_CUR:
    x_rpsb: Parameter = None  # type: ignore[assignment] # [r,p,ts,bd,allyear] X_RPSB:
    x_rpb: Parameter = None  # type: ignore[assignment] # [r,p,bd,allyear] X_RPB:
    x_rp: Parameter = None  # type: ignore[assignment] # [r,p,allyear] X_RP:
    x_ireflo: Parameter = None  # type: ignore[assignment] # [r,p,c,ts,ie,allyear] X_IREFLO:
    x_rcs: Parameter = None  # type: ignore[assignment] # [r,c,ts,allyear] X_RCS:
    x_rpggs: Parameter = None  # type: ignore[assignment] # [r,p,cg1,cg2,ts,allyear] X_RPGGS:
    x_rpgcgs: Parameter = None  # type: ignore[assignment] # [r,p,cg1,c,cg2,ts,allyear] X_RPGCGS:
    x_rpg: Parameter = None  # type: ignore[assignment] # [r,p,cg,allyear] X_RPG:
    x_rpcl: Parameter = None  # type: ignore[assignment] # [r,p,c,bd,allyear] X_RPCL:
    x_mark: Parameter = None  # type: ignore[assignment] # [r,p,item,c,bd,allyear] X_MARK:
    x_uzrpcs: Parameter = None  # type: ignore[assignment] # [ucn,side,r,p,c,ts,allyear] X_UZRPCS:
    x_rpgsb: Parameter = None  # type: ignore[assignment] # [r,p,cg,ts,bd,allyear] X_RPGSB:
    x_rpcsl: Parameter = None  # type: ignore[assignment] # [r,p,c,ts,lim,allyear] X_RPCSL:
    x_rpcgsb: Parameter = None  # type: ignore[assignment] # [r,p,c,cg,ts,bd,allyear] X_RPCGSB:
    x_rul: Parameter = None  # type: ignore[assignment] # [allr,ucn,lim,allyear] X_RUL:
    x_rusl: Parameter = None  # type: ignore[assignment] # [allr,ucn,ts,l,allyear] X_RUSL:
    x_rpgs: Parameter = None  # type: ignore[assignment] # [r,p,cg,ts,allyear] X_RPGS:
    x_rpgcs: Parameter = None  # type: ignore[assignment] # [r,p,cg,Com,s,allyear] X_RPGCS:
    Ancat: Set = None  # type: ignore[assignment] # [UcCost, item] ANCAT:
    Subt: Set = None  # type: ignore[assignment] # [t] SUBT:
    Rtpgig: Set = None  # type: ignore[assignment] # [r,allyear,p,cg,io,cg] RTPGIG:
    RtpCg: Set = None  # type: ignore[assignment] # [r,allyear,p,cg,io] RTP_CG:
    RtpGrp: Set = None  # type: ignore[assignment] # [r,allyear,p,cg,io] RTP_GRP:
    RpGic: Set = None  # type: ignore[assignment] # [r,p,cg,io,c] RP_GIC:
    maxlife: Parameter = None  # type: ignore[assignment] # MAXLIFE:
    Agefil: Set = None  # type: ignore[assignment] # [age] AGEFIL:
    UcCapflo: Set = None  # type: ignore[assignment] # [ucn,side,r,p,c] UC_CAPFLO:
    rtcs_fr: Parameter = None  # type: ignore[assignment] # [r,t,c,s,s] RTCS_FR:
    rtcs_frmx: Parameter = None  # type: ignore[assignment] # [r,t,c,s,s] RTCS_FRMX: real storage backing RTCS_FR when S_COM_FR is defined (see RtcsFrContext)
    RpcPkc: Set = None  # type: ignore[assignment] # [r,p,c] RPC_PKC:
    rpc_pkf: Parameter = None  # type: ignore[assignment] # [r,p,c] RPC_PKF:
    ChpElc: Set = None  # type: ignore[assignment] # [r,p,c] CHP_ELC:
    Ffcks: Set = None  # type: ignore[assignment] # [Reg,prc,cg,cg,ts] FFCKS:
    Fstsl: Set = None  # type: ignore[assignment] # [tslvl,r,p,cg,cg,cg,s] FSTSL:
    RtxMark: Set = None  # type: ignore[assignment] # [r,t,item,c,bd,s] RTX_MARK:
    RxMark: Set = None  # type: ignore[assignment] # [r,year,item,c,bd] RX_MARK:
    RtpMrk: Set = None  # type: ignore[assignment] # [Reg,t,p,item,Com,bd] RTP_MRK:
    RtxMrk: Set = None  # type: ignore[assignment] # [Reg,t,item,Com,bd] RTX_MRK:
    Rmkc: Set = None  # type: ignore[assignment] # [Reg,item,Com] RMKC:
    Bdval: Set = None  # type: ignore[assignment] # [bd] BDVAL:
    ts_bd: Parameter = None  # type: ignore[assignment] # [s,bd] TS_BD:
    UcMapFlo: Set = None  # type: ignore[assignment] # [ucn,side,allreg,prc,Com] UC_MAP_FLO: Assigning processes to UC_GRP
    UcMapIre: Set = None  # type: ignore[assignment] # [ucn,allreg,prc,Com,ie] UC_MAP_IRE: Assigning processes to UC_GRP
    BleSpe: Set = None  # type: ignore[assignment] # [r,Com,spe] BLE_SPE:
    BleTp: Set = None  # type: ignore[assignment] # [r,allyear,*] BLE_TP:
    BleSpeopr: Set = None  # type: ignore[assignment] # [r,Com,spe,Opr] BLE_SPEOPR:
    BleOpr: Set = None  # type: ignore[assignment] # [r,Com,Com] BLE_OPR:
    BleInp: Set = None  # type: ignore[assignment] # [r,Com,Com] BLE_INP:
    BleSpeinp: Set = None  # type: ignore[assignment] # [r,Com,spe,Com] BLE_SPEINP:
    BleEnv: Set = None  # type: ignore[assignment] # [r,Com,Com,Opr] BLE_ENV:
    dinv: Parameter = None  # type: ignore[assignment] # [r,year,cur] DINV:
    ble_bal: Parameter = None  # type: ignore[assignment] # [r,year,c,c] BLE_BAL:
    opr2: Alias = None  # type: ignore[assignment] # [*] OPR2: Aliased with OPR
    micro: Parameter = None  # type: ignore[assignment] # MICRO:
    RpgAfcx: Set = None  # type: ignore[assignment] # [r,p,c,ie] RPG_AFCX:
    RtpShapi: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,bd,j,j,ll,ll] RTP_SHAPI:
    Cgtest: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,c,cg] CGTEST:
    Cgtes2: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,cg,c,cg] CGTES2:
    k: Alias = None  # type: ignore[assignment] # [*] K: Aliased with EACHYEAR
    CmKind: Set = None  # type: ignore[assignment] # [CM_ITEM] CM_KIND
    CmTkind: Set = None  # type: ignore[assignment]
    Y: Set = None  # type: ignore[assignment] # [allyear] Y:
    YEoh: Set = None  # type: ignore[assignment] # [allyear] Y_EOH:
    Yk: Set = None  # type: ignore[assignment] # [allyear,allyear] YK:
    TsAnn: Set = None  # type: ignore[assignment] # [s,s] TS_ANN:
    sol_bprice: Parameter = None  # type: ignore[assignment] # [Reg, allyear, Com, allts, cur] SOL_BPRICE
    sol_acfr: Parameter = None  # type: ignore[assignment] # [r, UcCost, year] SOL_ACFR
    yr_v1: Parameter = None  # type: ignore[assignment] # YR_V1:
    yr_vl: Parameter = None  # type: ignore[assignment] # YR_VL:
    acl: Parameter = None  # type: ignore[assignment] # ACL:
    span: Alias = None  # type: ignore[assignment] # [*] SPAN: Aliased with AGE
    Shedj: Set = None  # type: ignore[assignment] # [lim,j] SHEDJ: Elastic demand shape indexes
    shaped: Parameter = None  # type: ignore[assignment] # [bd,j,age] SHAPED: Elastic demand shape curves
    ob_icost: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_ICOST:
    ob_isub: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_ISUB:
    ob_itax: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_ITAX:
    ob_fom: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_FOM:
    ob_fsb: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_FSB:
    ob_ftx: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_FTX:
    ob_dcc: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_DCC:
    ob_dlc: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_DLC:
    ob_act: Parameter = None  # type: ignore[assignment] # [r,p,cur,allyear] OB_ACT:
    ob_com: Parameter = None  # type: ignore[assignment] # [r,c,s,costype,cur,allyear] OB_COM:
    ob_ire: Parameter = None  # type: ignore[assignment] # [r,p,c,s,ie,cur,allyear] OB_IRE:
    ob_fcos: Parameter = None  # type: ignore[assignment] # [r,p,c,s,cur,allyear] OB_FCOS:
    ob_fdel: Parameter = None  # type: ignore[assignment] # [r,p,c,s,cur,allyear] OB_FDEL:
    ob_ftax: Parameter = None  # type: ignore[assignment] # [r,p,c,s,cur,allyear] OB_FTAX:
    Perdinv: Set = None  # type: ignore[assignment] # [allyear,allyear] PERDINV:
    Tpulseyr: Set = None  # type: ignore[assignment] # [t,allyear] TPULSEYR:
    tpulse: Parameter = None  # type: ignore[assignment] # [allyear,allyear] TPULSE:
    obj_lint: Parameter = None  # type: ignore[assignment] # [r,t,allyear,cur] OBJ_LINT:
    obj_altv: Parameter = None  # type: ignore[assignment] # [r,t] OBJ_ALTV:
    rtp_capvl: Parameter = None  # type: ignore[assignment] # [r,year,p] RTP_CAPVL:
    rb: Parameter = None  # type: ignore[assignment] # [r,t] RB:
    r_df: Parameter = None  # type: ignore[assignment] # [r,allyear] R_DF:
    obj_wd: Parameter = None  # type: ignore[assignment] # [Reg,cur,allyear,age,allyear] OBJ_WD:
    obj_jd: Parameter = None  # type: ignore[assignment] # [Reg,cur,allyear,age] OBJ_JD:
    rtp_ffcx: Parameter = None  # type: ignore[assignment] # [Reg,allyear,allyear,prc,cg,cg] RTP_FFCX:
    rtp_ffcs: Parameter = None  # type: ignore[assignment] # [R,ALLYEAR,P,CG,CG %SWD%] RTP_FFCS:
    Agej: Set = None  # type: ignore[assignment] # [j,age] AGEJ:
    vda_disc: Parameter = None  # type: ignore[assignment] # [r,allyear] VDA_DISC:
    dp_non: Parameter = None  # type: ignore[assignment] # [r,ll,p,upt,tsl,bd] DP_NON: Bounds on non-operational time between shut-down and next start-up
    obv: Set = None  # type: ignore[assignment] # [*] OBV:
    Obvann: Set = None  # type: ignore[assignment] # [obv] OBVANN: Annualized objective components
    VAR_ACT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] VAR_ACT: Overall activity of a process
    VAS_ACT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] VAS_ACT: Overall activity of a process
    Z_ACT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_ACT ($macro Z_ACT)
    VAR_CAP: Variable = None  # type: ignore[assignment]# [r,allyear,p] VAR_CAP: Installed capacity of a process
    VAS_CAP: Variable = None  # type: ignore[assignment]# [r,allyear,p] VAS_CAP: Installed capacity of a process
    VAR_FLO: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAR_FLO: Level of process commodity flow
    VAS_FLO: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAS_FLO: Level of process commodity flow
    Z_FLO: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_FLO ($macro Z_FLO)
    VAR_IRE: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s,ie] VAR_IRE: Inter-regional trade flow
    VAS_IRE: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s,ie] VAS_IRE: Inter-regional trade flow
    Z_IRE: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_IRE ($macro Z_IRE)
    VAR_NCAP: Variable = None  # type: ignore[assignment]# [r,allyear,p] VAR_NCAP: New capacity of a process
    VAS_NCAP: Variable = None  # type: ignore[assignment]# [r,allyear,p] VAS_NCAP: New capacity of a process
    VAR_COMNET: Variable = None  # type: ignore[assignment]# [r,allyear,c,s] VAR_COMNET: Net commodity level
    VAS_COMNET: Variable = None  # type: ignore[assignment]# [r,allyear,c,s] VAS_COMNET: Net commodity level
    Z_COMNET: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_COMNET ($macro Z_COMNET)
    VAR_COMPRD: Variable = None  # type: ignore[assignment]# [r,allyear,c,s] VAR_COMPRD: Production of commodity
    VAS_COMPRD: Variable = None  # type: ignore[assignment]# [r,allyear,c,s] VAS_COMPRD: Production of commodity
    Z_COMPRD: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_COMPRD ($macro Z_COMPRD)
    VAR_ELAST: Variable = None  # type: ignore[assignment]# [r,allyear,c,s,j,bd] VAR_ELAST: Demand change due to price elasticity
    VAS_ELAST: Variable = None  # type: ignore[assignment]# [r,allyear,c,s,j,bd] VAS_ELAST: Demand change due to price elasticity
    Z_ELAST: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_ELAST ($macro Z_ELAST)
    VAR_DEM: Variable = None  # type: ignore[assignment]# [r,Milestonyr,c] VAR_DEM: Demand variable for MACRO
    VAS_DEM: Variable = None  # type: ignore[assignment]# [r,Milestonyr,c] VAS_DEM: Demand variable for MACRO
    Z_DEM: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_DEM ($macro Z_DEM)
    VAR_CUMCOM: Variable = None  # type: ignore[assignment]# [r,c,comvar,allyear,allyear] VAR_CUMCOM: Cumulative commodity PRD or NET
    VAS_CUMCOM: Variable = None  # type: ignore[assignment]# [r,c,comvar,allyear,allyear] VAS_CUMCOM: Cumulative commodity PRD or NET
    Z_CUMCOM: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_CUMCOM ($macro Z_CUMCOM)
    VAR_CUMFLO: Variable = None  # type: ignore[assignment]# [r,p,c,allyear,allyear] VAR_CUMFLO: Cumulative process flow
    VAS_CUMFLO: Variable = None  # type: ignore[assignment]# [r,p,c,allyear,allyear] VAS_CUMFLO: Cumulative process flow
    Z_CUMFLO: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_CUMFLO ($macro Z_CUMFLO)
    VAR_CUMCST: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,costagg,cur] VAR_CUMCST: Cumulative regional cost
    VAS_CUMCST: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,costagg,cur] VAS_CUMCST: Cumulative regional cost
    Z_CUMCST: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_CUMCST ($macro Z_CUMCST)
    VAR_SIN: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAR_SIN: Input flow into storage
    VAS_SIN: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAS_SIN: Input flow into storage
    Z_SIN: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_SIN ($macro Z_SIN)
    VAR_SOUT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAR_SOUT: Output flow from storage
    VAS_SOUT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] VAS_SOUT: Output flow from storage
    Z_SOUT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_SOUT ($macro Z_SOUT)
    VAR_BLND: Variable = None  # type: ignore[assignment]  # [r,allyear,Com,Com] VAR_BLND: Refinery blending
    VAS_BLND: Variable = None  # type: ignore[assignment]  # [r,allyear,Com,Com] VAS_BLND: Refinery blending
    Z_BLND: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_BLND ($macro Z_BLND)
    VAR_DAM: Variable = None  # type: ignore[assignment]  # [r,t,c,bd,j] VAR_DAM: Damage variables
    VAS_DAM: Variable = None  # type: ignore[assignment]  # [r,t,c,bd,j] VAS_DAM: Damage variables
    VAR_RCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,ll,p] VAR_RCAP: New retirements
    VAS_RCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,ll,p] VAS_RCAP: New retirements
    VAR_SCAP: Variable = None  # type: ignore[assignment]# [r,allyear,ll,p] VAR_SCAP: Cumulative retirements
    VAS_SCAP: Variable = None  # type: ignore[assignment]# [r,allyear,ll,p] VAS_SCAP: Cumulative retirements
    VAR_UPS: Variable = None  # type: ignore[assignment]  # [r,allyear,allyear,p,s,l] VAR_UPS: Start-ups
    VAS_UPS: Variable = None  # type: ignore[assignment]  # [r,allyear,allyear,p,s,l] VAS_UPS: Start-ups
    Z_UPS: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UPS ($macro Z_UPS)
    VAR_UPT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s,upt] VAR_UPT: Start-ups by type
    VAS_UPT: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s,upt] VAS_UPT: Start-ups by type
    Z_UPT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UPT ($macro Z_UPT)
    VAR_UDP: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s,l] VAR_UDP: Unit dispatching
    VAS_UDP: Variable = None  # type: ignore[assignment]# [r,allyear,allyear,p,s,l] VAS_UDP: Unit dispatching
    Z_UDP: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UDP ($macro Z_UDP)
    VAR_RLD: Variable = None  # type: ignore[assignment]  # [r,t,s,item] VAR_RLD: Residual loads
    VAS_RLD: Variable = None  # type: ignore[assignment]  # [r,t,s,item] VAS_RLD: Residual loads
    Z_RLD: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_RLD ($macro Z_RLD)
    VAR_BSPRS: Variable = None  # type: ignore[assignment]  # [r,year,t,p,c,s,l] VAR_BSPRS: Balancing services
    VAS_BSPRS: Variable = None  # type: ignore[assignment]  # [r,year,t,p,c,s,l] VAS_BSPRS: Balancing services
    VAR_ANNCST: Variable = None  # type: ignore[assignment]# [obv,r,allyear,cur] VAR_ANNCST: Annualized objective costs
    VAR_EC: Variable = None  # type: ignore[assignment]  # [r,allyear] VAR_EC: Annual energy costs in MACRO
    VAR_C: Variable = None  # type: ignore[assignment]  # [r,t] VAR_C: Annual consumption in MACRO
    VAR_CDM: Variable = None  # type: ignore[assignment]  # [r,item,ll] VAR_CDM: Climate change damage
    VAR_Y: Variable = None  # type: ignore[assignment]  # [r,t] VAR_Y: Annual production in MACRO
    VAR_K: Variable = None  # type: ignore[assignment]  # [r,t] VAR_K: Total capital
    VAR_INV: Variable = None  # type: ignore[assignment]  # [r,t] VAR_INV: Annual investments in MACRO
    VAR_D: Variable = None  # type: ignore[assignment]  # [r,t,cg] VAR_D: Annual useful demand in MACRO
    VAR_SP: Variable = None  # type: ignore[assignment]  # [r,t,cg] VAR_SP: Artificial variable for scaling shadow price
    VAR_OBJCOST: Variable = None  # type: ignore[assignment]  # [r,allyear] VAR_OBJCOST: Annual energy costs in TIMES
    VAR_XCAPP: Variable = None  # type: ignore[assignment]  # [r,year,p,j] VAR_XCAPP: Market penetration bounds - additional capacity
    VAR_MELA: Variable = None  # type: ignore[assignment]  # [r,t,cg,j,bd] VAR_MELA: Step variables for elasticities
    VAR_UTIL: Variable = None  # type: ignore[assignment]  # VAR_UTIL: Total utility
    VAR_NTX: Variable = None  # type: ignore[assignment]  # [r,t] VAR_NTX: Trade in numeraire
    VAR_OBJ: Variable = None  # type: ignore[assignment]# [r,obv,cur] VAR_OBJ: Objective costs INV,SAL,FIX,VAR,DAM
    VAS_OBJ: Variable = None  # type: ignore[assignment]# [r,obv,cur] VAS_OBJ: Objective costs INV,SAL,FIX,VAR,DAM
    Z_OBJ: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_OBJ ($macro Z_OBJ)
    VAR_OBJELS: Variable = None  # type: ignore[assignment]# [r,bd,cur] VAR_OBJELS: Change in Consumer surplus
    VAS_OBJELS: Variable = None  # type: ignore[assignment]# [r,bd,cur] VAS_OBJELS: Change in Consumer surplus
    Z_OBJELS: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_OBJELS ($macro Z_OBJELS)
    VAS_EXPOBJ: Variable = None  # type: ignore[assignment] # VAS_EXPOBJ Expected value of total OBJ
    VAS_UPDEV: Variable = None  # type: ignore[assignment]  # [allsow] VAS_UPDEV: Upside deviation of OBJ
    VAR_UC: Variable = None  # type: ignore[assignment]  # [ucn] VAR_UC: Slacks for UC constraints
    VAS_UC: Variable = None  # type: ignore[assignment]  # [ucn] VAS_UC: Slacks for UC constraints
    Z_UC: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UC ($macro Z_UC)
    VAR_UCR: Variable = None  # type: ignore[assignment]  # [ucn,r] VAR_UCR: Slacks for UCR constraints
    VAS_UCR: Variable = None  # type: ignore[assignment]  # [ucn,r] VAS_UCR: Slacks for UCR constraints
    Z_UCR: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UCR ($macro Z_UCR)
    VAR_UCT: Variable = None  # type: ignore[assignment]  # [ucn,t] VAR_UCT: Slacks for UCT constraints
    VAS_UCT: Variable = None  # type: ignore[assignment]  # [ucn,t] VAS_UCT: Slacks for UCT constraints
    Z_UCT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UCT ($macro Z_UCT)
    VAR_UCRT: Variable = None  # type: ignore[assignment]  # [ucn,r,t] VAR_UCRT: Slacks for UCRT constraints
    VAS_UCRT: Variable = None  # type: ignore[assignment]  # [ucn,r,t] VAS_UCRT: Slacks for UCRT constraints
    Z_UCRT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UCRT ($macro Z_UCRT)
    VAR_UCTS: Variable = None  # type: ignore[assignment]  # [ucn,t,s] VAR_UCTS: Slacks for UCTS constraints
    VAS_UCTS: Variable = None  # type: ignore[assignment]  # [ucn,t,s] VAS_UCTS: Slacks for UCTS constraints
    Z_UCTS: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UCTS ($macro Z_UCTS)
    VAR_UCRTS: Variable = None  # type: ignore[assignment] # [ucn,r,t,s] VAR_UCRTS: Slacks for UCRTS constraints
    VAS_UCRTS: Variable = None  # type: ignore[assignment] # [ucn,r,t,s] VAS_UCRTS: Slacks for UCRTS constraints
    Z_UCRTS: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_UCRTS ($macro Z_UCRTS)
    VAR_DNCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,p,unit] VAR_DNCAP:
    VAS_DNCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,p,unit] VAS_DNCAP:
    VAR_SNCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,p] VAR_SNCAP:
    VAS_SNCAP: Variable = None  # type: ignore[assignment]  # [r,allyear,p] VAS_SNCAP:
    eq_objann: Equation = None  # type: ignore[assignment] # EQ_OBJANN:
    eq_objbal: Equation = None  # type: ignore[assignment] # EQ_OBJBAL:
    eq_annfix: Equation = None  # type: ignore[assignment] # EQ_ANNFIX:
    eq_anninv: Equation = None  # type: ignore[assignment] # EQ_ANNINV
    eq_annvar: Equation = None  # type: ignore[assignment] # EQ_ANNVAR
    eq_util: Equation = None  # type: ignore[assignment] # EQ_UTIL
    eq_prod_y: Equation = None  # type: ignore[assignment] # EQ_PROD_Y
    eq_akl: Equation = None  # type: ignore[assignment] # EQ_AKL
    eq_labor: Equation = None  # type: ignore[assignment] # EQ_LABOR
    eq_kncap: Equation = None  # type: ignore[assignment] # EQ_KNCAP
    eq_mcap: Equation = None  # type: ignore[assignment] # EQ_MCAP
    eq_tmc: Equation = None  # type: ignore[assignment] # EQ_TMC
    eq_dd: Equation = None  # type: ignore[assignment] # EQ_DD
    eq_ivecbnd: Equation = None  # type: ignore[assignment] # EQ_IVECBND
    eq_dnlces: Equation = None  # type: ignore[assignment] # EQ_DNLCES
    eq_enscst: Equation = None  # type: ignore[assignment] # EQ_ENSCST
    eq_trdbal: Equation = None  # type: ignore[assignment] # EQ_TRDBAL
    eq_conso: Equation = None  # type: ignore[assignment] # EQ_CONSO
    eq_conda: Equation = None  # type: ignore[assignment] # EQ_CONDA
    eq_logbd: Equation = None  # type: ignore[assignment] # EQ_LOGBD
    eq_macsh: Equation = None  # type: ignore[assignment] # EQ_MACSH
    eq_macag: Equation = None  # type: ignore[assignment] # EQ_MACAG
    eq_maces: Equation = None  # type: ignore[assignment] # EQ_MACES
    eq_demsh: Equation = None  # type: ignore[assignment] # EQ_DEMSH
    eq_demag: Equation = None  # type: ignore[assignment] # EQ_DEMAG
    eq_demces: Equation = None  # type: ignore[assignment] # EQ_DEMCES
    eq_escost: Equation = None  # type: ignore[assignment] # EQ_ESCOST
    eq_mpen: Equation = None  # type: ignore[assignment] # EQ_MPEN
    eq_xcapdb: Equation = None  # type: ignore[assignment] # EQ_XCAPDB
    eq_bs00: Equation = None  # type: ignore[assignment] # EQ_BS00
    eq_bs01: Equation = None  # type: ignore[assignment] # EQ_BS01
    eq_bs02: Equation = None  # type: ignore[assignment] # EQ_BS02
    eq_bs03: Equation = None  # type: ignore[assignment] # EQ_BS03
    eq_bs04: Equation = None  # type: ignore[assignment] # EQ_BS04
    eq_bs05: Equation = None  # type: ignore[assignment] # EQ_BS05
    eq_bs07: Equation = None  # type: ignore[assignment] # EQ_BS07
    eq_bs09: Equation = None  # type: ignore[assignment] # EQ_BS09
    eq_bs10: Equation = None  # type: ignore[assignment] # EQ_BS10
    eq_bs11: Equation = None  # type: ignore[assignment] # EQ_BS11
    eq_bs18: Equation = None  # type: ignore[assignment] # EQ_BS18
    eq_bs19: Equation = None  # type: ignore[assignment] # EQ_BS19
    eq_bs22: Equation = None  # type: ignore[assignment] # EQ_BS22
    eq_bs23: Equation = None  # type: ignore[assignment] # EQ_BS23
    eq_bs24: Equation = None  # type: ignore[assignment] # EQ_BS24
    eq_bs25: Equation = None  # type: ignore[assignment] # EQ_BS25
    eq_bs26: Equation = None  # type: ignore[assignment] # EQ_BS26
    eq_bs27: Equation = None  # type: ignore[assignment] # EQ_BS27
    eq_bs28: Equation = None  # type: ignore[assignment] # EQ_BS28
    eqe_mrkprd: Equation = None  # type: ignore[assignment] # EQE_MRKPRD
    eql_mrkprd: Equation = None  # type: ignore[assignment] # EQL_MRKPRD
    eqg_mrkprd: Equation = None  # type: ignore[assignment] # EQG_MRKPRD
    eqe_mrkcon: Equation = None  # type: ignore[assignment] # EQE_MRKCON
    eql_mrkcon: Equation = None  # type: ignore[assignment] # EQL_MRKCON
    eqg_mrkcon: Equation = None  # type: ignore[assignment] # EQG_MRKCON
    eql_chpcon: Equation = None  # type: ignore[assignment] # EQL_CHPCON
    eql_chpbpt: Equation = None  # type: ignore[assignment] # EQL_CHPBPT
    eqe_chpcon: Equation = None  # type: ignore[assignment] # EQE_CHPCON
    eqe_chpbpt: Equation = None  # type: ignore[assignment] # EQE_CHPBPT
    eq_sdind_1: Equation = None  # type: ignore[assignment] # EQ_SDIND_1
    eq_sdind_0: Equation = None  # type: ignore[assignment] # EQ_SDIND_0
    eq_gr_powflo: Equation = None  # type: ignore[assignment] # EQ_GR_POWFLO
    eq_gr_ptdflo: Equation = None  # type: ignore[assignment] # EQ_GR_PTDFLO
    eq_gr_genall: Equation = None  # type: ignore[assignment] # EQ_GR_GENALL
    eq_gr_demall: Equation = None  # type: ignore[assignment] # EQ_GR_DEMALL
    eq_gr_xbnd: Equation = None  # type: ignore[assignment] # EQ_GR_XBND
    eq_gr_virtcap: Equation = None  # type: ignore[assignment] # EQ_GR_VIRTCAP
    eq_gr_virtbnd: Equation = None  # type: ignore[assignment] # EQ_GR_VIRTBND
    eq_gg_mflo: Equation = None  # type: ignore[assignment] # EQ_GG_MFLO
    eq_gg_gama: Equation = None  # type: ignore[assignment] # EQ_GG_GAMA
    eq_gg_hlip: Equation = None  # type: ignore[assignment] # EQ_GG_HLIP
    eq_gg_hlev: Equation = None  # type: ignore[assignment] # EQ_GG_HLEV
    eq_gg_step: Equation = None  # type: ignore[assignment] # EQ_GG_STEP
    eq_gg_prio: Equation = None  # type: ignore[assignment] # EQ_GG_PRIO
    eq_gg_mbnd: Equation = None  # type: ignore[assignment] # EQ_GG_MBND
    eq_gg_pdif1: Equation = None  # type: ignore[assignment] # EQ_GG_PDIF1
    eq_gg_pdif2: Equation = None  # type: ignore[assignment] # EQ_GG_PDIF2
    eq_gg_weymst: Equation = None  # type: ignore[assignment] # EQ_GG_WEYMST
    eq_gg_weymtx: Equation = None  # type: ignore[assignment] # EQ_GG_WEYMTX
    VAR_CLITOT: Variable = None  # type: ignore[assignment]  # [cmitem,ll] VAR_CLITOT: Total emissions or forcing by milestone year
    VAS_CLITOT: Variable = None  # type: ignore[assignment]  # [cmitem,ll] VAS_CLITOT: Total emissions or forcing by milestone year
    Z_CLITOT: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_CLITOT ($macro Z_CLITOT)
    VAR_CLIBOX: Variable = None  # type: ignore[assignment]  # [cmitem,CmBox,ll] VAR_CLIBOX: Quantities in the climate reservoirs
    VAS_CLIBOX: Variable = None  # type: ignore[assignment]  # [cmitem,CmBox,ll] VAS_CLIBOX: Quantities in the climate reservoirs
    Z_CLIBOX: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_CLIBOX ($macro Z_CLIBOX)
    eq_dscncap: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQ_DSCNCAP
    eq_dscone: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQ_DSCONE
    es_dscncap: Equation = None  # type: ignore[assignment]  # SPINES-only alias of EQ_DSCNCAP ($macro Q_DSCNCAP)
    es_dscone: Equation = None  # type: ignore[assignment]  # SPINES-only alias of EQ_DSCONE ($macro Q_DSCONE)
    eq_obj: Equation = None  # type: ignore[assignment]  #  EQ_OBJ: Overall Objective Function
    eq_ccdm: Equation = None  # type: ignore[assignment]  # [r,mdm,year] EQ_CCDM: Damage from climate change
    eq_utilp: Equation = None  # type: ignore[assignment]  # EQ_UTILP: Utility function
    eq_objels: Equation = None  # type: ignore[assignment]  # [r,bd,cur] EQ_OBJELS: Costs of elastic demands
    es_objels: Equation = None  # type: ignore[assignment]
    q_objels: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_OBJELS ($macro Q_OBJELS)
    eq_objfix: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJFIX: Fixed Costs
    es_objfix: Equation = None  # type: ignore[assignment]
    eq_objinv: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJINV: Investment component
    es_objinv: Equation = None  # type: ignore[assignment]
    es_obw1: Equation = None  # type: ignore[assignment]  # [obv,r,cur,allsow] ES_OBW1: SPINES pinned-SOW objective-component mapping
    eq_objsalv: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJSALV: Salvage
    es_objsalv: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJSALV: Salvage
    eq_objvar: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJVAR: Variable operating costs
    es_objvar: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJVAR: Variable operating costs
    q_objvar: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_OBJVAR ($macro Q_OBJVAR)
    eq_objdam: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJDAM: Damage costs
    es_objdam: Equation = None  # type: ignore[assignment]  # [r,cur] EQ_OBJDAM: Damage costs
    eq_clitot: Equation = None  # type: ignore[assignment]  # [cmitem,t,ll] EQ_CLITOT: Balances for the total emissions or forcing
    es_clitot: Equation = None  # type: ignore[assignment]  # [cmitem,t,ll] ES_CLITOT: Balances for the total emissions or forcing
    eq_cliconc: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t] EQ_CLICONC: Balances for the concentration in the reservoirs
    es_cliconc: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t] ES_CLICONC: Balances for the concentration in the reservoirs
    eq_clitemp: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t] EQ_CLITEMP: Balances for the temperature in the reservoirs
    es_clitemp: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t] ES_CLITEMP: Balances for the temperature in the reservoirs
    eq_clibeoh: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t,ll] EQ_CLIBEOH: Balances for the quantities in the BEOH reservoirs
    es_clibeoh: Equation = None  # type: ignore[assignment]  # [cmitem,CmBox,t,ll] ES_CLIBEOH: Balances for the quantities in the BEOH reservoirs
    eq_climax: Equation = None  # type: ignore[assignment]  # [allyear,cmitem] EQ_CLIMAX: Constraint for maximum climate quantities
    es_climax: Equation = None  # type: ignore[assignment]  # [allyear,cmitem] ES_CLIMAX: Constraint for maximum climate quantities
    eq_actflo: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQ_ACTFLO: Process Activity/Primary Commodity Flows
    es_actflo: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] ES_ACTFLO: Process Activity/Primary Commodity Flows
    eqg_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQG_ACTBND: Process activity Bound in a Period (=G=)
    esg_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQG_ACTBND: Process activity Bound in a Period (=G=)
    eqe_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQE_ACTBND: Process activity Bound in a Period (=E=)
    ese_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQE_ACTBND: Process activity Bound in a Period (=E=)
    eql_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQL_ACTBND: Process activity Bound in a Period (=L=)
    esl_actbnd: Equation = None  # type: ignore[assignment]# [r,allyear,p,s] EQL_ACTBND: Process activity Bound in a Period (=L=)
    eqg_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_BNDNET: Net bound on a commodity (=G=)
    esg_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_BNDNET: Net bound on a commodity (=G=)
    eqe_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_BNDNET: Net bound on a commodity (=E=)
    ese_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_BNDNET: Net bound on a commodity (=E=)
    eql_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQL_BNDNET: Net bound on a commodity (=L=)
    esl_bndnet: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQL_BNDNET: Net bound on a commodity (=L=)
    eqg_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_BNDPRD: Production bound on a commodity (=G=)
    esg_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_BNDPRD: Production bound on a commodity (=G=)
    eqe_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_BNDPRD: Production bound on a commodity (=E=)
    ese_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_BNDPRD: Production bound on a commodity (=E=)
    eql_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQL_BNDPRD: Production bound on a commodity (=L=)
    esl_bndprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQL_BNDPRD: Production bound on a commodity (=L=)
    eql_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQL_CAPACT: Capacity Utilzation (=L=)
    esl_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQL_CAPACT: Capacity Utilzation (=L=)
    eqe_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQE_CAPACT: Capacity Utilzation (=E=)
    ese_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQE_CAPACT: Capacity Utilzation (=E=)
    eqg_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQG_CAPACT: Capacity Utilzation (=G=)
    esg_capact: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,s] EQG_CAPACT: Capacity Utilzation (=G=)
    eql_capvac: Equation = None  # type: ignore[assignment]# [r,allyear,t,p,s,allsow] EQL_CAPVAC: Capacity Utilization (=L=)
    eqe_capvac: Equation = None  # type: ignore[assignment]# [r,allyear,t,p,s,allsow] EQE_CAPVAC: Capacity Utilization (=E=)
    eqg_capvac: Equation = None  # type: ignore[assignment]# [r,allyear,t,p,s,allsow] EQG_CAPVAC: Capacity Utilization (=G=)
    eqg_combal: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_COMBAL: Commodity Balance (=G=)
    esg_combal: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQG_COMBAL: Commodity Balance (=G=)
    eqe_combal: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_COMBAL: Commodity Balance (=E=)
    ese_combal: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_COMBAL: Commodity Balance (=E=)
    eqe_comprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_COMPRD: Commodity Production (=E=)
    ese_comprd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s] EQE_COMPRD: Commodity Production (=E=)
    eql_comces: Equation = None  # type: ignore[assignment]# [r,allyear,c,c,s] EQL_COMCES: CES substitution steps (=L=)
    esl_comces: Equation = None  # type: ignore[assignment]# [r,allyear,c,c,s] EQL_COMCES: CES substitution steps (=L=)
    eqg_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQG_CPT: Capacity Transfer (=G=)
    esg_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQG_CPT: Capacity Transfer (=G=)
    eqe_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQE_CPT: Capacity Transfer (=E=)
    ese_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQE_CPT: Capacity Transfer (=E=)
    eql_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQL_CPT: Capacity Transfer (=L=)
    esl_cpt: Equation = None  # type: ignore[assignment]  # [r,allyear,p] EQL_CPT: Capacity Transfer (=L=)
    eq_cumnet: Equation = None  # type: ignore[assignment]# [r,c,allyear,allyear] EQ_CUMNET: Cummulative Net Commodity Limit (=E=)
    es_cumnet: Equation = None  # type: ignore[assignment]# [r,c,allyear,allyear] EQ_CUMNET: Cummulative Net Commodity Limit (=E=)
    q_cumnet: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_CUMNET ($macro Q_CUMNET)
    eq_cumprd: Equation = None  # type: ignore[assignment]# [r,c,allyear,allyear] EQ_CUMPRD: Cummulative Commodity Production Limit (=E=)
    es_cumprd: Equation = None  # type: ignore[assignment]# [r,c,allyear,allyear] EQ_CUMPRD: Cummulative Commodity Production Limit (=E=)
    q_cumprd: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_CUMPRD ($macro Q_CUMPRD)
    eq_cumflo: Equation = None  # type: ignore[assignment]# [r,p,c,allyear,ll] EQ_CUMFLO: Cummulative Commodity Flow Limit (=E=)
    es_cumflo: Equation = None  # type: ignore[assignment]# [r,p,c,allyear,ll] EQ_CUMFLO: Cummulative Commodity Flow Limit (=E=)
    q_cumflo: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_CUMFLO ($macro Q_CUMFLO)
    eqg_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQG_FLOFR: Flow fraction (=G=)
    esg_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQG_FLOFR: Flow fraction (=G=)
    eqe_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQE_FLOFR: Flow fraction (=E=)
    ese_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQE_FLOFR: Flow fraction (=E=)
    eql_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQL_FLOFR: Flow fraction (=L=)
    esl_flofr: Equation = None  # type: ignore[assignment]  # [r,t,p,c,s,l] EQL_FLOFR: Flow fraction (=L=)
    eqg_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQG_FLOBND: Flow bound (=G=)
    esg_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQG_FLOBND: Flow bound (=G=)
    eqe_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQE_FLOBND: Flow bound (=E=)
    ese_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQE_FLOBND: Flow bound (=E=)
    eql_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQL_FLOBND: Flow bound (=L=)
    esl_flobnd: Equation = None  # type: ignore[assignment]  # [r,t,p,cg,s] EQL_FLOBND: Flow bound (=L=)
    eqg_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQG_INSHR: Commodity Input Group Share (=G=)
    esg_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQG_INSHR: Commodity Input Group Share (=G=)
    eqe_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQE_INSHR: Commodity Input Group Share (=E=)
    ese_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQE_INSHR: Commodity Input Group Share (=E=)
    eql_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQL_INSHR: Commodity Input Group Share (=L=)
    esl_inshr: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,cg,s] EQL_INSHR: Commodity Input Group Share (=L=)
    eq_stgips: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,item] EQ_STGIPS: Inter-period storage equation
    es_stgips: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,item] EQ_STGIPS: Inter-period storage equation
    eq_stgaux: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] EQ_STGAUX: Storage auxiliary flows
    es_stgaux: Equation = None  # type: ignore[assignment]# [r,allyear,allyear,p,c,s] EQ_STGAUX: Storage auxiliary flows
    eq_ire: Equation = None  # type: ignore[assignment]# [r,allyear,p,c,ie,s] EQ_IRE: Inter-regional Exchange Process Balance (=E=)
    es_ire: Equation = None  # type: ignore[assignment]# [r,allyear,p,c,ie,s] EQ_IRE: Inter-regional Exchange Process Balance (=E=)
    eqg_irebnd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s,allreg,ie] EQG_IREBND: Limit on Inter-regional Exchange (=G=)
    esg_irebnd: Equation = None  # type: ignore[assignment]# [r,allyear,c,s,allreg,ie] EQG_IREBND: Limit on Inter-regional Exchange (=G=)
    eqe_irebnd: Equation = None  # type: ignore[assignment] # [r,allyear,c,s,allreg,ie] EQE_IREBND: Limit on Inter-regional Exchange (=E=)
    ese_irebnd: Equation = None  # type: ignore[assignment] # [r,allyear,c,s,allreg,ie] EQE_IREBND: Limit on Inter-regional Exchange (=E=)
    eql_irebnd: Equation = None  # type: ignore[assignment] # [r,allyear,c,s,allreg,ie] EQL_IREBND: Limit on Inter-regional Exchange (=L=)
    esl_irebnd: Equation = None  # type: ignore[assignment] # [r,allyear,c,s,allreg,ie] EQL_IREBND: Limit on Inter-regional Exchange (=L=)
    eqg_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQG_XBND: Limit on Total Exchange (=G=)
    esg_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQG_XBND: Limit on Total Exchange (=G=)
    eqe_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQE_XBND: Limit on Total Exchange (=E=)
    ese_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQE_XBND: Limit on Total Exchange (=E=)
    eql_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQL_XBND: Limit on Total Exchange (=L=)
    esl_xbnd: Equation = None  # type: ignore[assignment] # [allreg,allyear,c,s,ie] EQL_XBND: Limit on Total Exchange (=L=)
    eqg_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQG_OUTSHR: Commodity Output Group Share (=G=)
    esg_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQG_OUTSHR: Commodity Output Group Share (=G=)
    eqe_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQE_OUTSHR: Commodity Output Group Share (=E=)
    ese_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQE_OUTSHR: Commodity Output Group Share (=E=)
    eql_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQL_OUTSHR: Commodity Output Group Share (=L=)
    esl_outshr: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,cg,s] EQL_OUTSHR: Commodity Output Group Share (=L=)
    eqg_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQG_FLOMRK: Process market-share (=G=)
    esg_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQG_FLOMRK: Process market-share (=G=)
    eqe_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQE_FLOMRK: Process market-share (=E=)
    ese_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQE_FLOMRK: Process market-share (=E=)
    eql_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQL_FLOMRK: Process market-share (=L=)
    esl_flomrk: Equation = None  # type: ignore[assignment] # [r,allyear,item,c,s] EQL_FLOMRK: Process market-share (=L=)
    eq_peak: Equation = None  # type: ignore[assignment] # [r,allyear,comgrp,s] EQ_PEAK: Commodity Peaking constraint (=G=)
    es_peak: Equation = None  # type: ignore[assignment] # [r,allyear,comgrp,s] EQ_PEAK: Commodity Peaking constraint (=G=)
    eq_ptrans: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,cg,s] EQ_PTRANS: Commodity-to-Commodity Transform (=E=)
    es_ptrans: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,cg,s] EQ_PTRANS: Commodity-to-Commodity Transform (=E=)
    eq_stgtss: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_STGTSS: Time-slice storage equation
    es_stgtss: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_STGTSS: Time-slice storage equation
    eq_stsbal: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,s,l] EQ_STSBAL: Time-slice storage balancer
    es_stsbal: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,s,l] EQ_STSBAL: Time-slice storage balancer
    eq_stslev: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tslvl,s,allsow] EQ_STSLEV: Time-slice storage levelizer
    es_stslev: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tslvl,s,allsow] EQ_STSLEV: Time-slice storage levelizer
    eqg_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQG_STGIN: Bound on input flow of storage (=G=)
    esg_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQG_STGIN: Bound on input flow of storage (=G=)
    eqe_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQE_STGIN: Bound on input flow of storage (=E=)
    ese_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQE_STGIN: Bound on input flow of storage (=E=)
    eql_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQL_STGIN: Bound on input flow of storage (=L=)
    esl_stgin: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQL_STGIN: Bound on input flow of storage (=L=)
    eqg_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQG_STGOUT: Bound on output flow of storage (=G=)
    esg_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQG_STGOUT: Bound on output flow of storage (=G=)
    eqe_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQE_STGOUT: Bound on output flow of storage (=E=)
    ese_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQE_STGOUT: Bound on output flow of storage (=E=)
    eql_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQL_STGOUT: Bound on output flow of storage (=L=)
    esl_stgout: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s] EQL_STGOUT: Bound on output flow of storage (=L=)
    eq_cumret: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p] EQ_CUMRET: Cumulative retirements
    es_cumret: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p] EQ_CUMRET: Cumulative retirements
    eql_refit: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,l] EQL_REFIT: Retrofit/life-extension (=L=)
    esl_refit: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,l] EQL_REFIT: Retrofit/life-extension (=L=)
    eql_scap: Equation = None  # type: ignore[assignment] # [r,allyear,p,ips] EQL_SCAP: Salvage capacity (=L=)
    esl_scap: Equation = None  # type: ignore[assignment] # [r,allyear,p,ips] EQL_SCAP: Salvage capacity (=L=)
    ql_scap: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESL_SCAP ($macro QL_SCAP)
    eq_bndcst: Equation = None  # type: ignore[assignment] # [Reg,allyear,t,allyear,costcat,cur] EQ_BNDCST: Bound on cumulative costs
    es_bndcst: Equation = None  # type: ignore[assignment] # [Reg,allyear,t,allyear,costcat,cur] EQ_BNDCST: Bound on cumulative costs
    q_bndcst: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_BNDCST ($macro Q_BNDCST)
    eqe_uc: Equation = None  # type: ignore[assignment]  # [ucn] EQE_UC: User-constraints (=E=)
    ese_uc: Equation = None  # type: ignore[assignment]  # [ucn] EQE_UC: User-constraints (=E=)
    qe_uc: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UC ($macro QE_UC)
    eqe_ucr: Equation = None  # type: ignore[assignment]  # [r,ucn] EQE_UCR: User-constraints (=E=)
    ese_ucr: Equation = None  # type: ignore[assignment]  # [r,ucn] EQE_UCR: User-constraints (=E=)
    qe_ucr: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCR ($macro QE_UCR)
    eqe_uct: Equation = None  # type: ignore[assignment]  # [ucn,t] EQE_UCT: User-constraints (=E=)
    ese_uct: Equation = None  # type: ignore[assignment]  # [ucn,t] EQE_UCT: User-constraints (=E=)
    qe_uct: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCT ($macro QE_UCT)
    eqe_ucrt: Equation = None  # type: ignore[assignment]  # [r,t,ucn] EQE_UCRT: User-constraints (=E=)
    ese_ucrt: Equation = None  # type: ignore[assignment]  # [r,t,ucn] EQE_UCRT: User-constraints (=E=)
    qe_ucrt: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCRT ($macro QE_UCRT)
    eqe_ucts: Equation = None  # type: ignore[assignment]  # [ucn,t,s] EQE_UCTS: User-constraints (=E=)
    ese_ucts: Equation = None  # type: ignore[assignment]  # [ucn,t,s] EQE_UCTS: User-constraints (=E=)
    qe_ucts: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCTS ($macro QE_UCTS)
    eqe_ucrs: Equation = None  # type: ignore[assignment]  # [r,t,ucn,tsl,s] EQE_UCRS: User-constraints (=E=)
    ese_ucrs: Equation = None  # type: ignore[assignment]  # [r,t,ucn,tsl,s] EQE_UCRS: User-constraints (=E=)
    qe_ucrs: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCRS ($macro QE_UCRS)
    eqe_ucrts: Equation = None  # type: ignore[assignment]  # [r,t,ucn,s] EQE_UCRTS: User-constraints (=E=)
    ese_ucrts: Equation = None  # type: ignore[assignment]  # [r,t,ucn,s] EQE_UCRTS: User-constraints (=E=)
    qe_ucrts: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCRTS ($macro QE_UCRTS)
    eqe_ucsu: Equation = None  # type: ignore[assignment]  # [ucn,t] EQE_UCSU: User-constraints (=E=)
    ese_ucsu: Equation = None  # type: ignore[assignment]  # [ucn,t] EQE_UCSU: User-constraints (=E=)
    qe_ucsu: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCSU ($macro QE_UCSU)
    eqe_ucsus: Equation = None  # type: ignore[assignment]  # [ucn,t,s] EQE_UCSUS: User-constraints (=E=)
    ese_ucsus: Equation = None  # type: ignore[assignment]  # [ucn,t,s] EQE_UCSUS: User-constraints (=E=)
    qe_ucsus: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCSUS ($macro QE_UCSUS)
    eqe_ucrsus: Equation = None  # type: ignore[assignment]  # [r,t,ucn,s] EQE_UCRSUS: User-constraints (=E=)
    ese_ucrsus: Equation = None  # type: ignore[assignment]  # [r,t,ucn,s] EQE_UCRSUS: User-constraints (=E=)
    qe_ucrsus: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCRSUS ($macro QE_UCRSUS)
    eqe_ucrsu: Equation = None  # type: ignore[assignment]  # [r,t,ucn] EQE_UCRSU: User-constraints (=E=)
    ese_ucrsu: Equation = None  # type: ignore[assignment]  # [r,t,ucn] EQE_UCRSU: User-constraints (=E=)
    qe_ucrsu: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ESE_UCRSU ($macro QE_UCRSU)
    eql_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQL_BLND: Blending (=L=)
    esl_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQL_BLND: Blending (=L=)
    eqg_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQG_BLND: Blending (=G=)
    esg_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQG_BLND: Blending (=G=)
    eqe_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQE_BLND: Blending (=E=)
    ese_blnd: Equation = None  # type: ignore[assignment]  # [r,year,Ble,spe,allsow] EQE_BLND: Blending (=E=)
    eqn_blnd: Equation = None  # type: ignore[assignment] # [r,year,Ble,spe,allsow] EQN_BLND: Blending non-binding
    esn_blnd: Equation = None  # type: ignore[assignment] # [r,year,Ble,spe,allsow] EQN_BLND: Blending non-binding
    eq_damage: Equation = None  # type: ignore[assignment]  # [r,t,c] EQ_DAMAGE: Damages
    es_damage: Equation = None  # type: ignore[assignment]  # [r,t,c] EQ_DAMAGE: Damages
    eq_robj: Equation = None  # type: ignore[assignment] # [r] EQ_ROBJ: Deterministic objective by region and SOW
    es_robj: Equation = None  # type: ignore[assignment] # [r] EQ_ROBJ: Deterministic objective by region and SOW
    q_robj: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_ROBJ ($macro Q_ROBJ)
    eq_sobj: Equation = None  # type: ignore[assignment]  # [lim] EQ_SOBJ: Deterministic objective by SOW
    es_sobj: Equation = None  # type: ignore[assignment]  # [lim] EQ_SOBJ: Deterministic objective by SOW
    q_sobj: Equation = None  # type: ignore[assignment]  # SPINES-only alias of ES_SOBJ ($macro Q_SOBJ)
    eq_expobj: Equation = None  # type: ignore[assignment] # [allsow] EQ_EXPOBJ: Expected value of total system cost
    es_expobj: Equation = None  # type: ignore[assignment] # [allsow] EQ_EXPOBJ: Expected value of total system cost
    eq_updev: Equation = None  # type: ignore[assignment]  # [allsow] EQ_UPDEV: Upper absolute deviation
    es_updev: Equation = None  # type: ignore[assignment]  # [allsow] EQ_UPDEV: Upper absolute deviation
    eqe_acteff: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,io,s] EQE_ACTEFF: Process Activity Efficiency (=)
    ese_acteff: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,io,s] EQE_ACTEFF: Process Activity Efficiency (=)
    eqe_caflac: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQE_CAFLAC: Commodity based availability (=E=)
    ese_caflac: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQE_CAFLAC: Commodity based availability (=E=)
    eql_caflac: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQL_CAFLAC: Commodity based availability (=L=)
    esl_caflac: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQL_CAFLAC: Commodity based availability (=L=)
    eql_capflo: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,s] EQL_CAPFLO: Flow-specific availability (=L=)
    esl_capflo: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,s] EQL_CAPFLO: Flow-specific availability (=L=)
    eqe_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQE_ASHAR: Advanced share constraint (=E=)
    ese_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQE_ASHAR: Advanced share constraint (=E=)
    eql_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQL_ASHAR: Advanced share constraint (=L=)
    esl_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQL_ASHAR: Advanced share constraint (=L=)
    eqg_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQG_ASHAR: Advanced share constraint (=G=)
    esg_ashar: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,cg,comgrp,s] EQG_ASHAR: Advanced share constraint (=G=)
    eqn_ucrtp: Equation = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype,bd] EQN_UCRTP: Dynamic process bound (=L=)
    esn_ucrtp: Equation = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype,bd] EQN_UCRTP: Dynamic process bound (=L=)
    eqe_ucrtp: Equation = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype,bd] EQE_UCRTP: Dynamic process bound (=E=)
    ese_ucrtp: Equation = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype,bd] EQE_UCRTP: Dynamic process bound (=E=)
    eqn_ucrtc: Equation = None  # type: ignore[assignment] # [ucn,comvar,r,t,c,ts,bd] EQN_UCRTC: Dynamic commodity bound (=NE=)
    esn_ucrtc: Equation = None  # type: ignore[assignment] # [ucn,comvar,r,t,c,ts,bd] EQN_UCRTC: Dynamic commodity bound (=NE=)
    eq_capload: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s,l] EQ_CAPLOAD: Augmented capacity-activity
    es_capload: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s,l] EQ_CAPLOAD: Augmented capacity-activity
    eq_actramp: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s,l] EQ_ACTRAMP: Activity ramping equations
    es_actramp: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s,l] EQ_ACTRAMP: Activity ramping equations
    eqe_actups: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQE_ACTUPS: Activity startup equations
    ese_actups: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQE_ACTUPS: Activity startup equations
    eql_actups: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQL_ACTUPS: Activity offline balance
    esl_actups: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQL_ACTUPS: Activity offline balance
    eql_actupc: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQL_ACTUPC: Activity cycling constraints
    esl_actupc: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,tsl,l,s] EQL_ACTUPC: Activity cycling constraints
    eq_actpl: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_ACTPL: Activity partial loads
    es_actpl: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_ACTPL: Activity partial loads
    eq_actrmpc: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_ACTRMPC: Activity ramping costs
    es_actrmpc: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,s] EQ_ACTRMPC: Activity ramping costs
    eql_stgccl: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,allsow] EQL_STGCCL: Storage cycling constraints
    esl_stgccl: Equation = None  # type: ignore[assignment] # [r,allyear,allyear,p,allsow] EQL_STGCCL: Storage cycling constraints
    eq_slsift: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s,l,l] EQ_SLSIFT: Time-slice load sifting
    es_slsift: Equation = None  # type: ignore[assignment] # [r,allyear,p,c,s,l,l] EQ_SLSIFT: Time-slice load sifting
    eq_sdlogic: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,l,allsow] eq_sdlogic: Logical relationship between decision variables
    es_sdlogic: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,l,allsow] eq_sdlogic: Logical relationship between decision variables
    eq_sudupt: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,upt,allsow] eq_sudupt: Selection of start up type a according to non-operational time
    es_sudupt: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,upt,allsow] eq_sudupt: Selection of start up type a according to non-operational time
    eq_sdslant: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,allsow] eq_sdslant: Slanting equation for start-up and shut-down phase
    es_sdslant: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,allsow] eq_sdslant: Slanting equation for start-up and shut-down phase
    eq_sdminon: Equation = None  # type: ignore[assignment] # [r,ll,t,p,s,allsow] eq_sdminon: Minimum on-line capacity constraints
    es_sdminon: Equation = None  # type: ignore[assignment] # [r,ll,t,p,s,allsow] eq_sdminon: Minimum on-line capacity constraints
    eq_sudload: Equation = None  # type: ignore[assignment] # [r,ll,t,p,s,allsow] eq_sudload: Load during start-up/shut down phase of the unit (linear growth)
    es_sudload: Equation = None  # type: ignore[assignment] # [r,ll,t,p,s,allsow] eq_sudload: Load during start-up/shut down phase of the unit (linear growth)
    eq_sudtime: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,bd,allsow] eq_sudtime: Minimum on-line / off-line time constraint
    es_sudtime: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,bd,allsow] eq_sudtime: Minimum on-line / off-line time constraint
    eq_sudpll: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,allsow] eq_sudpll: Efficiency losses due to start-up/shut-down of the unit
    es_sudpll: Equation = None  # type: ignore[assignment] # [r,ll,t,p,tsl,s,allsow] eq_sudpll: Efficiency losses due to start-up/shut-down of the unit
    eqg_ucmax: Equation = None  # type: ignore[assignment] # [ucn,allr,item,c,*] EQG_UCMAX: Maximum group-wise flow (G)
    esg_ucmax: Equation = None  # type: ignore[assignment] # [ucn,allr,item,c,*] EQG_UCMAX: Maximum group-wise flow (G)
    eqg_ucsumax: Equation = None  # type: ignore[assignment] # [ucn] EQG_UCSUMAX: Maximum group-wise flow over regions (G)
    esg_ucsumax: Equation = None  # type: ignore[assignment] # [ucn] EQG_UCSUMAX: Maximum group-wise flow over regions (G)
    eq_rl_load: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_LOAD: Total dispatchable residual loads
    es_rl_load: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_LOAD: Total dispatchable residual loads
    eq_rl_ndis: Equation = None  # type: ignore[assignment] # [r,t,s,item] EQ_RL_NDIS: Non-dispatchable loads by group
    es_rl_ndis: Equation = None  # type: ignore[assignment] # [r,t,s,item] EQ_RL_NDIS: Non-dispatchable loads by group
    eq_rl_stcap: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_STCAP: Minimum available storage capacity
    es_rl_stcap: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_STCAP: Minimum available storage capacity
    eq_rl_pkcap: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_PKCAP: Minimum dispatchable reserve during peak
    es_rl_pkcap: Equation = None  # type: ignore[assignment] # [r,t,s] EQ_RL_PKCAP: Minimum dispatchable reserve during peak
    eq_rl_thmin: Equation = None  # type: ignore[assignment] # [r,t,s,bd] EQ_RL_THMIN: Aggregate thermal minimum constraint
    es_rl_thmin: Equation = None  # type: ignore[assignment] # [r,t,s,bd] EQ_RL_THMIN: Aggregate thermal minimum constraint
    sum_obj: Parameter = None  # type: ignore[assignment]  # [item,item] SUM_OBJ: Objective component summation
    KEoh: Set = None  # type: ignore[assignment] # [allyear] K_EOH:
    Ktyage: Set = None  # type: ignore[assignment] # [ll,year,ll,age] KTYAGE:
    Obj1a: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_1A:
    Obj1b: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_1B:
    Obj2a: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_2A:
    Obj2b: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_2B:
    ObjSums: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_SUMS:
    ObjSums3: Set = None  # type: ignore[assignment] # [r,allyear,p] OBJ_SUMS3:
    ObjSumsi: Set = None  # type: ignore[assignment] # [r,allyear,p,allyear] OBJ_SUMSI:
    jot: Alias = None  # type: ignore[assignment] # [*] JOT: Aliased with AGE
    obj_c: Parameter = None  # type: ignore[assignment] # OBJ_C:
    obj_d: Parameter = None  # type: ignore[assignment] # OBJ_D:
    ObjSumii: Set = None  # type: ignore[assignment] # [r,allyear,p,age,allyear,age] OBJ_SUMII:
    ObjSumiii: Set = None  # type: ignore[assignment] # [r,allyear,p,allyear,year,allyear] OBJ_SUMIII:
    ObjYes: Set = None  # type: ignore[assignment] # [Reg,allyear,p] OBJ_YES:
    ObjI2: Set = None  # type: ignore[assignment] # [Reg,allyear,p] OBJ_I2:
    Ykage: Set = None  # type: ignore[assignment] # [allyear,allyear,age] YKAGE:
    Kage: Set = None  # type: ignore[assignment] # [allyear,age] KAGE:
    ObjSpred: Set = None  # type: ignore[assignment] # [r,allyear,p,age] OBJ_SPRED:
    Invstep: Set = None  # type: ignore[assignment] # [allyear,age,allyear,age] INVSTEP:
    Invspred: Set = None  # type: ignore[assignment] # [allyear,age,allyear,allyear] INVSPRED:
    obj_pasti: Parameter = None  # type: ignore[assignment] # [Reg,allyear,p,cur] OBJ_PASTI:
    salv_inv: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,allyear] SALV_INV:
    cor_salvi: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] COR_SALVI:
    cor_salvd: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] COR_SALVD:
    obj_divi: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] OBJ_DIVI:
    obj_diviii: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] OBJ_DIVIII:
    stp_div: Parameter = None  # type: ignore[assignment] # [j,r,t,p] STP_DIV:
    # solve.stp (stepped solution) scratch symbols
    presol: Parameter = None  # type: ignore[assignment] # PRESOL:
    UcRn: Set = None  # type: ignore[assignment] # [ucn,allr] UC_RN:
    RtpIre: Set = None  # type: ignore[assignment] # [r,t,p,ie] RTP_IRE: IRE equations with fixed regions
    IreRpr: Set = None  # type: ignore[assignment] # [r,p,r,ie] IRE_RPR: All regions REG linked to IRE process by equations in R
    IreFxt: Set = None  # type: ignore[assignment] # [r,t,p] IRE_FXT: IRE with some linked regions fixed at T
    stp_uct: Parameter = None  # type: ignore[assignment] # [j,allr,ucnA,ll] STP_UCT:
    uc_bnd: Parameter = None  # type: ignore[assignment] # [j,allr,ucnA,ll,s,lA] UC_BND:
    par_ucr: Parameter = None  # type: ignore[assignment] # [ucn,allr] PAR_UCR:
    ObjIdc: Set = None  # type: ignore[assignment] # [r,allyear,p,life,allyear,age] OBJ_IDC:
    obj_iad: Parameter = None  # type: ignore[assignment] # [r,cur] OBJ_IAD:
    ObjFcur: Set = None  # type: ignore[assignment] # [Reg,allyear,p,cur] OBJ_FCUR:
    ObjSumiv: Set = None  # type: ignore[assignment] # [allyear,r,allyear,p,age,age] OBJ_SUMIV:
    ObjSumivs: Set = None  # type: ignore[assignment] # [r,allyear,p,allyear,allyear] OBJ_SUMIVS:
    RtpShape: Set = None  # type: ignore[assignment] # [Reg,allyear,prc,j,j,j] RTP_SHAPE:
    obj_diviv: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] OBJ_DIVIV:
    obj_life: Parameter = None  # type: ignore[assignment] # [allyear,Reg,age,age,cur] OBJ_LIFE:
    salv_dec: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] SALV_DEC:
    objscc: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc,cur] OBJSCC:
    objsic: Parameter = None  # type: ignore[assignment] # [Reg,allyear,prc] OBJSIC:
    obj_dceoh: Parameter = None  # type: ignore[assignment] # [Reg,cur] OBJ_DCEOH:
    ObjSali: Set = None  # type: ignore[assignment] # [r,allyear,p,age,year,age,allyear,year] OBJ_SALI:
    Afs: Set = None  # type: ignore[assignment] # [r,t,p,s,bd] AFS:
    Afsv: Set = None  # type: ignore[assignment] # [r,t,p,s,bd] AFSV: AFS entries handled by the simplified-vintaging capacity utilization equation
    Superyr: Set = None  # type: ignore[assignment] # [t,allyear] SUPERYR: SUpremum PERiod YeaR
    Ykk: Set = None  # type: ignore[assignment] # [allyear,allyear,allyear] YKK:
    RtpIan: Set = None  # type: ignore[assignment] # [Reg,t,p,cur] RTP_IAN:
    RtIan: Set = None  # type: ignore[assignment] # [Reg,allyear,allyear,cur,costagg] RT_IAN:
    cst_annc: Parameter = None  # type: ignore[assignment] # [r,allyear,p,allyear,ucname,cur] CST_ANNC:
    CostGmap: Set = None  # type: ignore[assignment] # [costagg,costagg,costype] COST_GMAP:
    Rvpt: Set = None  # type: ignore[assignment] # [r,allyear,p,t] RVPT:
    UcRhstmp: Set = None  # type: ignore[assignment] # [Reg,ucn,t,s,ucnumber] UC_RHSTMP:
    UcRhsmap: Set = None  # type: ignore[assignment] # [Reg,t,ucn,ucnumber,s] UC_RHSMAP:
    Ructs: Set = None  # type: ignore[assignment] # [allreg,ucn,allyear,ts] RUCTS:
    UcUt: Set = None  # type: ignore[assignment] # [ucn,allyear] UC_UT:
    UcUts: Set = None  # type: ignore[assignment] # [ucn,allyear,ts] UC_UTS:
    UcTmap: Set = None  # type: ignore[assignment] # [year,year,t,side,UcDynt] UC_TMAP:
    dp_uns: Parameter = None  # type: ignore[assignment] # [r,ll,t,p,tsl,ips,l] DP_UNS:
    uc2: Alias = None  # type: ignore[assignment] # [*] UC2: Universe Alias
    uc3: Alias = None  # type: ignore[assignment] # [*] UC3: Universe Alias
    uc4: Alias = None  # type: ignore[assignment] # [*] UC4: Universe Alias
    Qastat: Set = None  # type: ignore[assignment] # [j] QASTAT:
    adesc: Set = None  # type: ignore[assignment] # [*] ADESC: Attribute Descriptions
    ire: Set = None  # type: ignore[assignment] #  iRE: Inter-regional Exchange (Exports & Imports)
    Irelx: Set = None  # type: ignore[assignment] # [ire] IRELX: Electricity Exchange Processes
    Irenx: Set = None  # type: ignore[assignment] # [ire] IRENX: Enodogenous Trade Exchange
    Stg: Set = None  # type: ignore[assignment] # [ire] STG: Storage Processes (genuine)
    Sts: Set = None  # type: ignore[assignment] # [ire] STS: General Multilevel Storage
    Rcap: Set = None  # type: ignore[assignment] # [ire] RCAP: Processes with Retirements
    Nst: Set = None  # type: ignore[assignment] # [ire] NST: Night Storage
    Dmd: Set = None  # type: ignore[assignment] # [r,p] DMD: Demand Devices
    Pre: Set = None  # type: ignore[assignment] # [r,p] PRE: Energy Processes
    Prw: Set = None  # type: ignore[assignment] # [r,p] PRW: Material Processes - Weight
    Prv: Set = None  # type: ignore[assignment] # [r,p] PRV: Material Processes - Volume
    Distr: Set = None  # type: ignore[assignment] # [r,p] DISTR: Distribution Technologies
    Renew: Set = None  # type: ignore[assignment] # [r,p] RENEW: Renewables Processes
    Xtract: Set = None  # type: ignore[assignment] # [r,p] XTRACT: Extraction Processes
    Res: Set = None  # type: ignore[assignment] # [r,Com] RES: Residential Sector Demands
    Comm: Set = None  # type: ignore[assignment] # [r,Com] COMM: Commercial Sector Demands
    Trn: Set = None  # type: ignore[assignment] # [r,Com] TRN: Transporation Sector Demands
    Agr: Set = None  # type: ignore[assignment] # [Reg,Com] AGR: Agriculature Sector Demands
    Othd: Set = None  # type: ignore[assignment] # [r,Com] OTHD: Other Demands
    Ind: Set = None  # type: ignore[assignment] # [Reg,Com] IND: Industrial Demands
    Nrgfos: Set = None  # type: ignore[assignment] # [r,c] NRGFOS: Fossil
    Nrgren: Set = None  # type: ignore[assignment] # [r,c] NRGREN: Renewable
    Nrgsyn: Set = None  # type: ignore[assignment] # [r,c] NRGSYN: Synthetic
    Nrghet: Set = None  # type: ignore[assignment] # [allr,c] NRGHET: Heat
    Rs: Set = None  # type: ignore[assignment] # [r,allts] RS:
    nonset: Set = None  # type: ignore[assignment] # [*] NONSET:
    pluset: Set = None  # type: ignore[assignment] # [*] PLUSET:
    Othcom: Set = None  # type: ignore[assignment] # [item] OTHCOM:
    RegAct: Set = None  # type: ignore[assignment] # [item,c] REG_ACT:
    UcConst: Set = None  # type: ignore[assignment] # [*,ucn] UC_CONST: Genuine TIMES UC constraints
    UcMarks: Set = None  # type: ignore[assignment] # [r,item] UC_MARKS: PRC_MARK Share UC constraints
    UcDynbd: Set = None  # type: ignore[assignment] # [r,ucn] UC_DYNBD: Dynamic UC bound constraints
    sysuc: Set = None  # type: ignore[assignment] # [*] SYSUC:
    Sysucmap: Set = None  # type: ignore[assignment] # [sysuc,*] SYSUCMAP:
    ww: Alias = None  # type: ignore[assignment] # [*] WW: Aliased with ALLSOW
    rtp_obj: Parameter = None  # type: ignore[assignment] # [j,r,allyear,p,cur] RTP_OBJ:
    rtp_npv: Parameter = None  # type: ignore[assignment] # [j,r,allyear,p,cur] RTP_NPV:
    par_actc: Parameter = None  # type: ignore[assignment] # [j,r,ll,t,p,c,cur] PAR_ACTC:
    par_floc: Parameter = None  # type: ignore[assignment] # [j,r,ll,t,p,c,cur] PAR_FLOC:
    par_comc: Parameter = None  # type: ignore[assignment] # [j,r,t,c,cur] PAR_COMC:
    par_rpmx: Parameter = None  # type: ignore[assignment] # [r,p,j,ll,t,c,cur] PAR_RPMX:
    par_rcmx: Parameter = None  # type: ignore[assignment] # [r,c,j,t,cur] PAR_RCMX:
    par_objcap: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] PAR_OBJCAP:
    par_xpri: Parameter = None  # type: ignore[assignment] # [r,t,p,c,ts,Reg,Com] PAR_XPRI:
    coef_objinv: Parameter = None  # type: ignore[assignment] # [r,allyear,prc] COEF_OBJINV:
    coef_obinv: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] COEF_OBINV:
    coef_obfix: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] COEF_OBFIX:
    coef_obinvn: Parameter = None  # type: ignore[assignment] # [r,year,p,cur] COEF_OBINVN:
    coef_obfixn: Parameter = None  # type: ignore[assignment] # [r,year,p,cur] COEF_OBFIXN:
    coef_crf: Parameter = None  # type: ignore[assignment] # [r,allyear,p,cur] COEF_CRF:
    var_ncaprng: Parameter = None  # type: ignore[assignment] # [r,allyear,p,bd] VAR_NCAPRNG:
    cstvnt: Parameter = None  # type: ignore[assignment] # [j,r,ll,year,p,sysuc] CSTVNT:
    cstvpj: Parameter = None  # type: ignore[assignment] # [r,ll,p,j,sysuc,year] CSTVPJ:
    f_vio: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,io] F_VIO:
    f_ios: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s] F_IOS:
    f_inout: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,io] F_INOUT:
    f_inouts: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s,io] F_INOUTS:
    reg_obj: Parameter = None  # type: ignore[assignment] # [Reg] REG_OBJ:
    bc_invact: Parameter = None  # type: ignore[assignment] # [r,allyear,ll,prc,s] BC_INVACT:
    bc_invtot: Parameter = None  # type: ignore[assignment] # [r,allyear,prc] BC_INVTOT:
    val_flo: Parameter = None  # type: ignore[assignment] # [r,allyear,ll,prc,c] VAL_FLO:
    par_rtcs: Parameter = None  # type: ignore[assignment] # [r,t,c,s] PAR_RTCS:
    par_top: Parameter = None  # type: ignore[assignment] # [r,t,p,c,io] PAR_TOP:
    NcapYes: Set = None  # type: ignore[assignment] # [r,allyear,p] NCAP_YES:
    FIoset: Set = None  # type: ignore[assignment] # [r,allyear,t,p,c,s,io] F_IOSET:
    Rvtpc: Set = None  # type: ignore[assignment] # [r,allyear,t,p,c] RVTPC:
    Rttc: Set = None  # type: ignore[assignment] # [r,allyear,c] RTTC:
    pastcv: Set = None  # type: ignore[assignment] # [*] PASTCV:
    rpm: Set = None  # type: ignore[assignment] # [*] RPM:
    Rnglim: Set = None  # type: ignore[assignment] # [sysuc] RNGLIM:
    Sysinv: Set = None  # type: ignore[assignment] # [sysuc] SYSINV:
    Sucmap: Set = None  # type: ignore[assignment] # [j,sysuc] SUCMAP:
    Rngmap: Set = None  # type: ignore[assignment] # [sysuc,bd] RNGMAP:
    vdisc: Parameter = None  # type: ignore[assignment] # VDISC:
    obj_sumik: Parameter = None  # type: ignore[assignment] # [Reg, allyear, prc, cur] OBJ_SUMIK
    ykagep: Parameter = None  # type: ignore[assignment] # [allyear, allyear, age] YKAGEP
    objval_1: Parameter = None  # type: ignore[assignment] # OBJVAL_1:
    objval_2: Parameter = None  # type: ignore[assignment] # OBJVAL_2:
    sysone: Parameter = None  # type: ignore[assignment] # [sysuc] SYSONE:
    sysplit: Parameter = None  # type: ignore[assignment] # [sysuc] SYSPLIT:
    cst_pvc: Parameter = None  # type: ignore[assignment] # [sysuc,r,c] CST_PVC:
    scst_pvc: Parameter = None  # type: ignore[assignment] # [sysuc,r,c] SCST_PVC:
    cst_pvp: Parameter = None  # type: ignore[assignment] # [sysuc,r,p] CST_PVP:
    scst_pvp: Parameter = None  # type: ignore[assignment] # [sysuc,r,p] SCST_PVP:
    f_in: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s] F_IN:
    sf_in: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s] SF_IN:
    f_out: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s] F_OUT:
    sf_out: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c,s] SF_OUT:
    p_out: Parameter = None  # type: ignore[assignment] # [r,t,p,c,s] P_OUT:
    sp_out: Parameter = None  # type: ignore[assignment] # [r,t,p,c,s] SP_OUT:
    agg_out: Parameter = None  # type: ignore[assignment] # [r,t,c,ts] AGG_OUT:
    sagg_out: Parameter = None  # type: ignore[assignment] # [r,t,c,ts] SAGG_OUT:
    par_actl: Parameter = None  # type: ignore[assignment] # [r,ll,ll,p,s] PAR_ACTL:
    spar_actl: Parameter = None  # type: ignore[assignment] # [r,ll,ll,p,s] PAR_ACTL:
    par_actm: Parameter = None  # type: ignore[assignment] # [r,ll,ll,p,s] PAR_ACTM:
    spar_actm: Parameter = None  # type: ignore[assignment] # [r,ll,ll,p,s] PAR_ACTM:
    par_pasti: Parameter = None  # type: ignore[assignment] # [r,t,p,item] PAR_PASTI:
    spar_pasti: Parameter = None  # type: ignore[assignment] # [r,t,p,item] PAR_PASTI:
    par_capl: Parameter = None  # type: ignore[assignment] # [r,year,p] PAR_CAPL:
    spar_capl: Parameter = None  # type: ignore[assignment] # [r,year,p] PAR_CAPL:
    par_capm: Parameter = None  # type: ignore[assignment] # [r,year,p] PAR_CAPM:
    spar_capm: Parameter = None  # type: ignore[assignment] # [r,year,p] PAR_CAPM:
    par_capbd: Parameter = None  # type: ignore[assignment] # [r,year,p,bd] PAR_CAPBD:
    spar_capbd: Parameter = None  # type: ignore[assignment] # [r,year,p,bd] PAR_CAPBD:
    par_cumret: Parameter = None  # type: ignore[assignment] # [r,year,year,p] PAR_CUMRET:
    spar_cumret: Parameter = None  # type: ignore[assignment] # [r,year,year,p] PAR_CUMRET:
    par_ncapl: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PAR_NCAPL:
    spar_ncapl: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PAR_NCAPL:
    par_ncapm: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PAR_NCAPM:
    spar_ncapm: Parameter = None  # type: ignore[assignment] # [r,allyear,p] PAR_NCAPM:
    par_ncapr: Parameter = None  # type: ignore[assignment] # [r,allyear,p,item] PAR_NCAPR:
    spar_ncapr: Parameter = None  # type: ignore[assignment] # [r,allyear,p,item] PAR_NCAPR:
    par_comprdl: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMPRDL:
    spar_comprdl: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMPRDL:
    par_comprdm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMPRDM:
    spar_comprdm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMPRDM:
    par_comnetl: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMNETL:
    spar_comnetl: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMNETL:
    par_comnetm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMNETM:
    spar_comnetm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMNETM:
    par_combalem: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMBALEM:
    spar_combalem: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMBALEM:
    par_combalgm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMBALGM:
    spar_combalgm: Parameter = None  # type: ignore[assignment] # [r,allyear,c,s] PAR_COMBALGM:
    par_peakm: Parameter = None  # type: ignore[assignment] # [r,allyear,cg,s] PAR_PEAKM:
    spar_peakm: Parameter = None  # type: ignore[assignment] # [r,allyear,cg,s] PAR_PEAKM:
    par_ucsl: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCSL:
    spar_ucsl: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCSL:
    par_ucsm: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCSM:
    spar_ucsm: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCSM:
    par_rtus: Parameter = None  # type: ignore[assignment] # [r,year,ucn,s] PAR_RTUS: par_uc.rpt working parameter
    par_urts: Parameter = None  # type: ignore[assignment] # [ucn,r,year,s] PAR_URTS: par_uc.rpt working parameter
    par_ucmrk: Parameter = None  # type: ignore[assignment] # [r,t,item,c,s] PAR_UCMRK:
    spar_ucmrk: Parameter = None  # type: ignore[assignment] # [r,t,item,c,s] PAR_UCMRK:
    par_ucmax: Parameter = None  # type: ignore[assignment] # [ucn,allr,item,c] PAR_UCMAX:
    spar_ucmax: Parameter = None  # type: ignore[assignment] # [ucn,allr,item,c] PAR_UCMAX:
    par_cumflol: Parameter = None  # type: ignore[assignment] # [r,p,c,ll,ll] PAR_CUMFLOL:
    spar_cumflol: Parameter = None  # type: ignore[assignment] # [r,p,c,ll,ll] PAR_CUMFLOL:
    par_cumflom: Parameter = None  # type: ignore[assignment] # [r,p,c,ll,ll] PAR_CUMFLOM:
    spar_cumflom: Parameter = None  # type: ignore[assignment] # [r,p,c,ll,ll] PAR_CUMFLOM:
    par_cumcst: Parameter = None  # type: ignore[assignment] # [r,ll,ll,costagg,cur] PAR_CUMCST:
    spar_cumcst: Parameter = None  # type: ignore[assignment] # [r,ll,ll,costagg,cur] PAR_CUMCST:
    par_ucrtp: Parameter = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype] PAR_UCRTP:
    spar_ucrtp: Parameter = None  # type: ignore[assignment] # [ucn,r,t,p,ucgrptype] PAR_UCRTP:
    reg_wobj: Parameter = None  # type: ignore[assignment] # [Reg,item,cur] REG_WOBJ:
    sreg_wobj: Parameter = None  # type: ignore[assignment] # [Reg,item,cur] REG_WOBJ:
    reg_irec: Parameter = None  # type: ignore[assignment] # [Reg] REG_IREC:
    sreg_irec: Parameter = None  # type: ignore[assignment] # [Reg] REG_IREC:
    reg_acost: Parameter = None  # type: ignore[assignment] # [r,allyear,item] REG_ACOST:
    sreg_acost: Parameter = None  # type: ignore[assignment] # [r,allyear,item] REG_ACOST:
    cst_invc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,sysuc] CST_INVC:
    scst_invc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,sysuc] CST_INVC:
    cst_invx: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,sysuc] CST_INVX:
    scst_invx: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,sysuc] CST_INVX:
    cst_decc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_DECC:
    scst_decc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_DECC:
    cst_fixc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_FIXC:
    scst_fixc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_FIXC:
    cst_fixx: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_FIXX:
    scst_fixx: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p] CST_FIXX:
    cst_actc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,rpm] CST_ACTC:
    scst_actc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,rpm] CST_ACTC:
    cst_floc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_FLOC:
    scst_floc: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_FLOC:
    cst_flox: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_FLOX:
    scst_flox: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_FLOX:
    cst_irec: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_IREC:
    scst_irec: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] CST_IREC:
    cst_comc: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COMC:
    scst_comc: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COMC:
    cst_comx: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COMX:
    scst_comx: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COMX:
    cst_come: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COME:
    scst_come: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_COME:
    cst_salv: Parameter = None  # type: ignore[assignment] # [r,allyear,p] CST_SALV:
    par_caplo: Parameter = None  # type: ignore[assignment] # [r,t,p] PAR_CAPLO
    par_capup: Parameter = None  # type: ignore[assignment] # [r,t,p] PAR_CAPUP
    par_uclom: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCLOM
    par_ucupm: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCUPM
    par_ucfxm: Parameter = None  # type: ignore[assignment] # [ucn,*,*,*] PAR_UCFXM
    tot_inv: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_INV: Total annual disocunted investment costs
    tot_dec: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_DEC: Total annual disocunted decommissioning costs
    tot_fix: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_FIX: Total annual disocunted FOM costs
    tot_sal: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_SAL: Total annual disocunted salvage value
    tot_lat: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_LAT: Total annual disocunted late costs
    tot_act: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_ACT: Total annual disocunted variable costs
    tot_com: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_COM: Total annual disocunted commodity costs
    tot_flo: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_FLO: Total annual disocunted flow costs
    tot_ble: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_BLE: Total annual disocunted blending costs
    tot_obj: Parameter = None  # type: ignore[assignment] # [r,allyear,cur] TOT_OBJ: Annual discounted objective value
    tot_objv: Parameter = None  # type: ignore[assignment] # [r,allyear] TOT_OBJV
    cst_invv: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p] CST_INVV
    cst_decv: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p] CST_DECV
    cst_fixv: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p] CST_FIXV
    cst_latv: Parameter = None  # type: ignore[assignment] # [r,allyear,p] CST_LATV
    cst_actv: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,ts] CST_ACTV
    cst_flov: Parameter = None  # type: ignore[assignment] # [r,allyear,allyear,p,c,ts] CST_FLOV
    cst_comv: Parameter = None  # type: ignore[assignment] # [r,allyear,c,ts] CST_COMV
    cst_elsv: Parameter = None  # type: ignore[assignment] # [r,allyear,c] CST_ELSV
    scst_salv: Parameter = None  # type: ignore[assignment] # [r,allyear,p] CST_SALV:
    cst_time: Parameter = None  # type: ignore[assignment] # [r,allyear,s,sysuc] CST_TIME:
    scst_time: Parameter = None  # type: ignore[assignment] # [r,allyear,s,sysuc] CST_TIME:
    cap_new: Parameter = None  # type: ignore[assignment] # [r,allyear,p,t,sysuc] CAP_NEW:
    scap_new: Parameter = None  # type: ignore[assignment] # [r,allyear,p,t,sysuc] CAP_NEW:
    dam_obj: Parameter = None  # type: ignore[assignment] # [r,t,c,cur] DAM_OBJ:
    sdam_obj: Parameter = None  # type: ignore[assignment] # [r,t,c,cur] DAM_OBJ:
    par_eout: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] PAR_EOUT:
    spar_eout: Parameter = None  # type: ignore[assignment] # [r,allyear,t,p,c] PAR_EOUT:
    niter: Set = None  # type: ignore[assignment] # NITER:
    TmPp: Set = None  # type: ignore[assignment] # TM_PP:
    miter: Set = None  # type: ignore[assignment] # MITER:
    Tb: Set = None  # type: ignore[assignment] # [t] TB:
    Pp: Set = None  # type: ignore[assignment] # [t] PP:
    Tlast: Set = None  # type: ignore[assignment] # [t] TLAST:
    Xcp: Set = None  # type: ignore[assignment] # [j] XCP: Market penetration step index used for VAR_XCAPP bounds
    tp: Alias = None  # type: ignore[assignment] # [t, tp] TP:
    T1: Alias = None  # type: ignore[assignment] # [*] T_1: Aliased with MIYR_1
    tb: Alias = None  # type: ignore[assignment] # [*] TB: Aliased with MIYR_1
    tm_arbm: Parameter = None  # type: ignore[assignment] # TM_ARBM:
    tm_sl: Parameter = None  # type: ignore[assignment] # TM_SL: Additions to support MACRO soft-link
    tm_scale_cst: Parameter = None  # type: ignore[assignment] # TM_SCALE_CST:
    tm_scale_nrg: Parameter = None  # type: ignore[assignment] # TM_SCALE_NRG:
    tm_scale_util: Parameter = None  # type: ignore[assignment] # TM_SCALE_UTIL:
    tm_desub: Parameter = None  # type: ignore[assignment] # [r] TM_DESUB: Elasticity of substitution between demands
    tm_step: Parameter = None  # type: ignore[assignment] # [r, cg, lim] TM_STEP: Steps in CES substitution
    tm_voc: Parameter = None  # type: ignore[assignment] # [r, year, cg, bd] TM_VOC: Variance in CES component or utility
    tm_defval: Parameter = None  # type: ignore[assignment] # [*] TM_DEFVAL:
    Mr: Set = None  # type: ignore[assignment] # [REG] MR:
    Mag: Set = None  # type: ignore[assignment] # [cg] MAG:
    Dm: Set = None  # type: ignore[assignment] # [COM] DM:
    Mrtc: Set = None  # type: ignore[assignment] # [REG,YEAR,COM] MRTC:
    trd: Set = None  # type: ignore[assignment] # [*] TRD:
    TmDam: Set = None  # type: ignore[assignment] # [R,ITEM] TM_DAM:
    TmDm: Set = None  # type: ignore[assignment] # [REG,COM] TM_DM:
    tm_gr: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_GR: 'Growth rate'
    tm_gdp0: Parameter = None  # type: ignore[assignment] # [REG] TM_GDP0: ''Initial GDP''
    tm_depr: Parameter = None  # type: ignore[assignment] # [R] TM_DEPR: 'Depreciation rate'
    tm_dmtol: Parameter = None  # type: ignore[assignment] # [R] TM_DMTOL: 'Demand lower bound factor'
    tm_ivetol: Parameter = None  # type: ignore[assignment] # [R] TM_IVETOL: 'Investment and enery tolerance'
    tm_kgdp: Parameter = None  # type: ignore[assignment] # [R] TM_KGDP: 'Initial capital to GDP ratio'
    tm_kpvs: Parameter = None  # type: ignore[assignment] # [R] TM_KPVS: 'Capital value share'
    tm_esub: Parameter = None  # type: ignore[assignment] # [R] TM_ESUB: 'Elasticity of substitution'
    tm_mdtl: Parameter = None  # type: ignore[assignment] # [R] TM_MDTL: 'Market damage linear coeff.'
    tm_mdtq: Parameter = None  # type: ignore[assignment] # [R] TM_MDTQ: 'Market damage quadratic coeff.'
    tm_hsx: Parameter = None  # type: ignore[assignment] # [R,YEAR] TM_HSX: 'Hockey-stick exponent'
    tm_ddatpref: Parameter = None  # type: ignore[assignment] # [REG,COM] TM_DDATPREF
    tm_ddf: Parameter = None  # type: ignore[assignment] # [REG,YEAR,COM] TM_DDF
    tm_dem: Parameter = None  # type: ignore[assignment] # [REG,YEAR,COM] TM_DEM
    tm_dmc: Parameter = None  # type: ignore[assignment] # [REG,YEAR,COM] TM_DMC
    nyper: Parameter = None  # type: ignore[assignment] # [T] NYPER(T) number of years until next milestone
    tm_ec0: Parameter = None  # type: ignore[assignment] # [REG] TM_EC0(REG) initial energy system cost
    tm_c0: Parameter = None  # type: ignore[assignment] # [REG] TM_C0(REG) initial consumption
    tm_y0: Parameter = None  # type: ignore[assignment] # [REG] TM_Y0(REG) initial gross output
    tm_iv0: Parameter = None  # type: ignore[assignment] # [REG] TM_IV0(REG) initial investment
    tm_k0: Parameter = None  # type: ignore[assignment] # [REG] TM_K0(REG) initial capital
    tm_rho: Parameter = None  # type: ignore[assignment] # [R] TM_RHO(R) exponent derived from esub
    tm_asrv: Parameter = None  # type: ignore[assignment] # [R] TM_ASRV(R) annual capital survival factor
    tm_tsrv: Parameter = None  # type: ignore[assignment] # [R,T] TM_TSRV(R,T) yearly capital survival factor
    tm_akl: Parameter = None  # type: ignore[assignment] # [REG] TM_AKL(REG) prod function constant for k-l index
    tm_expbnd: Parameter = None  # type: ignore[assignment] # [r, allyear,p] TM_EXPBND: Market Penetration Cutoff for Applying Cost Penalty
    tm_expf: Parameter = None  # type: ignore[assignment] # [r, allyear] TM_EXPF: Annual percent expansion factor

    # From src/core/initmty_etl.py
    Teg: Set = None  # type: ignore[assignment] # [PRC] TEG(PRC)
    tl_sc0: Parameter = None  # type: ignore[assignment] # [R,PRC] TL_SC0(R,PRC)
    tl_prat: Parameter = None  # type: ignore[assignment] # [R,PRC] TL_PRAT(R,PRC)
    tl_seg: Parameter = None  # type: ignore[assignment] # [R,PRC] TL_SEG(R,PRC)
    tl_ccap0: Parameter = None  # type: ignore[assignment] # [R,PRC] TL_CCAP0(R,PRC)
    tl_ccapm: Parameter = None  # type: ignore[assignment] # [R,PRC] TL_CCAPM(R,PRC)
    tl_cluster: Parameter = None  # type: ignore[assignment] # [R,P,P] TL_CLUSTER(R,P,P)
    tl_mrclust: Parameter = None  # type: ignore[assignment] # [R,P,R,P] TL_MRCLUST(R,P,R,P)
    sc0: Parameter = None  # type: ignore[assignment] # [R,PRC] SC0(R,PRC)
    prat: Parameter = None  # type: ignore[assignment] # [R,PRC] PRAT(R,PRC)
    seg: Parameter = None  # type: ignore[assignment] # [R,PRC] SEG(R,PRC)
    ccap0: Parameter = None  # type: ignore[assignment] # [R,PRC] CCAP0(R,PRC)
    ccapm: Parameter = None  # type: ignore[assignment] # [R,PRC] CCAPM(R,PRC)
    cluster: Parameter = None  # type: ignore[assignment] # [R,P,P] CLUSTER(R,P,P)
    pat: Parameter = None  # type: ignore[assignment] # [R,PRC] PAT(R,PRC)
    pbt: Parameter = None  # type: ignore[assignment] # [R,PRC] PBT(R,PRC)
    ccost0: Parameter = None  # type: ignore[assignment] # [R,PRC] CCOST0(R,PRC)
    ccostm: Parameter = None  # type: ignore[assignment] # [R,PRC] CCOSTM(R,PRC)
    weig: Parameter = None  # type: ignore[assignment] # [R,KP,PRC] WEIG(R,KP,PRC)
    ccostk: Parameter = None  # type: ignore[assignment] # [R,KP,PRC] CCOSTK(R,KP,PRC)
    ccapk: Parameter = None  # type: ignore[assignment] # [R,KP,PRC] CCAPK(R,KP,PRC)
    beta: Parameter = None  # type: ignore[assignment] # [R,KP,PRC] BETA(R,KP,PRC)
    alph: Parameter = None  # type: ignore[assignment] # [R,KP,PRC] ALPH(R,KP,PRC)
    ntchteg: Parameter = None  # type: ignore[assignment] # [R,PRC] NTCHTEG(R,PRC) Number of technologies in cluster
    invc_unit: Parameter = None  # type: ignore[assignment] # [R,T,P] INVC_UNIT(R,T,P)
    prev: Parameter = None  # type: ignore[assignment] # [R,PRC] PREV(R,PRC)
    tl_start: Set = None  # type: ignore[assignment] # [R,T,P] TL_START(R,T,P)
    tl_rp_ct: Set = None  # type: ignore[assignment] # [REG,PRC] TL_RP_CT(REG,PRC)
    tl_rp_kc: Set = None  # type: ignore[assignment] # [REG,PRC] TL_RP_KC(REG,PRC)
    tl_ct_cost: Parameter = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,CUR] TL_CT_COST(R,ALLYEAR,PRC,CUR)
    mliter: Set = None  # type: ignore[assignment] # MLITER
    mliterm: Parameter = None  # type: ignore[assignment] # MLITERM
    ccdifcrit: Parameter = None  # type: ignore[assignment] # CCDIFCRIT

    # From src/core/mod_vars_etl.py
    VAR_LAMBD: Variable = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swd] VAR_LAMBD
    VAR_CCAP: Variable = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swd] VAR_CCAP
    VAR_CCOST: Variable = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swd] VAR_CCOST
    VAR_DELTA: Variable = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swd] VAR_DELTA (BINARY)
    eq_cuinv: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_CUINV: Cumulative Capacity Definition
    eq_cc: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_CC: Cumulative Capacity Interpolation
    eq_del: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_DEL: Delta to 1
    eq_cos: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_COS: Cumulative Cost
    eq_la1: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swtd] EQ_LA1: Constraints on lambda 1
    eq_la2: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swtd] EQ_LA2: Constraints on lambda 2
    eq_expe1: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swtd] EQ_EXPE1: Experience grows 1
    eq_expe2: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,KP,swtd] EQ_EXPE2: Experience grows 2
    eq_ic1: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_IC1: Investments tech. change 1st period
    eq_ic2: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_IC2: Investments tech. change other periods
    eq_clu: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_CLU: Cluster
    eq_mrclu: Equation = None  # type: ignore[assignment] # [R,ALLYEAR,PRC,swtd] EQ_MRCLU: Multi-regional Cluster

    # From src/core/initmty_tm.py
    tm_qfac: Parameter = None  # type: ignore[assignment] # [R] TM_QFAC(R) Switch for market penetration penalty function
    tm_captb: Parameter = None  # type: ignore[assignment] # [R,P] TM_CAPTB(R,P) Cumulative quadratic capacity penalty level

    # --- Intermediate Parameters for MACRO--2 ---
    tm_aeeiv: Parameter = None  # type: ignore[assignment] # [R,YEAR,C] TM_AEEIV Annual AEEI and demand decoupling factor
    tm_aeeifac: Parameter = None  # type: ignore[assignment] # [R,LL,C] TM_AEEIFAC Periodwise AEEI and demand decoupling factor
    tm_adder: Parameter = None  # type: ignore[assignment] # [r, t, c] TM_ADDER: Demand decoupling adder
    tm_b: Parameter = None  # type: ignore[assignment] # [REG,COM] TM_B Prod function constant for demand of useful energy
    tm_d0: Parameter = None  # type: ignore[assignment] # [REG,COM] TM_D0 Base year useful demand - from TIMES
    tm_dfactcurr: Parameter = None  # type: ignore[assignment] # [R,LL] TM_DFACTCURR Current annual utility discount factor
    tm_dfact: Parameter = None  # type: ignore[assignment] # [R,ALLYEAR] TM_DFACT Utility discount factor
    tm_pwt: Parameter = None  # type: ignore[assignment] # [YEAR] TM_PWT Periodic utility weight
    tm_l: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_L Current labor force index (efficiency units)
    tm_annc: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_ANNC Estimate of annual energy system cost
    tm_amp: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_AMP Amortisation of past investments
    tm_gdpgoal: Parameter = None  # type: ignore[assignment] # [REG,TP] TM_GDPGOAL Projected Baseline GDP
    tm_growv: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_GROWV Potential Labor Growth Rates
    tm_qsfa: Parameter = None  # type: ignore[assignment] # [REG,TP] TM_QSFA Quadratic supply function A
    tm_qsfb: Parameter = None  # type: ignore[assignment] # [REG,TP,COM] TM_QSFB Quadratic supply function B
    tm_catt: Parameter = None  # type: ignore[assignment] # [R] TM_CATT Catastrophic temperature
    tm_udf: Parameter = None  # type: ignore[assignment] # [R,ALLYEAR] TM_UDF Utility discount factor
    tm_cap: Parameter = None  # type: ignore[assignment] # [r, p] Base year capacity values for expanding technologies
    tm_nwt: Parameter = None  # type: ignore[assignment] # [REG] TM_NWT Negishi weights
    tm_nwtit: Parameter = None  # type: ignore[assignment] # [NITER,REG] TM_NWTIT Negishi weights by iteration
    tm_cie: Parameter = None  # type: ignore[assignment] # [niter, reg] TM_CIE: Expnditure rate
    tm_pvpi: Parameter = None  # type: ignore[assignment] # [ITEM,TP] TM_PVPI Present value prices of tradeables
    par_y: Parameter = None  # type: ignore[assignment] # [R,T] PAR_Y Production parameter
    par_iv: Parameter = None  # type: ignore[assignment] # [R,YEAR] PAR_IV Investment parameter
    par_grgdp: Parameter = None  # type: ignore[assignment] # [R,T] PAR_GRGDP Growth rate of GDP
    par_mc: Parameter = None  # type: ignore[assignment] # [R,T,C] PAR_MC Marginal costs of demands
    tm_ddf_y: Parameter = None  # type: ignore[assignment] # [R,T] TM_DDF_Y
    tm_ddf_dm: Parameter = None  # type: ignore[assignment] # [R,T,C] TM_DDF_DM
    tm_ddf_sp: Parameter = None  # type: ignore[assignment] # [R,T,C] TM_DDF_SP
    tm_f2: Parameter = None  # type: ignore[assignment] # [R,T,C] TM_F2
    tm_cstinv: Parameter = None  # type: ignore[assignment] # [r, allyear, p] TM_CSTINV Annualized investment costs
    tm_ycheck: Parameter = None  # type: ignore[assignment] # [R] TM_YCHECK
    tm_dd: Parameter = None  # type: ignore[assignment] # [R,C,T] TM_DD Demand ratio MSA estimates to TED demand levels
    tm_gdp: Parameter = None  # type: ignore[assignment] # [REG,YEAR] TM_GDP Actualized gross domestic product

    # From src/core/solve_msa.py
    mce: Model = None  # type: ignore[assignment] # MCE: MACRO soft-link solve model
    loops: Set = None  # type: ignore[assignment] # [*] LOOPS: NWT, DDF, GDP
    gdploss: Parameter = None  # type: ignore[assignment] # [MITER,REG,tp] GDPLOSS: GDP losses in percent
    msa_err: Parameter = None  # type: ignore[assignment] # [MITER,NITER,LOOPS,REG] MSA_ERR
    tm_tol: Parameter = None  # type: ignore[assignment] # [ITEM] TM_TOL: MSA/CSA iteration tolerances
    errdem: Parameter = None  # type: ignore[assignment] # ERRDEM
    errgdp: Parameter = None  # type: ignore[assignment] # ERRGDP
    tm_cal: Parameter = None  # type: ignore[assignment] # TM_CAL

    # From src/core/presolve_mlf.py
    TmDmas: Set = None  # type: ignore[assignment] # [cg,cg] TM_DMAS
    TmCes: Set = None  # type: ignore[assignment] # [cg] TM_CES
    TmRcj: Set = None  # type: ignore[assignment] # [r,cg,j,bd] TM_RCJ
    Logj: Set = None  # type: ignore[assignment] # [j,bd] LOGJ
    tm_logjot: Parameter = None  # type: ignore[assignment] # TM_LOGJOT
    tm_lsc: Parameter = None  # type: ignore[assignment] # TM_LSC
    tm_basepri: Parameter = None  # type: ignore[assignment] # [r,t,cg] TM_BASEPRI
    tm_baselev: Parameter = None  # type: ignore[assignment] # [r,t,cg] TM_BASELEV
    tm_pref: Parameter = None  # type: ignore[assignment] # [r,t,cg] TM_PREF
    tm_qref: Parameter = None  # type: ignore[assignment] # [r,t,cg] TM_QREF
    tm_shar: Parameter = None  # type: ignore[assignment] # [r,t,cg,cg] TM_SHAR
    tm_agg: Parameter = None  # type: ignore[assignment] # [r,t,cg,cg] TM_AGG
    tm_ceslev: Parameter = None  # type: ignore[assignment] # [r,t,cg] TM_CESLEV
    tm_agc: Parameter = None  # type: ignore[assignment] # [r,t,cg,cg,j,bd] TM_AGC
    tm_midcon: Parameter = None  # type: ignore[assignment] # [r,t] TM_MIDCON
    tm_logval: Parameter = None  # type: ignore[assignment] # [j,bd] TM_LOGVAL

    var_sts: Parameter = None  # type: ignore[assignment] # [R,YEAR,T,P,S,L] VAR_STS
    cm_history: Parameter = None  # type: ignore[assignment] # [ALLYEAR,CM_ITEM] CM_HISTORY Calibration values for CO2 and forcing
    cm_stats: Parameter = None  # type: ignore[assignment] # [CM_ITEM,ALLYEAR,CM_Q] CM_STATS Calibration values for CO2 and forcing
    CmHists: Set = None  # type: ignore[assignment] # [CG] CM_HISTS Calibration sets for CO2 and forcing
    CmBox: Set = None  # type: ignore[assignment] # [CM_Q] CM_BOX Reservoir buckets
    CmBoxmap: Set = None  # type: ignore[assignment] # [CM_ITEM,CM_ITEM,CM_BOX] CM_BOXMAP Calibration boxes for CO2 and forcing
    cm_evar: Parameter = None  # type: ignore[assignment] # [CM_ITEM,LL] CM_EVAR
    cm_bemi: Parameter = None  # type: ignore[assignment] # [CM_ITEM,LL] CM_BEMI
    CmEmis: Set = None  # type: ignore[assignment] # [CM_ITEM] CM_EMIS
    cm_maxco2c: Parameter = None  # type: ignore[assignment] # [ALLYEAR] CM_MAXCO2C
    cm_linfor: Parameter = None  # type: ignore[assignment] # [ALLYEAR,CM_ITEM,LIM] CM_LINFOR
    cm_maxc: Parameter = None  # type: ignore[assignment] # [ALLYEAR,ITEM] CM_MAXC
    cm_exoforc: Parameter = None  # type: ignore[assignment] # [ALLYEAR] CM_EXOFORC
    s_cm_maxco2c: Parameter = None  # type: ignore[assignment] # [ALLYEAR,J,ALLSOW] S_CM_MAXCO2C
    s_cm_maxc: Parameter = None  # type: ignore[assignment] # [ALLYEAR,ITEM,J,ALLSOW] S_CM_MAXC
    cmpredef: Set = None  # type: ignore[assignment]
    cmitem: Alias = None  # type: ignore[assignment]
    cmq: Set = None  # type: ignore[assignment]
    CmOfor: Set = None  # type: ignore[assignment]
    cm_co2gtc: Parameter = None  # type: ignore[assignment]
    cm_ghgmap: Parameter = None  # type: ignore[assignment]
    cm_ppm: Parameter = None  # type: ignore[assignment]
    cm_decay: Parameter = None  # type: ignore[assignment]
    cm_couple: Parameter = None  # type: ignore[assignment]
    SwTstg: Set = None  # type: ignore[assignment] # [LL,J] SW_TSTG
    attlvl: Parameter = None  # type: ignore[assignment] # ATTLVL
    vallvl: Parameter = None  # type: ignore[assignment] # VALLVL
    cm_calib: Parameter = None  # type: ignore[assignment] # CM_CALIB
    cm_dt_forc: Parameter = None  # type: ignore[assignment] #
    cm_sresult: Parameter = None  # type: ignore[assignment] #
    cm_smaxc_m: Parameter = None  # type: ignore[assignment] #
    cmstcc: Set = None  # type: ignore[assignment] #
    CmConc: Set = None  # type: ignore[assignment] #
    CmAtmap: Set = None  # type: ignore[assignment] #
    CmBuck: Alias = None  # type: ignore[assignment] #
    CmUsubs: Set = None  # type: ignore[assignment]
    CmRebox: Set = None  # type: ignore[assignment]
    CmCoupmap: Set = None  # type: ignore[assignment]
    Pret: Set = None  # type: ignore[assignment] #
    CmForcmap: Set = None  # type: ignore[assignment] #
    cm_stat0: Parameter = None  # type: ignore[assignment] #
    cm_sig1: Parameter = None  # type: ignore[assignment] #
    cm_phi: Parameter = None  # type: ignore[assignment] #
    cm_sig: Parameter = None  # type: ignore[assignment] #
    cm_aa: Parameter = None  # type: ignore[assignment] #
    cm_bb: Parameter = None  # type: ignore[assignment] #
    cm_cc: Parameter = None  # type: ignore[assignment] #
    cm_rr: Parameter = None  # type: ignore[assignment] #
    cm_deltat: Parameter = None  # type: ignore[assignment] #
    cm_led: Parameter = None  # type: ignore[assignment] #
    tm_taxrev: Parameter = None  # type: ignore[assignment] # TM_TAXREV
    tm_hdf: Parameter = None  # type: ignore[assignment] # TM_HDF
    cm_const: Parameter = None  # type: ignore[assignment] #
    s_cm_const: Parameter = None  # type: ignore[assignment] #
    cm_default: Parameter = None  # type: ignore[assignment] #
    s_ucobj: Parameter = None  # type: ignore[assignment] #
    gg_m1: Parameter = None  # type: ignore[assignment]  # GG_M1
    gg_mm: Parameter = None  # type: ignore[assignment] # GG_MM
    gg_ppm: Parameter = None  # type: ignore[assignment] # GG_PPM
    gg_ppw: Parameter = None  # type: ignore[assignment] # GG_PPW
    cru: Alias = None  # type: ignore[assignment] #
    sw_tprob: Parameter = None  # type: ignore[assignment] # [T,ALLSOW] SW_TPROB
    sw_unpb: Parameter = None  # type: ignore[assignment] # [LL,WW] SW_UNPB
    rypm: Parameter = None  # type: ignore[assignment] #
    rycsm: Parameter = None  # type: ignore[assignment] #
    rypcsm: Parameter = None  # type: ignore[assignment] #
    rypcsrxm: Parameter = None  # type: ignore[assignment] #
    Vnret: Set = None  # type: ignore[assignment] # VNRET
    rp_rtf: Parameter = None  # type: ignore[assignment] # RP_RTF
    GgArc: Set = None  # type: ignore[assignment] # [allreg,c,allreg,c] GG_ARC Undirected grid edges
    GgTop: Set = None  # type: ignore[assignment] # [allr,c,allr,c,p] GG_TOP Undirected grid pipeline topology
    GgLink: Set = None  # type: ignore[assignment] # [allr,p,c,allr,c] GG_LINK Directed grid pipeline topology
    GgEdge: Set = None  # type: ignore[assignment] # [allr,p,allr] GG_EDGE Undirected grid pipeline topology
    GgWink: Set = None  # type: ignore[assignment] # [allr,p,c,allr,c] GG_WINK Alternate Weymouth topology
    GgRtc: Set = None  # type: ignore[assignment] # [r,year,c] GG_RTC Grid nodes by period
    GgRtpc: Set = None  # type: ignore[assignment] # [r,milestonyr,p,c] GG_RTPC Grid pipelines by period
    GgWtx: Set = None  # type: ignore[assignment] # [r,p,c] GG_WTX Pipelines with Taylor expansion
    Omg: Set = None  # type: ignore[assignment] # [j] OMG
    GgO: Set = None  # type: ignore[assignment] # [j] GG_O
    GgVi: Set = None  # type: ignore[assignment] # [j] GG_VI
    RpGrid: Set = None  # type: ignore[assignment] # [r,p] RP_GRID
    RcGrid: Set = None  # type: ignore[assignment] # [r,t,c] RC_GRID
    GrTop: Set = None  # type: ignore[assignment] # [allreg,c,allreg,c,p] GR_TOP
    GrArc: Set = None  # type: ignore[assignment] # [allreg,c,allreg,c] GR_ARC
    GrGrid: Set = None  # type: ignore[assignment] # [j,r,Com] GR_GRID
    GrAllmap: Set = None  # type: ignore[assignment] # [r,cg,Com] GR_ALLMAP
    GrPrcmap: Set = None  # type: ignore[assignment] # [r,p,c,item] GR_PRCMAP
    GrDemmap: Set = None  # type: ignore[assignment] # [r,c,Com] GR_DEMMAP
    GrAlgmap: Set = None  # type: ignore[assignment] # [r,cg,cg] GR_ALGMAP
    GrEndc: Set = None  # type: ignore[assignment] # [r,cg] GR_ENDC
    GrGenp: Set = None  # type: ignore[assignment] # [r,p] GR_GENP
    GrCandid: Set = None  # type: ignore[assignment] # [r,year,p] GR_CANDID
    GrGnall: Set = None  # type: ignore[assignment] # [r,t,c] GR_GNALL
    gr_sus: Parameter = None  # type: ignore[assignment] # [allreg,t,c,allreg,c] GR_SUS
    gr_flow: Parameter = None  # type: ignore[assignment] # [r,p,c] GR_FLOW
    gr_gid: Parameter = None  # type: ignore[assignment] # [r,c] GR_GID
    gr_admit: Parameter = None  # type: ignore[assignment] # [allreg,t,c,allreg,c] GR_ADMIT
    gr_units: Parameter = None  # type: ignore[assignment] # [r,t,item] GR_UNITS
    gr_capup: Parameter = None  # type: ignore[assignment] # [r,year,p] GR_CAPUP
    VAR_GG_PR: Variable = None  # type: ignore[assignment]  # [r, t, c, s] VAR_GG_PR: Nodal pressures
    VAR_GG_MF: Variable = None  # type: ignore[assignment]  # [r, t, p, c, r, c, s] VAR_GG_MF: Mass flows of gases
    VAR_GG_PDIF: Variable = None  # type: ignore[assignment]  # [r, t, p, c, r, c, s] VAR_GG_PDIF: Pressure differences over pipeline
    VAR_GG_PADD: Variable = None  # type: ignore[assignment]  # [r, t, p, c, s] VAR_GG_PADD: Pressure boost due to compressor at input node
    VAR_GG_STEP: Variable = None  # type: ignore[assignment]  # [r, t, p, c, s, j] VAR_GG_STEP: Alternate step variables
    VAR_GG_Y: Variable = None  # type: ignore[assignment]  # [r, t, p, c, s] VAR_GG_Y
    PrcUnits: Set = None  # type: ignore[assignment] # [r, p, ucgrptype, units] PRC_UNITS
    eqg_uc: Equation = None  # type: ignore[assignment] # EQG_UC
    eqg_ucr: Equation = None  # type: ignore[assignment] # EQG_UCR
    eqg_uct: Equation = None  # type: ignore[assignment] # EQG_UCT
    eqg_ucrt: Equation = None  # type: ignore[assignment] # EQG_UCRT
    eqg_ucts: Equation = None  # type: ignore[assignment] # EQG_UCTS
    eqg_ucrs: Equation = None  # type: ignore[assignment] # EQG_UCRS
    eqg_ucrts: Equation = None  # type: ignore[assignment] # EQG_UCRTS
    eqg_ucsu: Equation = None  # type: ignore[assignment] # EQG_UCSU
    eqg_ucsus: Equation = None  # type: ignore[assignment] # EQG_UCSUS
    eqg_ucrsus: Equation = None  # type: ignore[assignment] # EQG_UCRSUS
    eqg_ucrsu: Equation = None  # type: ignore[assignment] # EQG_UCRSU
    eql_uc: Equation = None  # type: ignore[assignment] # EQL_UC
    eql_ucr: Equation = None  # type: ignore[assignment] # EQL_UCR
    eql_uct: Equation = None  # type: ignore[assignment] # EQL_UCT
    eql_ucrt: Equation = None  # type: ignore[assignment] # EQL_UCRT
    eql_ucts: Equation = None  # type: ignore[assignment] # EQL_UCTS
    eql_ucrs: Equation = None  # type: ignore[assignment] # EQL_UCRS
    eql_ucrts: Equation = None  # type: ignore[assignment] # EQL_UCRTS
    eql_ucsu: Equation = None  # type: ignore[assignment] # EQL_UCSU
    eql_ucsus: Equation = None  # type: ignore[assignment] # EQL_UCSUS
    eql_ucrsus: Equation = None  # type: ignore[assignment] # EQL_UCRSUS
    eql_ucrsu: Equation = None  # type: ignore[assignment] # EQL_UCRSU
    eqrobj: Equation = None  # type: ignore[assignment] # EQROBJ
    eqsobj: Equation = None  # type: ignore[assignment] # EQSOBJ
    VAR_ONIND: Variable = None  # type: ignore[assignment]  # [r, ll, t, p, s, lA] VAR_ONIND: on-line status of unit in timeslice s
    VAR_IC: Variable = None  # type: ignore[assignment] # [r, year, Rpc] # VAR_IC
    VAR_GRIDIO: Variable = None  # type: ignore[assignment]  # [r, year, c, c, s, io, *swd] VAR_GRIDIO
    VAS_GRIDIO: Variable = None  # type: ignore[assignment]  # [r, year, c, c, s, io, *swd] VAS_GRIDIO
    Z_GRIDIO: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_GRIDIO ($macro Z_GRIDIO)
    VAR_XCAP: Variable = None  # type: ignore[assignment]  # [r, year, item, *swd] VAR_XCAP
    VAS_XCAP: Variable = None  # type: ignore[assignment]  # [r, year, item, *swd] VAS_XCAP
    Z_XCAP: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_XCAP ($macro Z_XCAP)
    VAR_COMAUX: Variable = None  # type: ignore[assignment]  # [r, t, c, s, *swd] VAR_COMAUX
    VAS_COMAUX: Variable = None  # type: ignore[assignment]  # [r, t, c, s, *swd] VAS_COMAUX
    Z_COMAUX: Variable = None  # type: ignore[assignment]  # SPINES-only alias of VAS_COMAUX ($macro Z_COMAUX)
    eq_msncap: Equation = None  # type: ignore[assignment]  # [r, year, c, swd] eq_msncap
    eq_msncapb: Equation = None  # type: ignore[assignment]  # [r, year, c, p, swd] eq_msncapb
    SwChild: Set = None  # type: ignore[assignment]
    SwTree: Set = None  # type: ignore[assignment]
    SwCopy: Set = None  # type: ignore[assignment]
    SwCpmap: Set = None  # type: ignore[assignment]
    SwMap: Set = None  # type: ignore[assignment]
    SwRev: Set = None  # type: ignore[assignment]
    sw_phase: Parameter = None  # type: ignore[assignment]
    sw_desc: Parameter = None  # type: ignore[assignment]
    sw_parm: Parameter = None  # type: ignore[assignment]
    sw_norm: Parameter = None  # type: ignore[assignment]
    doiter: Parameter = None  # type: ignore[assignment]
    Auxsow: Set = None  # type: ignore[assignment] # AUXSOW
    SwStage: Set = None  # type: ignore[assignment] # SW_TSW
    SwUct: Set = None  # type: ignore[assignment] # SW_STAGE
    sw_start: Parameter = None  # type: ignore[assignment] # SW_START
    sw_subs: Parameter = None  # type: ignore[assignment] # SW_SUBS
    sw_sprob: Parameter = None  # type: ignore[assignment] # SW_SPROB
    sw_prob: Parameter = None  # type: ignore[assignment] # SW_PROB
    sw_lambda: Parameter = None  # type: ignore[assignment] # SW_LAMBDA
    s_com_cum: Parameter = None  # type: ignore[assignment] # S_COM_CUM
    T0: Set = None  # type: ignore[assignment] # T0
    SwT2w: Set = None  # type: ignore[assignment] # SW_T2W
    Rtcsw: Set = None  # type: ignore[assignment] # RTCSW
    Rtpw: Set = None  # type: ignore[assignment] # RTPW
    RpFfsgg: Set = None  # type: ignore[assignment] # RP_FFSGG
    RpFfsggm: Set = None  # type: ignore[assignment] # RP_FFSGGM
    obj_sic: Parameter = None  # type: ignore[assignment] # OBJ_SIC
    suc_l: Parameter = None  # type: ignore[assignment] # SUC_L
    rtp_safs: Parameter = None  # type: ignore[assignment] # RTP_SAFS
    rtcs_sfr: Parameter = None  # type: ignore[assignment] # RTCS_SFR
    rcs_ssfr: Parameter = None  # type: ignore[assignment] # RCS_SSFR
    Rcgrid: Set = None  # type: ignore[assignment] # [r, t, c] RC_GRID:
    obj_combal: Parameter = None  # type: ignore[assignment] # [r, t, c, s, item, cur] OBJ_COMBAL:
    par_bptl: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_BPTL:
    par_bptm: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_BPTM:
    par_condl: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_CONDL:
    par_condm: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_CONDM:
    par_heatl: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_HEATL:
    par_heatm: Parameter = None  # type: ignore[assignment] # [r, t, p] PAR_HEATM:
    ele_condl: Parameter = None  # type: ignore[assignment] # [r, year, year, p, c, s] ELE_CONDL:
    ele_condm: Parameter = None  # type: ignore[assignment] # [r, year, year, p, c, s] ELE_CONDM:
    ele_bptl: Parameter = None  # type: ignore[assignment] # [r, year, year, p, c, ts] ELE_BPTL:
    ele_bptm: Parameter = None  # type: ignore[assignment] # [r, year, year, p, c, ts] ELE_BPTM:

    RtpEqstk: Set = None  # type: ignore[assignment] # [r, allyear, t, p, item] RTP_EQSTK:
    BsRvt: Set = None  # type: ignore[assignment] # [r, year, t] BS_RVT:
    Vtv: Set = None  # type: ignore[assignment] # [ll, ll, t] VTV:
    # endregion

    # region DUMPSOL extension (dumpsol.mod solution dump)
    varact: Parameter = None  # type: ignore[assignment] # [r,t,p] VARACT
    # endregion

    # region ABS extension (initmty.abs ancillary balancing services)
    VAR_DRCAP: Variable = None  # type: ignore[assignment]  # [R, ALLYEAR, LL, P, *SWD, J] VAR_DRCAP
    VAS_DRCAP: Variable = None  # type: ignore[assignment]  # [R, ALLYEAR, LL, P, *SWD, J] VAS_DRCAP
    eq_dscret: Equation = None  # type: ignore[assignment]  # [R, ALLYEAR, ALLYEAR, P, *SWTD] EQ_DSCRET
    es_dscret: Equation = None  # type: ignore[assignment]  # [R, ALLYEAR, ALLYEAR, P, *SWTD] ES_DSCRET
    # endregion

    # region MICRO extension (pp_micro.mod elastic/NLP demand coefficients)
    ddf_qref: Parameter = None  # type: ignore[assignment] # [r,t,c] DDF_QREF
    ddf_pref: Parameter = None  # type: ignore[assignment] # [r,t,c] DDF_PREF
    mi_agc: Parameter = None  # type: ignore[assignment] # [r,t,c,c,j,lA] MI_AGC: integral demand prices
    mi_dope: Parameter = None  # type: ignore[assignment] # [r,t,c] MI_DOPE: demand own price elasticity
    mi_esub: Parameter = None  # type: ignore[assignment] # [r,t,c] MI_ESUB: elasticity of substitution
    mi_rho: Parameter = None  # type: ignore[assignment] # [r,t,c] MI_RHO: measure of substitutability
    mi_elasp: Parameter = None  # type: ignore[assignment] # [r,t,c] MI_ELASP: consumer surplus elasticity
    mi_ccons: Parameter = None  # type: ignore[assignment] # [r,t,c] MI_CCONS: constant of the demand function
    # endregion

    def __post_init__(self) -> None:
        """
        Runs immediately AFTER the dataclass finishes creating itself.
        """
        self.logger = logging.getLogger("TimesModel")
        self.container = Container()
        # macro_config is a process-wide singleton (module import survives
        # across model builds in the same process, e.g. in a pytest run), so
        # without an explicit reset here a Context activated by a previous
        # build (e.g. CoefAfMxContext when S_NCAP_AFS was defined) would leak
        # into this build even when the GAMS module that would activate it
        # (recurrin.stc's MXPAR label) never runs for this instance.
        macro_config.reset()

    def register_module(self, module: GamsClass) -> None:
        """Register a module object."""
        if not isinstance(module, GamsClass):
            raise TypeError(
                f"Object {module} does not implement the required TIMES interface."
            )
        self._modules.append(module)

    # -----------------------
    # Code embedding helpers
    # -----------------------
    def add_gams_code(
        self,
        module: GamsClass,
        phase: GamsPhase,
        code: str,
    ) -> None:
        """
        Add raw GAMS code into the Container with a traceable header.
        """

        header = (
            f"\n* ============================================================\n"
            f"* {module.module_name} :: {phase}\n"
            f"* source: {module.gams_source}\n"
            f"* ============================================================\n"
        )

        self.container.addGamsCode(header + code)

    def dump_generated_gams(self, path: str = "generated_times.gms") -> None:
        """
        Write the currently generated GAMS code to a file for inspection.
        """
        gms = self.container.generateGamsString()
        with open(path, "w", encoding="utf-8") as f:
            f.write(gms)

    def save_test_state(self, env: CompileEnvironment, checkpoint: str) -> None:
        """
        Saves the state of all compile time variables for later testing.

        :param self: Description
        :param env: Description
        :param checkpoint: name of the checkpoint
        """
        state = env.get_test_state()
        self.compile_states[checkpoint] = state

    # -----------------------
    # Orchestration phases
    # -----------------------
    def initialization(self) -> None:
        """Modules are initialized / compiled within their __init__ method. Only used to write GDX state after compilation."""
        self.container.write(self.output_compile, eps_to_zero=False, compress=True)

    def enqueue(
        self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Adds a function call to the end of the execution queue."""
        self.execution_list.append((func, args, kwargs))

    def run(self) -> None:
        """Executes all queued functions in order."""
        self.logger.info("Phase: run")
        for func, args, kwargs in self.execution_list:
            func(*args, **kwargs)
        self.container.write(self.output_execute, eps_to_zero=False, compress=True)

    # -----------------------
    # Utils
    # -----------------------
    def declared(self, symbol: Set | Parameter | Variable | str) -> bool:
        if isinstance(symbol, str):
            return symbol in self.container.listSymbols()
        else:
            return symbol is not None

    def has_records(self, symbol: Set | Parameter | Variable | str) -> bool:
        if not self.declared(symbol):
            return False
        else:
            if isinstance(symbol, str):
                symbol = self.container[symbol]  # type: ignore
            assert not isinstance(symbol, str)
            return bool(symbol.number_records > 0)

    def defined(self, symbol: Set | Parameter | Variable | str) -> bool:
        if not self.declared(symbol):
            return False
        else:
            if isinstance(symbol, str):
                symbol = self.container[symbol]  # type: ignore
            assert not isinstance(symbol, str)
            return self.has_records(symbol) | self.assigned(symbol)

    def assigned(self, symbol: Set | Parameter | Variable) -> bool:
        return symbol in self.assigned_symbols

    def register_assignment(self, symbol: Set | Parameter | Variable) -> None:
        self.assigned_symbols.add(symbol)

    def set_equation(self, name: str, eq: Equation) -> None:
        setattr(self, name.lower(), eq)

    def get_equation(self, name: str) -> Equation:
        return getattr(self, name.lower())  # type: ignore [no-any-return]

    def get_parameter(self, name: str) -> Parameter:
        return getattr(self, name.lower())  # type: ignore [no-any-return]

    def get_variable(self, name: str) -> Variable:
        return getattr(self, name.upper())  # type: ignore [no-any-return]

    def set_parameter(self, name: str, parameter: Parameter) -> None:
        setattr(self, name.lower(), parameter)

    def set_variable(self, name: str, var: Variable) -> None:
        setattr(self, name.upper(), var)

    def set_set(self, name: str, set: Set, domain: bool) -> None:
        if domain:
            cased_name = "".join(word.capitalize() for word in name.split("_"))
        else:
            cased_name = name.lower()
        setattr(self, cased_name, set)

    def get_set(self, name: str) -> Any:
        return self.container[name]
