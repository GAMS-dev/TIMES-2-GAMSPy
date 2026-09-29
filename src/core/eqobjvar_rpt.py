# eqobjvar_rpt.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * EQOBJVAR - the variable O&M, flow and commodity direct costs
# *  arg1 - mod or prefix
# *  arg2 - '1', or J(UNCD1),
# *  arg3 - '2', or J(UNCD1),
# *  arg4 - T OR Y_EOH
# *  arg5 - SUM or ''

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gamspy import Domain, Loop, Number, Sum, sparse
from gamspy.math import diag, power, project

from core.base_class import GamsClass
from core.cal_caps_mod import CalCapsModConfig, cal_caps_mod, cal_caps_mod_GP
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy._algebra.condition import Condition
    from gamspy._algebra.expression import Expression
    from gamspy._symbols.implicits import ImplicitParameter, ImplicitSet
    from gamspy.math import MathOp

    from core.utils import SET_OR_ALIAS
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

    # %TPULSE% / %TMP% always expand to "<sum domain>,<multiplier of the summand>"
    PulseSum = tuple[Condition | Domain, Expression | ImplicitParameter | Number | int]

logger = logging.getLogger(__name__)


@dataclass
class EqobjvarRptConfig:
    """Strongly typed data contract for eqobjvar.rpt."""

    # %1 - 'mod' selects the legacy reporting, anything else is a parameter prefix
    arg1: str = "mod"
    # %2 - the leading index of the cost slice, e.g. (J('1'),) or (J(UNCD1),)
    arg2: tuple[ImplicitSet | SET_OR_ALIAS | str, ...] | tuple[()] = ()
    # %3 - the leading index of the tax slice, e.g. (J('2'),)
    arg3: tuple[ImplicitSet | SET_OR_ALIAS | str, ...] | tuple[()] = ()
    # %4 - year index (T or Y_EOH)
    arg4: SET_OR_ALIAS | None = None
    # %5 - True where the legacy '%5' was SUM: the annual cost terms are summed
    #      over the %TPULSE% years instead of being taken for a single year
    arg5: bool = False
    # %TPULSE% and %TMP%. `$IFI '%5'=='' $SET TPULSE '' SET TMP ''` blanks both
    # whenever %5 is empty, so they are only ever read when arg5 is True.
    tpulse: PulseSum | None = None
    tmp: PulseSum | None = None


class EqobjvarRpt(GamsClass):
    """Translation unit for eqobjvar.rpt."""

    # Instance attributes
    module_name: str = "eqobjvar_rpt"
    gams_source: str = "eqobjvar.rpt"

    def __init__(
        self, tc: TimesModelClass, env: CompileEnvironment, config: EqobjvarRptConfig
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.config = config
        self.compile()

    def compile(self) -> None:
        self.tc.enqueue(
            self.exec_eqobjvar_rpt,
            config=self.config,
            pgprim=self.env.pgprim,
            stages=self.env.stages,
            is_vnret_defined=self.tc.defined("VNRET"),
            varv=self.env.varv_GP,
            sws=self.env.sws_GP,
            varm=self.env.varm_GP,
        )

    def exec_eqobjvar_rpt(
        self: EqobjvarRpt,
        config: EqobjvarRptConfig,
        pgprim: str,
        stages: str,
        is_vnret_defined: bool,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varm: tuple[str, ImplicitSet | None],
    ) -> None:
        # $IFI '%1'==MOD $GOTO LEGACY
        if config.arg1.upper() != "MOD":
            self._current(
                config=config,
                pgprim=pgprim,
                stages=stages,
                is_vnret_defined=is_vnret_defined,
                varv=varv,
                sws=sws,
                varm=varm,
            )
        else:
            self._legacy(
                is_vnret_defined=is_vnret_defined, varv=varv, sws=sws, varm=varm
            )

    def _current(
        self: EqobjvarRpt,
        config: EqobjvarRptConfig,
        pgprim: str,
        stages: str,
        is_vnret_defined: bool,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varm: tuple[str, ImplicitSet | None],
    ) -> None:
        g = self.tc
        cc = config

        r, v, t, p, c, s, sl, ts, tsl, cur, j, io, ie, upt, bd, lA = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.sl,
            g.ts,
            g.tsl,
            g.cur,
            g.j,
            g.io,
            g.ie,
            g.upt,
            g.bd,
            g.lA,
        )
        Annual, Bdneq, Ble, BleOpr, Opr, PrcTs, Rdcur = (
            g.Annual,
            g.Bdneq,
            g.Ble,
            g.BleOpr,
            g.Opr,
            g.PrcTs,
            g.Rdcur,
        )
        RhsCombal, RhsComprd, Rpc, RpcCapflo, RpcCur, RpcIre, RpcIreio, RpcStg = (
            g.RhsCombal,
            g.RhsComprd,
            g.Rpc,
            g.RpcCapflo,
            g.RpcCur,
            g.RpcIre,
            g.RpcIreio,
            g.RpcStg,
        )
        RpcsVar, RpDpl, RpIre, RpStg, RpUpr, RpUps, RpUpt = (
            g.RpcsVar,
            g.RpDpl,
            g.RpIre,
            g.RpStg,
            g.RpUpr,
            g.RpUps,
            g.RpUpt,
        )
        RtcsVarc, RtpcsVarf, RtpVintyr, TsAnn, TsGroup, Trackpc, Vnt = (
            g.RtcsVarc,
            g.RtpcsVarf,
            g.RtpVintyr,
            g.TsAnn,
            g.TsGroup,
            g.Trackpc,
            g.Vnt,
        )
        ObjVflo, Sow, SwTsw, comvar, w = (
            g.ObjVflo,
            g.Sow,
            g.SwTsw,
            g.comvar,
            g.w,
        )
        act_cstrmp, act_cstsd, act_cstup, f_inouts, g_yrfr = (
            g.act_cstrmp,
            g.act_cstsd,
            g.act_cstup,
            g.f_inouts,
            g.g_yrfr,
        )
        obj_blndv, obj_comnt, obj_compd, obj_ipric, par_flo, par_ire = (
            g.obj_blndv,
            g.obj_comnt,
            g.obj_compd,
            g.obj_ipric,
            g.par_flo,
            g.par_ire,
        )
        rs_stgav, rs_stgprd, s_com_tax, stg_eff, sw_prob, z = (
            g.rs_stgav,
            g.rs_stgprd,
            g.s_com_tax,
            g.stg_eff,
            g.sw_prob,
            g.z,
        )
        VAR_ACT, VAR_BLND, VAR_COMNET, VAR_COMPRD, VAR_SIN, VAR_SOUT = (
            g.VAR_ACT,
            g.VAR_BLND,
            g.VAR_COMNET,
            g.VAR_COMPRD,
            g.VAR_SIN,
            g.VAR_SOUT,
        )
        VAR_UDP, VAR_UPS, VAR_UPT = g.VAR_UDP, g.VAR_UPS, g.VAR_UPT

        ACTC = g.get_parameter(f"{cc.arg1}_ACTC")
        COMC = g.get_parameter(f"{cc.arg1}_COMC")
        FLOC = g.get_parameter(f"{cc.arg1}_FLOC")

        # %4 is only optional because the legacy branch does not take a year index
        assert cc.arg4 is not None
        y = cc.arg4

        def summed(
            pair: PulseSum | None,
            x: Expression | ImplicitParameter | MathOp,
        ) -> Expression | ImplicitParameter | MathOp | Sum:
            """%5(<pair> x): sum x over the pulse years, or take it as is."""
            if not cc.arg5:
                return x
            assert pair is not None
            domain, multiplier = pair
            return Sum(domain, multiplier * x)

        def pulse(
            x: Expression | ImplicitParameter | MathOp,
        ) -> Expression | ImplicitParameter | MathOp | Sum:
            """%5(%TPULSE% x)"""
            return summed(cc.tpulse, x)

        # $IFI %STAGES%==YES Z=SUM(W(SOW),SW_PROB(W));
        if stages.upper() == "YES":
            z[...] = Sum(w[Sow], sw_prob[w])

        # *----------------------------------------------------------------------
        ACTC.setRecords(None)
        COMC.setRecords(None)
        FLOC.setRecords(None)

        # *----------------------------------------------------------------------
        # * Costs based on overall activity of process
        # *----------------------------------------------------------------------
        ACTC[*cc.arg2, RtpVintyr[r, v, t, p], pgprim, cur].where[
            Rdcur[r, cur] & macro.obj_acost_GP(r, t, p, cur)
        ] = pulse(macro.obj_acost_GP(r, y, p, cur)) * Sum(
            PrcTs[r, p, s],
            VAR_ACT.l[r, v, t, p, s]
            * power(rs_stgav[r, s], Number(1).where[RpStg[r, p]]),
        )
        ACTC[*cc.arg3, RtpVintyr[r, v, t, p], c[pgprim], cur].where[
            RpcCur[r, p, c, cur]
        ] = (
            Sum(
                RpUps[r, p, tsl, lA["UP"]],
                pulse(act_cstup[r, v, p, tsl, cur])
                * Sum(
                    TsGroup[r, tsl, s],
                    rs_stgprd[r, s] * VAR_UPS.l[r, v, t, p, s, lA],
                ),
            )
            + Sum(
                RpUpt[r, p, upt, "UP"],
                pulse(
                    act_cstsd[r, v, p, upt, "FX", cur]
                    * Sum(
                        TsGroup[r, tsl, s].where[RpDpl[r, p, tsl]],
                        rs_stgprd[r, s] * VAR_UPT.l[r, v, t, p, s, upt],
                    )
                ),
            )
            + Sum(
                RpUpr[r, p, Bdneq[bd]],
                pulse(act_cstrmp[r, v, p, bd, cur])
                * Sum(
                    PrcTs[r, p, s],
                    rs_stgprd[r, s] * VAR_UDP.l[r, v, t, p, s, bd],
                ),
            )
        )

        # *----------------------------------------------------------------------
        # * Commodity added costs and sub/tax
        # *----------------------------------------------------------------------
        COMC[*cc.arg2, r, t, c, cur].where[Rdcur[r, cur]] = sparse(
            Sum(
                RhsCombal[r, t, c, s],
                VAR_COMNET.l[r, t, c, s] * pulse(obj_comnt[r, y, c, s, "COST", cur]),
            )
            + Sum(
                RhsComprd[r, t, c, s],
                VAR_COMPRD.l[r, t, c, s] * pulse(obj_compd[r, y, c, s, "COST", cur]),
            )
        )
        COMC[*cc.arg3, r, t, c, cur].where[Rdcur[r, cur]] = sparse(
            Sum(
                RhsCombal[r, t, c, s],
                VAR_COMNET.l[r, t, c, s]
                * pulse(
                    obj_comnt[r, y, c, s, "TAX", cur]
                    + obj_comnt[r, y, c, s, "SUB", cur]
                ),
            )
            + Sum(
                RhsComprd[r, t, c, s],
                VAR_COMPRD.l[r, t, c, s]
                * pulse(
                    obj_compd[r, y, c, s, "TAX", cur]
                    + obj_compd[r, y, c, s, "SUB", cur]
                ),
            )
        )
        if stages.upper() == "YES":
            # RTC(R,T,C) of the assignment domain already restricts R/T/C, so the
            # RTC tuple-set of the GAMS source is spelled out as R,T,C here.
            COMC[*cc.arg3, g.Rtc[r, t, c], cur].where[Rdcur[r, cur]] = sparse(
                Sum(
                    Domain(RtcsVarc[r, t, c, s], comvar, SwTsw[Sow, t, w]).where[
                        s_com_tax[r, t, c, s, comvar, cur, "1", w]
                    ],
                    (
                        summed(cc.tmp, s_com_tax[r, y, c, s, comvar, cur, "1", w])
                        * (
                            VAR_COMPRD.l[r, t, c, s].where[diag("PRD", comvar)]
                            + VAR_COMNET.l[r, t, c, s].where[diag("NET", comvar)]
                        )
                        + COMC[j, r, t, c, cur] * g_yrfr[r, s]
                    )
                    * sw_prob[w]
                    / z,
                )
            )

        # *----------------------------------------------------------------------
        # * Commodity costs associated with imports/exports from outside study area
        # *----------------------------------------------------------------------
        FLOC[*cc.arg2, RtpVintyr[r, v, t, p], c, cur].where[
            Rdcur[r, cur] & Rpc[r, p, c] & RpIre[r, p]
        ] = sparse(
            Sum(
                Domain(RtpcsVarf[r, t, p, c, s], RpcIreio[r, p, c, ie, "OUT"]),
                pulse(obj_ipric[r, y, p, c, s, ie, cur])
                * par_ire[r, v, t, p, c, s, ie],
            )
        )

        # *----------------------------------------------------------------------
        # * Flow level costs
        # *----------------------------------------------------------------------
        project(source=par_flo, target=Trackpc)
        FLOC[*cc.arg2, RtpVintyr[r, v, t, p], c, cur].where[
            ObjVflo[r, p, c, cur, "COST"] & Trackpc[r, p, c]
        ] = Sum(
            RtpcsVarf[r, t, p, c, s],
            Sum(
                TsAnn[s, ts],
                pulse(
                    macro.obj_fcost_GP(r, y, p, c, ts, cur)
                    + macro.obj_fdelv_GP(r, y, p, c, ts, cur)
                ),
            )
            * par_flo[r, v, t, p, c, s],
        )

        FLOC[*cc.arg2, RtpVintyr[r, v, t, p], c, cur].where[
            ObjVflo[r, p, c, cur, "COST"] & RpcStg[r, p, c]
        ] = Sum(
            RpcsVar[r, p, c, s],
            Sum(
                TsAnn[s, ts],
                pulse(
                    VAR_SIN.l[r, v, t, p, c, s]
                    * macro.obj_fcost_GP(r, y, p, c, ts, cur)
                    + VAR_SOUT.l[r, v, t, p, c, s]
                    * stg_eff[r, v, p]
                    * macro.obj_fdelv_GP(r, y, p, c, ts, cur)
                ),
            ),
        )

        FLOC[*cc.arg2, RtpVintyr[r, v, t, p], c, cur].where[
            ObjVflo[r, p, c, cur, "COST"] & RpIre[r, p]
        ] = FLOC[j, r, v, t, p, c, cur] + Sum(
            RtpcsVarf[r, t, p, c, s],
            Sum(
                TsAnn[s, ts],
                pulse(
                    macro.obj_fcost_GP(r, y, p, c, ts, cur)
                    + macro.obj_fdelv_GP(r, y, p, c, ts, cur)
                ),
            )
            * (
                Sum(RpcIre[r, p, c, ie], par_ire[r, v, t, p, c, s, ie])
                + Sum(
                    io.where[f_inouts[r, v, t, p, c, s, io]],
                    f_inouts[r, v, t, p, c, s, io],
                )
            ),
        )

        # * handle the fact that commodity costs may be associated with capacity
        FLOC[*cc.arg2, r, v, t, p, c, cur].where[
            Vnt[v, t] & ObjVflo[r, p, c, cur, "COST"] & RpcCapflo[r, v, p, c]
        ] = FLOC[j, r, v, t, p, c, cur] + Sum(
            Annual[s],
            cal_caps_mod_GP(
                g,
                CalCapsModConfig(
                    is_vnret_defined=is_vnret_defined,
                    varv=varv,
                    sws=sws,
                    varm=varm,
                    arg1=t,
                    arg2=Sum(
                        TsAnn[ts, sl],
                        pulse(
                            macro.obj_fcost_GP(r, y, p, c, sl, cur)
                            + macro.obj_fdelv_GP(r, y, p, c, sl, cur)
                        ),
                    ),
                    arg3=ts,
                    is_output=True,
                ),
            ),
        )

        # *----------------------------------------------------------------------
        # * Flow level tax/sub
        # *----------------------------------------------------------------------
        FLOC[*cc.arg3, RtpVintyr[r, v, t, p], c, cur].where[
            ObjVflo[r, p, c, cur, "TAX"] & Trackpc[r, p, c]
        ] = Sum(
            RtpcsVarf[r, t, p, c, s],
            Sum(TsAnn[s, ts], pulse(macro.obj_ftax_GP(r, y, p, c, ts, cur)))
            * par_flo[r, v, t, p, c, s],
        )

        FLOC[*cc.arg3, RtpVintyr[r, v, t, p], c, cur].where[
            ObjVflo[r, p, c, cur, "TAX"] & RpIre[r, p]
        ] = Sum(
            RtpcsVarf[r, t, p, c, s],
            Sum(TsAnn[s, ts], pulse(macro.obj_ftax_GP(r, y, p, c, ts, cur)))
            * (
                Sum(RpcIre[r, p, c, ie], par_ire[r, v, t, p, c, s, ie])
                + Sum(
                    io.where[f_inouts[r, v, t, p, c, s, io]],
                    f_inouts[r, v, t, p, c, s, io],
                )
            ),
        )

        # * handle the fact that commodity costs may be associated with capacity
        FLOC[*cc.arg3, r, v, t, p, c, cur].where[
            Vnt[v, t] & ObjVflo[r, p, c, cur, "TAX"] & RpcCapflo[r, v, p, c]
        ] = FLOC[j, r, v, t, p, c, cur] + Sum(
            Annual[s],
            cal_caps_mod_GP(
                g,
                CalCapsModConfig(
                    is_vnret_defined=is_vnret_defined,
                    varv=varv,
                    sws=sws,
                    varm=varm,
                    arg1=t,
                    arg2=Sum(
                        TsAnn[ts, sl],
                        pulse(macro.obj_ftax_GP(r, y, p, c, sl, cur)),
                    ),
                    arg3=ts,
                    is_output=True,
                ),
            ),
        )
        Trackpc.setRecords(None)

        # *----------------------------------------------------------------------
        # * Commodity blending costs
        # *----------------------------------------------------------------------
        COMC[*cc.arg2, r, t, Ble, cur].where[Rdcur[r, cur]] = COMC[
            j, r, t, Ble, cur
        ] + Sum(
            BleOpr[r, Ble, Opr],
            pulse(obj_blndv[r, y, Ble, Opr, cur]) * VAR_BLND.l[r, t, Ble, Opr],
        )

    def _legacy(
        self: EqobjvarRpt,
        is_vnret_defined: bool,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varm: tuple[str, ImplicitSet | None],
    ) -> None:
        # *=====================================================================
        # * Legacy reporting (by every year and timeslice, discounted):
        # * Generate Variable cost formulas summing over all active indexes by
        # * region and currency
        # *=====================================================================
        g = self.tc

        r, v, t, p, c, s, sl, ts, cur, io, ie = (
            g.r,
            g.v,
            g.t,
            g.p,
            g.c,
            g.s,
            g.sl,
            g.ts,
            g.cur,
            g.io,
            g.ie,
        )
        Ble, BleOpr, Opr, Periodyr, PrcTs, Rdcur, RpcCapflo = (
            g.Ble,
            g.BleOpr,
            g.Opr,
            g.Periodyr,
            g.PrcTs,
            g.Rdcur,
            g.RpcCapflo,
        )
        RhsCombal, RhsComprd, RpcIre, RpcIreio, RpcsVar, RpFlo, RpIre = (
            g.RhsCombal,
            g.RhsComprd,
            g.RpcIre,
            g.RpcIreio,
            g.RpcsVar,
            g.RpFlo,
            g.RpIre,
        )
        RpStg, RtpcsVarf, RtpVintyr, TsAnn, Vnt, YEoh = (
            g.RpStg,
            g.RtpcsVarf,
            g.RtpVintyr,
            g.TsAnn,
            g.Vnt,
            g.YEoh,
        )
        ObjVflo, UcCost, costype, obv, sum_obj = (
            g.ObjVflo,
            g.UcCost,
            g.costype,
            g.obv,
            g.sum_obj,
        )
        f_inouts, obj_blndv, obj_comnt, obj_compd, obj_disc = (
            g.f_inouts,
            g.obj_blndv,
            g.obj_comnt,
            g.obj_compd,
            g.obj_disc,
        )
        obj_ipric, par_flo, par_ire, rs_stgav = (
            g.obj_ipric,
            g.par_flo,
            g.par_ire,
            g.rs_stgav,
        )
        par_objact, par_objble, par_objcom, par_objflo = (
            g.par_objact,
            g.par_objble,
            g.par_objcom,
            g.par_objflo,
        )
        obj_c, obj_d = g.obj_c, g.obj_d
        VAR_ACT, VAR_BLND, VAR_COMNET, VAR_COMPRD, VAR_OBJ = (
            g.VAR_ACT,
            g.VAR_BLND,
            g.VAR_COMNET,
            g.VAR_COMPRD,
            g.VAR_OBJ,
        )

        # *----------------------------------------------------------------------
        # * Overall activity of a process based costs
        # *----------------------------------------------------------------------
        with Loop(t):
            par_objact[r, v, YEoh, p, s, cur].where[
                Periodyr[t, YEoh] * RtpVintyr[r, v, t, p] * PrcTs[r, p, s]
            ] = (
                obj_disc[r, YEoh, cur]
                * macro.obj_acost_GP(r, YEoh, p, cur)
                * VAR_ACT.l[r, v, t, p, s]
                * power(rs_stgav[r, s], Number(1).where[RpStg[r, p]])
            )

        # *----------------------------------------------------------------------
        # * Commodity added costs and sub/tax
        # *----------------------------------------------------------------------
        with Loop(t):
            par_objcom[r, YEoh, c, s, cur].where[Periodyr[t, YEoh]] = sparse(
                Sum(
                    RhsCombal[r, t, c, s],
                    obj_disc[r, YEoh, cur]
                    * VAR_COMNET.l[r, t, c, s]
                    * Sum(costype, obj_comnt[r, YEoh, c, s, costype, cur]),
                )
                + Sum(
                    RhsComprd[r, t, c, s],
                    obj_disc[r, YEoh, cur]
                    * VAR_COMPRD.l[r, t, c, s]
                    * Sum(costype, obj_compd[r, YEoh, c, s, costype, cur]),
                )
            )

        # *----------------------------------------------------------------------
        # * Commodity costs/tax/sub associated with imports/exports from outside
        # * study area (external regions)
        # *----------------------------------------------------------------------
        with Loop(t):
            par_objflo[r, v, YEoh, p, c, s, cur].where[
                Periodyr[t, YEoh] * RtpcsVarf[r, t, p, c, s] * RtpVintyr[r, v, t, p]
                & RpIre[r, p]
            ] = sparse(
                Sum(
                    RpcIreio[r, p, c, ie, "OUT"],
                    obj_disc[r, YEoh, cur]
                    * obj_ipric[r, YEoh, p, c, s, ie, cur]
                    * par_ire[r, v, t, p, c, s, ie],
                )
            )

        # *----------------------------------------------------------------------
        # * Flow level costs/tax/sub
        # *----------------------------------------------------------------------
        with Loop(t):
            par_objflo[r, v, YEoh, p, c, s, cur].where[
                Periodyr[t, YEoh]
                * RtpcsVarf[r, t, p, c, s]
                * RtpVintyr[r, v, t, p]
                * RpFlo[r, p]
            ] = (
                obj_disc[r, YEoh, cur]
                * par_flo[r, v, t, p, c, s]
                * Sum(
                    TsAnn[s, ts],
                    macro.obj_fcost_GP(r, YEoh, p, c, ts, cur)
                    + macro.obj_fdelv_GP(r, YEoh, p, c, ts, cur)
                    + macro.obj_ftax_GP(r, YEoh, p, c, ts, cur),
                )
            )

        with Loop(t):
            par_objflo[r, v, YEoh, p, c, s, cur].where[
                Sum(ObjVflo[r, p, c, cur, UcCost], 1)
                & Periodyr[t, YEoh] * RtpcsVarf[r, t, p, c, s] * RtpVintyr[r, v, t, p]
                & RpIre[r, p]
            ] = par_objflo[r, v, YEoh, p, c, s, cur] + obj_disc[r, YEoh, cur] * Sum(
                TsAnn[s, ts],
                macro.obj_fcost_GP(r, YEoh, p, c, ts, cur)
                + macro.obj_fdelv_GP(r, YEoh, p, c, ts, cur)
                + macro.obj_ftax_GP(r, YEoh, p, c, ts, cur),
            ) * (
                Sum(RpcIre[r, p, c, ie], par_ire[r, v, t, p, c, s, ie])
                + Sum(
                    io.where[f_inouts[r, v, t, p, c, s, io]],
                    f_inouts[r, v, t, p, c, s, io],
                )
            )

        # * handle the fact that commodity costs may be associated with capacity
        with Loop(t):
            par_objflo[r, v, YEoh, p, c, s, cur].where[
                Periodyr[t, YEoh]
                * RpcsVar[r, p, c, s]
                * Vnt[v, t]
                * RpcCapflo[r, v, p, c]
            ] = par_objflo[r, v, YEoh, p, c, s, cur] + obj_disc[
                r, YEoh, cur
            ] * cal_caps_mod_GP(
                g,
                CalCapsModConfig(
                    is_vnret_defined=is_vnret_defined,
                    varv=varv,
                    sws=sws,
                    varm=varm,
                    arg1=t,
                    arg2=Sum(
                        TsAnn[ts, sl],
                        macro.obj_fcost_GP(r, YEoh, p, c, sl, cur)
                        + macro.obj_fdelv_GP(r, YEoh, p, c, sl, cur)
                        + macro.obj_ftax_GP(r, YEoh, p, c, sl, cur),
                    ),
                    arg3=ts,
                    is_output=True,
                ),
            )

        # *----------------------------------------------------------------------
        # * Commodity blending costs
        # *----------------------------------------------------------------------
        par_objble[r, YEoh, Ble, cur].where[Rdcur[r, cur]] = obj_disc[
            r, YEoh, cur
        ] * Sum(
            Domain(BleOpr[r, Ble, Opr], Periodyr[t, YEoh]),
            obj_blndv[r, YEoh, Ble, Opr, cur] * VAR_BLND.l[r, t, Ble, Opr],
        )

        # * Check that the Calculated objective components are equal to those
        # * Derived by the solver:
        obj_c[...] = (
            Sum(
                Domain(r, v, YEoh, p, s, cur).where[par_objact[r, v, YEoh, p, s, cur]],
                par_objact[r, v, YEoh, p, s, cur],
            )
            + Sum(
                Domain(r, v, YEoh, p, c, s, cur).where[
                    par_objflo[r, v, YEoh, p, c, s, cur]
                ],
                par_objflo[r, v, YEoh, p, c, s, cur],
            )
            + Sum(
                Domain(r, YEoh, c, s, cur).where[par_objcom[r, YEoh, c, s, cur]],
                par_objcom[r, YEoh, c, s, cur],
            )
        )
        obj_d[...] = Sum(
            Rdcur[r, cur],
            Sum(obv, sum_obj["OBJVAR", obv] * VAR_OBJ.l[r, obv, cur]),
        )
        print(obj_c.records)
        print(obj_d.records)


def eqobjvar_rpt(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    pgprim: str,
    tpulse: str,
    tmp: str,
    stages: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
) -> str:
    return_str = ""
    if arg1.upper() != "MOD":
        if arg5.upper() == "":
            tpulse = ""
            tmp = ""
        return_str = eqobjvar_rpt_current(
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            arg4=arg4,
            arg5=arg5,
            pgprim=pgprim,
            tpulse=tpulse,
            tmp=tmp,
            stages=stages,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )
    else:
        return_str = eqobjvar_rpt_legacy(
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )

    return return_str


def eqobjvar_rpt_current(
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    pgprim: str,
    tpulse: str,
    tmp: str,
    stages: str,
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
) -> str:
    include_cal_caps_1 = cal_caps_mod(
        is_vnret_defined=is_vnret_defined,
        arg1="T",
        arg2=f"SUM(TS_ANN(TS,SL),{arg5}({tpulse}({macro.obj_fcost('R', arg4, 'P', 'C', 'SL', 'CUR')}+{macro.obj_fdelv('R', arg4, 'P', 'C', 'SL', 'CUR')})))",
        arg3="TS",
        arg4=".L",
        varv=varv,
        sws=sws,
        varm=varm,
    )
    include_cal_caps_2 = cal_caps_mod(
        is_vnret_defined=is_vnret_defined,
        arg1="T",
        arg2=f"SUM(TS_ANN(TS,SL),{arg5}({tpulse} {macro.obj_ftax('R', arg4, 'P', 'C', 'SL', 'CUR')}))",
        arg3="TS",
        arg4=".L",
        varv=varv,
        sws=sws,
        varm=varm,
    )

    return rf"""
{"Z=SUM(W(SOW),SW_PROB(W));" if stages.upper() == "YES" else ""}
*------------------------------------------------------------------------------
  OPTION CLEAR={arg1}_ACTC,CLEAR={arg1}_COMC,CLEAR={arg1}_FLOC;
*------------------------------------------------------------------------------
* Costs based on overall activity of process
*------------------------------------------------------------------------------

  {arg1}_ACTC({arg2}RTP_VINTYR(R,V,T,P),'{pgprim}',CUR)$(RDCUR(R,CUR)${macro.obj_acost("R", "T", "P", "CUR")}) =
      {arg5}({tpulse} {macro.obj_acost("R", arg4, "P", "CUR")}) *
      SUM(PRC_TS(R,P,S), VAR_ACT.L(R,V,T,P,S) * POWER(RS_STGAV(R,S),1$RP_STG(R,P)));
  {arg1}_ACTC({arg3}RTP_VINTYR(R,V,T,P),C('{pgprim}'),CUR)$RPC_CUR(R,P,C,CUR) =
      SUM(RP_UPS(R,P,TSL,L('UP')),{arg5}({tpulse} ACT_CSTUP(R,V,P,TSL,CUR))*SUM(TS_GROUP(R,TSL,S),RS_STGPRD(R,S)*VAR_UPS.L(R,V,T,P,S,L))) +
      SUM(RP_UPT(R,P,UPT,'UP'),{arg5}({tpulse} ACT_CSTSD(R,V,P,UPT,'FX',CUR)*SUM(TS_GROUP(R,TSL,S)$RP_DPL(R,P,TSL),RS_STGPRD(R,S)*VAR_UPT.L(R,V,T,P,S,UPT)))) +
      SUM(RP_UPR(R,P,BDNEQ(BD)),{arg5}({tpulse} ACT_CSTRMP(R,V,P,BD,CUR))*SUM(PRC_TS(R,P,S),RS_STGPRD(R,S)*VAR_UDP.L(R,V,T,P,S,BD)));

*------------------------------------------------------------------------------
* Commodity added costs and sub/tax
*------------------------------------------------------------------------------
  {arg1}_COMC({arg2}R,T,C,CUR)$RDCUR(R,CUR) $=
        SUM(RHS_COMBAL(R,T,C,S), VAR_COMNET.L(R,T,C,S) * {arg5}({tpulse} OBJ_COMNT(R,{arg4},C,S,'COST',CUR))) +
        SUM(RHS_COMPRD(R,T,C,S), VAR_COMPRD.L(R,T,C,S) * {arg5}({tpulse} OBJ_COMPD(R,{arg4},C,S,'COST',CUR)));
  {arg1}_COMC({arg3}R,T,C,CUR)$RDCUR(R,CUR) $=
        SUM(RHS_COMBAL(R,T,C,S), VAR_COMNET.L(R,T,C,S) * {arg5}({tpulse} (OBJ_COMNT(R,{arg4},C,S,'TAX',CUR)+OBJ_COMNT(R,{arg4},C,S,'SUB',CUR)))) +
        SUM(RHS_COMPRD(R,T,C,S), VAR_COMPRD.L(R,T,C,S) * {arg5}({tpulse} (OBJ_COMPD(R,{arg4},C,S,'TAX',CUR)+OBJ_COMPD(R,{arg4},C,S,'SUB',CUR))));
{f"{arg1}_COMC({arg3}RTC(R,T,C),CUR)$RDCUR(R,CUR) $= SUM((RTCS_VARC(RTC,S),COM_VAR,SW_TSW(SOW,T,W))$S_COM_TAX(RTC,S,COM_VAR,CUR,'1',W),({arg5}({tmp}S_COM_TAX(R,{arg4},C,S,COM_VAR,CUR,'1',W))*(VAR_COMPRD.L(RTC,S)$DIAG('PRD',COM_VAR)+VAR_COMNET.L(RTC,S)$DIAG('NET',COM_VAR))+{arg1}_COMC(J,RTC,CUR)*G_YRFR(R,S))*SW_PROB(W)/Z);" if stages.upper() == "YES" else ""}

*------------------------------------------------------------------------------
* Commodity costs associated with imports/exports from outside study area
*------------------------------------------------------------------------------
  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(RDCUR(R,CUR)$RPC(R,P,C)$RP_IRE(R,P)) $=
        SUM((RTPCS_VARF(R,T,P,C,S),RPC_IREIO(R,P,C,IE,'OUT')), {arg5}({tpulse} OBJ_IPRIC(R,{arg4},P,C,S,IE,CUR)) * PAR_IRE(R,V,T,P,C,S,IE));

*------------------------------------------------------------------------------
* Flow level costs
*------------------------------------------------------------------------------
  OPTION TRACKPC < PAR_FLO;
  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$TRACKPC(R,P,C)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} ({macro.obj_fcost("R", arg4, "P", "C", "TS", "CUR")}+{macro.obj_fdelv("R", arg4, "P", "C", "TS", "CUR")}))) * PAR_FLO(R,V,T,P,C,S));

  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$RPC_STG(R,P,C)) =
     SUM(RPCS_VAR(R,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} (VAR_SIN.L(R,V,T,P,C,S)*{macro.obj_fcost("R", arg4, "P", "C", "TS", "CUR")}+VAR_SOUT.L(R,V,T,P,C,S)*STG_EFF(R,V,P)*{macro.obj_fdelv("R", arg4, "P", "C", "TS", "CUR")}))));

  {arg1}_FLOC({arg2}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'COST')$RP_IRE(R,P)) =
     {arg1}_FLOC(J,R,V,T,P,C,CUR) +
     SUM(RTPCS_VARF(R,T,P,C,S),
      SUM(TS_ANN(S,TS),{arg5}({tpulse} ({macro.obj_fcost("R", arg4, "P", "C", "TS", "CUR")} + {macro.obj_fdelv("R", arg4, "P", "C", "TS", "CUR")}))) *
      (
         SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
         SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
      ));

* handle the fact that commodity costs may be associated with capacity
  {arg1}_FLOC({arg2}R,V,T,P,C,CUR)$(VNT(V,T)$OBJ_VFLO(R,P,C,CUR,'COST')$RPC_CAPFLO(R,V,P,C)) =
      {arg1}_FLOC(J,R,V,T,P,C,CUR) +
      SUM(ANNUAL(S),
{include_cal_caps_1}
        );

*------------------------------------------------------------------------------
* Flow level tax/sub
*------------------------------------------------------------------------------

  {arg1}_FLOC({arg3}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'TAX')$TRACKPC(R,P,C)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
         SUM(TS_ANN(S,TS),{arg5}({tpulse} {macro.obj_ftax("R", arg4, "P", "C", "TS", "CUR")})) * PAR_FLO(R,V,T,P,C,S));

  {arg1}_FLOC({arg3}RTP_VINTYR(R,V,T,P),C,CUR)$(OBJ_VFLO(R,P,C,CUR,'TAX')$RP_IRE(R,P)) =
     SUM(RTPCS_VARF(R,T,P,C,S),
      SUM(TS_ANN(S,TS),{arg5}({tpulse} {macro.obj_ftax("R", arg4, "P", "C", "TS", "CUR")})) *
      (
         SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
         SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
      ));

* handle the fact that commodity costs may be associated with capacity
  {arg1}_FLOC({arg3}R,V,T,P,C,CUR)$(VNT(V,T)$OBJ_VFLO(R,P,C,CUR,'TAX')$RPC_CAPFLO(R,V,P,C)) =
      {arg1}_FLOC(J,R,V,T,P,C,CUR) +
      SUM(ANNUAL(S),
{include_cal_caps_2}
        );
  OPTION CLEAR=TRACKPC;

*------------------------------------------------------------------------------
* Commodity blending costs
*------------------------------------------------------------------------------
  {arg1}_COMC({arg2}R,T,BLE,CUR)$RDCUR(R,CUR) = {arg1}_COMC(J,R,T,BLE,CUR) +
     SUM(BLE_OPR(R,BLE,OPR), {arg5}({tpulse} OBJ_BLNDV(R,{arg4},BLE,OPR,CUR)) * VAR_BLND.L(R,T,BLE,OPR));

*------------------------------------------------------------------------------
"""


def eqobjvar_rpt_legacy(
    is_vnret_defined: bool,
    varv: str,
    sws: str,
    varm: str,
) -> str:
    include_cal_caps = cal_caps_mod(
        is_vnret_defined=is_vnret_defined,
        arg1="T",
        arg2=f"SUM(TS_ANN(TS,SL),{macro.obj_fcost('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')}+{macro.obj_fdelv('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')}+{macro.obj_ftax('R', 'Y_EOH', 'P', 'C', 'SL', 'CUR')})",
        arg3="TS",
        arg4=".L",
        varv=varv,
        sws=sws,
        varm=varm,
    )
    return rf"""
*==============================================================================
* Legacy reporting (by every year and timeslice, discounted):
* Generate Variable cost formulas summing over all active indexes by region and currency
*===============================================================================

*------------------------------------------------------------------------------
* Overall activity of a process based costs
*------------------------------------------------------------------------------
 LOOP(T,
        PAR_OBJACT(R,V,Y_EOH,P,S,CUR)$(PERIODYR(T,Y_EOH)*RTP_VINTYR(R,V,T,P)*PRC_TS(R,P,S)) =
          OBJ_DISC(R,Y_EOH,CUR) * {macro.obj_acost("R", "Y_EOH", "P", "CUR")} * VAR_ACT.L(R,V,T,P,S) * POWER(RS_STGAV(R,S),1$RP_STG(R,P))
     );

*------------------------------------------------------------------------------
* Commodity added costs and sub/tax
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJCOM(R,Y_EOH,C,S,CUR)$PERIODYR(T,Y_EOH) $=
         SUM(RHS_COMBAL(R,T,C,S), OBJ_DISC(R,Y_EOH,CUR) * VAR_COMNET.L(R,T,C,S) * SUM(COSTYPE,OBJ_COMNT(R,Y_EOH,C,S,COSTYPE,CUR))) +
         SUM(RHS_COMPRD(R,T,C,S), OBJ_DISC(R,Y_EOH,CUR) * VAR_COMPRD.L(R,T,C,S) * SUM(COSTYPE,OBJ_COMPD(R,Y_EOH,C,S,COSTYPE,CUR)));
     );

*------------------------------------------------------------------------------
* Commodity costs/tax/sub associated with imports/exports from outside study area (external regions)
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$((PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P))$RP_IRE(R,P)) $=
         SUM(RPC_IREIO(R,P,C,IE,'OUT'), OBJ_DISC(R,Y_EOH,CUR) * OBJ_IPRIC(R,Y_EOH,P,C,S,IE,CUR) * PAR_IRE(R,V,T,P,C,S,IE));
     );

*------------------------------------------------------------------------------
* Flow level costs/tax/sub
*------------------------------------------------------------------------------
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P)*RP_FLO(R,P)) =

         OBJ_DISC(R,Y_EOH,CUR) * PAR_FLO(R,V,T,P,C,S) *
         SUM(TS_ANN(S,TS),{macro.obj_fcost("R", "Y_EOH", "P", "C", "TS", "CUR")} + {macro.obj_fdelv("R", "Y_EOH", "P", "C", "TS", "CUR")} + {macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")})
     );

 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(SUM(OBJ_VFLO(R,P,C,CUR,UC_COST),1)$(PERIODYR(T,Y_EOH)*RTPCS_VARF(R,T,P,C,S)*RTP_VINTYR(R,V,T,P)$RP_IRE(R,P))) =

         PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR) +
         OBJ_DISC(R,Y_EOH,CUR) *
         SUM(TS_ANN(S,TS),{macro.obj_fcost("R", "Y_EOH", "P", "C", "TS", "CUR")} + {macro.obj_fdelv("R", "Y_EOH", "P", "C", "TS", "CUR")} + {macro.obj_ftax("R", "Y_EOH", "P", "C", "TS", "CUR")}) *
         (
           SUM(RPC_IRE(R,P,C,IE), PAR_IRE(R,V,T,P,C,S,IE)) +
           SUM(IO$F_INOUTS(R,V,T,P,C,S,IO),F_INOUTS(R,V,T,P,C,S,IO))
         )
     );

* handle the fact that commodity costs may be associated with capacity
 LOOP(T,
       PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR)$(PERIODYR(T,Y_EOH)*RPCS_VAR(R,P,C,S)*VNT(V,T)*RPC_CAPFLO(R,V,P,C)) =
         PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR) +
         OBJ_DISC(R,Y_EOH,CUR) *
         (
{include_cal_caps}
         )
     );

*------------------------------------------------------------------------------
* Commodity blending costs
*------------------------------------------------------------------------------
   PAR_OBJBLE(R,Y_EOH,BLE,CUR)$RDCUR(R,CUR) = OBJ_DISC(R,Y_EOH,CUR) *
        SUM((BLE_OPR(R,BLE,OPR),PERIODYR(T,Y_EOH)), OBJ_BLNDV(R,Y_EOH,BLE,OPR,CUR) * VAR_BLND.L(R,T,BLE,OPR));

* Check that the Calculated objective components are equal to those Derived by the solver:
OBJ_C = SUM((R,V,Y_EOH,P,S,CUR)$PAR_OBJACT(R,V,Y_EOH,P,S,CUR),PAR_OBJACT(R,V,Y_EOH,P,S,CUR))+
   SUM((R,V,Y_EOH,P,C,S,CUR)$PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR),PAR_OBJFLO(R,V,Y_EOH,P,C,S,CUR))+
   SUM((R,Y_EOH,C,S,CUR)$PAR_OBJCOM(R,Y_EOH,C,S,CUR),PAR_OBJCOM(R,Y_EOH,C,S,CUR));
OBJ_D = SUM(RDCUR(R,CUR),SUM(OBV,SUM_OBJ('OBJVAR',OBV)*VAR_OBJ.L(R,OBV,CUR)));
DISPLAY OBJ_C,OBJ_D;
"""
