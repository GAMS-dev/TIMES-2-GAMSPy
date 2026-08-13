# eqpk_ect_ier.py
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * [UR]: 04/22/2003: adjustment for extraction condensing CHP plants

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Number, Sum

from core.cal_fflo_mod import CalFfloModConfig, cal_fflo_mod_GP

if TYPE_CHECKING:
    from gamspy import Alias, Set, Variable
    from gamspy._symbols.implicits import ImplicitSet, ImplicitVariable

    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def eqpk_ect_ier_GP(
    g: TimesModelClass,
    varv: tuple[str, ImplicitSet | None],
    sws: tuple[Set | Alias, ...] | tuple[()],
    # args for cal_fflo_mod_GP
    reduce: str,
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
    var: str,
    pgprim: str,
    is_rtp_ffcs_defined: bool,
) -> Sum:
    """GAMSPy counterpart of eqpk_ect_ier()."""
    r, v, t, p, c, s = g.r, g.v, g.t, g.p, g.c, g.s
    # ECT_CHP / ECT_ELC are declared by initmty.ier
    varv_id, varv_set = varv
    VARV_NCAP: Variable = g.get_variable(f"{varv_id}_NCAP")

    include_cal_fflo = cal_fflo_mod_GP(
        g=g,
        config=CalFfloModConfig(
            reduce=reduce,
            sow=sow,
            var=var,
            pgprim=pgprim,
            is_rtp_ffcs_defined=is_rtp_ffcs_defined,
            arg1="OUT",
            # arg2 = "O" in cal_fflo_mod stated as no longer used
            arg3=(-(g.ncap_pkcnt[r, v, p, s] ** g.rpc_pkf[r, p, c])).where[
                g.rpc_pkf[r, p, c]
            ],
            arg4=Number(1),
        ),
    )

    ncap: ImplicitVariable | Sum = VARV_NCAP[r, v, p, *sws]
    if varv_set is not None:
        ncap = Sum(varv_set, ncap)

    return Sum(
        g.EctElc[g.EctChp[r, p], c].where[
            # NB: in GAMS `not` binds looser than `*`, so NOT A*B means NOT (A*B)
            (~(g.PrcCap[r, p] * g.RpcPkc[r, p, c])).where[g.Top[r, p, c, "OUT"]]
        ],
        include_cal_fflo
        + g.g_yrfr[r, s]
        * Sum(
            g.RtpCptyr[r, v, t, p],
            g.prc_capact[r, p]
            * g.ncap_pkcnt[r, v, p, s]
            * g.coef_cpt[r, v, t, p]
            * (
                ncap.where[g.Milestonyr[v]] + g.ncap_pasti[r, v, p].where[g.Pastyear[v]]
            ),
        ),
    )
