# prepparam_gms.py
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
# *******************************************************************************


import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PrepparamGms(GamsClass):
    """Translation unit for prepparam.gms."""

    # Instance attributes
    module_name: str = "prepparam_gms"
    gams_source: str = "prepparam.gms"

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
        phase = "init"
        self.env.set_local("data",f"MY_FIL2({self.arg5})")
        self.env.set_local('opt', "*")
        self.opt = False
        self.env.set_local("ll", "")
        if not self.arg7 == "0":
            self.env_set_local("ll", f",'{self.env.dflbl}'")
            self.env.set_local('opt', "")
            self.opt = True
        self.def_iebd = self.env.def_iebd
        if len(self.arg8):
            self.env.set_local("def_iebd", self.arg8)
        if len(self.arg9):
            tc.add_gams_code(
                module=self,
                phase=phase,
                code=f"PARAMETER {self.arg9}({self.arg2},{self.arg3},ALLYEAR);",
            )
        tc.enqueue(self.interpolation_extrapolation, tc)

    def interpolation_extrapolation(self, tc):
        code = f"""
$EOLCOM !
* conditional interpolation flag
IF(G_NOINTERP, INT_DEFAULT('{self.arg1}')=NO;
  ELSE OPTION CLEAR=UNCD7; CNT = ({self.def_iedb}+(3-{self.def_iedb})$IE_DEFAULT('{self.arg1}'))${self.arg7};
   IF(CNT=0, UNCD7({self.arg2}{self.ll},{self.arg3}{self.arg4})$({self.arg1}({self.arg2},'{dflbl},{self.arg3})>0) = YES;
"""
        if self.opt:
            code += f"""
   ELSE UNCD7({self.arg2},{self.arg5},{self.arg3}{self.arg4})$({self.arg1}({self.arg2},'{self.env.dflbl}',{self.arg3})=-13) $= {self.arg1}({self.arg2},{self.arg5},{self.arg3});
     IF(CARD(UNCD7),{self.arg1}({self.arg2},{self.arg5},{self.arg3})$UNCD7({self.arg2},{self.arg5},{self.arg3}{self.arg4})=0; OPTION CLEAR=UNCD7);
     UNCD7({self.arg2},LL--ORD(LL),{self.arg3}{self.arg4})$(({self.arg10}({self.arg1}({self.arg2},'{self.env.dflbl}',{self.arg3}))>-.5)${self.arg1}({self.arg2},LL,{self.arg2}))=YES;
"""
        code += f"""
   LOOP(UNCD7({self.arg2}{self.ll},{self.arg3}{self.arg4}), DFUNC = CNT; DFUNC $= ROUND({self.arg1}({self.arg2},'{self.env.dflbl}',{self.arg3}));
      MY_ARRAY(DM_YEAR) = {self.arg1}({self.arg2},DM_YEAR,{self.arg3}); OPTION CLEAR=MY_FIL2;
* do interpolate
      IF(DFUNC NE 10, LAST_VAL=0; F = 0; Z = 0;
        LOOP(DM_YEAR$MY_ARRAY(DM_YEAR),          ! check for nonzero (including EPS)
           MY_F = MY_ARRAY(DM_YEAR); Z = YEARVAL(DM_YEAR);
           IF(LAST_VAL,
             IF((Z GT DFUNC)$(DFUNC GT 999),     ! exponential function
                {self.data}$((Z>YEARVAL({self.arg5}))$(YEARVAL({self.arg5})>MY_FYEAR))
			= LAST_VAL*POWER(1+MY_F,YEARVAL({self.arg5})-MY_FYEAR)+EPS;
                MY_F = LAST_VAL*POWER(1+MY_F,Z-MY_FYEAR)+EPS;
                MY_FIL2(DM_YEAR) = MY_F;         ! overwrite old data
             ELSE                                ! linear interpolation
                {self.data}$((Z>YEARVAL({self.arg5}))$(YEARVAL({self.arg5})>MY_FYEAR))
			= LAST_VAL + (MY_F-LAST_VAL)/(Z-MY_FYEAR)*(YEARVAL({self.arg5})-MY_FYEAR);
             );
           ELSE F = Z; FIRST_VAL = MY_F);
           LAST_VAL = MY_F; MY_FYEAR=Z;);        ! remember the value and year
"""
        if self.opt:
            code += f"""
      ELSE FIRST_VAL = 0; MY_FYEAR = 0;          ! intra-period I/E
        LOOP(MY_FIL(LL)$MY_ARRAY(MY_FIL),        ! check for data values
          MY_F = MY_ARRAY(LL); Z = YEARVAL(LL); F = FIL2(LL);
          IF(MY_FYEAR < F, IF(F > MIN(FIRST_VAL,Z), LAST_VAL = MY_F; FIRST_VAL = F);
            MY_FIL2({self.arg5}(LL+(F-YEARVAL(LL))))$(NOT MY_ARRAY({self.arg5})) = LAST_VAL+(MY_F-LAST_VAL)/(Z-MY_FYEAR)*(F-MY_FYEAR));
            LAST_VAL = MY_F; MY_FYEAR=Z;);       ! remember the value and year
        DFUNC = {self.arg7};
"""
        code += ");\n"
        if self.opt:
            code += f"""
      IF(FLOOR(DFUNC/10)=1,
        LOOP(MIYR_1(LL), MY_FYEAR=YEARVAL(LL);
         MY_F = FIL2(LL+(F-MY_FYEAR)); IF(MY_F<F$MY_F,MY_FIL2({self.arg5}(LL+(MY_F-MY_FYEAR))) = FIRST_VAL);
         MY_F = FIL2(LL+(Z-MY_FYEAR)); IF(MY_F>Z,MY_FIL2({self.arg5}(LL+(MY_F-MY_FYEAR))) = LAST_VAL));
        DFUNC=DFUNC-10);
"""
        code += f"""
      IF(DFUNC NE {self.arg7},
* Do back/forward extrapolate, or fill in with EPS
       IF(DFUNC LE 2, {self.data}$({self.arg6}$(NOT {self.data}+MY_ARRAY({self.arg5}))) = EPS; ELSE
         IF(DFUNC EQ 4, Z = INF; ELSEIF DFUNC EQ 5, F = 0);
         {self.data}$({self.arg6}) $= FIRST_VAL$(YEARVAL({self.arg5})<F) + LAST_VAL$(YEARVAL({self.arg5})>Z);
         IF((NOT {self.arg7})$LAST_VAL, {self.data}$({self.arg6}$(NOT {self.data}+MY_ARRAY({self.arg5})))=EPS);
      ));
"""
        if len(self.arg9):
            code += (
                f"{self.arg1}({self.arg2},{self.arg5},{self.arg3})   $= {self.data};"
            )
        else:
            code += f"{self.arg9}({self.arg2},{self.arg3},{self.arg5})$({self.arg6}) $= {self.data};"
        code += ");\n"

        if not self.arg10 == "+.":
            code += f"{self.arg1}({self.arg2},'0',{self.arg3})$(MAX(0,{self.arg1}({self.arg2},'0',{self.arg3})-MAX({self.arg7},{self.env.reset}))${self.arg1}({self.arg2},'0',{self.arg3})) = {self.env.reset};"
        if len(self.arg9):
            code += f"{self.arg1}({self.arg2},{self.arg5},{self.arg3}) $= {self.arg9}({self.arg2},{self.arg3},{self.arg5}); OPTION KILL={self.arg9};"
        code += f"  ); {self.arg1}({self.arg2},'EMPTY',{self.arg3})=0;"

        tc.add_gams_code(
            module=self,
            phase="run",
            code=code,
        )
