# bnd_set_mod.py
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
#  This file is part of the IEA-ETSAP TIMES model generator, licensed
#  under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# =============================================================================*
#  BND_SET.MOD set the actual bounds on variables
#   %1 - variable reference
#   %2 - primary index into variable
#   %3 - qualifier/bound expression
#   %4 - control index
#   %5 - stochastic qualifier
# =============================================================================*
# GaG Questions/Comments:
#   - FX take precedence as is set last!!!
#   - take primary index loop control criteria too, or reset all in case change
#     in data (e.g., process moves from 1 region to another?) LATTER!!!
# -----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Number, SpecialValues, sparse

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SET_OR_ALIAS, SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def bnd_set_mod_GP(
    *,
    g: TimesModelClass,
    variable_name: str,  # is bnd_set.mod's own %1
    primary_domain: tuple[SET_OR_ALIAS, ...],  # is bnd_set.mod's own %2
    bound_param_name: str,  # is bnd_set.mod's own %3
    control_domain: tuple[SET_OR_ALIAS, ...],  # is bnd_set.mod's own %4
    extra_condition: Condition
    | Expression
    | ImplicitSet
    | Number,  # is bnd_set.mod's own %5
    arg6: str = "",  # is bnd_set.mod's own %6
    swd: tuple[Set | Alias] | tuple[()],
    sow: SowGPType,
    stages: str,
    stochastic_symbol_declared: bool,
) -> None:
    """GAMSPy twin of :func:`bnd_set_mod`."""
    if arg6 == "":
        stop = stages != "YES"
    elif arg6 == "I":
        stop = stages.upper() != "YES"
    else:
        raise ValueError(f"Unhandled argument arg6={arg6!r} passed.")

    variable = g.get_variable(variable_name)
    bound_param = g.get_parameter(bound_param_name)

    # reset any existing bounds
    variable.lo[*primary_domain, *swd] = 0
    variable.up[*primary_domain, *swd] = SpecialValues.POSINF

    # assign from user data
    variable.lo[*control_domain, *sow].where[extra_condition] = sparse(
        bound_param[*primary_domain, "LO"]
    )
    variable.up[*control_domain, *sow].where[extra_condition] = sparse(
        bound_param[*primary_domain, "UP"]
    )
    variable.fx[*control_domain, *sow].where[extra_condition] = sparse(
        bound_param[*primary_domain, "FX"]
    )

    if stop or not stochastic_symbol_declared:
        return

    # Stochastic bounds
    stochastic_param = g.get_parameter(f"S_{bound_param_name}")
    Sow = g.Sow
    variable.lo[*control_domain, *sow].where[extra_condition] = sparse(
        stochastic_param[*primary_domain, "LO", "1", Sow]
    )
    variable.up[*control_domain, *sow].where[extra_condition] = sparse(
        stochastic_param[*primary_domain, "UP", "1", Sow]
    )
    variable.fx[*control_domain, *sow].where[extra_condition] = sparse(
        stochastic_param[*primary_domain, "FX", "1", Sow]
    )


def bnd_set_mod(
    *,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
    arg6: str = "",
    stages: str,
    swd: str,
    sow: str,
    stochastic_symbol_declared: bool,
) -> str:
    if arg6 == "":
        stop = stages != "YES"
    elif arg6 == "I":
        stop = stages.upper() != "YES"
    else:
        raise ValueError(f"Unhandled argument arg6={arg6!r} passed.")

    return rf"""
* reset any existing bounds
  {arg1}.LO({arg2}{swd}) = 0;
  {arg1}.UP({arg2}{swd}) = INF;
* assign from user data
  {arg1}.LO({arg4}{sow}){arg5}  $=  {arg3}({arg2},'LO');
  {arg1}.UP({arg4}{sow}){arg5}  $=  {arg3}({arg2},'UP');
  {arg1}.FX({arg4}{sow}){arg5}  $=  {arg3}({arg2},'FX');
{
        rf'''
*-----------------------------------------------------------------------------
* Stochastic bounds
  {arg1}.LO({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'LO','1',SOW);
  {arg1}.UP({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'UP','1',SOW);
  {arg1}.FX({arg4}{sow}){arg5}  $=  S_{arg3}({arg2},'FX','1',SOW);
'''
        if not stop and stochastic_symbol_declared
        else ""
    }
"""
