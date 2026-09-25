# eqcapact_mod.py

# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQCAPACT is the capacity utilization equation
# *   %1 - equation declaration type
# *   %2 - bound type for %1
# *=============================================================================*
# * Questions/Comments:
# *  - COEF_CPT is defined in COEF_CPT.MOD
# *  - COEF_AF established by applying SHAPE in COEF_CPT.MOD
# *  - Commodity-specific AF handled by EQ(l)_CAFLAC (VDA extension)
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Alias, Expression, Loop, Number, Set, Sum
from gamspy._algebra.condition import Condition
from gamspy._symbols.implicits import ImplicitSet
from gamspy.math import exp, power

from core.base_class import GamsClass
from core.utils import generate_equation
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqcapactModConfig:
    """Strongly typed data contract replacing legacy positional batch-include loops."""

    sense: Literal["G", "E", "L"]
    bound_type: Literal["LO", "FX", "UP"]
    arg3: Sum | Expression | tuple[Set | Alias | str, ...] | tuple[()]


class EqcapactMod(GamsClass):
    """Translation unit for eqcapact.mod."""

    # Instance attributes
    module_name: str = "eqcapact_mod"
    gams_source: str = "eqcapact.mod"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqcapactModConfig
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        pass_var = (
            ~g.RpsCaflac[g.r, g.p, g.s, self.config.bound_type]
            if self.tc.defined("RPS_CAFLAC")
            else Number(1)
        )

        g.Afs = Set(m, name="AFS", domain=[g.r, g.t, g.p, g.s, g.bd])

        self.tc.enqueue(
            self.exec,
            validate=(self.env.validate == "YES"),
            eq=self.env.eq,
            var=self.env.var,
            varv=self.env.varv_GP,
            varm=self.env.varm_GP,
            pass_var=pass_var,
            sws=self.env.sws_GP,
            swt=self.env.swt_GP,
            sow=self.env.sow_GP,
            r_v_t=self.env.r_v_t_GP,
            rcapsbm=self.env.rcapsbm_GP,
            rcapsub=self.env.rcapsub_GP,
            sense=self.config.sense,
            arg2=self.config.bound_type,
            arg3=self.config.arg3,
        )

    def exec(
        self: EqcapactMod,
        validate: bool,
        eq: str,
        var: str,
        varv: tuple[str, ImplicitSet | None],
        varm: tuple[str, ImplicitSet | None],
        pass_var: Expression | Number,
        sws: tuple[Set | Alias, ...] | tuple[()],
        swt: tuple[Set | Alias, ...] | tuple[()],
        sow: tuple[Literal["0", "1"] | Set | Alias] | tuple[()],
        r_v_t: tuple[Set | Alias | ImplicitSet, ...],
        rcapsbm: Condition | Number,
        rcapsub: Expression | Number,
        sense: Literal["G", "E", "L"],
        arg2: Literal["LO", "FX", "UP"],
        arg3: Sum | Expression | tuple[Set | Alias | str, ...] | tuple[()],
    ) -> None:
        g = self.tc
        (
            Modlyear,
            coef_cpt,
            r,
            t,
            p,
            coef_af,
            s,
            ncap_pasti,
            Pastyear,
            prc_capact,
        ) = (
            g.Modlyear,
            g.coef_cpt,
            g.r,
            g.t,
            g.p,
            g.coef_af,
            g.s,
            g.ncap_pasti,
            g.Pastyear,
            g.prc_capact,
        )
        PrcTs, ts, v, TsMap, RpStg, rs_fr, prc_sc, rs_stgprd = (
            g.PrcTs,
            g.ts,
            g.v,
            g.TsMap,
            g.RpStg,
            g.rs_fr,
            g.prc_sc,
            g.rs_stgprd,
        )
        RtpVintyr, PrcVint, g_yrfr = g.RtpVintyr, g.PrcVint, g.g_yrfr
        Afs, RtpVara, bd, RtpsOff = g.Afs, g.RtpVara, g.bd, g.RtpsOff

        VAR_ACT = g.get_variable(f"{var}_ACT")
        eqe_capact = g.get_equation(f"{eq}{sense}_CAPACT")

        if not validate:
            rhs_start = (
                Sum(
                    Modlyear.where[coef_cpt[r, Modlyear, t, p]],
                    coef_cpt[r, Modlyear, t, p]
                    * macro.coef_af_mx.coef_af_GP(arg3, r, Modlyear, t, p, s, arg2)
                    * (
                        macro.VAR_NCAP_GP(varm, r, Modlyear, p, sws).where[t[Modlyear]]
                        + ncap_pasti[r, Modlyear, p].where[Pastyear[Modlyear]]
                        + rcapsbm
                    ),
                )
                * prc_capact[r, p]
            )
        else:
            rhs_start = (
                coef_af[r, t, t, p, s, arg2]
                * prc_capact[r, p]
                * macro.VAR_CAP_GP(var, r, t, p, sow)
            )

        if sense == "L":
            # COEF_AFs are always at PRC_TS or above, can be directly used for testing:
            with Loop(v):
                Afs[RtpVara[r, t, p], s, bd].where[coef_af[r, v, t, p, s, bd]] = True

            Afs[RtpsOff, bd] = False

        eqe_capact[RtpVintyr[*r_v_t, p], s, *swt].where[
            Afs[r, t, p, s, arg2] * pass_var
        ] = generate_equation(
            # normal processes
            Sum(
                PrcTs[r, p, ts].where[TsMap[r, s, ts]], VAR_ACT[r, v, t, p, ts, *sow]
            ).where[~RpStg[r, p]]
            # storage: parent timeslice fraction of the number of storage cycles in a year
            + Sum(
                PrcTs[r, p, ts].where[rs_fr[r, ts, s]],
                (
                    VAR_ACT[r, v, t, p, ts, *sow]
                    + macro.var_sts.render_GP(r, v, t, p, ts, arg2)
                )
                * rs_fr[r, ts, s]
                * exp(prc_sc[r, p])
                / rs_stgprd[r, ts],
            ).where[RpStg[r, p]],
            sense,
            (
                rhs_start.where[~PrcVint[r, p]]
                + (
                    # process is vintaged
                    macro.coef_af_mx.coef_af_GP(arg3, r, v, t, p, s, arg2)
                    * coef_cpt[r, v, t, p]
                    * prc_capact[r, p]
                    * (
                        macro.VAR_NCAP_GP(varv, r, v, p, sws).where[t[v]]
                        + ncap_pasti[r, v, p].where[Pastyear[v]]
                        + rcapsub
                    )
                ).where[PrcVint[r, p]]
            )
            * power(
                g_yrfr[r, s], 1 - (Number(1)).where[RpStg[r, p]]
            ),  # capacity of storage process fully available in each time slice)
        )
