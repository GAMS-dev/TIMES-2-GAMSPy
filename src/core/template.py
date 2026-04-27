# filename_ext.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.fillparm_gms import FillparmGms

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class TemplateMod(GamsClass):  # FilenameExt
    """Translation unit for filename.extension."""

    # Instance attributes
    module_name: str = "filename_ext"
    gams_source: str = "filename.ext"

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
        self.compile()

    def compile(self) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="init",
            code=rf"""
PARAMETER {self.arg3} //;
""",
        )
        # fmt: off
        batincludes = [
            ("VDA_EMCB", "R", "C,COM", ",'0','0','0','0'", "V", "1", "GE 0", ""),
        ]
        # fmt: on
        for arg in batincludes:
            self.include(
                FillparmGms(
                    self.tc,
                    self.env,
                    arg1=arg[0],
                    arg2=arg[1],
                    arg3=arg[2],
                    arg4=arg[3],
                    arg5=arg[4],
                    arg6=arg[5],
                    arg7=arg[6],
                    arg8=arg[7],
                )
            )
        if self.tc.defined("GR_VARGEN"):
            pass
        if self.env.powerflow.upper() == "YES":  # IFI
            pass
        self.tc.enqueue(
            self.exec1,
            waver=self.env.waver.upper() == "YES",
        )

    def exec1(self: TemplateMod, waver: bool) -> None:
        self.tc.add_gams_code(
            module=self,
            phase="run",
            code=rf"""
  FLO_FUNCX(R,LL,P,C,CG)$(NOT PRC_VINT(R,P)) = {"0" if waver else "1"};
""",
        )
