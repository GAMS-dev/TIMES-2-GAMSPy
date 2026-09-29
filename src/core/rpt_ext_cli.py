# rpt_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * RPT_EXT.cli - Extension for Climate Module: Stochastic report
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------
# * Calculate Reporting parameters for Climate Module

# *-----------------------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Domain, Equation, Loop, Sum, Variable, sparse

from core.base_class import GamsClass
from core.rpt_par_cli import rpt_par_cli_GP
from core.utils import apply_sw_notags, apply_sw_tags

if TYPE_CHECKING:
    from gamspy import Alias, Number, Set
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class RptExtCli(GamsClass):
    """Translation unit for rpt_ext.cli."""

    # Instance attributes
    module_name: str = "rpt_ext_cli"
    gams_source: str = "rpt_ext.cli"

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

        if self.env.sensis.upper() == "YES":
            return

        apply_sw_notags(env=self.env)
        self.declarations(eq=self.env.eq, var=self.env.var, swd=self.env.swd_GP)

        if self.env.stages == "YES":
            apply_sw_tags(env=self.env, g=g)
            self.env.set_scoped("swsw", "SW_TSW(SOW,T,WW),")
            self.env.set_scoped("swsw_GP", (g.SwTsw[g.Sow, g.t, g.ww],))

        if self.env.scum == "1":
            self.env.set_scoped("swsw", "SW_T(T,WW),")
            self.env.set_scoped("swsw_GP", (g.SwT[g.t, g.ww],))
            self.env.set_scoped("scum", "*SW_TPROB(T,WW)")
            self.env.set_scoped("scum_GP", g.sw_tprob[g.t, g.ww])

        self.add_records_to_universe_item(
            ["FORC+CO2", "FORC+TOT", "DELTA+ATM", "DELTA+LO"]
        )
        self.tc.enqueue(
            self.exec_loop,
            stages=self.env.stages,
            swsw=self.env.swsw_GP,
            var=self.env.var,
            swd=self.env.swd_GP,
            scum=self.env.scum,
            scum_GP=self.env.scum_GP,
            eq=self.env.eq,
        )

    def declarations(
        self: RptExtCli, eq: str, var: str, swd: tuple[Set | Alias, ...] | tuple[()]
    ) -> None:
        """Untagged reporting copies of the climate variables and equations.

        GAMS ignores a repeated declaration of a symbol, so for a deterministic run
        mod_vars.cli has already declared these very names (as POSITIVE variables)
        and this block is a no-op there. Only a stochastic run, where mod_vars.cli
        tagged them ``VAS_``/``ES_``, actually creates them here.
        """
        g = self.tc
        m = g.container

        if not g.declared(f"{eq}_CLITOT"):
            g.set_equation(
                name=f"{eq}_CLITOT",
                eq=Equation(
                    m,
                    name=f"{eq}_CLITOT",
                    domain=[g.cmitem, g.t, g.ll, *swd],
                    description="Balances for the total emissions or forcing",
                ),
            )
        if not g.declared(f"{eq}_CLIMAX"):
            g.set_equation(
                name=f"{eq}_CLIMAX",
                eq=Equation(
                    m,
                    name=f"{eq}_CLIMAX",
                    domain=[g.allyear, g.cmitem, *swd],
                    description="Constraint for maximum climate quantities",
                ),
            )
        if not g.declared(f"{var}_CLITOT"):
            g.set_variable(
                name=f"{var}_CLITOT",
                var=Variable(
                    m,
                    name=f"{var}_CLITOT",
                    domain=[g.cmitem, g.ll, *swd],
                    description="Total emissions or forcing by milestone year",
                ),
            )
        if not g.declared(f"{var}_CLIBOX"):
            g.set_variable(
                name=f"{var}_CLIBOX",
                var=Variable(
                    m,
                    name=f"{var}_CLIBOX",
                    type="Positive",
                    domain=[g.cmitem, g.CmBox, g.ll, *swd],
                    description="Quantities in the climate reservoirs",
                ),
            )

    def exec_loop(
        self: RptExtCli,
        stages: str,
        swsw: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        swd: tuple[Set | Alias, ...] | tuple[()],
        scum: str,
        scum_GP: ImplicitParameter | Number,
        eq: str,
    ) -> None:
        g = self.tc
        t, ll, ww = g.t, g.ll, g.ww
        CmBox, CmVar = g.CmBox, g.CmVar
        VAR_CLIBOX, VAR_CLITOT = g.VAR_CLIBOX, g.VAR_CLITOT
        EQ_CLIMAX, EQ_CLITOT = g.eq_climax, g.eq_clitot

        # $%SW_TAGS% ran after the declaration block, so %VAR%/%EQ% are the
        # stochastic VAS_/ES_ symbols wherever the blocks below use these.
        TAGGED_VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        TAGGED_VAR_CLITOT = g.get_variable(f"{var}_CLITOT")
        TAGGED_EQ_CLIMAX = g.get_equation(f"{eq}_CLIMAX")
        TAGGED_EQ_CLITOT = g.get_equation(f"{eq}_CLITOT")

        # * Results for each SOW
        sow_loop = g.Sow if stages != "YES" else g.Auxsow[g.Sow].where[g.sw_prob[g.Sow]]
        with Loop(sow_loop):
            # * Clear results from previous SOW
            if stages == "YES":
                VAR_CLITOT.setRecords(None)
                VAR_CLIBOX.setRecords(None)
                EQ_CLITOT.setRecords(None)
                EQ_CLIMAX.setRecords(None)
                with Loop(g.Superyr[t, ll].where[g.cm_led[ll]]):
                    VAR_CLITOT.l[CmVar, ll] = sparse(
                        Sum(
                            Domain(*swsw),
                            TAGGED_VAR_CLITOT.l[(CmVar, ll, *swd)] * scum_GP,
                        )
                    )
                    VAR_CLIBOX.l[CmVar, CmBox, ll] = sparse(
                        Sum(
                            Domain(*swsw),
                            TAGGED_VAR_CLIBOX.l[(CmVar, CmBox, ll, *swd)] * scum_GP,
                        )
                    )
                    if f"{stages}{scum}" == "YES":
                        VAR_CLIBOX.l[CmVar, CmBox, ll] = sparse(
                            TAGGED_VAR_CLIBOX.l[CmVar, CmBox, ll, g.Sow]
                        )
                    EQ_CLIMAX.m[ll, CmVar] = sparse(
                        Sum(
                            Domain(*swsw),
                            TAGGED_EQ_CLIMAX.m[(ll, CmVar, *swd)] * g.sw_unpb[t, ww],
                        )
                    )
                EQ_CLITOT.m[CmVar, t, t] = sparse(
                    Sum(
                        Domain(*swsw),
                        TAGGED_EQ_CLITOT.m[(CmVar, t, t, *swd)] * g.sw_unpb[t, ww],
                    )
                )

            rpt_par_cli_GP(g)

        # Reading .records flushes the loop above to GAMS first, so the printed
        # values are the ones GAMS would have DISPLAYed here.
        if g.Sow.number_records == 1:
            print(g.cm_result.records)
            print(g.cm_maxc_m.records)
        else:
            print(g.cm_sresult.records)
            print(g.cm_smaxc_m.records)
        # *-----------------------------------------------------------------------------
        if stages != "YES":
            return

        # * Expected marginals
        with Loop(g.Superyr[t, ll].where[g.cm_led[ll]]):
            EQ_CLIMAX.m[ll, CmVar] = sparse(
                Sum(g.SwT[t, g.w], TAGGED_EQ_CLIMAX.m[ll, CmVar, g.w])
            )
            VAR_CLITOT.l[CmVar, ll] = sparse(
                Sum(
                    g.SwT[t, g.w],
                    g.sw_tprob[t, g.w] * TAGGED_VAR_CLITOT.l[CmVar, ll, g.w],
                )
            )
            VAR_CLIBOX.l[CmVar, CmBox, ll] = sparse(
                Sum(
                    g.SwT[t, g.w],
                    g.sw_tprob[t, g.w] * TAGGED_VAR_CLIBOX.l[CmVar, CmBox, ll, g.w],
                )
            )
