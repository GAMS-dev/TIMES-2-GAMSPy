# coef_ext_cli.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *-----------------------------------------------------------------------------
# * COEF_EXT.cli - Coefficients for the Climate Module Extension
# *-----------------------------------------------------------------------------
# * Questions/Comments:
# *
# *-----------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import (
    Card,
    Domain,
    Else,
    For,
    If,
    Loop,
    Number,
    Ord,
    Smax,
    Smin,
    SpecialValues,
    Sum,
)
from gamspy.math import (
    Max,
    Min,
    Round,
    aggregate,
    diag,
    exp,
    log,
    mod,
    power,
    project,
    same_as,
)

from core.base_class import GamsClass
from core.fillsow_stc import FillsowStc, exec_fillsow_stc

# from core.fillparm_gms import FillparmGms
from core.filparam_gms import FilparamGms, FilparamGmsConfig

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class CoefExtCli(GamsClass):
    """Translation unit for coef_ext.cli."""

    # Instance attributes
    module_name: str = "coef_ext_cli"
    gams_source: str = "coef_ext.cli"

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
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        g = self.tc
        if self.arg1 == "SLOPE":
            self.tc.enqueue(self.exec_slope)
            return

        self.tc.enqueue(self.exec1)

        if self.env.cm_calib.upper() == "B":
            self.tc.enqueue(self.exec2)

        if self.env.cm_calib.upper() == "M":
            self.tc.enqueue(self.exec3)

        self.tc.enqueue(self.exec4)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                FilparamGmsConfig(
                    src=g.cm_history,
                    arg2=(),
                    tail1=(g.CmHists,),
                    arg4=("", "", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Fil,
                ),
            )
        )

        self.tc.enqueue(self.exec4_2)

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.cm_stats,
                    arg2=(g.CmHists,),
                    tail1=(g.CmBox,),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Fil,
                ),
            )
        )

        self.tc.enqueue(self.exec5)

        if self.env.stages.upper() == "YES":
            self.tc.enqueue(self.exec6)

        if self.tc.defined("DAM_COST"):
            self.tc.enqueue(self.exec7)

        self.tc.enqueue(self.exec8, stages=self.env.stages.upper() == "YES")

        # * Interpolate BEMI and BEOH over FIL (mucks-up F, Z, MY_F, MY_FYEAR, FIRST_VAL, LAST_VAL)
        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.cm_bemi,
                    arg2=(g.CmEmis,),
                    tail1=(),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Fil,
                ),
            )
        )

        self.include(
            FilparamGms(
                self.tc,
                self.env,
                config=FilparamGmsConfig(
                    src=g.cm_evar,
                    arg2=(g.CmEmis,),
                    tail1=(),
                    arg4=("", "", "", "", ""),
                    arg5=g.ll,
                    arg6=g.Fil,
                ),
            )
        )

        self.tc.enqueue(self.exec11, stages=self.env.stages)

        self.tc.enqueue(self.exec12)

        # * Prepare input parameters
        # *-----------------------------------------------------------------------------
        # * Interpolate parameters by default or if requested by user:
        batincludes: list[FilparamGmsConfig] = [
            FilparamGmsConfig(
                src=g.cm_linfor,
                arg2=(),
                tail1=(g.CmVar, g.lim),
                arg4=("", "", "", "", ""),
                arg5=g.Datayear,
                arg6=g.Fil,
            ),
            FilparamGmsConfig(
                src=g.cm_maxco2c,
                arg2=(),
                tail1=(),
                arg4=("", "", "", "", "", ""),
                arg5=g.ll,
                arg6=g.t,
                arg9=-1,
            ),
            FilparamGmsConfig(
                src=g.cm_maxc,
                arg2=(),
                tail1=(g.cg,),
                arg4=("", "", "", "", "", ""),
                arg5=g.ll,
                arg6=g.Fil,
                arg9=-1,
            ),
            FilparamGmsConfig(
                src=g.cm_exoforc,
                arg2=(),
                tail1=(),
                arg4=("", "", "", "", "", ""),
                arg5=g.ll,
                arg6=g.MyFil,
            ),
            FilparamGmsConfig(
                src=g.uc_cli,
                arg2=(g.ucn, g.side, g.r),
                tail1=(g.CmVar,),
                arg4=("", "", ""),
                arg5=g.Datayear,
                arg6=g.t,
            ),
        ]

        if self.env.stages.upper() == "YES":
            batincludes.append(
                FilparamGmsConfig(
                    src=g.s_cm_maxco2c,
                    arg2=(),
                    tail1=(g.j, g.ww),
                    arg4=("", "", "", "", ""),
                    arg5=g.Datayear,
                    arg6=g.t,
                    arg7=g.SwTstg[g.t, g.j],
                    arg9=-1,
                )
            )
            batincludes.append(
                FilparamGmsConfig(
                    src=g.s_cm_maxc,
                    arg2=(),
                    tail1=(g.cg, g.j, g.ww),
                    arg4=("", "", "", ""),
                    arg5=g.Datayear,
                    arg6=g.t,
                    arg7=g.SwTstg[g.t, g.j],
                    arg9=-1,
                )
            )

        for config in batincludes:
            self.include(FilparamGms(self.tc, self.env, config=config))

        self.tc.enqueue(self.exec15)

        if self.env.stages.upper() != "YES":
            self.tc.enqueue(self.exec_slope)
            return

        self.tc.enqueue(self.exec16)

        self.include(
            FillsowStc(
                self.tc,
                self.env,
                arg1="CM_MAXC",
                arg2="",
                arg3="CG",
                arg4="LL",
                arg5="YES",
                arg6="SUPERYR(T,LL)",
                arg7="YES",
            )
        )

    def exec_slope(self: CoefExtCli) -> None:
        coef_ext_cli_slope_GP(self.tc)
        # self.tc.add_gams_code(module=self, phase="run", code=coef_ext_cli_slope())

    def exec1(self: CoefExtCli) -> None:
        g = self.tc
        # * Set up the history calibration values
        # * If calibration values are not provided by user, use the defaults:
        g.cm_const[g.CmHists] = 0.0
        with Loop(Domain(g.ll, g.CmHists).where[g.cm_history[g.ll, g.CmHists]]):
            g.cm_const[g.CmHists] = SpecialValues.EPS
        sparseExpr = g.cm_default[g.ll, g.CmHists]
        g.cm_history[g.ll, g.CmHists].where[~(g.cm_const[g.CmHists]) & sparseExpr] = (
            sparseExpr
        )
        # * Pick up the appropriate calibration values for the calibration year;
        g.cm_calib[...] = 1.0

    def exec2(self: CoefExtCli) -> None:
        g = self.tc
        g.cm_calib[...] = Sum(g.Miyr1[g.t], g.m[g.t] - g.b[g.t]) + 1.0

    def exec3(self: CoefExtCli) -> None:
        self.tc.cm_calib[...] = SpecialValues.EPS

    def exec4(self: CoefExtCli) -> None:
        g = self.tc
        # * Inter-/extrapolate calibration values
        g.Fil.setRecords(None)
        with Loop(g.Miyr1[g.ll]):
            g.Fil[g.ll - g.cm_calib] = True

    def exec4_2(self: CoefExtCli) -> None:
        g = self.tc
        g.cm_stat0[g.CmHists, g.CmBox] = 0.0
        g.CmUsubs[g.CmHists] = g.CmEmis[g.CmHists].where[~(g.CmHists.sameAs("CO2-GTC"))]
        with Loop(
            Domain(g.CmHists, g.ll, g.CmBox).where[g.cm_stats[g.CmHists, g.ll, g.CmBox]]
        ):
            g.cm_stat0[g.CmHists, g.CmBox] = SpecialValues.EPS
        with Loop(
            g.CmBoxmap[g.CmHists, g.CmVar, g.CmBox[g.cmq]].where[
                ~(g.cm_stat0[g.CmHists, g.cmq])
            ]
        ):
            g.cm_stats[g.CmHists, g.ll, g.cmq].where[g.cm_history[g.ll, g.CmVar]] = (
                g.cm_history[g.ll, g.CmVar]
                * power(g.cm_ppm[g.CmHists], -Number(1.0).where[g.CmUsubs[g.CmHists]])
            )

    def exec5(self: CoefExtCli) -> None:
        g = self.tc
        # * Pick the history values
        with Loop(Domain(g.Miyr1[g.ll], g.year[g.ll - g.cm_calib])):
            g.cm_stat0[g.CmHists, g.CmBox] = g.cm_stats[
                g.CmHists, g.year, g.CmBox
            ] * power(g.cm_ppm[g.CmHists], Number(1.0).where[g.CmUsubs[g.CmHists]])
        g.cm_stat0[g.CmHists, "N"] = 0.0
        # *-----------------------------------------------------------------------------
        # * Preprocess concentration decays
        g.cm_decay["CH4-MT", "ATM"] = g.cm_const["PHI-CH4"]
        g.cm_decay["N2O-MT", "ATM"] = g.cm_const["PHI-N2O"]
        sparseExpr = g.cm_decay[g.CmEmis, "N"]
        g.cm_decay[g.CmEmis, "ATM"].where[sparseExpr] = sparseExpr
        g.cm_decay[g.CmEmis, g.cmq[g.lA]] = 0.0
        g.cm_decay[g.CmEmis, g.CmBox].where[g.cm_stat0[g.CmEmis, g.CmBox]] = (
            g.cm_decay[g.CmEmis, g.CmBox] + SpecialValues.EPS
        )
        g.CmAtmap[g.CmEmis, g.CmEmis].where[~(Sum(g.CmAtmap[g.CmEmis, g.CmVar], 1))] = (
            True
        )
        with Loop(g.CmEmis.where[~(Sum(g.CmBoxmap[g.CmEmis, g.CmVar, g.CmBox], 1))]):
            g.CmBoxmap[g.CmAtmap[g.CmEmis, g.CmVar], g.CmBox].where[
                g.cm_decay[g.CmEmis, g.CmBox]
            ] = True
        # * Coupled concentrations
        with Loop(
            g.CmCoupmap[g.CmVar, g.CmEmis, "ATM"].where[g.cm_stat0[g.CmEmis, "UP"]]
        ):
            g.cm_decay[g.CmEmis, "N"] = g.cm_decay[g.CmEmis, "ATM"]
            g.CmBoxmap[g.CmEmis, g.CmEmis, "N"] = True
        # * Reference concentration
        g.cm_couple[g.CmVar, g.t, g.CmEmis, "FX"].where[
            (
                (g.cm_couple[g.CmVar, g.t, g.CmEmis, "FX"] <= 0.0).where[
                    g.cm_couple[g.CmVar, g.t, g.CmEmis, "ATM"]
                ]
            )
        ] = g.cm_stat0[g.CmEmis, "ATM"] * g.cm_decay[g.CmEmis, "ATM"]
        # * Reference life and final unit life coefficient
        g.cm_couple[g.CmVar, g.t, g.CmEmis, "N"].where[
            g.cm_couple[g.CmVar, g.t, g.CmEmis, "ATM"]
        ] = (
            (
                g.cm_couple[g.CmVar, g.t, g.CmEmis, "FX"]
                + g.cm_stat0[g.CmEmis, "UP"] / g.cm_stat0[g.CmEmis, "LIFE"]
            )
            * g.cm_decay[g.CmEmis, "ATM"]
            / g.cm_ppm[g.CmVar]
        )
        project(source=g.cm_couple, target=g.CmCoupmap)
        # *-----------------------------------------------------------------------------
        # * Set up the 3x3 PHI matrix for emissions
        if (
            Sum([g.CmBox, g.CmBuck], g.cm_phi["CO2-GTC", g.CmBox, g.CmBuck]).toValue()
            == 0
        ):
            # * Set up the 3x3 PHI matrix
            g.cm_phi["CO2-GTC", "ATM", "UP"] = g.cm_const["PHI-UP-AT"]
            g.cm_phi["CO2-GTC", "UP", "ATM"] = g.cm_const["PHI-AT-UP"]
            g.cm_phi["CO2-GTC", "UP", "LO"] = g.cm_const["PHI-LO-UP"]
            g.cm_phi["CO2-GTC", "LO", "UP"] = g.cm_const["PHI-UP-LO"]

        # * Default first-order decay models for CH4 and N2O
        with Loop(g.CmUsubs[g.CmEmis]):  # noqa: SIM117
            with If(~(Sum([g.CmBox, g.CmBuck], g.cm_phi[g.CmEmis, g.CmBox, g.CmBuck]))):
                g.cm_phi[g.CmEmis, g.CmBox, g.CmBox].where[
                    g.cm_decay[g.CmEmis, g.CmBox]
                ] = 1.0 - g.cm_decay[g.CmEmis, g.CmBox] + SpecialValues.EPS
                g.cm_phi[g.CmEmis, "UP", g.CmEmis] = Number(SpecialValues.EPS).where[
                    g.cm_stat0[g.CmEmis, "UP"]
                ]
        # *-----------------------------------------------------------------------------
        # * Set emission kinds and FORCING to CM_KIND when active
        g.CmKind[g.CmVar].where[
            (
                Sum(
                    Domain(g.CmBox, g.CmBuck).where[
                        g.cm_phi[g.CmVar, g.CmBox, g.CmBuck]
                    ],
                    1,
                ).where[g.CmEmis[g.CmVar]]
            )
        ] = True
        g.CmEmis[g.CmVar] = g.CmKind[g.CmVar].where[g.cm_ppm[g.CmVar]]
        g.CmKind["FORCING"] = Number(1).where[
            (Sum(g.ll.where[g.cm_maxc[g.ll, "DELTA-ATM"]], 1) + (Card(g.CmEmis) > 1))
        ]
        # since Card is not zero if records exist
        if g.uc_cli.records:
            g.CmKind["FORCING"] = True
        g.CmTkind[g.CmKind] = True
        with Loop(
            g.CmForcmap[g.CmVar, g.CmHists].where[
                Sum(g.ll.where[g.cm_maxc[g.ll, g.CmVar]], 1)
            ]
        ):
            g.CmTkind[g.CmVar] = True
        g.CmForcmap["FORC-KYO", g.CmVar].where[
            ~(g.CmForcmap[g.CmVar, g.CmVar]) & g.cm_ppm[g.CmVar]
        ] = g.cm_ppm[g.CmVar]
        g.CmForcmap["FORCING", g.CmVar].where[g.cm_ppm[g.CmVar]] = g.cm_ppm[g.CmVar]
        g.CmForcmap[g.CmHists, g.CmVar].where[
            (
                Sum(g.CmEmis.where[g.CmForcmap[g.CmVar, g.CmEmis]], 1).where[
                    ~(g.CmEmis[g.CmVar])
                ]
            )
        ] = False

    def exec6(self: CoefExtCli) -> None:
        g = self.tc
        g.CmKind["FORCING"].where[
            Sum(
                Domain(g.ll, g.j, g.w).where[g.s_cm_maxc[g.ll, "DELTA-ATM", g.j, g.w]],
                1,
            )
        ] = True

    def exec7(self: CoefExtCli) -> None:
        g = self.tc
        g.CmKind["FORCING"].where[
            Sum(
                g.r.where[(g.dam_bqty[g.r, "FORCING"] + g.dam_bqty[g.r, "DELTA-ATM"])],
                1,
            )
        ] = True

    def exec8(self: CoefExtCli, stages: bool) -> None:
        g = self.tc
        # *-----------------------------------------------------------------------------
        # * Establish set of years beyond EOH
        # * Set extended EOH (EXT-EOH) year into FIL; -1 deactivates EOH extension
        g.Fil.setRecords(None)
        g.yr_vl[...] = 0.0
        g.first_val[...] = g.cm_const["EXT-EOH"]
        if g.first_val.toValue() > 0.0:
            g.first_val[...] = Round(Max(g.miyr_vl, g.first_val))
            with Loop(g.Miyr1[g.ll]):
                g.f[...] = g.first_val - g.yearval[g.ll]
                g.Fil[g.ll + g.f] = True
            g.cm_bemi[g.CmEmis, g.Fil] = SpecialValues.EPS
            g.cm_evar[g.CmEmis, g.Fil] = 1.0
            # * Set all MAXC year beyond EOH into FIL
            if stages:
                aggregate(source=g.s_cm_maxc, target=g.cm_maxc_m)
            g.f[...] = Smax(g.t[g.ll], Ord(g.ll))
            g.cm_maxc_m[g.CmVar, g.ll].where[g.cm_maxc[g.ll, g.CmVar]] = (
                SpecialValues.EPS
            )
            with Loop(  # noqa: SIM117
                Domain(g.ll, g.CmVar[g.cg]).where[
                    ((Ord(g.ll) > g.f).where[g.cm_maxc_m[g.cg, g.ll]])
                ]
            ):
                with If(
                    (g.yearval[g.ll] > g.first_val | ~(g.CmEmis[g.CmVar])).where[
                        g.yearval[g.ll]
                    ]
                ):
                    g.yr_vl[...] = Ord(g.ll)  # type: ignore [assignment]
                    g.Fil[g.ll] = True
            g.Fil[g.ll].where[(Ord(g.ll) > g.yr_vl)] = False
            # * Set BEMI to MAXC emissions for years beyond EXT-EOH and zero at EXT-EOH
            g.cm_bemi[g.CmEmis[g.CmHists[g.cg]], g.Fil[g.ll]].where[
                (g.yearval[g.ll] > g.first_val)
            ] = g.cm_maxc[g.ll, g.cg]
            g.cm_evar[g.CmEmis, g.Fil[g.ll]].where[(g.yearval[g.ll] > g.first_val)] = (
                Number(SpecialValues.EPS).where[g.cm_bemi[g.CmEmis, g.ll]]
            )
            # * Set EOH contribution to zero at final year (deactivated for now)
            # *   LOOP(MIYR_1(YEAR), CM_EVAR(CM_EMIS,YEAR+(YR_VL-ORD(YEAR))) = EPS);
            # * Set all years Modulo BEOHMOD to FIL
            g.my_f[...] = Round(Max(1.0, g.cm_const["BEOHMOD"]))
            g.Fil[g.ll].where[
                ((Ord(g.ll) < g.yr_vl).where[(mod(g.yearval[g.ll], g.my_f) == 0.0)])
            ] = Number(1).where[(Ord(g.ll) > g.f)]

        g.cm_maxc[g.ll, g.CmEmis[g.CmHists[g.cg]]].where[
            (g.yearval[g.ll] > g.miyr_vl)
        ] = 0.0
        # * Complete CM_LED
        with Loop(g.Fil[g.ll]):
            g.z[...] = Ord(g.ll)  # type: ignore [assignment]
            g.cm_led[g.ll] = g.z - g.f
            g.f[...] = g.z
        g.cm_led[g.t] = g.lead[g.t]
        g.cm_led[g.Miyr1] = g.cm_calib
        g.Pret[g.t, g.t - 1] = True

    def exec11(self: CoefExtCli, stages: str) -> None:
        g = self.tc

        g.cm_evar[g.CmEmis, g.t] = 1

        # -----------------------------------------------------------------------------

        if "FORCING" in g.CmKind.toList():
            g.cm_sig1[g.Sow] = g.cm_const["SIGMA1"]

            # * Set up the 2x2 SIG matrix for forcing
            if stages.upper() == "YES":
                # fmt: off
                batincludes = [
                    ("CM_CONST", "CM_STCC", '', '', "YES", "YES", "YES"),
                    ("DAM_COST", 'R,', '"DELTA-ATM",CUR', "TT", "YES", "YES", "NO")
                ]
                # fmt: on
                for arg in batincludes:
                    exec_fillsow_stc(
                        module=self,
                        arg1=arg[0],
                        arg2=arg[1],
                        arg3=arg[2],
                        arg4=arg[3],
                        arg5=arg[4],
                        arg6=arg[5],
                        arg7=arg[6],
                    )
            if stages.upper() == "YES":
                g.cm_sig1[g.Sow] = g.s_cm_const["SIGMA1", "1", g.Sow]
                g.cm_sig[g.Sow, "ATM", "ATM"] = 1.0 - g.cm_sig1[g.Sow] * (
                    g.cm_const["GAMMA"] / g.s_cm_const["CS", "1", g.Sow]
                    + g.cm_const["SIGMA2"]
                )
            else:
                g.cm_sig["1", "ATM", "ATM"] = 1.0 - g.cm_sig1["1"] * (
                    g.cm_const["LAMBDA"] + g.cm_const["SIGMA2"]
                )
            g.cm_sig[g.Sow, "ATM", "LO"] = g.cm_sig1[g.Sow] * g.cm_const["SIGMA2"]
            g.cm_sig[g.Sow, "LO", "ATM"] = g.cm_const["SIGMA3"]
            g.cm_sig[g.Sow, "LO", "LO"] = 1.0 - g.cm_const["SIGMA3"]
            g.cm_phi["FORCING", "ATM", "FORCING"] = 1.0
            # * Intialize CM_AA to the identity matrix, CM_BB to zero
            g.cm_aa["FORCING", g.ll, g.Sow, g.CmBuck, g.CmBox].where[g.cm_led[g.ll]] = (
                diag(g.CmBuck, g.CmBox)
            )
            g.cm_bb["FORCING", g.ll, g.Sow, g.CmBuck].where[g.cm_led[g.ll]] = 0.0
            g.cnt[...] = 0.0
            # * Assume linear evolution of forcing between milestone years
            with Loop(Domain(g.CmVar["FORCING"], g.ll).where[g.cm_led[g.ll]]):
                with If(g.cnt):
                    g.cnt[...] = 1.0
                    g.z[...] = g.cm_led[g.ll]
                with Else():  # type: ignore
                    g.cnt[...] = SpecialValues.EPS
                    g.z[...] = g.cm_calib
                with For(g.f, 0.0, g.z - 1.0):  # type: ignore
                    g.my_f[...] = g.f / g.z * g.cnt
                    g.cm_bb[g.CmVar, g.ll, g.Sow, g.CmBox] = (
                        g.cm_bb[g.CmVar, g.ll, g.Sow, g.CmBox]
                        + g.cm_sig1[g.Sow]
                        * (1.0 - g.my_f)
                        * g.cm_aa[g.CmVar, g.ll, g.Sow, g.CmBox, "ATM"]
                    )
                    g.cm_cc[g.CmVar, g.ll, g.Sow, g.CmBox] = (
                        g.cm_cc[g.CmVar, g.ll, g.Sow, g.CmBox]
                        + g.cm_sig1[g.Sow]
                        * g.my_f
                        * g.cm_aa[g.CmVar, g.ll, g.Sow, g.CmBox, "ATM"]
                    )
                    g.cm_aa[g.CmVar, g.ll, g.Sow, g.CmBuck, g.CmBox] = Sum(
                        g.cmq.where[g.CmBox[g.cmq]],
                        g.cm_aa[g.CmVar, g.ll, g.Sow, g.CmBuck, g.cmq]
                        * g.cm_sig[g.Sow, g.cmq, g.CmBox],
                    )

    def exec12(self: CoefExtCli) -> None:
        g = self.tc
        # *-----------------------------------------------------------------------------
        # * Set up control set CM_CONC for the BOX equations; complete PHI
        project(source=g.CmBoxmap, target=g.CmConc, direction="left")
        g.cm_phi[g.CmKind, g.CmBox, g.CmBox].where[
            ~(g.cm_phi[g.CmKind, g.CmBox, g.CmBox])
        ] = Number(1.0).where[g.cm_stat0[g.CmKind, g.CmBox]] - Sum(
            g.CmBuck.where[~(same_as(g.CmBox, g.CmBuck))],
            g.cm_phi[g.CmKind, g.CmBuck, g.CmBox],
        )
        # *-----------------------------------------------------------------------------
        # * Calculate the ith powers of PHI, i=1...Z, where Z = LEAD(T)
        # * First intialize CM_AA to the identity matrix, and CM_BB(T,1) to 0:
        with Loop(g.CmEmis[g.CmVar]):
            g.cm_phi[g.CmVar, "ATM", g.CmVar].where[
                ~(Sum(g.CmBox.where[g.cm_phi[g.CmVar, "ATM", g.CmVar]], 1))
            ] = 1.0
            g.cm_aa[g.CmVar, g.ll, "1", g.CmBuck, g.CmBox].where[g.cm_led[g.ll]] = diag(
                g.CmBuck, g.CmBox
            )
            g.cm_bb[g.CmVar, g.ll, "1", g.CmBuck].where[g.cm_led[g.ll]] = 0.0
            g.cnt[...] = g.altobj != 3.0
            # * Loop over MILESTONYR and calculate rest of the powers of PHI
            with Loop(g.t.where[(g.altobj != 3.0)]):
                with If(Ord(g.t) > 1.0):
                    g.my_f[...] = g.m[g.t] - g.b[g.t] + 1.0
                    g.z[...] = g.lead[g.t]
                with Else():  # type: ignore
                    g.my_f[...] = g.cm_calib
                    g.z[...] = g.my_f
                with For(g.f, 1.0, g.z):
                    with If(g.f <= g.my_f):
                        g.cm_bb[g.CmVar, g.t, "1", g.CmBox] = g.cm_bb[
                            g.CmVar, g.t, "1", g.CmBox
                        ] + Sum(
                            g.CmBuck,
                            g.cm_phi[g.CmVar, g.CmBuck, g.CmVar]
                            * g.cm_aa[g.CmVar, g.t, "1", g.CmBox, g.CmBuck],
                        )
                    with Else():  # type: ignore
                        g.cm_cc[g.CmVar, g.t, "1", g.CmBox] = g.cm_cc[
                            g.CmVar, g.t, "1", g.CmBox
                        ] + Sum(
                            g.CmBuck,
                            g.cm_phi[g.CmVar, g.CmBuck, g.CmVar]
                            * g.cm_aa[g.CmVar, g.t, "1", g.CmBox, g.CmBuck],
                        )
                    g.cm_aa[g.CmVar, g.t, "1", g.CmBuck, g.CmBox] = Sum(
                        g.cmq.where[g.CmBox[g.cmq]],
                        g.cm_aa[g.CmVar, g.t, "1", g.CmBuck, g.cmq]
                        * g.cm_phi[g.CmVar, g.cmq, g.CmBox],
                    )
            # * If linear evolution formulation, assume linear evolution of emissions
            with Loop(
                g.ll.where[(((g.altobj == 3.0) | ~(g.t[g.ll])).where[g.cm_led[g.ll]])]
            ):
                with If(g.cnt):
                    g.cnt[...] = 1.0
                    g.z[...] = g.cm_led[g.ll]
                with Else():  # type: ignore
                    g.cnt[...] = SpecialValues.EPS
                    g.z[...] = g.cm_calib
                with For(g.f, 0.0, g.z - 1.0):  # type: ignore
                    g.my_f[...] = g.f / g.z * g.cnt
                    g.cm_bb[g.CmVar, g.ll, "1", g.CmBox] = g.cm_bb[
                        g.CmVar, g.ll, "1", g.CmBox
                    ] + (1.0 - g.my_f) * Sum(
                        g.CmBuck,
                        g.cm_phi[g.CmVar, g.CmBuck, g.CmVar]
                        * g.cm_aa[g.CmVar, g.ll, "1", g.CmBox, g.CmBuck],
                    )
                    g.cm_cc[g.CmVar, g.ll, "1", g.CmBox] = g.cm_cc[
                        g.CmVar, g.ll, "1", g.CmBox
                    ] + g.my_f * Sum(
                        g.CmBuck,
                        g.cm_phi[g.CmVar, g.CmBuck, g.CmVar]
                        * g.cm_aa[g.CmVar, g.ll, "1", g.CmBox, g.CmBuck],
                    )
                    g.cm_aa[g.CmVar, g.ll, "1", g.CmBuck, g.CmBox] = Sum(
                        g.cmq.where[g.CmBox[g.cmq]],
                        g.cm_aa[g.CmVar, g.ll, "1", g.CmBuck, g.cmq]
                        * g.cm_phi[g.CmVar, g.cmq, g.CmBox],
                    )
        # *-----------------------------------------------------------------------------
        # * Prepare commodity variables for emissions:
        g.cm_ghgmap[g.r, g.c, "CO2-GTC"].where[g.cm_co2gtc[g.r, g.c]] = g.cm_co2gtc[
            g.r, g.c
        ]
        with Loop(
            Domain(g.r, g.c, g.CmKind[g.CmVar[g.cg]]).where[g.cm_ghgmap[g.r, g.c, g.cg]]
        ):
            g.RhsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s]] = True
            g.RcsCombal[g.RtcsVarc[g.r, g.t, g.c, g.s], "FX"] = True
        # *-----------------------------------------------------------------------------
        # * Construct SUPERYR (needed in MAX constraints)
        g.Superyr[g.Periodyr[g.t, g.ll]].where[(g.yearval[g.ll] <= g.yearval[g.t])] = (
            True
        )
        g.Superyr[g.t + 1, g.ll].where[
            ((g.yearval[g.ll] > g.yearval[g.t]).where[g.Periodyr[g.t, g.ll]])
        ] = True
        with Loop(g.Miyr1[g.t + +1]):
            g.Superyr[g.t, g.ll].where[(g.yearval[g.ll] > g.m[g.t])] = True
        project(source=g.cm_led, target=g.Fil)
        project(source=g.Y, target=g.MyFil)
        g.MyFil[g.ll].where[
            ((g.yearval[g.ll] > g.miyr_vl).where[(Ord(g.ll) <= g.yr_vl)])
        ] = True

    def exec15(self: CoefExtCli) -> None:
        g = self.tc
        # * Convert all concentration bounds to PPM basis
        g.cm_maxc[g.ll, g.cg["CO2-PPM"]].where[g.cm_maxco2c[g.ll]] = Min(
            g.cm_maxc[g.ll, g.cg]
            + Number(SpecialValues.POSINF).where[~(g.cm_maxc[g.ll, g.cg])],
            g.cm_maxco2c[g.ll] / g.cm_ppm["CO2-GTC"],
        )
        g.cm_maxc[g.ll, g.cg["CO2-PPM"]].where[g.cm_maxc[g.ll, "CO2-ATM"]] = Min(
            g.cm_maxc[g.ll, g.cg]
            + Number(SpecialValues.POSINF).where[~(g.cm_maxc[g.ll, g.cg])],
            g.cm_maxc[g.ll, "CO2-ATM"] * g.cm_const["CO2-PREIND"] / g.cm_ppm["CO2-GTC"],
        )
        g.cm_maxc[g.ll, g.cg["CO2-PPM"]].where[
            (g.cm_maxc[g.ll, "FORCING"] * ~(g.CmKind["FORCING"]))
        ] = Min(
            g.cm_maxc[g.ll, g.cg]
            + Number(SpecialValues.POSINF).where[~(g.cm_maxc[g.ll, g.cg])],
            g.cm_const["CO2-PREIND"]
            / g.cm_ppm["CO2-GTC"]
            * exp(
                (g.cm_maxc[g.ll, "FORCING"] - g.cm_exoforc[g.ll])
                * log(2.0)
                / g.cm_const["GAMMA"]
            ),
        )
        # * Remove bounds from years with undefined concentration
        g.f[...] = Smin(g.t, g.yearval[g.t])
        g.cm_maxc[g.ll, g.cg].where[(g.yearval[g.ll] < g.f)] = 0.0

    def exec16(self: CoefExtCli) -> None:
        g = self.tc
        g.s_cm_maxc[g.ll, g.cg["CO2-PPM"], g.j, g.w].where[
            g.s_cm_maxco2c[g.ll, g.j, g.w]
        ] = Min(
            g.s_cm_maxc[g.ll, g.cg, g.j, g.w]
            + Number(SpecialValues.POSINF).where[~(g.s_cm_maxc[g.ll, g.cg, g.j, g.w])],
            g.s_cm_maxco2c[g.ll, g.j, g.w] / g.cm_ppm["CO2-GTC"],
        )
        g.s_cm_maxc[g.ll, g.cg["CO2-PPM"], g.j, g.w].where[
            g.s_cm_maxc[g.ll, "CO2-ATM", g.j, g.w]
        ] = Min(
            g.s_cm_maxc[g.ll, g.cg, g.j, g.w]
            + Number(SpecialValues.POSINF).where[~(g.s_cm_maxc[g.ll, g.cg, g.j, g.w])],
            g.s_cm_maxc[g.ll, "CO2-ATM", g.j, g.w]
            * g.cm_const["CO2-PREIND"]
            / g.cm_ppm["CO2-GTC"],
        )
        g.s_cm_maxc[g.ll, g.cg["CO2-PPM"], g.j, g.w].where[
            (g.s_cm_maxc[g.ll, "FORCING", g.j, g.w] * ~(g.CmKind["FORCING"]))
        ] = Min(
            g.s_cm_maxc[g.ll, g.cg, g.j, g.w]
            + Number(SpecialValues.POSINF).where[~(g.s_cm_maxc[g.ll, g.cg, g.j, g.w])],
            g.cm_const["CO2-PREIND"]
            / g.cm_ppm["CO2-GTC"]
            * exp(
                (g.s_cm_maxc[g.ll, "FORCING", g.j, g.w] - g.cm_exoforc[g.ll])
                * log(2.0)
                / g.cm_const["GAMMA"]
            ),
        )
        g.s_cm_maxc[g.ll, g.cg, g.j, g.w].where[(g.yearval[g.ll] < g.f)] = 0.0


def coef_ext_cli_slope() -> str:
    return r"""
*-----------------------------------------------------------------------------
* Calculate linear slope for FORCING from CO2
IF(CM_KIND('FORCING'),OPTION FIL<CM_LED;
LOOP(CM_ATMAP(CM_EMIS,CM_VAR),CM_LINFOR(FIL(LL),CM_EMIS,L) $= CM_LINFOR(LL,CM_VAR,L));
CM_LINFOR(FIL(LL),'CO2-GTC',BDNEQ) $= CM_LINFOR(LL,'CO2-ATM',BDNEQ)*CM_CONST('CO2-PREIND')*(1/CM_PPM('CO2-GTC'));
MY_ARRAY(FIL(LL)) = MAX(CM_LINFOR(LL,'CO2-GTC','LO'),
    ((CM_LINFOR(LL,'CO2-GTC','UP')-CM_LINFOR(LL,'CO2-GTC','LO')) /
    LOG(MAX(1.001,CM_LINFOR(LL,'CO2-GTC','UP')/CM_LINFOR(LL,'CO2-GTC','LO')))))$(CM_LINFOR(LL,'CO2-GTC','LO') GT 0);
CM_LINFOR(FIL(LL),'CO2-GTC','N')$MY_ARRAY(LL) = CM_CONST('GAMMA')/MY_ARRAY(LL)/LOG(2);
CM_LINFOR(FIL(LL),'CO2-GTC','FX')$MY_ARRAY(LL) =
    (CM_CONST('GAMMA')/LOG(2) *
    LOG(MY_ARRAY(LL)*CM_LINFOR(LL,'CO2-GTC','LO')/POWER(CM_CONST('CO2-PREIND')/CM_PPM('CO2-GTC'),2)) -
    CM_LINFOR(LL,'CO2-GTC','N')*(MY_ARRAY(LL)+CM_LINFOR(LL,'CO2-GTC','LO')))/2);
*-----------------------------------------------------------------------------
* If EXOFORCING is not provided by the user, use default values
IF(NOT SUM(T,CM_EXOFORC(T)),CM_EXOFORC(MY_FIL(LL)) = MIN(1.15, -0.1965 + 0.013465 * (YEARVAL(LL)-1995)));
"""


def coef_ext_cli_slope_GP(g: TimesModelClass) -> None:
    # * Calculate linear slope for FORCING from CO2
    if g.CmKind["FORCING"].records is not None:
        project(source=g.cm_led, target=g.Fil)
        with Loop(g.CmAtmap[g.CmEmis, g.CmVar]):
            sparseExpr = g.cm_linfor[g.ll, g.CmVar, g.lA]
            g.cm_linfor[g.Fil[g.ll], g.CmEmis, g.lA].where[sparseExpr] = sparseExpr
        sparseExpr = (
            g.cm_linfor[g.ll, "CO2-ATM", g.Bdneq]  # type: ignore
            * g.cm_const["CO2-PREIND"]
            * (1.0 / g.cm_ppm["CO2-GTC"])
        )
        g.cm_linfor[g.Fil[g.ll], "CO2-GTC", g.Bdneq].where[sparseExpr] = sparseExpr
        g.my_array[g.Fil[g.ll]] = Max(
            g.cm_linfor[g.ll, "CO2-GTC", "LO"],
            (
                (
                    g.cm_linfor[g.ll, "CO2-GTC", "UP"]
                    - g.cm_linfor[g.ll, "CO2-GTC", "LO"]
                )
                / log(
                    Max(
                        1.001,
                        g.cm_linfor[g.ll, "CO2-GTC", "UP"]
                        / g.cm_linfor[g.ll, "CO2-GTC", "LO"],
                    )
                )
            ),
        ).where[(g.cm_linfor[g.ll, "CO2-GTC", "LO"] > 0.0)]
        g.cm_linfor[g.Fil[g.ll], "CO2-GTC", "N"].where[g.my_array[g.ll]] = (
            g.cm_const["GAMMA"] / g.my_array[g.ll] / log(2.0)
        )
        g.cm_linfor[g.Fil[g.ll], "CO2-GTC", "FX"].where[g.my_array[g.ll]] = (
            g.cm_const["GAMMA"]
            / log(2.0)
            * log(
                g.my_array[g.ll]
                * g.cm_linfor[g.ll, "CO2-GTC", "LO"]
                / power(g.cm_const["CO2-PREIND"] / g.cm_ppm["CO2-GTC"], 2.0)
            )
            - g.cm_linfor[g.ll, "CO2-GTC", "N"]
            * (g.my_array[g.ll] + g.cm_linfor[g.ll, "CO2-GTC", "LO"])
        ) / 2.0
    # *-----------------------------------------------------------------------------
    # * If EXOFORCING is not provided by the user, use default values
    if (Sum(g.t, g.cm_exoforc[g.t])).toValue() == 0:
        g.cm_exoforc[g.MyFil[g.ll]] = Min(
            1.15, -0.1965 + 0.013465 * (g.yearval[g.ll] - 1995.0)
        )
