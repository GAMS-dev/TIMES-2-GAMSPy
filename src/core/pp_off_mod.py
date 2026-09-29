# pp_off_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_OFF sets to Start/End of the OFF period range
# *   %1 - OFF Set name
# *   %2 - 'C'ommodity/'P'rocess index indicator
# *   %3 - control set
# *   %4 - Table to set for each off-range with qualifier and one open (
# *   %5 - The value for the off range (EPS/NO)
# *=============================================================================*
# * Comments: Depends on BOHYEAR/EOHYEAR being ordered 1 higher than ALLYEAR
# *-----------------------------------------------------------------------------

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gamspy import Alias, Expression, Number, Set
    from gamspy._symbols.implicits import ImplicitSet

from gamspy import Loop, Ord, Sum

from utils.times_model_class import TimesModelClass


def pp_off_GP(
    g: TimesModelClass,
    arg1: Set | Alias,
    arg2: tuple[Set | Alias, ...] | tuple[()],
    arg3: ImplicitSet | Expression | Number,  # expect Number(1) for ""
    arg4: ImplicitSet,
    arg5: int,  # 1 or 0
) -> None:
    # * Cope with multiple OFF-ranges
    g.Fil.setRecords(None)
    with Loop(arg1[g.r, *arg2, g.bohyear, g.eohyear].where[arg3]):
        g.startoff[...] = Ord(g.bohyear) - 2.0
        g.endoff[...] = Ord(g.eohyear)
        # * set the flags of the shutoff period
        g.Fil[g.Eohyears[g.ll]].where[
            ((Ord(g.ll) > g.startoff).where[(Ord(g.ll) < g.endoff)])
        ] = True
    # * open (
    arg4.where[
        (
            (Sum(g.Periodyr[g.t, g.Fil], 1) / g.d[g.t] >= g.g_offthd[g.t]).where[
                g.Fil[g.t]
            ]
        )
    ] = arg5


def pp_off(
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
) -> str:
    return rf"""
*$ONLISTING
* Cope with multiple OFF-ranges
      OPTION CLEAR=FIL;
      LOOP({arg1}(R,{arg2},BOHYEAR,EOHYEAR){arg3}, STARTOFF=ORD(BOHYEAR)-2; ENDOFF=ORD(EOHYEAR);
* set the flags of the shutoff period
        FIL(EOHYEARS(LL))$((ORD(LL) > STARTOFF)$(ORD(LL) < ENDOFF)) = YES);
* open (
      {arg4}(SUM(PERIODYR(T,FIL),1)/D(T) GE G_OFFTHD(T))$FIL(T)) = {arg5};
*$OFFLISTING
"""
