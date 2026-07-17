# gdxfilter_gms.py
# *++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# * Copyright (C) 2023 IEA-ETSAP.  Licensed under GPLv3 (see file NOTICE-GPLv3.txt).
# *=============================================================================*
from __future__ import annotations

import logging
import platform
from typing import TYPE_CHECKING

from core.base_class import GamsClass

if TYPE_CHECKING:
    from utils.compile_environment import CompileEnvironment
    from utils.times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class GdxfilterGms(GamsClass):
    """Translation unit for gdxfilter.gms."""

    module_name: str = "gdxfilter_gms"
    gams_source: str = "gdxfilter.gms"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.tc = tc
        self.arg1 = arg1
        self.compile()

    def compile(self) -> None:
        self.main()

        # skipped the following because with up-to-date GAMS, only $LABEL MAIN is used.
        # *------------------------------------------------------------------------------
        # $ LABEL DAM_COST
        # * Prepare for killing with GAMS 34.2
        # $ LABEL MORE
        # $ IF %1.==. $GOTO PUTOUT
        # $ IF DECLARED %1
        # $ IF NOT DEFINED %1 $SET MX %1 %MX%
        # $ SHIFT GOTO MORE
        # $ LABEL PUTOUT
        # $ echon $KILL %MX% > _dd_.dmp

    def main(self) -> None:
        self.env.set_scoped("tmp", "'")
        self.env.set_scoped("mx", "")
        self.env.set_scoped("mx_GP", ())
        if platform.system().upper().startswith("WIN"):
            self.env.set_scoped("tmp", '"')

        self.tc.enqueue(self.display_warning)

        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
$hiddencall gdxdump _dd_.gdx NODATA > _dd_.dmp
$hiddencall sed {self.env.tmp}/^\(Scalar\|[^$(]*([^,]*)\|[^$].*empty *$\)/{{N;d;}}; /^\([^$]\|$\)/d; s/\$LOAD.. /\$LOADR /I{self.env.tmp} _dd_.dmp > _dd_.dd
$INCLUDE _dd_.dd
$GDXIN
$hiddencall rm -f _dd_.dmp
""",
        )

    def display_warning(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=r"""
DISPLAY 'GAMS Warnings detected; Data have been Filtered via GDX';
""",
        )
