# filparam_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILPARAM : Fill parameter
# * Description: Dense interpolation/extrapolation of parameters
# * Parameters:
# *      %1 - table name
# *      %2 - control set 1 (before year index)
# *      %3 - control set 2 (after year index)
# *      %4 - UNCD7 residual dimension
# *      %5 - Source data years (e.g. ALLYEAR, DM_YEAR)
# *      %6 - Target data years (e.g. ALLYEAR, MILESTONYR)
# *      %7 - Qualifier restricting backward extrapolation
# *      %8 - Qualifier restricting forward extrapolation
# *      %9 - Default interpolation option
# *******************************************************************************


import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class Filparam(GamsClass):
    """Translation unit for filparam.gms."""

    # Instance attributes
    module_name: str = "filparam_gms"
    gams_source: str = "filparam.gms"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
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
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        self.env.set_local("src", self.arg1)
        self.env.set_local("tail1", self.arg3)
        self.env.set_local("tail2", f",{self.arg3}")

        if self.arg3 == "":
            self.env.set_local("tail1", "''")
            self.env.set_local("tail2", "")

        tc.enqueue(
            self.assign_uncd7,
            tc=tc,
            tail1=self.env.tail1,
            tail2=self.env.tail2,
            src=self.env.src,
        )
        tc.enqueue(
            self.assign_dfunc,
            tc=tc,
            tail1=self.env.tail1,
            tail2=self.env.tail2,
            src=self.env.src,
        )
        tc.enqueue(self.interpolate, tc=tc, tail2=self.env.tail2)
        tc.enqueue(self.extrapolate, tc=tc, tail2=self.env.tail2)

    def assign_uncd7(self, tc, tail1, tail2, src):
        if self.arg10 == "":
            code_block = f"IF(YES, OPTION CLEAR = UNCD7; LOOP(({self.arg2}{self.arg5}{tail2})${src}({self.arg2}{self.arg5}{tail2}), UNCD7({self.arg2}{tail1}{self.arg4}) = YES));"
        else:
            code_block = f"IF(YES, OPTION CLEAR = UNCD7; UNCD7({self.arg2}LL--ORD(LL),{tail1}{self.arg4})${src}({self.arg2}LL{tail2}) = YES);"

        tc.add_gams_code(module=self, phase="run", code=code_block)

    def assign_dfunc(self, tc, tail1, tail2, src, dflbl):
        tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
 LOOP(UNCD7({self.arg2}{self.arg10}{tail1}{self.arg4}), F=0; Z=INF; MY_FYEAR=9999;
   DFUNC = ROUND({src}({self.arg2}'{dflbl}'{tail2}));
""",
        )
        if not self.arg9 == "":
            tc.add_gams_code(
                module=self, phase="run", code=f"IF(NOT DFUNC, DFUNC = {self.arg9});"
            )

        tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
   IF(DFUNC GE 0,
    MY_ARRAY({self.arg5}) = {src}({self.arg2}{self.arg5}{tail2}); MY_ARRAY('{dflbl}')=0;
""",
        )

    def interpolate(self, tc, tail2):
        tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
$ EOLCOM !
    LOOP({self.arg5}$MY_ARRAY({self.arg5}),              ! check for nonzero (including EPS)
	  MY_F = MY_ARRAY({self.arg5}); Z = YEARVAL({self.arg5});
	  IF(Z > MY_FYEAR+1,               ! linear interpolation
	     {self.arg1}({self.arg2}{self.arg6}{tail2})$((Z GT YEARVAL({self.arg6}))$(YEARVAL({self.arg6}) GT MY_FYEAR))
			= LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(YEARVAL({self.arg6})-MY_FYEAR); ! not the first one
	  ELSEIF Z LT MY_FYEAR, F=Z; FIRST_VAL = MY_F);
	  LAST_VAL = MY_F; MY_FYEAR=Z);    ! remember the value and year
""",
        )

    def extrapolate(self, tc, tail2):
        tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
    IF(DFUNC GT 1, DFUNC=MOD(DFUNC,10);
      IF(DFUNC EQ 2, FIRST_VAL=EPS; LAST_VAL=EPS; ELSEIF DFUNC EQ 4, Z=INF; ELSEIF DFUNC EQ 5, F=0));
    IF(DFUNC NE 1,
      {self.arg1}({self.arg2}{self.arg6}{tail2}) $= FIRST_VAL$({self.arg7}(YEARVAL({self.arg6}) LT F)) + LAST_VAL$({self.arg8}(YEARVAL({self.arg6}) GT Z));
    ));
  );
""",
        )
