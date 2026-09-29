# solsubta_ans.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *---------------------------------------------------------------------
# * SOLSUB_TA.ANS
# *
# * Sub routine for SOLPUTTA.ANS to ouput ANSWER dumps
# *   arg1  - control set
# *   arg2  - qualifier
# *   arg3  - parameter name
# *   arg4  - region
# *   arg5  - process
# *   arg6  - commodity
# *   arg7  - vintage
# *   arg8  - timeslice
# *   arg9  - .Level/.Marginal indicator
# *   arg10 - result values
# *   arg11 - loop indices
# *   arg12 - assigned indices
# *   - Looping over all rows and filling cells
# *
# *---------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class SolsubtaAns(GamsClass):
    """Translation unit for solsubta.ans."""

    # Instance attributes
    module_name: str = "solsubta_ans"
    gams_source: str = "solsubta.ans"

    def __init__(
        self,
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
        arg13: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
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
        self.arg13 = arg13
        self.compile()

    def compile(self) -> None:
        self.env.set_scoped("sow", "1")
        self.env.set_scoped("sow_GP", ("1",))
        if self.env.stages.upper() == "YES":
            self.env.set_scoped("sow", "SOW.TL")
            raise NotImplementedError("sow GP not implemented")

        self.tc.enqueue(
            self.exec1,
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
            arg11=self.arg11,
            arg12=self.arg12,
            arg13=self.arg13,
            supzero=self.env.supzero,
            sow=self.env.sow,
        )

    def exec1(
        self: SolsubtaAns,
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
        arg13: str,
        supzero: str,
        sow: str,
    ) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
*---------------------------------------------------------------------
*PUT                     @1,  'ATTRIB',
****                     @17, 'SCENARIO',
*                        @21, 'REG',
*                        @32, 'PRC',
*                        @57, 'COM'
*                        @82, 'VIN'
*                        @91, 'TS'
*                        @:1, 'P/D'
OPTION CLEAR={arg1};
{f"{arg1}{arg12}${arg2} $= {arg10};" if supzero != "NO" else ""}
{f"{arg1}{arg12}${arg2}  = YES;" if supzero == "NO" else ""}
LOOP(({arg1}{arg11}),
* print trigger so that only output once
                     PUT @1,   '{arg3}':0, '{arg9}':0, {arg13}
                         @17,  {sow},
                         @21,  {arg4},
                         @32,  {arg5},
                         @57,  {arg6},
                         @82,  {arg7},
                         @91,  {arg8}, @116
{"LOOP(T, " if arg9 != "" else ""}
                          PUT ({arg10}):12,' ':0
{"  )" if arg9 != "" else ""}
                     PUT  / ;
    );
OPTION CLEAR={arg1};
""",
        )
