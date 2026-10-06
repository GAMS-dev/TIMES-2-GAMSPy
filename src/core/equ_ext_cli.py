# equ_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * EQU_EXT.cli - Extension for Climate Module
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *=============================================================================


from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from gamspy import Domain, Number, Ord, Sum
from gamspy.math import same_as

from core.base_class import GamsClass
from core.utils import apply_sw_stvars, extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from core.utils import SowGPType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EquExtCli(GamsClass):
    """Translation unit for equ_ext.cli."""

    # Instance attributes
    module_name: str = "equ_ext_cli"
    gams_source: str = "equ_ext.cli"

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

        # CLIMATE MODULE EQUATIONS
        if self.env.stages.upper() == "YES":
            self.env.set_local("swtd", "SUM(SOW,")
            self.env.set_local("swtd_GP", (g.Sow,))
            self.env.set_local("swo", ",SOW")
            self.env.set_local("swo_GP", (g.Sow,))
            self.env.set_local("send", ")")
            self.env.set_local("swts", ",SW_TSW(SOW,T,W)")
            self.env.set_local("swts_GP", (g.SwTsw[g.Sow, g.t, g.w],))
        else:
            self.env.set_local("swo", ",'1'")
            self.env.set_local("swo_GP", ("1",))
            self.env.set_local("send", "")
            self.env.set_local("swts", "")
            self.env.set_local("swts_GP", ())

        if self.env.stages == "YES":
            self.env.set_local("swtd", "SUM(SW_TSW(SOW,T-1,W),")
            self.env.set_local("swtd_GP", (g.SwTsw[g.Sow, g.t - 1, g.w],))
            self.env.set_local("swd", ",W")
            self.env.set_local("swd_GP", (g.w,))
            # added missing closing parenthese
            self.env.set_local("send", ")")
            self.env.set_local("swt", "$SW_T(T,SOW)")
            self.env.set_local("swt_GP", (g.SwT[g.t, g.Sow],))
        else:
            self.env.set_local("cpar", "CM_MAXC(LL,CG)")
            self.env.set_local("cpar_GP", g.cm_maxc[g.ll, g.cg])

        if self.env.stages == "YES":
            self.env.set_local("cpar", f"S_CM_MAXC(LL,CG,'1'{self.env.sow})")
            self.env.set_local(
                "cpar_GP", g.s_cm_maxc[g.ll, g.cg, "1", *self.env.sow_GP]
            )
            apply_sw_stvars(env=self.env, g=self.tc, witspine=self.env.witspine)

        eq = self.env.eq
        var = self.env.var
        vart = self.env.vart_GP
        vartt = self.env.vartt_GP
        sow = self.env.sow_GP
        sws = self.env.sws_GP
        stages = self.env.stages
        obj = self.env.obj
        cpar = self.env.cpar_GP
        swt = self.env.swt_GP
        swd = self.env.swd_GP
        swtd = self.env.swtd_GP
        swts = self.env.swts_GP
        swo = self.env.swo_GP

        self.balance_equation_for_total_emission(
            eq=eq, var=var, sow=sow, cpar=cpar, swt=swt
        )
        self.balance_equation_co2_in_box_t(
            eq=eq, var=var, sow=sow, swd=swd, sws=sws, swt=swt, swtd=swtd
        )
        self.balance_equation_temperature_clitemp(
            eq=eq, var=var, vart=vart, sow=sow, swo=swo, sws=sws, swtd=swtd
        )
        self.balance_equation_temperature_clibeoh(
            eq=eq, var=var, vart=vart, sow=sow, sws=sws, swo=swo, swd=swd, swts=swts
        )
        self.constraint_max_ghg(
            stages=stages,
            obj=obj,
            eq=eq,
            var=var,
            vart=vart,
            vartt=vartt,
            sow=sow,
            cpar=cpar,
            sws=sws,
        )

    def balance_equation_for_total_emission(
        self: EquExtCli,
        eq: str,
        var: str,
        sow: SowGPType,
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        cpar: ImplicitParameter,
    ) -> None:
        """Balance equation for the total emissions/forcing in each T"""
        g = self.tc

        eq_clitot = g.get_equation(f"{eq}_CLITOT")
        VAR_COMNET = g.get_variable(f"{var}_COMNET")
        VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")

        swt_cond = swt[0] if swt else Number(1)

        eq_clitot[g.CmTkind, g.Superyr[g.t, g.ll], *sow].where[
            g.cm_led[g.ll].where[swt_cond]
        ] = (
            Sum(
                Domain(g.RtcsVarc[g.r, g.t, g.c, g.s], g.cg[g.CmEmis[g.CmTkind]]).where[
                    g.cm_ghgmap[g.r, g.c, g.cg]
                ],
                VAR_COMNET[g.r, g.t, g.c, g.s, *sow]
                * g.cm_ghgmap[g.r, g.c, g.cg]
                * g.cm_evar[g.CmTkind, g.ll],
            ).where[g.cm_ppm[g.CmTkind]]
            + g.cm_bemi[g.CmTkind, g.ll]
            + Sum(
                g.CmForcmap[g.CmTkind, g.CmEmis].where[~g.CmEmis[g.CmTkind]],
                g.cm_linfor[g.ll, g.CmEmis, "FX"]
                + g.cm_linfor[g.ll, g.CmEmis, "N"]
                / g.cm_ppm[g.CmEmis]
                * Sum(
                    g.CmBoxmap[g.CmEmis, g.CmVar, g.CmBox].where[
                        g.cm_phi[g.CmEmis, g.CmBox, g.CmEmis]
                    ],
                    VAR_CLIBOX[g.CmVar, g.CmBox, g.ll, *sow],
                ),
            )
            + Sum(g.CmForcmap[g.CmTkind, g.CmVar[g.cg]].where[~g.CmEmis[g.CmVar]], cpar)
            + Sum(same_as("FORCING", g.CmTkind), g.cm_exoforc[g.ll])
            == VAR_CLITOT[g.CmTkind, g.ll, *sow]
        )

    def balance_equation_co2_in_box_t(
        self: EquExtCli,
        eq: str,
        var: str,
        sow: SowGPType,
        swd: tuple[Set | Alias] | tuple[()],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swtd: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    ) -> None:
        """Balance equation for the mass of CO2 in each box in each T"""
        g = self.tc

        eq_cliconc = g.get_equation(f"{eq}_CLICONC")
        VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")

        swt_cond = swt[0] if swt else Number(1)

        eq_cliconc[g.CmConc[g.CmEmis[g.CmKind], g.CmBox], g.t, *sow].where[swt_cond] = (
            wrap_in_sum(
                Sum(
                    g.CmBoxmap[g.CmKind, g.CmVar, g.CmBuck],
                    g.cm_aa[g.CmKind, g.t, "1", g.CmBox, g.CmBuck]
                    * VAR_CLIBOX[g.CmVar, g.CmBuck, g.t - 1, *swd],
                )
                + g.cm_cc[g.CmKind, g.t, "1", g.CmBox]
                * VAR_CLITOT[g.CmKind, g.t - 1, *swd]
                + g.cm_bb[g.CmKind, g.t, "1", g.CmBox] * VAR_CLITOT[g.CmKind, g.t, *sow]
                + Sum(
                    g.CmCoupmap[g.CmEmis, g.CmVar, g.CmBox],
                    g.cm_couple[g.CmVar, g.t, g.CmEmis, "N"]
                    * g.cm_couple[g.CmVar, g.t, g.CmEmis, "ATM"]
                    * (
                        g.cm_bb[g.CmKind, g.t, "1", "ATM"]
                        * VAR_CLIBOX[g.CmVar, "ATM", g.t, *sow]
                        + g.cm_cc[g.CmKind, g.t, "1", "ATM"]
                        * VAR_CLIBOX[g.CmVar, "ATM", g.t - 1, *sws]
                    ),
                )
                + Sum(
                    g.CmBoxmap[g.CmKind, g.CmHists, g.CmBuck].where[
                        g.cm_aa[g.CmKind, g.t, "1", g.CmBox, g.CmBuck]
                    ],
                    g.cm_aa[g.CmKind, g.t, "1", g.CmBox, g.CmBuck]
                    * g.cm_stat0[g.CmKind, g.CmBuck],
                ).where[Ord(g.t) == 1],
                swtd[0] if swtd else (),
            )
            == Sum(
                g.CmBoxmap[g.CmKind, g.CmVar, g.CmBox],
                VAR_CLIBOX[g.CmVar, g.CmBox, g.t, *sow],
            )
        )

    def balance_equation_temperature_clitemp(
        self: EquExtCli,
        eq: str,
        var: str,
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        sow: SowGPType,
        swo: tuple[Literal["1"] | Set | Alias],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swtd: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    ) -> None:
        """Balance equation for the temperature"""
        g = self.tc

        vart_id, vart_set = extract_var_domain(vart)

        eq_clitemp = g.get_equation(f"{eq}_CLITEMP")
        VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")
        VART_CLITOT = g.get_variable(f"{vart_id}_CLITOT")

        eq_clitemp[g.CmConc[g.CmKind["FORCING"], g.CmBox], g.t, *sow] = wrap_in_sum(
            Sum(
                g.CmBoxmap[g.CmKind, g.CmVar, g.CmBuck],
                g.cm_aa[g.CmKind, g.t, *swo, g.CmBox, g.CmBuck]
                * VAR_CLIBOX[g.CmVar, g.CmBuck, g.t - 1, *sow],
            )
            + g.cm_cc[g.CmKind, g.t, *swo, g.CmBox]
            * VAR_CLITOT[g.CmKind, g.t - 1, *sws]
            + g.cm_bb[g.CmKind, g.t, *swo, g.CmBox]
            * wrap_in_sum(VART_CLITOT[g.CmKind, g.t, *sws], vart_set)
            + Sum(
                g.CmBoxmap[g.CmKind, g.CmHists, g.CmBuck].where[
                    g.cm_aa[g.CmKind, g.t, *swo, g.CmBox, g.CmBuck]
                ],
                g.cm_aa[g.CmKind, g.t, *swo, g.CmBox, g.CmBuck]
                * g.cm_stat0[g.CmKind, g.CmBuck],
            ).where[Ord(g.t) == 1],
            swtd[0] if swtd else (),
        ) == Sum(
            g.CmBoxmap[g.CmKind, g.CmVar, g.CmBox],
            VAR_CLIBOX[g.CmVar, g.CmBox, g.t, *sow],
        )

    def balance_equation_temperature_clibeoh(
        self: EquExtCli,
        eq: str,
        var: str,
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        sow: SowGPType,
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        swo: tuple[Literal["1"] | Set | Alias],
        swd: tuple[Set | Alias] | tuple[()],
        swts: tuple[ImplicitSet] | tuple[()],
    ) -> None:
        """Balance equation for the temperature"""
        g = self.tc

        vart_id, vart_set = extract_var_domain(vart)

        eq_clibeoh = g.get_equation(f"{eq}_CLIBEOH")
        VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")
        VART_CLIBOX = g.get_variable(f"{vart_id}_CLIBOX")
        VART_CLITOT = g.get_variable(f"{vart_id}_CLITOT")

        eq_clibeoh[g.CmConc[g.CmKind, g.CmBox], g.Superyr[g.t, g.ll], *sow].where[
            (~g.Milestonyr[g.ll]).where[g.cm_led[g.ll]]
        ] = Sum(
            g.year[g.ll - g.cm_led[g.ll]],
            Sum(
                g.CmBoxmap[g.CmKind, g.CmVar, g.CmBuck],
                g.cm_aa[g.CmKind, g.ll, "1", g.CmBox, g.CmBuck]
                * wrap_in_sum(VART_CLIBOX[g.CmVar, g.CmBuck, g.year, *sws], vart_set),
            )
            + g.cm_cc[g.CmKind, g.ll, "1", g.CmBox]
            * wrap_in_sum(VART_CLITOT[g.CmKind, g.year, *sws], vart_set)
            + g.cm_bb[g.CmKind, g.ll, "1", g.CmBox]
            * wrap_in_sum(VART_CLITOT[g.CmKind, g.ll, *sws], vart_set),
        ).where[g.CmEmis[g.CmKind]] + Sum(
            [g.year[g.ll - g.cm_led[g.ll]], *swts],
            Sum(
                g.CmBoxmap[g.CmKind, g.CmVar, g.CmBuck],
                g.cm_aa[g.CmKind, g.ll, *swo, g.CmBox, g.CmBuck]
                * VAR_CLIBOX[g.CmVar, g.CmBuck, g.year, *sow],
            )
            + g.cm_cc[g.CmKind, g.ll, *swo, g.CmBox]
            * VAR_CLITOT[g.CmKind, g.year, *swd]
            + g.cm_bb[g.CmKind, g.ll, *swo, g.CmBox] * VAR_CLITOT[g.CmKind, g.ll, *swd],
        ).where[~g.CmEmis[g.CmKind]] == Sum(
            g.CmBoxmap[g.CmKind, g.CmVar, g.CmBox],
            wrap_in_sum(VART_CLIBOX[g.CmVar, g.CmBox, g.ll, *sws], vart_set).where[
                g.CmEmis[g.CmKind]
            ]
            + VAR_CLIBOX[g.CmVar, g.CmBox, g.ll, *sow].where[~g.CmEmis[g.CmKind]],
        )

    def constraint_max_ghg(
        self: EquExtCli,
        stages: str,
        obj: str,
        eq: str,
        var: str,
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        vartt: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        sow: SowGPType,
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        cpar: ImplicitParameter,
    ) -> None:
        """Constraint for the maximum atmospheric concentration of GHGs"""
        g = self.tc

        vart_id, vart_set = extract_var_domain(vart)
        vartt_id, vartt_set = extract_var_domain(vartt)

        eq_climax = g.get_equation(f"{eq}_CLIMAX")
        VAR_CLIBOX = g.get_variable(f"{var}_CLIBOX")
        VAR_CLITOT = g.get_variable(f"{var}_CLITOT")
        VART_CLITOT = g.get_variable(f"{vart_id}_CLITOT")
        VARTT_CLIBOX = g.get_variable(f"{vartt_id}_CLIBOX")
        VARTT_CLITOT = g.get_variable(f"{vartt_id}_CLITOT")

        # Bound on temperature
        if stages != "YES":
            temperature = (
                g.VAR_CLIBOX[g.CmVar, "ATM", g.t]
                + (
                    g.VAR_CLIBOX[g.CmVar, "ATM", g.tt]
                    - g.VAR_CLIBOX[g.CmVar, "ATM", g.t]
                )
                * (g.yearval[g.t] - g.yearval[g.ll])
                / g.lead[g.t]
            )
        else:
            temperature = (
                Sum(
                    g.SwTsw[g.w, g.t, g.Sow],
                    g.sw_prob[g.w] * VAR_CLIBOX[g.CmVar, "ATM", g.t, g.w],
                )
                / g.sw_tprob[g.t, g.Sow]
                * (g.lead[g.t] + g.yearval[g.ll] - g.yearval[g.t])
                + Sum(
                    g.SwTsw[g.ww, g.tt, g.w].where[g.SwTsw[g.Sow, g.tt, g.w]],
                    g.sw_prob[g.ww]
                    * VAR_CLIBOX[g.CmVar, "ATM", g.tt, g.ww]
                    / g.sw_tprob[g.tt, g.w],
                )
                * (g.yearval[g.t] - g.yearval[g.ll])
            ) / g.lead[g.t]

        # Bound on global emissions
        if obj.upper() != "LIN":
            global_emissions = Sum(
                [g.CmEmis[g.CmHists], g.Periodyr[g.t, g.Eohyears[g.ll]]],
                wrap_in_sum(VART_CLITOT[g.CmHists, g.t, *sws], vart_set),
            )
        else:
            global_emissions = Sum(
                [g.CmEmis[g.CmHists], g.Tpulseyr[g.t, g.ll]],
                g.tpulse[g.t, g.ll]
                * wrap_in_sum(VART_CLITOT[g.CmEmis, g.t, *sws], vart_set),
            )

        eq_climax[g.ll, g.CmHists[g.cg], *sow].where[cpar] = (
            Sum(
                [g.Superyr[g.Yk[g.t, g.ll]], g.Pret[g.t, g.tt]],
                # Bound on atmospheric quantity (concentration/delta-T)
                Sum(
                    g.CmBoxmap[g.CmEmis, g.CmVar, g.CmBox].where[
                        g.CmAtmap[g.CmEmis, g.CmHists]
                        * g.cm_phi[g.CmEmis, g.CmBox, g.CmEmis]
                    ],
                    (
                        VAR_CLIBOX[g.CmVar, g.CmBox, g.t, *sow]
                        + (
                            wrap_in_sum(
                                VARTT_CLIBOX[g.CmVar, g.CmBox, g.tt, *sws], vartt_set
                            )
                            - VAR_CLIBOX[g.CmVar, g.CmBox, g.t, *sow]
                        )
                        * (g.yearval[g.t] - g.yearval[g.ll])
                        / g.lead[g.t]
                    )
                    / g.cm_ppm[g.CmEmis],
                ).where[~g.CmTkind[g.CmHists]]
                # Bound on temperature
                + Sum(
                    g.CmBoxmap["FORCING", g.CmVar, "ATM"].where[
                        g.CmAtmap["FORCING", g.CmHists]
                    ],
                    temperature,
                )
                # Bound on radiative forcing
                + Sum(
                    g.CmTkind[g.CmHists].where[
                        Sum(g.CmForcmap[g.CmTkind, g.CmEmis], 1).where[
                            ~g.CmEmis[g.CmHists]
                        ]
                    ],
                    VAR_CLITOT[g.CmHists, g.t, *sow]
                    + (
                        wrap_in_sum(VARTT_CLITOT[g.CmHists, g.tt, *sws], vartt_set)
                        - VAR_CLITOT[g.CmHists, g.t, *sow]
                    )
                    * (g.yearval[g.t] - g.yearval[g.ll])
                    / g.lead[g.t],
                ),
            )
            # Bound on global emissions
            + global_emissions
            # Bound beyond last Milestone
            + Sum(
                g.Superyr[g.t, g.ll].where[~g.Yk[g.t, g.ll]],
                Sum(
                    g.CmBoxmap[g.CmEmis, g.CmVar, g.CmBox].where[
                        g.CmAtmap[g.CmEmis, g.CmHists]
                        * g.cm_phi[g.CmEmis, g.CmBox, g.CmEmis]
                    ],
                    VAR_CLIBOX[g.CmVar, g.CmBox, g.ll, *sow] / g.cm_ppm[g.CmEmis],
                ).where[~g.CmTkind[g.CmHists]]
                + Sum(
                    g.CmBoxmap["FORCING", g.CmVar, "ATM"].where[
                        g.CmAtmap["FORCING", g.CmHists]
                    ],
                    VAR_CLIBOX[g.CmVar, "ATM", g.ll, *sow],
                )
                + Sum(
                    g.CmTkind[g.CmHists].where[
                        Sum(g.CmForcmap[g.CmTkind, g.CmEmis], 1).where[
                            ~g.CmEmis[g.CmHists]
                        ]
                    ],
                    VAR_CLITOT[g.CmHists, g.ll, *sow],
                ),
            )
            <= cpar.where[
                Sum(g.CmAtmap[g.CmKind, g.CmHists], True) + g.CmTkind[g.CmHists]
            ]
        )
