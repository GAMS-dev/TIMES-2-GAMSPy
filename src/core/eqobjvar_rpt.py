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
from core.utils import wrap_in_sum
from utils.macros import macro_config as macro

if TYPE_CHECKING:
    from gamspy import Expression
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SET_OR_ALIAS, TpulseType
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


@dataclass
class EqobjvarRptConfig:
    """Strongly typed data contract for eqobjvar.rpt."""

    # %1 - 'mod' selects the legacy reporting, anything else is a parameter prefix
    arg1: str = "mod"
    # %2 - leading J(...) index of the cost slice, e.g. (g.j["1"],) or (g.j[g.uncd1],)
    arg2: tuple[SET_OR_ALIAS, ...] | tuple[()] = ()
    # %3 - leading J(...) index of the tax/sub slice, e.g. (g.j["2"],)
    arg3: tuple[SET_OR_ALIAS, ...] | tuple[()] = ()
    # %4 - year index, e.g. (g.t,) or (g.YEoh,)
    arg4: tuple[SET_OR_ALIAS, ...] = ()
    # %5 - True where the legacy '%5' was SUM
    arg5: bool = False


class EqobjvarRpt(GamsClass):
    """Translation unit for eqobjvar.rpt."""

    # Instance attributes
    module_name: str = "eqobjvar_rpt"
    gams_source: str = "eqobjvar.rpt"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        config: EqobjvarRptConfig,
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
            tpulse=self.env.tpulse_GP,
            tmp=self.env.tmp_GP,
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
        tpulse: TpulseType,
        tmp: Expression | Number | int | TpulseType,
        stages: str,
        is_vnret_defined: bool,
        varv: tuple[str, ImplicitSet | None],
        sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
        varm: tuple[str, ImplicitSet | None],
    ) -> None:
        eqobjvar_rpt_GP(
            g=self.tc,
            config=config,
            pgprim=pgprim,
            tpulse=tpulse,
            tmp=tmp,
            stages=stages,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )


def eqobjvar_rpt_GP(
    g: TimesModelClass,
    config: EqobjvarRptConfig,
    pgprim: str,
    tpulse: TpulseType | tuple[()],
    tmp: Expression | Number | int | TpulseType | tuple[()],
    stages: str,
    is_vnret_defined: bool,
    varv: tuple[str, ImplicitSet | None],
    sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
    varm: tuple[str, ImplicitSet | None],
) -> None:
    # $IFI '%1'==MOD $GOTO LEGACY
    if config.arg1.upper() != "MOD":
        # $IFI '%5'=='' $SET TPULSE '' SET TMP ''
        if not config.arg5:
            tpulse = ()
            tmp = ()
        eqobjvar_rpt_current_GP(
            g=g,
            config=config,
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
        eqobjvar_rpt_legacy_GP(
            g=g,
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
        )


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


def eqobjvar_rpt_current_GP(
    g: TimesModelClass,
    config: EqobjvarRptConfig,
    pgprim: str,
    tpulse: TpulseType | tuple[()],
    tmp: Expression | Number | int | TpulseType | tuple[()],
    stages: str,
    is_vnret_defined: bool,
    varv: tuple[str, ImplicitSet | None],
    sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
    varm: tuple[str, ImplicitSet | None],
) -> None:
    cc = config
    # %4 is a single year index here; an empty %4 only occurs on the legacy (mod) path
    (arg4,) = cc.arg4
    actc = g.get_parameter(f"{cc.arg1}_ACTC")
    comc = g.get_parameter(f"{cc.arg1}_COMC")
    floc = g.get_parameter(f"{cc.arg1}_FLOC")

    if stages.upper() == "YES":
        g.z[...] = Sum(g.w[g.Sow], g.sw_prob[g.w])

    # *------------------------------------------------------------------------------
    actc.setRecords(None)
    comc.setRecords(None)
    floc.setRecords(None)

    # *------------------------------------------------------------------------------
    # * Costs based on overall activity of process
    # *------------------------------------------------------------------------------
    actc[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], pgprim, g.cur].where[
        g.Rdcur[g.r, g.cur].where[macro.obj_acost_GP(g.r, g.t, g.p, g.cur)]
    ] = wrap_in_sum(macro.obj_acost_GP(g.r, arg4, g.p, g.cur), tpulse) * Sum(
        g.PrcTs[g.r, g.p, g.s],
        g.VAR_ACT.l[g.r, g.v, g.t, g.p, g.s]
        * power(g.rs_stgav[g.r, g.s], Number(1).where[g.RpStg[g.r, g.p]]),
    )
    actc[*cc.arg3, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c[pgprim], g.cur].where[
        g.RpcCur[g.r, g.p, g.c, g.cur]
    ] = (
        Sum(
            g.RpUps[g.r, g.p, g.tsl, g.lA["UP"]],
            wrap_in_sum(g.act_cstup[g.r, g.v, g.p, g.tsl, g.cur], tpulse)
            * Sum(
                g.TsGroup[g.r, g.tsl, g.s],
                g.rs_stgprd[g.r, g.s] * g.VAR_UPS.l[g.r, g.v, g.t, g.p, g.s, g.lA],
            ),
        )
        + Sum(
            g.RpUpt[g.r, g.p, g.upt, "UP"],
            wrap_in_sum(
                g.act_cstsd[g.r, g.v, g.p, g.upt, "FX", g.cur]
                * Sum(
                    g.TsGroup[g.r, g.tsl, g.s].where[g.RpDpl[g.r, g.p, g.tsl]],
                    g.rs_stgprd[g.r, g.s] * g.VAR_UPT.l[g.r, g.v, g.t, g.p, g.s, g.upt],
                ),
                tpulse,
            ),
        )
        + Sum(
            g.RpUpr[g.r, g.p, g.Bdneq[g.bd]],
            wrap_in_sum(g.act_cstrmp[g.r, g.v, g.p, g.bd, g.cur], tpulse)
            * Sum(
                g.PrcTs[g.r, g.p, g.s],
                g.rs_stgprd[g.r, g.s] * g.VAR_UDP.l[g.r, g.v, g.t, g.p, g.s, g.bd],
            ),
        )
    )

    # *------------------------------------------------------------------------------
    # * Commodity added costs and sub/tax
    # *------------------------------------------------------------------------------
    comc[*cc.arg2, g.r, g.t, g.c, g.cur].where[g.Rdcur[g.r, g.cur]] = sparse(
        Sum(
            g.RhsCombal[g.r, g.t, g.c, g.s],
            g.VAR_COMNET.l[g.r, g.t, g.c, g.s]
            * wrap_in_sum(g.obj_comnt[g.r, arg4, g.c, g.s, "COST", g.cur], tpulse),
        )
        + Sum(
            g.RhsComprd[g.r, g.t, g.c, g.s],
            g.VAR_COMPRD.l[g.r, g.t, g.c, g.s]
            * wrap_in_sum(g.obj_compd[g.r, arg4, g.c, g.s, "COST", g.cur], tpulse),
        )
    )
    comc[*cc.arg3, g.r, g.t, g.c, g.cur].where[g.Rdcur[g.r, g.cur]] = sparse(
        Sum(
            g.RhsCombal[g.r, g.t, g.c, g.s],
            g.VAR_COMNET.l[g.r, g.t, g.c, g.s]
            * wrap_in_sum(
                g.obj_comnt[g.r, arg4, g.c, g.s, "TAX", g.cur]
                + g.obj_comnt[g.r, arg4, g.c, g.s, "SUB", g.cur],
                tpulse,
            ),
        )
        + Sum(
            g.RhsComprd[g.r, g.t, g.c, g.s],
            g.VAR_COMPRD.l[g.r, g.t, g.c, g.s]
            * wrap_in_sum(
                g.obj_compd[g.r, arg4, g.c, g.s, "TAX", g.cur]
                + g.obj_compd[g.r, arg4, g.c, g.s, "SUB", g.cur],
                tpulse,
            ),
        )
    )
    if stages.upper() == "YES":
        comc[*cc.arg3, g.Rtc[g.r, g.t, g.c], g.cur].where[g.Rdcur[g.r, g.cur]] = sparse(
            Sum(
                Domain(
                    g.RtcsVarc[g.Rtc, g.s], g.comvar, g.SwTsw[g.Sow, g.t, g.w]
                ).where[g.s_com_tax[g.Rtc, g.s, g.comvar, g.cur, "1", g.w]],
                (
                    wrap_in_sum(
                        g.s_com_tax[g.r, arg4, g.c, g.s, g.comvar, g.cur, "1", g.w],
                        # %TMP% is a pulse pair whenever %5 is SUM (rpt_obj.rpt);
                        # env.tmp_GP's multiplier forms never reach this line
                        tmp,  # type: ignore[arg-type]
                    )
                    * (
                        g.VAR_COMPRD.l[g.Rtc, g.s].where[diag("PRD", g.comvar)]
                        + g.VAR_COMNET.l[g.Rtc, g.s].where[diag("NET", g.comvar)]
                    )
                    + comc[g.j, g.Rtc, g.cur] * g.g_yrfr[g.r, g.s]
                )
                * g.sw_prob[g.w]
                / g.z,
            )
        )

    # *------------------------------------------------------------------------------
    # * Commodity costs associated with imports/exports from outside study area
    # *------------------------------------------------------------------------------
    floc[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.Rdcur[g.r, g.cur].where[g.Rpc[g.r, g.p, g.c].where[g.RpIre[g.r, g.p]]]
    ] = sparse(
        Sum(
            [
                g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
                g.RpcIreio[g.r, g.p, g.c, g.ie, "OUT"],
            ],
            wrap_in_sum(g.obj_ipric[g.r, arg4, g.p, g.c, g.s, g.ie, g.cur], tpulse)
            * g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
        )
    )

    # *------------------------------------------------------------------------------
    # * Flow level costs
    # *------------------------------------------------------------------------------
    project(source=g.par_flo, target=g.Trackpc)
    floc[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.ObjVflo[g.r, g.p, g.c, g.cur, "COST"].where[g.Trackpc[g.r, g.p, g.c]]
    ] = Sum(
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
        Sum(
            g.TsAnn[g.s, g.ts],
            wrap_in_sum(
                macro.obj_fcost_GP(g.r, arg4, g.p, g.c, g.ts, g.cur)
                + macro.obj_fdelv_GP(g.r, arg4, g.p, g.c, g.ts, g.cur),
                tpulse,
            ),
        )
        * g.par_flo[g.r, g.v, g.t, g.p, g.c, g.s],
    )

    floc[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.ObjVflo[g.r, g.p, g.c, g.cur, "COST"].where[g.RpcStg[g.r, g.p, g.c]]
    ] = Sum(
        g.RpcsVar[g.r, g.p, g.c, g.s],
        Sum(
            g.TsAnn[g.s, g.ts],
            wrap_in_sum(
                g.VAR_SIN.l[g.r, g.v, g.t, g.p, g.c, g.s]
                * macro.obj_fcost_GP(g.r, arg4, g.p, g.c, g.ts, g.cur)
                + g.VAR_SOUT.l[g.r, g.v, g.t, g.p, g.c, g.s]
                * g.stg_eff[g.r, g.v, g.p]
                * macro.obj_fdelv_GP(g.r, arg4, g.p, g.c, g.ts, g.cur),
                tpulse,
            ),
        ),
    )

    floc[*cc.arg2, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.ObjVflo[g.r, g.p, g.c, g.cur, "COST"].where[g.RpIre[g.r, g.p]]
    ] = floc[g.j, g.r, g.v, g.t, g.p, g.c, g.cur] + Sum(
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
        Sum(
            g.TsAnn[g.s, g.ts],
            wrap_in_sum(
                macro.obj_fcost_GP(g.r, arg4, g.p, g.c, g.ts, g.cur)
                + macro.obj_fdelv_GP(g.r, arg4, g.p, g.c, g.ts, g.cur),
                tpulse,
            ),
        )
        * (
            Sum(
                g.RpcIre[g.r, g.p, g.c, g.ie],
                g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
            )
            + Sum(
                g.io.where[g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io]],
                g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io],
            )
        ),
    )

    # * handle the fact that commodity costs may be associated with capacity
    obj_fcost_fdelv = wrap_in_sum(
        macro.obj_fcost_GP(g.r, arg4, g.p, g.c, g.sl, g.cur)
        + macro.obj_fdelv_GP(g.r, arg4, g.p, g.c, g.sl, g.cur),
        tpulse,
    )
    # BATINCLUDE cal_caps.mod T 'SUM(TS_ANN(TS,SL),%5(%TPULSE%(OBJ_FCOST(R,%4,P,C,SL,CUR)+OBJ_FDELV(R,%4,P,C,SL,CUR))))' TS .L
    include_cal_caps_1 = cal_caps_mod_GP(
        g=g,
        config=CalCapsModConfig(
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            arg1=g.t,
            arg2=Sum(g.TsAnn[g.ts, g.sl], obj_fcost_fdelv),
            arg3=g.ts,
            is_output=True,
        ),
    )
    floc[*cc.arg2, g.r, g.v, g.t, g.p, g.c, g.cur].where[
        g.Vnt[g.v, g.t].where[
            g.ObjVflo[g.r, g.p, g.c, g.cur, "COST"].where[
                g.RpcCapflo[g.r, g.v, g.p, g.c]
            ]
        ]
    ] = floc[g.j, g.r, g.v, g.t, g.p, g.c, g.cur] + Sum(
        g.Annual[g.s], include_cal_caps_1
    )

    # *------------------------------------------------------------------------------
    # * Flow level tax/sub
    # *------------------------------------------------------------------------------
    floc[*cc.arg3, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.ObjVflo[g.r, g.p, g.c, g.cur, "TAX"].where[g.Trackpc[g.r, g.p, g.c]]
    ] = Sum(
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
        Sum(
            g.TsAnn[g.s, g.ts],
            wrap_in_sum(macro.obj_ftax_GP(g.r, arg4, g.p, g.c, g.ts, g.cur), tpulse),
        )
        * g.par_flo[g.r, g.v, g.t, g.p, g.c, g.s],
    )

    floc[*cc.arg3, g.RtpVintyr[g.r, g.v, g.t, g.p], g.c, g.cur].where[
        g.ObjVflo[g.r, g.p, g.c, g.cur, "TAX"].where[g.RpIre[g.r, g.p]]
    ] = Sum(
        g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s],
        Sum(
            g.TsAnn[g.s, g.ts],
            wrap_in_sum(macro.obj_ftax_GP(g.r, arg4, g.p, g.c, g.ts, g.cur), tpulse),
        )
        * (
            Sum(
                g.RpcIre[g.r, g.p, g.c, g.ie],
                g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
            )
            + Sum(
                g.io.where[g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io]],
                g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io],
            )
        ),
    )

    # * handle the fact that commodity costs may be associated with capacity
    obj_ftax = wrap_in_sum(macro.obj_ftax_GP(g.r, arg4, g.p, g.c, g.sl, g.cur), tpulse)
    # BATINCLUDE cal_caps.mod T 'SUM(TS_ANN(TS,SL),%5(%TPULSE%(OBJ_FTAX(R,%4,P,C,SL,CUR))))' TS .L
    include_cal_caps_2 = cal_caps_mod_GP(
        g=g,
        config=CalCapsModConfig(
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            arg1=g.t,
            arg2=Sum(g.TsAnn[g.ts, g.sl], obj_ftax),
            arg3=g.ts,
            is_output=True,
        ),
    )
    floc[*cc.arg3, g.r, g.v, g.t, g.p, g.c, g.cur].where[
        g.Vnt[g.v, g.t].where[
            g.ObjVflo[g.r, g.p, g.c, g.cur, "TAX"].where[
                g.RpcCapflo[g.r, g.v, g.p, g.c]
            ]
        ]
    ] = floc[g.j, g.r, g.v, g.t, g.p, g.c, g.cur] + Sum(
        g.Annual[g.s], include_cal_caps_2
    )
    g.Trackpc.setRecords(None)

    # *------------------------------------------------------------------------------
    # * Commodity blending costs
    # *------------------------------------------------------------------------------
    comc[*cc.arg2, g.r, g.t, g.Ble, g.cur].where[g.Rdcur[g.r, g.cur]] = comc[
        g.j, g.r, g.t, g.Ble, g.cur
    ] + Sum(
        g.BleOpr[g.r, g.Ble, g.Opr],
        wrap_in_sum(g.obj_blndv[g.r, arg4, g.Ble, g.Opr, g.cur], tpulse)
        * g.VAR_BLND.l[g.r, g.t, g.Ble, g.Opr],
    )

    # *------------------------------------------------------------------------------


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


def eqobjvar_rpt_legacy_GP(
    g: TimesModelClass,
    is_vnret_defined: bool,
    varv: tuple[str, ImplicitSet | None],
    sws: tuple[SET_OR_ALIAS, ...] | tuple[()],
    varm: tuple[str, ImplicitSet | None],
) -> None:
    include_cal_caps = cal_caps_mod_GP(
        g=g,
        config=CalCapsModConfig(
            is_vnret_defined=is_vnret_defined,
            varv=varv,
            sws=sws,
            varm=varm,
            arg1=g.t,
            arg2=Sum(
                g.TsAnn[g.ts, g.sl],
                macro.obj_fcost_GP(g.r, g.YEoh, g.p, g.c, g.sl, g.cur)
                + macro.obj_fdelv_GP(g.r, g.YEoh, g.p, g.c, g.sl, g.cur)
                + macro.obj_ftax_GP(g.r, g.YEoh, g.p, g.c, g.sl, g.cur),
            ),
            arg3=g.ts,
            is_output=True,
        ),
    )

    # *==============================================================================
    # * Legacy reporting (by every year and timeslice, discounted):
    # * Generate Variable cost formulas summing over all active indexes by region and currency
    # *===============================================================================

    # *------------------------------------------------------------------------------
    # * Overall activity of a process based costs
    # *------------------------------------------------------------------------------
    with Loop(g.t):
        g.par_objact[g.r, g.v, g.YEoh, g.p, g.s, g.cur].where[
            g.Periodyr[g.t, g.YEoh]
            * g.RtpVintyr[g.r, g.v, g.t, g.p]
            * g.PrcTs[g.r, g.p, g.s]
        ] = (
            g.obj_disc[g.r, g.YEoh, g.cur]
            * macro.obj_acost_GP(g.r, g.YEoh, g.p, g.cur)
            * g.VAR_ACT.l[g.r, g.v, g.t, g.p, g.s]
            * power(g.rs_stgav[g.r, g.s], Number(1).where[g.RpStg[g.r, g.p]])
        )

    # *------------------------------------------------------------------------------
    # * Commodity added costs and sub/tax
    # *------------------------------------------------------------------------------
    with Loop(g.t):
        g.par_objcom[g.r, g.YEoh, g.c, g.s, g.cur].where[g.Periodyr[g.t, g.YEoh]] = (
            sparse(
                Sum(
                    g.RhsCombal[g.r, g.t, g.c, g.s],
                    g.obj_disc[g.r, g.YEoh, g.cur]
                    * g.VAR_COMNET.l[g.r, g.t, g.c, g.s]
                    * Sum(
                        g.costype, g.obj_comnt[g.r, g.YEoh, g.c, g.s, g.costype, g.cur]
                    ),
                )
                + Sum(
                    g.RhsComprd[g.r, g.t, g.c, g.s],
                    g.obj_disc[g.r, g.YEoh, g.cur]
                    * g.VAR_COMPRD.l[g.r, g.t, g.c, g.s]
                    * Sum(
                        g.costype, g.obj_compd[g.r, g.YEoh, g.c, g.s, g.costype, g.cur]
                    ),
                )
            )
        )

    # *------------------------------------------------------------------------------
    # * Commodity costs/tax/sub associated with imports/exports from outside study area (external regions)
    # *------------------------------------------------------------------------------
    with Loop(g.t):
        g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur].where[
            (
                g.Periodyr[g.t, g.YEoh]
                * g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s]
                * g.RtpVintyr[g.r, g.v, g.t, g.p]
            ).where[g.RpIre[g.r, g.p]]
        ] = sparse(
            Sum(
                g.RpcIreio[g.r, g.p, g.c, g.ie, "OUT"],
                g.obj_disc[g.r, g.YEoh, g.cur]
                * g.obj_ipric[g.r, g.YEoh, g.p, g.c, g.s, g.ie, g.cur]
                * g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
            )
        )

    # *------------------------------------------------------------------------------
    # * Flow level costs/tax/sub
    # *------------------------------------------------------------------------------
    with Loop(g.t):
        g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur].where[
            g.Periodyr[g.t, g.YEoh]
            * g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s]
            * g.RtpVintyr[g.r, g.v, g.t, g.p]
            * g.RpFlo[g.r, g.p]
        ] = (
            g.obj_disc[g.r, g.YEoh, g.cur]
            * g.par_flo[g.r, g.v, g.t, g.p, g.c, g.s]
            * Sum(
                g.TsAnn[g.s, g.ts],
                macro.obj_fcost_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur)
                + macro.obj_fdelv_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur)
                + macro.obj_ftax_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur),
            )
        )

    with Loop(g.t):
        g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur].where[
            Sum(g.ObjVflo[g.r, g.p, g.c, g.cur, g.UcCost], 1).where[
                g.Periodyr[g.t, g.YEoh]
                * g.RtpcsVarf[g.r, g.t, g.p, g.c, g.s]
                * g.RtpVintyr[g.r, g.v, g.t, g.p].where[g.RpIre[g.r, g.p]]
            ]
        ] = g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur] + g.obj_disc[
            g.r, g.YEoh, g.cur
        ] * Sum(
            g.TsAnn[g.s, g.ts],
            macro.obj_fcost_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur)
            + macro.obj_fdelv_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur)
            + macro.obj_ftax_GP(g.r, g.YEoh, g.p, g.c, g.ts, g.cur),
        ) * (
            Sum(
                g.RpcIre[g.r, g.p, g.c, g.ie],
                g.par_ire[g.r, g.v, g.t, g.p, g.c, g.s, g.ie],
            )
            + Sum(
                g.io.where[g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io]],
                g.f_inouts[g.r, g.v, g.t, g.p, g.c, g.s, g.io],
            )
        )

    # * handle the fact that commodity costs may be associated with capacity
    with Loop(g.t):
        g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur].where[
            g.Periodyr[g.t, g.YEoh]
            * g.RpcsVar[g.r, g.p, g.c, g.s]
            * g.Vnt[g.v, g.t]
            * g.RpcCapflo[g.r, g.v, g.p, g.c]
        ] = (
            g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur]
            + g.obj_disc[g.r, g.YEoh, g.cur] * include_cal_caps
        )

    # *------------------------------------------------------------------------------
    # * Commodity blending costs
    # *------------------------------------------------------------------------------
    g.par_objble[g.r, g.YEoh, g.Ble, g.cur].where[g.Rdcur[g.r, g.cur]] = g.obj_disc[
        g.r, g.YEoh, g.cur
    ] * Sum(
        [g.BleOpr[g.r, g.Ble, g.Opr], g.Periodyr[g.t, g.YEoh]],
        g.obj_blndv[g.r, g.YEoh, g.Ble, g.Opr, g.cur]
        * g.VAR_BLND.l[g.r, g.t, g.Ble, g.Opr],
    )

    # * Check that the Calculated objective components are equal to those Derived by the solver:
    g.obj_c[...] = (
        Sum(
            Domain(g.r, g.v, g.YEoh, g.p, g.s, g.cur).where[
                g.par_objact[g.r, g.v, g.YEoh, g.p, g.s, g.cur]
            ],
            g.par_objact[g.r, g.v, g.YEoh, g.p, g.s, g.cur],
        )
        + Sum(
            Domain(g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur).where[
                g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur]
            ],
            g.par_objflo[g.r, g.v, g.YEoh, g.p, g.c, g.s, g.cur],
        )
        + Sum(
            Domain(g.r, g.YEoh, g.c, g.s, g.cur).where[
                g.par_objcom[g.r, g.YEoh, g.c, g.s, g.cur]
            ],
            g.par_objcom[g.r, g.YEoh, g.c, g.s, g.cur],
        )
    )
    g.obj_d[...] = Sum(
        g.Rdcur[g.r, g.cur],
        Sum(g.obv, g.sum_obj["OBJVAR", g.obv] * g.VAR_OBJ.l[g.r, g.obv, g.cur]),
    )
    print(g.obj_c.records)
    print(g.obj_d.records)


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
