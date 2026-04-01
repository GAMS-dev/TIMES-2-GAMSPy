# initmty_mlf.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyMlf(GamsClass):
    """Translation unit for initmty.mlf."""

    # Instance attributes
    module_name: str = "initmty_mlf"
    gams_source: str = "initmty.mlf"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
        arg1: str = "",
        arg2: str = "",
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase = "init"
        print(phase)
