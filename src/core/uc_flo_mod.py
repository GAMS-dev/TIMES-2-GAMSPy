# uc_flo_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2024 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * UC_FLO the code associated with the flow variable in the EQ_USERCON
# *     - arg1 region summation index
# *     - arg2 period summation index
# *     - arg3 time-slice summation index
# *     - arg4 'T' or 'T+1' index
# *     - arg5 'LHS' or 'RHS'
# *     - arg6 Type of constraint (0=EACH, 1=SUCC or 2=SEVERAL)
# *=============================================================================*
# *UR Questions/Comments:
# *  -

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from gamspy import Domain, Number, Product, Sum
from gamspy.math import Max, Min, abs, power, same_as

from core.cal_caps_mod import CalCapsModConfig, cal_caps_mod_GP
from core.cal_nored_red import cal_nored_red_GP
from core.cal_red_red import CalRedRedConfig, cal_red_red_GP
from core.utils import (
    SET_OR_ALIAS,
    BaseUcModConfig,
    SowGPType,
    extract_var_domain,
    wrap_in_sum,
)
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._algebra.operation import Operation
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class UcFloModConfig(BaseUcModConfig):
    cal_red: Literal["cal_red.red", "cal_nored.red"]
    var: str | tuple[str, Any]
    swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()]
    def_rtp_ffcs: bool
    sow: SowGPType
    cufscal: int
    pgprim: str
    sws: tuple[Set | Alias, ...] | tuple[()]
    varm: tuple[str, ImplicitSet | None]
    varv: tuple[str, ImplicitSet | None]
    is_vnret_defined: bool
    arg8: ImplicitSet | ImplicitParameter | Expression | None
    # %VAR%/%SOW% are replaced by %9/%10 for arg6 == "1"
    arg9: tuple[Any, Any]
    arg10: (
        SET_OR_ALIAS
        | Condition
        | tuple[Condition | ImplicitSet, ImplicitParameter]
        | None
    ) = None


def uc_flo_mod(g: TimesModelClass, config: UcFloModConfig) -> Expression | Sum:
    cc = config
    r, v, p, c, s, ts, sl = g.r, g.v, g.p, g.c, g.s, g.ts, g.sl
    ucn, t, ll, cur, allyear = g.ucn, g.t, g.ll, g.cur, g.allyear

    var, sow = cc.var, cc.sow
    if cc.arg6 == 1:
        var, sow = cc.arg9

    uc_flo = g.uc_flo[ucn, cc.arg5, r, cc.arg7, p, c, ts]
    uc_perds = g.UcAttr[r, ucn, cc.arg5, "FLO", g.UcPerds]

    # * [UR] model reduction REDUCE is set in *.run
    cal_red_config = CalRedRedConfig(
        var=var,
        sow=sow,
        pgprim=cc.pgprim,
        def_rtp_ffcs=cc.def_rtp_ffcs,
        arg1=c,
        arg2=g.Com,
        arg3=ts,
        arg4=p,
        arg5=cc.arg4,
        arg10=Number(1),
    )
    if cc.cal_red == "cal_red.red":
        include_cal_red = cal_red_red_GP(g=g, config=cal_red_config)
    elif cc.cal_red == "cal_nored.red":
        include_cal_red = cal_nored_red_GP(g=g, config=cal_red_config)
    else:
        raise ValueError(f"Unexpected value for cal_red: {cc.cal_red}")

    include_cal_caps = cal_caps_mod_GP(
        g=g,
        config=CalCapsModConfig(
            is_vnret_defined=cc.is_vnret_defined,
            varv=cc.varv,
            sws=cc.sws,
            varm=cc.varm,
            arg1=cc.arg4,
            arg2=uc_flo,
            arg3=ts,
        ),
    )

    def flow_costs(index: Set | Alias) -> Sum:
        """The UC_COST attributes, priced with the objective cost coefficients."""
        return Sum(
            Domain(g.Rdcur[r, cur], g.TsAnn[index, sl]),
            macro.obj_fcost_GP(r, cc.arg4, p, c, sl, cur).where[
                g.UcAttr[r, ucn, cc.arg5, "FLO", "COST"]
            ]
            + macro.obj_fdelv_GP(r, cc.arg4, p, c, sl, cur).where[
                g.UcAttr[r, ucn, cc.arg5, "FLO", "DELIV"]
            ]
            + Min(0, macro.obj_ftax_GP(r, cc.arg4, p, c, sl, cur)).where[
                g.UcAttr[r, ucn, cc.arg5, "FLO", "SUB"]
            ]
            + Max(0, macro.obj_ftax_GP(r, cc.arg4, p, c, sl, cur)).where[
                g.UcAttr[r, ucn, cc.arg5, "FLO", "TAX"]
            ],
        )

    # PROD(REG(R)$SUM(UC_ATTR(R,UC_N,%5,'FLO',UC_COST),1), ...)
    def cost_term(inner: Expression | Operation) -> Product:
        return Product(
            g.Reg[r].where[Sum(g.UcAttr[r, ucn, cc.arg5, "FLO", g.UcCost], 1)], inner
        )

    # *V0.9a S reference should be TS
    flow_term = (
        include_cal_red
        * uc_flo
        # *GG* use the derived multipier
        # * [AL] PROD operator is useful here, but must be activated due to a GAMS bug:
        * Product(g.Annual, 1)
        * Product(
            g.RsBelow[r, ts, s],
            g.rs_fr[r, s, ts]
            * (1 + macro.rtcs_fr.rtcs_fr_GP(r, cc.arg4, c, s, ts, sow=sow)),
        )
    )
    capflo_term: Expression | Sum = include_cal_caps
    if cc.arg6 == 1:
        arg8_rep = 1 if cc.arg8 is None else cc.arg8
        growth_attr = g.UcAttr[r, ucn, cc.arg5, "FLO", "GROWTH"]
        pwr_term = power(abs(uc_flo), arg8_rep * g.uc_sign[cc.arg5] - 1)

        flow_term *= Product(growth_attr, pwr_term)
        capflo_term *= Product(
            growth_attr, Sum(g.RpcsVar[r, p, c, ts], g.rs_fr[r, ts, s] * pwr_term)
        )

    flow_term *= Product(
        uc_perds,
        g.fpd[cc.arg4]
        * Product(
            g.UcNewflo[g.UcPerds],
            Number(1).where[same_as(v, cc.arg4) + g.Rvpt[r, v, p, cc.arg4]]
            / g.fpd[cc.arg4],
        ),
    ) * cost_term(flow_costs(ts))

    capflo_term *= Product(
        uc_perds, g.fpd[cc.arg4].where[~g.UcNewflo[g.UcPerds]]
    ) * cost_term(Sum(g.RpcsVar[r, p, c, ts], g.rs_fr[r, ts, s] * flow_costs(ts)))

    term: Expression | Sum = Sum(
        Domain(g.RtpVintyr[r, v, cc.arg4, p], g.RtpcsVarf[r, cc.arg4, p, c, ts]).where[
            g.UcMapFlo[ucn, cc.arg5, r, p, c] & g.rs_fr[r, s, ts]
        ],
        wrap_in_sum(target=flow_term, domain=cc.arg10),
    ) + Sum(g.UcCapflo[ucn, cc.arg5, r, p, c], capflo_term)

    term = wrap_in_sum(target=term, domain=cc.arg3)

    if cc.arg6 == "S":
        term = 1 / g.g_yrfr[r, s] * term
    elif cc.arg6 == 2:
        discount_adj = (
            g.fpd[t]
            + (g.coef_pvt[r, t] - g.fpd[t]).where[
                g.UcAttr[r, ucn, "LHS", "FLO", "PERDISC"]
            ]
            - 1
        ).where[g.UcDt[r, ucn]]
        term = (1 + discount_adj) * term

    args_to_sum = [arg for arg in [cc.arg2, cc.arg1] if arg is not None]
    for arg in args_to_sum:
        term = wrap_in_sum(target=term, domain=arg)

    if cc.arg6 != 2:
        return term

    # * Add Cumflos
    var_id, domain = extract_var_domain(var)
    var_cumflo = wrap_in_sum(
        target=macro.VAR_CUMFLO_GP(var_id, r, p, c, allyear, ll, cc.swt), domain=domain
    )
    cumflo_region = (cc.arg8,) if cc.arg8 is not None else ()

    cumflo_sum = Sum(
        Domain(*cumflo_region, g.RpcCumflo[r, p, c, allyear, ll]).where[
            g.uc_cumflo[ucn, r, p, c, allyear, ll]
        ],
        g.uc_cumflo[ucn, r, p, c, allyear, ll] * var_cumflo * cc.cufscal,
    )

    return term + cumflo_sum
