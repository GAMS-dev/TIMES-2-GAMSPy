# eqbndcst_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQBNDCOST: bounds on undiscounted cost components
# *   arg1 -
# *=============================================================================*
# *[AL] Questions/Comments:
# *

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, cast

from gamspy import Domain, Loop, Number, Ord, Parameter, Set, SpecialValues, Sum, sparse
from gamspy.math import Max, Min, Round, same_as

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.utils import SowGPType, extract_var_domain, wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from collections.abc import Callable

    from gamspy import Alias
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)

# SET COST_GMAP(COSTAGG,COSTAGG,COSTYPE) / ... /;
# The nested GAMS short-hand `AGG.(CAT.TYPE,...)` is expanded here.
COST_GMAP_RECORDS: list[tuple[str, str, str]] = [
    ("INVTAXSUB", "INVTAX", "TAX"),
    ("INVTAXSUB", "INVSUB", "SUB"),
    ("INVALL", "INV", "COST"),
    ("INVALL", "INVTAX", "TAX"),
    ("INVALL", "INVSUB", "SUB"),
    ("FOMTAXSUB", "FOMTAX", "TAX"),
    ("FOMTAXSUB", "FOMSUB", "SUB"),
    ("FOMALL", "FOM", "COST"),
    ("FOMALL", "FOMTAX", "TAX"),
    ("FOMALL", "FOMSUB", "SUB"),
    ("FIX", "INV", "COST"),
    ("FIX", "FOM", "COST"),
    ("FIXTAX", "INVTAX", "TAX"),
    ("FIXTAX", "FOMTAX", "TAX"),
    ("FIXSUB", "INVSUB", "TAX"),
    ("FIXSUB", "FOMSUB", "TAX"),
    ("FIXTAXSUB", "INVTAX", "TAX"),
    ("FIXTAXSUB", "INVSUB", "SUB"),
    ("FIXTAXSUB", "FOMTAX", "TAX"),
    ("FIXTAXSUB", "FOMSUB", "SUB"),
    ("FIXALL", "INV", "COST"),
    ("FIXALL", "INVTAX", "TAX"),
    ("FIXALL", "INVSUB", "SUB"),
    ("FIXALL", "FOM", "COST"),
    ("FIXALL", "FOMTAX", "TAX"),
    ("FIXALL", "FOMSUB", "SUB"),
    ("COMTAXSUB", "COMTAX", "TAX"),
    ("COMTAXSUB", "COMSUB", "SUB"),
    ("FLOTAXSUB", "FLOTAX", "TAX"),
    ("FLOTAXSUB", "FLOSUB", "SUB"),
    ("ALLTAX", "INVTAX", "TAX"),
    ("ALLTAX", "FOMTAX", "TAX"),
    ("ALLTAX", "COMTAX", "TAX"),
    ("ALLTAX", "FLOTAX", "TAX"),
    ("ALLSUB", "INVSUB", "TAX"),
    ("ALLSUB", "FOMSUB", "TAX"),
    ("ALLSUB", "COMSUB", "TAX"),
    ("ALLSUB", "FLOSUB", "TAX"),
    ("ALLTAXSUB", "INVTAX", "TAX"),
    ("ALLTAXSUB", "INVSUB", "SUB"),
    ("ALLTAXSUB", "FOMTAX", "TAX"),
    ("ALLTAXSUB", "FOMSUB", "SUB"),
    ("ALLTAXSUB", "COMTAX", "TAX"),
    ("ALLTAXSUB", "COMSUB", "SUB"),
    ("ALLTAXSUB", "FLOTAX", "TAX"),
    ("ALLTAXSUB", "FLOSUB", "SUB"),
]


class EqbndcstMod(GamsClass):
    """Translation unit for eqbndcst.mod."""

    # Instance attributes
    module_name: str = "eqbndcst_mod"
    gams_source: str = "eqbndcst.mod"

    def __init__(self, tc: TimesModelClass, env: CompileEnvironment):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.compile()

    def compile(self) -> None:
        g = self.tc
        m = g.container

        # * Need a few more aliases and sets
        g.Superyr = Set(
            m,
            name="SUPERYR",
            domain=[g.t, g.allyear],
            description="SUpremum PERiod YeaR",
        )
        g.Ykk = Set(m, name="YKK", domain=[g.allyear, g.allyear, g.allyear])
        g.RtpIan = Set(m, name="RTP_IAN", domain=[g.Reg, g.t, g.p, g.cur])
        g.RtIan = Set(
            m,
            name="RT_IAN",
            domain=[g.Reg, g.allyear, g.allyear, g.cur, g.costagg],
        )
        g.cst_annc = Parameter(
            m,
            name="CST_ANNC",
            domain=[g.r, g.allyear, g.p, g.allyear, g.ucname, g.cur],
        )

        # $IF NOT DEFINED OBJ_SUMII $EXIT
        if not g.declared("OBJ_SUMII"):
            return

        g.CostGmap = Set(
            m,
            name="COST_GMAP",
            domain=[g.costagg, g.costagg, g.costype],
            records=COST_GMAP_RECORDS,
        )

        self.tc.enqueue(self.exec1, declif=self.env.declif)
        if self.env.stages == "YES":
            self.env.set_scoped("swt", f"SW_T(TT{self.env.sow})$")
            self.env.set_scoped(
                "swt_GP", (g.SwT[g.tt, *self.env.sow_GP],)
            )  # ToDo: Move $ to main code

        if self.env.scum == "1":
            self.env.set_scoped("swt", "")
            self.env.set_scoped("swt_GP", ())

        sowstart = self.env.sow_GP

        if self.env.stages == "YES":
            self.env.set_scoped("swd", self.env.sow)
            self.env.set_scoped("swd_GP", self.env.sow_GP)
            self.env.set_scoped("sow", self.env.swd)
            self.env.set_scoped("sow_GP", self.env.swd_GP)
            self.env.set_scoped("swtd", "SUM")
            self.env.set_scoped("swtd_GP", "SUM")

        # The domain (and multiplier) of the SUM over the pulse years
        if self.env.obj.upper() != "LIN":
            self.env.set_scoped(
                "tpulse", "(PERIODYR(T,Y_EOH),YK(ALLYEAR,Y_EOH))$YK(Y_EOH,YEAR),"
            )
            self.env.set_scoped(
                "tpulse_GP",
                (
                    Domain(g.Periodyr[g.t, g.YEoh], g.Yk[g.allyear, g.YEoh]).where[
                        g.Yk[g.YEoh, g.year]
                    ],
                    Number(1),
                ),
            )
        else:
            self.env.set_scoped(
                "tpulse",
                "(TPULSEYR(T,Y_EOH),YK(ALLYEAR,Y_EOH))$YK(Y_EOH,YEAR),TPULSE(T,Y_EOH)*",
            )
            self.env.set_scoped(
                "tpulse_GP",
                (
                    Domain(g.Tpulseyr[g.t, g.YEoh], g.Yk[g.allyear, g.YEoh]).where[
                        g.Yk[g.YEoh, g.year]
                    ],
                    g.tpulse[g.t, g.YEoh],
                ),
            )
        if self.env.varcost.upper() == "LIN":
            self.env.set_scoped(
                "tpulse",
                "(PERIODYR(T,Y),MILESTONYR(Y_EOH),YK(ALLYEAR,Y))$(YK(Y,YEAR)$TPULSE(Y_EOH,Y)),TPULSE(Y_EOH,Y)*",
            )
            self.env.set_scoped(
                "tpulse_GP",
                (
                    Domain(
                        g.Periodyr[g.t, g.Y],
                        g.Milestonyr[g.YEoh],
                        g.Yk[g.allyear, g.Y],
                    ).where[g.Yk[g.Y, g.year] & g.tpulse[g.YEoh, g.Y]],
                    g.tpulse[g.YEoh, g.Y],
                ),
            )
        if f"{self.env.obj.upper()}{self.env.varcost.upper()}" == "LINLIN":
            self.env.set_scoped(
                "tpulse",
                "(TPULSEYR(T,Y),MILESTONYR(Y_EOH),YK(ALLYEAR,Y))$(YK(Y,YEAR)$TPULSE(Y_EOH,Y)),TPULSE(Y_EOH,Y)*TPULSE(T,Y)*",
            )
            self.env.set_scoped(
                "tpulse_GP",
                (
                    Domain(
                        g.Tpulseyr[g.t, g.Y],
                        g.Milestonyr[g.YEoh],
                        g.Yk[g.allyear, g.Y],
                    ).where[g.Yk[g.Y, g.year] & g.tpulse[g.YEoh, g.Y]],
                    g.tpulse[g.YEoh, g.Y] * g.tpulse[g.t, g.Y],
                ),
            )

        # $SET VART1 %VART%
        temp_vart = self.env.vart_GP
        # $IF %SCUM%==1 $SET VART SUM(SW_TSW(W,T,W),SW_TPROB(T,W)*Z
        if self.env.scum == "1":
            self.env.set_scoped("vart", "SUM(SW_TSW(W,T,W),SW_TPROB(T,W)*Z")
            self.env.set_scoped(
                "vart_GP", ("Z", (g.SwTsw[g.w, g.t, g.w], g.sw_tprob[g.t, g.w]))
            )

        sowend = self.env.sow_GP
        if self.env.stages == "YES":
            sowend = self.env.swd_GP

        self.equation(
            eq=self.env.eq,
            sowstart=sowstart,
            swt=self.env.swt_GP,
            vart1=temp_vart,
            sws=self.env.sws_GP,
            declif=self.env.declif,
            tpulse=self.env.tpulse_GP,
            vart=self.env.vart_GP,
            swtd=self.env.swtd_GP,
            swsw=self.env.swsw_GP,
            cal_red=self.env.cal_red,
            var=self.env.var,
            sowend=sowend,
            pgprim=self.env.pgprim,
            sow=self.env.sow_GP,
            def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
        )

        if self.env.stages == "YES":
            self.env.set_scoped("sow", self.env.swd)
            self.env.set_scoped("sow_GP", self.env.swd_GP)

    def equation(
        self: EqbndcstMod,
        eq: str,
        sowstart: SowGPType,
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        vart1: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias, ...] | tuple[()],
        declif: str,
        tpulse: tuple[Condition | Domain, Expression | ImplicitParameter | Number],
        vart: tuple[str, Any],
        swtd: tuple[Set | Alias | ImplicitSet, ...] | tuple[()] | str,
        swsw: tuple[ImplicitSet] | tuple[ImplicitSet, ImplicitParameter] | tuple[()],
        cal_red: str,
        var: str,
        sowend: SowGPType,
        pgprim: str,
        sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()],
        def_rtp_ffcs: bool,
    ) -> None:
        g = self.tc
        r, t, tt, v, p, c, s, ts = g.r, g.t, g.tt, g.v, g.p, g.c, g.s, g.ts
        year, allyear, ll, k, Y = g.year, g.allyear, g.ll, g.k, g.Y
        age, jot, life, span = g.age, g.jot, g.life, g.span
        j, jj, cur, costcat, costagg, costype = (
            g.j,
            g.jj,
            g.cur,
            g.costcat,
            g.costagg,
            g.costype,
        )
        Com, ie, io, YEoh, Yk = g.Com, g.ie, g.io, g.YEoh, g.Yk
        KEoh, ObjSumiv, RtpShape, obj_diviv = (
            g.KEoh,
            g.ObjSumiv,
            g.RtpShape,
            g.obj_diviv,
        )

        eq_bndcst, sowstart = macro.EQ_BNDCST_GP(eq, sowstart)
        ncap_declif = g.get_parameter(f"NCAP_{declif}")
        tpulse_domain, tpulse_mult = tpulse

        vart_id, vart_set = extract_var_domain(vart)
        suffixes = ["COMNET", "COMPRD", "IRE", "ACT"]
        VART_COMNET, VART_COMPRD, VART_IRE, VART_ACT = (
            g.get_variable(f"{vart_id}_{suffix}") for suffix in suffixes
        )

        # ------------------------------------------------------------------------------
        # Investment Costs
        investment = (
            Sum(
                Domain(
                    g.ObjSumii[r, t, p, age, KEoh[ll], jot],
                    span[age + Min(Ord(ll) + Ord(jot) - Ord(year) - 1, 0)],
                ).where[Yk[tt, t]],
                Sum(
                    g.Invspred[ll, jot, Y, k].where[Yk[allyear, Y]],
                    macro.obj_icost_GP(r, k, p, cur)
                    * Max(
                        0,
                        Min(g.yearval[allyear] + 1, g.yearval[Y] + Ord(age))
                        - Max(g.yearval[year], g.yearval[Y]),
                    ),
                )
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws)
                * g.obj_crf[r, t, p, cur]
                / g.obj_divi[r, t, p],
            ).where[~g.RtIan[r, year, allyear, cur, "INV"]]
            + Sum(
                Domain(t, p).where[g.cst_annc[r, t, p, tt, "INVCOST", cur]],
                g.cst_annc[r, t, p, tt, "INVCOST", cur]
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws),
            ).where[g.RtIan[r, year, allyear, cur, "INV"]]
        ).where[same_as(costcat, "INV")]

        # Decommissioning Costs
        decommissioning = Sum(
            g.Rtp[r, t, p].where[Yk[tt, t] & macro.obj_dcost_GP(r, t, p, cur)],
            Sum(
                g.ObjSumiii[r, t, p, KEoh, k, ll].where[Yk[allyear, ll]],
                macro.obj_dcost_GP(r, k, p, cur)
                * Max(
                    0,
                    Min(Ord(allyear) + 1, Ord(ll) + Round(ncap_declif[r, t, p]))
                    - Max(Ord(year), Ord(ll)),
                ),
            )
            * macro.VAR_NCAP_GP(vart1, r, t, p, sws)
            * g.obj_crfd[r, t, p, cur]
            / g.obj_diviii[r, t, p],
        ).where[same_as(costcat, "INV")]

        # Investment Taxes and Subsidies
        def investment_taxsub(
            obj_macro: Callable[..., ImplicitParameter],
        ) -> Condition:
            """The INVTAX / INVSUB components, driven by OBJ_ITAX / OBJ_ISUB."""
            return Sum(
                g.ObjSumii[r, t, p, age, KEoh, jot].where[
                    Yk[tt, t] & obj_macro(r, t, p, cur)
                ],
                Sum(
                    Domain(
                        g.Invspred[KEoh, jot, ll, k],
                        span[age + Min(Ord(ll) - Ord(year), 0)],
                    ).where[Yk[allyear, ll]],
                    obj_macro(r, k, p, cur)
                    * (
                        Min(Ord(allyear) + 1, Ord(ll) + Ord(age))
                        - Max(Ord(year), Ord(ll))
                    ),
                )
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws)
                * g.obj_crf[r, t, p, cur]
                / g.obj_divi[r, t, p],
            ).where[~g.RtIan[r, year, allyear, cur, "INVTAXSUB"]]

        def investment_taxsub_annual(item: str) -> Condition:
            """The pre-calculated annual INVTAX / INVSUB coefficients (see exec1)."""
            return Sum(
                Domain(t, p).where[g.cst_annc[r, t, p, tt, item, cur]],
                g.cst_annc[r, t, p, tt, item, cur]
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws),
            ).where[g.RtIan[r, year, allyear, cur, "INVTAXSUB"]]

        invtax = (
            investment_taxsub(macro.obj_itax_GP) + investment_taxsub_annual("INVTAX")
        ).where[same_as(costcat, "INVTAX")]
        # NB: CST_ANNC holds the subsidies with a negative sign, hence the minus
        invsub = (
            investment_taxsub(macro.obj_isub_GP) - investment_taxsub_annual("INVSUB")
        ).where[same_as(costcat, "INVSUB")]

        # ------------------------------------------------------------------------------
        # Fixed O&M Cost / Taxes / Subsidies
        def fom(
            obj_macro: Callable[..., ImplicitParameter],
            shape_index: str,
            item: str,
            condition: Expression | ImplicitSet,
        ) -> Condition:
            """FOM, FOMTAX and FOMSUB share one formulation, shaped or not."""
            unshaped = Sum(
                Domain(
                    ObjSumiv[ll, r, t, p, jot, life],
                    span[life + Min(Ord(ll) + Ord(jot) - Ord(year) - 1, 0)],
                ).where[condition],
                Sum(
                    g.Invstep[ll, jot, k, jot].where[Yk[allyear, k]],
                    obj_macro(r, k, p, cur)
                    * Max(
                        0,
                        Min(g.yearval[allyear] + 1, g.yearval[k] + Ord(life))
                        - Max(g.yearval[year], g.yearval[k]),
                    ),
                )
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws)
                / obj_diviv[r, t, p],
            )
            shaped = Sum(
                RtpShape[r, t, p, shape_index, j, jj].where[condition],
                Sum(
                    Domain(
                        ObjSumiv[k, r, t, p, jot, life],
                        g.Invstep[k, jot, ll, jot],
                        span[life + Min(Ord(ll) - Ord(year), 0)],
                    ).where[Yk[allyear, ll]],
                    Sum(
                        g.Opyear[life, age].where[
                            (Ord(ll) + Ord(age) > Ord(year)).where[
                                Ord(ll) + Ord(age) < Ord(allyear) + 2
                            ]
                        ],
                        g.shape[j, age] * g.multi[jj, ll + (Ord(age) - 1)] - 1,
                    )
                    * obj_macro(r, ll, p, cur),
                )
                * macro.VAR_NCAP_GP(vart1, r, t, p, sws)
                / obj_diviv[r, t, p],
            )
            return (unshaped + shaped).where[same_as(costcat, item)]

        # NB: unlike the taxes and subsidies, FOM is not conditioned on its coefficient
        fixed_om = fom(macro.obj_fom_GP, "1", "FOM", Yk[tt, t])
        fixed_om_tax = fom(
            macro.obj_ftx_GP,
            "2",
            "FOMTAX",
            Yk[tt, t] & macro.obj_ftx_GP(r, t, p, cur),
        )
        fixed_om_sub = fom(
            macro.obj_fsb_GP,
            "3",
            "FOMSUB",
            Yk[tt, t] & macro.obj_fsb_GP(r, t, p, cur),
        )

        # ------------------------------------------------------------------------------
        # Variable commodity taxes and subsidies
        def commodity_taxsub(item: Literal["TAX", "SUB"]) -> Condition:
            return Sum(
                tpulse_domain,
                tpulse_mult
                * (
                    Sum(
                        g.RhsCombal[r, t, c, s],
                        wrap_in_sum(VART_COMNET[r, t, c, s, *sws], vart_set)
                        * g.obj_comnt[r, YEoh, c, s, item, cur],
                    )
                    + Sum(
                        g.RhsComprd[r, t, c, s],
                        wrap_in_sum(VART_COMPRD[r, t, c, s, *sws], vart_set)
                        * g.obj_compd[r, YEoh, c, s, item, cur],
                    )
                ),
            ).where[same_as(costcat, f"COM{item}")]

        commodity_tax = commodity_taxsub("TAX")
        commodity_sub = commodity_taxsub("SUB")

        # ------------------------------------------------------------------------------
        # Variable flow taxes and subsidies
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        # NB: without an index_set both cal_red variants build an Expression, which
        # is the only return type of theirs that carries .where
        include_cal_red = cast(
            "Expression",
            cal_red_func_GP(
                g=g,
                config=CalRedRedConfig(
                    arg1=c,
                    arg2=Com,
                    arg3=s,
                    arg4=p,
                    arg5=t,
                    arg10=Number(1),
                    pgprim=pgprim,
                    def_rtp_ffcs=def_rtp_ffcs,
                    sow=sow,
                    var=var,
                ),
            ),
        )
        # %SWTD%(%SWSW% ... ): SUM over the SOW mapping of %SWSW%, which carries the
        # state probability when cumulating over the states, or plain parentheses
        flows: Expression | Sum = include_cal_red
        if swtd:
            if not swsw:
                raise ValueError(f"swtd needs the swsw domain: {swtd}")
            swsw_prob: ImplicitParameter | None = swsw[1] if len(swsw) > 1 else None  # type: ignore[misc]
            flows = Sum(
                swsw[0],
                include_cal_red if swsw_prob is None else swsw_prob * include_cal_red,
            )

        # * inter-regional trade
        trade = (
            Sum(
                g.RpcIre[r, p, c, ie],
                wrap_in_sum(VART_IRE[r, v, t, p, c, s, ie, *sws], vart_set).where[
                    ~g.RpcAire[r, p, c]
                ]
                + (
                    wrap_in_sum(VART_ACT[r, v, t, p, s, *sws], vart_set)
                    * g.prc_actflo[r, v, p, c]
                ).where[g.RpcAire[r, p, c]],
            )
            + Sum(
                Domain(g.RpcIre[r, p, Com, ie], io).where[
                    g.RtpcsVarf[r, t, p, Com, s]
                    & g.ire_flosum[r, t, p, Com, s, ie, c, io]
                ],
                g.ire_flosum[r, t, p, Com, s, ie, c, io]
                * (
                    wrap_in_sum(VART_IRE[r, v, t, p, Com, s, ie, *sws], vart_set).where[
                        ~g.RpcAire[r, p, Com]
                    ]
                    + (
                        wrap_in_sum(VART_ACT[r, v, t, p, s, *sws], vart_set)
                        * g.prc_actflo[r, v, p, Com]
                    ).where[g.RpcAire[r, p, Com]]
                ),
            )
        ).where[g.RpIre[r, p]]

        def flow_taxsub(item: Literal["TAX", "SUB"]) -> Condition:
            ftax = macro.obj_ftax_GP(r, YEoh, p, c, ts, cur)
            return Sum(
                t.where[Yk[tt, t] * ((g.m[t] + g.lagt[t]) > g.yearval[year])],
                Sum(
                    g.RtpcsVarf[r, t, p, c, s].where[g.ObjVflo[r, p, c, cur, item]],
                    Sum(
                        g.TsAnn[s, ts],
                        Sum(
                            tpulse_domain,
                            tpulse_mult * Max(0, ftax if item == "TAX" else -ftax),
                        ),
                    )
                    * Sum(
                        g.RtpVintyr[r, v, t, p],
                        flows.where[~g.RpIre[r, p]] + trade,
                    ),
                ),
            ).where[same_as(costcat, f"FLO{item}")]

        flow_tax = flow_taxsub("TAX")
        flow_sub = flow_taxsub("SUB")

        # ------------------------------------------------------------------------------
        # DIAG(COSTYPE,'SUB') flips the sign of the subsidy components
        components = Sum(
            g.CostGmap[costcat, costagg, costype],
            macro.VAR_CUMCST_GP(var, r, year, allyear, costagg, cur, sowend)
            * (1 - Number(2).where[same_as(costype, "SUB")]),
        )

        condition: Condition | Expression | ImplicitParameter = g.reg_cumcst[
            r, year, allyear, costcat, cur, "UP"
        ]
        if swt:
            condition = swt[0] & condition

        eq_bndcst[r, year, g.Superyr[tt, allyear], costcat, cur, *sowstart].where[
            condition
        ] = (
            investment
            + decommissioning
            + invtax
            + invsub
            + fixed_om
            + fixed_om_tax
            + fixed_om_sub
            + commodity_tax
            - commodity_sub
            + flow_tax
            + flow_sub
            + components
            == macro.VAR_CUMCST_GP(var, r, year, allyear, costcat, cur, sowend)
        )

    def exec1(self: EqbndcstMod, declif: str) -> None:
        g = self.tc
        r, t, tt, p, cur, bd = g.r, g.t, g.tt, g.p, g.cur, g.bd
        year, allyear, ll, k = g.year, g.allyear, g.ll, g.k
        age, life, jot, side, ucn = g.age, g.life, g.jot, g.side, g.ucn
        costcat, costagg, costype = g.costcat, g.costagg, g.costype
        f, z, Yk, Yk1, Ykk, KEoh = g.f, g.z, g.Yk, g.Yk1, g.Ykk, g.KEoh
        reg_cumcst, Superyr, Trackp = g.reg_cumcst, g.Superyr, g.Trackp
        ncap_declif = g.get_parameter(f"NCAP_{declif}")

        # -----------------------------------------------------------------------------
        # Construct SUPERYR (needed for filtering)
        Superyr[g.Periodyr[t, ll]].where[g.yearval[ll] <= g.yearval[t]] = True
        Superyr[t + 1, ll].where[
            (g.yearval[ll] > g.yearval[t]).where[g.Periodyr[t, ll]]
        ] = True
        with Loop(g.Miyr1[t.lead(1, "circular")]):
            Superyr[t, ll].where[g.yearval[ll] > g.m[t]] = True
        # Add single MILESTONYR bounds to REG_CUMCST
        reg_cumcst[r, t, t, costagg, cur, bd] = sparse(
            g.reg_bndcst[r, t, costagg, cur, bd]
        )
        # Add infinite bound for components if aggregate bound
        with Loop(Domain(g.CostGmap[costcat, costagg, costype], bd)):
            reg_cumcst[r, year, ll, costagg, cur, "UP"].where[
                (~reg_cumcst[r, year, ll, costagg, cur, "UP"]).where[
                    reg_cumcst[r, year, ll, costcat, cur, bd]
                ]
            ] = SpecialValues.POSINF
        with Loop(g.Bdlox[bd]):
            reg_cumcst[r, year, ll, costcat, cur, "UP"].where[
                (~reg_cumcst[r, year, ll, costcat, cur, "UP"]).where[
                    reg_cumcst[r, year, ll, costcat, cur, bd]
                ]
            ] = SpecialValues.POSINF
        # -----------------------------------------------------------------------------
        # Prepare INVCOST and ITAXSUB coefficients
        with Loop(g.UcAttr[r, ucn, side, "NCAP", "INVCOST"]), Loop(t):
            Trackp[r, p].where[g.uc_ncap[ucn, side, r, t, p]] = True
        g.RtIan[r, t, t, cur, "INV"].where[reg_cumcst[r, t, t, "INV", cur, "UP"]] = True
        g.RtpIan[g.ObjIcur[r, t, p, cur]].where[
            g.RtIan[r, t, t, cur, "INV"] + Trackp[r, p]
        ] = True
        # Calculate annual undiscounted INVCOST coefficients
        Yk1.setRecords(None)
        Yk1[tt, t].where[Yk[t, tt]] = True
        g.cst_annc[r, tt, p, t[year], "INVCOST", cur].where[
            Yk1[tt, t] & g.RtpIan[r, tt, p, cur]
        ] = Sum(
            g.ObjSumii[r, tt, p, age, KEoh[ll], jot].where[
                (Ord(ll) + Ord(age) + Ord(jot) - 1 > Ord(year)).where[Yk[t, ll]]
            ],
            Sum(
                g.Invspred[ll, jot, allyear, k].where[
                    (Ord(allyear) + Ord(age) > Ord(year)).where[Yk[t, allyear]]
                ],
                macro.obj_icost_GP(r, k, p, cur),
            )
            * g.obj_crf[r, tt, p, cur]
            / g.obj_divi[r, tt, p],
        )
        # Add decommissioning costs when defined
        with Loop(g.RtpIan[r, tt, p, cur].where[macro.obj_dcost_GP(r, tt, p, cur)]):
            g.cst_annc[r, tt, p, t[year], "INVCOST", cur].where[Yk1[tt, t]] = (
                g.cst_annc[r, tt, p, t, "INVCOST", cur]
                + g.obj_crfd[r, tt, p, cur]
                / g.obj_diviii[r, tt, p]
                * Sum(
                    g.ObjSumiii[r, tt, p, KEoh, k, ll].where[
                        (Ord(ll) + Round(ncap_declif[r, tt, p]) > Ord(year)).where[
                            Yk[t, ll]
                        ]
                    ],
                    macro.obj_dcost_GP(r, k, p, cur),
                )
            )
        # Calculate annual undiscounted INVTAXSUB coefficients
        Trackp.setRecords(None)
        g.RtpIan.setRecords(None)
        with (
            Loop(g.UcAttr[r, ucn, side, "NCAP", g.UcAnnul[g.ucname[costcat]]]),
            Loop(t),
        ):
            Trackp[r, p].where[g.uc_ncap[ucn, side, r, t, p]] = True
        g.RtIan[r, t, t, cur, "INVTAXSUB"].where[
            reg_cumcst[r, t, t, "INVTAX", cur, "UP"]
            + reg_cumcst[r, t, t, "INVSUB", cur, "UP"]
        ] = True
        g.RtpIan[g.ObjIcur[r, t, p, cur]].where[
            g.RtIan[r, t, t, cur, "INVTAXSUB"] + Trackp[r, p]
        ] = True
        with Loop(
            g.RtpIan[r, tt, p, cur].where[
                macro.obj_itax_GP(r, tt, p, cur) + macro.obj_isub_GP(r, tt, p, cur)
            ]
        ):
            Ykk[allyear, ll, year] = False  # OPTION CLEAR=YKK
            f[...] = g.obj_crf[r, tt, p, cur] / g.obj_divi[r, tt, p]
            with Loop(g.ObjSumii[r, tt, p, life, KEoh, jot]):
                z[...] = Ord(life)
                Ykk[Yk[t[year], ll], k].where[
                    (Ord(year) < Ord(ll) + z).where[g.Invspred[KEoh, jot, ll, k]]
                ] = True
            g.cst_annc[r, tt, p, t, "INVTAX", cur].where[Yk1[tt, t]] = Sum(
                Ykk[t, ll, k], f * macro.obj_itax_GP(r, k, p, cur)
            )
            g.cst_annc[r, tt, p, t, "INVSUB", cur].where[Yk1[tt, t]] = Sum(
                Ykk[t, ll, k], -f * macro.obj_isub_GP(r, k, p, cur)
            )
        Trackp.setRecords(None)
        g.RtpIan.setRecords(None)
