# initmty_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * INITMTY.cli - Extension for Climate Module
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Parameter, Set, Smax
from gamspy.math import log

from core.base_class import GamsClass
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyCli(GamsClass):
    """Translation unit for initmty.cli."""

    # Instance attributes
    module_name: str = "initmty_cli"
    gams_source: str = "initmty.cli"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, arg1: str, arg2: str
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container
        self.env.set_global("cli", "YES")

        g.attlvl = Parameter(m, name="ATTLVL", records=0)
        g.vallvl = Parameter(m, name="VALLVL", records=0)
        g.cm_calib = Parameter(m, name="CM_CALIB", records=0)

        # -----------------------------------------------------------------------------
        # Set for calibration quantities
        records = [
            ("CO2-ATM", "Mass of CO2 in the atmosphere (in GtC)"),
            ("CO2-UP", "Mass of CO2 in the upper ocean layer (in GtC)"),
            ("CO2-LO", "Mass of CO2 in the lower ocean layer (in GtC)"),
            ("CH4-ATM", ""),
            ("CH4-UP", ""),
            ("CH4-LO", "Mass of CH4 in the atmosphere"),
            ("N2O-ATM", ""),
            ("N2O-UP", ""),
            ("N2O-LO", "Mass of N2O in the atmosphere"),
            ("FORCING", "Radiative Forcing"),
            ("FORC-CO2", ""),
            ("FORC-CH4", ""),
            ("FORC-N2O", ""),
            ("FORC-FGS", ""),
            ("FORC-KYO", ""),
            ("CO2-GTC", ""),
            ("CH4-MT", ""),
            ("N2O-MT", ""),
            ("FGS-MT", ""),
            ("CO2-PPM", ""),
            ("CH4-PPB", ""),
            ("N2O-PPB", ""),
            ("FGS-CON", ""),
            ("DELTA-ATM", "Temperature change in the surface"),
            ("DELTA-LO", "Temperature change in the deep ocean layer"),
        ]

        g.cmpredef = Set(
            m,
            name="CM_PREDEF",
            description="Historical CO2 concentration and incremental forcing quantities",
            records=records,
        )

        expand_set(g.comgrp, records)
        g.CmHists = Set(m, name="CM_HISTS", domain=[g.cg], records=records)
        g.CmVar = Alias(m, name="CM_VAR", alias_with=g.CmHists)
        g.cmitem = Alias(m, name="CM_ITEM", alias_with=g.cg)
        g.CmOfor = Set(
            m,
            name="CM_OFOR",
            domain=[g.cmitem],
            records=["FORC-CH4", "FORC-N2O", "FORC-FGS"],
        )
        expand_set(g.ucgrptype, ["CLI"])
        g.cmq = Set(
            m,
            name="CM_Q",
            description="Reservoir Qualifier",
            records=[
                *g.lim.toList(),
                "ATM",
                "CM-EMIS",
                "CM-PPX",
                "CM-FORC",
                "CM-DT",
                "CM-ATM",
                "CM-LO",
                "CM-UP",
                "LIFE",
            ],
        )
        # Mapping and conversion parameter for total CO2 emissions
        g.cm_co2gtc = Parameter(
            m,
            name="CM_CO2GTC",
            domain=[g.Reg, g.c],
            description="Conversion factors from CO2 commodities to GtC",
        )
        g.cm_ghgmap = Parameter(
            m,
            name="CM_GHGMAP",
            domain=[g.r, g.c, g.cg],
            description="Conversion factors from regional GHG commodities to CLI",
        )
        g.cm_ppm = Parameter(
            m,
            name="CM_PPM",
            domain=[g.cmitem],
            description="Conversion factors between Gt/Mt and ppm/ppb",
            records=[("CO2-GTC", 2.13), ("CH4-MT", 2.84), ("N2O-MT", 7.81)],
        )

        # Climate module time-dependent parameters
        g.cm_history = Parameter(
            m,
            name="CM_HISTORY",
            domain=[g.allyear, g.cmitem],
            description="Calibration values for CO2 and forcing",
        )
        g.cm_stats = Parameter(
            m,
            name="CM_STATS",
            domain=[g.cmitem, g.allyear, g.cmq],
            description="Calibration values for CO2 and forcing",
        )
        g.cm_exoforc = Parameter(
            m,
            name="CM_EXOFORC",
            domain=[g.allyear],
            description="Radiative forcing from exogenous sources",
        )
        g.cm_maxco2c = Parameter(
            m,
            name="CM_MAXCO2C",
            domain=[g.allyear],
            description="Maximum allowable atmospheric CO2 concentration",
        )
        g.cm_maxc = Parameter(
            m,
            name="CM_MAXC",
            domain=[g.allyear, g.item],
            description="Maximum level of climate variable",
        )
        g.cm_decay = Parameter(
            m,
            name="CM_DECAY",
            domain=[g.cmitem, g.cmq],
            description="Annual decay of concentration",
        )
        g.cm_couple = Parameter(
            m,
            name="CM_COUPLE",
            domain=[g.cmitem, g.year, g.cmitem, g.cmq],
            description="Coupled impact on concentration",
        )
        g.cm_linfor = Parameter(
            m,
            name="CM_LINFOR",
            domain=[g.allyear, g.cmitem, g.lim],
            description="Linearized forcing function",
        )
        g.uc_cli = Parameter(
            m,
            name="UC_CLI",
            domain=[g.ucn, g.side, g.Reg, g.allyear, g.cmitem],
            description="Climate variable",
        )

        #  Reporting parameters
        g.cm_dt_forc = Parameter(
            m, name="CM_DT_FORC", domain=[g.allyear], description="Delta forcing"
        )
        g.cm_maxc_m = Parameter(
            m,
            name="CM_MAXC_M",
            domain=[g.item, g.allyear],
            description="Marginals of max constraints",
        )
        g.cm_sresult = Parameter(
            m,
            name="CM_SRESULT",
            domain=[g.allsow, g.item, g.item, g.allyear],
            description="Climate Module basic results",
        )
        g.cm_smaxc_m = Parameter(
            m,
            name="CM_SMAXC_M",
            domain=[g.allsow, g.item, g.allyear],
            description="Marginals for max constraints",
        )

        # Internal sets for reservoirs
        g.cmstcc = Set(m, name="CM_STCC", records=["CS", "SIGMA1"])
        g.CmBox = Set(
            m,
            name="CM_BOX",
            domain=[g.cmq],
            description="Reservoir buckets",
            records=["ATM", "UP", "LO", "N"],
        )
        g.CmEmis = Set(m, name="CM_EMIS", domain=[g.cmitem], records=["CO2-GTC"])
        g.CmKind = Set(m, name="CM_KIND", domain=[g.cmitem], records=["CO2-GTC"])
        g.CmTkind = Set(m, name="CM_TKIND", domain=[g.cmitem])
        g.CmConc = Set(
            m, name="CM_CONC", domain=[g.cmitem, g.CmBox], records=[("CO2-GTC", "ATM")]
        )
        g.CmAtmap = Set(
            m,
            name="CM_ATMAP",
            domain=[g.cmitem, g.cmitem],
            description="Atmospheric reservoir buckets",
            records=[
                ("CO2-GTC", "CO2-PPM"),
                ("CH4-MT", "CH4-PPB"),
                ("N2O-MT", "N2O-PPB"),
                ("FGS-MT", "FGS-CON"),
                ("FORCING", "DELTA-ATM"),
            ],
        )
        g.CmBuck = Alias(m, name="CM_BUCK", alias_with=g.CmBox)
        g.CmBoxmap = Set(
            m,
            name="CM_BOXMAP",
            domain=[g.cmitem, g.cmitem, g.CmBox],
            records=[
                ("CO2-GTC", "CO2-ATM", "ATM"),
                ("CO2-GTC", "CO2-UP", "UP"),
                ("CO2-GTC", "CO2-LO", "LO"),
                ("CH4-MT", "CH4-ATM", "ATM"),
                ("CH4-MT", "CH4-UP", "UP"),
                ("N2O-MT", "N2O-ATM", "ATM"),
                ("N2O-MT", "N2O-UP", "UP"),
                ("FORCING", "DELTA-ATM", "ATM"),
                ("FORCING", "DELTA-LO", "LO"),
            ],
        )
        g.Pret = Set(m, name="PRET", domain=[g.t, g.t])
        g.Superyr = Set(
            m,
            name="SUPERYR",
            domain=[g.t, g.allyear],
            description="SUpremum PERiod YeaR",
        )
        g.CmForcmap = Set(
            m,
            name="CM_FORCMAP",
            domain=[g.cmitem, g.cmitem],
            records=[
                ("FORCING", "FORC-FGS"),
                ("FORC-KYO", "FORC-FGS"),
                ("FORC-CO2", "CO2-GTC"),
                ("FORC-CH4", "CH4-MT"),
                ("FORC-N2O", "N2O-MT"),
                ("FORC-FGS", "FGS-MT"),
                ("FORC-FGS", "FORC-FGS"),
            ],
        )

        # Internal parameters
        g.cm_stat0 = Parameter(
            m,
            name="CM_STAT0",
            domain=[g.cmitem, g.cmq],
            records=[("N2O-MT", "LIFE", 121), ("CH4-MT", "LIFE", 7)],
        )
        g.cm_sig1 = Parameter(m, name="CM_SIG1", domain=[g.allsow])
        g.cm_phi = Parameter(
            m,
            name="CM_PHI",
            domain=[g.cmitem, "*", "*"],
            description="Conc. transport matrix between reservoirs",
        )
        g.cm_sig = Parameter(
            m,
            name="CM_SIG",
            domain=[g.allsow, "*", "*"],
            description="Temperature transport matrix between reservoirs",
        )
        g.cm_aa = Parameter(
            m,
            name="CM_AA",
            domain=[g.cmitem, g.allyear, g.allsow, "*", "*"],
            description="Periodical CO2 transport matrix",
        )
        g.cm_bb = Parameter(
            m,
            name="CM_BB",
            domain=[g.cmitem, g.allyear, g.allsow, g.CmBox],
            description="Periodical emission transport vector",
        )
        g.cm_cc = Parameter(
            m,
            name="CM_CC",
            domain=[g.cmitem, g.allyear, g.allsow, g.CmBox],
            description="Periodical emission transport vector",
        )
        g.cm_rr = Parameter(
            m, name="CM_RR", domain=[g.j, g.CmBox, "*"], description="Reporting"
        )
        g.cm_deltat = Parameter(
            m,
            name="CM_DELTAT",
            domain=[g.allyear, g.CmBox],
            description="Temperature change in T boxes",
        )
        g.cm_led = Parameter(m, name="CM_LED", domain=[g.allyear])
        g.cm_bemi = Parameter(m, name="CM_BEMI", domain=[g.cmitem, g.ll])
        g.cm_evar = Parameter(m, name="CM_EVAR", domain=[g.cmitem, g.ll])

        # *-----------------------------------------------------------------------------
        # * If CM_CO2GTC is not implemented in the shell, IRE_CCVT can alternatively be used
        # * For that purpose, a predefined commodity for global CO2 emissions is needed:
        comgrp_records = [
            "FORC-CO2",
            "FORC-CH4",
            "FORC-N2O",
            "FORC-FGS",
            "FORC-KYO",
            "DELTA",
        ]
        com_records = ["CO2-GTC", "CH4-MT", "N2O-MT", "FORCING", "CO2-ATM", "DELTA-ATM"]
        expand_set(g.comgrp, [*comgrp_records, "ACT"])
        expand_set(g.Com, com_records)
        # *-----------------------------------------------------------------------------
        g.cm_const = Parameter(
            m,
            name="CM_CONST",
            domain=["*"],
            description="Climate module constants",
            records=[
                ("PHI-UP-AT", 0.0453),
                ("PHI-AT-UP", 0.0495),
                ("PHI-LO-UP", 0.00053),
                ("PHI-UP-LO", 0.0146),
                ("GAMMA", 0),
                ("LAMBDA", 1.41),
                ("CS", 2.91),
                ("SIGMA1", 0.024),
                ("SIGMA2", 0.44),
                ("SIGMA3", 0.002),
                ("CO2-PREIND", 596.4),
                ("PHI-CH4", 0.09158),
                ("PHI-N2O", 0.008803),
                ("EXT-EOH", -1),
                ("BEOHMOD", 20),
            ],
        )

        self.tc.enqueue(self.exec1)

        # *-----------------------------------------------------------------------------
        # * The following parameters describe historical mass of CO2 in the ATM and ocean
        # * as well as historical temperature increases in surface and deep ocean
        # **** User provided values override these default hard-coded values ****
        g.cm_default = Parameter(
            m,
            name="CM_DEFAULT",
            domain=[g.allyear, g.cmitem],
            records=[
                ("1990", "CO2-ATM", 735.0),
                ("1990", "CO2-UP", 0),
                ("1990", "CO2-LO", 19230.0),
                ("1990", "DELTA-ATM", 0.43),
                ("1990", "DELTA-LO", 0.06),
                ("1990", "CH4-ATM", 0),
                ("1990", "CH4-UP", 0),
                ("1990", "N2O-ATM", 0),
                ("1990", "N2O-UP", 0),
                ("1995", "CO2-ATM", 765.0),
                ("1995", "CO2-UP", 781.0),
                ("1995", "CO2-LO", 19230.0),
                ("1995", "DELTA-ATM", 0.5),
                ("1995", "DELTA-LO", 0.06),
                ("1995", "CH4-ATM", 0),
                ("1995", "CH4-UP", 0),
                ("1995", "N2O-ATM", 0),
                ("1995", "N2O-UP", 0),
                ("2000", "CO2-ATM", 785.0),
                ("2000", "CO2-UP", 798.0),
                ("2000", "CO2-LO", 19230.0),
                ("2000", "DELTA-ATM", 0.65),
                ("2000", "DELTA-LO", 0.06),
                ("2000", "CH4-ATM", 3030.0),
                ("2000", "CH4-UP", 1988.0),
                ("2000", "N2O-ATM", 360.0),
                ("2000", "N2O-UP", 2109.0),
                ("2005", "CO2-ATM", 806.0),
                ("2005", "CO2-UP", 0),
                ("2005", "CO2-LO", 19230.0),
                ("2005", "DELTA-ATM", 0.75),
                ("2005", "DELTA-LO", 0.06),
                ("2005", "CH4-ATM", 3067.0),
                ("2005", "CH4-UP", 1988.0),
                ("2005", "N2O-ATM", 390.0),
                ("2005", "N2O-UP", 2109.0),
                ("2010", "CO2-ATM", 826.0),
                ("2010", "CO2-UP", 830.0),
                ("2010", "CO2-LO", 19230.0),
                ("2010", "DELTA-ATM", 0.8),
                ("2010", "DELTA-LO", 0.06),
                ("2010", "CH4-ATM", 3122.0),
                ("2010", "CH4-UP", 1988.0),
                ("2010", "N2O-ATM", 414.0),
                ("2010", "N2O-UP", 2109.0),
            ],
        )
        # *-----------------------------------------------------------------------------

    def exec1(self: InitmtyCli) -> None:
        g = self.tc
        ll = g.ll
        cm_const = g.cm_const

        if cm_const["GAMMA"].toDense() == 0:
            cm_const["GAMMA"] = 5.35 * log(2)

        if cm_const["LAMBDA"].toDense() == 0:
            cm_const["LAMBDA"] = 1.25

        if cm_const["CS"].toDense() == 0:
            cm_const["CS"] = cm_const["GAMMA"] / cm_const["LAMBDA"]

        cm_const["LAMBDA"] = cm_const["GAMMA"] / cm_const["CS"]
        g.e["0"] = 0.0

        if cm_const["EXT-EOH"].toDense() == 0:
            cm_const["EXT-EOH"] = Smax(ll.where[g.e[ll]], g.e[ll])
