# initmty_stc.py


import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class InitmtyStc(GamsClass):
    """Translation unit for initmty.stc"""

    # Instance attributes
    module_name: str = "initmty_stc"
    gams_source: str = "initmty.stc"

    def __init__(self, tc: "TimesModelClass", env: "CompileEnvironment"):
        self.env = env.fork()
        self.snapshot = None
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        pass

    def run(self, tc: "TimesModelClass") -> None:
        pass
