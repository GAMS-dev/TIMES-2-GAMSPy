# eqchpelc_ier.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * Equation bounding the electricity production of extraction condensing CHP plant
# * by the available condensing resp. backpressure capacity
# *   sense - =L= or =E= qualifier
# *   arg2  - UP of FX bound for ECT_AFCON/ECT_AFCHP
# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import Number, Sum

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import EquationSenseTypes, generate_equation, wrap_in_sum

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqchpelcIerConfig:
    """Strongly typed data contract replacing the positional batch-include args."""

    sense: EquationSenseTypes
    arg2: Literal["UP", "FX"]


class EqchpelcIer(GamsClass):
    """Translation unit for eqchpelc.ier."""

    # Instance attributes
    module_name: str = "eqchpelc_ier"
    gams_source: str = "eqchpelc.ier"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqchpelcIerConfig,
    ):
        self.env = env.fork()
        self._sub_modules: dict[str, GamsClass] = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc
        cc = self.config

        r, v, t, p, c, ts, k = g.r, g.v, g.t, g.p, g.c, g.ts, g.k
        Com, Modlyear = g.Com, g.Modlyear
        RtpVintyr, RtpCptyr, RtpcsVarf = g.RtpVintyr, g.RtpCptyr, g.RtpcsVarf
        EctChp, EctElc, EctDht = g.EctChp, g.EctElc, g.EctDht
        coef_cpt, prc_capact, ncap_pasti = g.coef_cpt, g.prc_capact, g.ncap_pasti

        var = self.env.var
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        swx = self.env.swx_GP
        swtx = self.env.swtx_GP
        pgprim = self.env.pgprim
        is_rtp_ffcs_defined = self.tc.defined("RTP_FFCS")

        varm_id, varm_set = self.env.varm_GP
        varv_id, varv_set = self.env.varv_GP
        VARM_NCAP = g.get_variable(f"{varm_id}_NCAP")
        VARV_NCAP = g.get_variable(f"{varv_id}_NCAP")

        cal_red = self.env.cal_red
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        # $BATINCLUDE %cal_red% C COM TS P T
        # [UR] model reduction %REDUCE% is set in *.run
        include_cal_red: Condition | Expression | ImplicitSet | Sum = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=c,
                arg2=Com,
                arg3=ts,
                arg4=p,
                arg5=t,
                arg10=Number(1),
                pgprim=pgprim,
                def_rtp_ffcs=is_rtp_ffcs_defined,
                sow=sow,
                var=var,
            ),
        )

        # Electricity produced, and the heat it displaces at the backpressure ratio
        electricity = Sum(
            RtpcsVarf[r, t, p, c, ts].where[EctElc[r, p, c]], include_cal_red
        )
        heat = Sum(
            RtpcsVarf[r, t, p, c, ts].where[EctDht[r, p, c]],
            g.ect_reh[r, t, p] * include_cal_red,
        )

        def available_capacity(
            availability: str, conversion: str
        ) -> Expression | Condition:
            """RHS of both equations: installed capacity in the given CHP mode.

            `availability` picks ECT_AFCON/ECT_AFBPT and `conversion`
            ECT_INP2CON/ECT_INP2ELC; the two only ever pair up as (AFCON, INP2CON)
            and (AFBPT, INP2ELC).
            """
            af = g.get_parameter(availability)
            inp2 = g.get_parameter(conversion)

            # Case I if AFpcg -- process is not vintaged
            not_vintaged: Condition = Sum(
                RtpCptyr[r, Modlyear[k], t, p],
                af[r, t, p, cc.arg2]
                * inp2[r, t, p]
                * coef_cpt[r, k, t, p]
                * prc_capact[r, p]
                * (
                    wrap_in_sum(VARM_NCAP[r, k, p, *sws], varm_set).where[t[k]]
                    + ncap_pasti[r, k, p]
                ),
            ).where[~g.PrcVint[r, p]]

            # process is vintaged
            vintaged: Condition = (
                af[r, t, p, cc.arg2]
                * inp2[r, t, p]
                * coef_cpt[r, v, t, p]
                * prc_capact[r, p]
                * (
                    wrap_in_sum(VARV_NCAP[r, v, p, *sws], varv_set).where[t[v]]
                    + ncap_pasti[r, v, p]
                )
            ).where[g.PrcVint[r, p]]

            return not_vintaged + vintaged

        eq_chpcon = g.get_equation(f"EQ{cc.sense}_CHPCON")
        eq_chpcon[RtpVintyr[r, v, t, p], *swx].where[
            swtx
            * g.ect_afcon[r, t, p, cc.arg2]
            * Sum(RtpcsVarf[r, t, p, c, ts].where[EctElc[r, p, c]], 1).where[
                EctChp[r, p]
            ]
        ] = generate_equation(
            lhs=electricity - heat,
            type=cc.sense,
            rhs=available_capacity("ECT_AFCON", "ECT_INP2CON"),
        )

        eq_chpbpt = g.get_equation(f"EQ{cc.sense}_CHPBPT")
        eq_chpbpt[RtpVintyr[r, v, t, p], *swx].where[
            swtx
            * g.ect_afbpt[r, t, p, cc.arg2]
            * Sum(RtpcsVarf[r, t, p, c, ts].where[EctDht[r, p, c]], 1).where[
                EctChp[r, p]
            ]
        ] = generate_equation(
            lhs=heat,
            type=cc.sense,
            rhs=available_capacity("ECT_AFBPT", "ECT_INP2ELC"),
        )
