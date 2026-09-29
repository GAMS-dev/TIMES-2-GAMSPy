# initsys_mod.py
# *==========================================================================================*
# * INITSYS.MOD has all the fixed system declarations for ETSAP TIMES                        *
# *==========================================================================================*
# *  Copyright (C) 2000-2025 IEA Energy Technology Systems Analysis Programme (IEA-ETSAP).
# *  This software (ETSAP TIMES) is open source: you can redistribute it and/or modify it
# *  under the terms of the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *  For further information, visit: <https://www.gnu.org/licenses/gpl-3.0.html>.
# *
# *  This software is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# *  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# *===========================================================================================

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Ord, Parameter, Set, UniverseAlias

from core.base_class import GamsClass
from core.globals_def import Globals
from core.maplists_def import Maplists
from core.units_def import Units
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import GamsPhase, TimesModelClass

logger = logging.getLogger(__name__)


class InitsysMod(GamsClass):
    """Translation unit for initsys.mod."""

    # Instance attributes
    module_name: str = "initsys_mod"
    gams_source: str = "inisys.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase: GamsPhase = "init"
        # Easy access gamspy.Container
        m = self.tc.container
        g = self.tc

        self.env.set_scoped("tmp", "restart")
        # TODO: $ IF %SYSTEM.LICENSELEVEL%==2 $SET TMP Runtime
        # TODO: $ IF SET RunTimes $TITLE %SYSTEM.TITLE% -- %TMP% (v%RunTimes%)

        # $ PHANTOM EMPTY
        g.phantom = Set(m, "PHANTOM", records=["EMPTY"])

        self.tc.add_gams_code(
            module=self,
            phase=phase,
            code="""
$ PHANTOM EMPTY
$ ONEMPTY
""",
        )

        g.item = UniverseAlias(m, name="ITEM")

        # moved to UserConfig
        # # $IF NOT SET BOTIME $SETGLOBAL BOTIME 1850
        # if not self.env.is_set("botime"):
        #     self.env.set_global("botime", 1850)

        # moved to UserConfig
        # # $IF NOT SET EOTIME $SETGLOBAL EOTIME 2200
        # if not self.env.is_set("eotime"):
        #     self.env.set_global("eotime", 2200)

        eotime = self.env.eotime
        botime = self.env.botime

        # $IF NOT %SHELL%==ANSWER
        # $IF SET MAXSOW SET ITEM /BOH, 1*%EOTIME%/;
        if (
            self.env.is_set("shell")
            and self.env.shell != "ANSWER"
            and self.env.is_set("maxsow")
        ):
            # Expand the universe alias item
            item_records = ["BOH"] + [str(i) for i in range(1, eotime + 1)]
            self.add_records_to_universe_item(records=item_records)

        allyear_records = list(range(botime, eotime + 1))
        g.bohyear = Set(
            container=m,
            name="BOHYEAR",
            description="BOH + years",
            records=["BOH", *allyear_records],
        )
        g.allyear = Set(
            container=m,
            name="ALLYEAR",
            description="All Years",
            records=allyear_records,
        )
        g.yearval = Parameter(
            m, name="YEARVAL", description="Value of each year", domain=[g.allyear]
        )

        # catch botime now and store with queue
        self.tc.enqueue(self.assign_yearval, botime=botime)

        eoh_records = [*g.bohyear.toList(), "EOH"]
        g.eohyear = Set(
            m, name="EOHYEAR", description="'BOH/EOH' + years", records=eoh_records
        )
        g.beoh = Parameter(
            m,
            name="BEOH",
            description="BOH / EOH offset",
            domain=["*"],
            records=[("BOH", "+1"), ("EOH", -1)],
        )
        g.Periodyr = Set(
            m,
            name="PERIODYR",
            description="All years in each period",
            domain=[g.allyear, g.allyear],
        )
        expand_set(g.allts, ["ANNUAL"])

        g.Annual = Set(
            m,
            name="ANNUAL",
            domain=[g.allts],
            description="Annual identifier",
            records=["ANNUAL"],
        )
        g.tslvl = Set(
            m,
            name="TSLVL",
            description="Timeslice levels",
            records=["ANNUAL", "SEASON", "WEEKLY", "DAYNITE"],
        )
        g.tslvlnum = Parameter(
            m,
            name="TSLVLNUM",
            domain=[g.tslvl],
            description="Timeslice level values",
            records=[
                ("ANNUAL", "  1"),
                ("SEASON", "  2"),
                ("WEEKLY", "  3"),
                ("DAYNITE", " 4"),
            ],
        )

        # g.Season = Set(m, name="SEASON", description="Seasons", domain=[g.Reg, g.allts])
        # g.Week = Set(
        #     m, name="WEEK", description="Week Sub-divisions ", domain=[g.Reg, g.allts]
        # )
        # g.Daynite = Set(
        #     m,
        #     name="DAYNITE",
        #     description="Daily Sub-divisions",
        #     domain=[g.Reg, g.allts],
        # )

        g.year = Alias(m, name="YEAR", alias_with=g.allyear)
        g.ll = Alias(m, name="LL", alias_with=g.allyear)

        # topology
        g.impexp = Set(
            m, name="IMPEXP", description="Imports/Exports", records=["IMP", "EXP"]
        )
        g.imp = Set(
            m,
            name="IMP",
            description="Imports",
            records=["IMP"],
        )
        g.xpt = Set(m, name="XPT", description="Exports", records=["EXP"])
        g.inout = Set(
            m,
            name="IN_OUT",
            description="Input/Output",
            records=["IN", "OUT"],
        )

        g.ie = Alias(m, name="IE", alias_with=g.impexp)
        g.io = Alias(m, name="IO", alias_with=g.inout)

        # limits
        g.lim = Set(
            m,
            name="LIM",
            description="Limit Types",
            records=["LO", "FX", "UP", "N"],
        )
        g.BndType = Set(
            m,
            name="BND_TYPE",
            domain=[g.lim],
            description="Bound Types",
            records=["LO", "FX", "UP"],
        )

        g.lA = Alias(m, name="L", alias_with=g.lim)
        g.limtype = Alias(m, name="LIM_TYPE", alias_with=g.lim)
        g.bd = Alias(m, name="BD", alias_with=g.BndType)

        g.upt = Set(
            m,
            name="UPT",
            description="Start-up types",
            records=["COLD", "WARM", "HOT"],
        )

        # Numbered sets
        expand_set(symbol=g.allyear, elements=["0"])

        g.age = Set(
            m,
            name="AGE",
            description="Age for SHAPEing",
            records=range(1, 201),
        )
        g.j = Set(
            m,
            name="J",
            description="Supply/demand steps 1*COM_STEP and SHAPE/MULTI",
            records=range(1, 1000),
        )

        g.jj = Alias(m, name="JJ", alias_with=g.j)

        # Master Set declarations
        g.allreg = Set(
            m, name="ALL_REG", description="External + Internal Regions", domain=["*"]
        )
        g.Reg = Set(m, name="REG", description="Region", domain=[g.allreg])
        g.allr = Alias(m, name="ALL_R", alias_with=g.allreg)
        g.r = Alias(m, name="R", alias_with=g.Reg)

        g.comgrp = Set(
            m,
            name="COM_GRP",
            description="Commodities & Groups",
            records=[
                ("DEM", "Demands"),
                ("NRG", "Energy"),
                ("MAT", "Material"),
                ("ENV", "Environmental Indicators"),
                ("FIN", "Financial"),
            ],
        )

        g.cg = Alias(m, name="CG", alias_with=g.comgrp)
        g.cg1 = Alias(m, name="CG1", alias_with=g.comgrp)
        g.cg2 = Alias(m, name="CG2", alias_with=g.comgrp)

        g.Com = Set(m, name="COM", description="Commodities", domain=[g.comgrp])

        g.c = Alias(m, name="C", alias_with=g.Com)
        g.com1 = Alias(m, name="COM1", alias_with=g.Com)
        g.com2 = Alias(m, name="COM2", alias_with=g.Com)

        g.prc = Set(m, name="PRC", description="Processes", domain=["*"])
        g.p = Alias(m, name="P", alias_with=g.prc)

        g.cur = Set(m, name="CUR", description="Currencies = c$", domain=["*"])
        g.curr = Alias(m, name="CURR", alias_with=g.cur)

        # Stochastics
        self.env.set_global("maxsow", "96")
        g.allsow = Set(
            m,
            name="ALLSOW",
            description="State-of-the-World",
            records=range(1, int(self.env.maxsow) + 1),
        )
        g.Sow = Set(m, name="SOW", description="State-of-the-World", domain=[g.allsow])
        g.w = Alias(m, name="W", alias_with=g.Sow)

        # *-------------------------------------------------------------------------------
        # * UC facility - fixed sets and controls for user-constraints
        # *-------------------------------------------------------------------------------

        g.side = Set(
            m,
            name="SIDE",
            description="LHS and RHS of an equation",
            records=["LHS", "RHS"],
        )
        g.uc_sign = Parameter(
            m,
            name="UC_SIGN",
            domain=[g.side],
            description="Sign of LHS and RHS expression",
            records=[("LHS", " 1"), ("RHS", "-1")],
        )
        g.comvar = Set(
            m,
            name="COM_VAR",
            records=["NET", "PRD"],
        )
        g.CovMap = Set(
            m,
            name="COV_MAP",
            domain=["*", "*"],
            records=[("NET", "COMNET"), ("PRD", "COMPRD")],
        )

        # List of parameters that can be used in user-constraints
        uc_names = [
            "COST",
            "DELIV",
            "TAX",
            "SUB",
            "EFF",
            "NET",
            "N",
            "GROWTH",
            "PERIOD",
            "PERDISC",
            "BUILDUP",
            "CUMSUM",
            "CUM+",
            "SYNC",
            "YES",
            "CAPACT",
            "CAPFLO",
            "NEWFLO",
            "ONLINE",
            "ANNUL",
            "INVCOST",
            "INVTAX",
            "INVSUB",
            "FLO_COST",
            "FLO_DELIV",
            "FLO_SUB",
            "FLO_TAX",
            "NCAP_COST",
            "NCAP_ITAX",
            "NCAP_ISUB",
        ]
        g.ucname = Set(
            m,
            name="UC_NAME",
            description="Allowed parameters in user-constraints",
            records=uc_names,
        )

        g.UcCost = Set(
            m,
            name="UC_COST",
            domain=[g.ucname],
            description="UC cost attributes",
            records=["COST", "DELIV", "TAX", "SUB", "ANNUL"],
        )
        g.UcMapcost = Set(
            m,
            name="UC_MAPCOST",
            domain=[g.UcCost, g.ucname],
            description="Compatibility map for cost attributes",
            records=[
                ("COST", "FLO_COST"),
                ("COST", "NCAP_COST"),
                ("DELIV", "FLO_DELIV"),
                ("ANNUL", "INVCOST"),
                ("ANNUL", "INVTAX"),
                ("ANNUL", "INVSUB"),
                ("TAX", "FLO_TAX"),
                ("TAX", "NCAP_ITAX"),
                ("SUB", "FLO_SUB"),
                ("SUB", "NCAP_ISUB"),
            ],
        )

        g.UcAnnul = Set(
            m,
            name="UC_ANNUL",
            domain=[g.ucname],
            records=["INVCOST", "INVTAX", "INVSUB"],
        )
        g.UcDynt = Set(
            m,
            name="UC_DYNT",
            domain=[g.ucname],
            records=["N", "CUMSUM", "CUM+", "SYNC"],
        )
        g.ucnumber = Set(
            m,
            name="UC_NUMBER",
            description="Determines way of handling REG, T and TS",
            records=["SEVERAL", "SUCC", "EACH", "DYNAMIC"],
        )
        g.UcPerds = Set(
            m,
            name="UC_PERDS",
            domain=[g.ucname],
            records=["PERIOD", "NEWFLO"],
        )
        g.UcNewflo = Set(m, name="UC_NEWFLO", domain=[g.ucname], records=["NEWFLO"])
        g.ucgrptype = Set(
            m,
            name="UC_GRPTYPE",
            description="Type of components within UC_GRP",
            records=[
                "ACT",
                "FLO",
                "IRE",
                "CAP",
                "NCAP",
                "COMNET",
                "COMPRD",
                "COMCON",
                "UCN",
            ],
        )
        g.costagg = Set(
            m,
            name="COSTAGG",
            description="Types of cost aggregations",
            records=[
                "INV",
                "INVTAX",
                "INVSUB",
                "FOM",
                "FOMTAX",
                "FOMSUB",
                "COMTAX",
                "COMSUB",
                "FLOTAX",
                "FLOSUB",
                "INVTAXSUB",
                "INVALL",
                "FOMTAXSUB",
                "FOMALL",
                "FIX",
                "FIXTAX",
                "FIXSUB",
                "FIXTAXSUB",
                "FIXALL",
                "COMTAXSUB",
                "FLOTAXSUB",
                "ALLTAX",
                "ALLSUB",
                "ALLTAXSUB",
            ],
        )

        g.costcat = Alias(m, name="COSTCAT", alias_with=g.costagg)
        g.costype = Alias(m, name="COSTYPE", alias_with=g.UcCost)

        # *-------------------------------------------------------------------------------
        # * control sets
        # *  - expected in *.RUN file
        # *  - throw switch other way in *.RUN to change
        # *-------------------------------------------------------------------------------
        # * user should provide name in *.RUN
        # self.env.set_scoped("model_name", "TIMES") # moved to UserConfig
        # self.env.set_scoped("run_name", "TEST")  # moved to UserConfig
        # * control of whether all 0 lines are dumped in *.PUT files; user provides 0 to NOT print lines with all 0s (or empty)
        g.dump0 = Parameter(m, name="DUMP0", records=1)
        g.optfileid = Parameter(m, name="OPTFILEID", records=1)

        # * user set to 'YES' to activate
        # self.env.set_scoped("debug", "NO") # moved to UserConfig
        # self.env.set_scoped("dumpsol", "NO") # moved to UserConfig
        # self.env.set_scoped("solans", "NO") # moved to UserConfig

        # * user set to 'NO' to not abort when error condition fails
        # self.env.set_scoped("err_abort", "YES") # moved to UserConfig
        # * user sets to 'WWW' to activate
        # self.env.set_scoped("gams_cgi", "NO") # moved to UserConfig
        # * user sets to 'NO' if only want to compile
        # self.env.set_scoped("solve_now", "YES") # moved to UserConfig

        # get list of default units
        self.include(Units(tc=self.tc, env=self.env))

        # get list of default mapping group lists
        self.include(Maplists(tc=self.tc, env=self.env))

        # # get default global scalars and parameters
        self.include(Globals(tc=self.tc, env=self.env))

    def assign_yearval(self, botime: int) -> None:
        g = self.tc
        g.yearval[g.allyear] = botime + Ord(g.allyear) - 1
