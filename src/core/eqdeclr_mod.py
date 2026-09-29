# eqdeclr_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQDECLR.MOD declarations for actual equations
# *   %1 - mod or v# for the source code to be used
# *=============================================================================*
# *GaG Questions/Comments:
# *   - declare all equations so that restarting changed models will work
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Alias, Equation, Set

from core.base_class import GamsClass
from core.eqdeclr_tm import EqdeclrTm

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqdeclrMod(GamsClass):
    """Translation unit for eqdeclr.mod."""

    # Instance attributes
    module_name: str = "eqdeclr_mod"
    gams_source: str = "eqdeclr.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment, arg1: str):
        self.env = env.fork()
        self._sub_modules = {}
        self.arg1 = arg1
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        eq: str = self.env.eq
        swtd: tuple[Alias | Set, ...] | tuple[()] = self.env.swtd_GP
        swd = self.env.swd_GP

        if self.env.macro.upper() == "YES":
            self.include(EqdeclrTm(self.tc, self.env))
        else:
            # *-----------------------------------------------------------------------------
            # * Objective Function & Components
            # *-----------------------------------------------------------------------------
            # * Overall OBJ linear combination of the regional objs (which are built from rest)
            g.eq_obj = Equation(
                m, name="EQ_OBJ", description="Overall Objective Function"
            )

            g.set_equation(
                name=f"{eq}_OBJELS",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJELS",
                    domain=[g.r, g.bd, g.cur, *swd],
                    description="Costs of elastic demands",
                ),
            )
            g.set_equation(
                name=f"{eq}_OBJFIX",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJFIX",
                    domain=[g.r, g.cur, *swd],
                    description="Fixed Costs",
                ),
            )
            g.set_equation(
                name=f"{eq}_OBJINV",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJINV",
                    domain=[g.r, g.cur, *swd],
                    description="Investment component",
                ),
            )
            g.set_equation(
                name=f"{eq}_OBJSALV",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJSALV",
                    domain=[g.r, g.cur, *swd],
                    description="Salvage",
                ),
            )
            g.set_equation(
                name=f"{eq}_OBJVAR",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJVAR",
                    domain=[g.r, g.cur, *swd],
                    description="Variable operating costs",
                ),
            )
            g.set_equation(
                name=f"{eq}_OBJDAM",
                eq=Equation(
                    m,
                    name=f"{eq}_OBJDAM",
                    domain=[g.r, g.cur, *swd],
                    description="Damage costs",
                ),
            )

        # *-----------------------------------------------------------------------------
        # * Core Equations
        # *-----------------------------------------------------------------------------

        # Relationship between process activity & individual primary commodity flows
        g.set_equation(
            f"{eq}_ACTFLO",
            Equation(
                m,
                name=f"{eq}_ACTFLO",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swtd],
                description="Process Activity/Primary Commodity Flows",
            ),
        )

        # * Bound on activity
        g.set_equation(
            f"{eq}G_ACTBND",
            Equation(
                m,
                name=f"{eq}G_ACTBND",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.s, *swtd],
                description="Process activity Bound in a Period (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_ACTBND",
            Equation(
                m,
                name=f"{eq}E_ACTBND",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.s, *swtd],
                description="Process activity Bound in a Period (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_ACTBND",
            Equation(
                m,
                name=f"{eq}L_ACTBND",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.s, *swtd],
                description="Process activity Bound in a Period (=L=)",
            ),
        )

        # * Bound on commodities
        g.set_equation(
            f"{eq}G_BNDNET",
            Equation(
                m,
                name=f"{eq}G_BNDNET",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Net bound on a commodity (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_BNDNET",
            Equation(
                m,
                name=f"{eq}E_BNDNET",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Net bound on a commodity (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_BNDNET",
            Equation(
                m,
                name=f"{eq}L_BNDNET",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Net bound on a commodity (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}G_BNDPRD",
            Equation(
                m,
                name=f"{eq}G_BNDPRD",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Production bound on a commodity (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_BNDPRD",
            Equation(
                m,
                name=f"{eq}E_BNDPRD",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Production bound on a commodity (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_BNDPRD",
            Equation(
                m,
                name=f"{eq}L_BNDPRD",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Production bound on a commodity (=L=)",
            ),
        )

        # * Utilization of capacity, or the relationship between process capacity and activity
        g.set_equation(
            f"{eq}L_CAPACT",
            Equation(
                m,
                name=f"{eq}L_CAPACT",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swtd],
                description="Capacity Utilzation (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}E_CAPACT",
            Equation(
                m,
                name=f"{eq}E_CAPACT",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swtd],
                description="Capacity Utilzation (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}G_CAPACT",
            Equation(
                m,
                name=f"{eq}G_CAPACT",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swtd],
                description="Capacity Utilzation (=G=)",
            ),
        )

        # * Basic commodity balance equations (by type) ensuring that production >=/= consumption
        g.set_equation(
            f"{eq}G_COMBAL",
            Equation(
                m,
                name=f"{eq}G_COMBAL",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Commodity Balance (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_COMBAL",
            Equation(
                m,
                name=f"{eq}E_COMBAL",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Commodity Balance (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_COMPRD",
            Equation(
                m,
                name=f"{eq}E_COMPRD",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, *swtd],
                description="Commodity Production (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_COMCES",
            Equation(
                m,
                name=f"{eq}L_COMCES",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.c, g.s, *swtd],
                description="CES substitution steps (=L=)",
            ),
        )

        # * Transfer of installed capacity between periods
        g.set_equation(
            f"{eq}G_CPT",
            Equation(
                m,
                name=f"{eq}G_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_CPT",
            Equation(
                m,
                name=f"{eq}E_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_CPT",
            Equation(
                m,
                name=f"{eq}L_CPT",
                type="regular",
                domain=[g.r, g.allyear, g.p, *swtd],
                description="Capacity Transfer (=L=)",
            ),
        )
        # * Cumulative constraints
        g.set_equation(
            f"{eq}_CUMNET",
            Equation(
                m,
                name=f"{eq}_CUMNET",
                type="regular",
                domain=[g.r, g.c, g.allyear, g.allyear, *swd],
                description="Cummulative Net Commodity Limit (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}_CUMPRD",
            Equation(
                m,
                name=f"{eq}_CUMPRD",
                type="regular",
                domain=[g.r, g.c, g.allyear, g.allyear, *swd],
                description="Cummulative Commodity Production Limit (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}_CUMFLO",
            Equation(
                m,
                name=f"{eq}_CUMFLO",
                type="regular",
                domain=[g.r, g.p, g.c, g.allyear, g.ll, *swd],
                description="Cummulative Commodity Flow Limit (=E=)",
            ),
        )

        # * Bound on the fraction of a flow within a time slice
        g.set_equation(
            f"{eq}G_FLOFR",
            Equation(
                m,
                name=f"{eq}G_FLOFR",
                type="regular",
                domain=[g.r, g.t, g.p, g.c, g.s, g.lA, *swtd],
                description="Flow fraction (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_FLOFR",
            Equation(
                m,
                name=f"{eq}E_FLOFR",
                type="regular",
                domain=[g.r, g.t, g.p, g.c, g.s, g.lA, *swtd],
                description="Flow fraction (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_FLOFR",
            Equation(
                m,
                name=f"{eq}L_FLOFR",
                type="regular",
                domain=[g.r, g.t, g.p, g.c, g.s, g.lA, *swtd],
                description="Flow fraction (=L=)",
            ),
        )

        # * Bound on the total flow
        g.set_equation(
            f"{eq}G_FLOBND",
            Equation(
                m,
                name=f"{eq}G_FLOBND",
                type="regular",
                domain=[g.r, g.t, g.p, g.cg, g.s, *swtd],
                description="Flow bound (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_FLOBND",
            Equation(
                m,
                name=f"{eq}E_FLOBND",
                type="regular",
                domain=[g.r, g.t, g.p, g.cg, g.s, *swtd],
                description="Flow bound (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_FLOBND",
            Equation(
                m,
                name=f"{eq}L_FLOBND",
                type="regular",
                domain=[g.r, g.t, g.p, g.cg, g.s, *swtd],
                description="Flow bound (=L=)",
            ),
        )

        # * Market share equation allocating commodity percentages of a group
        g.set_equation(
            f"{eq}G_INSHR",
            Equation(
                m,
                name=f"{eq}G_INSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Input Group Share (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_INSHR",
            Equation(
                m,
                name=f"{eq}E_INSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Input Group Share (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_INSHR",
            Equation(
                m,
                name=f"{eq}L_INSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Input Group Share (=L=)",
            ),
        )

        # * Inter-period storage equation
        g.set_equation(
            f"{eq}_STGIPS",
            Equation(
                m,
                name=f"{eq}_STGIPS",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.item, *swtd],
                description="Inter-period storage equation",
            ),
        )
        g.set_equation(
            f"{eq}_STGAUX",
            Equation(
                m,
                name=f"{eq}_STGAUX",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.s, *swtd],
                description="Storage auxiliary flows",
            ),
        )

        # * Inter-regional exchange balance
        g.set_equation(
            f"{eq}_IRE",
            Equation(
                m,
                name=f"{eq}_IRE",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.ie, g.s, *swtd],
                description="Inter-regional Exchange Process Balance (=E=)",
            ),
        )

        # * Bound on inter-regional exchange of a commodity
        g.set_equation(
            f"{eq}G_IREBND",
            Equation(
                m,
                name=f"{eq}G_IREBND",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, g.allreg, g.ie, *swtd],
                description="Limit on Inter-regional Exchange (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_IREBND",
            Equation(
                m,
                name=f"{eq}E_IREBND",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, g.allreg, g.ie, *swtd],
                description="Limit on Inter-regional Exchange (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_IREBND",
            Equation(
                m,
                name=f"{eq}L_IREBND",
                type="regular",
                domain=[g.r, g.allyear, g.c, g.s, g.allreg, g.ie, *swtd],
                description="Limit on Inter-regional Exchange (=L=)",
            ),
        )

        # * Bound on total exchange of a commodity to/from all regions
        g.set_equation(
            f"{eq}G_XBND",
            Equation(
                m,
                name=f"{eq}G_XBND",
                type="regular",
                domain=[g.allreg, g.allyear, g.c, g.s, g.ie, *swtd],
                description="Limit on Total Exchange (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_XBND",
            Equation(
                m,
                name=f"{eq}E_XBND",
                type="regular",
                domain=[g.allreg, g.allyear, g.c, g.s, g.ie, *swtd],
                description="Limit on Total Exchange (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_XBND",
            Equation(
                m,
                name=f"{eq}L_XBND",
                type="regular",
                domain=[g.allreg, g.allyear, g.c, g.s, g.ie, *swtd],
                description="Limit on Total Exchange (=L=)",
            ),
        )

        # * Product share equation allocating commodity percentages of a group
        g.set_equation(
            f"{eq}G_OUTSHR",
            Equation(
                m,
                name=f"{eq}G_OUTSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Output Group Share (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_OUTSHR",
            Equation(
                m,
                name=f"{eq}E_OUTSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Output Group Share (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_OUTSHR",
            Equation(
                m,
                name=f"{eq}L_OUTSHR",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.c, g.cg, g.s, *swtd],
                description="Commodity Output Group Share (=L=)",
            ),
        )

        # * Process market-share equation of total commodity production
        g.set_equation(
            f"{eq}G_FLOMRK",
            Equation(
                m,
                name=f"{eq}G_FLOMRK",
                type="regular",
                domain=[g.r, g.allyear, g.item, g.c, g.s, *swtd],
                description="Process market-share (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_FLOMRK",
            Equation(
                m,
                name=f"{eq}E_FLOMRK",
                type="regular",
                domain=[g.r, g.allyear, g.item, g.c, g.s, *swtd],
                description="Process market-share (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_FLOMRK",
            Equation(
                m,
                name=f"{eq}L_FLOMRK",
                type="regular",
                domain=[g.r, g.allyear, g.item, g.c, g.s, *swtd],
                description="Process market-share (=L=)",
            ),
        )

        # * Peaking Equation
        g.set_equation(
            f"{eq}_PEAK",
            Equation(
                m,
                name=f"{eq}_PEAK",
                type="regular",
                domain=[g.r, g.allyear, g.comgrp, g.s, *swtd],
                description="Commodity Peaking constraint (=G=)",
            ),
        )

        # * Commodity-to-commodity transformation
        g.set_equation(
            f"{eq}_PTRANS",
            Equation(
                m,
                name=f"{eq}_PTRANS",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.cg, g.cg, g.s, *swtd],
                description="Commodity-to-Commodity Transform (=E=)",
            ),
        )

        # * Time-slice storage equation
        g.set_equation(
            f"{eq}_STGTSS",
            Equation(
                m,
                name=f"{eq}_STGTSS",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.s, *swtd],
                description="Time-slice storage equation",
            ),
        )
        g.set_equation(
            f"{eq}_STSBAL",
            Equation(
                m,
                name=f"{eq}_STSBAL",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.tsl, g.s, g.lA, *swtd],
                description="Time-slice storage balancer",
            ),
        )
        g.eq_stslev = Equation(
            m,
            name="EQ_STSLEV",
            type="regular",
            domain=[g.r, g.allyear, g.allyear, g.p, g.tslvl, g.s, g.allsow],
            description="Time-slice storage levelizer",
        )

        # * Bound on storage flow
        g.set_equation(
            f"{eq}G_STGIN",
            Equation(
                m,
                name=f"{eq}G_STGIN",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on input flow of storage (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_STGIN",
            Equation(
                m,
                name=f"{eq}E_STGIN",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on input flow of storage (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_STGIN",
            Equation(
                m,
                name=f"{eq}L_STGIN",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on input flow of storage (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}G_STGOUT",
            Equation(
                m,
                name=f"{eq}G_STGOUT",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on output flow of storage (=G=)",
            ),
        )
        g.set_equation(
            f"{eq}E_STGOUT",
            Equation(
                m,
                name=f"{eq}E_STGOUT",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on output flow of storage (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}L_STGOUT",
            Equation(
                m,
                name=f"{eq}L_STGOUT",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.c, g.s, *swtd],
                description="Bound on output flow of storage (=L=)",
            ),
        )

        # *Retirements
        g.set_equation(
            f"{eq}_CUMRET",
            Equation(
                m,
                name=f"{eq}_CUMRET",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, *swtd],
                description="Cumulative retirements",
            ),
        )
        g.set_equation(
            f"{eq}L_REFIT",
            Equation(
                m,
                name=f"{eq}L_REFIT",
                type="regular",
                domain=[g.r, g.allyear, g.allyear, g.p, g.lA, *swtd],
                description="Retrofit/life-extension (=L=)",
            ),
        )
        g.set_equation(
            f"{eq}L_SCAP",
            Equation(
                m,
                name=f"{eq}L_SCAP",
                type="regular",
                domain=[g.r, g.allyear, g.p, g.ips, *swd],
                description="Salvage capacity (=L=)",
            ),
        )

        # * Cost bounds
        g.set_equation(
            f"{eq}_BNDCST",
            Equation(
                m,
                name=f"{eq}_BNDCST",
                type="regular",
                domain=[g.Reg, g.allyear, g.t, g.allyear, g.costcat, g.cur, *swd],
                description="Bound on cumulative costs",
            ),
        )

        # *User - constraints
        g.set_equation(
            f"{eq}E_UC",
            Equation(
                m,
                name=f"{eq}E_UC",
                type="regular",
                domain=[g.ucn, *swd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCR",
            Equation(
                m,
                name=f"{eq}E_UCR",
                type="regular",
                domain=[g.r, g.ucn, *swd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCT",
            Equation(
                m,
                name=f"{eq}E_UCT",
                type="regular",
                domain=[g.ucn, g.t, *swtd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRT",
            Equation(
                m,
                name=f"{eq}E_UCRT",
                type="regular",
                domain=[g.r, g.t, g.ucn, *swtd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCTS",
            Equation(
                m,
                name=f"{eq}E_UCTS",
                type="regular",
                domain=[g.ucn, g.t, g.s, *swtd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRS",
            Equation(
                m,
                name=f"{eq}E_UCRS",
                type="regular",
                domain=[g.r, g.t, g.ucn, g.tsl, g.s, *swtd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRTS",
            Equation(
                m,
                name=f"{eq}E_UCRTS",
                type="regular",
                domain=[g.r, g.t, g.ucn, g.s, *swtd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCSU",
            Equation(
                m,
                name=f"{eq}E_UCSU",
                type="regular",
                domain=[g.ucn, g.t, *swd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCSUS",
            Equation(
                m,
                name=f"{eq}E_UCSUS",
                type="regular",
                domain=[g.ucn, g.t, g.s, *swd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRSUS",
            Equation(
                m,
                name=f"{eq}E_UCRSUS",
                type="regular",
                domain=[g.r, g.t, g.ucn, g.s, *swd],
                description="User-constraints (=E=)",
            ),
        )
        g.set_equation(
            f"{eq}E_UCRSU",
            Equation(
                m,
                name=f"{eq}E_UCRSU",
                type="regular",
                domain=[g.r, g.t, g.ucn, *swd],
                description="User-constraints (=E=)",
            ),
        )

        if self.env.var_uc != "YES":
            g.eqg_uc = Equation(
                m, name="EQG_UC", domain=[g.ucn], description="User-constraints (=G=)"
            )
            g.eqg_ucr = Equation(
                m,
                name="EQG_UCR",
                domain=[g.r, g.ucn],
                description="User-constraints (=G=)",
            )
            g.eqg_uct = Equation(
                m,
                name="EQG_UCT",
                domain=[g.ucn, g.t],
                description="User-constraints (=G=)",
            )
            g.eqg_ucrt = Equation(
                m,
                name="EQG_UCRT",
                domain=[g.r, g.t, g.ucn],
                description="User-constraints (=G=)",
            )
            g.eqg_ucts = Equation(
                m,
                name="EQG_UCTS",
                domain=[g.ucn, g.t, g.s],
                description="User-constraints (=G=)",
            )
            g.eqg_ucrs = Equation(
                m,
                name="EQG_UCRS",
                domain=[g.r, g.t, g.ucn, g.tsl, g.s],
                description="User-constraints (=G=)",
            )
            g.eqg_ucrts = Equation(
                m,
                name="EQG_UCRTS",
                domain=[g.r, g.t, g.ucn, g.s],
                description="User-constraints (=G=)",
            )
            g.eqg_ucsu = Equation(
                m,
                name="EQG_UCSU",
                domain=[g.ucn, g.t],
                description="User-constraints (=G=)",
            )
            g.eqg_ucsus = Equation(
                m,
                name="EQG_UCSUS",
                domain=[g.ucn, g.t, g.s],
                description="User-constraints (=G=)",
            )
            g.eqg_ucrsus = Equation(
                m,
                name="EQG_UCRSUS",
                domain=[g.r, g.t, g.ucn, g.s],
                description="User-constraints (=G=)",
            )
            g.eqg_ucrsu = Equation(
                m,
                name="EQG_UCRSU",
                domain=[g.r, g.t, g.ucn],
                description="User-constraints (=G=)",
            )
            g.eql_uc = Equation(
                m, name="EQL_UC", domain=[g.ucn], description="User-constraints (=L=)"
            )
            g.eql_ucr = Equation(
                m,
                name="EQL_UCR",
                domain=[g.r, g.ucn],
                description="User-constraints (=L=)",
            )
            g.eql_uct = Equation(
                m,
                name="EQL_UCT",
                domain=[g.ucn, g.t],
                description="User-constraints (=L=)",
            )
            g.eql_ucrt = Equation(
                m,
                name="EQL_UCRT",
                domain=[g.r, g.t, g.ucn],
                description="User-constraints (=L=)",
            )
            g.eql_ucts = Equation(
                m,
                name="EQL_UCTS",
                domain=[g.ucn, g.t, g.s],
                description="User-constraints (=L=)",
            )
            g.eql_ucrs = Equation(
                m,
                name="EQL_UCRS",
                domain=[g.r, g.t, g.ucn, g.tsl, g.s],
                description="User-constraints (=L=)",
            )
            g.eql_ucrts = Equation(
                m,
                name="EQL_UCRTS",
                domain=[g.r, g.t, g.ucn, g.s],
                description="User-constraints (=L=)",
            )
            g.eql_ucsu = Equation(
                m,
                name="EQL_UCSU",
                domain=[g.ucn, g.t],
                description="User-constraints (=L=)",
            )
            g.eql_ucsus = Equation(
                m,
                name="EQL_UCSUS",
                domain=[g.ucn, g.t, g.s],
                description="User-constraints (=L=)",
            )
            g.eql_ucrsus = Equation(
                m,
                name="EQL_UCRSUS",
                domain=[g.r, g.t, g.ucn, g.s],
                description="User-constraints (=L=)",
            )
            g.eql_ucrsu = Equation(
                m,
                name="EQL_UCRSU",
                domain=[g.r, g.t, g.ucn],
                description="User-constraints (=L=)",
            )

        # *GG* V07_2 BLENDing equation
        g.eql_blnd = Equation(
            m,
            name="EQL_BLND",
            domain=[g.r, g.year, g.Ble, g.spe, g.allsow],
            description="Blending (=L=)",
        )
        g.eqg_blnd = Equation(
            m,
            name="EQG_BLND",
            domain=[g.r, g.year, g.Ble, g.spe, g.allsow],
            description="Blending (=G=)",
        )
        g.eqe_blnd = Equation(
            m,
            name="EQE_BLND",
            domain=[g.r, g.year, g.Ble, g.spe, g.allsow],
            description="Blending (=E=)",
        )
        g.eqn_blnd = Equation(
            m,
            name="EQN_BLND",
            domain=[g.r, g.year, g.Ble, g.spe, g.allsow],
            type="nonbinding",
            description="Blending non-binding",
        )

        # * Damage Extension
        g.set_equation(
            name=f"{eq}_DAMAGE",
            eq=Equation(
                m,
                name=f"{eq}_DAMAGE",
                domain=[g.r, g.t, g.c, *swd],
                description="Damages",
            ),
        )

        # * Stochastic extension
        g.set_equation(
            name=f"{eq}_ROBJ",
            eq=Equation(
                m,
                name=f"{eq}_ROBJ",
                domain=[g.r, *swd],
                description="Deterministic objective by region and SOW",
            ),
        )
        g.set_equation(
            name=f"{eq}_SOBJ",
            eq=Equation(
                m,
                name=f"{eq}_SOBJ",
                domain=[g.lim, *swd],
                description="Deterministic objective by SOW",
            ),
        )
        g.eq_expobj = Equation(
            m,
            name="EQ_EXPOBJ",
            domain=[g.allsow],
            description="Expected value of total system cost",
        )
        g.eq_updev = Equation(
            m,
            name="EQ_UPDEV",
            domain=[g.allsow],
            description="Upper absolute deviation",
        )
