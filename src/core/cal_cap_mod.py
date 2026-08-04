# cal_cap_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_CAP the code for capacity dependent commodity flows in EQ_COMxxx
# *   arg1 - IN/OUT indicator
# *   arg2 - I/O indicator
# *   arg3 - cost expression for EQOBJVAR
# *=============================================================================*
# *GaG Questions/Comments:
# *  - COEF_CPT derived in COEF_CPT.MOD

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Sum

if TYPE_CHECKING:
    from gamspy import Alias, Parameter, Set, Variable
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._algebra.number import Number
    from gamspy._symbols.implicits import ImplicitSet, ImplicitVariable

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CalCapModConfig:
    """Strongly typed data contract for cal_cap_mod."""

    varv: tuple[str, ImplicitSet | None]
    sws: tuple[Set | Alias, ...] | tuple[()]
    rcapsub: Condition | Expression | Number
    arg1: Literal["IN", "OUT"]
    arg2: Literal["I", "O"]
    arg3: Condition | Expression | Number  # default Number(1)
    arg4: str = ""


def cal_cap_mod_GP(
    g: TimesModelClass, config: CalCapModConfig
) -> Expression | ImplicitSet:
    """GAMSPy counterpart of cal_cap_mod().

    arg3 is the cost expression for EQOBJVAR and arg4 a suffix of the NCAP variable.
    """
    cc = config
    r, v, t, p, c, s = g.r, g.v, g.t, g.p, g.c, g.s
    varv_id, varv_set = cc.varv
    VARV_NCAP: Variable = g.get_variable(f"{varv_id}_NCAP{cc.arg4}")
    coef_com: Parameter = g.get_parameter(f"COEF_{cc.arg2}COM")

    def capacity(with_rcapsub: bool) -> Expression | ImplicitSet:
        ncap: ImplicitVariable | Sum = VARV_NCAP[r, v, p, *cc.sws]
        if varv_set is not None:
            ncap = Sum(varv_set, ncap)
        installed = ncap.where[g.t[v]] + g.ncap_pasti[r, v, p].where[g.Pastyear[v]]
        return installed + cc.rcapsub if with_rcapsub else installed

    return Sum(
        g.RtpCptyr[r, v, t, p].where[g.ncap_com[r, v, p, c, cc.arg1]],
        # *V05b 980902 - need to apply seasonal fraction
        g.coef_cpt[r, v, t, p]
        * g.ncap_com[r, v, p, c, cc.arg1]
        * g.g_yrfr[r, s]
        * capacity(with_rcapsub=True)
        * cc.arg3
        # * Adjust for lagged commodity flows
        * (1 + g.coef_cio[r, v, t, p, c, cc.arg1]),
        # * CAL_NCOM: the term associated with invest/decommission commodities in the EQ_COMxxx
    ) + Sum(
        g.RpcCapflo[r, v, p, c].where[coef_com[r, v, t, p, c]],
        coef_com[r, v, t, p, c]
        * g.g_yrfr[r, s]
        * capacity(with_rcapsub=False)
        * cc.arg3,
    )


def cal_cap_mod(
    varv: str,
    sws: str,
    rcapsub: str,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
) -> str:
    """Translation unit for cal_cap.mod."""
    return rf"""
         SUM(RTP_CPTYR(R,V,T,P)$NCAP_COM(R,V,P,C,'{arg1}'),
*V05b 980902 - need to apply seasonal fraction
             COEF_CPT(R,V,T,P) * NCAP_COM(R,V,P,C,'{arg1}') * G_YRFR(R,S) *
             {arg3}
             ({varv}_NCAP{arg4}(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P)$PASTYEAR(V) {rcapsub}) *
* Adjust for lagged commodity flows
             (1 + COEF_CIO(R,V,T,P,C,'{arg1}'))
         ) +
* CAL_NCOM: the term associated with invest/decommission commodities in the EQ_COMxxx
         SUM(RPC_CAPFLO(R,V,P,C)$COEF_{arg2}COM(R,V,T,P,C), COEF_{arg2}COM(R,V,T,P,C) *
             {arg3}
             G_YRFR(R,S) * ({varv}_NCAP{arg4}(R,V,P {sws})$T(V)+NCAP_PASTI(R,V,P)$PASTYEAR(V))
         )
"""
