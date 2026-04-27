# pp_lvlfc_mod.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
# * PP_LVLPC aggregate/inherit attributes if at different than target level
# * Parameter arguments must be of the form (R,V,{P/C/P,C},S[,xx]*)
# *   arg1 - attribute name (FLO_COST, FLO_TAX etc.)
# *   arg2 - 'P', 'C' 'COM' or 'P,C' depending on attribute
# *   arg3 - TS set shooting for
# *   arg4 - remaining indexes (e.g. ',CUR')
# *   arg5 - UNCD7 residual dimension
# *   arg6 - ALL_TS or TS depending on whether inheritance is allowed
# *   arg7 - YEAR set to look for data (DATAYEAR/XMILE/V/'')
# *   arg8 - Existence qualifier set or YES
# *   arg9 - Optional indicator for weighting: Use 1 if inheritance is weighted
# *  arg10 - Optional indexes between TS set items and the S index
# *=============================================================================*


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlfcMod(GamsClass):
    """Translation unit for pp_lvlfc.mod."""

    # Instance attributes
    module_name: str = "pp_lvlfc_mod"
    gams_source: str = "pp_lvlfc.mod"

    def __init__(
        self: PpLvlfcMod,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
        arg3: str = "",
        arg4: str = "",
        arg5: str = "",
        arg6: str = "",
        arg7: str = "",
        arg8: str = "",
        arg9: str = "",
        arg10: str = "",
        arg11: str = "",
        arg12: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.arg4 = arg4
        self.arg5 = arg5
        self.arg6 = arg6
        self.arg7 = arg7
        self.arg8 = arg8
        self.arg9 = arg9
        self.arg10 = arg10
        self.arg11 = arg11
        self.arg12 = arg12
        self._sub_modules = {}
        self.compile()

    def compile(self: PpLvlfcMod) -> None:
        self.tc.enqueue(clear_uncd7, module=self)
        self.env.set_local("take", self.arg12)
        self.env.set_local("regy", f"R,{self.arg7}")
        self.env.set_local("ts", f"(NOT {self.arg3}(R,{self.arg2},S))$")
        self.env.set_local("awgt", "G_YRFR(R,S)/G_YRFR(R,TS)")
        self.env.set_local("iwgt", "")
        if not len(self.arg7):
            self.env.set_local("regy", "R")
        if self.arg6 == "S2":
            self.env.set_local("ts", "")
        if self.arg9 == "1":
            self.env.set_local("awgt", "1")
            self.env.set_local("iwgt", f"*G_YRFR(R,S)/G_YRFR(R,{self.arg6})")
        if self.arg11 == "N":
            self.env.set_local(
                "take",
                f"${self.arg1}(R,'0',{self.arg2}{self.arg10},'ANNUAL'{self.arg4})",
            )

        self.tc.enqueue(
            all_exec,
            module=self,
            take=self.env.take,
            regy=self.env.regy,
            ts=self.env.ts,
            awgt=self.env.awgt,
            iwgt=self.env.iwgt,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg8=self.arg8,
            arg10=self.arg10,
            arg11=self.arg11,
        )


def clear_uncd7(module: GamsClass) -> None:
    module.tc.add_gams_code(module=module, phase="run", code=r"OPTION CLEAR=UNCD7;")


def all_exec(
    module: GamsClass,
    take: str,
    regy: str,
    ts: str,
    awgt: str,
    iwgt: str,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg8: str,
    arg10: str,
    arg11: str,
) -> None:
    if arg11 == "N":
        module.tc.add_gams_code(
            module=module,
            phase="run",
            code=rf"""
{arg1}(R,LL--ORD(LL),{arg2}{arg10},S+STOA(S){arg4})$(STOAL(R,S)${arg1}(R,LL,{arg2}{arg10},S{arg4})) = 1;
""",
        )
    module.tc.add_gams_code(
        module=module,
        phase="run",
        code=rf"""
* Mark to be levelized if inheritance is allowed or S is not ANNUAL:
LOOP(({regy},{arg2}{arg10},S{arg4})$({ts}{arg1}({regy},{arg2}{arg10},S{arg4})), UNCD7({regy},{arg2}{arg10}{arg4}{arg5})$({arg8}{take}) = YES);
*-----------------------------------------------------------------------------
* Aggregation/inheritance to target timeslices
*-----------------------------------------------------------------------------
LOOP(UNCD7({regy},{arg2}{arg10}{arg4}{arg5}), TS_ARRAY(S) = {arg1}({regy},{arg2}{arg10},S{arg4});
 IF((NOT SUM(RS_BELOW(R,'ANNUAL',S)$TS_ARRAY(S),1))$TS_ARRAY('ANNUAL'),
   {arg1}({regy},{arg2}{arg10},S{arg4})${arg3}(R,{arg2},S) = SUM(ANNUAL({arg6}),TS_ARRAY({arg6}){iwgt});
 ELSE
* Leveling by simultaneous aggregation/inheritance; but only if target level value is not present
   LOOP({arg3}(R,{arg2},TS)$(NOT TS_ARRAY(TS)),
    {arg1}({regy},{arg2}{arg10},TS{arg4}) $=
     SUM(TS_MAP(R,TS,S)$FINEST(R,S), {awgt} * (TS_ARRAY(S) +
            SUM(RS_BELOW(R,{arg6},S)$(TS_ARRAY({arg6}) AND NOT SUM(SL$RS_BELOW(R,{arg6},SL),TS_MAP(R,SL,S)*TS_ARRAY(SL))),
                       TS_ARRAY({arg6}){iwgt})));)));
*-----------------------------------------------------------------------------
""",
    )
    if arg11 == "0":
        module.tc.add_gams_code(
            module=module,
            phase="run",
            code=rf"""
{arg1}({regy},{arg2}{arg10},S{arg4})$((NOT {arg1}({regy},{arg2}{arg10},S{arg4}))${arg3}(R,{arg2},S)) $= {arg1}({regy},{arg2}{arg10},'ANNUAL'{arg4});
""",
        )
    if len(arg11):
        module.tc.add_gams_code(
            module=module,
            phase="run",
            code=rf"""
{arg1}(R,LL,{arg2}{arg10},S{arg4})$((NOT {arg3}(R,{arg2},S)){take}) = 0;
""",
        )


def pp_lvlfc_mod(
    module: GamsClass,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg7: str,
    arg8: str,
    arg9: str,
    arg10: str,
    arg11: str,
    arg12: str,
) -> None:
    clear_uncd7(module=module)

    take = arg12
    regy = f"R,{arg7}"
    ts = f"(NOT {arg3}(R,{arg2},S))$"
    awgt = "G_YRFR(R,S)/G_YRFR(R,TS)"
    iwgt = ""
    if not len(arg7):
        regy = "R"
    if arg6 == "S2":
        ts = ""
    if arg9 == "1":
        awgt = "1"
        iwgt = f"*G_YRFR(R,S)/G_YRFR(R,{arg6})"
    if arg11 == "N":
        take = f"${arg1}(R,'0',{arg2}{arg10},'ANNUAL'{arg4})"

    all_exec(
        module=module,
        take=take,
        regy=regy,
        ts=ts,
        awgt=awgt,
        iwgt=iwgt,
        arg1=arg1,
        arg2=arg2,
        arg3=arg3,
        arg4=arg4,
        arg5=arg5,
        arg6=arg6,
        arg8=arg8,
        arg10=arg10,
        arg11=arg11,
    )
