# initmty_ier.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyIer(GamsClass):
    """Translation unit for initmty.ier."""

    # Instance attributes
    module_name: str = "initmty_ier"
    gams_source: str = "initmty.ier"

    def __init__(
        self,
        tc: TimesModelClass,
        env: CompileEnvironment,
    ):
        self.env = env.fork()
        self.tc = tc
        self._sub_modules = {}
        self.compile()

    def compile(self) -> None:
        phase = "init"
        print(phase)
