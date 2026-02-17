# equcrtp_vda.py

import logging
from typing import TYPE_CHECKING

from .base_class import GamsClass

if TYPE_CHECKING:
    from .compile_environment import CompileEnvironment
    from .times_model_class import TimesModelClass

logger = logging.getLogger(__name__)


class EqucrtpVda(GamsClass):
    """Translation unit for equcrtp.vda."""

    # Instance attributes
    module_name: str = "equcrtp_vda"
    gams_source: str = "equcrtp.vda"

    def __init__(
        self, tc: "TimesModelClass", env: "CompileEnvironment", arg1: str = ""
    ):
        self.env = env.fork()
        self.arg1 = arg1
        self._sub_modules = {}
        self.compile(tc)

    def compile(self, tc: "TimesModelClass") -> None:
        phase = "init"
        print(phase)
