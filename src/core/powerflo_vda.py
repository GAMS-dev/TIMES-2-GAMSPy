# powerflo_vda.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * Powerflo - define powerflow equations and nodal balance costs
# *=============================================================================*

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from gamspy import (
    Card,
    Domain,
    ElseIf,
    Equation,
    If,
    Loop,
    Number,
    Ord,
    Parameter,
    Product,
    Set,
    Smax,
    SpecialValues,
    Sum,
    Variable,
    sparse,
)
from gamspy.math import Max, Min, Round, abs, aggregate, power, project, same_as, sign

from core.base_class import GamsClass
from core.cal_red_red import CalRedRedConfig
from core.fillparm_gms import FillparmGms, FillparmGmsConfig
from core.filparam_gms import FilparamGms, FilparamGmsConfig
from core.gasgrids_vda import GasgridsVda
from core.pp_lvlfc_mod import PpLvlfcMod, PpLvlfcModConfig
from core.utils import SowGPType, expand_set, extract_var_domain, wrap_in_sum
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


@dataclass
class PowerfloVdaConfig:
    """Strongly typed data contract for powerflo.vda."""

    # %1 - GOTO label selecting which section of powerflo.vda to emit;
    #      "" runs the top-level declarations + init flow
    arg1: Literal[
        "",
        "PREP",
        "DECL",
        "POWFLO",
        "OBJBAL",
        "RPTB",
        "CSTBAL",
        "IREAUXIN-",
        "IREAUXOUT",
    ] = ""
    # %2 - second token of the GOTO label (always blank at every call site)
    arg2: str = ""
    # %3 - third token of the GOTO label; also becomes MX when %1 is blank
    arg3: str = ""
    # %4 - RPTB only: prefix for REG_WOBJ/CST_COMC parameter names
    arg4: str = ""
    # %5 - RPTB only: index prefix ahead of R/RTC, e.g. cost_ann.rpt's cc.arg2
    arg5: tuple[Set | Alias | str, ...] | tuple[()] = ()
    # %6 - RPTB only: SOW suffix
    arg6: SowGPType = ()


class PowerfloVda(GamsClass):
    """Translation unit for powerflo.vda."""

    # Instance attributes
    module_name: str = "powerflo_vda"
    gams_source: str = "powerflo.vda"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: PowerfloVdaConfig,
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        g = self.tc

        self.env.set_scoped("mx", f"{self.config.arg3}")
        if self.config.arg3 == "":
            self.env.set_scoped("mx_GP", ())
        else:
            raise ValueError("Double check MX variable. Not implemented")
        pdtol = 1e-5
        bigm = 10

        if self.config.arg1 == "":
            # this ends with a $EXIT so we flip the if to keep the layout
            self.declaration1()
            self.tc.enqueue(self.exec1)
            # RC_GRID is only assigned inside exec1; GAMS' $IF NOT DEFINED RC_GRID
            # (CSTBAL) sees the assignment at parse time
            self.tc.register_assignment(g.RcGrid)
            # * levelization
            self.include(
                PpLvlfcMod(
                    self.tc,
                    self.env,
                    config=PpLvlfcModConfig(
                        arg1=g.gr_demfr,
                        arg2=(g.c,),
                        arg3=g.ComTs,
                        arg4=(),
                        arg5=("0", "0", "0", "0"),
                        arg6=g.allts,
                        arg7=(g.t,),
                        arg8=g.Rtc[g.r, g.t, g.c],
                    ),
                )
            )
            self.tc.enqueue(self.exec2)
            tmp: (
                Number
                | ImplicitParameter
                | ImplicitSet
                | tuple[Number, Callable[[], None]]
            ) = Number(0)
            if f"{self.env.dsc}{self.env.solmip}".upper() == "YESYES":
                tmp = g.ncap_disc[g.r, g.v, g.p, g.u]
            macro.gr_dunit_active = True
            if not (isinstance(tmp, Number) and tmp._value == 0):
                tmp = g.PrcDscncap[g.r, g.p]
            macro.gr_dncap_active = True
            if not (isinstance(tmp, Number) and tmp._value == 0):
                # $SET TMP 1;%TMP%$PRC_YMAX(R,P) = NO;
                def clear_prc_dscncap() -> None:
                    g.PrcDscncap[g.r, g.p].where[g.prc_ymax[g.r, g.p]] = False

                tmp = (Number(1), clear_prc_dscncap)

            self.tc.enqueue(
                self.complete_ptfd_processing,
                pdtol=pdtol,
                tmp=tmp,
            )

            self.include(GasgridsVda(self.tc, self.env))

        else:  # $GOTO %1%2%3
            label = f"{self.config.arg1}{self.config.arg2}{self.config.arg3}"
            if label == "PREP":
                # ends with $EXIT
                if not self.tc.defined("PRC_REACT"):
                    g.prc_react.setRecords(None)
                # fmt: off
                batincludes: list[FillparmGmsConfig] = [
                    FillparmGmsConfig(g.prc_react, (g.r, ), (g.p,),                   ("0",) * 5, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_ptdf,   (g.r, ), (g.p, g.c, g.Reg, g.Com), ("0",) * 2, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_demfr,  (g.r, ), (g.c, g.s),               ("0",) * 4, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_endfr,  (g.r, ), (g.c, g.Com),             ("0",) * 4, g.t, Number(1), Number(0)),
                    FillparmGmsConfig(g.gr_genfr,  (g.r, ), (g.c, g.item),            ("0",) * 4, g.t, Number(1), Number(0)),
                ]
                # fmt: on
                for config in batincludes:
                    self.include(FillparmGms(self.tc, self.env, config))

                self.include(
                    FilparamGms(
                        self.tc,
                        self.env,
                        FilparamGmsConfig(
                            src=g.gr_xbnd,
                            arg2=(g.r,),
                            tail1=(),
                            arg4=("0", "0", "0", "0", "0"),
                            arg5=g.Datayear,
                            arg6=g.t,
                        ),
                    )
                )

                if self.tc.gg_kgf.number_records == 0:
                    return

                # fmt: off
                fillparam_batincludes: list[FillparmGmsConfig] = [
                    FillparmGmsConfig(g.gg_gamma,  (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_kgf,    (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_klp,    (g.r,), (g.p, g.c),            ("0",) * 4, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_pp,     (g.r,), (g.p, g.c, g.bd, g.j), ("0",) * 2, g.t, g.Rtp[g.r, g.t, g.p], Number(0)),
                    FillparmGmsConfig(g.gg_prbd,   (g.r,), (g.c, g.lA),           ("0",) * 4, g.t, Number(1),            Number(0)),
                ]
                # fmt: on
                for config in fillparam_batincludes:
                    self.include(FillparmGms(self.tc, self.env, config))

            elif label == "DECL":
                # ends with $EXIT
                self.declaration2(
                    var=self.env.var,
                    swd=self.env.swd_GP,
                    eq=self.env.eq,
                    swtd=self.env.swtd_GP,
                )
                self.env.set_global("ireauxbal", "$BATINCLUDE powerflo.vda IREAUX")
                self.tc.enqueue(
                    self.exec4,
                    var=self.env.var,
                    sow_GP=self.env.sow_GP,
                )
                if self.tc.defined("VAR_GRVIRT"):
                    # TODO: Technically, VAR_GRVIRT can never be in the container. This is a redundant check
                    return

                macro.var_ptdncap.activate(
                    dsc_mip=f"{self.env.dsc}{self.env.solmip}".upper() == "YESYES",
                    varv_GP=self.env.varv_GP,
                    sws_GP=self.env.sws_GP,
                    bigm=bigm,
                )
                macro.var_grvirt_active = True

                self.tc.enqueue(
                    self.exec5,
                    var=self.env.var,
                    sow_GP=self.env.sow_GP,
                )

                self.include(GasgridsVda(self.tc, self.env, "DECL"))

            elif label == "POWFLO":
                # ends with $EXIT
                self.dc_power_flow_eqs(
                    eq=self.env.eq,
                    r_t=self.env.r_t_GP,
                    swt=self.env.swt_GP,
                    var=self.env.var,
                    sow=self.env.sow_GP,
                    bigm=bigm,
                    varv=self.env.varv_GP,
                    sws=self.env.sws_GP,
                    pgprim=self.env.pgprim,
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                    cal_red=self.env.cal_red,
                )
                self.include(GasgridsVda(self.tc, self.env, arg1="MODEL"))

            elif label == "IREAUXOUT":
                pass  # end of file

            elif label == "CSTBAL":
                # ends with $EXIT
                self.comp2()
                if not self.tc.defined("RC_GRID"):
                    self.tc.enqueue(self.exec6)
                # * levelization
                self.include(
                    PpLvlfcMod(
                        self.tc,
                        self.env,
                        config=PpLvlfcModConfig(
                            arg1=g.com_cstbal,
                            arg2=(g.c,),
                            arg3=g.ComTs,
                            arg4=(g.item, g.cur),
                            arg5=("0", "0"),
                            arg6=g.allts,
                            arg7=(g.t,),
                            arg8=g.Rtc[g.r, g.t, g.c],
                            arg11="N",
                        ),
                    )
                )

                # OBJ_COMBAL is only assigned inside exec7; GAMS' $IF DEFINED OBJ_COMBAL
                # (cost_ann.rpt RPTB) sees the assignment at parse time
                self.tc.register_assignment(g.obj_combal)
                self.tc.enqueue(self.exec7)

            elif label == "OBJBAL":
                # ends with $EXIT
                self.env.set_scoped(
                    "tpulse_GP",
                    (
                        g.tt.where[g.obj_lint[g.r, g.t, g.tt, g.cur]],
                        g.obj_lint[g.r, g.t, g.tt, g.cur],
                    ),
                )
                # $set SOWPRE %SOW%: needed because SOW is reset before the equation definition
                sowpre = self.env.sow_GP
                if self.env.stages == "YES":
                    self.env.set_scoped("sow_GP", (g.ww,))
                self.eq_objbal(
                    sowpre=sowpre,
                    var=self.env.var,
                    swd=self.env.swd_GP,
                    swx=self.env.swx_GP,
                    swsw=self.env.swsw_GP,
                    sow=self.env.sow_GP,
                    tpulse=self.env.tpulse_GP,
                    condition=self.env.stages == "YES",
                    cal_red=self.env.cal_red,
                    pgprim=self.env.pgprim,
                    def_rtp_ffcs=self.tc.defined("RTP_FFCS"),
                )

            elif label == "RPTB":
                # ends with $EXIT
                self.tc.enqueue(
                    self.exec_powerflo_vda_rptb,
                    arg4=self.config.arg4,
                    arg5=self.config.arg5,
                    arg6=self.config.arg6,
                    var=self.env.var,
                    vart=self.env.vart_GP,
                    sws=self.env.sws_GP,
                )

    def declaration1(self: PowerfloVda) -> None:
        g = self.tc
        m = g.container
        # * Declarations
        g.RpGrid = Set(m, name="RP_GRID", domain=[g.r, g.p])
        g.RcGrid = Set(m, name="RC_GRID", domain=[g.r, g.t, g.c])
        g.GrTop = Set(m, name="GR_TOP", domain=[g.allreg, g.c, g.allreg, g.c, g.p])
        g.GrArc = Set(m, name="GR_ARC", domain=[g.allreg, g.c, g.allreg, g.c])
        g.GrGrid = Set(m, name="GR_GRID", domain=[g.j, g.r, g.Com])
        g.GrAllmap = Set(m, name="GR_ALLMAP", domain=[g.r, g.cg, g.Com])
        g.GrPrcmap = Set(m, name="GR_PRCMAP", domain=[g.r, g.p, g.c, g.item])
        g.GrDemmap = Set(m, name="GR_DEMMAP", domain=[g.r, g.c, g.Com])
        g.GrAlgmap = Set(m, name="GR_ALGMAP", domain=[g.r, g.cg, g.cg])
        g.GrEndc = Set(m, name="GR_ENDC", domain=[g.r, g.cg])
        g.GrGenp = Set(m, name="GR_GENP", domain=[g.r, g.p])
        g.GrCandid = Set(m, name="GR_CANDID", domain=[g.r, g.year, g.p])
        g.GrGnall = Set(m, name="GR_GNALL", domain=[g.r, g.t, g.c])
        g.gr_sus = Parameter(
            m, name="GR_SUS", domain=[g.allreg, g.t, g.c, g.allreg, g.c]
        )
        g.gr_flow = Parameter(m, name="GR_FLOW", domain=[g.r, g.p, g.c])
        g.gr_gid = Parameter(m, name="GR_GID", domain=[g.r, g.c])
        g.gr_admit = Parameter(
            m, name="GR_ADMIT", domain=[g.allreg, g.t, g.c, g.allreg, g.c]
        )
        g.gr_units = Parameter(m, name="GR_UNITS", domain=[g.r, g.t, g.item])
        g.gr_capup = Parameter(m, name="GR_CAPUP", domain=[g.r, g.year, g.p])

    def exec1(self: PowerfloVda) -> None:
        g = self.tc

        # * Define grid and default line directions
        g.Nrgelc[g.Rc[g.r, g.c]].where[g.ComTmap[g.r, "NRG", g.c]] = sparse(
            g.NrgTmap[g.r, "ELC", g.c]
        )
        g.Trackp[g.r, g.p] = sparse(
            Sum(g.RpcIre[g.r, g.p, g.c, g.ie].where[g.Nrgelc[g.r, g.c]], 1.0)
        )
        g.prc_react[g.r, g.ll, g.p].where[(~(g.Trackp[g.r, g.p]))] = 0.0
        project(source=g.gr_demfr, target=g.Trackc, direction="left")
        aggregate(source=g.gr_endfr, target=g.gr_gid, direction="left")
        g.gr_gid[g.Trackc] = 1.0
        project(source=g.gg_prbd, target=g.Trackc)
        g.gr_gid[g.Trackc] = 1.0
        with Loop(
            Domain(g.r, g.ll, g.c, g.item).where[g.gr_genfr[g.r, g.ll, g.c, g.item]]
        ):
            g.gr_gid[g.r, g.c] = 1.0
        g.Trackc.setRecords(None)
        project(source=g.prc_react, target=g.Trackp)
        project(source=g.gr_ptdf, target=g.RpPrc)
        g.dfunc[...] = Card(g.RpPrc)
        g.Trackp[g.RpPrc] = True
        g.Trackc[g.r, g.c] = sparse(Sum(g.NrgGmap[g.r, g.nrggrid, g.c], 1.0))
        # * Add any IRE between add-on nodes
        with Loop(g.RpcIre[g.r, g.p, g.c, g.ie].where[g.gr_gid[g.r, g.c]]):
            g.Trackp[g.r, g.p] = True
        g.GrTop[g.TopIre[g.r, g.c, g.Trackc[g.Reg, g.Com], g.p]].where[
            (g.Trackc[g.r, g.c].where[g.Trackp[g.r, g.p]])
        ] = True
        g.GrTop[g.TopIre[g.Trackc[g.Reg, g.Com], g.r, g.c, g.p]].where[
            (g.Trackc[g.r, g.c].where[g.Trackp[g.r, g.p]])
        ] = True
        with Loop(g.GrTop[g.r, g.c, g.Reg, g.Com, g.p]):
            g.gr_flow[g.r, g.p, g.c] = g.gr_flow[g.r, g.p, g.c] * 2.0 + 1.0
            g.gr_flow[g.Reg, g.p, g.Com] = g.gr_flow[g.Reg, g.p, g.Com] * 2.0 - 1.0
        g.Trackp.setRecords(None)
        g.RpPrc.setRecords(None)
        project(source=g.gr_flow, target=g.RpGrid)
        g.GrTop[g.r, g.c, g.Reg, g.Com, g.p].where[(g.gr_flow[g.r, g.p, g.c] < 0.0)] = (
            False
        )
        g.GrTop[g.r, g.c, g.r, g.c, g.p] = False
        with Loop(
            g.GrTop[g.r, g.c, g.r, g.Com, g.p].where[
                Sum(g.RpcIre[g.RpcPg[g.r, g.p, g.c], g.ie], g.RpcPg[g.r, g.p, g.Com])
            ]
        ):
            g.PrcMap[g.r, "DISTR", g.p] = True
        # * Synchronize and check for zero line reactances
        with Loop(g.GrTop[g.r, g.c, g.Reg, g.Com, g.p]):
            g.f[...] = 1.0
            with If(~(same_as(g.r, g.Reg))):
                g.RpPrc[g.Reg, g.p] = True
                g.f[...] = 0.0
                g.RtpVara[g.Rtp[g.r, g.t, g.p]].where[
                    (~(g.RtpVara[g.Reg, g.t, g.p]))
                ] = False
                g.prc_react[g.r, g.t, g.p] = Max(
                    g.prc_react[g.r, g.t, g.p], g.prc_react[g.Reg, g.t, g.p]
                )
            with If(~(same_as(g.c, g.Com).where[g.f])):
                g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.com2].where[
                    g.gr_ptdf[g.Reg, g.t, g.p, g.Com, g.allr, g.com2]
                ] = Max(
                    abs(g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.com2]),
                    abs(g.gr_ptdf[g.Reg, g.t, g.p, g.Com, g.allr, g.com2]),
                ) * sign(
                    2.0
                    * sign(
                        g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.com2]
                        - sign(g.gr_ptdf[g.Reg, g.t, g.p, g.Com, g.allr, g.com2])
                    )
                )
                g.gr_ptdf[g.Reg, g.t, g.p, g.Com, g.allr, g.com2] = -g.gr_ptdf[
                    g.r, g.t, g.p, g.c, g.allr, g.com2
                ]
        g.prc_react[g.r, g.t, g.p].where[
            ((g.prc_react[g.r, g.t, g.p] <= 0.0).where[g.prc_react[g.r, g.t, g.p]])
        ] = 0.0
        with Loop(g.GrTop[g.r, g.c, g.Reg, g.Com, g.p]):
            g.GrArc[g.r, g.c, g.Reg, g.Com] = True
        project(source=g.gr_flow, target=g.Trackc)
        # * Internodal admittance
        aggregate(source=g.gr_ptdf, target=g.gr_gid, direction="left")
        with Loop(g.RpcIre[g.r, g.p, g.c, g.ie].where[g.gr_gid[g.r, g.c]]):
            g.prc_react[g.r, g.t, g.p] = 0.0
        g.gr_admit[g.r, g.t, g.c, g.Reg, g.Com].where[
            g.GrArc[g.r, g.c, g.Reg, g.Com]
        ] = Sum(
            g.GrTop[g.r, g.c, g.Reg, g.Com, g.p].where[
                (g.prc_react[g.r, g.t, g.p].where[g.RtpVara[g.r, g.t, g.p]])
            ],
            1.0 / g.prc_react[g.r, g.t, g.p],
        )
        project(source=g.GrArc, target=g.Rreg, direction="left")
        # * Construct all disjoint grids
        g.cnt[...] = SpecialValues.EPS
        g.gr_gid.setRecords(None)
        with Loop(g.GrArc[g.r, g.c, g.Reg, g.Com]):
            g.f[...] = g.gr_gid[g.r, g.c]
            g.z[...] = g.gr_gid[g.Reg, g.Com]
            with If(~(g.f + g.z)):
                g.gr_gid[g.r, g.c] = g.cnt
                g.gr_gid[g.Reg, g.Com] = g.cnt
                g.cnt[...] = g.cnt + 1.0
            with ElseIf(~(g.f)):
                g.gr_gid[g.r, g.c] = g.z
            with ElseIf(~(g.z)):
                g.gr_gid[g.Reg, g.Com] = g.f
            with ElseIf(g.f != g.z):
                g.my_f[...] = Min(g.f, g.z)
                g.done[...] = Max(g.f, g.z)
                with If(g.cnt == g.done + 1.0):
                    g.cnt[...] = g.done
                g.gr_gid[g.Trackc].where[(g.gr_gid[g.Trackc] == g.done)] = g.my_f
        # * Assign each node with unique grid ID
        with Loop(g.j.where[same_as("1", g.j)]):
            g.GrGrid[g.j + g.gr_gid[g.r, g.c], g.Trackc[g.r, g.c]] = True
        # * GR_GID holds the reactance grid nodes only
        aggregate(source=g.gr_ptdf, target=g.gr_gid, direction="left")
        g.gr_gid[g.Trackc] = ~(g.gr_gid[g.Trackc])
        # * QA checks - for reactance nodes only
        g.Trackpc[g.RpGrid[g.r, g.p], g.c].where[g.gr_flow[g.r, g.p, g.c]] = sparse(
            g.gr_gid[g.r, g.c]
        )
        with Loop(Domain(g.r, g.tsl["DAYNITE"])):
            g.z[...] = 0.0
            with If(
                Sum(
                    g.Trackpc[g.r, g.p, g.c].where[
                        (~(g.PrcTsl[g.r, g.p, g.tsl].where[g.ComTsl[g.r, g.c, g.tsl]]))
                    ],
                    1.0,
                )
            ):
                g.z[...] = 1.0
            with Loop(g.Rreg[g.r, g.Reg]):  # noqa: SIM117
                with If(
                    Sum(
                        g.s.where[
                            (
                                (g.TsGroup[g.r, g.tsl, g.s])
                                ^ (g.TsGroup[g.Reg, g.tsl, g.s])
                            )
                        ],
                        1.0,
                    )
                ):
                    g.Trackc[g.Nrgelc[g.Reg, g.c]].where[g.gr_gid[g.Reg, g.c]] = False
                    g.z[...] = 1.0
            with If(g.z):
                g.Trackc[g.Nrgelc[g.r, g.c]].where[g.gr_gid[g.r, g.c]] = False
        g.RcGrid[g.Rtc[g.r, g.t, g.c]].where[g.Trackc[g.r, g.c]] = True
        # * Collect RP_GRID for PTDF grids
        project(source=g.gr_ptdf, target=g.Trackpc, direction="left")
        g.Trackpc[g.r, g.p, g.c].where[g.gr_gid[g.r, g.c]] = False
        project(source=g.Trackpc, target=g.RpGrid)
        g.Trackpc.setRecords(None)
        g.Trackp.setRecords(None)
        # * Admittance / susceptance matrix
        aggregate(source=g.gr_admit, target=g.gr_sus)
        g.gr_sus[g.RcGrid, g.Rc] = sparse(g.gr_admit[g.RcGrid, g.Rc] * (-1.0))
        g.gr_sus[g.RcGrid[g.r, g.t, g.c], g.r, g.c] = -Sum(
            g.Trackc[g.Rc], g.gr_sus[g.RcGrid, g.Rc]
        )

    def exec2(self: PowerfloVda) -> None:
        g = self.tc

        # * Preliminaries
        g.gr_endfr[g.r, g.t, g.Com, g.c].where[g.Trackc[g.r, g.c]] = 0.0
        g.Rxx.setRecords(None)
        project(source=g.gr_genmap, target=g.GrGenp)
        project(source=g.gr_endfr, target=g.GrEndc)
        g.gr_genlev[g.Trackc] = 0.0
        g.gr_genlev[g.r, g.c].where[g.gr_genlev[g.r, g.c]] = Round(
            g.gr_genlev[g.r, g.c]
        )
        g.Trackpc[g.Rpc[g.GrGenp[g.r, g.p], g.c]].where[g.gr_genlev[g.r, g.c]] = True
        g.GrPrcmap[g.Trackpc[g.r, g.p, g.c], g.item].where[
            (g.Top[g.r, g.p, g.c, "OUT"].where[g.gr_genmap[g.r, g.p, g.item]])
        ] = True
        g.GrPrcmap[g.Trackpc[g.RpIre[g.r, g.p], g.c], g.item].where[
            g.gr_genmap[g.r, g.p, g.item]
        ] = True
        g.gr_genfr[g.r, g.ll.lag(Ord(g.ll), "circular"), g.c, g.item].where[
            g.gr_genfr[g.r, g.ll, g.c, g.item]
        ] = 1.0
        with Loop(  # noqa: SIM117
            Domain(g.GrGrid[g.j, g.r, g.c], g.item).where[
                g.gr_genfr[g.r, "0", g.c, g.item]
            ]
        ):
            with Loop(g.GrPrcmap[g.r, g.p, g.Com, g.item]):
                g.Rxx[g.r, g.j, g.Com] = True
        with Loop(g.Rxx[g.r, g.j, g.Com]):
            g.GrAllmap[g.Trackc[g.r, g.c], g.Com].where[g.GrGrid[g.j, g.r, g.c]] = True
        with Loop(g.nrggrid):
            g.GrAllmap[g.r, g.c, g.Com].where[
                (
                    (~(g.NrgGmap[g.r, g.nrggrid, g.c])).where[
                        g.NrgGmap[g.r, g.nrggrid, g.Com]
                    ]
                )
            ] = False
        # * Grid allocations
        g.GrAlgmap[g.r, "NRG", g.c].where[
            ((g.gr_genlev[g.r, g.c] == 1.0).where[g.gr_genlev[g.r, g.c]])
        ] = True
        g.GrAlgmap[g.r, g.c, g.c].where[
            ((g.gr_genlev[g.r, g.c] == 2.0).where[g.gr_genlev[g.r, g.c]])
        ] = True
        g.GrAlgmap[g.r, g.ComType[g.cg], g.cg].where[
            (Sum(g.Trackc[g.r, g.c], 1.0) > 1.0)
        ] = sparse(Sum(g.GrAlgmap[g.r, g.cg, g.c], 1.0))
        g.GrDemmap[g.GrAllmap[g.r, g.c, g.Com]].where[
            (g.gr_genlev[g.r, g.Com] < 3.0)
        ] = True
        if ((Card(g.gr_demfr)) * 1).toValue():
            g.gr_demfr[g.RtcsVarc[g.RcGrid[g.r, g.t, g.c], g.s]] = (
                g.gr_demfr[g.r, g.t, g.c, g.s] + SpecialValues.EPS
            )
        g.GrEndc[g.r, "DEM"].where[Sum(g.GrEndc[g.r, g.c], 1.0)] = True
        # * Process regions with sectoral demand fractions
        with Loop(g.r.where[g.GrEndc[g.r, "DEM"]]):
            g.gr_demfr[g.RtcsVarc[g.RcGrid[g.r, g.t, g.c], g.s]] = Sum(
                g.GrEndc[g.r, g.Com], Min(0.33, g.gr_endfr[g.r, g.t, g.c, g.Com])
            )
            g.gr_units[g.Rtc[g.r, g.t, g.Com]].where[g.GrEndc[g.r, g.Com]] = (
                Sum(g.RcGrid[g.r, g.t, g.c], g.gr_endfr[g.r, g.t, g.c, g.Com])
                + 1.0
                - 1.0
            )
            g.gr_endfr[g.RcGrid[g.r, g.t, g.c], g.Com].where[
                g.gr_units[g.r, g.t, g.Com]
            ] = g.gr_endfr[g.r, g.t, g.c, g.Com] / g.gr_units[g.r, g.t, g.Com]
            g.gr_units.setRecords(None)
        g.GrEndc[g.r, g.c].where[
            ((g.gr_genlev[g.r, g.c] > 2.0).where[g.gr_genlev[g.r, g.c]])
        ] = True
        g.GrEndc[g.r, "NRG"].where[(~(g.GrEndc[g.r, "DEM"]))] = True
        # * Genmap normalization
        g.prc_ymax[g.GrGenp[g.r, g.p]] = (
            Sum(
                Domain(g.item).where[g.gr_genmap[g.r, g.p, g.item]],
                g.gr_genmap[g.r, g.p, g.item],
            )
            + 1.0
            - 1.0
        )
        g.gr_genmap[g.GrGenp[g.r, g.p], g.item].where[
            (g.prc_ymax[g.r, g.p].where[g.gr_genmap[g.r, g.p, g.item]])
        ] = g.gr_genmap[g.r, g.p, g.item] / g.prc_ymax[g.r, g.p]
        # * GENFR normalization
        with Loop(g.RcGrid[g.r, g.t, g.c]):
            g.gr_units[g.r, g.t, g.item].where[g.gr_genfr[g.r, g.t, g.c, g.item]] = 1.0
        g.gr_units[g.r, g.t, g.item].where[g.gr_units[g.r, g.t, g.item]] = (
            Sum(g.Trackc[g.r, g.c], g.gr_genfr[g.r, g.t, g.c, g.item]) + 1.0 - 1.0
        )
        g.gr_genfr[g.RcGrid[g.r, g.t, g.c], g.item].where[
            g.gr_units[g.r, g.t, g.item]
        ] = g.gr_genfr[g.r, g.t, g.c, g.item] / g.gr_units[g.r, g.t, g.item]
        g.prc_ymax.setRecords(None)
        g.gr_units.setRecords(None)
        # * DEMFR normalization
        with Loop(g.RcGrid[g.r, g.t, g.c]):
            g.gr_units[g.r, g.t, g.s].where[g.gr_demfr[g.r, g.t, g.c, g.s]] = 1.0
        g.gr_units[g.r, g.t, g.s].where[g.gr_units[g.r, g.t, g.s]] = (
            Sum(g.Trackc[g.r, g.c], g.gr_demfr[g.r, g.t, g.c, g.s]) + 1.0 - 1.0
        )
        g.gr_demfr[g.RcGrid[g.r, g.t, g.c], g.s].where[g.gr_units[g.r, g.t, g.s]] = (
            g.gr_demfr[g.r, g.t, g.c, g.s] / g.gr_units[g.r, g.t, g.s]
            + SpecialValues.EPS
        )
        g.gr_units.setRecords(None)
        g.Rxx.setRecords(None)
        # * Find and remove node with max demand fraction from GR_DEMFR
        with Loop(g.j.where[Sum(g.GrGrid[g.j, g.r, g.c], 1.0)]):
            g.gr_units[g.RcGrid[g.r, g.t, g.c]].where[g.GrGrid[g.j, g.r, g.c]] = Sum(
                g.ComTs[g.r, g.c, g.s], g.gr_demfr[g.r, g.t, g.c, g.s]
            )
            with Loop(Domain(g.r, g.t)):
                g.z[...] = Max(
                    SpecialValues.EPS,
                    Smax(g.GrGrid[g.j, g.r, g.c], g.gr_units[g.r, g.t, g.c]),
                )
                with Loop(g.GrGrid[g.j, g.r, g.c].where[g.z]):  # noqa: SIM117
                    with If(g.gr_units[g.r, g.t, g.c] == g.z):
                        g.Rxx[g.r, g.t, g.c] = True
                        g.z[...] = 0.0
            g.gr_demfr[g.Rxx[g.r, g.t, g.c], g.s] = 0.0
            with If(
                Sum(g.GrAllmap[g.r, g.c, g.Com].where[g.GrGrid[g.j, g.r, g.c]], 1.0)
            ):
                g.GrGnall[g.RcGrid[g.r, g.t, g.c]].where[g.GrGrid[g.j, g.r, g.c]] = True

    def complete_ptfd_processing(
        self: PowerfloVda,
        pdtol: float,
        tmp: Number
        | ImplicitParameter
        | ImplicitSet
        | tuple[Number, Callable[[], None]],
    ) -> None:
        g = self.tc
        # * Complete PTDF processing
        if ((g.dfunc) * 1).toValue():
            project(source=g.GrTop, target=g.GrArc, direction="left")
            g.GrCandid.setRecords(None)
            g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com].where[g.RpPrc[g.r, g.p]] = 0.0
            g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com].where[
                (
                    (abs(g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com]) < pdtol).where[
                        g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com]
                    ]
                )
            ] = 0.0
            g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com].where[
                (
                    (~(g.GrAlgmap[g.r, "NRG", "NRG"])).where[
                        g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com]
                    ]
                )
            ] = Round(
                g.gr_ptdf[g.r, g.t, g.p, g.c, g.allr, g.Com] / power(2.0, -32.0)
            ) * power(2.0, -32.0)
            project(source=g.gr_ptdf, target=g.Trackp)
            aggregate(source=g.ncap_pasti, target=g.prc_ymax)
            project(source=g.gr_ptdf, target=g.Trackc)
            # *...First set all lines with non-zero PTDF as candidates
            g.GrCandid[g.r, g.t, g.p].where[
                (g.RpGrid[g.r, g.p].where[g.Trackp[g.r, g.p]])
            ] = True
            # *...No new capacity allowed for existing lines
            g.ncap_bnd[g.GrCandid[g.r, g.t, g.p], "UP"].where[g.prc_ymax[g.r, g.p]] = (
                Max(SpecialValues.EPS, g.ncap_bnd[g.r, g.t, g.p, "UP"])
            )
            if isinstance(tmp, tuple):
                value, clear_prc_dscncap = tmp
                g.dfunc[...] = value
                clear_prc_dscncap()
            else:
                g.dfunc[...] = tmp
            g.prc_ymax.setRecords(None)
            g.Trackp.setRecords(None)
        else:
            g.RpGrid.setRecords(None)
        # * Check nodal commodity balances
        # *  COM_BNDNET(RTCS_VARC(RC_GRID,S),'LO') = EPS;
        g.ComLim[g.Trackc[g.Rc], "FX"].where[
            ((~(Sum(g.ComLim[g.Rc, g.lA], 1.0))).where[g.gr_gid[g.Rc]])
        ] = True
        g.Trackc.setRecords(None)
        g.RpPrc.setRecords(None)
        g.Trackpc.setRecords(None)

    def declaration2(
        self: PowerfloVda,
        var: str,
        swd: tuple[Set | Alias] | tuple[()],
        eq: str,
        swtd: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    ) -> None:
        g = self.tc
        m = g.container
        r, c, t, p, j, io, cg, ie, bd, s, year, item = (
            g.r,
            g.c,
            g.t,
            g.p,
            g.j,
            g.io,
            g.cg,
            g.ie,
            g.bd,
            g.s,
            g.year,
            g.item,
        )
        # * Declare variables and equations
        g.set_variable(
            f"{var}_GRIDIO",
            Variable(
                m,
                name=f"{var}_GRIDIO",
                domain=[r, year, c, c, s, io, *swd],
                type="POSITIVE",
            ),
        )
        g.set_variable(
            f"{var}_XCAP",
            Variable(
                m, name=f"{var}_XCAP", domain=[r, year, item, *swd], type="POSITIVE"
            ),
        )
        g.set_variable(
            f"{var}_COMAUX",
            Variable(m, name=f"{var}_COMAUX", domain=[r, t, c, s, *swd]),
        )
        g.set_equation(
            f"{eq}_GR_POWFLO",
            Equation(
                m,
                name=f"{eq}_GR_POWFLO",
                domain=[r, t, c, s, r, c, *swtd],
                description="Phase-angle formulation",
            ),
        )
        g.set_equation(
            f"{eq}_GR_PTDFLO",
            Equation(
                m,
                name=f"{eq}_GR_PTDFLO",
                domain=[r, t, p, c, s, *swtd],
                description="Generalized PTDF formulation",
            ),
        )
        g.set_equation(
            f"{eq}_GR_GENALL",
            Equation(
                m,
                name=f"{eq}_GR_GENALL",
                domain=[r, t, c, s, cg, *swtd],
                description="Allocation of supply to Add-on nodes",
            ),
        )
        g.set_equation(
            f"{eq}_GR_DEMALL",
            Equation(
                m,
                name=f"{eq}_GR_DEMALL",
                domain=[r, t, c, s, *swtd],
                description="Allocation of demand to Add-on nodes",
            ),
        )
        g.set_equation(
            f"{eq}_GR_XBND",
            Equation(
                m,
                name=f"{eq}_GR_XBND",
                domain=[r, t, j, ie, s, *swtd],
                description="Simplified N-1 security constraint",
            ),
        )
        g.set_equation(
            f"{eq}_GR_VIRTCAP",
            Equation(
                m,
                name=f"{eq}_GR_VIRTCAP",
                domain=[r, t, p, c, s, bd, *swtd],
                description="Candidate line virtual capacity",
            ),
        )
        g.set_equation(
            f"{eq}_GR_VIRTBND",
            Equation(
                m,
                name=f"{eq}_GR_VIRTBND",
                domain=[r, t, p, *swtd],
                description="Bound on virtual capacity",
            ),
        )

    def exec4(self: PowerfloVda, var: str, sow_GP: SowGPType) -> None:
        g = self.tc
        VAR_COMAUX = g.get_variable(f"{var}_COMAUX")
        # * For each disjoint grid, set phase angle to zero for the node with most connected lines
        with Loop(
            g.j.where[Sum(g.GrGrid[g.j, g.r, g.c].where[g.gr_gid[g.r, g.c]], 1.0)]
        ):
            g.z[...] = Smax(
                g.GrGrid[g.j, g.r, g.c], Sum(g.p.where[g.gr_flow[g.r, g.p, g.c]], 1.0)
            )
            with Loop(g.GrGrid[g.j, g.r, g.c].where[g.z]):  # noqa: SIM117
                with If(Sum(g.p.where[g.gr_flow[g.r, g.p, g.c]], 1.0) == g.z):
                    g.z[...] = 0.0
                    VAR_COMAUX.fx[g.r, g.t, g.c, g.s, *sow_GP] = SpecialValues.EPS
        g.GrGrid[g.j, g.r, "ACT"] = sparse(Sum(g.GrGrid[g.j, g.Nrgelc[g.r, g.c]], 1.0))

    def exec5(self: PowerfloVda, var: str, sow_GP: SowGPType) -> None:
        g = self.tc
        VAR_IRE = g.get_variable(f"{var}_IRE")
        if ((Card(g.GrCandid)) * 1).toValue():
            # *...Remove existing lines from candidate lines for their full lifespan
            g.gr_capup[g.GrCandid[g.r, g.t, g.p]] = Sum(
                g.pyr[g.v].where[g.coef_cpt[g.r, g.v, g.t, g.p]],
                g.ncap_pasti[g.r, g.v, g.p] * Round(g.coef_cpt[g.r, g.v, g.t, g.p]),
            )
            g.GrCandid[g.r, g.t, g.p].where[
                Sum(g.RpGrid[g.Reg, g.p].where[g.gr_capup[g.Reg, g.t, g.p]], 1.0)
            ] = False
            g.Rvp[g.GrCandid] = True
            # *...Complete virtual CAP bounds for candidate/removed lines
            g.gr_capup[g.Rvp[g.r, g.t, g.p]].where[
                macro.gr_dncap_GP(g.r, g.p, self.env)
            ] = Max(
                0.0,
                Smax(
                    Domain(g.Vnt[g.v, g.t], g.unit).where[
                        g.coef_cpt[g.r, g.v, g.t, g.p]
                    ],
                    macro.gr_dunit_GP(g.r, g.v, g.p, g.unit, self.env)
                    * (g.coef_cpt[g.r, g.v, g.t, g.p] > 0.0),
                ),
            )
            with Loop(g.t):
                g.gr_capup[g.Rvp[g.r, g.tt[g.Miyr1], g.p]].where[
                    (~(g.gr_capup[g.Rvp]))
                ] = (
                    Max(g.cap_bnd[g.r, g.t, g.p, "UP"], g.gr_capup[g.r, g.t, g.p])
                    + 1.0
                    - 1.0
                )
            with Loop(g.tt[g.t + 1]):
                g.gr_capup[g.Rvp[g.r, g.tt, g.p]].where[(~(g.gr_capup[g.Rvp]))] = (
                    g.gr_capup[g.r, g.t, g.p]
                    + (g.cap_bnd[g.Rvp, "UP"] - g.gr_capup[g.r, g.t, g.p]).where[
                        (g.cap_bnd[g.Rvp, "UP"] > 0.0)
                    ]
                )
            # *...Copy CAP bounds from import side if needed
            with Loop(g.GrTop[g.r, g.c, g.Reg, g.Com, g.p]):
                g.gr_capup[g.r, g.t, g.p].where[g.gr_capup[g.Reg, g.t, g.p]] = Min(
                    g.gr_capup[g.Reg, g.t, g.p],
                    g.gr_capup[g.r, g.t, g.p]
                    + Number(SpecialValues.POSINF).where[
                        (~(g.gr_capup[g.r, g.t, g.p]))
                    ],
                )
                with If(~(same_as(g.r, g.Reg))):
                    g.gr_capup[g.Reg, g.t, g.p] = 0.0
            g.GrCandid[g.Rvp].where[(~(g.gr_capup[g.Rvp]))] = False
            g.cap_bnd[g.GrCandid[g.r, g.t, g.p], "UP"].where[
                (
                    (~(g.cap_bnd[g.r, g.t, g.p, "UP"])).where[
                        (~(macro.gr_dncap_GP(g.r, g.p, self.env)))
                    ]
                )
            ] = g.gr_capup[g.r, g.t, g.p]
            g.RtpVarp[g.GrCandid[g.r, g.t, g.p]].where[
                (~(macro.gr_dncap_GP(g.r, g.p, self.env)))
            ] = True
            VAR_IRE.lo[g.r, g.t, g.t, g.p, g.c[g.Actcg], g.s, "EXP", *sow_GP].where[
                (g.PrcTs[g.r, g.p, g.s].where[g.Rvp[g.r, g.t, g.p]])
            ] = SpecialValues.NEGINF
            g.Rvp.setRecords(None)

    def dc_power_flow_eqs(
        self: PowerfloVda,
        eq: str,
        r_t: tuple[Set | Alias | ImplicitSet, Set | Alias | ImplicitSet],
        swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        var: str,
        sow: SowGPType,
        bigm: int,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
        pgprim: str,
        def_rtp_ffcs: bool,
        cal_red: str,
    ) -> None:
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        g = self.tc
        include_cal_red = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=g.Com,
                arg2=g.com1,
                arg3=g.ts,
                arg4=g.p,
                arg5=g.t,
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                arg10=Number(1),
            ),
        )
        rts = macro.rts_GP(s=g.s, g=g, env=self.env)

        eq_gr_powflo = g.get_equation(f"{eq}_GR_POWFLO")
        eq_gr_ptdflo = g.get_equation(f"{eq}_GR_PTDFLO")
        eq_gr_virtcap = g.get_equation(f"{eq}_GR_VIRTCAP")
        eq_gr_virtbnd = g.get_equation(f"{eq}_GR_VIRTBND")
        eq_gr_genall = g.get_equation(f"{eq}_GR_GENALL")
        eq_gr_demall = g.get_equation(f"{eq}_GR_DEMALL")
        eq_gr_xbnd = g.get_equation(f"{eq}_GR_XBND")
        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_COMAUX = g.get_variable(f"{var}_COMAUX")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        VAR_GRIDIO = g.get_variable(f"{var}_GRIDIO")
        VAR_SOUT = g.get_variable(f"{var}_SOUT")
        VAR_SIN = g.get_variable(f"{var}_SIN")

        # * Standard DC power flow equations - Omega
        eq_gr_powflo[g.RtcsVarc[g.RcGrid[*r_t, g.c], rts], g.Reg, g.Com, *swt].where[
            g.gr_admit[g.r, g.t, g.c, g.Reg, g.Com]
        ] = (
            Sum(
                Domain(
                    g.GrTop[g.r, g.c, g.Reg, g.Com, g.p],
                    g.RtpVintyr[g.Reg, g.v, g.t, g.p],
                ).where[g.RtpcsVarf[g.Reg, g.t, g.p, g.Com, g.s]],
                Sum(
                    g.RpcIre[g.Reg, g.p, g.Com, g.ie].where[g.prc_react[g.r, g.t, g.p]],
                    VAR_IRE[g.Reg, g.v, g.t, g.p, g.Com, g.s, g.ie, *sow]
                    * (1.0 - 2.0 * g.xpt[g.ie]),
                ),
            )
            == (
                VAR_COMAUX[g.r, g.t, g.c, g.s, *sow]
                - VAR_COMAUX[g.Reg, g.t, g.Com, g.s, *sow]
            )
            * g.gr_admit[g.r, g.t, g.c, g.Reg, g.Com]
        )
        # *------------------------------------------------------------------------

        # * Standard DC power flow equations - PTDF
        eq_gr_ptdflo[*r_t, g.p, g.c, rts, *swt].where[
            (
                g.RpsS1[g.r, g.p, g.s].where[
                    (g.gr_flow[g.r, g.p, g.c] > 0.0) & g.RpGrid[g.r, g.p]
                ]
            )
            # *...Real flow over the line
        ] = Sum(
            Domain(
                g.RtpVintyr[g.r, g.v, g.t, g.p], g.RtpcsVarf[g.r, g.t, g.p, g.c, g.ts]
            ).where[g.rs_fr[g.r, g.s, g.ts]],
            g.rs_fr[g.r, g.s, g.ts]
            # *...Virtual powerflow over the line (if candidate)
            * Sum(
                g.RpcIre[g.r, g.p, g.c, g.ie],
                VAR_IRE[g.r, g.v, g.t, g.p, g.c, g.s, g.ie, *sow]
                * (2.0 * g.xpt[g.ie] - 1.0),
            ),
        ) + Sum(
            g.RcGrid[g.r, g.t, g.c],
            macro.var_grvirt_GP(g.r, g.t, g.p, g.s, var, pgprim, sow),
        ).where[g.GrCandid[g.r, g.t, g.p]] == Sum(
            # *...PTDF for net injections: Normal grid nodes
            g.RcGrid[g.Reg, g.t, g.Com].where[
                (
                    g.ComTs[g.Reg, g.Com, g.s].where[
                        g.gr_ptdf[g.r, g.t, g.p, g.c, g.Reg, g.Com]
                    ]
                )
            ],
            g.gr_ptdf[g.r, g.t, g.p, g.c, g.Reg, g.Com]
            * VAR_COMAUX[g.Reg, g.t, g.Com, g.s, *sow],
        )
        # *...PTDF for virtual injections (redundant in this formulation)
        # *   +SUM(GR_TOP(REG,COM1,RC,PRC)$GR_CANDID(REG,T,PRC),
        # *     (GR_PTDF(R,T,P,C,REG,COM1)-GR_PTDF(R,T,P,C,RC)) * SUM(RPS_S1(REG,PRC,TS)$RS_FR(REG,S,TS),RS_FR(REG,S,TS)*VAR_GRVIRT(REG,T,PRC,COM1,TS)));
        # *------------------------------------------------------------------------
        # * Implied capacity of virtual powerflow
        eq_gr_virtcap[g.GrCandid[*r_t, g.p], g.c, rts, g.Bdneq[g.bd], *swt].where[
            ((g.gr_flow[g.r, g.p, g.c] > 0.0).where[g.RpsS1[g.r, g.p, g.s]])
        ] = (
            Sum(
                g.GrTop[g.r, g.c, g.Rc, g.p],
                macro.var_grvirt_GP(g.r, g.t, g.p, g.s, var, pgprim, sow),
            )
            * g.bdsig[g.bd]
            <= macro.VAR_XCAP_GP(var, g.r, g.t, g.p, sow)
            * g.prc_capact[g.r, g.p]
            * g.g_yrfr[g.r, g.s]
        )
        # *------------------------------------------------------------------------
        # * Bounds on virtual capacity
        eq_gr_virtbnd[g.GrCandid[*r_t, g.p], *swt] = macro.VAR_XCAP_GP(
            var, g.r, g.t, g.p, sow
        ) == bigm * g.gr_capup[
            # *...Upper bound on virtual flow capacity: Zero if line is installed, less than BIGM*F if line not installed
            g.r, g.t, g.p
        ] * (
            1.0
            - (
                macro.var_ptdncap_GP(g.r, g.t, g.p).where[
                    macro.gr_dncap_GP(g.r, g.p, self.env)
                ]
                # *...Virtual capacity indicator
                + (
                    1.0
                    - (
                        1.0
                        - Sum(
                            g.Rtp[g.r, g.t, g.p],
                            macro.VAR_CAP_GP(var, g.r, g.t, g.p, sow),
                        )
                        / g.gr_capup[g.r, g.t, g.p]
                    )
                    / bigm
                ).where[(~(macro.gr_dncap_GP(g.r, g.p, self.env)))]
            )
        )
        # *------------------------------------------------------------------------
        # * Generation fractions for all grid nodes C
        eq_gr_genall[g.RtcsVarc[g.GrGnall[*r_t, g.c], rts], g.cg, *swt].where[
            g.GrAlgmap[g.r, g.cg, g.cg]
            # * Normal processes
        ] = Sum(
            [
                g.GrPrcmap[g.RpStd[g.r, g.p], g.Com, g.item],
                g.GrAlgmap[g.r, g.cg, g.Com],
            ],
            g.gr_genmap[g.r, g.p, g.item]
            * g.gr_genfr[g.r, g.t, g.c, g.item]
            * Sum(
                Domain(
                    g.RtpVintyr[g.r, g.v, g.t, g.p],
                    g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                ).where[g.rs_fr[g.r, g.s, g.ts]],
                include_cal_red
                * g.rs_fr[g.r, g.s, g.ts]
                * (1.0 + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow)),
            ).where[g.GrAllmap[g.r, g.c, g.Com]],
            # * Imports
        ) + Sum(
            Domain(
                g.GrPrcmap[g.RpIre[g.r, g.p], g.Com, g.item],
                g.RpcIre[g.r, g.p, g.Com, g.ie["IMP"]],
            ).where[g.GrAlgmap[g.r, g.cg, g.Com]],
            g.gr_genmap[g.r, g.p, g.item]
            * g.gr_genfr[g.r, g.t, g.c, g.item]
            * Sum(
                Domain(
                    g.RtpVintyr[g.r, g.v, g.t, g.p],
                    g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                ).where[g.rs_fr[g.r, g.s, g.ts]],
                (1.0 + g.ire_flosum[g.r, g.t, g.p, g.Com, g.ts, g.ie, g.Com, "OUT"])
                * (
                    VAR_IRE[g.r, g.v, g.t, g.p, g.Com, g.ts, g.ie, *sow].where[
                        (~(g.RpcAire[g.r, g.p, g.Com]))
                    ]
                    + (
                        VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow]
                        * g.prc_actflo[g.r, g.v, g.p, g.Com]
                    ).where[g.RpcAire[g.r, g.p, g.Com]]
                )
                * g.rs_fr[g.r, g.s, g.ts],
            ),
            # * Net storage output
        ) + Sum(
            [
                g.GrPrcmap[g.RpcStg[g.r, g.p, g.Com], g.item],
                g.GrAlgmap[g.r, g.cg, g.Com],
            ],
            g.gr_genmap[g.r, g.p, g.item]
            * g.gr_genfr[g.r, g.t, g.c, g.item]
            * Sum(
                [g.RtpVintyr[g.r, g.v, g.t, g.p], g.RpcsVar[g.r, g.p, g.Com, g.ts]],
                (
                    VAR_SOUT[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow]
                    - VAR_SIN[g.r, g.v, g.t, g.p, g.Com, g.ts, *sow].where[
                        g.Top[g.r, g.p, g.Com, "IN"]
                    ]
                )
                * g.rs_fr[g.r, g.s, g.ts],
            ),
            # * Net balance
        ) + Sum(
            g.GrAllmap[g.r, g.cg, g.c],
            VAR_GRIDIO[g.r, g.t, g.c, g.c, g.s, "OUT", *sow]
            - VAR_GRIDIO[g.r, g.t, g.c, g.c, g.s, "IN", *sow]
            - Sum(
                g.GrDemmap[g.r, g.c, g.Com],
                VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "OUT", *sow]
                - VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "IN", *sow].where[
                    g.GrAlgmap[g.r, "NRG", g.Com]
                ],
            ),
        ) == Sum(
            Domain(g.GrAlgmap[g.r, g.cg, g.Com], g.GrAllmap[g.r, g.c, g.Com]).where[
                g.Rtc[g.r, g.t, g.Com]
            ],
            VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "OUT", *sow]
            + VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "IN", *sow].where[
                g.GrAlgmap[g.r, g.Com, g.Com]
            ],
        )
        # *------------------------------------------------------------------------
        # * Demand fractions for all but the largest fraction
        eq_gr_demall[g.RtcsVarc[g.RcGrid[*r_t, g.c], rts], *swt].where[
            g.gr_demfr[g.r, g.t, g.c, g.s]
        ] = (
            # * Net injection
            Sum(
                g.GrEndc[g.r, g.Com],
                Sum(
                    g.Top[g.RpStd[g.r, g.p], g.Com, "OUT"].where[
                        (~(g.GrGenp[g.r, g.p] * g.GrDemmap[g.r, g.c, g.Com]))
                    ],
                    Sum(
                        Domain(
                            g.RtpVintyr[g.r, g.v, g.t, g.p],
                            g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                        ).where[g.rs_fr[g.r, g.s, g.ts]],
                        include_cal_red
                        * g.rs_fr[g.r, g.s, g.ts]
                        * (
                            1.0
                            + macro.rtcs_fr.rtcs_fr_GP(g.r, g.t, g.Com, g.s, g.ts, sow)
                        ),
                    )
                    * (
                        Sum(
                            g.GrPrcmap[g.r, g.p, g.Com, g.item],
                            g.gr_genmap[g.r, g.p, g.item]
                            * g.gr_genfr[g.r, g.t, g.c, g.item],
                        )
                        - g.gr_endfr[g.r, g.t, g.c, g.Com]
                        * (1.0 + g.gr_endfr[g.r, g.t, g.Com, g.Com])
                        - g.gr_demfr[g.r, g.t, g.c, g.s].where[
                            g.GrGenp[g.r, g.p] & g.GrEndc[g.r, "NRG"]
                        ]
                    ),
                ),
            )
            # * Exports
            + Sum(
                Domain(
                    g.GrPrcmap[g.RpIre[g.r, g.p], g.Com, g.item],
                    g.RpcIre[g.r, g.p, g.Com, g.ie["EXP"]],
                ).where[g.GrAlgmap[g.r, "NRG", g.Com]],
                g.gr_genmap[g.r, g.p, g.item]
                * (
                    g.gr_endfr[g.r, g.t, g.c, g.Com]
                    + g.gr_demfr[g.r, g.t, g.c, g.s].where[g.GrEndc[g.r, "NRG"]]
                    - g.gr_genfr[g.r, g.t, g.c, g.item]
                )
                * Sum(
                    Domain(
                        g.RtpVintyr[g.r, g.v, g.t, g.p],
                        g.RtpcsVarf[g.r, g.t, g.p, g.Com, g.ts],
                    ).where[g.rs_fr[g.r, g.s, g.ts]],
                    (1.0 + g.ire_flosum[g.r, g.t, g.p, g.Com, g.ts, g.ie, g.Com, "IN"])
                    * (
                        VAR_IRE[g.r, g.v, g.t, g.p, g.Com, g.ts, g.ie, *sow].where[
                            (~(g.RpcAire[g.r, g.p, g.Com]))
                        ]
                        + (
                            VAR_ACT[g.r, g.v, g.t, g.p, g.ts, *sow]
                            * g.prc_actflo[g.r, g.v, g.p, g.Com]
                        ).where[g.RpcAire[g.r, g.p, g.Com]]
                    )
                    * g.rs_fr[g.r, g.s, g.ts],
                ).where[g.GrAllmap[g.r, g.c, g.Com]],
            )
            # * Net demand shares
            + Sum(
                g.GrDemmap[g.r, g.c, g.Com].where[g.Rtc[g.r, g.t, g.Com]],
                VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "IN", *sow]
                - (
                    g.gr_endfr[g.r, g.t, g.c, g.Com]
                    + g.gr_demfr[g.r, g.t, g.c, g.s].where[g.GrEndc[g.r, "NRG"]]
                )
                * Sum(
                    g.Rtc[g.r, g.t, g.com2].where[g.GrDemmap[g.r, g.com2, g.Com]],
                    VAR_GRIDIO[g.r, g.t, g.Com, g.com2, g.s, "IN", *sow],
                ),
            )
            == 0.0
        )
        # *------------------------------------------------------------------------
        # * Bound on net imports/exports from grid J
        eq_gr_xbnd[*r_t, g.j, g.ie, rts, *swt].where[
            (g.Finest[g.r, g.s].where[g.GrGrid[g.j, g.r, "ACT"] & g.gr_xbnd[g.r, g.t]])
        ] = (
            Sum(
                Domain(g.GrGrid[g.j, g.r, g.c], g.GrDemmap[g.r, g.c, g.Com]).where[
                    (g.Rtc[g.r, g.t, g.Com].where[g.RcGrid[g.r, g.t, g.c]])
                ],
                Product(g.xpt[g.ie], -1.0)
                * (
                    VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "IN", *sow].where[
                        g.GrAlgmap[g.r, "NRG", g.Com]
                    ]
                    - VAR_GRIDIO[g.r, g.t, g.Com, g.c, g.s, "OUT", *sow]
                ),
            )
            <= Sum(
                Domain(
                    g.GrGrid[g.j, g.r, g.c], g.TopIre[g.r, g.c, g.allr, g.Com, g.p]
                ).where[((~(same_as(g.r, g.allr))).where[g.RcGrid[g.r, g.t, g.c]])],
                Sum(
                    g.v.where[g.coef_vnt[g.r, g.t, g.p, g.v]],
                    g.coef_vnt[g.r, g.t, g.p, g.v]
                    * g.prc_capact[g.r, g.p]
                    * g.gr_xbnd[g.r, g.t]
                    * g.g_yrfr[g.r, g.s]
                    * (
                        macro.VAR_NCAP_GP(varv, g.r, g.v, g.p, sws).where[g.tt[g.v]]
                        + g.ncap_pasti[g.r, g.v, g.p].where[g.Pastyear[g.v]]
                    ),
                ).where[g.PrcCap[g.r, g.p]]
                + Sum(
                    Domain(g.Reg[g.allr], g.v).where[g.coef_vnt[g.Reg, g.t, g.p, g.v]],
                    g.coef_vnt[g.Reg, g.t, g.p, g.v]
                    * g.prc_capact[g.Reg, g.p]
                    * g.gr_xbnd[g.r, g.t]
                    * g.g_yrfr[g.r, g.s]
                    * (
                        macro.VAR_NCAP_GP(varv, g.Reg, g.v, g.p, sws).where[g.tt[g.v]]
                        + g.ncap_pasti[g.Reg, g.v, g.p].where[g.Pastyear[g.v]]
                    ).where[g.PrcCap[g.Reg, g.p]],
                ).where[(~(g.PrcCap[g.r, g.p]))],
            ).where[g.xpt[g.ie]]
            + Sum(
                Domain(
                    g.TopIre[g.allr, g.Com, g.r, g.c, g.p], g.GrGrid[g.j, g.r, g.c]
                ).where[((~(same_as(g.r, g.allr))).where[g.RcGrid[g.r, g.t, g.c]])],
                Sum(
                    g.v.where[g.coef_vnt[g.r, g.t, g.p, g.v]],
                    g.coef_vnt[g.r, g.t, g.p, g.v]
                    * g.prc_capact[g.r, g.p]
                    * g.gr_xbnd[g.r, g.t]
                    * g.g_yrfr[g.r, g.s]
                    * (
                        macro.VAR_NCAP_GP(varv, g.r, g.v, g.p, sws).where[g.tt[g.v]]
                        + g.ncap_pasti[g.r, g.v, g.p].where[g.Pastyear[g.v]]
                    ),
                ).where[g.PrcCap[g.r, g.p]]
                + Sum(
                    Domain(g.Reg[g.allr], g.v).where[g.coef_vnt[g.Reg, g.t, g.p, g.v]],
                    g.coef_vnt[g.Reg, g.t, g.p, g.v]
                    * g.prc_capact[g.Reg, g.p]
                    * g.gr_xbnd[g.r, g.t]
                    * g.g_yrfr[g.r, g.s]
                    * (
                        macro.VAR_NCAP_GP(varv, g.Reg, g.v, g.p, sws).where[g.tt[g.v]]
                        + g.ncap_pasti[g.Reg, g.v, g.p].where[g.Pastyear[g.v]]
                    ).where[g.PrcCap[g.Reg, g.p]],
                ).where[(~(g.PrcCap[g.r, g.p]))],
            ).where[g.imp[g.ie]]
        )

    def comp2(self: PowerfloVda) -> None:
        g = self.tc
        m = g.container
        # * Preprocess nodal balance costs
        if g.obv is None:
            g.obv = Set(m, name="OBV", records=["OBJBAL"])
        else:
            expand_set(g.obv, ["OBJBAL"])
        self.add_records_to_universe_item(records=["CON", "NTX", "NPG"])

        g.RcGrid = Set(m, name="RC_GRID", domain=[g.r, g.t, g.c])
        g.GrAllmap = Set(m, name="GR_ALLMAP", domain=[g.r, g.cg, g.Com])
        g.GrPrcmap = Set(m, name="GR_PRCMAP", domain=[g.r, g.p, g.c, g.item])
        g.GrDemmap = Set(m, name="GR_DEMMAP", domain=[g.r, g.c, g.Com])
        g.GrAlgmap = Set(m, name="GR_ALGMAP", domain=[g.r, g.cg, g.cg])
        g.GrEndc = Set(m, name="GR_ENDC", domain=[g.r, g.cg])
        g.obj_combal = Parameter(
            m, name="OBJ_COMBAL", domain=[g.r, g.t, g.c, g.s, g.item, g.cur]
        )

    def exec6(self: PowerfloVda) -> None:
        g = self.tc
        g.RcGrid.setRecords(None)
        g.GrAllmap.setRecords(None)
        g.GrAlgmap.setRecords(None)
        g.GrDemmap.setRecords(None)
        g.GrPrcmap.setRecords(None)
        g.GrEndc.setRecords(None)

    def exec7(self: PowerfloVda) -> None:
        g = self.tc
        project(source=g.com_cstbal, target=g.Trackc)
        g.Trackc[g.r, g.c].where[Sum(g.GrAllmap[g.r, g.c, g.Com], 1.0)] = False
        g.obj_combal[g.RtcsVarc[g.Rtc[g.r, g.t, g.c], g.ts], "PRD", g.cur].where[
            g.Trackc[g.r, g.c]
        ] = Sum(
            g.TsAnn[g.ts, g.s],
            g.com_cstbal[g.Rtc, g.s, "PRD", g.cur]
            + g.com_cstbal[g.Rtc, g.s, "CON", g.cur]
            + g.com_cstbal[g.Rtc, g.s, "OUT", g.cur],
        )
        g.obj_combal[g.RtcsVarc[g.Rtc[g.r, g.t, g.c], g.ts], "IMP", g.cur].where[
            g.Trackc[g.r, g.c]
        ] = Sum(
            g.TsAnn[g.ts, g.s],
            g.com_cstbal[g.Rtc, g.s, "IMP", g.cur]
            + g.com_cstbal[g.Rtc, g.s, "NTX", g.cur]
            - g.com_cstbal[g.Rtc, g.s, "PRD", g.cur],
        )
        g.obj_combal[g.RtcsVarc[g.Rtc[g.r, g.t, g.c], g.ts], "EXP", g.cur].where[
            g.Trackc[g.r, g.c]
        ] = Sum(
            g.TsAnn[g.ts, g.s],
            g.com_cstbal[g.Rtc, g.s, "EXP", g.cur]
            - g.com_cstbal[g.Rtc, g.s, "NTX", g.cur]
            - g.com_cstbal[g.Rtc, g.s, "CON", g.cur],
        )
        with Loop(g.Rdcur[g.r, g.cur]):
            g.RhsComprd[g.RtcsVarc[g.r, g.t, g.c, g.s]].where[
                g.obj_combal[g.r, g.t, g.c, g.s, "PRD", g.cur]
            ] = True
        g.RcsComprd[g.RhsComprd[g.r, g.t, g.c, g.s], "FX"].where[g.Trackc[g.r, g.c]] = (
            True
        )
        g.obj_combal[g.RtcsVarc[g.Rtc[g.RcGrid], g.ts], "GEN", g.cur] = Sum(
            g.TsAnn[g.ts, g.s],
            g.com_cstbal[g.Rtc, g.s, "PRD", g.cur]
            + g.com_cstbal[g.Rtc, g.s, "CON", g.cur],
        )
        g.obj_combal[g.RtcsVarc[g.Rtc[g.RcGrid], g.ts], "NTX", g.cur] = Sum(
            g.TsAnn[g.ts, g.s],
            g.com_cstbal[g.Rtc, g.s, "NTX", g.cur]
            + g.com_cstbal[g.Rtc, g.s, "CON", g.cur],
        )
        g.obj_combal[g.RtcsVarc[g.Rtc[g.RcGrid], g.ts], g.ie, g.cur] = Sum(
            g.TsAnn[g.ts, g.s], g.com_cstbal[g.Rtc, g.s, g.ie, g.cur]
        )
        # * Add balancer variables if penalty costs on excess

        g.Uncd7.setRecords(None)
        g.Uncd7[
            g.r,
            g.t.lag(Ord(g.t), "circular"),
            g.c,
            g.s.lag(Ord(g.s), "circular"),
            g.cur,
            "",
            "",
        ].where[g.RcGrid[g.r, g.t, g.c]] = sparse(
            g.com_cstbal[g.r, g.t, g.c, g.s, "NPG", g.cur]
        )
        with Loop(g.Uncd7[g.r, g.tt, g.c, g.sl, g.cur, "", ""]):
            g.GrAllmap[g.r, "FIN", g.c] = True
            g.GrAlgmap[g.r, g.cg["FIN"], g.cg] = True
            g.obj_combal[g.RcGrid[g.r, g.t, g.c], g.ts, "NPG", g.cur] = sparse(
                Sum(g.TsAnn[g.ts, g.s], g.com_cstbal[g.r, g.t, g.c, g.s, "NPG", g.cur])
            )
        g.Trackc.setRecords(None)

    def eq_objbal(
        self: PowerfloVda,
        cal_red: str,
        sowpre: SowGPType,
        var: str,
        swd: tuple[Set | Alias] | tuple[()],
        swx: tuple[Literal["1"] | Set | Alias] | tuple[()],
        swsw: tuple[Set | Alias | ImplicitSet, ...]
        | tuple[ImplicitSet, ImplicitParameter]
        | tuple[()],
        sow: SowGPType,
        tpulse: tuple[Condition | Domain, Expression | ImplicitParameter | Number],
        pgprim: str,
        def_rtp_ffcs: bool,
        condition: bool,
    ) -> None:
        if cal_red == "cal_red.red":
            from core.cal_red_red import cal_red_red_GP as cal_red_func_GP
        elif cal_red == "cal_nored.red":
            from core.cal_nored_red import cal_nored_red_GP as cal_red_func_GP
        else:
            raise ValueError(f"Unexpected value for cal_red: {cal_red}")

        g = self.tc
        m = g.container
        r, c, io, cur, s, year, allsow = g.r, g.c, g.io, g.cur, g.s, g.year, g.allsow
        t, Com, p, v, ts, ie, tt = g.t, g.Com, g.p, g.v, g.ts, g.ie, g.tt

        include_cal_red = cal_red_func_GP(
            g=g,
            config=CalRedRedConfig(
                arg1=Com,
                arg2=g.com1,
                arg3=ts,
                arg4=p,
                arg5=t,
                var=var,
                sow=sow,
                pgprim=pgprim,
                def_rtp_ffcs=def_rtp_ffcs,
                arg10=Number(1),
            ),
        )
        g.set_variable(
            f"{var}_GRIDIO",
            Variable(
                m,
                name=f"{var}_GRIDIO",
                domain=[r, year, c, c, s, io, *swd],
                type="POSITIVE",
            ),
        )
        g.eq_objbal = Equation(m, name="EQ_OBJBAL", domain=[r, cur, allsow])
        VAR_GRIDIO = g.get_variable(f"{var}_GRIDIO")
        VAR_OBJ = g.get_variable(f"{var}_OBJ")
        VAR_COMPRD = g.get_variable(f"{var}_COMPRD")
        VAR_IRE = g.get_variable(f"{var}_IRE")
        VAR_ACT = g.get_variable(f"{var}_ACT")
        obj_combal = g.obj_combal

        # * Costs on commodity production
        rhs: Expression | Sum = (
            Sum(
                g.RhsComprd[r, t, c, s],
                VAR_COMPRD[r, t, c, s, *sow]
                * wrap_in_sum(obj_combal[r, tt, c, s, "PRD", cur], tpulse),  # type: ignore[arg-type]
            )
            + Sum(
                g.RtcsVarc[g.RcGrid[r, t, c], s].where[
                    obj_combal[r, t, c, s, "GEN", cur]
                ],
                (
                    Sum(
                        g.GrAlgmap[r, g.cg, Com].where[g.GrAllmap[r, c, Com]],
                        VAR_GRIDIO[r, t, Com, c, s, "OUT", *sow]
                        + VAR_GRIDIO[r, t, Com, c, s, "IN", *sow].where[
                            g.GrAlgmap[r, Com, Com]
                        ],
                    )
                    + Sum(
                        Domain(
                            g.GrPrcmap[g.RpStd[r, p], Com, g.item], g.GrEndc[r, Com]
                        ),
                        g.gr_genmap[r, p, g.item]
                        * g.gr_genfr[r, t, c, g.item]
                        * Sum(
                            Domain(
                                g.RtpVintyr[r, v, t, p], g.RtpcsVarf[r, t, p, Com, ts]
                            ).where[g.rs_fr[r, s, ts]],
                            include_cal_red * g.rs_fr[r, s, ts],
                        ),
                    )
                )
                * wrap_in_sum(obj_combal[r, tt, c, s, "GEN", cur], tpulse),  # type: ignore[arg-type]
            )
            # * Costs on net imports to grid node
            + Sum(
                g.RtcsVarc[g.RcGrid[r, t, c], s].where[
                    obj_combal[r, t, c, s, "NTX", cur]
                ],
                Sum(
                    g.GrDemmap[r, c, Com],
                    VAR_GRIDIO[r, t, Com, c, s, "IN", *sow].where[
                        g.GrAlgmap[r, "NRG", Com]
                    ]
                    - VAR_GRIDIO[r, t, Com, c, s, "OUT", *sow],
                )
                * wrap_in_sum(obj_combal[r, tt, c, s, "NTX", cur], tpulse),  # type: ignore[arg-type]
            )
            # * Costs on Net Positive Generation (NPG)
            + Sum(
                g.RtcsVarc[g.RcGrid[r, t, c], s].where[
                    obj_combal[r, t, c, s, "NPG", cur]
                ],
                VAR_GRIDIO[r, t, c, c, s, "OUT", *sow]
                * wrap_in_sum(Max(0.0, obj_combal[r, tt, c, s, "NPG", cur]), tpulse),  # type: ignore[arg-type]
            )
            # * Costs on commodity imports / exports
            + Sum(
                Domain(g.RtpcsVarf[r, t, p, c, s], g.RpcIre[r, p, c, ie]).where[
                    obj_combal[r, t, c, s, ie, cur]
                ],
                Sum(
                    g.RtpVintyr[r, v, t, p],
                    VAR_IRE[r, v, t, p, c, s, ie, *sow].where[~g.RpcAire[r, p, c]]
                    + (VAR_ACT[r, v, t, p, s, *sow] * g.prc_actflo[r, v, p, c]).where[
                        g.RpcAire[r, p, c]
                    ],
                )
                * wrap_in_sum(obj_combal[r, tt, c, s, ie, cur], tpulse),  # type: ignore[arg-type]
            )
        )
        if condition:
            rhs = wrap_in_sum(rhs, swsw)  # type: ignore[arg-type]

        g.eq_objbal[g.Rdcur[r, cur], *swx] = VAR_OBJ[r, "OBJBAL", cur, *sowpre] == rhs

    def exec_powerflo_vda_rptb(
        self: PowerfloVda,
        arg4: str,
        arg5: tuple[Set | Alias | str, ...] | tuple[()],
        arg6: SowGPType,
        var: str,
        vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
        sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    ) -> None:
        powerflo_vda_rptb_GP(
            g=self.tc,
            arg4=arg4,
            arg5=arg5,
            arg6=arg6,
            var=var,
            vart=vart,
            sws=sws,
        )


def powerflo_vda_ireaux_GP(
    g: TimesModelClass,
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    var: str = "",
    sow: tuple[Literal["0", "1"] | Set | Alias, ...] | tuple[()] = (),
) -> Expression | ImplicitSet | int:
    """GAMSPy counterpart of powerflo_vda_ireaux(). Returns 0 outside the two labels."""
    target_label = f"{arg1}{arg2}{arg3}".strip().upper()

    if target_label not in ["IREAUXIN", "IREAUXOUT-"]:
        return 0

    r, t, c, s, Com = g.r, g.t, g.c, g.s, g.Com
    VAR_GRIDIO: Variable = g.get_variable(f"{var}_GRIDIO")

    # arg3 is "-" for IREAUXOUT-, i.e. the terms are negated
    def mx(expr: Expression | ImplicitSet) -> Expression | ImplicitSet:
        if target_label == "IREAUXIN":
            return g.com_ie[r, t, c, s] * expr
        return -expr

    # * For balance of C (and grid nodes COM)
    balance_c = Sum(
        g.GrDemmap[r, Com, c],
        mx(
            VAR_GRIDIO[r, t, c, Com, s, "OUT", *sow]
            - VAR_GRIDIO[r, t, c, Com, s, "IN", *sow].where[g.GrAlgmap[r, "NRG", c]]
        ),
    )
    # * For balance of grid node C
    balance_node = Sum(
        g.GrDemmap[r, c, Com],
        mx(
            VAR_GRIDIO[r, t, Com, c, s, "IN", *sow].where[g.GrAlgmap[r, "NRG", Com]]
            - VAR_GRIDIO[r, t, Com, c, s, "OUT", *sow]
        ),
    )
    return balance_c + balance_node


def powerflo_vda_rptb(
    arg4: str,
    arg5: str,
    arg6: str,
    var: str,
    vart: str,
    sws: str,
) -> str:
    return rf"""
 {arg4}REG_WOBJ({arg5}R,'VAR',CUR) = {arg4}REG_WOBJ({arg5}R,'VAR',CUR) + {var}_OBJ.L(R,'OBJBAL',CUR{arg6});
 OPTION TRACKC < COM_CSTBAL;
 {arg4}CST_COMC({arg5}RTC(R,T,C))$TRACKC(R,C) = {arg4}CST_COMC({arg5}RTC) +
   SUM((RTCS_VARC(RTC,S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'PRD',CUR),OBJ_COMBAL(RTC,S,'PRD',CUR)*VAR_COMPRD.L(RTC,S)) +
   SUM((RPCS_VAR(R,P,C,S),RPC_IRE(R,P,C,IE),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,IE,CUR),
     SUM(RTP_VINTYR(R,V,T,P),OBJ_COMBAL(RTC,S,IE,CUR)*PAR_IRE(R,V,T,P,C,S,IE))) +
* Cost on generation to grid
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'GEN',CUR),
     OBJ_COMBAL(RTC,S,'GEN',CUR) *
     (SUM(GR_ALGMAP(R,CG,COM),{vart}_GRIDIO.L(R,T,COM,C,S,'OUT' {sws}) + {vart}_GRIDIO.L(R,T,COM,C,S,'IN'{sws})$GR_ALGMAP(R,COM,COM))+
      SUM((GR_PRCMAP(RP_STD(R,P),COM,ITEM),GR_ENDC(R,COM)), GR_GENMAP(R,P,ITEM)*GR_GENFR(RTC,ITEM) *
        SUM((RTP_VINTYR(R,V,T,P),RPCS_VAR(R,P,C,TS))$RS_FR(R,S,TS),
          PAR_FLO(R,V,T,P,C,TS)*RS_FR(R,S,TS))))) +
* Costs on net imports to grid node
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'NTX',CUR),
     SUM(GR_DEMMAP(R,C,COM),{vart}_GRIDIO.L(R,T,COM,C,S,'IN'{sws})$GR_ALGMAP(R,'NRG',COM) - {vart}_GRIDIO.L(R,T,COM,C,S,'OUT'{sws})) *
     OBJ_COMBAL(RTC,S,'NTX',CUR)) +
* Costs on Net Positive Generation (NPG)
   SUM((RTCS_VARC(RC_GRID(RTC),S),RDCUR(R,CUR))$OBJ_COMBAL(RTC,S,'NPG',CUR),
     {vart}_GRIDIO.L(RTC,C,S,'OUT'{sws}) * OBJ_COMBAL(RTC,S,'NPG',CUR));

 OPTION CLEAR=TRACKC;
"""


def powerflo_vda_rptb_GP(
    g: TimesModelClass,
    arg4: str,
    arg5: tuple[Set | Alias | str, ...] | tuple[()],
    arg6: SowGPType,
    var: str,
    vart: tuple[str, ImplicitSet | tuple[ImplicitSet, ImplicitParameter] | None],
    sws: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
) -> None:
    """GAMSPy counterpart of powerflo_vda_rptb()."""
    r, t, c, s, cur, p, v, ie, ts, Com = (
        g.r, g.t, g.c, g.s, g.cur, g.p, g.v, g.ie, g.ts, g.Com
    )  # fmt: skip
    Rtc, obj_combal = g.Rtc, g.obj_combal
    reg_wobj = g.get_parameter(f"{arg4}REG_WOBJ")
    cst_comc = g.get_parameter(f"{arg4}CST_COMC")
    VAR_OBJ = g.get_variable(f"{var}_OBJ")
    vart_id, vart_set = extract_var_domain(vart)
    VART_GRIDIO = g.get_variable(f"{vart_id}_GRIDIO")

    reg_wobj[*arg5, r, "VAR", cur] = (
        reg_wobj[*arg5, r, "VAR", cur] + VAR_OBJ.l[r, "OBJBAL", cur, *arg6]
    )
    project(source=g.com_cstbal, target=g.Trackc)
    cst_comc[*arg5, Rtc[r, t, c]].where[g.Trackc[r, c]] = (
        cst_comc[*arg5, Rtc]
        + Sum(
            Domain(g.RtcsVarc[Rtc, s], g.Rdcur[r, cur]).where[
                obj_combal[Rtc, s, "PRD", cur]
            ],
            obj_combal[Rtc, s, "PRD", cur] * g.VAR_COMPRD.l[Rtc, s],
        )
        + Sum(
            Domain(g.RpcsVar[r, p, c, s], g.RpcIre[r, p, c, ie], g.Rdcur[r, cur]).where[
                obj_combal[Rtc, s, ie, cur]
            ],
            Sum(
                g.RtpVintyr[r, v, t, p],
                obj_combal[Rtc, s, ie, cur] * g.par_ire[r, v, t, p, c, s, ie],
            ),
        )
        # * Cost on generation to grid
        + Sum(
            Domain(g.RtcsVarc[g.RcGrid[Rtc], s], g.Rdcur[r, cur]).where[
                obj_combal[Rtc, s, "GEN", cur]
            ],
            obj_combal[Rtc, s, "GEN", cur]
            * (
                Sum(
                    g.GrAlgmap[r, g.cg, Com],
                    wrap_in_sum(VART_GRIDIO.l[r, t, Com, c, s, "OUT", *sws], vart_set)
                    + wrap_in_sum(
                        VART_GRIDIO.l[r, t, Com, c, s, "IN", *sws], vart_set
                    ).where[g.GrAlgmap[r, Com, Com]],
                )
                + Sum(
                    Domain(g.GrPrcmap[g.RpStd[r, p], Com, g.item], g.GrEndc[r, Com]),
                    g.gr_genmap[r, p, g.item]
                    * g.gr_genfr[Rtc, g.item]
                    * Sum(
                        Domain(g.RtpVintyr[r, v, t, p], g.RpcsVar[r, p, c, ts]).where[
                            g.rs_fr[r, s, ts]
                        ],
                        g.par_flo[r, v, t, p, c, ts] * g.rs_fr[r, s, ts],
                    ),
                )
            ),
        )
        # * Costs on net imports to grid node
        + Sum(
            Domain(g.RtcsVarc[g.RcGrid[Rtc], s], g.Rdcur[r, cur]).where[
                obj_combal[Rtc, s, "NTX", cur]
            ],
            Sum(
                g.GrDemmap[r, c, Com],
                wrap_in_sum(VART_GRIDIO.l[r, t, Com, c, s, "IN", *sws], vart_set).where[
                    g.GrAlgmap[r, "NRG", Com]
                ]
                - wrap_in_sum(VART_GRIDIO.l[r, t, Com, c, s, "OUT", *sws], vart_set),
            )
            * obj_combal[Rtc, s, "NTX", cur],
        )
        # * Costs on Net Positive Generation (NPG)
        + Sum(
            Domain(g.RtcsVarc[g.RcGrid[Rtc], s], g.Rdcur[r, cur]).where[
                obj_combal[Rtc, s, "NPG", cur]
            ],
            wrap_in_sum(VART_GRIDIO.l[Rtc, c, s, "OUT", *sws], vart_set)
            * obj_combal[Rtc, s, "NPG", cur],
        )
    )

    g.Trackc.setRecords(None)
