# initmty_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * INITMTY.VDA has all the EMPTY declarations for system & user data           *
# *=============================================================================*

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Parameter, Set

from core.base_class import GamsClass
from core.utils import expand_set

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyVda(GamsClass):
    """Translation unit for initmty.vda."""

    # Instance attributes
    module_name: str = "initmty_msa"
    gams_source: str = "initmty.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        self.env.set_global("vda", "YES")

        # User Input attributes in the VDA extension
        # -----------------------------------------------------------------------------
        # Process transformation parameters:
        g.vda_flop = Parameter(
            m,
            name="VDA_FLOP",
            description="General process transformation parameter",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.s],
        )
        g.vda_emcb = Parameter(
            m,
            name="VDA_EMCB",
            description="Combustion emission parameter (aka EMI_comb)",
            domain=[g.Reg, g.allyear, g.Com, g.Com],
        )
        g.vda_ceh = Parameter(
            m,
            name="VDA_CEH",
            description="The slope of pass-out turbine (alias NCAP_CEH)",
            domain=[g.Reg, g.allyear, g.prc],
        )
        g.flo_emis = Parameter(
            m,
            name="FLO_EMIS",
            description="General process emission parameter",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.Com, g.s],
        )
        g.flo_eff = Parameter(
            m,
            name="FLO_EFF",
            description="General process flow-relation parameter",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.Com, g.s],
        )
        # -----------------------------------------------------------------------------

        # Commodity-dependent availabilities:
        self.env.set_scoped("mx", ",SEASON, WEEKLY, DAYNITE")
        self.env.set_scoped("mx_GP", ("SEASON", "WEEKLY", "DAYNITE"))
        mx = ["SEASON", "WEEKLY", "DAYNITE"]

        stl_records = g.s.toList() + mx
        g.stl = Set(m, name="STL", records=stl_records)

        g.ncap_afac = Parameter(
            m,
            name="NCAP_AFAC",
            description="Annual availability of capacity for commodity group CG",
            domain=[g.Reg, g.allyear, g.prc, g.cg],
        )
        g.ncap_afc = Parameter(
            m,
            name="NCAP_AFC",
            description="Availability of capacity for commodity group CG",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.stl],
        )
        g.ncap_afcs = Parameter(
            m,
            name="NCAP_AFCS",
            description="Availability of capacity for commodity group CG",
            domain=[g.Reg, g.allyear, g.prc, g.cg, g.ts],
        )
        # -----------------------------------------------------------------------------
        # Dynamic UC variable bounds (UC_DYNBND user-defined)
        g.UcDynbnd = Set(
            m,
            name="UC_DYNBND",
            description="Dynamic process-wise UC bounds",
            domain=[g.ucn, g.lim],
        )
        # -----------------------------------------------------------------------------
        # Activity efficiency and dispatching options
        g.act_eff = Parameter(
            m,
            name="ACT_EFF",
            description="Activity efficiency for process",
            domain=[g.Reg, g.year, g.prc, g.cg, g.ts],
        )
        g.act_ups = Parameter(
            m,
            name="ACT_UPS",
            description="Max. ramp rate, fraction of capacity per hour",
            domain=[g.r, g.allyear, g.p, g.s, g.lA],
        )
        g.act_minld = Parameter(
            m,
            name="ACT_MINLD",
            description="Minimum stable operation level",
            domain=[g.r, g.allyear, g.p],
        )
        g.act_lospl = Parameter(
            m,
            name="ACT_LOSPL",
            description="Fuel consumption increase at minimum load",
            domain=[g.r, g.allyear, g.p, g.lA],
        )
        g.act_cstpl = Parameter(
            m,
            name="ACT_CSTPL",
            description="Partial load cost penalty",
            domain=[g.r, g.allyear, g.p, g.cur],
        )
        g.act_maxnon = Parameter(
            m,
            name="ACT_MAXNON",
            description="Max. non-operational time before transition to next stand-by condition, by start-up type, in hours",
            domain=[g.r, g.ll, g.p, g.upt],
        )
        g.act_sdtime = Parameter(
            m,
            name="ACT_SDTIME",
            description="Duration of start-up (BD=UP) and shut-down BD=LO) phases, by start-up type, in hours",
            domain=[g.r, g.ll, g.p, g.upt, g.bd],
        )
        g.act_lossd = Parameter(
            m,
            name="ACT_LOSSD",
            description="Efficiency at one hour from start-up (BD=UP) or at one hour to end of shut-down (BD=LO)",
            domain=[g.r, g.ll, g.p, g.upt, g.bd],
        )
        g.stg_maxcyc = Parameter(
            m,
            name="STG_MAXCYC",
            description="Maximum number of storage cycles over lifetime",
            domain=[g.r, g.year, g.p],
        )
        # -----------------------------------------------------------------------------
        # Risk parameters & network modeling attributes
        g.uc_actbet = Parameter(
            m, name="UC_ACTBET", domain=[g.ucn, g.allreg, g.allyear, g.prc]
        )
        g.uc_flobet = Parameter(
            m, name="UC_FLOBET", domain=[g.ucn, g.allreg, g.allyear, g.prc, g.cg]
        )
        g.com_cstbal = Parameter(
            m,
            name="COM_CSTBAL",
            description="Cost on specific component of node balance",
            domain=[g.r, g.allyear, g.c, g.s, g.item, g.cur],
        )
        g.prc_react = Parameter(
            m,
            name="PRC_REACT",
            description="Reactance of transmission line",
            domain=[g.r, g.allyear, g.p],
        )
        g.gr_ptdf = Parameter(
            m,
            name="GR_PTDF",
            description="PTDF of transmission line",
            domain=[g.r, g.year, g.p, g.c, g.allr, g.c],
        )
        g.gr_genlev = Parameter(
            m,
            name="GR_GENLEV",
            description="Grid connection category for electricity generation commodity",
            domain=[g.r, g.c],
        )
        g.gr_demfr = Parameter(
            m,
            name="GR_DEMFR",
            description="Fraction of total electricity demand allocated to grid node",
            domain=[g.r, g.allyear, g.c, g.s],
        )
        g.gr_endfr = Parameter(
            m,
            name="GR_ENDFR",
            description="Fraction of sectoral electricity demand allocated to grid node",
            domain=[g.r, g.allyear, g.c, g.cg],
        )
        g.gr_genfr = Parameter(
            m,
            name="GR_GENFR",
            description="Fraction of electricity generation type allocated to grid node",
            domain=[g.r, g.allyear, g.c, g.item],
        )
        g.gr_genmap = Parameter(
            m,
            name="GR_GENMAP",
            description="Mapping of technology to generation type",
            domain=[g.r, g.p, g.item],
        )
        g.gr_xbnd = Parameter(
            m,
            name="GR_XBND",
            description="Maximum level of net imports to / exports from region",
            domain=[g.r, g.allyear],
        )
        g.gr_thmin = Parameter(
            m,
            name="GR_THMIN",
            description="Thermal minimum level",
            domain=[g.r, g.ll, g.p],
        )
        g.gr_vargen = Parameter(
            m,
            name="GR_VARGEN",
            description="Variance in type of generation",
            domain=[g.r, g.s, g.item, g.bd],
        )
        g.gg_dens = Parameter(
            m, name="GG_DENS", description="Density of gases", domain=[g.r, g.c]
        )
        g.gg_gamma = Parameter(
            m,
            name="GG_GAMMA",
            description="Comprossion factor",
            domain=[g.r, g.year, g.p, g.c],
        )
        g.gg_kgf = Parameter(
            m,
            name="GG_KGF",
            description="Weymouth constants",
            domain=[g.r, g.year, g.p, g.c],
        )
        g.gg_klp = Parameter(
            m,
            name="GG_KLP",
            description="Linepack constants",
            domain=[g.r, g.year, g.p, g.c],
        )
        g.gg_prbd = Parameter(
            m,
            name="GG_PRBD",
            description="Nodal pressure bounds",
            domain=[g.r, g.year, g.c, g.lim],
        )
        g.gg_pp = Parameter(
            m,
            name="GG_PP",
            description="Fixed pressure points",
            domain=[g.r, g.year, g.p, g.c, g.lA, g.j],
        )
        # -----------------------------------------------------------------------------
        # Attributes for experimental ECB extension
        g.com_mshgv = Parameter(
            m,
            name="COM_MSHGV",
            description="Choices heterogeneity parameter",
            domain=[g.r, g.year, g.c],
        )
        g.ncap_msprf = Parameter(
            m,
            name="NCAP_MSPRF",
            description="Preference parameters in choice",
            domain=[g.r, g.year, g.c, g.p, g.lim],
        )
        # -----------------------------------------------------------------------------
        # Predefined items
        allreg_records = ["IMPEXP"]
        if g.allreg is None:
            g.allreg = Set(m, name="ALL_REG", records=allreg_records)
        else:
            expand_set(g.allreg, allreg_records)

        comgrp_records = ["IMP", "EXP"]
        if g.comgrp is None:
            g.comgrp = Set(m, name="COM_GRP", records=comgrp_records)
        else:
            expand_set(g.comgrp, comgrp_records)

        self.add_records_to_universe_item(records=["OBJ"])

        #   SET UC_NAME / ANNUAL %MX% /;
        #   SET UNIT 'Numbers of different units' /0/;
        #   SET UC_N /%SYSPREFIX%SOLVE_STATUS 'Model solution status code'/;

        ucname_records = ["ANNUAL", *mx]
        if g.ucname is None:
            g.ucname = Set(m, name="UC_NAME", records=ucname_records)
        else:
            expand_set(g.ucname, ucname_records)

        unit_records = ["0"]
        if g.unit is None:
            g.unit = Set(
                m,
                name="UNIT",
                description="Numbers of different units",
                records=unit_records,
            )
        else:
            expand_set(g.unit, unit_records)

        ucn_records = [
            (f"{self.env.sysprefix}SOLVE_STATUS", "Model solution status code")
        ]
        if g.ucn is None:
            g.ucn = Set(m, name="UC_N", records=ucn_records)
        else:
            expand_set(g.ucn, ucn_records)
        # -----------------------------------------------------------------------------
