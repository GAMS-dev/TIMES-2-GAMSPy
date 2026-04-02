# prepparm_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2025 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * PREPPAR : Prepare parameters for preprocessing
# * Description: Non-default interpolation/extrapolation according to user option
# *              DFUNC = -1-> no interpolation, 0-> default action, 10->intra-period
# *              DFUNC = +1-> interp., 2->interp.+EPS, 3->interp.+extrap.
# *              DFUNC >999 -> exponential interpolation beyond year DFUNC
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1
# *      arg3 - control set 2
# *      arg4 - UNCD7 residual dimension
# *      arg5 - MODLYEAR or MILESTONYR depending on parameter
# *      arg6 - RTP controlling the assignment to the MODLYEARs
# *      arg7 - Option to prohibit extrapolation (1 for other than cost parameters)
# *      arg8 -
# *      arg9 -
# *      arg10-
# *******************************************************************************


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepparmGms(GamsClass):
    """Translation unit for prepparm.gms."""

    # Instance attributes
    module_name: str = "prepparm_gms"
    gams_source: str = "prepparm.gms"

    def __init__(
        self: PrepparmGms,
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
        self._sub_modules = {}
        self.compile()

    def compile(self: PrepparmGms) -> None:
        self.env.set_local("data", f"MY_FIL2({self.arg5})")
        self.env.set_local("opt", "*")
        self.env.set_local("ll", "")
        if not self.arg7 == "0":
            self.env.set_local("ll", f",'{self.env.dflbl}'")
            self.env.set_local("opt", "")
        if len(self.arg8):
            self.env.set_local("def_iebd", self.arg8)
        if len(self.arg9):
            self.tc.add_gams_code(
                module=self,
                phase="init",
                code=f"PARAMETER {self.arg9}({self.arg2},{self.arg3},ALLYEAR);",
            )

        # Universe set workaround
        self.add_records_to_universe_item(records=[self.arg1])

        if self.tc.test_run:
            self.tc.save_test_state(env=self.env, checkpoint="prepparm_gms")

        self.tc.enqueue(
            self.interpolation_extrapolation,
            arg1=self.arg1,
            arg2=self.arg2,
            arg3=self.arg3,
            arg4=self.arg4,
            arg5=self.arg5,
            arg6=self.arg6,
            arg7=self.arg7,
            arg8=self.arg8,
            arg9=self.arg9,
            arg10=self.arg10,
            dflbl=self.env.dflbl,
            def_iebd=self.env.def_iebd,
            reset=self.env.reset,
        )

    def interpolation_extrapolation(
        self: PrepparmGms,
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
        dflbl: str,
        def_iebd: str,
        reset: str,
    ):
        prepparm(
            module=self,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            arg4=arg4,
            arg5=arg5,
            arg6=arg6,
            arg7=arg7,
            arg8=arg8,
            arg9=arg9,
            arg10=arg10,
            dflbl=dflbl,
            def_iebd=def_iebd,
            reset=reset,
        )


def prepparm(
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
    dflbl: str,
    def_iebd: str,
    reset: str,
) -> None:
    # TODO: put into function that depends on the environment given
    data = f"MY_FIL2({arg5})"
    opt = False
    ll = ""
    if arg7 != "0":
        ll = f",'{dflbl}'"
        opt = True

    if len(arg8):
        def_iebd = arg8

    code = f"""
* conditional interpolation flag
IF(G_NOINTERP, INT_DEFAULT('{arg1}')=NO;
ELSE OPTION CLEAR=UNCD7; CNT = ({def_iebd}+(3-{def_iebd})$IE_DEFAULT('{arg1}'))${arg7};
IF(CNT=0, UNCD7({arg2}{ll},{arg3}{arg4})$({arg1}({arg2},'{dflbl}',{arg3})>0) = YES;
"""

    if opt:
        code += f"""
ELSE UNCD7({arg2},{arg5},{arg3}{arg4})$({arg1}({arg2},'{dflbl}',{arg3})=-13) $= {arg1}({arg2},{arg5},{arg3});
    IF(CARD(UNCD7),{arg1}({arg2},{arg5},{arg3})$UNCD7({arg2},{arg5},{arg3}{arg4})=0; OPTION CLEAR=UNCD7);
    UNCD7({arg2},LL--ORD(LL),{arg3}{arg4})$(({arg10}({arg1}({arg2},'{dflbl}',{arg3}))>-.5)${arg1}({arg2},LL,{arg3}))=YES;
"""

    code += "   );\n"

    code += f"""
LOOP(UNCD7({arg2}{ll},{arg3}{arg4}), DFUNC = CNT; DFUNC $= ROUND({arg1}({arg2},'{dflbl}',{arg3}));
    MY_ARRAY(DM_YEAR) = {arg1}({arg2},DM_YEAR,{arg3}); OPTION CLEAR=MY_FIL2;
* do interpolate
    IF(DFUNC NE 10, LAST_VAL=0; F = 0; Z = 0;
    LOOP(DM_YEAR$MY_ARRAY(DM_YEAR),          {"! check for nonzero (including EPS)" if False else ""}
        MY_F = MY_ARRAY(DM_YEAR); Z = YEARVAL(DM_YEAR);
        IF(LAST_VAL,
            IF((Z GT DFUNC)$(DFUNC GT 999),     {"! exponential function" if False else ""}
            {data}$((Z>YEARVAL({arg5}))$(YEARVAL({arg5})>MY_FYEAR))
        = LAST_VAL*POWER(1+MY_F,YEARVAL({arg5})-MY_FYEAR)+EPS;
            MY_F = LAST_VAL*POWER(1+MY_F,Z-MY_FYEAR)+EPS;
            MY_FIL2(DM_YEAR) = MY_F;         {"! overwrite old data" if False else ""}
            ELSE                                {"! linear interpolation" if False else ""}
            {data}$((Z>YEARVAL({arg5}))$(YEARVAL({arg5})>MY_FYEAR))
        = LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(YEARVAL({arg5})-MY_FYEAR);
            );
        ELSE F = Z; FIRST_VAL = MY_F);
        LAST_VAL = MY_F; MY_FYEAR=Z;);        {"! remember the value and year" if False else ""}
"""
    if opt:
        code += f"""
    ELSE FIRST_VAL = 0; MY_FYEAR = 0;          {"! intra-period I/E" if False else ""}
    LOOP(MY_FIL(LL)$MY_ARRAY(MY_FIL),        {"! check for data values" if False else ""}
        MY_F = MY_ARRAY(LL); Z = YEARVAL(LL); F = FIL2(LL);
        IF(MY_FYEAR < F, IF(F > MIN(FIRST_VAL,Z), LAST_VAL = MY_F; FIRST_VAL = F);
        MY_FIL2({arg5}(LL+(F-YEARVAL(LL))))$(NOT MY_ARRAY({arg5})) = LAST_VAL+(MY_F-LAST_VAL)/(Z-MY_FYEAR)*(F-MY_FYEAR));
        LAST_VAL = MY_F; MY_FYEAR=Z;);       {"! remember the value and year" if False else ""}
    DFUNC = {arg7};
"""
    code += ");\n"
    if opt:
        code += f"""
    IF(FLOOR(DFUNC/10)=1,
    LOOP(MIYR_1(LL), MY_FYEAR=YEARVAL(LL);
        MY_F = FIL2(LL+(F-MY_FYEAR)); IF(MY_F<F$MY_F,MY_FIL2({arg5}(LL+(MY_F-MY_FYEAR))) = FIRST_VAL);
        MY_F = FIL2(LL+(Z-MY_FYEAR)); IF(MY_F>Z,MY_FIL2({arg5}(LL+(MY_F-MY_FYEAR))) = LAST_VAL));
    DFUNC=DFUNC-10);
"""
    code += f"""
    IF(DFUNC NE {arg7},
* Do back/forward extrapolate, or fill in with EPS
    IF(DFUNC LE 2, {data}$({arg6}$(NOT {data}+MY_ARRAY({arg5}))) = EPS; ELSE
        IF(DFUNC EQ 4, Z = INF; ELSEIF DFUNC EQ 5, F = 0);
        {data}$({arg6}) $= FIRST_VAL$(YEARVAL({arg5})<F) + LAST_VAL$(YEARVAL({arg5})>Z);
        IF((NOT {arg7})$LAST_VAL, {data}$({arg6}$(NOT {data}+MY_ARRAY({arg5})))=EPS);
    ));
"""
    if 0 == len(arg9):
        code += f"{arg1}({arg2},{arg5},{arg3})   $= {data};"
    else:
        code += f"{arg9}({arg2},{arg3},{arg5})$({arg6}) $= {data};"
    code += ");\n"

    if not arg10 == "+":
        code += f"{arg1}({arg2},'0',{arg3})$(MAX(0,{arg1}({arg2},'0',{arg3})-MAX({arg7},{reset}))${arg1}({arg2},'0',{arg3})) = {reset};"
    if len(arg9):
        code += f"{arg1}({arg2},{arg5},{arg3}) $= {arg9}({arg2},{arg3},{arg5}); OPTION KILL={arg9};"
    code += f"  ); {arg1}({arg2},'EMPTY',{arg3})=0;"

    module.tc.add_gams_code(module=module, phase="run", code=code)
