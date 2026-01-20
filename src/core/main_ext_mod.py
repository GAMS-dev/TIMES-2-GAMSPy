# main_ext_mod.py

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class MainExtMod(GamsClass):
    """Translation unit for main_ext.mod."""

    # Instance attributes
    module_name: str = "main_ext_mod"
    gams_source: str = "main_ext.mod"

    def __init__(
        self, tc: "TimesModelClass", env: "CompileEnvironment", arg1: str, arg2: str
    ):
        self.env = env.fork()
        self.snapshot = None
        self.arg1 = arg1
        self.arg2 = arg2
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        pass

    def run(self, tc: "TimesModelClass") -> None:
        pass
