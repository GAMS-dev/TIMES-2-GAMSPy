# mod_equa_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_EQUA.MOD lists all the equations for each of the MODEL instances        *
# *  a MODEL / <list of equations> / block will appear for each model supported *
# *=============================================================================*
# *GaG Questions/Comments:
# *   - any non-binding (=N=) accounting equations, or do it all with reports?
# *   - Investment component = investment cost + tax/sub + decom, not split?
# *   - Fixed component = O&M cost + tax/sub, not split?
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def mod_equa_mod(
    equations: list[str],
    arg1: str,
    stages: str,
    eq: str,
    timesed: str,
    objann: str,
    var_uc: str,
    damage: str,
    spines: str,
    def_prc_simv: bool,
    def_dam_cost: bool,
    def_vnret: bool,
) -> list[str]:
    if arg1 != "CORE":
        # *-----------------------------------------------------------------------------
        # * Objective Function & Components
        # *-----------------------------------------------------------------------------
        # * Overall OBJ linear combination of the regional objs (which are built from rest)
        equations.append("EQ_OBJ")

        if stages.upper() == "YES":
            equations.extend(["EQ_EXPOBJ", "EQ_UPDEV", f"{eq}_SOBJ", f"{eq}_ROBJ"])

        # * Resource depletion costs
        # equations.append("EQ_OBJDPL")

        # Costs of elastic demands
        if timesed == "YES":
            equations.append(f"{eq}_OBJELS")

        if objann.upper() != "YES":
            # Fixed Costs including tax/subsidy
            equations.append(f"{eq}_OBJFIX")

            # investment component including tax/subsidy
            equations.append(f"{eq}_OBJINV")

            # Salvage
            equations.append(f"{eq}_OBJSALV")

            # Variable operating costs
            equations.append(f"{eq}_OBJVAR")

    # Core Equations
    equations.extend(
        core_equations(
            eq=eq,
            timesed=timesed,
            var_uc=var_uc,
            damage=damage,
            spines=spines,
            objann=objann,
            def_prc_simv=def_prc_simv,
            def_dam_cost=def_dam_cost,
            def_vnret=def_vnret,
        )
    )

    return equations


def core_equations(
    eq: str,
    timesed: str,
    var_uc: str,
    damage: str,
    spines: str,
    objann: str,
    def_prc_simv: bool,
    def_dam_cost: bool,
    def_vnret: bool,
) -> list[str]:
    """Core Equations"""
    equations = []

    # MACRO calibration
    if objann.upper() == "YES":
        equations.extend(["EQ_OBJANN, EQ_ANNFIX, EQ_ANNINV, EQ_ANNVAR"])

    # Relationship between process activity & individual commodity flows
    equations.append(f"{eq}_ACTFLO")

    # Bound of vintage process activity or TS-level above PRC_TS
    equations.append(f"{eq}G_ACTBND")
    equations.append(f"{eq}E_ACTBND")
    equations.append(f"{eq}L_ACTBND")

    # Bound on commodities
    equations.append(f"{eq}G_BNDNET")
    equations.append(f"{eq}E_BNDNET")
    equations.append(f"{eq}L_BNDNET")
    equations.append(f"{eq}G_BNDPRD")
    equations.append(f"{eq}E_BNDPRD")
    equations.append(f"{eq}L_BNDPRD")

    #  Utilization of capacity, or the relationship between process capacity and activity
    equations.append(f"{eq}L_CAPACT")
    equations.append(f"{eq}E_CAPACT")
    equations.append(f"{eq}G_CAPACT")

    if def_prc_simv:
        equations.extend(["EQL_CAPVAC", "EQE_CAPVAC", "EQG_CAPVAC"])

    # Basic commodity balance equations (by type) ensuring that production >=/= consumption
    equations.append(f"{eq}G_COMBAL")
    equations.append(f"{eq}E_COMBAL")
    equations.append(f"{eq}E_COMPRD")

    if timesed == "YES":
        equations.append(f"{eq}L_COMCES")

    # Transfer of installed capacity between periods
    equations.append(f"{eq}E_CPT")
    equations.append(f"{eq}G_CPT")
    equations.append(f"{eq}L_CPT")

    # Bound on the flow variable
    equations.append(f"{eq}G_FLOBND")
    equations.append(f"{eq}E_FLOBND")
    equations.append(f"{eq}L_FLOBND")

    # Bound on the fraction of a flow within a time slice
    equations.append(f"{eq}G_FLOFR")
    equations.append(f"{eq}E_FLOFR")
    equations.append(f"{eq}L_FLOFR")

    # Market share equation allocating commodity percentages of a group
    equations.append(f"{eq}G_INSHR")
    equations.append(f"{eq}E_INSHR")
    equations.append(f"{eq}L_INSHR")

    #  Inter-regional exchange balance
    equations.append(f"{eq}_IRE")

    # Bound on inter-regional exchange of a commodity
    equations.append(f"{eq}G_IREBND")
    equations.append(f"{eq}E_IREBND")
    equations.append(f"{eq}L_IREBND")

    # Bound on total exchange of a commodity to/from all regions
    equations.append(f"{eq}G_XBND")
    equations.append(f"{eq}E_XBND")
    equations.append(f"{eq}L_XBND")

    # Product share equation allocating commodity percentages of a group
    equations.append(f"{eq}G_OUTSHR")
    equations.append(f"{eq}E_OUTSHR")
    equations.append(f"{eq}L_OUTSHR")

    # Market share equation for process in total commodity production
    equations.append(f"{eq}G_FLOMRK")
    equations.append(f"{eq}E_FLOMRK")
    equations.append(f"{eq}L_FLOMRK")

    # Peaking Equation
    equations.append(f"{eq}_PEAK")

    # Commodity-to-commodity transformation
    equations.append(f"{eq}_PTRANS")

    # Cumulative commodity NET/PRD and flow constraint
    equations.append(f"{eq}_CUMNET")
    equations.append(f"{eq}_CUMPRD")
    equations.append(f"{eq}_CUMFLO")

    # Time-slice storage
    equations.append(f"{eq}_STGTSS")
    equations.append(f"{eq}_STSBAL")
    equations.append("EQ_STSLEV")

    # Bounds on in/output flows of storage process
    equations.append(f"{eq}G_STGIN")
    equations.append(f"{eq}E_STGIN")
    equations.append(f"{eq}L_STGIN")
    equations.append(f"{eq}G_STGOUT")
    equations.append(f"{eq}E_STGOUT")
    equations.append(f"{eq}L_STGOUT")

    #  Inter-period storage
    equations.append(f"{eq}_STGIPS")
    equations.append(f"{eq}_STGAUX")

    #  User-constraint
    equations.append(f"{eq}E_UC")
    equations.append(f"{eq}E_UCR")
    equations.append(f"{eq}E_UCT")
    equations.append(f"{eq}E_UCRS")
    equations.append(f"{eq}E_UCTS")
    equations.append(f"{eq}E_UCRT")
    equations.append(f"{eq}E_UCRTS")
    equations.append(f"{eq}E_UCSU")
    equations.append(f"{eq}E_UCRSU")
    equations.append(f"{eq}E_UCSUS")
    equations.append(f"{eq}E_UCRSUS")

    if var_uc != "YES":
        equations.extend(
            [
                "EQG_UC",
                "EQG_UCR",
                "EQG_UCT",
                "EQG_UCRS",
                "EQG_UCTS",
                "EQG_UCRT",
                "EQG_UCRTS",
                "EQG_UCSU",
                "EQG_UCRSU",
                "EQG_UCSUS",
                "EQG_UCRSUS",
                "EQL_UC",
                "EQL_UCR",
                "EQL_UCT",
                "EQL_UCRS",
                "EQL_UCTS",
                "EQL_UCRT",
                "EQL_UCRTS",
                "EQL_UCSU",
                "EQL_UCRSU",
                "EQL_UCSUS",
                "EQL_UCRSUS",
            ]
        )

    # * Bounds on costs by region, category and currency
    equations.append(f"{eq}_BNDCST")

    # *---------------------------------------------------------------------
    # *GG* V07_2 Refinery blending
    # *---------------------------------------------------------------------
    equations.append("EQL_BLND")
    equations.append("EQG_BLND")
    equations.append("EQE_BLND")
    equations.append("EQN_BLND")

    if def_dam_cost and damage != "NO":
        # damages
        equations.extend([f"{eq}_DAMAGE", f"{eq}_OBJDAM"])

    if def_vnret:
        equations.extend(
            [f"{eq}_DSCRET", f"{eq}_CUMRET", f"{eq}L_SCAP", f"{eq}L_REFIT"]
        )

    if spines.upper() == "YES":
        equations.append(f"{eq}_OBW1")

    return equations
