# pp_lvlpk_mod.py

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class PpLvlpkMod(GamsClass):
    """Translation unit for pp_lvlpk.mod."""

    # Instance attributes
    module_name: str = "pp_lvlpk_mod"
    gams_source: str = "pp_lvlpk.mod"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)
