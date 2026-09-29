# maplists_def.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *==============================================================================*
# * MAPLISTS.DEF has all the (fixed for now) MAPPING set group declarations
# *   For the most part the primary purpose of these lists is to group reporting
# *   table information, however some set members are explicitly tested for in
# *   the code and should not be removed/re-defined.
# *==============================================================================*
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Maplists(GamsClass):
    """Translation unit for maplists.def."""

    # Instance attributes
    module_name: str = "maplists"
    gams_source: str = "maplists.def"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # commodities
        # This list should NOT be adjusted as these group names are explicitly referenced in the code!
        com_type_records = [
            ("DEM", "Demands"),
            ("NRG", "Energy"),
            ("MAT", "Material"),
            ("ENV", "Environmental Indicators"),
            ("FIN", "Financial"),
        ]
        g.ComType = Set(
            m,
            name="COM_TYPE",
            domain=[g.comgrp],
            description="List of main commodity types groups",
            records=com_type_records,
        )

        g.PgSmap = Set(
            m,
            name="PG_SMAP",
            domain=[g.cg, g.j, g.cg],
            description="Map from PG to SPG",
            records=[
                ("DEM", "1", "NRG"),
                ("DEM", "2", "MAT"),
                ("DEM", "3", "ENV"),
                ("NRG", "1", "MAT"),
                ("NRG", "2", "DEM"),
                ("NRG", "3", "ENV"),
                ("MAT", "1", "NRG"),
                ("MAT", "2", "DEM"),
                ("MAT", "3", "ENV"),
                ("ENV", "1", "NRG"),
                ("ENV", "2", "MAT"),
                ("ENV", "3", "DEM"),
            ],
        )

        # currency
        g.curgrp = Set(
            m,
            name="CUR_GRP",
            description="List of currency groups",
            records=[
                ("DOMESTIC", "Domestic"),
                ("FOREIGN", "Foreign"),
                ("INTLAID", "International Aid"),
                ("RDD", "Research & Development"),
            ],
        )

        # demands
        g.demsect = Set(
            m,
            name="DEM_SECT",
            description="List of demand sectors",
            records=[
                ("RES", "Residential"),
                ("COM", "Commercial"),
                ("IND", "Industrial"),
                ("TRN", "Transportation"),
                ("AGR", "Agriculture"),
                ("NE", "Non-energy"),
                ("OTH", "Other"),
            ],
        )

        # environmental
        g.envgrp = Set(
            m,
            name="ENV_GRP",
            description="List of emission groups",
            records=[
                ("GHG", "Greenhouse Gases"),
                ("PEM", "Particulate emissions"),
                ("OEM", "Other emissions"),
                ("OTHENV", "Other indicators"),
            ],
        )

        # financial
        g.fingrp = Set(
            m,
            name="FIN_GRP",
            description="List of financial groups",
            records=[
                ("DOMESTIC", "Domestic"),
                ("FOREIGN", "Foreign"),
                ("INTLAID", "International Aid"),
            ],
        )

        # materials
        g.matgrp = Set(
            m,
            name="MAT_GRP",
            description="List of material groups",
            records=[
                ("PRIMARY", "Primary"),
                ("PRODUCT", "Product"),
                ("WASTE", "Waste"),
            ],
        )
        g.mattype = Set(
            m,
            name="MAT_TYPE",
            description="List of material types",
            records=[
                ("DURABLE", "Durables"),
                ("CONSUMED", "Consumed"),
                ("FINITE", "Finite"),
                ("RECYCLED", "Recycled"),
                ("RNEWABLE", "Renewable"),
            ],
        )

        # energy
        g.nrgform = Set(
            m,
            name="NRG_FORM",
            description="List of energy forms",
            records=[
                ("SOLID", "Solids"),
                ("LIQUID", "Liquids"),
                ("GAS", "Gaseous"),
            ],
        )

        nrg_grid_records = [
            ("ELC", "Electricity"),
            ("LTHEAT", "Low-temperature Heat"),
            ("HTHEAT", "High-temperature Heat"),
            ("GAS", "Gaseous"),
        ]

        g.nrggrid = Set(
            m,
            name="NRG_GRID",
            description="List of grid types",
            records=nrg_grid_records,
        )

        type_records = [
            ("FOSSIL", "Fossil"),
            ("NUCLR", "Nuclear"),
            ("SYNTH", "Synthetic"),
            ("RATE", "Rate of doing work or transferring heat (dW/dt)"),
            ("RENEN", "Renewable Energies"),
            ("LIMRENEW", "Limited Renewables"),
            # these values are explicitly referenced in the code to release the balance EQ
            ("FRERENEW", "Unlimited Renewables"),
            ("CONSRV", "Conservation"),
        ]

        # nrg_grid_records values are explicitly referenced in the code, e.g. part of CHP modeling
        nrg_type_records = type_records + nrg_grid_records
        g.nrgtype = Set(
            m,
            name="NRG_TYPE",
            description="List of energy types",
            records=nrg_type_records,
        )

        g.prcgrp = Set(
            m,
            name="PRC_GRP",
            description="List of process groups",
            records=[
                ("XTRACT", "Extraction"),
                ("RENEW", "Renewables (limited)"),
                ("PRE", "Energy"),
                ("PRW", "Material (by weight)"),
                ("PRV", "Material (by volume)"),
                ("REF", "Refined Products"),
                ("ELE", "Electric Generation"),
                ("HPL", "Heat Generation"),
                # this value is explicitly referenced in the code to ensure CHP attributes appropriate
                ("CHP", "Combined Heat+Power"),
                ("DMD", "Demand Devices"),
                ("DISTR", "Distribution Systems"),
                ("CORR", "Corridor Device"),
                ("STG", "Storage"),
                ("NST", "Night (Off-peak) Storage"),
                ("IRE", "Inter-region exchange (IMPort/EXPort)"),
                ("STK", "Stockpiling"),
                ("MISC", "Miscellaneous"),
                ("STS", "Time-slice storage (excluding night storages)"),
                ("SGS", "General process with storage capability"),
            ],
        )

        g.prcrsourc = Set(
            m,
            name="PRC_RSOURC",
            description="List of domestic resource supply groups",
            records=[
                ("UNDRGRD", "Underground"),
                ("STRIP", "Strip Mine"),
                ("OFFSHR", "Offshore"),
                ("ONSHR", "Onshore"),
                ("ENHANCED", "Enhanced Recovery"),
                ("BYPRD", "By-product"),
                ("HARVST", "Harvest & Gathering"),
            ],
        )
