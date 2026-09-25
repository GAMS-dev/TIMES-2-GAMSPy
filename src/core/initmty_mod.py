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

from gamspy import Alias, Ord, Parameter, Set, Sum

from core.base_class import GamsClass
from core.err_stat_mod import ErrStatMod
from core.initmty_abs import InitmtyAbs
from core.initmty_cli import InitmtyCli
from core.initmty_dsc import InitmtyDsc
from core.initmty_etl import InitmtyEtl
from core.initmty_ier import InitmtyIer
from core.initmty_mlf import InitmtyMlf
from core.initmty_msa import InitmtyMsa
from core.initmty_stc import InitmtyStc
from core.initmty_tm import InitmtyTm
from core.initmty_vda import InitmtyVda
from core.main_ext_mod import include_extension
from core.maindrv_mod import MainDrvMod
from core.utils import EscapeStack, expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

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

        g = self.tc
        m = g.container

        def set_section() -> None:
            """
            SET SECTION
            Note: the *-out user SETs are declared in INITSYS.MOD
            """

            # commodities
            # g.comgrp = Set(m, name='COM_GRP', description='All CGs and each individal commodity')
            # g.Com = Set(m, name='COM', description='All Commodities', domain=[g.comgrp])
            g.ComDesc = Set(
                m,
                name="COM_DESC",
                description="Region-based commodity descriptions",
                domain=[g.Reg, g.Com],
            )
            # g.ComType = Set(m, name='COM_TYPE', description='Primary grouping of commodities', domain=[g.comgrp])
            g.ComGmap = Set(
                m,
                name="COM_GMAP",
                description="User groups of individual commodities",
                domain=[g.Reg, g.comgrp, g.Com],
            )
            g.ComLim = Set(
                m,
                name="COM_LIM",
                description="List of equation type for balance",
                domain=[g.Reg, g.Com, g.lim],
            )
            g.ComOff = Set(
                m,
                name="COM_OFF",
                description="Periods for which a commodity is unavailable",
                domain=[g.Reg, g.Com, "*", "*"],
            )
            g.ComTmap = Set(
                m,
                name="COM_TMAP",
                description="Primary grouping of commodities",
                domain=[g.Reg, g.ComType, g.Com],
            )
            g.ComTs = Set(
                m,
                name="COM_TS",
                description="List of commodity timeslices",
                domain=[g.Reg, g.Com, g.allts],
            )
            g.ComTsl = Set(
                m,
                name="COM_TSL",
                description="Level at which a commodity tracked",
                domain=[g.Reg, g.Com, g.tslvl],
            )
            g.ComUnit = Set(
                m,
                name="COM_UNIT",
                description="Units associated with each commodity",
                domain=[g.Reg, g.Com, g.UnitsCom],
            )

            # currency
            # g.cur = Set(m, name="CUR", description="Currencies (c$)")
            g.CurMap = Set(
                m,
                name="CUR_MAP",
                description="Grouping of the currenies",
                domain=[g.Reg, g.curgrp, g.cur],
            )

            # demands / emissions / financials
            g.DemSmap = Set(
                m,
                name="DEM_SMAP",
                description="Grouping of DEMs (commodities) to their sector",
                domain=[g.Reg, g.demsect, g.Com],
            )
            g.EnvMap = Set(
                m,
                name="ENV_MAP",
                description="Grouping of ENVs (commodities) to their emissions group",
                domain=[g.Reg, g.envgrp, g.Com],
            )
            g.FinMap = Set(
                m,
                name="FIN_MAP",
                description="Grouping of FINs (commodities) to their financial group",
                domain=[g.Reg, g.fingrp, g.Com],
            )

            # materials
            g.MatGmap = Set(
                m,
                name="MAT_GMAP",
                description="Grouping of materials",
                domain=[g.Reg, g.matgrp, g.Com],
            )
            g.MatTmap = Set(
                m,
                name="MAT_TMAP",
                description="Material by type",
                domain=[g.Reg, g.mattype, g.Com],
            )
            g.MatVol = Set(
                m,
                name="MAT_VOL",
                description="Material accounted for by volume",
                domain=[g.Reg, g.Com],
            )
            g.MatWt = Set(
                m,
                name="MAT_WT",
                description="Material accounted for by weight",
                domain=[g.Reg, g.Com],
            )

            # energy
            g.NrgFmap = Set(
                m,
                name="NRG_FMAP",
                description="Grouping of NRG by Solid/Liquid/Gas",
                domain=[g.Reg, g.nrgform, g.Com],
            )
            g.NrgGmap = Set(
                m,
                name="NRG_GMAP",
                description="Association of energy carriers to grids",
                domain=[g.Reg, g.nrggrid, g.Com],
            )
            g.NrgTmap = Set(
                m,
                name="NRG_TMAP",
                description="Grouping of energy carriers by type",
                domain=[g.Reg, g.nrgtype, g.Com],
            )

            # process
            # g.prc = Set(m, name='PRC', description='List of all processes')
            g.PrcAoff = Set(
                m,
                name="PRC_AOFF",
                description="Periods for which activity is unavailable",
                domain=[g.Reg, g.prc, "*", "*"],
            )
            g.PrcActunt = Set(
                m,
                name="PRC_ACTUNT",
                description="Primary commodity (or group) & activity unit",
                domain=[g.Reg, g.prc, g.cg, g.UnitsAct],
            )
            g.PrcCapunt = Set(
                m,
                name="PRC_CAPUNT",
                description="Unit of capacity",
                domain=[g.Reg, g.prc, g.cg, g.UnitsCap],
            )
            g.PrcCg = Set(
                m,
                name="PRC_CG",
                description="Commodity groups for a process",
                domain=[g.r, g.prc, g.comgrp],
            )
            g.PrcDesc = Set(
                m,
                name="PRC_DESC",
                description="Process descriptions by region",
                domain=[g.r, g.p],
            )
            g.PrcFoff = Set(
                m,
                name="PRC_FOFF",
                description="Periods/timeslices for which flow is not possible",
                domain=[g.Reg, g.prc, g.Com, g.allts, "*", "*"],
            )
            g.PrcMap = Set(
                m,
                name="PRC_MAP",
                description="Grouping of processes to nature",
                domain=[g.Reg, g.prcgrp, g.prc],
            )
            g.PrcNoff = Set(
                m,
                name="PRC_NOFF",
                description="Periods for which new capacity can NOT be built",
                domain=[g.Reg, g.prc, "*", "*"],
            )
            g.PrcRmap = Set(
                m,
                name="PRC_RMAP",
                description="Grouping of XTRACT processes",
                domain=[g.Reg, g.prcrsourc, g.prc],
            )
            g.PrcSpg = Set(
                m,
                name="PRC_SPG",
                description="Shadow Primary Group",
                domain=[g.Reg, g.prc, g.comgrp],
            )
            g.PrcTs = Set(
                m,
                name="PRC_TS",
                description="Timeslices for a process",
                domain=[g.allreg, g.prc, g.allts],
            )
            g.PrcTsl = Set(
                m,
                name="PRC_TSL",
                description="Timeslice level for a process",
                domain=[g.Reg, g.prc, g.tslvl],
            )
            g.PrcVint = Set(
                m,
                name="PRC_VINT",
                description="Process is to be vintaged",
                domain=[g.Reg, g.prc],
            )
            g.PrcDscncap = Set(
                m,
                name="PRC_DSCNCAP",
                description="Process with discrete capacity additions",
                domain=[g.r, g.p],
            )
            g.PrcRcap = Set(
                m,
                name="PRC_RCAP",
                description="Process with early retirement",
                domain=[g.Reg, g.prc],
            )
            g.PrcSimv = Set(
                m,
                name="PRC_SIMV",
                description="Process is to be vintage-simulated",
                domain=[g.Reg, g.prc],
            )

            # region
            # g.Reg = Set(m, name='REG', description='List of Regions', domain=[g.allreg])
            g.reggrp = Set(
                m, name="REG_GRP", description="List of regional groups", domain=["*"]
            )
            g.RegRmap = Set(
                m,
                name="REG_RMAP",
                description="Grouping of regions in/out of area of study",
                domain=[g.reggrp, g.allreg],
            )

            # time
            # g.ts = Set(
            #     m, name="TS", description="'Time slices of the year", domain=[g.allts]
            # )

            #   ALIAS(ALL_TS,TS,S,SL,S2);
            g.ts = Alias(m, "TS", alias_with=g.allts)
            g.s = Alias(m, "S", alias_with=g.allts)
            g.sl = Alias(m, "SL", alias_with=g.allts)
            g.s2 = Alias(m, "S2", alias_with=g.allts)

            g.TsOff = Set(
                m,
                name="TS_OFF",
                domain=[g.Reg, g.ts, g.bohyear, g.eohyear],
                description="Timeslices turned off",
            )
            g.TsGroup = Set(
                m,
                name="TS_GROUP",
                domain=[g.allreg, g.tslvl, g.ts],
                description="Timeslice Level assignment",
            )
            g.TsMap = Set(
                m,
                name="TS_MAP",
                domain=[g.allreg, g.allts, g.allts],
                description="Timeslice hierarchy tree: node+below",
            )
            g.Milestonyr = Set(
                m,
                name="MILESTONYR",
                domain=[g.allyear],
                description="Projection years for which model to be run",
            )

            #   ALIAS(MILESTONYR,T,TT);
            g.t = Alias(m, "T", alias_with=g.Milestonyr)
            g.tt = Alias(m, "TT", alias_with=g.Milestonyr)

            g.Datayear = Set(
                m,
                name="DATAYEAR",
                domain=[g.allyear],
                description="Years for which user data is provided",
            )
            g.Pastyear = Set(
                m,
                name="PASTYEAR",
                domain=[g.allyear],
                description="Years before 1st MILESTONYR for which PASTI needs to be handled",
            )
            g.Modlyear = Set(
                m,
                name="MODLYEAR",
                domain=[g.allyear],
                description="Years for which the model is to be run (MILESTONYR+PASTYEAR)",
            )

            g.tsl = Alias(m, "TSL", alias_with=g.tslvl)

            # topology
            g.Top = Set(
                m,
                name="TOP",
                description="Topology for all process",
                domain=[g.Reg, g.prc, g.Com, g.io],
            )
            g.TopIre = Set(
                m,
                name="TOP_IRE",
                description="Trade within area of study",
                domain=[g.allreg, g.Com, g.allreg, g.Com, g.prc],
            )

            # peaking
            g.ComPeak = Set(
                m,
                name="COM_PEAK",
                description="Peaking required flag",
                domain=[g.Reg, g.comgrp],
            )
            g.ComPkts = Set(
                m,
                name="COM_PKTS",
                description="Peaking time-slices",
                domain=[g.Reg, g.comgrp, g.ts],
            )
            g.PrcPkno = Set(
                m,
                name="PRC_PKNO",
                description="Processes which cannot be involved in peaking",
                domain=[g.allreg, g.prc],
            )
            g.PrcPkaf = Set(
                m,
                name="PRC_PKAF",
                description="Flag for default value of NCAP_PKCNT",
                domain=[g.allreg, g.prc],
            )

            # storage
            g.PrcNstts = Set(
                m,
                name="PRC_NSTTS",
                description="Night storage process and time-slice for storaging",
                domain=[g.Reg, g.prc, g.allts],
            )
            g.PrcStgtss = Set(
                m,
                name="PRC_STGTSS",
                description="Storage process and stored commodity for time-slice storage",
                domain=[g.Reg, g.prc, g.Com],
            )
            g.PrcStgips = Set(
                m,
                name="PRC_STGIPS",
                description="Storage process and stored commodity for inter-period storage",
                domain=[g.Reg, g.prc, g.Com],
            )

            # user constraints
            g.ucn = Set(
                m,
                name="UC_N",
                domain=["*"],
                description="Names of all manual constraints",
                records=["OBJVAR"],
            )
            g.UcTSucc = Set(
                m,
                name="UC_T_SUCC",
                domain=[g.allr, g.ucn, g.allyear],
                description="'Specification of periods",
            )
            g.UcTSum = Set(
                m,
                name="UC_T_SUM",
                domain=[g.allr, g.ucn, g.allyear],
                description="Specification of periods, if UC_DYN=SUCC",
            )
            g.UcTEach = Set(
                m,
                name="UC_T_EACH",
                domain=[g.allr, g.ucn, g.allyear],
                description="Specification of periods, if UC_DYN=EACH",
            )
            g.UcRSum = Set(
                m,
                name="UC_R_SUM",
                domain=[g.allr, g.ucn],
                description="Specification of regions, if UC_REG=SUM",
            )
            g.UcREach = Set(
                m,
                name="UC_R_EACH",
                domain=[g.allr, g.ucn],
                description="Specification of regions, if UC_REG=EACH",
            )
            g.UcTsSum = Set(
                m,
                name="UC_TS_SUM",
                domain=[g.allr, g.ucn, g.allts],
                description="Specification of time-slices, if UC_TS=SUM",
            )
            g.UcTsEach = Set(
                m,
                name="UC_TS_EACH",
                domain=[g.allr, g.ucn, g.allts],
                description="Specification of time-slices, if UC_TS=EACH",
            )
            g.UcAttr = Set(
                m,
                name="UC_ATTR",
                domain=[g.allr, g.ucn, g.side, g.ucgrptype, g.ucname],
                description="Mapping of parameter names to groups",
            )
            g.UcTsl = Set(
                m,
                name="UC_TSL",
                domain=[g.allr, g.ucn, g.side, g.tslvl],
                description="UC timeslice level",
            )

            g.ucnA = Alias(m, name="UCN", alias_with=g.ucn)

            # miscellaneous
            # g.Sow = Set(m, name="SOW", description="Stochastic State-of-the-World")
            g.SwT = Set(
                m,
                name="SW_T",
                domain=[g.allyear, g.allsow],
                description="Stochastic state indexes by period",
            )
            g.GUamat = Set(
                m,
                name="G_UAMAT",
                domain=[g.u],
                description="Unit for activity of material process",
            )
            g.GUanrg = Set(
                m,
                name="G_UANRG",
                domain=[g.u],
                description="Unit for activity of energy process",
            )
            g.GUcmat = Set(
                m,
                name="G_UCMAT",
                domain=[g.u],
                description="Unit for capacity of material process",
            )
            g.GUcnrg = Set(
                m,
                name="G_UCNRG",
                domain=[g.u],
                description="Unit for capacity of energy process",
            )
            g.GRcur = Set(
                m,
                name="G_RCUR",
                domain=[g.Reg, g.cur],
                description="Main currency unit by region",
            )

            # Predefined system CGs and one COM:
            self.env.set_if_not_exists("pgprim", "ACT", scope="global")
            comgrp_records = [self.env.pgprim, "CAPFLO"]
            if g.comgrp is None:
                g.comgrp = Set(
                    m,
                    name="COM_GRP",
                    description="All CGs and each individal commodity",
                    records=comgrp_records,
                )
            else:
                expand_set(g.comgrp, comgrp_records)
            g.Actcg = Set(m, name="ACTCG", domain=[g.cg], records=[self.env.pgprim])
            com_records = [self.env.pgprim]
            if g.Com is None:
                g.Com = Set(
                    m,
                    name="COM",
                    domain=[g.comgrp],
                    description="Commodities",
                    records=com_records,
                )
            else:
                expand_set(g.Com, com_records)

        def parameters_section() -> None:
            """Parameters section"""
            # time
            g.b = Parameter(
                m,
                name="B",
                description="Beginning year of each model period",
                domain=[g.allyear],
            )
            g.e = Parameter(
                m,
                name="E",
                description="Ending year of each model period",
                domain=[g.allyear],
            )
            g.m = Parameter(
                m,
                name="M",
                description="Middle year of each Period",
                domain=[g.allyear],
            )
            g.d = Parameter(
                m, name="D", description="Length of each period", domain=[g.allyear]
            )

            # Activity
            g.act_bnd = Parameter(
                m,
                name="ACT_BND",
                domain=[g.Reg, g.allyear, g.prc, g.ts, g.bd],
                description="Bound on activity of a process",
            )
            g.act_cost = Parameter(
                m,
                name="ACT_COST",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Variable costs associated with activity of a process",
            )
            g.act_cstup = Parameter(
                m,
                name="ACT_CSTUP",
                domain=[g.r, g.allyear, g.p, g.tslvl, g.cur],
                description="Variable costs associated with startup of a process",
            )
            g.act_cstsd = Parameter(
                m,
                name="ACT_CSTSD",
                domain=[g.r, g.allyear, g.p, g.upt, g.bd, g.cur],
                description="'Start-up (BD=UP) and shutdown costs (BD=LO) per unit of started-up capacity, by start-up type",
            )
            g.act_cstrmp = Parameter(
                m,
                name="ACT_CSTRMP",
                domain=[g.r, g.allyear, g.p, g.lA, g.cur],
                description="Ramp-up (L=UP) or ramp-down (L=LO) cost per unit of load change",
            )
            g.act_flo = Parameter(
                m,
                name="ACT_FLO",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.s],
                description="General process transformation parameter",
            )
            g.act_time = Parameter(
                m,
                name="ACT_TIME",
                domain=[g.r, g.allyear, g.p, g.lA],
                description="Minimum online/offline hours",
            )
            g.act_cum = Parameter(
                m,
                name="ACT_CUM",
                domain=[g.Reg, g.prc, g.item, g.item, g.lim],
                description="Bound on cumulative activity",
            )

            # New Capacity
            g.ncap_af = Parameter(
                m,
                name="NCAP_AF",
                domain=[g.Reg, g.allyear, g.prc, g.ts, g.bd],
                description="Availability of capacity",
            )
            g.ncap_afa = Parameter(
                m,
                name="NCAP_AFA",
                domain=[g.Reg, g.allyear, g.prc, g.bd],
                description="Annual Availability of capacity",
            )
            g.ncap_afs = Parameter(
                m,
                name="NCAP_AFS",
                domain=[g.Reg, g.allyear, g.prc, g.ts, g.bd],
                description="Seasonal Availability of capacity",
            )
            g.ncap_afx = Parameter(
                m,
                name="NCAP_AFX",
                domain=[g.r, g.allyear, g.p],
                description="Change in capacity availability",
            )
            g.ncap_afsx = Parameter(
                m,
                name="NCAP_AFSX",
                domain=[g.r, g.allyear, g.p, g.bd],
                description="Change in seasonal capacity availability",
            )
            g.ncap_afm = Parameter(
                m,
                name="NCAP_AFM",
                domain=[g.r, g.allyear, g.p],
                description="Pointer to availity change multiplier",
            )
            g.ncap_bnd = Parameter(
                m,
                name="NCAP_BND",
                domain=[g.Reg, g.allyear, g.prc, g.lim],
                description="Bound on overall capacity in a period",
            )
            g.ncap_bpme = Parameter(
                m,
                name="NCAP_BPME",
                domain=[g.Reg, g.allyear, g.prc],
                description="Back pressure mode efficiency (or total eff.)",
            )
            g.ncap_cdme = Parameter(
                m,
                name="NCAP_CDME",
                domain=[g.Reg, g.allyear, g.prc],
                description="Condensing mode efficiency",
            )
            g.ncap_ceh = Parameter(
                m,
                name="NCAP_CEH",
                domain=[g.Reg, g.allyear, g.prc],
                description="Coefficient of electricity to heat",
            )
            g.ncap_chpr = Parameter(
                m,
                name="NCAP_CHPR",
                domain=[g.Reg, g.allyear, g.prc, g.lim],
                description="Combined heat:power ratio",
            )
            g.ncap_cled = Parameter(
                m,
                name="NCAP_CLED",
                domain=[g.Reg, g.allyear, g.prc, g.Com],
                description="Leadtime of a commodity before new capacity ready",
            )
            g.ncap_clag = Parameter(
                m,
                name="NCAP_CLAG",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.io],
                description="Lagtime of a commodity after new capacity ready",
            )
            g.ncap_com = Parameter(
                m,
                name="NCAP_COM",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.io],
                description="Use (but +) of commodity based upon capacity",
            )
            g.ncap_cost = Parameter(
                m,
                name="NCAP_COST",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Investment cost for new capacity",
            )
            g.ncap_cpx = Parameter(
                m,
                name="NCAP_CPX",
                domain=[g.Reg, g.allyear, g.prc],
                description="Pointer to capacity transfer multiplier",
            )
            g.ncap_drate = Parameter(
                m,
                name="NCAP_DRATE",
                domain=[g.Reg, g.allyear, g.prc],
                description="Process specific discount (hurdle) rate",
            )
            g.ncap_fdr = Parameter(
                m,
                name="NCAP_FDR",
                domain=[g.Reg, g.allyear, g.prc],
                description="Functional depreciation rate of process",
            )
            g.ncap_elife = Parameter(
                m,
                name="NCAP_ELIFE",
                domain=[g.Reg, g.allyear, g.prc],
                description="Economic (payback) lifetime",
            )
            g.ncap_fom = Parameter(
                m,
                name="NCAP_FOM",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Fixed annual O&M costs",
            )
            g.ncap_fomx = Parameter(
                m,
                name="NCAP_FOMX",
                domain=[g.Reg, g.allyear, g.prc],
                description="Change in fixed O&M",
            )
            g.ncap_fomm = Parameter(
                m,
                name="NCAP_FOMM",
                domain=[g.Reg, g.allyear, g.prc],
                description="Pointer to fixed O&M change multiplier",
            )
            g.ncap_fsub = Parameter(
                m,
                name="NCAP_FSUB",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Fixed tax on installed capacity",
            )
            g.ncap_fsubx = Parameter(
                m,
                name="NCAP_FSUBX",
                domain=[g.Reg, g.allyear, g.prc],
                description="Change in fixed tax",
            )
            g.ncap_fsubm = Parameter(
                m,
                name="NCAP_FSUBM",
                domain=[g.Reg, g.allyear, g.prc],
                description="Pointer to fixed subsidy change multiplier",
            )
            g.ncap_ftax = Parameter(
                m,
                name="NCAP_FTAX",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Fixed tax on installed capacity",
            )
            g.ncap_ftaxx = Parameter(
                m,
                name="NCAP_FTAXX",
                domain=[g.Reg, g.allyear, g.prc],
                description="Change in fixed tax",
            )
            g.ncap_ftaxm = Parameter(
                m,
                name="NCAP_FTAXM",
                domain=[g.Reg, g.allyear, g.prc],
                description="Pointer to fixed tax change multiplier",
            )
            g.ncap_icom = Parameter(
                m,
                name="NCAP_ICOM",
                domain=[g.Reg, g.allyear, g.prc, g.Com],
                description="Input of commodity for install of new capacity",
            )
            g.ncap_iled = Parameter(
                m,
                name="NCAP_ILED",
                domain=[g.Reg, g.allyear, g.prc],
                description="Lead-time required for building a new capacity",
            )
            g.ncap_isub = Parameter(
                m,
                name="NCAP_ISUB",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Subsidy for a new investment in capacity",
            )
            g.ncap_itax = Parameter(
                m,
                name="NCAP_ITAX",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Tax on a new investment in capacity",
            )
            g.ncap_ispct = Parameter(
                m,
                name="NCAP_ISPCT",
                domain=[g.Reg, g.allyear, g.prc],
                description="Subsidy as % of new investment cost",
            )
            g.ncap_lcost = Parameter(
                m,
                name="NCAP_LCOST",
                domain=[g.Reg, g.allyear, g.prc],
                description="% labor cost of new investment",
            )
            g.ncap_lfom = Parameter(
                m,
                name="NCAP_LFOM",
                domain=[g.Reg, g.allyear, g.prc],
                description="% labor cost of fixed O&M",
            )
            g.ncap_pasti = Parameter(
                m,
                name="NCAP_PASTI",
                domain=[g.Reg, g.allyear, g.prc],
                description="Capacity install prior to study years",
            )
            g.ncap_pasty = Parameter(
                m,
                name="NCAP_PASTY",
                domain=[g.Reg, g.allyear, g.prc],
                description="Buildup years for past investments",
            )
            g.ncap_tlife = Parameter(
                m,
                name="NCAP_TLIFE",
                domain=[g.Reg, g.allyear, g.prc],
                description="Technical lifetime of a process",
            )
            g.ncap_olife = Parameter(
                m,
                name="NCAP_OLIFE",
                domain=[g.Reg, g.allyear, g.prc],
                description="Operating lifetime of a process",
            )
            g.rcap_blk = Parameter(
                m,
                name="RCAP_BLK",
                domain=[g.Reg, g.allyear, g.prc],
                description="Retirement block size",
            )
            g.rcap_bnd = Parameter(
                m,
                name="RCAP_BND",
                domain=[g.Reg, g.allyear, g.prc, g.lim],
                description="Retirement bounds",
            )

            # decommissioning of Capacity
            g.ncap_dcost = Parameter(
                m,
                name="NCAP_DCOST",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
                description="Cost of decomissioning",
            )
            g.ncap_dlag = Parameter(
                m,
                name="NCAP_DLAG",
                domain=[g.Reg, g.allyear, g.prc],
                description="Delay to begin decomissioning",
            )
            g.ncap_dlagc = Parameter(
                m,
                name="NCAP_DLAGC",
                description="Cost of decomissioning delay",
                domain=[g.Reg, g.allyear, g.prc, g.cur],
            )
            g.ncap_delif = Parameter(
                m,
                name="NCAP_DELIF",
                description="Economic lifetime to pay for decomissioning",
                domain=[g.Reg, g.allyear, g.prc],
            )
            g.ncap_dlife = Parameter(
                m,
                name="NCAP_DLIFE",
                description="Time for the actual decomissioning",
                domain=[g.Reg, g.allyear, g.prc],
            )
            g.ncap_ocom = Parameter(
                m,
                name="NCAP_OCOM",
                description="Commodity release during decomissioning",
                domain=[g.Reg, g.allyear, g.prc, g.Com],
            )
            g.ncap_valu = Parameter(
                m,
                name="NCAP_VALU",
                description="Value of material released during decomissioning",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.cur],
            )

            # capacity installed
            g.ncap_start = Parameter(
                m,
                name="NCAP_START",
                domain=[g.Reg, g.prc],
                description="Start year for new investments",
            )
            g.ncap_semi = Parameter(
                m,
                name="NCAP_SEMI",
                domain=[g.r, g.allyear, g.p],
                description="Semi-continuous capacity, lower bound",
            )
            g.cap_bnd = Parameter(
                m,
                name="CAP_BND",
                domain=[g.Reg, g.allyear, g.prc, g.bd],
                description="Bound on total installed capacity in a period",
            )

            # general commodities
            g.com_bndnet = Parameter(
                m,
                name="COM_BNDNET",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.lim],
                description="Net bound on commodity (e.g., emissions)",
            )
            g.com_bndprd = Parameter(
                m,
                name="COM_BNDPRD",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.lim],
                description="Limit on production of a commodity",
            )
            g.com_cumnet = Parameter(
                m,
                name="COM_CUMNET",
                domain=[g.Reg, g.bohyear, g.eohyear, g.Com, g.lim],
                description="Cumulative net bound on commodity (e.g. emissions)",
            )
            g.com_cumprd = Parameter(
                m,
                name="COM_CUMPRD",
                domain=[g.Reg, g.bohyear, g.eohyear, g.Com, g.lim],
                description="Cumulative limit on production of a commodity",
            )
            g.com_cstnet = Parameter(
                m,
                name="COM_CSTNET",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Cost on Net of commodity (e.g. emissions tax)",
            )
            g.com_cstprd = Parameter(
                m,
                name="COM_CSTPRD",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Cost on production of a commodity",
            )
            g.com_fr = Parameter(
                m,
                name="COM_FR",
                domain=[g.Reg, g.allyear, g.Com, g.ts],
                description="Seasonal distribution of a commodity",
            )
            g.com_ie = Parameter(
                m,
                name="COM_IE",
                domain=[g.Reg, g.allyear, g.Com, g.ts],
                description="Seasonal efficiency of commodity",
            )
            g.com_subnet = Parameter(
                m,
                name="COM_SUBNET",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Subsidy on a commodity net",
            )
            g.com_subprd = Parameter(
                m,
                name="COM_SUBPRD",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Subsidy on production of a commodity net",
            )
            g.com_taxnet = Parameter(
                m,
                name="COM_TAXNET",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Tax on a commodity net",
            )
            g.com_taxprd = Parameter(
                m,
                name="COM_TAXPRD",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Tax on production of a commodity net",
            )
            g.com_agg = Parameter(
                m,
                name="COM_AGG",
                domain=[g.Reg, g.allyear, g.Com, g.Com],
                description="Commodity aggregation parameter",
            )

            # demands
            g.com_bprice = Parameter(
                m,
                name="COM_BPRICE",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.cur],
                description="Base price of elastic demands",
            )
            g.com_bqty = Parameter(
                m,
                name="COM_BQTY",
                domain=[g.Reg, g.Com, g.ts],
                description="Base quantity for elastic demands",
            )
            g.com_elast = Parameter(
                m,
                name="COM_ELAST",
                domain=[g.Reg, g.allyear, g.Com, g.ts, g.lim],
                description="Elasticity of demand",
            )
            g.com_elastx = Parameter(
                m,
                name="COM_ELASTX",
                domain=[g.Reg, g.allyear, g.Com, g.bd],
                description="Elasticity shape of demand",
            )
            g.com_proj = Parameter(
                m,
                name="COM_PROJ",
                domain=[g.Reg, g.allyear, g.Com],
                description="Demand baseline projection",
            )
            g.com_step = Parameter(
                m,
                name="COM_STEP",
                domain=[g.Reg, g.Com, g.lim],
                description="Step size for elastic demand",
            )
            g.com_voc = Parameter(
                m,
                name="COM_VOC",
                domain=[g.Reg, g.allyear, g.Com, g.bd],
                description="Variance of elastic demand",
            )

            # flow of commodities through processes
            g.flo_bnd = Parameter(
                m,
                name="FLO_BND",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.ts, g.bd],
                description="Bound on the flow variable",
            )
            g.flo_bdlvl = Parameter(
                m,
                name="FLO_BDLVL",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.s, g.bd],
                description="Bound on the flow variable by hourly rate level",
            )
            g.flo_cost = Parameter(
                m,
                name="FLO_COST",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.cur],
                description="Added variable O&M of using a commodity",
            )
            g.flo_deliv = Parameter(
                m,
                name="FLO_DELIV",
                description="Delivery cost for using a commodity",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.cur],
            )
            g.flo_feq = Parameter(
                m,
                name="FLO_FEQ",
                domain=[g.Reg, g.allyear, g.prc, g.Com],
                description="Fossil equivalent of a commodity in a process",
            )
            g.flo_fr = Parameter(
                m,
                name="FLO_FR",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.lim],
                description="Load-curve limitations for a process commodity flow",
            )
            g.flo_func = Parameter(
                m,
                name="FLO_FUNC",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.cg, g.ts],
                description="Relationship between 2 (group of) flows",
            )
            g.flo_funcx = Parameter(
                m,
                name="FLO_FUNCX",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.cg],
                description="Change in FLO_FUNC/FLO_SUM by age",
            )
            g.flo_shar = Parameter(
                m,
                name="FLO_SHAR",
                domain=[g.Reg, g.allyear, g.prc, g.c, g.cg, g.ts, g.bd],
                description="Relationship between members of the same flow group",
            )
            g.flo_sub = Parameter(
                m,
                name="FLO_SUB",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.cur],
                description="Subsidy for the production/use of a commodity",
            )
            g.flo_sum = Parameter(
                m,
                name="FLO_SUM",
                domain=[g.Reg, g.allyear, g.prc, g.cg, g.c, g.cg, g.ts],
                description="Multipier for commodity in cg1 where each is summed into cg2",
            )
            g.flo_tax = Parameter(
                m,
                name="FLO_TAX",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.cur],
                description="Tax on the production/use of a commodity",
            )
            g.flo_cum = Parameter(
                m,
                name="FLO_CUM",
                domain=[g.Reg, g.prc, g.Com, g.item, g.item, g.lim],
                description="Bound on cumulative flow",
            )
            g.flo_mark = Parameter(
                m,
                name="FLO_MARK",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.bd],
                description="Process-wise market share in total commodity production",
            )
            g.prc_mark = Parameter(
                m,
                name="PRC_MARK",
                domain=[g.Reg, g.allyear, g.prc, g.item, g.c, g.lim],
                description="Process group-wise market share",
            )
            g.prc_resid = Parameter(
                m,
                name="PRC_RESID",
                domain=[g.Reg, g.allyear, g.prc],
                description="Residual capacity available in each period",
            )
            g.prc_refit = Parameter(
                m,
                name="PRC_REFIT",
                domain=[g.Reg, g.prc, g.prc],
                description="Process with retrofit or life-extension",
            )

            # peak
            g.ncap_pkcnt = Parameter(
                m,
                name="NCAP_PKCNT",
                domain=[g.Reg, g.allyear, g.prc, g.allts],
                description="Fraction of capacity contributing to peaking in time-slice TS",
            )
            g.com_pkrsv = Parameter(
                m,
                name="COM_PKRSV",
                domain=[g.Reg, g.allyear, g.Com],
                description="Peaking reserve margin",
            )
            g.com_pkflx = Parameter(
                m,
                name="COM_PKFLX",
                domain=[g.Reg, g.allyear, g.Com, g.ts],
                description="Peaking flux ratio",
            )
            g.flo_pkcoi = Parameter(
                m,
                name="FLO_PKCOI",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.allts],
                description="Factor increasing the average demand",
            )

            # Storage
            g.stg_eff = Parameter(
                m,
                name="STG_EFF",
                domain=[g.Reg, g.allyear, g.prc],
                description="Storage efficiency",
            )
            g.stg_loss = Parameter(
                m,
                name="STG_LOSS",
                domain=[g.Reg, g.allyear, g.prc, g.s],
                description="Annual energy loss from a storage technology",
            )
            g.stg_chrg = Parameter(
                m,
                name="STG_CHRG",
                domain=[g.Reg, g.allyear, g.prc, g.s],
                description="Exogeneous charging of a storage technology ",
            )
            g.stg_sift = Parameter(
                m,
                name="STG_SIFT",
                domain=[g.r, g.allyear, g.p, g.c, g.s],
                description="Max load sifting in proportion to total load",
            )
            g.stgout_bnd = Parameter(
                m,
                name="STGOUT_BND",
                domain=[g.Reg, g.allyear, g.prc, g.c, g.s, g.bd],
                description="Bound on output-flow of storage process",
            )
            g.stgin_bnd = Parameter(
                m,
                name="STGIN_BND",
                domain=[g.Reg, g.allyear, g.prc, g.c, g.s, g.bd],
                description="Bound on output-flow of storage process",
            )

            # Process units
            g.prc_actflo = Parameter(
                m,
                name="PRC_ACTFLO",
                domain=[g.Reg, g.allyear, g.prc, g.cg],
                description="Convert from process activity to particular commodity flow",
            )
            g.prc_capact = Parameter(
                m,
                name="PRC_CAPACT",
                domain=[g.Reg, g.prc],
                description="Factor for going from capacity to activity",
            )
            g.prc_gmap = Parameter(
                m,
                name="PRC_GMAP",
                domain=[g.Reg, g.prc, g.item],
                description="User-defined groupings of processes",
            )

            # globals
            g.g_chngmony = Parameter(
                m,
                name="G_CHNGMONY",
                description="Exchange rate for currency",
                domain=[g.Reg, g.allyear, g.cur],
            )
            g.g_drate = Parameter(
                m,
                name="G_DRATE",
                description="Discount rate for a currency",
                domain=[g.Reg, g.allyear, g.cur],
            )
            g.g_rfrir = Parameter(
                m,
                name="G_RFRIR",
                description="Riskfree real interest rate",
                domain=[g.Reg, g.allyear],
            )
            g.g_yrfr = Parameter(
                m,
                name="G_YRFR",
                description="Seasonal fraction of the year",
                domain=[g.allreg, g.ts],
            )
            g.ts_cycle = Parameter(
                m,
                name="TS_CYCLE",
                description="Length of cycles below timeslice in days",
                domain=[g.Reg, g.ts],
            )
            g.g_offthd = Parameter(
                m,
                name="G_OFFTHD",
                description="Threshold for OFF ranges",
                domain=[g.allyear],
            )
            g.g_overlap = Parameter(
                m,
                name="G_OVERLAP",
                description="Overlap of stepped solutions (in years)",
                records=0,
            )
            g.reg_fixt = Parameter(
                m,
                name="REG_FIXT",
                domain=[g.allr],
                description="Year up to which periods are fixed",
            )
            g.reg_bdncap = Parameter(
                m,
                name="REG_BDNCAP",
                domain=[g.allr, g.ll],
                description="Year up to which VAR_NCAPs are to be fixed",
            )
            g.g_curex = Parameter(
                m,
                name="G_CUREX",
                domain=[g.cur, g.cur],
                description="Global currency conversions",
            )
            g.r_curex = Parameter(
                m,
                name="R_CUREX",
                domain=[g.allreg, g.cur, g.cur],
                description="Regional currency conversions",
            )

            # trade of commodities
            g.ire_bnd = Parameter(
                m,
                name="IRE_BND",
                domain=[g.allr, g.allyear, g.Com, g.ts, g.allreg, g.ie, g.bd],
                description="Limit on inter-reg exchange of commodity",
            )
            g.ire_flo = Parameter(
                m,
                name="IRE_FLO",
                domain=[g.allr, g.allyear, g.prc, g.Com, g.allr, g.Com, g.ts],
                description="Efficiency of exchange for inter-regional trade",
            )
            g.ire_flosum = Parameter(
                m,
                name="IRE_FLOSUM",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.ie, g.Com, g.io],
                description="Aux. consumption/emissions from inter-regional trade",
            )
            g.ire_price = Parameter(
                m,
                name="IRE_PRICE",
                domain=[g.Reg, g.allyear, g.prc, g.Com, g.ts, g.allr, g.ie, g.cur],
                description="Exogenous price of import/export",
            )
            g.ire_xbnd = Parameter(
                m,
                name="IRE_XBND",
                domain=[g.allreg, g.allyear, g.Com, g.ts, g.ie, g.bd],
                description="Limit on all (external and inter-regional) exchange of commodity",
            )
            g.ire_ccvt = Parameter(
                m,
                name="IRE_CCVT",
                domain=[g.allreg, g.Com, g.allreg, g.Com],
                description="Commodity unit conversion factor between regions",
            )
            g.ire_tscvt = Parameter(
                m,
                name="IRE_TSCVT",
                domain=[g.allreg, g.allts, g.allreg, g.allts],
                description="Identification and TS-conversion factor between regions",
            )

            # Shape and Multi
            g.shape = Parameter(
                m, name="SHAPE", description="Shaping table", domain=[g.j, g.age]
            )
            g.multi = Parameter(
                m, name="MULTI", description="Multiplier table", domain=[g.j, g.allyear]
            )

            # Regional Cost bounds
            g.reg_bndcst = Parameter(
                m,
                name="REG_BNDCST",
                domain=[g.Reg, g.allyear, g.costagg, g.cur, g.bd],
                description="Bound on regional costs by type",
            )
            g.reg_cumcst = Parameter(
                m,
                name="REG_CUMCST",
                domain=[g.Reg, g.allyear, g.allyear, g.costagg, g.cur, g.bd],
                description="Cumulative bound on regional costs",
            )

            # User Constraints
            g.uc_rhs = Parameter(
                m,
                name="UC_RHS",
                description="Constant in user constraint",
                domain=[g.ucn, g.lim],
            )
            g.uc_rhst = Parameter(
                m,
                name="UC_RHST",
                description="Constant in user constraint",
                domain=[g.ucn, g.allyear, g.lim],
            )
            g.uc_rhsr = Parameter(
                m,
                name="UC_RHSR",
                description="Constant in user constraint",
                domain=[g.allreg, g.ucn, g.lim],
            )
            g.uc_rhss = Parameter(
                m,
                name="UC_RHSS",
                description="Constant in user constraint",
                domain=[g.ucn, g.ts, g.lim],
            )
            g.uc_rhsrt = Parameter(
                m,
                name="UC_RHSRT",
                description="Constant in user constraint",
                domain=[g.allreg, g.ucn, g.allyear, g.lim],
            )
            g.uc_rhsrs = Parameter(
                m,
                name="UC_RHSRS",
                description="Constant in user constraint",
                domain=[g.allreg, g.ucn, g.ts, g.lim],
            )
            g.uc_rhsrts = Parameter(
                m,
                name="UC_RHSRTS",
                description="Constant in user constraint",
                domain=[g.allreg, g.ucn, g.allyear, g.ts, g.lim],
            )
            g.uc_rhsts = Parameter(
                m,
                name="UC_RHSTS",
                description="Constant in user constraint",
                domain=[g.ucn, g.allyear, g.ts, g.lim],
            )

            g.uc_flo = Parameter(
                m,
                name="UC_FLO",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.prc, g.Com, g.ts],
                description="Multiplier of flow variables",
            )
            g.uc_act = Parameter(
                m,
                name="UC_ACT",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.prc, g.allts],
                description="Multiplier of activity variables",
            )
            g.uc_cap = Parameter(
                m,
                name="UC_CAP",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.prc],
                description="Multiplier of capacity variables",
            )
            g.uc_ncap = Parameter(
                m,
                name="UC_NCAP",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.prc],
                description="Multiplier of VAR_NCAP variables",
            )
            g.uc_comcon = Parameter(
                m,
                name="UC_COMCON",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.Com, g.ts],
                description="Multiplier of VAR_COMCON variables",
            )
            g.uc_comprd = Parameter(
                m,
                name="UC_COMPRD",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.Com, g.ts],
                description="Multiplier of VAR_COMPRD variables",
            )
            g.uc_comnet = Parameter(
                m,
                name="UC_COMNET",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.Com, g.ts],
                description="Multiplier of VAR_COMNET variables",
            )
            g.uc_ire = Parameter(
                m,
                name="UC_IRE",
                domain=[g.ucn, g.side, g.allreg, g.allyear, g.prc, g.Com, g.ts, g.ie],
                description="Multiplier of inter-regional exchange variables",
            )
            g.uc_cumact = Parameter(
                m,
                name="UC_CUMACT",
                domain=[g.ucn, g.allreg, g.prc, g.item, g.item],
                description="Multiplier of cumulative process activity variable",
            )
            g.uc_cumflo = Parameter(
                m,
                name="UC_CUMFLO",
                domain=[g.ucn, g.allreg, g.prc, g.Com, g.item, g.item],
                description="Multiplier of cumulative process flow variable",
            )
            g.uc_cumcom = Parameter(
                m,
                name="UC_CUMCOM",
                domain=[g.ucn, g.allreg, g.comvar, g.Com, g.item, g.item],
                description="Multiplier of cumulative commodity variable",
            )
            g.uc_ucn = Parameter(
                m,
                name="UC_UCN",
                domain=[g.ucn, g.side, g.allr, g.allyear, g.ucn],
                description="Multiplier of user constraint variable",
            )
            g.uc_time = Parameter(
                m,
                name="UC_TIME",
                domain=[g.ucn, g.allr, g.allyear],
                description="Multiplier of time in model periods (years)",
            )

        def extensions_and_system_scalars() -> None:
            """Extensions & System scalars"""

            #  Damage input parameters
            g.dam_cost = Parameter(
                m,
                name="DAM_COST",
                description="Marginal damage cost of emissions",
                domain=[g.Reg, g.allyear, g.Com, g.cur],
            )
            g.dam_bqty = Parameter(
                m,
                name="DAM_BQTY",
                description="Base quantity of emissions",
                domain=[g.Reg, g.Com],
            )
            g.dam_elast = Parameter(
                m,
                name="DAM_ELAST",
                description="Elasticity of damage cost",
                domain=[g.Reg, g.Com, g.lim],
            )
            g.dam_step = Parameter(
                m,
                name="DAM_STEP",
                description="Step number for emissions up to base",
                domain=[g.Reg, g.Com, g.lim],
            )
            g.dam_voc = Parameter(
                m,
                name="DAM_VOC",
                description="Variance of emissions",
                domain=[g.Reg, g.Com, g.lim],
            )
            # Experimental parameters
            g.dam_tqty = Parameter(
                m,
                name="DAM_TQTY",
                description="Base quantity of emissions by year",
                domain=[g.Reg, g.allyear, g.Com],
            )
            g.dam_tvoc = Parameter(
                m,
                name="DAM_TVOC",
                description="Variance of emissions by year",
                domain=[g.Reg, g.allyear, g.Com, g.lim],
            )
            g.dam_coef = Parameter(
                m,
                name="DAM_COEF",
                description="Coefficient from commodity to damage",
                domain=[g.Reg, g.allyear, g.Com, g.s],
            )
            # Parameters used in report routine
            g.rpt_opt = Parameter(
                m, name="RPT_OPT", description="Reporting options", domain=[g.item, g.j]
            )
            g.cst_dam = Parameter(
                m,
                name="CST_DAM",
                description="Damage costs",
                domain=[g.Reg, g.t, g.Com],
            )
            g.cm_result = Parameter(
                m,
                name="CM_RESULT",
                description="Climate module results",
                domain=[g.item, g.item, g.allyear],
            )
            g.cm_maxc_m = Parameter(
                m,
                name="CM_MAXC_M",
                description="Shadow price of climate constraint",
                domain=[g.item, g.allyear],
            )
            g.tm_result = Parameter(
                m,
                name="TM_RESULT",
                description="MACRO results",
                domain=[g.item, g.r, g.allyear],
            )

            # Scalars
            g.miyr_v1 = Parameter(m, records=0, name="MIYR_V1")
            g.miyr_vl = Parameter(m, records=0, name="MIYR_VL")
            g.pyr_v1 = Parameter(m, records=0, name="PYR_V1")
            g.my_f = Parameter(m, records=0, name="MY_F")
            g.f = Parameter(m, records=0, name="F")
            g.z = Parameter(m, records=0, name="Z")
            g.cnt = Parameter(m, records=0, name="CNT")
            g.dfunc = Parameter(m, records=0, name="DFUNC")
            g.done = Parameter(m, records=0, name="DONE")
            g.ifq = Parameter(m, records=1, name="IFQ")
            # * maximum NCAP_ILED+NCAP_TLIFE+NCAP_DLAG+NCAP_DLIFE+NCAP_DELIF
            g.dur_max = Parameter(m, records=0, name="DUR_MAX")
            # * first and last given data value to be extrapolated
            g.first_val = Parameter(m, records=0, name="FIRST_VAL")
            g.last_val = Parameter(m, records=0, name="LAST_VAL")
            g.my_fyear = Parameter(m, records=0, name="MY_FYEAR")

            # * Placeholder for interpolation control option
            self.env.set_global("dflbl", "0")
            dflbl = self.env.dflbl
            self.tc.enqueue(self.assign_yearval, dflbl=dflbl)

            g.Lastll = Set(m, name="LASTLL", domain=[g.ll], records=self.env.dflbl)

            self.tc.enqueue(self.assign_z)

            # Interpolation defaults
            g.intdefault = Set(m, name="INT_DEFAULT", description="", domain=["*"])
            g.uncd1 = Set(m, name="UNCD1", domain=["*"])
            g.ie_default = Parameter(m, name="IE_DEFAULT", description="", domain=["*"])

        def initializations_for_blending() -> None:
            """*GG* V07_2 Initializations for BLENDing"""
            # * user provided Sets & Scalars
            g.Ble = Set(m, name="BLE", description="", domain=[g.Com])
            g.Opr = Set(m, name="OPR", description="", domain=[g.Com])
            g.spe = Set(m, name="SPE", description="", domain=["*"])
            g.Ref = Set(m, name="REF", description="", domain=[g.r, g.prc])
            g.refunit = Parameter(m, name="REFUNIT", description="", domain=[g.r])

            # * internal Sets
            g.cvt = Set(
                m, records=["DENS", "WCV", "VCV", "SLF"], name="CVT", description=""
            )

            # * user provided Parameters
            g.convert = Parameter(
                m, name="CONVERT", description="", domain=[g.Opr, g.cvt]
            )
            g.bl_start = Parameter(
                m, name="BL_START", description="", domain=[g.r, g.Com, g.spe]
            )
            g.bl_unit = Parameter(
                m, name="BL_UNIT", description="", domain=[g.r, g.Com, g.spe]
            )
            g.bl_type = Parameter(
                m, name="BL_TYPE", description="", domain=[g.r, g.Com, g.spe]
            )
            g.bl_spec = Parameter(
                m, name="BL_SPEC", description="", domain=[g.r, g.Com, g.spe]
            )
            # g.tbl_spec = Parameter(
            #     m, name="TBL_SPEC", description="", domain=[g.Com, g.spe, g.year]
            # )
            g.bl_com = Parameter(
                m, name="BL_COM", description="", domain=[g.r, g.Com, g.Opr, g.spe]
            )
            # g.tbl_com = Parameter(
            #     m, name="TBL_COM", description="", domain=[g.Com, g.spe, g.Opr, g.year]
            # )
            g.bl_inp = Parameter(
                m, name="BL_INP", description="", domain=[g.r, g.Com, g.Com]
            )
            # g.tbl_inp = Parameter(
            #     m, name="TBL_INP", description="", domain=[g.Com, g.spe, g.com, g.year]
            # )
            g.bl_varomc = Parameter(
                m, name="BL_VAROMC", description="", domain=[g.r, g.Com, g.cur]
            )
            # g.tbl_varom = Parameter(
            #     m, name="TBL_VAROM", description="", domain=[g.Com, g.spe, g.year]
            # )
            g.bl_delivc = Parameter(
                m, name="BL_DELIVC", description="", domain=[g.r, g.Com, g.Com, g.cur]
            )
            # g.tbl_deliv = Parameter(
            #     m, name="TBL_DELIV", description="", domain=[g.Com, g.spe, g.com, g.year]
            # )
            g.env_bl = Parameter(
                m,
                name="ENV_BL",
                description="",
                domain=[g.r, g.Com, g.Com, g.Opr, g.year],
            )
            g.peakda_bl = Parameter(
                m, name="PEAKDA_BL", description="", domain=[g.r, g.Com, g.year]
            )

            # * internal Parameters
            g.ru_cvt = Parameter(
                m, name="RU_CVT", description="", domain=[g.r, g.Ble, g.spe, g.Opr]
            )
            g.ru_feq = Parameter(
                m, name="RU_FEQ", description="", domain=[g.r, g.Com, g.year]
            )
            g.obj_blndv = Parameter(
                m,
                name="OBJ_BLNDV",
                description="annual variable costs for blending",
                domain=[g.r, g.year, g.c, g.c, g.cur],
            )

        def control_section() -> None:
            """CONTROL section"""
            self.env.set_global("gdxpath", "")
            # TODO: $ IFI EXIST gamssave\nul $SETGLOBAL GDXPATH 'gamssave/'
            self.env.set_global("sysprefix", "")
            self.env.set_global("prf", "FILE=1")

            # Alternative objective controls
            g.altobj = Parameter(container=m, name="ALTOBJ", records=1)
            self.tc.enqueue(self.assign_alternative_objective, objective=self.env.obj)

            if self.env.macro.upper() == "YES":
                self.tc.enqueue(self.check_macro)
            if self.env.validate.upper() == "YES":
                self.tc.enqueue(self.validate)

            # $SETGLOBAL CTST
            self.env.set_global("ctst", "")
            if self.env.obj.upper() == "MOD":
                self.env.set_global("oblong", "YES")
            elif self.env.obj.upper() == "ALT":
                self.env.set_global("ctst", "**EPS")

            if self.env.oblong.upper() == "YES":
                self.env.set_global("ctst", "**0")

            if self.env.obj.upper() == "LIN":
                self.env.set_global("ctst", "**EPS")

            if self.env.oblong.upper() == "YES" and self.env.obj.upper() == "ALT":
                self.env.set_global("varcost", "LIN")
                self.tc.enqueue(self.assign_alternative_objective_long)

            # Stochastic extension
            if self.env.sensis.upper() == "YES":
                self.env.set_local("stages", "yes")
            if self.env.spines.upper() == "YES":
                self.env.set_local("stages", "YES")
            if self.env.stages.upper() == "YES":
                self.include(InitmtyStc(self.tc, self.env))

            # * Stepped extensions etc.
            itemadd_records = [self.env.fixboh, self.env.timestep, self.env.spoint]
            self.add_records_to_universe_item(records=itemadd_records)

            self.env.set_global("rpoint", "NO")

            if self.env.is_set("spoint"):
                self.tc.enqueue(
                    self.catch_invalid_spoint_control, spoint=self.env.spoint
                )

            if self.env.is_set("timestep"):
                self.tc.enqueue(
                    self.catch_invalid_timestep_control, timestep=self.env.timestep
                )

            if self.env.is_set("fixboh"):
                self.tc.enqueue(
                    self.catch_invalid_fixboh_control, fixboh=self.env.fixboh
                )

            if self.env.is_set("fixboh"):
                self.env.set_global("stepped", "-")
            if self.env.is_set("timestep"):
                self.env.set_global("stepped", "+")
            if self.env.is_set("stepped"):
                self.env.set_global("var_uc", "YES")

        def other_extensions() -> None:
            """Other extensions to TIMES code"""
            # Auto-activation of discrete capacity extensions
            if self.env.dscauto == "YES":
                self.env.set_global("dsc", "YES")
            if self.env.pgprim == "ACT":
                self.env.set_global("retire", "YES")
                self.env.set_global("dscauto", "Yes")
            # $IFI %DSC%==YES    $KILL RCAP_BLK
            if self.env.dsc == "YES":
                self.tc.add_gams_code(module=self, phase="init", code="$KILL RCAP_BLK")

            # Initialize list of standard extensions to be loaded
            self.env.set_scoped("vda", "YES")

            # Load all extension declarations
            def collect_active_extensions() -> None:
                """Collect active extensions based on various env variables
                will be collected and passed to MainExtMod"""
                self.env.set_global("extend", "")

                # Add recognized extensions if defined
                if self.env.ecb.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} ECB".strip())
                    # There is no initmty.ecb
                    raise KeyError("No module initmty ECB")
                if self.env.macro.upper() in ["CSA", "MSA"]:
                    self.env.set_global("extend", f"{self.env.extend} MSA".strip())
                elif self.env.macro.upper() == "MLF":
                    self.env.set_global("extend", f"{self.env.extend} MLF".strip())

                if self.env.etl.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} ETL".strip())

                if self.env.cli.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} CLI".strip())

                if self.env.dsc.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} DSC".strip())

                if self.env.vda.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} VDA".strip())

                if self.env.abs.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} ABS".strip())

                if self.env.mca.upper() == "YES":
                    self.env.set_global("extend", f"{self.env.extend} MCA".strip())
                    # There is no initmty.mca
                    raise KeyError("No module initmty MCA")

                # Finally, add args %1...%6 to list of extensions:
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

            # $BATINCLUDE main_ext.mod initmty %EXTEND%
            extensions = {
                "ABS": InitmtyAbs,
                "CLI": InitmtyCli,
                "DSC": InitmtyDsc,
                "ETL": InitmtyEtl,
                "IER": InitmtyIer,
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

        def call_macro_initmty_tm() -> None:
            if not self.env.is_set("macro"):
                self.env.set_global("macro", "N")
            if self.env.macro == "YES":
                self.include(InitmtyTm(tc=self.tc, env=self.env))
            if self.env.datagdxi == "YES":
                self.env.set_global("datagdx", "YES")
            if (
                self.env.datagdxi.upper() == "YES"
                and self.env.intext_only.upper() == "YES"
            ):
                self.env.set_scoped("datagdx", "NO")

            # Load data from GDX if DATAGDX set and %RUN_NAME%~DATA exists
            if not self.env.is_set("datagdx"):
                return
            if self.env.g2x6 != "YES":
                return
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
                self.env.set_scoped("tmp", f"{self.env.run_name}~data")

            # $ IFI %DATAGDXI%%DATAGDX%==YESNO
            # $ IF EXIST _dd_.gdx $SET TMP _dd_
            if (
                self.env.datagdxi.upper() == "YES"
                and self.env.datagdx.upper() == "NO"
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
                raise EscapeStack(f"Calling $stop in {self.module_name}.")

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
        self.tc.yearval[dflbl] = 0

    def assign_z(self) -> None:
        g = self.tc

        g.z[...] = Sum(g.Lastll[g.ll], Ord(g.ll))  # type: ignore
        if g.z.toValue() != g.ll.number_records:
            raise Exception("Fatal")

    def assign_alternative_objective(self, objective: str) -> None:
        # Alternative objective controls
        alt_obj = self.tc.altobj
        if objective == "STD":
            alt_obj[...] = 0
        elif objective == "ALT":
            alt_obj[...] = 2
        elif objective == "LIN":
            alt_obj[...] = 3

    def check_macro(self) -> None:
        altobj = self.tc.altobj.toValue()
        assert altobj is not None
        if altobj > 1:
            raise Exception("MACRO Cannot be used with Alternative Objective")

    def validate(self) -> None:
        altobj = self.tc.altobj.toValue()
        assert altobj is not None
        if altobj > 1:
            raise Exception("VALIDATE Cancels Alternative Objective")
        self.tc.altobj[...] = 0

    def assign_alternative_objective_long(self) -> None:
        self.tc.altobj[...] = -2

    def catch_invalid_spoint_control(self, spoint: str) -> None:
        if not self.tc.j[spoint] and not spoint == "YES":
            raise KeyError(f"Invalid Control: SPOINT = {spoint}")

    def catch_invalid_timestep_control(self, timestep: int) -> None:
        if len(self.tc.age[timestep]) == 0:
            raise KeyError(f"Invalid Control: TIMESTEP = {timestep}")

    def catch_invalid_fixboh_control(self, fixboh: str) -> None:
        if not self.tc.allyear[fixboh]:
            raise KeyError(f"Invalid Control: FIXBOH = {fixboh}")
