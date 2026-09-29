# clearsol_stp.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2025 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * CLEARSOL.stp: Clear solution values for projection years
# *=============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gamspy import Loop

if TYPE_CHECKING:
    from gamspy import Alias, Set
    from gamspy._symbols.implicits import ImplicitSet

    from core.utils import SowGPType
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


def clearsol_stp_GP(
    *,
    g: TimesModelClass,
    arg1: str = "",
    var: str,
    sow: SowGPType,
    eq: str,
    swt: tuple[Set | Alias | ImplicitSet, ...] | tuple[()],
    cli: str,
    abs_: str,
    macro: str,
    stages: str,
) -> None:
    """GAMSPy twin of :func:`clearsol_stp`.

    ``IF(1%1,`` is unconditional for the only argument-less caller, and ``gp.If``
    is confined to ``gp.Loop`` bodies, so the guard is dropped for ``arg1 == ""``
    and refused otherwise.
    """
    if arg1 != "":
        raise NotImplementedError(
            f"clearsol.stp guard IF(1{arg1}, ...) has no GAMSPy twin; "
            "use the raw GAMS variant for this caller."
        )
    if cli.upper() == "YES":
        raise NotImplementedError(
            "%VAR%_CLIBOX is still declared in raw GAMS (equ_ext.cli), so the "
            "CLI branch of clearsol.stp has no GAMSPy twin yet."
        )

    (r, v, t, p, c, s, ie, ll, lA, ucn) = (
        g.r,
        g.v,
        g.t,
        g.p,
        g.c,
        g.s,
        g.ie,
        g.ll,
        g.lA,
        g.ucn,
    )
    Rvt, Vnt, RtPp, Fil, no_rt = g.Rvt, g.Vnt, g.RtPp, g.Fil, g.no_rt

    (VAR_ACT, VAR_FLO, VAR_IRE, VAR_SIN, VAR_SOUT, VAR_NCAP) = (
        g.get_variable(f"{var}_ACT"),
        g.get_variable(f"{var}_FLO"),
        g.get_variable(f"{var}_IRE"),
        g.get_variable(f"{var}_SIN"),
        g.get_variable(f"{var}_SOUT"),
        g.get_variable(f"{var}_NCAP"),
    )
    (VAR_COMNET, VAR_COMPRD, VAR_UCT, VAR_UCTS, VAR_UCRT, VAR_UCRTS, VAR_SCAP) = (
        g.get_variable(f"{var}_COMNET"),
        g.get_variable(f"{var}_COMPRD"),
        g.get_variable(f"{var}_UCT"),
        g.get_variable(f"{var}_UCTS"),
        g.get_variable(f"{var}_UCRT"),
        g.get_variable(f"{var}_UCRTS"),
        g.get_variable(f"{var}_SCAP"),
    )

    Rvt[r, Vnt[v, t]].where[RtPp[r, t]] = True
    Fil[ll] = t[ll]
    with Loop(r):
        Fil[t].where[no_rt[r, t]] = False
    VAR_ACT.l[Rvt, p, s, *sow] = 0
    VAR_FLO.l[Rvt, p, c, s, *sow] = 0
    VAR_IRE.l[Rvt, p, c, s, ie, *sow] = 0
    VAR_SIN.l[Rvt, p, c, s, *sow] = 0
    VAR_SOUT.l[Rvt, p, c, s, *sow] = 0
    VAR_NCAP.l[RtPp, p, *sow] = 0
    VAR_COMNET.l[RtPp, c, s, *sow] = 0
    VAR_COMPRD.l[RtPp, c, s, *sow] = 0
    VAR_NCAP.l[RtPp, p, *sow] = 0
    VAR_UCT.l[ucn, t[Fil], *sow] = 0
    VAR_UCTS.l[ucn, t[Fil], s, *sow] = 0
    VAR_UCRT.l[ucn, RtPp, *sow] = 0
    VAR_UCRTS.l[ucn, RtPp, s, *sow] = 0
    VAR_SCAP.l[Rvt, p, *sow] = 0
    g.get_equation(f"{eq}G_COMBAL").l[RtPp, c, s, *swt] = 0
    if abs_.upper() == "YES":
        g.get_variable(f"{var}_BSPRS").l[Rvt, p, c, s, lA, *sow] = 0
    if macro.upper() != "YES":
        g.eq_obj.m[...] = 0

    # $IF NOT %STAGES%==YES $EXIT
    if stages != "YES":
        return

    g.VAR_NCAP.l[RtPp, p] = 0
    g.VAR_UCT.l[ucn, t[Fil]] = 0
    g.VAR_UCTS.l[ucn, t[Fil], s] = 0
    g.VAR_UCRT.l[ucn, RtPp] = 0
    g.VAR_UCRTS.l[ucn, RtPp, s] = 0


def clearsol_stp(
    *,
    arg1: str = "",
    var: str,
    sow: str,
    eq: str,
    swt: str,
    cli: str,
    abs_: str,
    macro: str,
    stages: str,
) -> str:
    return rf"""
  IF(1{arg1},
  RVT(R,VNT(V,T))$RT_PP(R,T) = YES;
  FIL(LL)=T(LL); LOOP(R, FIL(T)$NO_RT(R,T) = NO);
  {var}_ACT.L(RVT,P,S{sow}) = 0;
  {var}_FLO.L(RVT,P,C,S{sow}) = 0;
  {var}_IRE.L(RVT,P,C,S,IE{sow}) = 0;
  {var}_SIN.L(RVT,P,C,S{sow}) = 0;
  {var}_SOUT.L(RVT,P,C,S{sow}) = 0;
  {var}_NCAP.L(RT_PP,P{sow}) = 0;
  {var}_COMNET.L(RT_PP,C,S{sow}) = 0;
  {var}_COMPRD.L(RT_PP,C,S{sow}) = 0;
  {var}_NCAP.L(RT_PP,P{sow}) = 0;
  {var}_UCT.L(UC_N,T(FIL){sow}) = 0;
  {var}_UCTS.L(UC_N,T(FIL),S{sow}) = 0;
  {var}_UCRT.L(UC_N,RT_PP{sow}) = 0;
  {var}_UCRTS.L(UC_N,RT_PP,S{sow}) = 0;
  {var}_SCAP.L(RVT,P{sow}) = 0;
  {eq}G_COMBAL.L(RT_PP,C,S{swt}) = 0;
{f"{var}_CLIBOX.L(CM_VAR,CM_BOX,LL{sow})$CM_LED(LL)=0;" if cli.upper() == "YES" else ""}
{f"{var}_BSPRS.L(RVT,P,C,S,L{sow}) = 0;" if abs_.upper() == "YES" else ""}
{"EQ_OBJ.M = 0;" if macro.upper() != "YES" else ""}
  );
{
        r'''
  VAR_NCAP.L(RT_PP,P) = 0;
  VAR_UCT.L(UC_N,T(FIL)) = 0;
  VAR_UCTS.L(UC_N,T(FIL),S) = 0;
  VAR_UCRT.L(UC_N,RT_PP) = 0;
  VAR_UCRTS.L(UC_N,RT_PP,S) = 0;
'''
        if stages == "YES"
        else ""
    }
"""
