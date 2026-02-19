# <filename_ext>.py

import logging
from typing import TYPE_CHECKING

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
        tc: "TimesModelClass",
        env: "CompileEnvironment",
    ):
        self.env = env.fork()
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)
