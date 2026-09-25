# equ_ext_msa.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *============================================================================*
# * EQU_EXT.MSA Equation definitions for MACRO Stand-Alone
# *============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Equation, Sum, sparse
from gamspy.math import Max, log, rpower

from core.base_class import GamsClass
from core.eqobjann_tm import EqobjannTm, EqobjannTmConfig

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitVariable

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtMsa(GamsClass):
    """Translation unit for equ_ext.msa."""

    # Instance attributes
    module_name: str = "equ_ext_msa"
    gams_source: str = "equ_ext.msa"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # Prepare annualized coefficients and enable adjusted PV factors
        self.include(
            EqobjannTm(
                tc=self.tc,
                env=self.env,
                config=EqobjannTmConfig(arg1="N", arg2=0),
            )
        )

        if (self.env.objann + self.env.msa).upper() == "YESMSA":
            self.tc.enqueue(self.exec1)

        g.eq_util = Equation(
            m,
            name="EQ_UTIL",
            description="Utility equation - objective function for MKMC",
        )
        g.eq_conso = Equation(
            m,
            name="EQ_CONSO",
            domain=[g.Reg, g.tp],
            description="Computation of C (economy consumption)",
        )
        g.eq_prod_y = Equation(
            m,
            name="EQ_PROD_Y",
            domain=[g.Reg, g.tp],
            description="Computation of Y (economy output)",
        )
        g.eq_dd = Equation(
            m,
            name="EQ_DD",
            domain=[g.Reg, g.tp, g.Com],
            description="Demand decoupling",
        )
        g.eq_mcap = Equation(
            m,
            name="EQ_MCAP",
            domain=[g.Reg, g.tp],
            description="Capital - trillion dollars",
        )
        g.eq_tmc = Equation(
            m,
            name="EQ_TMC",
            domain=[g.Reg, g.tp],
            description="Terminal condition  - trillion dollars",
        )
        g.eq_ivecbnd = Equation(
            m,
            name="EQ_IVECBND",
            domain=[g.Reg, g.t],
            description="Bound on the sum of investment and energy costs",
        )
        g.eq_escost = Equation(
            m, name="EQ_ESCOST", domain=[g.Reg, g.tp], description="Energy system cost"
        )
        g.eq_trdbal = Equation(
            m, name="EQ_TRDBAL", domain=[g.tp, g.item], description="Trade balance"
        )
        g.eq_ccdm = Equation(
            m,
            name="EQ_CCDM",
            domain=[g.Reg, g.mdm, g.year],
            description="Damage from climate change",
        )

        # *=======================================================================
        # *  Utility Production Function, the Objective Function
        # * ======================================================================
        g.eq_util[...] = (
            Sum(
                g.Mr[g.r],
                Sum(
                    g.t,
                    g.tm_nwt[g.r]
                    * g.tm_pwt[g.t]
                    * g.tm_dfact[g.r, g.t]
                    * log(g.VAR_C[g.r, g.t]),
                )
                + Sum(
                    Domain(g.TmDam[g.r, g.lA], g.Xtp),
                    g.tm_nwt[g.r]
                    * g.tm_pwt[g.Xtp]
                    * g.tm_udf[g.r, g.Xtp]
                    * log(g.VAR_CDM[g.r, g.lA, g.Xtp]),
                ),
            )
            == g.VAR_UTIL * Max(1.0, log(g.tm_scale_util * 1000.0)) / 1000.0
        )
        # *=======================================================================
        # *  Consumption Constraint
        # *=======================================================================
        g.eq_conso[g.Mr[g.r], g.t] = (
            g.VAR_Y[g.r, g.t]
            == g.VAR_C[g.r, g.t]
            + g.VAR_INV[g.r, g.t]
            + g.VAR_EC[g.r, g.t]
            + (
                Sum(g.TmDam[g.r, g.io], g.VAR_CDM[g.r, g.io, g.t])
                + g.VAR_NTX[g.r, g.t, "NMR"]
            ).where[g.Pp[g.t]]
        )
        # *=======================================================================
        # *  Production Constraint
        # *=======================================================================
        g.eq_prod_y[g.Mr[g.r], g.t] = g.VAR_Y[g.r, g.t] <= (
            (
                g.tm_akl[g.r]
                * (g.VAR_K[g.r, g.t] ** (g.tm_kpvs[g.r] * g.tm_rho[g.r]))
                * (g.tm_l[g.r, g.t] ** ((1.0 - g.tm_kpvs[g.r]) * g.tm_rho[g.r]))
                + Sum(
                    g.Dem[g.r, g.Dm].where[g.tm_dem[g.r, g.t, g.Dm]],
                    g.tm_b[g.r, g.Dm] * (g.VAR_D[g.r, g.t, g.Dm] ** g.tm_rho[g.r]),
                )
            )
            ** (1.0 / g.tm_rho[g.r])
        )
        # *=======================================================================
        # *  Demand Decoupling  Constraint:
        # *  The energy service demands D are reduced by the DDF factors
        # *  while as production function factors increase ECONOMIC OUTPUT
        # *=======================================================================
        g.eq_dd[g.Mr[g.r], g.tp, g.Dm] = (
            g.VAR_DEM[g.r, g.tp, g.Dm]
            == (
                (1.0 / g.tm_scale_nrg)
                * (
                    g.tm_aeeifac[g.r, g.tp, g.Dm] * g.VAR_D[g.r, g.tp, g.Dm]
                    + g.VAR_SP[g.r, g.tp, g.Dm]
                )
            ).where[(g.tm_dem[g.r, g.tp, g.Dm] > 0.0)]
        )
        # *=======================================================================
        # *  Capital Constraint
        # *=======================================================================
        g.eq_mcap[g.Mr[g.r], g.Pp[g.t.lead(1)]] = (
            g.VAR_K[g.r, g.Pp]
            <= g.VAR_K[g.r, g.t] * g.tm_tsrv[g.r, g.t]
            + (
                g.d[g.Pp] * g.VAR_INV[g.r, g.Pp]
                + g.d[g.t] * g.VAR_INV[g.r, g.t] * g.tm_tsrv[g.r, g.t]
            )
            / 2.0
        )
        # *=======================================================================
        # *  Terminal Condition
        # *=======================================================================
        g.eq_tmc[g.Mr[g.r], g.Tlast] = (
            g.VAR_K[g.r, g.Tlast] * (g.tm_growv[g.r, g.Tlast] + g.tm_depr[g.r]) / 100.0
            <= g.VAR_INV[g.r, g.Tlast]
        )
        # *=======================================================================
        # *  Bound on Sum of Investment and Energy
        # *=======================================================================
        g.eq_ivecbnd[g.Mr[g.r], g.Pp[g.t]] = g.VAR_INV[g.r, g.t] + g.VAR_EC[
            g.r, g.t
        ] <= g.tm_y0[g.r] * (g.tm_l[g.r, g.t] ** g.tm_ivetol[g.r])
        # *=======================================================================
        # *  Cost of Energy
        # *=======================================================================
        g.eq_escost[g.Mr[g.r], g.Pp] = (
            g.tm_qsfa[g.r, g.Pp]
            + Sum(
                g.Dm,
                g.tm_qsfb[g.r, g.Pp, g.Dm] * (rpower(g.VAR_DEM[g.r, g.Pp, g.Dm], 2)),
            )
            + g.tm_amp[g.r, g.Pp]
            <= g.VAR_EC[g.r, g.Pp]
        )
        # *=======================================================================
        # * Trades and damage
        # *=======================================================================
        g.eq_trdbal[g.Pp, g.trd] = Sum(g.Mr[g.r], g.VAR_NTX[g.r, g.Pp, g.trd]) == 0.0

        g.eq_ccdm[g.TmDam[g.Mr[g.r], g.mdm], g.Xtp] = g.VAR_CDM[g.r, g.mdm, g.Xtp] == (
            (
                (
                    1.0
                    - (self.cm_clibox("DELTA-ATM", "ATM", g.Xtp) / g.tm_catt[g.r]) ** 2
                )
                ** g.tm_hsx[g.r, g.Xtp]
            ).where[g.lA[g.mdm]]
            + Sum(
                g.Superyr[g.t[g.Xtp], g.ll].where[g.Xtp[g.ll]],
                g.tm_gdpgoal[g.r, g.t]
                * g.tm_xwt[g.r, g.ll]
                * (
                    g.tm_mdtl[g.r]
                    * self.cm_clibox("DELTA-ATM", "ATM", g.ll)
                    / Max(1, g.tm_defval["REFTEMP"])
                    + g.tm_mdtq[g.r]
                    * (
                        self.cm_clibox("DELTA-ATM", "ATM", g.ll)
                        / Max(1, g.tm_defval["REFTEMP"])
                    )
                    ** 2
                ),
            ).where[g.io[g.mdm]]
        )

    def cm_clibox(
        self, arg1: str, arg2: str, arg3: Alias | Set
    ) -> ImplicitVariable | int:
        if self.env.cli.upper() != "YES":
            return 0

        return self.tc.VAR_CLIBOX[arg1, arg2, arg3]

    def exec1(self) -> None:
        g = self.tc
        g.coef_pvt[g.r, g.t] = sparse(g.tm_udf[g.r, g.t])
        g.obj_pvt[g.r, g.t, g.cur].where[g.Rdcur[g.r, g.cur]] = sparse(
            g.tm_udf[g.r, g.t]
        )
