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

from gamspy import Equation

from core.mod_equa_mod import core_equations
from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def mod_equa_tm(
    tc: TimesModelClass,
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
) -> list[Equation]:
    """Translation unit for mod_equa.tm."""
    equations = []
    if merge.upper() == "YES":
        return tc.container.getEquations()  # type: ignore[no-any-return]

    # Objective Function & Components
    #  Overall OBJ linear combination of the regional objs (which are built from rest)
    equations.append(tc.eq_obj)

    #  Fixed Costs
    equations.append(tc.eq_annfix)

    # Investment component
    equations.append(tc.eq_anninv)

    #  Variable operating costs (including substitution loss in MLF)
    equations.append(tc.eq_annvar)

    #  Core Equations
    objann = "NO"

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

    if macro == "Yes":
        if nonlp == "NL":
            # MACRO MLF NLP benchmark equations
            equations.extend(
                [
                    tc.eq_util,
                    tc.eq_prod_y,
                    tc.eq_akl,
                    tc.eq_labor,
                    tc.eq_kncap,
                    tc.eq_mcap,
                    tc.eq_tmc,
                    tc.eq_dd,
                    tc.eq_ivecbnd,
                    tc.eq_dnlces,
                    tc.eq_enscst,
                    tc.eq_trdbal,
                ]
            )
        else:
            # MACRO MLF equations
            equations.extend(
                [
                    tc.eq_utilp,
                    tc.eq_conso,
                    tc.eq_conda,
                    tc.eq_logbd,
                    tc.eq_macsh,
                    tc.eq_macag,
                    tc.eq_maces,
                    tc.eq_kncap,
                    tc.eq_mcap,
                    tc.eq_tmc,
                    tc.eq_ivecbnd,
                    tc.eq_dd,
                    tc.eq_demsh,
                    tc.eq_demag,
                    tc.eq_demces,
                    tc.eq_enscst,
                    tc.eq_trdbal,
                    # *  "EQ_MPEN",
                    # *  "EQ_XCAPDB"
                ]
            )
    else:
        # MACRO equations
        equations.extend(
            [
                tc.eq_util,
                tc.eq_conso,
                tc.eq_dd,
                tc.eq_mcap,
                tc.eq_tmc,
                tc.eq_ivecbnd,
                tc.eq_escost,
                tc.eq_mpen,
                tc.eq_xcapdb,
            ]
        )

    return equations
