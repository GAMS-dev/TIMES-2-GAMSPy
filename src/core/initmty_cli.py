# initmty_cli.py

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyCli(GamsClass):
    """Translation unit for initmty.cli."""

    # Instance attributes
    module_name: str = "initmty_cli"
    gams_source: str = "initmty.cli"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)
