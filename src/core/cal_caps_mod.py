# cal_caps_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CAL_CAPS the code for capacity dependent commodity flows regardless of IO
# *   arg1 - Milestone year
# *   arg2 - coefficient expression for EQOBJVAR / UC_FLO
# *   arg3 - TS control index for RPCS_VAR summing
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT derived in COEF_CPT.MOD

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, Sum

from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._algebra.number import Number
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from core.utils import SET_OR_ALIAS
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class CalCapsModConfig:
    """Strongly typed data contract for cal_caps_mod."""

    is_vnret_defined: bool
    varv: tuple[str, ImplicitSet | None]
    sws: tuple[SET_OR_ALIAS, ...] | tuple[()]
    varm: tuple[str, ImplicitSet | None]
    arg1: SET_OR_ALIAS
    # coefficient expression for EQOBJVAR / UC_FLO
    arg2: Condition | Expression | ImplicitParameter | MathOp | Number | Sum
    arg3: SET_OR_ALIAS
    is_output: bool = False  # old arg4, the '.L' suffix


def cal_caps_mod_GP(g: TimesModelClass, config: CalCapsModConfig) -> Sum:
    """GAMSPy counterpart of cal_caps_mod().

    arg1 is the milestone year, arg2 the coefficient expression and arg3 the TS
    control index of the RPCS_VAR summing.
    """
    cc = config
    r, v, p, c, s, ts, io = g.r, g.v, g.p, g.c, g.s, g.ts, g.io

    # SUM(RPCS_VAR(R,P,C,%3), RS_FR(R,TS,S) * %2)
    coefficient = Sum(g.RpcsVar[r, p, c, cc.arg3], g.rs_fr[r, ts, s] * cc.arg2)

    invest_decom = g.coef_icom[r, v, cc.arg1, p, c] + g.coef_ocom[r, v, cc.arg1, p, c]
    # * Flows related to existing capacity over lifetime
    installed = (
        macro.VAR_NCAP_GP(cc.varv, r, v, p, cc.sws, is_output=cc.is_output).where[
            g.t[v]
        ]
        + g.ncap_pasti[r, v, p]
    )
    if cc.is_vnret_defined:
        installed = (
            installed
            - Sum(
                g.Vnret[v, g.Modlyear[cc.arg1]],
                macro.VAR_SCAP_GP(
                    cc.varm, r, v, cc.arg1, p, cc.sws, is_output=cc.is_output
                ),
            ).where[g.PrcRcap[r, p]]
        )

    # *V05c 980923 - use the capacity flow control set
    return Sum(
        Domain(g.Vnt[v, cc.arg1], g.RpcCapflo[r, v, p, c]),
        # *V05b 980902 - need to apply seasonal fraction
        # * Flows related to investment / decommissioning
        (
            invest_decom
            * g.g_yrfr[r, s]
            * (
                macro.VAR_NCAP_GP(
                    cc.varv, r, v, p, cc.sws, is_output=cc.is_output
                ).where[g.Milestonyr[v]]
                + g.ncap_pasti[r, v, p]
            )
            * coefficient
        ).where[invest_decom]
        + Sum(
            Domain(g.RtpCptyr[r, v, cc.arg1, p], io).where[g.ncap_com[r, v, p, c, io]],
            g.coef_cpt[r, v, cc.arg1, p]
            * g.ncap_com[r, v, p, c, io]
            * g.g_yrfr[r, s]
            * installed
            * coefficient
            * (1 + g.coef_cio[r, v, cc.arg1, p, c, io]),
        ),
    )


def cal_caps_mod(
    is_vnret_defined: bool,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    varv: str = "",
    sws: str = "",
    varm: str = "",
) -> str:
    return rf"""
*V05c 980923 - use the capacity flow control set
   SUM((VNT(V,{arg1}),RPC_CAPFLO(R,V,P,C)),
*V05b 980902 - need to apply seasonal fraction
* Flows related to investment / decommissioning
      ((COEF_ICOM(R,V,{arg1},P,C)+COEF_OCOM(R,V,{arg1},P,C)) * G_YRFR(R,S) *
        ({varv}_NCAP{arg4}(R,V,P {sws})$MILESTONYR(V) + NCAP_PASTI(R,V,P)) *
        SUM(RPCS_VAR(R,P,C,{arg3}), RS_FR(R,TS,S) * {arg2}))$(COEF_ICOM(R,V,{arg1},P,C)+COEF_OCOM(R,V,{arg1},P,C)) +
* Flows related to existing capacity over lifetime
      SUM((RTP_CPTYR(R,V,{arg1},P),IO)$NCAP_COM(R,V,P,C,IO),
        COEF_CPT(R,V,{arg1},P) * NCAP_COM(R,V,P,C,IO) * G_YRFR(R,S) *
        ({varv}_NCAP{arg4}(R,V,P {sws})$T(V) + NCAP_PASTI(R,V,P)
{f"-SUM(VNRET(V,MODLYEAR({arg1})),{varm}_SCAP{arg4}(R,V,{arg1},P{sws}))$PRC_RCAP(R,P)" if is_vnret_defined else ""}
        ) * SUM(RPCS_VAR(R,P,C,{arg3}), RS_FR(R,TS,S) * {arg2}) * (1+COEF_CIO(R,V,{arg1},P,C,IO)))
     )
"""
