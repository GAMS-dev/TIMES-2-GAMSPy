# mod_equa_tm.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * MOD_EQUA.MOD lists all the equations for each of the MODEL instances        *
# *   a MODEL / <list of equaions> / block will appear for each model supported *
# *=============================================================================*

from __future__ import annotations

import logging

from core.mod_equa_mod import core_equations

logger = logging.getLogger(__name__)


def mod_equa_tm(
    equations: list[str],
    merge: str,
    eq: str,
    timesed: str,
    var_uc: str,
    damage: str,
    spines: str,
    def_prc_simv: bool,
    def_dam_cost: bool,
    def_vnret: bool,
    macro: str,
    nonlp: str,
) -> None:
    """Translation unit for mod_equa.tm."""

    if merge.upper() == "YES":
        equations.append("ALL")
        return

    # Objective Function & Components
    #  Overall OBJ linear combination of the regional objs (which are built from rest)
    equations.append("EQ_OBJ")

    #  Fixed Costs
    equations.append("EQ_ANNFIX")

    # Investment component
    equations.append("EQ_ANNINV")

    #  Variable operating costs (including substitution loss in MLF)
    equations.append("EQ_ANNVAR")

    #  Core Equations
    objann = "NO"

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

    if macro == "Yes":
        if nonlp == "NL":
            # MACRO MLF NLP benchmark equations
            equations.extend(
                [
                    "EQ_UTIL",
                    "EQ_PROD_Y",
                    "EQ_AKL",
                    "EQ_LABOR",
                    "EQ_KNCAP",
                    "EQ_MCAP",
                    "EQ_TMC",
                    "EQ_DD",
                    "EQ_IVECBND",
                    "EQ_DNLCES",
                    "EQ_ENSCST",
                    "EQ_TRDBAL",
                ]
            )
        else:
            # MACRO MLF equations
            equations.extend(
                [
                    "EQ_UTILP",
                    "EQ_CONSO",
                    "EQ_CONDA",
                    "EQ_LOGBD",
                    "EQ_MACSH",
                    "EQ_MACAG",
                    "EQ_MACES",
                    "EQ_KNCAP",
                    "EQ_MCAP",
                    "EQ_TMC",
                    "EQ_IVECBND",
                    "EQ_DD",
                    "EQ_DEMSH",
                    "EQ_DEMAG",
                    "EQ_DEMCES",
                    "EQ_ENSCST",
                    "EQ_TRDBAL",
                    # *  "EQ_MPEN",
                    # *  "EQ_XCAPDB"
                ]
            )
    else:
        # MACRO equations
        equations.extend(
            [
                "EQ_UTIL",
                "EQ_CONSO",
                "EQ_DD",
                "EQ_MCAP",
                "EQ_TMC",
                "EQ_IVECBND",
                "EQ_ESCOST",
                "EQ_MPEN",
                "EQ_XCAPDB",
            ]
        )
