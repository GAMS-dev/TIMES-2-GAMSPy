# initmty_msa.py

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyMsa(GamsClass):
    """Translation unit for initmty.msa."""

    # Instance attributes
    module_name: str = "initmty_msa"
    gams_source: str = "initmty.msa"

    def __init__(
        self,
        tc: "TimesModelClass",
        env: "CompileEnvironment",
    ):
        self.env = env.fork()
        self.snapshots = {}
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)

    def run(self, tc: "TimesModelClass") -> None:
        phase = "run"
        print(phase)
