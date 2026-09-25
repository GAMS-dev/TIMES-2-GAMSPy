# fillsow_stc.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2000-2023 Energy Technology Systems Analysis Programme (ETSAP)
# * This file is part of the IEA-ETSAP TIMES model generator, licensed
# * under the GNU General Public License v3.0 (see file NOTICE-GPLv3.txt).
# *******************************************************************************
# * FILLSOW : Fill stochastic parameters
# * Description: Preprocessing of stochastic uncertain data
# * Parameters:
# *      arg1 - table name
# *      arg2 - control set 1 (before year index)
# *      arg3 - control set 2 (after year index)
# *      arg4 - Source data years T/LL
# *      arg5 - YES/NO for absolute/relative parameters
# *      arg6 - PERIOD control (SW_T OR PERIODYR OR SUPERYR)
# *      arg7 - YES/NO to copy baseline parameters
# *******************************************************************************
# *$ONLISTING

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class FillsowStc(GamsClass):
    """Translation unit for fillsow.stc."""

    # Instance attributes
    module_name: str = "fillsow_stc"
    gams_source: str = "fillsow.stc"

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
    ) -> None:
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
        self.compile()

    def compile(self) -> None:
        self.env.set_local("tail", f",{self.arg3}")
        self.env.set_local("stg", "")
        self.env.set_local("ix", "'0'")

        if not len(self.arg3):
            self.env.set_local("tail", "")

        if not len(self.arg4):
            self.env.set_local("ix", "")

        if self.arg4 == "T":
            self.env.set_local("stg", "SW_TSTG(T,J)$")

        self.tc.enqueue(
            clean_up_sow,
            module=self,
            tail=self.env.tail,
            ix=self.env.ix,
            stg=self.env.stg,
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
        )

        if self.arg5 != "YES":
            return

        self.tc.enqueue(
            update_data_indicators,
            module=self,
            tail=self.env.tail,
            ix=self.env.ix,
            stg=self.env.stg,
            arg1=self.arg1,
            arg2=self.arg2,
            arg4=self.arg4,
            arg6=self.arg6,
            arg7=self.arg7,
        )


def clean_up_sow(
    module: GamsClass,
    tail: str,
    ix: str,
    stg: str,
    arg1: str,
    arg2: str,
    arg4: str,
) -> None:
    module.tc.add_gams_code(
        module=module,
        phase="run",
        code=rf"""
* Clean up stage 1 from invalid SOW:
  S_{arg1}({arg2}{arg4}{tail},'1',SOW)$(NOT SAMEAS(SOW,'1')) = 0;
* Set up data indicators
{f"S_{arg1}({arg2}LL--ORD(LL){tail},J,WW) $= S_{arg1}({arg2}LL{tail},J,WW);" if len(arg4) else ""}
  F = CARD(S_{arg1});

* Copy parameters from first to other branches when appropriate
  S_{arg1}({arg2}{arg4}{tail},J,WW)$({stg}(NOT S_{arg1}({arg2}{ix}{tail},J,WW))) $= SUM(SW_CPMAP(J,WW,SOW),S_{arg1}({arg2}{arg4}{tail},J,SOW));
""",
    )


def update_data_indicators(
    module: GamsClass,
    tail: str,
    ix: str,
    stg: str,
    arg1: str,
    arg2: str,
    arg4: str,
    arg6: str,
    arg7: str,
) -> None:
    module.tc.add_gams_code(
        module=module,
        phase="run",
        code=rf"""
* Update data indicators if eventual copy occurred
{f"IF(CARD(S_{arg1})>F, S_{arg1}({arg2}LL--ORD(LL){tail},J,WW) $= S_{arg1}({arg2}LL{tail},J,WW));" if len(arg4) else ""}

* Copy baseline parameters to stage 1, SOW 1:
{f"S_{arg1}({arg2}{arg4}{tail},'1','1')$(NOT S_{arg1}({arg2}{ix}{tail},'1','1')) $= {arg1}({arg2}{arg4}{tail});" if arg7 == "YES" else ""}

* Merge to single stage 1:

{f"LOOP(SW_TSTG(T,J), S_{arg1}({arg2}{arg4}{tail},'1',WW)$({arg6}$SW_T(T,WW)) $= SUM(SW_REV(WW,J,SOW),S_{arg1}({arg2}{arg4}{tail},J,SOW)));" if arg4.upper() == "LL" else f"LOOP(J$SW_START(J),S_{arg1}({arg2}{arg4}{tail},'1',WW)$({stg}{arg6}) $= SUM(SW_REV(WW,J,SOW),S_{arg1}({arg2}{arg4}{tail},J,SOW)));"}

* Remove flags if LL
{f"S_{arg1}({arg2}{ix}{tail},J,WW) = 0;" if arg4 == "LL" else ""}
""",
    )


def exec_fillsow_stc(
    module: GamsClass,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
    arg6: str,
    arg7: str,
) -> None:
    tail = arg3
    stg = ""
    ix = "0"

    if not len(arg3):
        tail = ""

    if not len(arg4):
        ix = ""

    if arg4 == "T":
        stg = "SW_TSTG(T,J)$"

    clean_up_sow(
        module=module,
        tail=tail,
        ix=ix,
        stg=stg,
        arg1=arg1,
        arg2=arg2,
        arg4=arg4,
    )

    if arg5 != "YES":
        return

    update_data_indicators(
        module=module,
        tail=tail,
        ix=ix,
        stg=stg,
        arg1=arg1,
        arg2=arg2,
        arg4=arg4,
        arg6=arg6,
        arg7=arg7,
    )
