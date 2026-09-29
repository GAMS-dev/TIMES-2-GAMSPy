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

from gamspy import Equation

from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_equa_mod(
    tc: TimesModelClass,
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
) -> list[Equation]:
    equations = []
    eq = eq.lower()
    if arg1 != "CORE":
        # *-----------------------------------------------------------------------------
        # * Objective Function & Components
        # *-----------------------------------------------------------------------------
        # * Overall OBJ linear combination of the regional objs (which are built from rest)
        equations.append(tc.eq_obj)

        if stages.upper() == "YES":
            equations.extend(
                [
                    tc.eq_expobj,
                    tc.eq_updev,
                    tc.get_equation(f"{eq}_sobj"),
                    tc.get_equation(f"{eq}_robj"),
                ]
            )

        # * Resource depletion costs
        # equations.append(tc.eq_objdpl)

        # Costs of elastic demands
        if timesed == "YES":
            equations.append(tc.get_equation(f"{eq}_objels"))

        if objann.upper() != "YES":
            # Fixed Costs including tax/subsidy
            equations.append(tc.get_equation(f"{eq}_objfix"))

            # investment component including tax/subsidy
            equations.append(tc.get_equation(f"{eq}_objinv"))

            # Salvage
            equations.append(tc.get_equation(f"{eq}_objsalv"))

            # Variable operating costs
            equations.append(tc.get_equation(f"{eq}_objvar"))

    # Core Equations
    equations.extend(
        core_equations(
            tc=tc,
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
    tc: TimesModelClass,
    eq: str,
    timesed: str,
    var_uc: str,
    damage: str,
    spines: str,
    objann: str,
    def_prc_simv: bool,
    def_dam_cost: bool,
    def_vnret: bool,
) -> list[Equation]:
    """Core Equations"""
    equations = []

    # MACRO calibration
    if objann.upper() == "YES":
        equations.extend(
            [
                tc.eq_objann,
                tc.eq_annfix,
                tc.eq_anninv,
                tc.eq_annvar,
            ]
        )

    # Relationship between process activity & individual commodity flows
    equations.append(tc.get_equation(f"{eq}_actflo"))

    # Bound of vintage process activity or TS-level above PRC_TS
    equations.append(tc.get_equation(f"{eq}g_actbnd"))
    equations.append(tc.get_equation(f"{eq}e_actbnd"))
    equations.append(tc.get_equation(f"{eq}l_actbnd"))

    # Bound on commodities
    equations.append(tc.get_equation(f"{eq}g_bndnet"))
    equations.append(tc.get_equation(f"{eq}e_bndnet"))
    equations.append(tc.get_equation(f"{eq}l_bndnet"))
    equations.append(tc.get_equation(f"{eq}g_bndprd"))
    equations.append(tc.get_equation(f"{eq}e_bndprd"))
    equations.append(tc.get_equation(f"{eq}l_bndprd"))

    #  Utilization of capacity, or the relationship between process capacity and activity
    equations.append(tc.get_equation(f"{eq}l_capact"))
    equations.append(tc.get_equation(f"{eq}e_capact"))
    equations.append(tc.get_equation(f"{eq}g_capact"))

    if def_prc_simv:
        equations.extend(
            [
                tc.eql_capvac,
                tc.eqe_capvac,
                tc.eqg_capvac,
            ]
        )

    # Basic commodity balance equations (by type) ensuring that production >=/= consumption
    equations.append(tc.get_equation(f"{eq}g_combal"))
    equations.append(tc.get_equation(f"{eq}e_combal"))
    equations.append(tc.get_equation(f"{eq}e_comprd"))

    if timesed == "YES":
        equations.append(tc.get_equation(f"{eq}l_comces"))

    # Transfer of installed capacity between periods
    equations.append(tc.get_equation(f"{eq}e_cpt"))
    equations.append(tc.get_equation(f"{eq}g_cpt"))
    equations.append(tc.get_equation(f"{eq}l_cpt"))

    # Bound on the flow variable
    equations.append(tc.get_equation(f"{eq}g_flobnd"))
    equations.append(tc.get_equation(f"{eq}e_flobnd"))
    equations.append(tc.get_equation(f"{eq}l_flobnd"))

    # Bound on the fraction of a flow within a time slice
    equations.append(tc.get_equation(f"{eq}g_flofr"))
    equations.append(tc.get_equation(f"{eq}e_flofr"))
    equations.append(tc.get_equation(f"{eq}l_flofr"))

    # Market share equation allocating commodity percentages of a group
    equations.append(tc.get_equation(f"{eq}g_inshr"))
    equations.append(tc.get_equation(f"{eq}e_inshr"))
    equations.append(tc.get_equation(f"{eq}l_inshr"))

    #  Inter-regional exchange balance
    equations.append(tc.get_equation(f"{eq}_ire"))

    # Bound on inter-regional exchange of a commodity
    equations.append(tc.get_equation(f"{eq}g_irebnd"))
    equations.append(tc.get_equation(f"{eq}e_irebnd"))
    equations.append(tc.get_equation(f"{eq}l_irebnd"))

    # Bound on total exchange of a commodity to/from all regions
    equations.append(tc.get_equation(f"{eq}g_xbnd"))
    equations.append(tc.get_equation(f"{eq}e_xbnd"))
    equations.append(tc.get_equation(f"{eq}l_xbnd"))

    # Product share equation allocating commodity percentages of a group
    equations.append(tc.get_equation(f"{eq}g_outshr"))
    equations.append(tc.get_equation(f"{eq}e_outshr"))
    equations.append(tc.get_equation(f"{eq}l_outshr"))

    # Market share equation for process in total commodity production
    equations.append(tc.get_equation(f"{eq}g_flomrk"))
    equations.append(tc.get_equation(f"{eq}e_flomrk"))
    equations.append(tc.get_equation(f"{eq}l_flomrk"))

    # Peaking Equation
    equations.append(tc.get_equation(f"{eq}_peak"))

    # Commodity-to-commodity transformation
    equations.append(tc.get_equation(f"{eq}_ptrans"))

    # Cumulative commodity NET/PRD and flow constraint
    equations.append(tc.get_equation(f"{eq}_cumnet"))
    equations.append(tc.get_equation(f"{eq}_cumprd"))
    equations.append(tc.get_equation(f"{eq}_cumflo"))

    # Time-slice storage
    equations.append(tc.get_equation(f"{eq}_stgtss"))
    equations.append(tc.get_equation(f"{eq}_stsbal"))
    equations.append(tc.get_equation("eq_stslev"))

    # Bounds on in/output flows of storage process
    equations.append(tc.get_equation(f"{eq}g_stgin"))
    equations.append(tc.get_equation(f"{eq}e_stgin"))
    equations.append(tc.get_equation(f"{eq}l_stgin"))
    equations.append(tc.get_equation(f"{eq}g_stgout"))
    equations.append(tc.get_equation(f"{eq}e_stgout"))
    equations.append(tc.get_equation(f"{eq}l_stgout"))

    #  Inter-period storage
    equations.append(tc.get_equation(f"{eq}_stgips"))
    equations.append(tc.get_equation(f"{eq}_stgaux"))

    #  User-constraint
    equations.append(tc.get_equation(f"{eq}e_uc"))
    equations.append(tc.get_equation(f"{eq}e_ucr"))
    equations.append(tc.get_equation(f"{eq}e_uct"))
    equations.append(tc.get_equation(f"{eq}e_ucrs"))
    equations.append(tc.get_equation(f"{eq}e_ucts"))
    equations.append(tc.get_equation(f"{eq}e_ucrt"))
    equations.append(tc.get_equation(f"{eq}e_ucrts"))
    equations.append(tc.get_equation(f"{eq}e_ucsu"))
    equations.append(tc.get_equation(f"{eq}e_ucrsu"))
    equations.append(tc.get_equation(f"{eq}e_ucsus"))
    equations.append(tc.get_equation(f"{eq}e_ucrsus"))

    if var_uc != "YES":
        equations.extend(
            [
                tc.eqg_uc,
                tc.eqg_ucr,
                tc.eqg_uct,
                tc.eqg_ucrs,
                tc.eqg_ucts,
                tc.eqg_ucrt,
                tc.eqg_ucrts,
                tc.eqg_ucsu,
                tc.eqg_ucrsu,
                tc.eqg_ucsus,
                tc.eqg_ucrsus,
                tc.eql_uc,
                tc.eql_ucr,
                tc.eql_uct,
                tc.eql_ucrs,
                tc.eql_ucts,
                tc.eql_ucrt,
                tc.eql_ucrts,
                tc.eql_ucsu,
                tc.eql_ucrsu,
                tc.eql_ucsus,
                tc.eql_ucrsus,
            ]
        )

    # * Bounds on costs by region, category and currency
    equations.append(tc.get_equation(f"{eq}_bndcst"))

    # *---------------------------------------------------------------------
    # *GG* V07_2 Refinery blending
    # *---------------------------------------------------------------------
    equations.append(tc.eql_blnd)
    equations.append(tc.eqg_blnd)
    equations.append(tc.eqe_blnd)
    equations.append(tc.eqn_blnd)

    if def_dam_cost and damage != "NO":
        # damages
        equations.extend(
            [tc.get_equation(f"{eq}_damage"), tc.get_equation(f"{eq}_objdam")]
        )

    if def_vnret:
        equations.extend(
            [
                tc.get_equation(f"{eq}_dscret"),
                tc.get_equation(f"{eq}_cumret"),
                tc.get_equation(f"{eq}l_scap"),
                tc.get_equation(f"{eq}l_refit"),
            ]
        )

    if spines.upper() == "YES":
        equations.append(tc.get_equation(f"{eq}_obw1"))

    return equations
