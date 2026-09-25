# setglobs_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=========================================================================
# * Setglobs initializes System Declarations and Global Controls
# * %1 - optional variable label to jump
# *=========================================================================
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from core.base_class import GamsClass
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

from gamspy import Alias, Number, Parameter, Set

logger = logging.getLogger(__name__)


class SetglobsGms(GamsClass):
    """Translation unit for setglobs.gms."""

    # Instance attributes
    module_name: str = "setglobs_gms"
    gams_source: str = "setglobs.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: Literal["1", ""],
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.x1 = arg1
        self.x2 = arg2
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        # TODO: Do we need any of this?
        # $ SETARGS X1 X2
        # * --- FIXT Dump ---
        if not self.env.is_set("fixboh") and self.tc.reg_fixt is not None:
            self.tc.reg_fixt.setRecords(None)
        # $ IF NOT SET FIXBOH $KILL REG_FIXT
        # * --- DATA Dump ---
        # $ IF NOT %DATAGDX%==YES $GOTO SYSD
        # $ IF NOT ERRORFREE $GOTO SYSD
        # $ GDXOUT _dd_.gdx
        # $ IF %G2X6%==YES
        # $ IF gamsversion 342 $UNLOAD XPT
        # $ UNLOAD
        # $ GDXOUT
        # $ IF ERRORFREE
        # $ IF %DATAGDXI%==YES $hiddencall gams %system.ifile% idir1=%gams.idir1%/ idir2=%gams.idir2%/ --INTEXT_ONLY=yes gdx=%RUN_NAME%_iedata.gdx LO=0 O=nul
        # $ IF NOT warnings $GOTO SYSD
        # $ IF NOT ERRORFREE $ABORT GAMS cannot filter domain violations
        # $ IF %G2X6%==YES $BATINCLUDE gdxfilter MAIN

        self.label_sysd()

    def label_sysd(self) -> None:
        """SYSTEM (Internal) Declarations"""
        g = self.tc
        m = g.container

        # *----------------------------------------------------------------------------------------------
        # * SET SECTION
        # *----------------------------------------------------------------------------------------------
        # * commodities
        g.Rc = Set(
            m, name="RC", domain=[g.r, g.c], description="Commodities in each region"
        )
        g.Rcj = Set(
            m,
            name="RCJ",
            domain=[g.r, g.c, g.j, g.bd],
            description="# of steps for elastic demands",
        )
        g.RcAgp = Set(
            m,
            name="RC_AGP",
            domain=[g.Reg, g.Com, g.lim],
            description="Commodity aggregation of production",
        )
        g.RtcNet = Set(
            m,
            name="RTC_NET",
            domain=[g.r, g.allyear, g.c],
            description="VAR_COMNETs within CUM constraint range",
        )
        g.RtcPrd = Set(
            m,
            name="RTC_PRD",
            domain=[g.r, g.allyear, g.c],
            description="VAR_COMPRDs within CUM constraint range",
        )
        g.RhsCombal = Set(
            m,
            name="RHS_COMBAL",
            domain=[g.r, g.allyear, g.c, g.s],
            description="VAR_COMNET needed on balance",
        )
        g.RhsComprd = Set(
            m,
            name="RHS_COMPRD",
            domain=[g.r, g.allyear, g.c, g.s],
            description="VAR_COMPRD needed on production",
        )
        g.RcsCombal = Set(
            m,
            name="RCS_COMBAL",
            domain=[g.r, g.allyear, g.c, g.s, g.lim],
            description="TS for balance given RHS requirements",
        )
        g.RcsComprd = Set(
            m,
            name="RCS_COMPRD",
            domain=[g.r, g.allyear, g.c, g.s, g.lim],
            description="TS for production given RHS requirements",
        )
        g.RcsComts = Set(
            m,
            name="RCS_COMTS",
            domain=[g.r, g.c, g.allts],
            description="All timeslices at/above the COM_TSL",
        )
        g.RdAgg = Set(
            m,
            name="RD_AGG",
            domain=[g.Reg, g.Com],
            description="Micro aggregated demands",
        )
        g.MiDmas = Set(
            m,
            name="MI_DMAS",
            domain=[g.Reg, g.Com, g.Com],
            description="Micro aggregation map",
        )
        g.Ne = Set(
            m, name="NE", domain=[g.allr, g.Com], description="Non-energy Demands"
        )
        # * currency
        g.Rdcur = Set(
            m,
            name="RDCUR",
            domain=[g.Reg, g.cur],
            description="Discounted currencies by region",
        )
        g.ObjIcur = Set(
            m,
            name="OBJ_ICUR",
            domain=[g.Reg, g.allyear, g.p, g.cur],
            description="Capacity-related cost indicator",
        )
        # * commodity types (basic)
        g.Dem = Set(
            m, name="DEM", description="Demand commodities", domain=[g.Reg, g.Com]
        )
        g.Env = Set(
            m,
            name="ENV",
            domain=[g.Reg, g.Com],
            description="Environmental indicator commodities",
        )
        g.Fin = Set(
            m,
            name="FIN",
            domain=[g.Reg, g.Com],
            description="Financial flow commodities",
        )
        g.Mat = Set(
            m, name="MAT", domain=[g.Reg, g.Com], description="Material commodities"
        )
        g.Nrg = Set(
            m,
            name="NRG",
            domain=[g.Reg, g.Com],
            description="Energy carrier commodities",
        )
        # * process
        g.Rp = Set(
            m, name="RP", domain=[g.r, g.p], description="Processes in each region"
        )
        g.RpFlo = Set(
            m,
            name="RP_FLO",
            domain=[g.r, g.p],
            description="Processes with VAR_FLOs (not IRE)",
        )
        g.RpStd = Set(
            m,
            name="RP_STD",
            domain=[g.r, g.p],
            description="Standard processes with VAR_FLOs",
        )
        g.RpStg = Set(
            m, name="RP_STG", domain=[g.r, g.p], description="Storage processes"
        )
        g.RpIre = Set(
            m,
            name="RP_IRE",
            domain=[g.allreg, g.p],
            description="Processes involved in inter-regional trade",
        )
        g.RpNrg = Set(
            m,
            name="RP_NRG",
            domain=[g.r, g.p],
            description="Processes with an energy carrier PCG",
        )
        g.RpInout = Set(
            m,
            name="RP_INOUT",
            domain=[g.r, g.p, g.io],
            description="Indicator if process input/output normalized (according to PG side)",
        )
        g.RpPg = Set(
            m,
            name="RP_PG",
            domain=[g.Reg, g.prc, g.cg],
            description="Primary commodity group (PG)",
        )
        g.RpPgtype = Set(
            m,
            name="RP_PGTYPE",
            domain=[g.r, g.p, g.cg],
            description="Group type of the primary group",
        )
        g.RpUpl = Set(
            m,
            name="RP_UPL",
            domain=[g.r, g.p, g.lA],
            description="Processes with dispatching equations",
        )
        g.RpUpr = Set(
            m,
            name="RP_UPR",
            domain=[g.r, g.p, g.lA],
            description="Processes with ramping costs",
        )
        g.RpUps = Set(
            m,
            name="RP_UPS",
            domain=[g.r, g.p, g.tslvl, g.lA],
            description="Timeslice levels for startup accounting",
        )
        g.RpUpt = Set(
            m,
            name="RP_UPT",
            domain=[g.r, g.p, g.upt, g.bd],
            description="Start-up types for unit commitment",
        )
        g.RpDpl = Set(
            m,
            name="RP_DPL",
            domain=[g.r, g.p, g.tslvl],
            description="Dispatching process timeslice levels",
        )
        g.RpAire = Set(
            m,
            name="RP_AIRE",
            domain=[g.r, g.p, g.ie],
            description="Exchange process activity directions",
        )
        g.Rpc = Set(
            m,
            name="RPC",
            domain=[g.r, g.p, g.c],
            description="Commodities in/out of a processes",
        )
        g.RpcCapflo = Set(
            m,
            name="RPC_CAPFLO",
            domain=[g.r, g.allyear, g.p, g.c],
            description="Commodities involved in capacity",
        )
        g.RpcConly = Set(
            m,
            name="RPC_CONLY",
            domain=[g.r, g.allyear, g.p, g.c],
            description="Commodities ONLY involved in capacity",
        )
        g.RpcNoflo = Set(
            m,
            name="RPC_NOFLO",
            domain=[g.r, g.p, g.c],
            description="Commodities ONLY involved in capacity",
        )
        g.RpcIre = Set(
            m,
            name="RPC_IRE",
            domain=[g.allreg, g.p, g.c, g.ie],
            description="Process/commodities involved in inter-regional trade",
        )
        g.RpcEqire = Set(
            m,
            name="RPC_EQIRE",
            domain=[g.r, g.p, g.c, g.ie],
            description="Indicator for EQIRE equation generation",
        )
        g.RpcMarket = Set(
            m,
            name="RPC_MARKET",
            domain=[g.r, g.p, g.c, g.ie],
            description="Market exchange process indicator",
        )
        g.RpcPg = Set(
            m,
            name="RPC_PG",
            domain=[g.r, g.p, g.c],
            description="Commodities in the primary group",
        )
        g.RpcSpg = Set(
            m,
            name="RPC_SPG",
            domain=[g.r, g.p, g.c],
            description="Commodities in the shadow primary group",
        )
        g.RpcsVar = Set(
            m,
            name="RPCS_VAR",
            domain=[g.r, g.p, g.c, g.allts],
            description="Timeslices at which VAR_FLOs are to be created",
        )
        g.RpsS1 = Set(
            m,
            name="RPS_S1",
            domain=[g.r, g.p, g.allts],
            description="All timeslices at the PRC_TSL/COM_TSLspg",
        )
        g.RpsS2 = Set(
            m,
            name="RPS_S2",
            domain=[g.r, g.p, g.allts],
            description="All timeslices at/above PRC_TSL/COM_TSLspg",
        )
        g.RpsPrcts = Set(
            m,
            name="RPS_PRCTS",
            domain=[g.r, g.p, g.allts],
            description="All timeslices at/above the PRC_TSL",
        )
        g.Rtc = Set(
            m, name="RTC", domain=[g.r, g.allyear, g.c], description="Commodity/time"
        )
        g.RtcShed = Set(
            m,
            name="RTC_SHED",
            domain=[g.r, g.year, g.c, g.bd, g.j],
            description="Elastic shape indexes",
        )
        g.RtcsVarc = Set(
            m,
            name="RTCS_VARC",
            domain=[g.r, g.allyear, g.c, g.allts],
            description="The VAR_COMNET/PRDs control set",
        )
        g.Rtp = Set(
            m, name="RTP", domain=[g.r, g.allyear, g.p], description="Process/time"
        )
        g.Rtpc = Set(
            m,
            name="RTPC",
            domain=[g.r, g.allyear, g.p, g.c],
            description="Commodities of process in period",
        )
        g.RtpCptyr = Set(
            m,
            name="RTP_CPTYR",
            domain=[g.r, g.allyear, g.allyear, g.p],
            description="Capcity transfer v/t years",
        )
        g.RtpOff = Set(
            m,
            name="RTP_OFF",
            domain=[g.r, g.allyear, g.p],
            description="Periods for which VAR_NCAP.UP = 0",
        )
        g.RtpcsVarf = Set(
            m,
            name="RTPCS_VARF",
            domain=[g.allreg, g.allyear, g.p, g.c, g.allts],
            description="The VAR_FLOs control set",
        )
        g.RtpVara = Set(
            m,
            name="RTP_VARA",
            domain=[g.r, g.allyear, g.p],
            description="The VAR_ACT control set",
        )
        g.RtpVarp = Set(
            m,
            name="RTP_VARP",
            domain=[g.r, g.t, g.p],
            description="RTPs that have a VAR_CAP",
        )
        g.RtpVintyr = Set(
            m,
            name="RTP_VINTYR",
            domain=[g.Reg, g.allyear, g.allyear, g.prc],
            description="v/t years according to vintaging",
        )
        g.RtpVntbyr = Set(
            m,
            name="RTP_VNTBYR",
            domain=[g.Reg, g.allyear, g.prc, g.allyear],
            description="RTP_VINTYR with years swapped",
        )
        g.RtpTt = Set(
            m,
            name="RTP_TT",
            domain=[g.r, g.year, g.t, g.prc],
            description="Retrofit control periods",
        )
        g.Rvp = Set(
            m,
            name="RVP",
            domain=[g.r, g.allyear, g.p],
            description="ALIAS(RTP) for Process/time",
        )
        g.RtpCapyr = Set(
            m,
            name="RTP_CAPYR",
            domain=[g.r, g.year, g.year, g.p],
            description="Capacity vintage years",
        )
        g.RtpIshpr = Set(
            m,
            name="RTP_ISHPR",
            domain=[g.Reg, g.allyear, g.prc],
            description="Attribute existence indicator",
        )
        g.RtpCgc = Set(
            m,
            name="RTP_CGC",
            domain=[g.r, g.year, g.p, g.cg, g.cg],
            description="Multi-purpose work set",
        )
        g.RtpsBd = Set(
            m,
            name="RTPS_BD",
            domain=[g.r, g.allyear, g.p, g.s, g.bd],
            description="Multi-purpose work set",
        )
        g.CgGrp = Set(
            m,
            name="CG_GRP",
            domain=[g.Reg, g.prc, g.cg, g.cg],
            description="Multi-purpose work set",
        )
        g.Fsck = Set(
            m,
            name="FSCK",
            domain=[g.Reg, g.prc, g.cg, g.c, g.cg],
            description="Multi-purpose work set",
        )
        g.Fscks = Set(
            m,
            name="FSCKS",
            domain=[g.Reg, g.prc, g.cg, g.c, g.cg, g.ts],
            description="Multi-purpose work set",
        )
        g.RpcIreio = Set(
            m,
            name="RPC_IREIO",
            domain=[g.r, g.p, g.c, g.ie, g.io],
            description="Types of trade flows",
        )
        g.RpcLs = Set(
            m,
            name="RPC_LS",
            domain=[g.r, g.p, g.c],
            description="Load sifting control",
        )
        # * process types
        g.Ele = Set(
            m,
            name="ELE",
            domain=[g.r, g.p],
            description="Electric Power Plants",
        )
        g.Chp = Set(
            m, name="CHP", description="Coupled Heat+Power Plants", domain=[g.r, g.p]
        )
        g.Hpl = Set(
            m, name="HPL", description="Heat and Steam Plants", domain=[g.r, g.p]
        )
        # * region
        g.Mreg = Set(
            m, name="MREG", description="Set of active regions", domain=[g.allr]
        )
        g.Rreg = Set(
            m,
            name="RREG",
            description="Set of paired regions",
            domain=[g.allreg, g.allreg],
        )
        # * cumulatives & UCs
        g.Rhs = Set(m, records=["RHS"], name="RHS", domain=[g.side])

        tslvl_records = g.tslvl.toList()
        if g.ucnumber is None:
            g.ucnumber = Set(
                m,
                name="UC_NUMBER",
                description="Determines way of handling REG,T and TS",
                records=tslvl_records,
            )
        else:
            expand_set(g.ucnumber, tslvl_records)

        g.UcOn = Set(
            m,
            name="UC_ON",
            description="Active UCs by region",
            domain=[g.allr, g.ucn],
        )
        g.UcGmapC = Set(
            m,
            name="UC_GMAP_C",
            description="Assigning commodities to UC_GRP",
            domain=[g.Reg, g.ucn, g.comvar, g.Com, g.ucgrptype],
        )
        g.UcGmapP = Set(
            m,
            name="UC_GMAP_P",
            description="Assigning processes to UC_GRP",
            domain=[g.Reg, g.ucn, g.ucgrptype, g.prc],
        )
        g.UcGmapU = Set(
            m,
            name="UC_GMAP_U",
            description="Assigning constraints to UC_GRP",
            domain=[g.allr, g.ucn, g.ucn],
        )
        g.UcJmap = Set(
            m,
            name="UC_JMAP",
            description="Collecting all processes for GMAP",
            domain=[g.j, g.ucn, g.side, g.Reg, g.t, g.prc, g.ucgrptype],
        )
        g.UcDynbnd = Set(
            m,
            name="UC_DYNBND",
            description="Dynamic process-wise UC bounds",
            domain=[g.ucn, g.lim],
        )
        g.UcDyndir = Set(
            m,
            name="UC_DYNDIR",
            description="Direction of dynamic constraint",
            domain=[g.allr, g.ucn, g.side],
        )
        g.UcDs = Set(
            m,
            name="UC_DS",
            description="Levels of TS-dynamic constraints",
            domain=[g.allr, g.ucn, g.tslvl],
        )
        g.UcQaflo = Set(
            m,
            name="UC_QAFLO",
            description="QA_checks for UC FLO/IRE tuples",
            domain=[g.j, g.ucn, g.side, g.r, g.p, g.c],
        )
        g.UcRtsuc = Set(
            m,
            name="UC_RTSUC",
            description="RT-map for T_SUCC",
            domain=[g.allr, g.allyear, g.ucn],
        )
        g.GUds = Set(
            m,
            name="G_UDS",
            description="Timeslice-dynamic candidates",
            domain=[g.s, g.side, g.s],
        )
        g.RcCumcom = Set(
            m,
            name="RC_CUMCOM",
            description="Cumulative commodity PRD/NET",
            domain=[g.Reg, g.comvar, g.allyear, g.allyear, g.Com],
        )
        g.RpcCumflo = Set(
            m,
            name="RPC_CUMFLO",
            description="Cumulative process flows",
            domain=[g.Reg, g.prc, g.Com, g.allyear, g.allyear],
        )
        # * time
        g.RsBelow = Set(
            m,
            name="RS_BELOW",
            description="Timeslices stictly below a node",
            domain=[g.allreg, g.ts, g.ts],
        )
        g.RsBelow1 = Set(
            m,
            name="RS_BELOW1",
            description="Timeslices strictly one level below",
            domain=[g.allreg, g.ts, g.ts],
        )
        g.RsTree = Set(
            m,
            name="RS_TREE",
            description="Timeslice subtree",
            domain=[g.allreg, g.ts, g.ts],
        )
        g.RsPrev = Set(
            m,
            name="RS_PREV",
            description="Previous timeslice in parent cycle",
            domain=[g.r, g.s, g.s],
        )
        g.Finest = Set(
            m,
            name="FINEST",
            description="Set of the finest timeslices in use",
            domain=[g.r, g.allts],
        )
        g.Pastmile = Set(
            m,
            name="PASTMILE",
            description="PAST years that are not MILESYONYR",
            domain=[g.allyear],
        )
        g.Eachyear = Set(
            m,
            name="EACHYEAR",
            description="Each year from 1st PASTYEAR to last MILESTONYR + DUR_MAX",
            domain=[g.allyear],
        )
        g.Eohyears = Set(
            m,
            name="EOHYEARS",
            description="Each year from 1st PASTYEAR to last MILESTONYR",
            domain=[g.allyear],
        )
        g.pyr = Alias(m, name="PYR", alias_with=g.Pastyear)
        g.v = Alias(m, name="V", alias_with=g.Modlyear)
        # * identifiers for beginning/end of model horizon
        g.Miyr1 = Set(m, name="MIYR_1", description="First T", domain=[g.allyear])
        g.MiyrL = Set(m, name="MIYR_L", description="Last year", domain=[g.allyear])
        # * miscellaneous
        g.ips = Set(m, records=["IN", "N"], name="IPS", description="")
        g.Lnx = Set(m, records=["N", "FX"], name="LNX", description="", domain=[g.lA])
        g.Bdupx = Set(
            m, records=["UP", "FX"], name="BDUPX", description="", domain=[g.bd]
        )
        g.Bdlox = Set(
            m, records=["LO", "FX"], name="BDLOX", description="", domain=[g.bd]
        )
        g.Bdneq = Set(
            m, records=["LO", "UP"], name="BDNEQ", description="", domain=[g.bd]
        )
        g.RpPrc = Set(m, name="RP_PRC", domain=[g.r, g.p])
        g.RpgRed = Set(m, name="RPG_RED", description="", domain=[g.r, g.p, g.cg, g.io])
        g.RpGrp = Set(m, name="RP_GRP", domain=[g.Reg, g.prc, g.cg])
        g.RpCcg = Set(m, name="RP_CCG", domain=[g.Reg, g.prc, g.c, g.cg])
        g.RpCgg = Set(m, name="RP_CGG", domain=[g.Reg, g.prc, g.c, g.cg, g.cg])
        g.Trackc = Set(m, name="TRACKC", domain=[g.r, g.c])
        g.Trackp = Set(m, name="TRACKP", domain=[g.r, g.p])
        g.Trackpc = Set(m, name="TRACKPC", domain=[g.r, g.p, g.c])
        g.Trackpg = Set(m, name="TRACKPG", domain=[g.r, g.p, g.cg])
        g.Rvt = Set(m, name="RVT", domain=[g.r, g.allyear, g.t])
        g.Rtpx = Set(m, name="RTPX", domain=[g.r, g.t, g.p])
        g.RtPp = Set(m, name="RT_PP", description="", domain=[g.r, g.t])
        g.no_rt = Parameter(m, name="NO_RT", description="", domain=[g.allr, g.t])
        # * ---------------------------------------------------------------------------------------------
        # * PARAMETERS SECTION
        # * ---------------------------------------------------------------------------------------------
        # * Years and splits of timeslices based upon level
        g.lead = Parameter(m, name="LEAD", description="", domain=[g.allyear])
        g.lagt = Parameter(m, name="LAGT", description="", domain=[g.allyear])
        g.fpd = Parameter(m, name="FPD", description="", domain=[g.allyear])
        g.ipd = Parameter(m, name="IPD", description="", domain=[g.allyear])
        g.rs_fr = Parameter(m, name="RS_FR", description="", domain=[g.r, g.s, g.s])
        g.js_ccl = Parameter(m, name="JS_CCL", description="", domain=[g.r, g.j, g.s])
        # * integrated parameters (created in PREPPM.mod)
        g.uc_com = Parameter(
            m,
            name="UC_COM",
            description="Multiplier of VAR_COM variables",
            domain=[
                g.ucn,
                g.comvar,
                g.side,
                g.Reg,
                g.allyear,
                g.Com,
                g.s,
                g.ucgrptype,
            ],
        )
        g.com_cum = Parameter(
            m,
            name="COM_CUM",
            description="Cumulative bound on commodity",
            domain=[g.Reg, g.comvar, g.allyear, g.allyear, g.Com, g.lim],
        )
        # * derived coefficient components (created in COEF*.MOD)
        g.coef_af = Parameter(
            m,
            name="COEF_AF",
            description="Capacity/Activity relationship",
            domain=[g.r, g.allyear, g.t, g.prc, g.s, g.bd],
        )
        g.coef_cpt = Parameter(
            m,
            name="COEF_CPT",
            description="Fraction of capacity available",
            domain=[g.r, g.allyear, g.t, g.prc],
        )
        g.coef_icom = Parameter(
            m,
            name="COEF_ICOM",
            description="Commodity flow at investment time",
            domain=[g.r, g.allyear, g.t, g.prc, g.c],
        )
        g.coef_ocom = Parameter(
            m,
            name="COEF_OCOM",
            description="Commodity flow at decommissioning time",
            domain=[g.r, g.allyear, g.t, g.prc, g.c],
        )
        g.coef_cio = Parameter(
            m,
            name="COEF_CIO",
            description="Capacity-related commodity in/out flows",
            domain=[g.r, g.allyear, g.t, g.p, g.c, g.io],
        )
        g.coef_ptran = Parameter(
            m,
            name="COEF_PTRAN",
            description="Multiplier for EQ_PTRANS",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.c, g.cg, g.ts],
        )
        g.coef_rpti = Parameter(
            m,
            name="COEF_RPTI",
            description="Repeated investment cycles",
            domain=[g.r, g.allyear, g.p],
        )
        g.coef_iled = Parameter(
            m,
            name="COEF_ILED",
            description="Investment lead time",
            domain=[g.r, g.allyear, g.p],
        )
        g.coef_pvt = Parameter(
            m,
            name="COEF_PVT",
            description="Present value of time in periods",
            domain=[g.r, g.t],
        )
        g.coef_vnt = Parameter(
            m,
            name="COEF_VNT",
            description="COEF_CPT with swapped indexes",
            domain=[g.r, g.t, g.prc, g.allyear],
        )
        g.coef_cap = Parameter(
            m,
            name="COEF_CAP",
            description="Generic re-usable work parameter",
            domain=[g.r, g.allyear, g.ll, g.p],
        )
        g.coef_rtp = Parameter(
            m,
            name="COEF_RTP",
            description="Generic re-usable work parameter",
            domain=[g.r, g.allyear, g.p],
        )
        g.coef_rvpt = Parameter(
            m,
            name="COEF_RVPT",
            description="Generic re-usable work parameter",
            domain=[g.r, g.allyear, g.prc, g.t],
        )
        g.rtp_cpx = Parameter(
            m,
            name="RTP_CPX",
            description="Shape multipliers for capacity transfer",
            domain=[g.r, g.allyear, g.p, g.ll],
        )
        g.ncap_afbx = Parameter(
            m,
            name="NCAP_AFBX",
            description="Shape multipliers for NCAP_AF factors",
            domain=[g.r, g.allyear, g.p, g.bd],
        )
        g.ncap_afsm = Parameter(
            m, name="NCAP_AFSM", description="", domain=[g.r, g.allyear, g.p]
        )
        g.rvprl = Parameter(m, name="RVPRL", description="", domain=[g.r, g.year, g.p])
        # * OBJ function yearly values established in COEF_OBJ and used in OBJ_*
        g.obj_rfr = Parameter(
            m,
            name="OBJ_RFR",
            description="Risk-free rates",
            domain=[g.r, g.year, g.cur],
        )
        g.obj_pvt = Parameter(
            m,
            name="OBJ_PVT",
            description="Present value of period",
            domain=[g.r, g.year, g.cur],
        )
        g.obj_crf = Parameter(
            m,
            name="OBJ_CRF",
            description="Capital recovery factor",
            domain=[g.r, g.allyear, g.p, g.cur],
        )
        g.obj_crfd = Parameter(
            m,
            name="OBJ_CRFD",
            description="Capital recovery factor for Decommissioning",
            domain=[g.r, g.allyear, g.p, g.cur],
        )
        g.obj_disc = Parameter(
            m,
            name="OBJ_DISC",
            description="Discounting factor",
            domain=[g.r, g.allyear, g.cur],
        )

        if self.env.obmac != "YES":
            g.obj_icost = Parameter(
                m,
                name="OBJ_ICOST",
                description="NCAP_COST for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_isub = Parameter(
                m,
                name="OBJ_ISUB",
                description="NCAP_ISUB for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_itax = Parameter(
                m,
                name="OBJ_ITAX",
                description="NCAP_ITAX for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_fom = Parameter(
                m,
                name="OBJ_FOM",
                description="NCAP_FOM for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_fsb = Parameter(
                m,
                name="OBJ_FSB",
                description="NCAP_FSUB for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_ftx = Parameter(
                m,
                name="OBJ_FTX",
                description="NCAP_FTX for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_dcost = Parameter(
                m,
                name="OBJ_DCOST",
                description="NCAP_DCOST for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_dlagc = Parameter(
                m,
                name="OBJ_DLAGC",
                description="NCAP_DLAGC for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_acost = Parameter(
                m,
                name="OBJ_ACOST",
                description="ACT_COST for each year",
                domain=[g.r, g.allyear, g.p, g.cur],
            )
            g.obj_fcost = Parameter(
                m,
                name="OBJ_FCOST",
                description="FLO_COST for each year",
                domain=[g.r, g.allyear, g.p, g.c, g.s, g.cur],
            )
            g.obj_fdelv = Parameter(
                m,
                name="OBJ_FDELV",
                description="FLO_DELIV for each year",
                domain=[g.r, g.allyear, g.p, g.c, g.s, g.cur],
            )
            g.obj_ftax = Parameter(
                m,
                name="OBJ_FTAX",
                description="FLO_TAX for each year",
                domain=[g.r, g.allyear, g.p, g.c, g.s, g.cur],
            )
        g.obj_fsub = Parameter(
            m,
            name="OBJ_FSUB",
            description="FLO_SUB for each year",
            domain=[g.r, g.allyear, g.p, g.c, g.s, g.cur],
        )
        g.obj_comnt = Parameter(
            m,
            name="OBJ_COMNT",
            description="CSTNET for each year",
            domain=[g.r, g.allyear, g.c, g.s, g.costype, g.cur],
        )
        g.obj_compd = Parameter(
            m,
            name="OBJ_COMPD",
            description="CSTPRD for each year",
            domain=[g.r, g.allyear, g.c, g.s, g.costype, g.cur],
        )
        g.obj_ipric = Parameter(
            m,
            name="OBJ_IPRIC",
            description="IRE_PRICE for each year",
            domain=[g.r, g.allyear, g.p, g.c, g.s, g.ie, g.cur],
        )
        # * Miscellanea
        g.prc_ymin = Parameter(
            m,
            name="PRC_YMIN",
            description="Generic process parameter",
            domain=[g.Reg, g.prc],
        )
        g.prc_ymax = Parameter(
            m,
            name="PRC_YMAX",
            description="Generic process parameter",
            domain=[g.Reg, g.prc],
        )
        g.prc_sc = Parameter(
            m,
            name="PRC_SC",
            description="Process storage cycles",
            domain=[g.Reg, g.prc],
        )
        g.prc_sgl = Parameter(
            m,
            name="PRC_SGL",
            description="Process shadow level (< DAYNITE)",
            domain=[g.Reg, g.prc],
        )
        g.prc_semi = Parameter(
            m,
            name="PRC_SEMI",
            description="Semi-continuous indicator",
            domain=[g.r, g.p],
        )
        g.rd_nlp = Parameter(
            m, name="RD_NLP", description="NLP demand indicator", domain=[g.r, g.c]
        )
        g.rd_shar = Parameter(
            m,
            name="RD_SHAR",
            description="Demand aggregation share",
            domain=[g.r, g.t, g.c, g.c],
        )
        g.rp_afb = Parameter(
            m,
            name="RP_AFB",
            description="Processes with NCAP_AF by bound type",
            domain=[g.Reg, g.prc, g.bd],
        )
        g.rs_stg = Parameter(
            m,
            name="RS_STG",
            description="Lead from previous storage timeslice",
            domain=[g.r, g.allts],
        )
        g.rs_stgprd = Parameter(
            m,
            name="RS_STGPRD",
            description="Number of storage periods for each timeslice",
            domain=[g.r, g.allts],
        )
        g.rs_stgav = Parameter(
            m,
            name="RS_STGAV",
            description="Average residence time for storage activity",
            domain=[g.r, g.allts],
        )
        g.rs_tslvl = Parameter(
            m, name="RS_TSLVL", description="Timeslice levels", domain=[g.r, g.allts]
        )
        g.ts_array = Parameter(
            m,
            name="TS_ARRAY",
            description="Array for leveling parameter values across timeslices",
            domain=[g.allts],
        )
        g.stoa = Parameter(
            m,
            name="STOA",
            description="ORD Lag from each timeslice to ANNUAL",
            domain=[g.allts],
        )
        g.stoal = Parameter(
            m,
            name="STOAL",
            description="ORD Lag from the LVL of each timeslice to ANNUAL",
            domain=[g.allreg, g.ts],
        )
        g.bdsig = Parameter(
            m,
            records=[("LO", 1), ("UP", -1)],
            name="BDSIG",
            description="Bound signum",
            domain=[g.lim],
        )
        # *-----------------------------------------------------------------------------
        # * Initialization interpolation/extrapolation
        # *-----------------------------------------------------------------------------
        g.Fil = Set(m, name="FIL", domain=[g.allyear])
        g.MyFil = Set(m, name="MY_FIL", description="", domain=[g.allyear])
        g.Vnt = Set(m, name="VNT", domain=[g.allyear, g.allyear])
        g.Yk1 = Set(m, name="YK1", domain=[g.allyear, g.allyear])
        g.fil2 = Parameter(m, name="FIL2", domain=[g.allyear])
        g.my_fil2 = Parameter(m, name="MY_FIL2", description="", domain=[g.allyear])
        g.my_array = Parameter(m, name="MY_ARRAY", domain=[g.allyear])
        g.ykval = Parameter(m, name="YKVAL", domain=[g.allyear, g.allyear])
        # * flags used in extrapolation
        g.Backward = Set(m, name="BACKWARD", description="", domain=[g.year])
        g.Forward = Set(m, name="FORWARD", description="", domain=[g.year])
        # * DM_YEAR is the union of the sets MODLYEAR and DATAYEAR
        g.DmYear = Set(m, name="DM_YEAR", description="", domain=[g.allyear])
        # *------------------------------------------------------------------------------
        # * Additional system declarations
        # *------------------------------------------------------------------------------
        # * Internal Sets:
        g.PyrS = Set(
            m, name="PYR_S", description="Residual vintage", domain=[g.allyear]
        )
        g.MyTs = Set(
            m,
            name="MY_TS",
            description="Temporary set for timeslices",
            domain=[g.allts],
        )
        g.RUc = Set(
            m,
            name="R_UC",
            description="Temporary set for UCs by region",
            domain=[g.allr, g.ucn],
        )
        g.RUct = Set(
            m,
            name="R_UCT",
            description="Set for UCs by Reg & period",
            domain=[g.allreg, g.ucn, g.allyear],
        )
        g.UcT = Set(
            m,
            name="UC_T",
            description="Temporary set for UCs by period",
            domain=[g.ucn, g.t],
        )
        g.Rxx = Set(
            m,
            name="RXX",
            description="General triples related to a region",
            domain=[g.allr, "*", "*"],
        )
        g.uncd1 = Set(
            m, name="UNCD1", description="Non-domain-controlled set", domain=["*"]
        )
        g.Uncd7 = Set(
            m,
            name="UNCD7",
            description="Non-domain-controlled set of 7-tuples",
            domain=["*", "*", "*", "*", "*", "*", "*"],
        )
        g.life = Alias(m, name="LIFE", alias_with=g.age)
        g.Opyear = Set(m, name="OPYEAR", description="", domain=[g.age, g.life])
        # *------------------------------------------------------------------------------
        # * Sets and parameters used in reduction algorithm
        # *------------------------------------------------------------------------------
        g.NoAct = Set(
            m,
            name="NO_ACT",
            description="Process not requiring activity variable",
            domain=[g.r, g.p],
        )
        g.RpPgact = Set(
            m,
            name="RP_PGACT",
            description="Process with PCG consisting of 1 commodity",
            domain=[g.r, g.p],
        )
        g.RpPgflo = Set(
            m,
            name="RP_PGFLO",
            description="Process with PCG having COM_FR",
            domain=[g.r, g.p],
        )
        g.RpXred = Set(
            m,
            name="RP_XRED",
            description="Process with extended reducable pcg flows",
            domain=[g.Reg, g.prc],
        )
        g.RpcAct = Set(
            m,
            name="RPC_ACT",
            description="PG commodity of Process with PCG consisting of 1",
            domain=[g.Reg, g.prc, g.cg],
        )
        g.RpcAflo = Set(
            m,
            name="RPC_AFLO",
            description="ACT_FLO residual groups to be handled specially",
            domain=[g.Reg, g.prc, g.cg],
        )
        g.RpcAire = Set(
            m,
            name="RPC_AIRE",
            description="Exchange process with only one commodity exchanged",
            domain=[g.allreg, g.prc, g.Com],
        )
        g.RpcEmis = Set(
            m,
            name="RPC_EMIS",
            description="Process with emission COM_GRP",
            domain=[g.r, g.p, g.comgrp],
        )
        g.FsEmis = Set(
            m,
            name="FS_EMIS",
            description="Indicator for emission related FLO_SUM",
            domain=[g.r, g.p, g.comgrp, g.c, g.Com],
        )
        g.FsEmit = Set(
            m,
            name="FS_EMIT",
            description="Indicator for emission related FLO_SUM",
            domain=[g.r, g.p, g.Com, g.comgrp, g.c],
        )
        g.RcIop = Set(
            m,
            name="RC_IOP",
            description="Processes associated with commodity",
            domain=[g.r, g.c, g.io, g.p],
        )
        g.RtcsSing = Set(
            m,
            name="RTCS_SING",
            description="Commodity not being consumed",
            domain=[g.r, g.t, g.c, g.s, g.io],
        )
        g.RtpsOff = Set(
            m,
            name="RTPS_OFF",
            description="Process being turned off",
            domain=[g.r, g.t, g.p, g.s],
        )
        g.RtpcsOut = Set(
            m,
            name="RTPCS_OUT",
            description="Process flows being turned off",
            domain=[g.r, g.allyear, g.p, g.c, g.s],
        )
        g.RpcFfunc = Set(
            m,
            name="RPC_FFUNC",
            description="RPC_ACT Commodity in FFUNC",
            domain=[g.r, g.p, g.c],
        )
        g.RpccFfunc = Set(
            m,
            name="RPCC_FFUNC",
            description="Pair of FFUNC commodities with RPC_ACT commodity",
            domain=[g.Reg, g.prc, g.cg, g.cg],
        )
        g.PrcCap = Set(
            m,
            name="PRC_CAP",
            description="Process requiring capacity variable",
            domain=[g.Reg, g.prc],
        )
        g.PrcAct = Set(
            m,
            name="PRC_ACT",
            description="Process requiring activity equation",
            domain=[g.Reg, g.prc],
        )
        g.PrcTs2 = Set(
            m,
            name="PRC_TS2",
            description="Alias for PRC_TS of processes with RPC_ACT",
            domain=[g.Reg, g.prc, g.ts],
        )
        g.RpcgPtran = Set(
            m,
            name="RPCG_PTRAN",
            description="Set for FLO_FUNC/FLO_SUM based substitution",
            domain=[g.r, g.p, g.Com, g.c, g.cg, g.cg],
        )
        g.KeepFlof = Set(
            m,
            name="KEEP_FLOF",
            description="Set for FFUNC-defined flows retained",
            domain=[g.r, g.p, g.c],
        )
        g.cg3 = Alias(m, "CG3", alias_with=g.comgrp)
        g.cg4 = Alias(m, "CG4", alias_with=g.comgrp)
        # ------------------------------------------------------------------------------
        # * Parameters used in report routine
        # *------------------------------------------------------------------------------
        # * Label lengths exceeding default
        # $SETGLOBAL RL 'R.TL:MAX(12,R.LEN)' SETGLOBAL PL 'P.TL:MAX(12,P.LEN)' SETGLOBAL CL C.TL:MAX(12,C.LEN)
        self.env.set_global("rl", "R.TL:MAX(12,R.LEN)")
        self.env.set_global("pl", "P.TL:MAX(12,P.LEN)")
        self.env.set_global("cl", "C.TL:MAX(12,C.LEN)")
        # $IFI NOT %G2X6%==YES $SETGLOBAL RL 'R.TL:MAX(12,CARD(R.TL))' SETGLOBAL PL 'P.TL:MAX(12,CARD(P.TL))' SETGLOBAL CL C.TL:MAX(12,CARD(C.TL))
        if self.env.g2x6 != "YES":
            self.env.set_global("rl", "R.TL:MAX(12,CARD(R.TL))")
            self.env.set_global("pl", "P.TL:MAX(12,CARD(P.TL))")
            self.env.set_global("cl", "C.TL:MAX(12,CARD(C.TL))")

        g.par_flo = Parameter(
            m,
            name="PAR_FLO",
            description="Flow parameter",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s],
        )
        g.par_flom = Parameter(
            m,
            name="PAR_FLOM",
            description="Reduced cost of flow variable",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s],
        )
        g.par_ire = Parameter(
            m,
            name="PAR_IRE",
            description="Parameter for im/export flow",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, g.impexp],
        )
        g.par_irem = Parameter(
            m,
            name="PAR_IREM",
            description="Reduced cost of import/export flow",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, g.impexp],
        )
        g.par_objinv = Parameter(
            m,
            name="PAR_OBJINV",
            description="Annual discounted investment costs",
            domain=[g.r, g.allyear, g.allyear, g.p, g.cur],
        )
        g.par_objdec = Parameter(
            m,
            name="PAR_OBJDEC",
            description="Annual discounted decommissioning costs",
            domain=[g.r, g.allyear, g.allyear, g.p, g.cur],
        )
        g.par_objfix = Parameter(
            m,
            name="PAR_OBJFIX",
            description="Annual discounted FOM cost",
            domain=[g.r, g.allyear, g.allyear, g.p, g.cur],
        )
        g.par_objsal = Parameter(
            m,
            name="PAR_OBJSAL",
            description="Annual discounted salvage value",
            domain=[g.r, g.allyear, g.p, g.cur],
        )
        g.par_objlat = Parameter(
            m,
            name="PAR_OBJLAT",
            description="Annual discounted late costs",
            domain=[g.r, g.allyear, g.p, g.cur],
        )
        g.par_objact = Parameter(
            m,
            name="PAR_OBJACT",
            description="Annual discounted variable costs",
            domain=[g.r, g.allyear, g.allyear, g.p, g.ts, g.cur],
        )
        g.par_objflo = Parameter(
            m,
            name="PAR_OBJFLO",
            description="Annual discounted flow costs (incl import/export)",
            domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.ts, g.cur],
        )
        g.par_objcom = Parameter(
            m,
            name="PAR_OBJCOM",
            description="Annual discounted commodity costs ",
            domain=[g.r, g.allyear, g.Com, g.ts, g.cur],
        )
        g.par_objble = Parameter(
            m,
            name="PAR_OBJBLE",
            description="Annual discounted blending costs",
            domain=[g.r, g.allyear, g.Com, g.cur],
        )
        g.par_objels = Parameter(
            m,
            name="PAR_OBJELS",
            description="Annual discounted elastic demand cost term",
            domain=[g.r, g.allyear, g.Com, g.cur],
        )

        # *----------------------------------------------------------------------------------------------
        # * GLOBALS SECTION - Safe Set of TIMES Critical Global control variables
        # *----------------------------------------------------------------------------------------------
        self.env.set_global("timesed", "0")
        control_abort_msg = "Abort Internal Control variable being set by user, aborted"
        self.env.set_scoped("ControlAbort", control_abort_msg)
        self.label_reset(msg=control_abort_msg)

    def label_reset(self, msg: str) -> None:
        if self.x2 != "":
            return

        # Normal Tags for standard TIMES (changed under stochastic mode)
        self.env.set_global("sw_notags", self.x1)
        ## Integrity check in full scope
        if self.env.sw_notags != self.x1:
            raise ValueError(f"{msg}: sw_notags")
        if self.x1 == "":
            self.env.set_global(
                "sw_notags",
                "SET EQ 'EQ' SET VAR 'VAR' SET SWS '' SET SOW '' SET SWT '' SET SWD '' SET SWTD '' SET SWSW '' SET VART 'VAR' SET VARV 'VAR' SET VARM 'VAR' SET VARTT VAR",
            )

        # Helper for process tranformation shape controls
        shff = self.x1
        self.env.set_global("rcapsub", self.x1)
        self.env.set_global("rcapsbm", self.x1)
        if self.x1 == "1":
            self.env.set_global("rcapsub_GP", Number(1))
            self.env.set_global("rcapsbm_GP", Number(1))
        elif self.x1 == "":
            self.env.set_global("rcapsub_GP", Number(0))
            self.env.set_global("rcapsbm_GP", Number(0))

        rcapsub = self.env.rcapsub
        rcapsbm = self.env.rcapsbm
        if f"{shff}{rcapsub}{rcapsbm}" != f"{self.x1}{self.x1}{self.x1}":
            raise ValueError(f"{msg}: shff / rcapsub")

        # Additional tags for stochastic
        self.env.set_global("mx", self.x1)
        mx = () if self.x1 == "" else ("1",)
        self.env.set_global("mx_GP", mx)
        self.env.set_global("scum", self.x1)
        # SCUM is a multiplicative suffix in the source, so the empty string is a
        # neutral factor of one for the GAMSPy twin (rpt_ext.cli replaces it with
        # SW_TPROB(T,WW) when SCUM is set).
        self.env.set_global("scum_GP", Number(1))
        self.env.set_global("sw_stvars", self.x1)
        mx = self.env.mx
        scum = self.env.scum
        sw_stvars = self.env.sw_stvars
        if f"{mx}{scum}{sw_stvars}" != f"{self.x1}{self.x1}{self.x1}":
            raise ValueError(f"{msg}: mx / sw_stvars / scum")

        # Objective function variants
        self.env.set_global("capjd", self.x1)
        self.env.set_global("capwd", self.x1)
        # Both are multiplicative prefixes in the source, so the empty string is a
        # neutral factor of one for the GAMSPy twins (see coef_alt.lin for the
        # variants that carry an actual weight).
        self.env.set_global("capjd_GP", Number(1))
        self.env.set_global("capwd_GP", Number(1))
        capjd = self.env.capjd
        capwd = self.env.capwd
        if f"{capjd}{capwd}" != f"{self.x1}{self.x1}":
            raise ValueError(f"{msg}: CAPxD")

        self.env.set_global("swx", self.x1)
        self.env.set_global("swtx", self.x1)
        if self.x1 == "1":
            self.env.set_global("swx_GP", (self.x1,))
            self.env.set_global("swtx_GP", Number(1))  # signals true
        elif self.x1 == "":
            self.env.set_global("swx_GP", ())
            self.env.set_global("swtx_GP", Number(1))  # signals true
        else:
            raise ValueError(f"Unexpected value {self.x1} for x1.")

        self.env.set_global("varmac", self.x1)
        swx = self.env.swx
        swtx = self.env.swtx
        varmac = self.env.varmac
        if f"{swx}{swtx}{varmac}" != f"{self.x1}{self.x1}{self.x1}":
            raise ValueError(f"{msg}: SWX")
        self.env.set_global("swx", ",'1'")
        self.env.set_global("swx_GP", ("1",))

        # $SET TMP '%CTST%'
        tmp = self.env.ctst
        # SETGLOBAL CTST %X1%
        self.env.set_global("ctst", self.x1)
        # $IF NOT "%CTST%"=='%X1%' $%ControlAbort%: CTST
        if self.env.ctst != self.x1:
            control_abort = self.env.get("ControlAbort")
            raise ValueError(f"{control_abort}: CTST")
        # $SETGLOBAL CTST %TMP%
        self.env.set_global("ctst", tmp)

        # Tags for stochastic TIMES (set in stages.stc)
        self.env.set_global("sw_tags", self.x1)
        if self.env.sw_tags != self.x1:
            raise ValueError(f"{control_abort}: sw_tags")
        self.env.set_global("sw_tags", self.x1)

        # --- Recursive Reset Logic ---
        if self.x1 != "":
            self.x1 = ""
            self.label_reset(msg=msg)

        self.env.set_global("varmac", "0==1")
