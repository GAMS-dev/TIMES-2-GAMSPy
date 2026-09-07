# rpt_dam_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *------------------------------------------------------------------------------
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
    sw_notags: str = "",
) -> str:
    """Translation unit for rpt_dam.mod."""

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
        sw1 = "'1',"
        raise NotImplementedError()
        # self.tc.add_gams_code(module=self, phase="init", code=self.env.sw_notags)

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
