# sensis_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * sensis.stc Wrapper for sensitivity analysis parameters
# *=============================================================================*

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gamspy import Alias, Set

    from core.utils import SowGPType

import logging

from gamspy import Domain, Else, If, Loop, Number, Product, SpecialValues, Sum, sparse
from gamspy.math import Min, diag, power

from core.bnd_set_mod import bnd_set_mod, bnd_set_mod_GP
from core.bnd_ucw_mod import bnd_ucw_mod, bnd_ucw_mod_GP
from core.clearsol_stp import clearsol_stp
from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def sensis_stc(
    *,
    var: str,
    cufscal: str,
    cucscal: str,
    cli: str,
    model_name: str,
    mca: str,
    stages: str,
    swd: str,
    sow: str,
    eq: str,
    swt: str,
    abs_: str,
    macro: str,
    rtp_ffcs_defined: bool,
    s_cap_bnd_declared: bool,
    bnd_ucw_defined: dict[str, bool],
) -> str:
    coef_ext_code = ""
    if mca.upper() == "YES":
        # from core.coef_ext_mca import coef_ext_mca
        # coef_ext_code = coef_ext_mca(arg1="MCA", arg2="sensis")
        raise FileNotFoundError("coef_ext.mca does not exist.")

    return rf"""
{coef_ext_code}
*------------------------------------------------------------------------------
* Clear deterministic parameter if to be set from uncertain
{"OPTION CLEAR=CM_MAXC;" if cli == "YES" else ""}
{"OPTION CLEAR=RTP_FFCS;" if rtp_ffcs_defined else ""}
* Cumulative variable bounds
 VAR_CUMFLO.LO(R,P,C,ALLYEAR,LL) = 0;
 VAR_CUMFLO.UP(R,P,C,ALLYEAR,LL) = INF;
 VAR_CUMCOM.LO(R,C,COM_VAR,ALLYEAR,LL) = 0;
 VAR_CUMCOM.UP(R,C,COM_VAR,ALLYEAR,LL) = INF;
*------------------------------------------------------------------------------
  LOOP(SOW,
{
        bnd_ucw_mod(
            arg1="",
            arg2="I",
            var=var,
            stages=stages,
            swd=swd,
            sow=sow,
            defined_symbols=bnd_ucw_defined,
        )
    }
{
        bnd_set_mod(
            arg1=f"{var}_CAP",
            arg2="R,T,P",
            arg3="CAP_BND",
            arg4="RTP(RT_PP(R,T),P)",
            arg5="",
            arg6="I",
            stages=stages,
            swd=swd,
            sow=sow,
            stochastic_symbol_declared=s_cap_bnd_declared,
        )
    }
* Cumulative variable bounds
    VAR_CUMFLO.LO(R,P,C,YEAR,LL)$S_FLO_CUM(R,P,C,YEAR,LL,'LO','1',SOW) = S_FLO_CUM(R,P,C,YEAR,LL,'LO','1',SOW)*(1/{
        cufscal
    })*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);
    VAR_CUMFLO.UP(R,P,C,YEAR,LL)$S_FLO_CUM(R,P,C,YEAR,LL,'UP','1',SOW) = S_FLO_CUM(R,P,C,YEAR,LL,'UP','1',SOW)*(1/{
        cufscal
    })*(FLO_CUM(R,P,C,YEAR,LL,'N')+1);
    S_COM_CUM(RC_CUMCOM(R,COM_VAR,YEAR,LL,C),L('LO'),'1',SOW)$(NOT S_COM_CUM(RC_CUMCOM,L,'1',SOW)) = -INF$SUM((RTC(R,T,C),ANNUAL(S)),MIN(0,COM_BNDPRD(RTC,S,L)$DIAG(COM_VAR,'PRD')+COM_BNDNET(RTC,S,L)$DIAG(COM_VAR,'NET')+1-1));
    VAR_CUMCOM.LO(R,C,COM_VAR,YEAR,LL)$S_COM_CUM(R,COM_VAR,YEAR,LL,C,'LO','1',SOW) = S_COM_CUM(R,COM_VAR,YEAR,LL,C,'LO','1',SOW)*(1/{
        cucscal
    })*(COM_CUM(R,COM_VAR,YEAR,LL,C,'N')+1);
    VAR_CUMCOM.UP(R,C,COM_VAR,YEAR,LL)$S_COM_CUM(R,COM_VAR,YEAR,LL,C,'UP','1',SOW) = S_COM_CUM(R,COM_VAR,YEAR,LL,C,'UP','1',SOW)*(1/{
        cucscal
    })*(COM_CUM(R,COM_VAR,YEAR,LL,C,'N')+1);

{
        '''
  RTP_FFCS(RTP(R,T,P),CG,COM_GRP)$RP_FFSGG(R,P,CG,COM_GRP) =
    SUM((RP_FFSGGM(R,P,CG,COM_GRP,CG1,CG2),SW_TSW(SOW,T,W)),PROD(SW_MAP(T,W,J,WW)$S_FLO_FUNC(RTP,CG1,CG2,J,WW),S_FLO_FUNC(RTP,CG1,CG2,J,WW))-1);
* Remap reduced FUNC flows
  LOOP(RPCG_PTRAN(RP,C,COM,CG,CG2)$RP_FFSGG(RP,CG,CG2),IF(RPC_FFUNC(RP,C),RP_DCGG(RP,C,CG,CG2,'UP')=YES; ELSE RP_DCGG(RP,COM,CG,CG2,'LO')=YES));
  RP_DCGG(RPC_FFUNC(RP,COM),CG,C,'UP')$(RPG_1ACE(RP,CG,COM)$RPC_ACT(RP,C)) $= RP_FFSGG(RP,CG,C);
  RTP_FFCS(RTP(R,T,P),ACTCG,C)$RPC_FFUNC(R,P,C) $= SUM(RP_DCGG(R,P,C,CG,CG2,L),(POWER(RTP_FFCS(RTP,CG,CG2)+1,BDSIG(L))-1)$(RTP_FFCS(RTP,CG,CG2)+1));
  OPTION CLEAR=RP_DCGG;
'''
        if rtp_ffcs_defined
        else ""
    }
{"CM_MAXC(ALLYEAR,ITEM) $= S_CM_MAXC(ALLYEAR,ITEM,'1',SOW);" if cli == "YES" else ""}
  );
*------------------------------------------------------------------------------
IF(SW_PHASE=2,SPAR_UCSL(SOW,UC_N,U2,U3,U4)=0);
IF(CARD(REG_FIXT)=0,EQ_OBJ.M$({model_name}.SOLVEOPT<>1)=0; OPTION SOLVEOPT=REPLACE);
{
        clearsol_stp(
            arg1="$EQ_OBJ.M",
            var=var,
            sow=sow,
            eq=eq,
            swt=swt,
            cli=cli,
            abs_=abs_,
            macro=macro,
            stages=stages,
        )
    }
"""


def sensis_stc_GP(
    g: TimesModelClass,
    var: str,
    cufscal: int,
    cucscal: int,
    cli: str,
    model_name: str,
    mca: str,
    stages: str,
    swd_GP: tuple[Set | Alias] | tuple[()],
    sow_GP: SowGPType,
    eq: str,
    swt_GP: str,
    abs_: str,
    macro: str,
    rtp_ffcs_defined: bool,
    s_cap_bnd_declared: bool,
    bnd_ucw_defined: dict[str, bool],
) -> tuple[str, dict[str, Any]]:
    if mca.upper() == "YES":
        # from core.coef_ext_mca import coef_ext_mca
        # coef_ext_code = coef_ext_mca(arg1="MCA", arg2="sensis")
        raise FileNotFoundError("coef_ext.mca does not exist.")

    r, p, c, allyear, ll, year, comvar, lA, s = (
        g.r,
        g.p,
        g.c,
        g.allyear,
        g.ll,
        g.year,
        g.comvar,
        g.lA,
        g.s,
    )
    t, j, ww, Rp, Com, w, cg, cg1, cg2, comgrp = (
        g.t,
        g.j,
        g.ww,
        g.Rp,
        g.Com,
        g.w,
        g.cg,
        g.cg1,
        g.cg2,
        g.comgrp,
    )

    # * Clear deterministic parameter if to be set from uncertain
    if cli == "YES":
        g.cm_maxc.setRecords(None)
    if rtp_ffcs_defined:
        g.rtp_ffcs.setRecords(None)

    VAR_CUMFLO = g.VAR_CUMFLO
    VAR_CUMCOM = g.VAR_CUMCOM

    # * Cumulative variable bounds
    VAR_CUMFLO.lo[r, p, c, allyear, ll] = 0
    VAR_CUMFLO.up[r, p, c, allyear, ll] = SpecialValues.POSINF
    VAR_CUMCOM.lo[r, c, comvar, allyear, ll] = 0
    VAR_CUMCOM.up[r, c, comvar, allyear, ll] = SpecialValues.POSINF

    with Loop(g.Sow):
        bnd_ucw_mod_GP(
            g=g,
            arg1=Number(1),
            arg2="I",
            var=var,
            stages=stages,
            swd_GP=swd_GP,
            sow_GP=sow_GP,
            defined_symbols=bnd_ucw_defined,
        )

        bnd_set_mod_GP(
            g=g,
            variable_name=f"{var}_CAP",
            primary_domain=(g.r, g.t, g.p),
            bound_param_name="CAP_BND",
            control_domain=(g.Rtp[g.RtPp[g.r, g.t], g.p],),
            extra_condition=Number(1),
            arg6="I",
            stages=stages,
            swd=swd_GP,
            sow=sow_GP,
            stochastic_symbol_declared=s_cap_bnd_declared,
        )

        # * Cumulative variable bounds
        VAR_CUMFLO.lo[r, p, c, year, ll].where[
            g.s_flo_cum[r, p, c, year, ll, "LO", "1", g.Sow]
        ] = (
            g.s_flo_cum[r, p, c, year, ll, "LO", "1", g.Sow]
            * (1 / cufscal)
            * (g.flo_cum[r, p, c, year, ll, "N"] + 1)
        )
        VAR_CUMFLO.up[r, p, c, year, ll].where[
            g.s_flo_cum[r, p, c, year, ll, "UP", "1", g.Sow]
        ] = (
            g.s_flo_cum[r, p, c, year, ll, "UP", "1", g.Sow]
            * (1 / cufscal)
            * (g.flo_cum[r, p, c, year, ll, "N"] + 1)
        )
        g.s_com_cum[g.RcCumcom[r, comvar, year, ll, c], lA["LO"], "1", g.Sow].where[
            ~g.s_com_cum[g.RcCumcom, lA, "1", g.Sow]
        ] = Number(SpecialValues.NEGINF).where[
            Sum(
                Domain(g.Rtc[r, g.t, c], g.Annual[s]),
                Min(
                    0,
                    g.com_bndprd[g.Rtc, s, lA].where[diag(comvar, "PRD")]
                    + g.com_bndnet[g.Rtc, s, lA].where[diag(comvar, "NET")]
                    + 1
                    - 1,
                ),
            )
        ]
        VAR_CUMCOM.lo[r, c, comvar, year, ll].where[
            g.s_com_cum[r, comvar, year, ll, c, "LO", "1", g.Sow]
        ] = (
            g.s_com_cum[r, comvar, year, ll, c, "LO", "1", g.Sow]
            * (1 / cucscal)
            * (g.com_cum[r, comvar, year, ll, c, "N"] + 1)
        )
        VAR_CUMCOM.up[r, c, comvar, year, ll].where[
            g.s_com_cum[r, comvar, year, ll, c, "UP", "1", g.Sow]
        ] = (
            g.s_com_cum[r, comvar, year, ll, c, "UP", "1", g.Sow]
            * (1 / cucscal)
            * (g.com_cum[r, comvar, year, ll, c, "N"] + 1)
        )

        if rtp_ffcs_defined:
            g.rtp_ffcs[g.Rtp[r, t, p], cg, comgrp].where[
                g.RpFfsgg[r, p, cg, comgrp]
            ] = Sum(
                Domain(g.RpFfsggm[r, p, cg, comgrp, cg1, cg2], g.SwTsw[g.Sow, t, w]),
                Product(
                    g.SwMap[t, w, j, ww].where[g.s_flo_func[r, t, p, cg1, cg2, j, ww]],
                    g.s_flo_func[r, t, p, cg1, cg2, j, ww],
                )
                - 1,
            )
            # * Remap reduced FUNC flows
            with Loop(g.RpcgPtran[Rp, c, Com, cg, cg2].where[g.RpFfsgg[Rp, cg, cg2]]):
                with If(g.RpcFfunc[Rp, c]):
                    g.RpDcgg[Rp, c, cg, cg2, "UP"] = True
                with Else():  # type: ignore[no-untyped-call]
                    g.RpDcgg[Rp, Com, cg, cg2, "LO"] = True
            g.RpDcgg[g.RpcFfunc[Rp, Com], cg, c, "UP"].where[
                g.Rpg1ace[Rp, cg, Com].where[g.RpcAct[Rp, c]]
            ] = sparse(g.RpFfsgg[Rp, cg, c])
            g.rtp_ffcs[g.Rtp[r, t, p], g.Actcg, c].where[g.RpcFfunc[r, p, c]] = sparse(
                Sum(
                    g.RpDcgg[r, p, c, cg, cg2, lA],
                    (power(g.rtp_ffcs[r, t, p, cg, cg2] + 1, g.bdsig[lA]) - 1).where[  # type: ignore[arg-type]
                        g.rtp_ffcs[r, t, p, cg, cg2] + 1
                    ],
                )
            )
            g.RpDcgg.setRecords(None)

        if cli == "YES":
            g.cm_maxc[g.allyear, g.item] = sparse(
                g.s_cm_maxc[g.allyear, g.item, "1", g.Sow]
            )

    sw_phase = 0.0 if g.sw_phase.records is None else float(g.sw_phase.toValue())
    if sw_phase == 2:
        g.spar_ucsl[g.Sow, g.ucn, g.u2, g.u3, g.u4] = 0

    return (
        rf"""IF(CARD(REG_FIXT)=0,EQ_OBJ.M$({model_name}.SOLVEOPT<>1)=0; OPTION SOLVEOPT=REPLACE);""",
        {  # clearsol_stp_GP args
            "arg1": "$EQ_OBJ.M",
            "var": var,
            "sow": sow_GP,
            "eq": eq,
            "swt": swt_GP,
            "cli": cli,
            "abs_": abs_,
            "macro": macro,
            "stages": stages,
        },
    )
