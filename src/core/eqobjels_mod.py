# eqobjels_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJELS the objective function flexible demand utility
# *=============================================================================*
# *GaG Questions/Comments:
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Ord, Sum
from gamspy.math import Max, ceil

from core.base_class import GamsClass
from core.pp_micro_mod import PpMicroMod
from core.utils import extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Set
    from gamspy._algebra.condition import Condition
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqobjelsMod(GamsClass):
    """Translation unit for eqobjels.mod."""

    # Instance attributes
    module_name: str = "eqobjels_mod"
    gams_source: str = "eqobjels.mod"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        is_micro = self.env.micro.upper() == "YES"
        if is_micro:
            self.include(PpMicroMod(self.tc, self.env, arg1="NLP"))
        self.comp1(
            eq=self.env.eq,
            sow=self.env.sow_GP,
            vart=self.env.vart_GP,
            sws=self.env.sws_GP,
            var=self.env.var,
            r_t=self.env.r_t_GP,
            swt=self.env.swt_GP,
            mx=self.env.mx_GP,
            is_micro=is_micro,
        )

    def comp1(
        self: EqobjelsMod,
        eq: str,
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        mx: Sum | Condition | Expression | tuple[Set | Alias | str, ...] | tuple[()],
        is_micro: bool,
    ) -> None:
        g = self.tc

        eq_objels = g.get_equation(name=f"{eq}_OBJELS")
        eq_l_comces = g.get_equation(name=f"{eq}L_COMCES")
        vart_id, vart_set = extract_var_domain(vart)
        var_id, var_set = extract_var_domain(var)

        vart_suffixes = ["ELAST", "DEM"]

        VART_ELAST, VART_DEM = [
            wrap_in_sum(
                target=g.get_variable(name=f"{vart_id}_{suffix}"), domain=vart_set
            )
            for suffix in vart_suffixes
        ]

        var_suffixes = ["OBJELS", "ELAST", "COMPRD"]

        VAR_OBJELS, VAR_ELAST, VAR_COMPRD = [
            wrap_in_sum(
                target=g.get_variable(name=f"{var_id}_{suffix}"), domain=var_set
            )
            for suffix in var_suffixes
        ]
        # * Micro NLP formulation (only when pp_micro.mod NLP was included)
        if is_micro:
            conditional_nlp: Condition | int = Sum(
                g.t.where[(Ord(g.t) > 1.0)],
                g.coef_pvt[g.r, g.t]
                * Sum(
                    g.Dem[g.r, g.c].where[
                        (g.mi_elasp[g.r, g.t, g.c].where[g.rd_nlp[g.r, g.c]])
                    ],
                    g.mi_ccons[g.r, g.t, g.c]
                    * (
                        (
                            VART_DEM[g.r, g.t, g.c, *sws] ** g.mi_elasp[g.r, g.t, g.c]
                        ).where[(g.rd_nlp[g.r, g.c] == 1.0)]
                        + (
                            (
                                Sum(
                                    g.MiDmas[g.r, g.c, g.Com],
                                    (
                                        g.rd_shar[g.r, g.t, g.c, g.Com]
                                        ** (1.0 / g.mi_esub[g.r, g.t, g.c])
                                    )
                                    * (
                                        (
                                            g.com_agg[g.r, g.t, g.Com, g.c]
                                            * VART_DEM[g.r, g.t, g.Com, *sws]
                                        )
                                        ** g.mi_rho[g.r, g.t, g.c]
                                    ),
                                )
                                ** (1.0 / g.mi_rho[g.r, g.t, g.c])
                            )
                            ** g.mi_elasp[g.r, g.t, g.c]
                        ).where[(g.rd_nlp[g.r, g.c] > 2.0)]
                        - (g.ddf_qref[g.r, g.t, g.c] ** g.mi_elasp[g.r, g.t, g.c])
                    ).where[(g.rd_nlp[g.r, g.c] > 0.0)],
                ),
            ).where[g.Lnx[g.bd]]
        else:
            conditional_nlp = 0

        # *------------------------------------------------------------------------------
        # * Direction with bound sign BDSIG
        # *------------------------------------------------------------------------------
        # *V0.5b 980824 - correct ORD adjustment
        eq_objels[g.r, g.bd, g.cur, *sow].where[
            (g.Rdcur[g.r, g.cur].where[g.sum_obj[g.r, "OBJELS"]])
        ] = (
            Sum(
                g.RtcsVarc[g.r, g.t, g.c, g.s].where[
                    (
                        g.com_elast[g.r, g.t, g.c, g.s, g.bd].where[
                            g.com_step[g.r, g.c, g.bd]
                        ]
                    )
                ],
                g.coef_pvt[g.r, g.t]
                * g.com_bprice[g.r, g.t, g.c, g.s, g.cur]
                * (
                    Sum(
                        g.Rcj[g.r, g.c, g.j, g.bd],
                        VART_ELAST[g.r, g.t, g.c, g.s, g.j, g.bd, *sws]
                        * (
                            (
                                1.0
                                - g.bdsig[g.bd]
                                * (Ord(g.j) - 0.5)
                                * g.com_voc[g.r, g.t, g.c, g.bd]
                                / g.com_step[g.r, g.c, g.bd]
                            )
                            ** (1.0 / g.com_elast[g.r, g.t, g.c, g.s, g.bd])
                        ),
                    ).where[(~(g.com_elastx[g.r, g.t, g.c, g.bd]))]
                    # * Shaped elasticities
                    + Sum(
                        g.RtcShed[g.r, g.t, g.c, g.bd, g.jj[g.age]],
                        Sum(
                            Domain(
                                g.Rcj[g.r, g.c, g.j, g.bd],
                                g.span[
                                    g.age
                                    + ceil(
                                        (Ord(g.j) - 0.5)
                                        * g.com_voc[g.r, g.t, g.c, g.bd]
                                        / g.com_step[g.r, g.c, g.bd]
                                        * 100.0
                                        - Ord(g.age)
                                    )
                                ],
                            ),
                            (
                                (
                                    g.shaped[g.bd, g.jj, g.span]
                                    * (
                                        (
                                            (
                                                1.0
                                                - g.bdsig[g.bd]
                                                * (Ord(g.j) - 0.5)
                                                * g.com_voc[g.r, g.t, g.c, g.bd]
                                                / g.com_step[g.r, g.c, g.bd]
                                            )
                                            / g.shaped[g.bd, "1", g.span]
                                        )
                                        ** (1.0 / Max(0.001, g.shape[g.jj, g.span]))
                                    )
                                )
                                ** (1.0 / g.com_elast[g.r, g.t, g.c, g.s, g.bd])
                            )
                            * VART_ELAST[g.r, g.t, g.c, g.s, g.j, g.bd, *sws],
                        ),
                    )
                    + Sum(
                        g.MiDmas[g.r, g.Com, g.c].where[g.mi_dope[g.r, g.t, g.c]],
                        Sum(
                            g.Rcj[g.r, g.c, g.j, g.bd],
                            VART_ELAST[g.r, g.t, g.c, g.s, g.j, g.bd, *sws]
                            * g.mi_agc[g.r, g.t, g.Com, g.c, g.j, g.bd],
                        ),
                    )
                ),
            ).where[g.Bdneq[g.bd]]
            # * Micro NLP formulation
            + conditional_nlp
            == VAR_OBJELS[g.r, g.bd, g.cur, *sow]
        )

        # *------------------------------------------------------------------------------
        # * Step bounds for linear CES demand functions
        eq_l_comces[g.Rtc[*r_t, g.Com], g.c, g.s, *swt].where[
            (
                g.RtcsVarc[g.r, g.t, g.c, g.s].where[
                    (g.mi_dope[g.r, g.t, g.c].where[g.MiDmas[g.r, g.Com, g.c]])
                ]
            )
        ] = (
            Sum(
                g.Rcj[g.r, g.c, g.j, g.Bdneq[g.bd]].where[
                    g.com_elast[g.r, g.t, g.c, g.s, g.bd]
                ],
                VAR_ELAST[g.r, g.t, g.c, g.s, g.j, g.bd, *sow]
                * g.com_step[g.r, g.c, g.bd]
                / Ord(g.j)
                / (
                    g.ddf_qref[g.r, g.t, g.c]
                    * macro.com_fr.com_fr_GP(mx, g.r, g.t, g.c, g.s)
                    * g.com_voc[g.r, g.t, g.c, g.bd]
                ),
            )
            <= VAR_COMPRD[g.r, g.t, g.Com, "ANNUAL", *sow] / g.ddf_qref[g.r, g.t, g.Com]
        )
