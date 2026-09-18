# rpt_dam_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop, Sum
from gamspy.math import Min

from core.utils import SowGPType, apply_sw_notags, extract_var_domain, wrap_in_sum

if TYPE_CHECKING:
    from gamspy._symbols.implicits import ImplicitParameter

    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def rpt_dam_mod_GP(
    tc: TimesModelClass,
    env: CompileEnvironment,
    *,
    solveda: str,
) -> None:
    """Translation unit for rpt_dam.mod.

    ``var``/``vart``/``cli``/``sws``/``sow``/``scum`` are read from ``env``
    (already scoped by the caller, mirroring how rpt_dam.mod relies on
    %VAR%/%VART%/... already being set by whichever tag state its own
    $BATINCLUDE was nested under) rather than being passed explicitly.
    ``solveda`` alone stays an explicit argument since callers may need to
    pass a snapshot taken before their own SOLVEDA override (see
    rptmain_mod.py's ``rpt_dam_solveda``).
    """
    g = tc
    env = env.fork()
    r, t, c, s, w, cur = g.r, g.t, g.c, g.s, g.w, g.cur

    stages_yes = env.stages.upper() == "YES"

    swp = ""
    sw1: SowGPType = ()
    if solveda == "1":
        swp = "S"
        sw1 = ("1",)
    if stages_yes:
        swp = "S"
        sw1 = (g.Sow,)

    cst_dam = g.get_parameter(f"{swp}CST_DAM")
    dam_obj = g.get_parameter(f"{swp}DAM_OBJ")

    var_obj = g.get_variable(f"{env.var}_OBJ")
    var_obj.m[r, "OBJDAM", cur, *env.sow_GP].where[g.Rdcur[r, cur]] = 0

    # Always report the accurate non-linear costs
    g.Rxx.setRecords(None)
    with Loop(g.Rdcur[r, cur]):
        g.Rxx[g.Rtc].where[g.dam_cost[g.Rtc, cur]] = True

    # If using climate module, enable damages for total emissions/concentration
    if env.cli == "YES":
        vart_id, vart_set = extract_var_domain(env.vart_GP)
        var_clitot = g.get_variable(f"{vart_id}_CLITOT")
        var_clibox = g.get_variable(f"{env.var}_CLIBOX")
        clitot_term = wrap_in_sum(
            target=var_clitot.l[g.CmVar, t, *env.sws_GP],  # type: ignore[type-var]
            domain=vart_set,
        ).where[g.CmKind[g.CmVar]]
        clibox_term = var_clibox.l[g.CmVar, "ATM", t, *env.sow_GP].where[
            ~g.CmKind[g.CmVar]
        ]
        cst_dam[*sw1, r, t, c[g.cg[g.CmVar]]].where[(~g.Rc[r, c]) & g.Rxx[r, t, c]] = (
            clitot_term + clibox_term
        )

    vart_id, vart_set = extract_var_domain(env.vart_GP)
    var_comnet = g.get_variable(f"{vart_id}_COMNET")
    var_comprd = g.get_variable(f"{vart_id}_COMPRD")

    comnet_term = wrap_in_sum(
        target=var_comnet.l[r, t, c, s, *env.sws_GP],  # type: ignore[type-var]
        domain=vart_set,
    ).where[~g.dam_elast[r, c, "N"]]
    comprd_term = wrap_in_sum(
        target=var_comprd.l[r, t, c, s, *env.sws_GP],  # type: ignore[type-var]
        domain=vart_set,
    ).where[g.dam_elast[r, c, "N"]]
    cst_dam[*sw1, g.Rxx[r, t, c]].where[g.Rc[r, c]] = Sum(
        g.ComTs[r, c, s],
        g.dam_coef[r, t, c, s] * (comnet_term + comprd_term),
    )

    cost_term: Sum | ImplicitParameter
    if stages_yes:
        cost_term = Sum(
            g.sww[g.Sow, w].where[
                g.SwTsw[g.Sow, t, w].where[~g.wwdam[c]]
                + g.sww[w, g.Sow].where[g.wwdam[c]]
            ],
            g.s_dam_cost[r, t, c, cur, "1", w],
        )
    else:
        cost_term = g.dam_cost[r, t, c, cur]

    dam_obj[*sw1, g.Rxx[r, t, c], cur].where[g.Rdcur[r, cur]] = cost_term * (
        g.dam_tvoc[r, t, c, "N"]
        * (
            Min(cst_dam[*sw1, r, t, c], g.dam_size[r, t, c, "N"])
            + g.dam_size[r, t, c, "N"] * g.dam_elast[r, c, "N"]
        )
        + (
            (
                Min(g.dam_tqty[r, t, c], cst_dam[*sw1, r, t, c])
                ** (g.dam_elast[r, c, "LO"] + 1)
                # Subtract full LO costs if DAM_ELAST(N) = -1 (constant term)
                + g.dam_elast[r, c, "N"]
                * (
                    g.dam_tqty[r, t, c] ** (g.dam_elast[r, c, "LO"] + 1)
                    - g.dam_size[r, t, c, "N"] ** (g.dam_elast[r, c, "LO"] + 1)
                )
                - Min(g.dam_size[r, t, c, "N"], cst_dam[*sw1, r, t, c])
                ** (g.dam_elast[r, c, "LO"] + 1)
            )
            / (
                g.dam_tqty[r, t, c] ** g.dam_elast[r, c, "LO"]
                * (g.dam_elast[r, c, "LO"] + 1)
            )
        )
        + (
            (
                cst_dam[*sw1, r, t, c] ** (g.dam_elast[r, c, "UP"] + 1)
                - g.dam_tqty[r, t, c] ** (g.dam_elast[r, c, "UP"] + 1)
            )
            / (
                g.dam_tqty[r, t, c] ** g.dam_elast[r, c, "UP"]
                * (g.dam_elast[r, c, "UP"] + 1)
            )
        ).where[cst_dam[*sw1, r, t, c] > g.dam_tqty[r, t, c]]
        # Shift cost curve by DAM_ELAST(N) if applicable
        + g.dam_elast[r, c, "N"]
        * (cst_dam[*sw1, r, t, c] + g.dam_elast[r, c, "N"] * g.dam_tqty[r, t, c])
    )

    if env.scum == "1":
        apply_sw_notags(env=env)
        sw1 = ("1",)
        g.sdam_obj[*sw1, g.Rxx[r, t, c], cur].where[g.Rdcur[r, cur]] = Sum(
            w, g.sw_prob[w] * g.sdam_obj[w, r, t, c, cur]
        )

    reg_acost = g.get_parameter(f"{swp}REG_ACOST")
    cst_pvc = g.get_parameter(f"{swp}CST_PVC")
    reg_wobj = g.get_parameter(f"{swp}REG_WOBJ")
    var_obj = g.get_variable(f"{env.var}_OBJ")

    cst_dam[*sw1, g.Rxx[r, t, c]] = Sum(g.Rdcur[r, cur], dam_obj[*sw1, r, t, c, cur])
    reg_acost[*sw1, r, t, "DAM"] = Sum(g.Rxx[r, t, c], cst_dam[*sw1, r, t, c])
    cst_pvc[*sw1, "DAM", r, c].where[g.dam_step[r, c, "FX"]] = Sum(
        t, cst_dam[*sw1, r, t, c] * g.coef_pvt[r, t]
    )
    # Complete also reporting of discounted costs
    reg_wobj[*sw1, r, "DAM", cur] = Sum(
        g.Rxx[r, t, c].where[(~g.dam_elast[r, c, "N"]) & g.dam_step[r, c, "FX"]],
        g.obj_pvt[r, t, cur] * dam_obj[*sw1, r, t, c, cur],
    )
    reg_wobj[*sw1, r, "DAS", cur] = Sum(
        g.Rxx[r, t, c].where[g.dam_elast[r, c, "N"] & g.dam_step[r, c, "FX"]],
        g.obj_pvt[r, t, cur] * dam_obj[*sw1, r, t, c, cur],
    )
    reg_wobj[*sw1, r, "DAM-EXT+", cur] = (
        reg_wobj[*sw1, r, "DAM", cur] + reg_wobj[*sw1, r, "DAS", cur]
    )
    reg_wobj[*sw1, r, "DAM", cur] = (
        reg_wobj[*sw1, r, "DAM", cur]
        / reg_wobj[*sw1, r, "DAM-EXT+", cur]
        * var_obj.l[r, "OBJDAM", cur, *env.sow_GP]
    ).where[reg_wobj[*sw1, r, "DAM-EXT+", cur] > 0]
    reg_wobj[*sw1, r, "DAS", cur] = (
        var_obj.l[r, "OBJDAM", cur, *env.sow_GP] - reg_wobj[*sw1, r, "DAM", cur]
    )
    # Complete also reporting of discounted external damages
    reg_wobj[*sw1, r, "DAM-EXT+", cur] = (
        Sum(g.Rxx[r, t, c], g.obj_pvt[r, t, cur] * dam_obj[*sw1, r, t, c, cur])
        - var_obj.l[r, "OBJDAM", cur, *env.sow_GP]
    )

    # Weighted results
    if f"{env.stages}{env.scum}" == "YES":
        g.reg_wobj[r, g.damobj, cur] = Sum(
            w, g.sw_prob[w] * g.sreg_wobj[w, r, g.damobj, cur]
        )


def rpt_dam_mod(
    *,
    stages: str,
    var: str,
    cli: str,
    vart: str,
    sws: str,
    sow: str,
    solveda: str,
    scum: str,
) -> str:
    """Translation unit for rpt_dam.mod.

    NOTE: kept as a raw-GAMS-string generator solely because its one
    remaining caller (solve_stc.py's ``exec_main``) splices this text into a
    runtime GAMS ``IF(NOT (SW_PARM OR GDL), ...)`` conditional that is itself
    still untranslated raw text. Calling the native ``rpt_dam_mod_GP``
    instead there would execute its assignments unconditionally at compile
    time rather than being gated by that runtime check. rptmain_mod.py and
    preppm_msa.py, whose call sites are NOT nested inside a runtime
    conditional, use ``rpt_dam_mod_GP``. Once solve_stc.py's ``exec_main`` is
    translated, delete this function (and exec1/exec2 below) and switch its
    call site to ``rpt_dam_mod_GP`` too.
    """

    swp = ""
    sw1 = ""

    if solveda == "1":
        swp = "S"
        sw1 = "'1',"

    stages_yes = stages.upper() == "YES"
    if stages_yes:
        swp = "S"
        sw1 = "SOW,"

    exec_1_code = exec1(
        stages=stages, var=var, cli=cli, swp=swp, vart=vart, sws=sws, sow=sow, sw1=sw1
    )

    if scum == "1":
        # Mirrors apply_sw_notags's fixed reset (rpt_dam.mod's own
        # $SETLOCAL SW1 "'1'," %SW_NOTAGS%): SW1 is pinned to the literal
        # '1' slot and VAR/SOW are untagged for the rest of this function.
        sw1 = "'1',"
        var = "VAR"
        sow = ""

    exec_2_code = exec2(stages=stages, var=var, swp=swp, sow=sow, sw1=sw1, scum=scum)
    return exec_1_code + exec_2_code


def exec1(
    stages: str,
    var: str,
    cli: str,
    swp: str,
    vart: str,
    sws: str,
    sow: str,
    sw1: str,
) -> str:
    block1 = rf"""
    {var}_OBJ.M(R,'OBJDAM',CUR {sow})$RDCUR(R,CUR) = 0;
*------------------------------------------------------------------------------
* Always report the accurate non-linear costs
      OPTION CLEAR=RXX; LOOP(RDCUR(R,CUR), RXX(RTC)$DAM_COST(RTC,CUR) = YES);
*------------------------------------------------------------------------------
    """

    # If using climate module, enable damages for total emissions/concentration
    cli_block = (
        rf"""
{swp}CST_DAM({sw1}R,T,C(CG(CM_VAR)))$((NOT RC(R,C))$RXX(R,T,C)) =
{vart}_CLITOT.L(CM_VAR,T{sws})$CM_KIND(CM_VAR)+{var}_CLIBOX.L(CM_VAR,'ATM',T{sow})$(NOT CM_KIND(CM_VAR));
"""
        if cli == "YES"
        else ""
    )

    block_3 = rf"""
{swp}CST_DAM({sw1}RXX(R,T,C))$RC(R,C) =
    SUM(COM_TS(R,C,S),DAM_COEF(R,T,C,S) *
    ({vart}_COMNET.L(R,T,C,S{sws})$(NOT DAM_ELAST(R,C,'N'))+{vart}_COMPRD.L(R,T,C,S{sws})$DAM_ELAST(R,C,'N')));
{swp}DAM_OBJ({sw1}RXX(R,T,C),CUR)$RDCUR(R,CUR) =
{"DAM_COST(R,T,C,CUR) *" if stages != "YES" else "SUM(SWW(SOW,W)$(SW_TSW(SOW,T,W)$(NOT WWDAM(C))+SWW(W,SOW)$WWDAM(C)),S_DAM_COST(R,T,C,CUR,'1',W)) *"}
(DAM_TVOC(R,T,C,'N')*(MIN({swp}CST_DAM({sw1}R,T,C),DAM_SIZE(R,T,C,'N'))+DAM_SIZE(R,T,C,'N')*DAM_ELAST(R,C,'N')) +
    ((MIN(DAM_TQTY(R,T,C),{swp}CST_DAM({sw1}R,T,C))**(DAM_ELAST(R,C,'LO')+1) +
* Subtract full LO costs if DAM_ELAST(N) = -1 (constant term)
    DAM_ELAST(R,C,'N')*(DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'LO')+1)-DAM_SIZE(R,T,C,'N')**(DAM_ELAST(R,C,'LO')+1)) -
    MIN(DAM_SIZE(R,T,C,'N'),{swp}CST_DAM({sw1}R,T,C))**(DAM_ELAST(R,C,'LO')+1)) /
    (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'LO')*(DAM_ELAST(R,C,'LO')+1))) +
    (({swp}CST_DAM({sw1}R,T,C)**(DAM_ELAST(R,C,'UP')+1) -
    DAM_TQTY(R,T,C)**(DAM_ELAST(R,C,'UP')+1)) /
    (DAM_TQTY(R,T,C)**DAM_ELAST(R,C,'UP')*(DAM_ELAST(R,C,'UP')+1)))$({swp}CST_DAM({sw1}R,T,C) GT DAM_TQTY(R,T,C)) +
* Shift cost curve by DAM_ELAST(N) if applicable
    DAM_ELAST(R,C,'N')*({swp}CST_DAM({sw1}R,T,C)+DAM_ELAST(R,C,'N')*DAM_TQTY(R,T,C))
);
"""
    return block1 + cli_block + block_3


def exec2(stages: str, var: str, swp: str, sow: str, sw1: str, scum: str) -> str:
    scum_block = (
        rf"""
    SDAM_OBJ({sw1}RXX(R,T,C),CUR)$RDCUR(R,CUR) = SUM(W,SW_PROB(W)*SDAM_OBJ(W,R,T,C,CUR));
    """
        if scum == "1"
        else ""
    )

    block_2 = rf"""
    {swp}CST_DAM({sw1}RXX(R,T,C)) = SUM(RDCUR(R,CUR),{swp}DAM_OBJ({sw1}R,T,C,CUR));
      {swp}REG_ACOST({sw1}R,T,'DAM') = SUM(RXX(R,T,C),{swp}CST_DAM({sw1}R,T,C));
      {swp}CST_PVC({sw1}'DAM',R,C)$DAM_STEP(R,C,'FX') = SUM(T,{swp}CST_DAM({sw1}R,T,C)*COEF_PVT(R,T));
* Complete also reporting of discounted costs
      {swp}REG_WOBJ({sw1}R,'DAM',CUR) = SUM(RXX(R,T,C)$((NOT DAM_ELAST(R,C,'N'))$DAM_STEP(R,C,'FX')),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR));
      {swp}REG_WOBJ({sw1}R,'DAS',CUR) = SUM(RXX(R,T,C)$(DAM_ELAST(R,C,'N')$DAM_STEP(R,C,'FX')),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR));
      {swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) = {swp}REG_WOBJ({sw1}R,'DAM',CUR)+{swp}REG_WOBJ({sw1}R,'DAS',CUR);
      {swp}REG_WOBJ({sw1}R,'DAM',CUR) = ({swp}REG_WOBJ({sw1}R,'DAM',CUR)/{swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR)*{var}_OBJ.L(R,'OBJDAM',CUR{sow}))$({swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) GT 0);
      {swp}REG_WOBJ({sw1}R,'DAS',CUR) = {var}_OBJ.L(R,'OBJDAM',CUR{sow}) - {swp}REG_WOBJ({sw1}R,'DAM',CUR);
* Complete also reporting of discounted external damages
      {swp}REG_WOBJ({sw1}R,'DAM-EXT+',CUR) = SUM(RXX(R,T,C),OBJ_PVT(R,T,CUR)*{swp}DAM_OBJ({sw1}R,T,C,CUR)) - {var}_OBJ.L(R,'OBJDAM',CUR{sow});
    """

    block_3 = (
        r"""
    REG_WOBJ(R,DAMOBJ,CUR) = SUM(W,SW_PROB(W)*SREG_WOBJ(W,R,DAMOBJ,CUR));
    """
        if stages + scum == "YES"
        else ""
    )

    return scum_block + block_2 + block_3
