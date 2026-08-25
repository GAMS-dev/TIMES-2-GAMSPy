# initmty_abs.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================
# * INIT Declarations for the ABS Extension (Ancillary Balancing Services)
# *=============================================================================
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number, Parameter, Set

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyAbs(GamsClass):
    """Translation unit for initmty_abs.mod."""

    # Instance attributes
    module_name: str = "initmty_abs"
    gams_source: str = "initmty.abs"

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

        self.env.set_global("abs", "YES")
        self.env.set_global("abs_GP", Number(1))

        # System sets
        self.add_records_to_universe_item(records=["SI"])
        g.Clvt = Set(m, name="CLVT", records=["PRB", "DET"])
        g.Rsp = Set(m, name="RSP", records=["EXOGEN", "WMAXSI", "DELTA", "OMEGA"])

        r, c, year, rsp, s, Com, bd, item, Reg, lA, tsl, t, ucnA, side, p, io, ts = (
            g.r,
            g.c,
            g.year,
            g.Rsp,
            g.s,
            g.Com,
            g.bd,
            g.item,
            g.Reg,
            g.lA,
            g.tsl,
            g.t,
            g.ucnA,
            g.side,
            g.p,
            g.io,
            g.ts,
        )
        # Input parameters
        g.bs_capact = Parameter(
            m,
            name="BS_CAPACT",
            domain=[r],
            description="Conversion factor from exogenous reserve demand to activity",
        )
        g.bs_rtype = Parameter(
            m,
            name="BS_RTYPE",
            domain=[r, c],
            description="Types of reserve commodities, positive or negative 1-4",
        )
        g.bs_demdet = Parameter(
            m,
            name="BS_DEMDET",
            domain=[r, year, rsp, c, s],
            description="Deterministic demands of reserves - EXOGEN and WMAXSI",
        )
        g.bs_stime = Parameter(
            m,
            name="BS_STIME",
            domain=[r, p, Com, bd],
            description="Minimum times for reserve provision from storage (hours)",
        )
        g.bs_detwt = Parameter(
            m,
            name="BS_DETWT",
            domain=[r, year, c],
            description="Weights for deterministic reserve demands",
        )
        g.bs_lambda = Parameter(
            m,
            name="BS_LAMBDA",
            domain=[r, year, c],
            description="Fudge factors for dependencies in reserve requirements",
        )
        g.bs_sigma = Parameter(
            m,
            name="BS_SIGMA",
            domain=[r, year, c, item, s],
            description="Standard deviation of imbalance source ITEM",
        )
        g.bs_omega = Parameter(
            m,
            name="BS_OMEGA",
            domain=[Reg, year, Com, ts],
            description="Indicator of how to define reserve demand from deterministic and probabilistic component",
        )
        g.bs_maint = Parameter(
            m,
            name="BS_MAINT",
            domain=[r, year, p, s],
            description="Continuous maintenance duration (hours)",
        )
        g.bs_rmax = Parameter(
            m,
            name="BS_RMAX",
            domain=[r, year, p, c, s],
            description="Maximum contribution of process p to provision of reserve c as a fraction of capacity",
        )
        g.bs_delta = Parameter(
            m,
            name="BS_DELTA",
            domain=[r, year, c, s],
            description="Calibration parameters for probabilistic reserve demands",
        )
        g.bs_share = Parameter(
            m,
            name="BS_SHARE",
            domain=[r, year, c, item, lA],
            description="Share of group reserve provision",
        )
        g.bs_bndprs = Parameter(
            m,
            name="BS_BNDPRS",
            domain=[r, year, p, c, s, lA],
            description="Bound on process reserve provision",
        )
        # Internal sets
        g.BsK = Set(
            m,
            name="BS_K",
            domain=[item],
            description="Sources of imbalance or provision",
            records=["UP", "LO"],
        )
        g.BsRtk = Set(
            m,
            name="BS_RTK",
            domain=[r, t, item],
            description="Sources of imbalances by period",
        )
        g.BsComts = Set(
            m,
            name="BS_COMTS",
            domain=[r, c, s],
            description="Reserve commodity timeslices",
        )
        g.BsApos = Set(
            m, name="BS_APOS", domain=[r, c], description="Positive reserve commodities"
        )
        g.BsAneg = Set(
            m, name="BS_ANEG", domain=[r, c], description="Negative reserve commodities"
        )
        g.BsAbd = Set(
            m,
            name="BS_ABD",
            domain=[r, c, lA],
            description="Reserve commodities by direction",
        )
        g.BsBsc = Set(
            m,
            name="BS_BSC",
            domain=[r, p, c],
            description="Reserve provisions by process",
        )
        g.BsUpl = Set(
            m,
            name="BS_UPL",
            domain=[r, p, lA],
            description="Maximum ramping rate indicator",
        )
        g.BsUpc = Set(
            m,
            name="BS_UPC",
            domain=[r, p, tsl, lA],
            description="Minimum uptime/downtime indicator",
        )
        g.BsTop = Set(
            m,
            name="BS_TOP",
            domain=[r, p, c, io],
            description="Topology for imbalance process",
        )
        g.BsEndp = Set(
            m, name="BS_ENDP", domain=[r, p], description="Reserve providion by demand"
        )
        g.BsSupp = Set(
            m,
            name="BS_SUPP",
            domain=[r, p],
            description="Reserve provision by generation",
        )
        g.BsStgp = Set(
            m, name="BS_STGP", domain=[r, p], description="Reserve provision by storage"
        )
        g.BsNegp = Set(
            m,
            name="BS_NEGP",
            domain=[r, p],
            description="Processes with negative provision",
        )
        g.BsPrs = Set(
            m,
            name="BS_PRS",
            domain=[r, p, s],
            description="Process slices for reserve tracking",
        )
        g.BsSbd = Set(
            m,
            name="BS_SBD",
            domain=[r, s, lA],
            description="Timeslices for reserve provision",
        )
        g.BsUcmap = Set(
            m,
            name="BS_UCMAP",
            domain=[ucnA, side, r, p, c],
            description="Map to refer to reserves in UC_FLO",
        )
        g.bs_rtcs = Parameter(
            m,
            name="BS_RTCS",
            domain=[rsp, r, year, c, s],
            description="Temporary work parameter",
        )
